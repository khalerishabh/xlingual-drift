"""
Stage attribution for Experiment 2 (docs/EXP2_SPEC.md, evaluation framework
"Stage-Attributed State Drift"). Every scored constraint in every episode
gets one label:

  ok             committed with the exact expected value
  tool_calling   never committed because the calls for it kept failing
                 (validation / not-found errors), or the episode ended on a
                 tool error
  planning       the episode was committed but this constraint was never
                 acted on at all (inferred from behaviour: no committed value)
  E1A            state loss, Tier A: the agent had used the exact expected
                 value in an earlier successful call, then committed another
  E1B            state loss, Tier B: the expected value appears in its
                 reasoning before the commit, but never in an earlier call
  E2             error-triggered substitution: a tool error in the three
                 steps before the commit, and a different value committed
  E3             decision error with the constraint in view: none of the
                 above (the right value was never held)
  termination    the episode ended (step limit, or a reply without the
                 final call) before this constraint was committed

"Held" (E1) is judged on exact values only, and only for distinctive
values (ids, numbers with four or more digits, codes): a generic word like
"mild" or "email" appearing in reasoning is not evidence of held state.

    python -m eval.stages runs/exp2_food_qwen36_27b_fp8.jsonl [more logs]
"""

import argparse
import json
import re
from collections import Counter, defaultdict

from eval.drift import wilson
from eval.metrics import latest_scored

GROUPS = {"en": "native", "hi": "non_native", "ta": "non_native", "hinglish": "code_mixed", "tanglish": "code_mixed"}
LABELS = ("ok", "tool_calling", "planning", "E1A", "E1B", "E2", "E3", "termination")
STAGE_OF = {"tool_calling": "tool_calling", "planning": "planning", "E1A": "execution", "E1B": "execution",
            "E2": "execution", "E3": "execution", "termination": "termination"}
_DISTINCT = re.compile(r"[A-Za-z]+-[A-Za-z0-9-]+|\d{4,}|[a-z0-9.]+@[a-z]+")


def distinctive(value):
    return bool(value) and bool(_DISTINCT.search(str(value)))


def _texts(value):
    v = str(value)
    out = {v}
    if re.fullmatch(r"\d+(\.0)?", v):
        n = int(float(v))
        out |= {str(n), f"{n:,}"}
    return out


def _in(blob, value):
    return any(t in blob for t in _texts(value))


def label(rec, name):
    if rec["constraint_ok"][name]:
        return "ok"
    steps = rec.get("steps") or []
    got, want = rec["constraint_got"].get(name), rec["constraint_expected"].get(name)
    commit = rec["constraint_commit_step"].get(name)
    if not rec.get("completed") and (got is None or rec["constraint_anchor"].get(name)):
        if steps and "error" in steps[-1]:
            return "tool_calling"
        return "termination"
    if got is None or got in ("None", "[]", "{}"):
        tried = [s for s in steps if "error" in s and want is not None and _in(json.dumps(s.get("args")), want)]
        return "tool_calling" if tried else "planning"
    commit = commit or len(steps)
    if any("error" in s for s in steps[max(0, commit - 4):commit - 1]):
        return "E2"
    if distinctive(want):
        before = steps[:commit - 1]
        if any("result" in s and _in(json.dumps(s.get("args"), ensure_ascii=False), want) for s in before):
            return "E1A"
        reasoning = ((rec.get("transcript") or {}).get("reasoning") or [])[:commit]
        if any(r and _in(r, want) for r in reasoning):
            return "E1B"
    return "E3"


def rows(records):
    out = []
    for r in records:
        for name in r.get("constraint_ok") or {}:
            lab = label(r, name)
            out.append({"episode": r["episode_key"], "domain": r["domain"], "format": r["format"],
                        "language": r["language"], "group": GROUPS.get(r["language"], r["language"]),
                        "seed": r["seed"], "constraint": name, "class": r["constraint_class"][name],
                        "stage_of_task": r["constraint_stage"][name], "anchor": r["constraint_anchor"][name],
                        "label": lab, "stage": "ok" if lab == "ok" else STAGE_OF[lab],
                        "decoy_hit": bool(r["constraint_decoy_hit"].get(name))})
    return out


def load(paths):
    recs = []
    for p in paths:
        recs += [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
    return [r for r in latest_scored(recs) if r.get("experiment") == "exp2" and r.get("policy") != "mock"]


def table(rs, key, col="stage"):
    by = defaultdict(Counter)
    for x in rs:
        by[x[key]][x[col]] += 1
    return by


def report(records):
    rs = rows(records)
    lines = [f"{len(records)} episodes, {len(rs)} constraints"]
    for key in ("group", "language", "format", "domain", "class"):
        lines.append(f"\nfailure stage by {key} (rate per constraint, 95% Wilson CI)")
        for k, c in sorted(table(rs, key).items()):
            n = sum(c.values())
            cells = []
            for st in ("tool_calling", "planning", "execution", "termination"):
                lo, hi = wilson(c[st], n)
                cells.append(f"{st}={c[st] / n:.3f} [{lo:.3f},{hi:.3f}]")
            lines.append(f"  {k:<12} n={n:<5} " + "  ".join(cells))
    lines.append("\nexecution sub-labels by group")
    for k, c in sorted(table(rs, "group", "label").items()):
        lines.append(f"  {k:<12} " + "  ".join(f"{l}={c[l]}" for l in LABELS if l != "ok"))
    ex = [x for x in rs if x["stage"] == "execution"]
    lines.append(f"\ndecoy hits among execution failures: {sum(x['decoy_hit'] for x in ex)}/{len(ex)}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--rows", help="write one JSON line per constraint here")
    a = ap.parse_args()
    recs = load(a.logs)
    print(report(recs))
    if a.rows:
        with open(a.rows, "w", encoding="utf-8") as f:
            for x in rows(recs):
                f.write(json.dumps(x) + "\n")


if __name__ == "__main__":
    main()
