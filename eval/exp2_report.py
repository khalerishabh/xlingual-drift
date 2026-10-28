"""
Experiment 2 evaluation for RQ1 and RQ2 (docs/EXP2_SPEC.md, sections 6 and 10).
Unit: the first attempt of each episode; a reply that hit max_tokens is a
failure ("loop"); endpoint errors are dropped (they were retried).

RQ1  success and drift by language group x horizon format: strict success,
     outcome decomposition, logistic model with a group x horizon term
     (cluster-robust by task), anchor survival, Pass^3, cost.
RQ2  where failures arise: episode failure stage, constraint failure rate by
     class, position of the first failure, decoy hits, tool-call errors.

    python -m eval.exp2_report runs/exp2_food_qwen36_27b_fp8.jsonl \
        runs/exp2_shopping_qwen36_27b_fp8.jsonl \
        runs/exp2_payment_qwen36_27b_fp8.rescored_waive.jsonl --out results/exp2_rq1_rq2.json
"""

import argparse
import json
import math
import re
from collections import Counter, defaultdict

from eval.drift import wilson
from eval.stages import GROUPS, STAGE_OF, episode_outcome, label, load_first_attempts

LANGS = ("en", "hi", "ta", "hinglish", "tanglish")
GROUP_ORDER = ("native", "non_native", "code_mixed")
FORMATS = ("short", "medium", "long")
SCRIPT = {"hi": (0x0900, 0x097F), "ta": (0x0B80, 0x0BFF)}


def rate(k, n):
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": round(k / n, 4) if n else None, "ci": [round(lo, 4), round(hi, 4)]}


def fisher_two_sided(a, n1, b, n2):
    big_n, k = n1 + n2, a + b

    def h(x):
        return math.comb(k, x) * math.comb(big_n - k, n1 - x) / math.comb(big_n, n1)
    p0 = h(a)
    return sum(h(x) for x in range(max(0, k - n2), min(k, n1) + 1) if h(x) <= p0 * (1 + 1e-9))


def outcome_table(rows, keyf):
    by = defaultdict(Counter)
    for r in rows:
        by[keyf(r)][episode_outcome(r)] += 1
    return {str(k): dict(v) for k, v in sorted(by.items(), key=lambda kv: str(kv[0]))}


def logistic(rows):
    import numpy as np
    import pandas as pd
    import statsmodels.formula.api as smf
    df = pd.DataFrame([{"y": int(episode_outcome(r) == "success"), "group": GROUPS[r["language"]],
                        "language": r["language"], "h": r["horizon"], "domain": r["domain"],
                        "task": r["template_id"]} for r in rows])
    df["hc"] = (df["h"] - df["h"].mean()) / 10.0
    out = {}
    for name, formula in (("group", "y ~ C(group, Treatment('native')) * hc + C(domain)"),
                          ("language", "y ~ C(language, Treatment('en')) * hc + C(domain)")):
        try:
            m = smf.glm(formula, df, family=__import__("statsmodels.api").api.families.Binomial()).fit(
                cov_type="cluster", cov_kwds={"groups": pd.factorize(df["task"])[0]})
            out[name] = {t: {"coef": round(float(m.params[t]), 3), "se": round(float(m.bse[t]), 3),
                             "p": round(float(m.pvalues[t]), 4),
                             "odds_ratio": round(float(np.exp(m.params[t])), 3)} for t in m.params.index}
        except Exception as e:
            out[name] = {"error": str(e)}
    out["note"] = "hc = gold tool calls, centred, per 10 calls; SE clustered by task (template); domain fixed effect"
    return out


