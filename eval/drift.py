"""
Drift metrics and the RQ1 / RQ3 analyses for the long-horizon domains
(docs/LONG_SPEC.md, "Drift definitions" and "Decision rules").

Unit of analysis: one scored constraint in one episode. Each has a class,
the step it was committed at (its distance from the request), whether it
survived, and, if not, a drift type:

  entity_swap   the wrong value belongs to another entity in the same task
  neighbour_id  the wrong id differs from the right one by one swapped digit
                pair, or is a near-identical name
  semantic      the agent restated the user's value correctly (confirm
                label, remark) but bound it to the wrong item
  other         anything else

`prior_correct_action` marks failures where the agent had acted on the
right item earlier in the episode (tool-call evidence, Tier A), i.e. it
had the state and lost it: the strict definition of state drift.

    python -m eval.drift runs/rq1_long_qwen36_27b_fp8.jsonl
"""

import argparse
import json
import math
from collections import Counter, defaultdict

from eval.metrics import latest_scored

LANGS = ("en", "zh", "hi", "ta", "hinglish")
DRIFT_TYPES = ("entity_swap", "neighbour_id", "semantic")


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (c - r) / d), min(1.0, (c + r) / d))


def load(path):
    return [r for r in latest_scored([json.loads(l) for l in open(path, encoding="utf-8") if l.strip()])
            if r.get("domain") in ("shop", "pay") and not r.get("injected")]


def constraint_rows(records):
    rows = []
    for r in records:
        ok = r.get("constraint_ok") or {}
        for name, good in ok.items():
            step = r["constraint_commit_step"].get(name)
            rows.append({"episode": r["episode_key"], "domain": r["domain"], "template": r["template_id"],
                         "language": r["language"], "cell": r["cell"], "seam": r.get("seam"), "constraint": name,
                         "class": r["constraint_class"][name], "ok": bool(good), "step": step,
                         "distance": (step / r["horizon"]) if step else None,
                         "drift": None if good else r["drift_type"].get(name, "other"),
                         "prior_correct": bool(r.get("prior_correct_action", {}).get(name)),
                         "regrounding": bool(r.get("regrounding", {}).get(name))})
    return rows


def stage_of(row):
    """Failure taxonomy stage (project doc Section 9) for one failed constraint."""
    if row["regrounding"]:
        return "recovery / re-grounding"
    if row["drift"] in ("entity_swap", "neighbour_id"):
        return "entity handling"
    if row["drift"] == "semantic":
        return "state carryover (semantic)"
    if row["prior_correct"]:
        return "state carryover"
    return "reasoning / comprehension"


def episode_table(records, field="success"):
    out = {}
    for cell in sorted({r["cell"] for r in records}):
        for lang in LANGS:
            rs = [r for r in records if r["cell"] == cell and r["language"] == lang]
            if rs:
                k = sum(bool(r.get(field)) for r in rs)
                out[(cell, lang)] = (k, len(rs), wilson(k, len(rs)))
    return out


def drift_rates(rows):
    by = defaultdict(Counter)
    n = Counter()
    for r in rows:
        key = (r["cell"], r["language"])
        n[key] += 1
        if not r["ok"]:
            by[key][r["drift"]] += 1
            if r["prior_correct"]:
                by[key]["state_drift_strict"] += 1
    return {k: {t: round(100 * by[k][t] / n[k], 2) for t in DRIFT_TYPES + ("other", "state_drift_strict")} | {"n": n[k]}
            for k in n}


def distance_model(rows, cell=None):
    """Constraint failure ~ language * distance + class + domain: logistic
    regression with standard errors clustered by episode. Distance is the
    commit step as a fraction of the episode. Global constraints (coupon,
    payment, batch) are not state elements and are left out. Returns the
    language x distance terms, each relative to English."""
    import pandas as pd
    import statsmodels.formula.api as smf
    d = pd.DataFrame([r for r in rows if r["distance"] is not None and r["class"] != "global"
                      and (cell is None or r["cell"] == cell)])
    if d.empty or d["ok"].all():
        return None
    d["fail"] = (~d["ok"]).astype(int)
    d = d.rename(columns={"class": "cclass"})
    d["language"] = pd.Categorical(d["language"], categories=[l for l in LANGS if l in set(d["language"])])
    formula = "fail ~ C(language) * distance + C(cclass)" + (" + C(domain)" if d["domain"].nunique() > 1 else "")
    fit = smf.logit(formula, data=d).fit(disp=0, maxiter=200, cov_type="cluster",
                                         cov_kwds={"groups": pd.factorize(d["episode"])[0]})
    terms = {k: (round(float(fit.params[k]), 3), round(float(fit.pvalues[k]), 4)) for k in fit.params.index if ":distance" in k}
    return {"terms": terms, "n_constraints": len(d), "n_episodes": int(d["episode"].nunique()),
            "distance_main": (round(float(fit.params["distance"]), 3), round(float(fit.pvalues["distance"]), 4))}


def rq1_decision(model, rates, cell):
    """Pre-registered rule (docs/LONG_SPEC.md): RQ1 is positive for language L
    if its language x distance term is > 0 with p < 0.05 AND its rate of
    typed drift (entity + neighbour + semantic) exceeds English's."""
    if model is None:
        return {}
    out = {}
    en = rates.get((cell, "en"), {})
    en_drift = sum(en.get(t, 0) for t in DRIFT_TYPES)
    for term, (coef, p) in model["terms"].items():
        lang = term.split("[T.")[1].split("]")[0]
        r = rates.get((cell, lang), {})
        drift = sum(r.get(t, 0) for t in DRIFT_TYPES)
        out[lang] = {"interaction": coef, "p": p, "typed_drift_per_100": drift, "english_typed_drift_per_100": en_drift,
                     "positive": coef > 0 and p < 0.05 and drift > en_drift}
    return out