def reasoning_script_share(rows):
    out = {}
    for lang, (lo, hi) in SCRIPT.items():
        tot = native = 0
        for r in rows:
            if r["language"] != lang:
                continue
            for t in (r.get("transcript") or {}).get("reasoning") or []:
                for ch in t or "":
                    if ch.isalpha():
                        tot += 1
                        native += lo <= ord(ch) <= hi
        out[lang] = round(native / tot, 4) if tot else None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--out")
    a = ap.parse_args()
    rows = load_first_attempts(a.logs)
    res = {"episodes": len(rows), "domains": sorted({r["domain"] for r in rows}),
           "unit": "first attempt per episode; loop (reply hit max_tokens) counted as failure"}

    succ = lambda r: episode_outcome(r) == "success"
    rq1 = {}
    rq1["success_group_format"] = {f"{g}|{f}": rate(sum(succ(r) for r in rows if GROUPS[r["language"]] == g and r["format"] == f),
                                                     sum(1 for r in rows if GROUPS[r["language"]] == g and r["format"] == f))
                                   for g in GROUP_ORDER for f in FORMATS}
    rq1["success_language_format"] = {f"{l}|{f}": rate(sum(succ(r) for r in rows if r["language"] == l and r["format"] == f),
                                                        sum(1 for r in rows if r["language"] == l and r["format"] == f))
                                      for l in LANGS for f in FORMATS + ("all",) if True} if False else {}
    for l in LANGS:
        for f in FORMATS + ("all",):
            sel = [r for r in rows if r["language"] == l and (f == "all" or r["format"] == f)]
            rq1["success_language_format"][f"{l}|{f}"] = rate(sum(succ(r) for r in sel), len(sel))
    rq1["success_domain_group_format"] = {}
    for d in res["domains"]:
        for g in GROUP_ORDER:
            for f in FORMATS:
                sel = [r for r in rows if r["domain"] == d and GROUPS[r["language"]] == g and r["format"] == f]
                rq1["success_domain_group_format"][f"{d}|{g}|{f}"] = rate(sum(succ(r) for r in sel), len(sel))
    rq1["outcomes_group_format"] = outcome_table(rows, lambda r: (GROUPS[r["language"]], r["format"]))
    rq1["outcomes_language"] = outcome_table(rows, lambda r: r["language"])
    rq1["logistic"] = logistic(rows)

    gap = {}
    for f in FORMATS:
        en = [r for r in rows if r["language"] == "en" and r["format"] == f]
        for g in ("non_native", "code_mixed"):
            ot = [r for r in rows if GROUPS[r["language"]] == g and r["format"] == f]
            gap[f"{g}|{f}"] = round(sum(map(succ, en)) / len(en) - sum(map(succ, ot)) / len(ot), 4)
    rq1["gap_vs_english"] = gap

    anc = defaultdict(lambda: [0, 0])
    for r in rows:
        if r.get("_truncated") or not r.get("completed"):
            continue
        for k, ok in r["constraint_ok"].items():
            if r["constraint_anchor"][k]:
                c = anc[(GROUPS[r["language"]], r["format"])]
                c[0] += ok
                c[1] += 1
    rq1["anchor_survival_completed"] = {f"{g}|{f}": rate(*anc[(g, f)]) for g in GROUP_ORDER for f in FORMATS}

    seeds = defaultdict(list)
    for r in rows:
        seeds[(r["template_id"], r["language"])].append(succ(r))
    p3 = defaultdict(lambda: [0, 0])
    for (t, l), v in seeds.items():
        if len(v) == 3:
            p3[(GROUPS[l], t.rsplit("_", 1)[1])][0] += all(v)
            p3[(GROUPS[l], t.rsplit("_", 1)[1])][1] += 1
    rq1["pass_hat_3"] = {f"{g}|{f}": rate(*p3[(g, f)]) for g in GROUP_ORDER for f in FORMATS}

    cost = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r.get("_truncated"):
            continue
        u = (r.get("transcript") or {}).get("usage") or {}
        key = f"{r['language']}|{r['format']}"
        cost[key]["completion_tokens"].append(u.get("completion_tokens", 0))
        cost[key]["extra_steps"].append(r.get("extra_steps", 0))
    rq1["cost_finished"] = {k: {m: round(sum(v) / len(v), 2) for m, v in d.items()} for k, d in sorted(cost.items())}
    rq1["reasoning_script_share"] = reasoning_script_share(rows)
    res["rq1"] = rq1

    rq2 = {}
    sub = defaultdict(Counter)
    first_pos = defaultdict(list)
    cases = []
    for r in rows:
        o = episode_outcome(r)
        g = GROUPS[r["language"]]
        if o == "loop":
            sub[g]["loop"] += 1
            if r.get("tool_turns_before_error") is not None:
                first_pos[(g, "loop")].append(r["tool_turns_before_error"] / r["horizon"])
            continue
        if o == "success":
            continue
        failed = [n for n, ok in r["constraint_ok"].items() if not ok]
        first = min(failed, key=lambda n: (r["constraint_commit_step"].get(n) is None, r["constraint_commit_step"].get(n) or 0))
        lab = label(r, first)
        sub[g][lab] += 1
        st = r["constraint_commit_step"].get(first)
        if st:
            first_pos[(g, "wrong_value")].append(st / r["horizon"])
        cases.append({"episode": r["episode_key"], "domain": r["domain"], "format": r["format"], "language": r["language"],
                      "first_failed": first, "class": r["constraint_class"][first], "label": lab,
                      "expected": r["constraint_expected"][first], "got": r["constraint_got"][first],
                      "decoy_hit": r["constraint_decoy_hit"][first], "all_failed": failed})
    rq2["first_failure_label_by_group"] = {g: dict(sub[g]) for g in GROUP_ORDER}
    rq2["relative_position_mean"] = {f"{g}|{k}": round(sum(v) / len(v), 3) for (g, k), v in sorted(first_pos.items())}

    cls = defaultdict(lambda: [0, 0])
    for r in rows:
        if r.get("_truncated"):
            continue
        for k, ok in r["constraint_ok"].items():
            for key in ((GROUPS[r["language"]], r["constraint_class"][k]), ("all", r["constraint_class"][k])):
                cls[key][0] += not ok
                cls[key][1] += 1
    rq2["constraint_failure_by_class"] = {f"{g}|{c}": rate(*v) for (g, c), v in sorted(cls.items())}
    rq2["cases"] = cases
    rq2["decoy_hits_in_cases"] = sum(c["decoy_hit"] for c in cases)

    val = defaultdict(lambda: [0, 0])
    for r in rows:
        if r.get("_truncated"):
            continue
        val[r["language"]][0] += r.get("validation_errors", 0)
        val[r["language"]][1] += r.get("num_steps_taken", 0)
    rq2["tool_call_error_rate_per_call"] = {l: rate(*val[l]) for l in LANGS}

    lng = [r for r in rows if r["format"] == "long" and episode_outcome(r) != "loop"]
    en_w = sum(1 for r in lng if r["language"] == "en" and episode_outcome(r) == "execution")
    en_n = sum(1 for r in lng if r["language"] == "en")
    ot_w = sum(1 for r in lng if r["language"] != "en" and episode_outcome(r) == "execution")
    ot_n = sum(1 for r in lng if r["language"] != "en")
    rq2["long_wrong_value_en_vs_other"] = {"en": rate(en_w, en_n), "other": rate(ot_w, ot_n),
                                           "fisher_p": round(fisher_two_sided(en_w, en_n, ot_w, ot_n), 4),
                                           "note": "exploratory: pooled across domains after the data were seen"}
    lp = [r for r in rows if r["format"] == "long"]
    en_l = sum(1 for r in lp if r["language"] == "en" and episode_outcome(r) == "loop")
    ot_l = sum(1 for r in lp if r["language"] != "en" and episode_outcome(r) == "loop")
    en_ln = sum(1 for r in lp if r["language"] == "en")
    ot_ln = sum(1 for r in lp if r["language"] != "en")
    rq2["long_loop_en_vs_other"] = {"en": rate(en_l, en_ln), "other": rate(ot_l, ot_ln),
                                    "fisher_p": round(fisher_two_sided(en_l, en_ln, ot_l, ot_ln), 4)}
    res["rq2"] = rq2

    text = json.dumps(res, indent=1, ensure_ascii=True)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