def stage_table(rows):
    t = defaultdict(Counter)
    for r in rows:
        if not r["ok"]:
            t[(r["cell"], r["seam"], r["language"])][stage_of(r)] += 1
    return t


def report(records):
    rows = constraint_rows(records)
    lines = [f"{len(records)} episodes, {len(rows)} scored constraints"]
    for field, label in (("success", "Episode success, final step required (pre-registered)"),
                         ("success_state", "Episode success on the state built (handing the OTP / payment to the user allowed)")):
        lines.append(f"\n{label} (k/n, 95% CI)")
        for (cell, lang), (k, n, ci) in episode_table(records, field).items():
            lines.append(f"  {cell:<28} {lang:<9} {k:>3}/{n:<3} [{ci[0]:.2f}, {ci[1]:.2f}]")
    lines.append("\nStopped before the final irreversible step (handover), by language")
    for cell in sorted({r["cell"] for r in records}):
        for lang in LANGS:
            rs = [r for r in records if r["cell"] == cell and r["language"] == lang]
            if rs:
                h = sum(1 for r in rs if not r.get("completed"))
                lines.append(f"  {cell:<28} {lang:<9} {h}/{len(rs)}")
    rates = drift_rates(rows)
    lines.append("\nDrift per 100 constraints (entity_swap, neighbour_id, semantic, other, strict state drift)")
    for (cell, lang), r in sorted(rates.items()):
        lines.append(f"  {cell:<28} {lang:<9} " + "  ".join(f"{t}={r[t]:.1f}" for t in DRIFT_TYPES + ("other", "state_drift_strict")))
    for cell in sorted({r["cell"] for r in records}):
        try:
            m = distance_model(rows, cell)
        except Exception as e:
            lines.append(f"\n{cell}: distance model failed ({e})")
            continue
        lines.append(f"\n{cell}: failure ~ language x distance (logistic, SE clustered by episode)")
        if m is None:
            lines.append("  no failures")
            continue
        lines.append(f"  distance (English): {m['distance_main']}; {m['n_constraints']} constraints, {m['n_episodes']} episodes")
        for term, v in m["terms"].items():
            lines.append(f"  {term}: coef {v[0]}, p {v[1]}")
        for lang, d in rq1_decision(m, rates, cell).items():
            lines.append(f"  RQ1 {lang}: {'POSITIVE' if d['positive'] else 'not positive'} "
                         f"(interaction {d['interaction']}, p {d['p']}, typed drift {d['typed_drift_per_100']:.1f} vs en {d['english_typed_drift_per_100']:.1f})")
    lines.append("\nFailure stages (count of failed constraints)")
    for key, c in sorted(stage_table(rows).items(), key=lambda x: tuple(str(v) for v in x[0])):
        lines.append(f"  {key}: {dict(c)}")
    regs = [r for r in rows if r["regrounding"]]
    if regs:
        lines.append("\nRe-grounding constraints survived (after the mid-episode disruption)")
        by = defaultdict(list)
        for r in regs:
            by[(r["cell"], r["language"])].append(r["ok"])
        for k, v in sorted(by.items()):
            lines.append(f"  {k}: {sum(v)}/{len(v)}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    args = ap.parse_args()
    print(report(load(args.log)))


if __name__ == "__main__":
    main()


def mcnemar_exact(b, c):
    """Two-sided exact McNemar p-value from the discordant counts."""
    from math import comb
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def seam_report(records, english_records=()):
    """RQ3: success by seam x language, paired by instance, plus where the
    failures sit (stage) under each seam."""
    lines = []
    by = defaultdict(dict)
    for r in records:
        by[(r["template_id"], r["language"])][r["seam"]] = bool(r["success"])
    seams = sorted({r["seam"] for r in records})
    lines.append("Success by seam (k/n)")
    for lang in [l for l in LANGS if any(r["language"] == l for r in records)]:
        row = []
        for s in seams:
            v = [d[s] for (t, l), d in by.items() if l == lang and s in d]
            row.append(f"{s} {sum(v)}/{len(v)}")
        lines.append(f"  {lang:<9} " + "   ".join(row))
    en = [r for r in english_records if r["language"] == "en"]
    if en:
        lines.append(f"  en (S0)   {sum(r['success'] for r in en)}/{len(en)}")
    lines.append("\nPaired seam contrasts (same instance, same language): b = only first seam succeeds, c = only second")
    for a, b_ in (("S1", "S2"), ("S2", "S3"), ("S1", "S3")):
        if a not in seams or b_ not in seams:
            continue
        for lang in [l for l in LANGS if any(r["language"] == l for r in records)]:
            pairs = [(d[a], d[b_]) for (t, l), d in by.items() if l == lang and a in d and b_ in d]
            bb = sum(1 for x, y in pairs if x and not y)
            cc = sum(1 for x, y in pairs if y and not x)
            lines.append(f"  {a} vs {b_} {lang:<9} n={len(pairs)} b={bb} c={cc} exact McNemar p={mcnemar_exact(bb, cc):.3f}")
    rows = constraint_rows(records)
    lines.append("\nFailed constraints by stage and seam")
    t = defaultdict(Counter)
    for r in rows:
        if not r["ok"]:
            t[(r["seam"], r["language"])][stage_of(r)] += 1
    for k, c in sorted(t.items()):
        lines.append(f"  {k}: {dict(c)}")
    return "\n".join(lines)
