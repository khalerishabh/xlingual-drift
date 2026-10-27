"""
Outcome tables for Experiment 2: success, state success (everything but
the anchors) and anchor success by domain x format x language group, with
95% Wilson intervals, and the early-stop check for a domain notebook.

    python -m eval.exp2_summary runs/exp2_*.jsonl
    python -m eval.exp2_summary runs/exp2_food_qwen36_27b_fp8.jsonl --early-stop

Early-stop rule (approved 27 Oct 2026): once English seed 1 has run
on all 15 instances of a domain (run_grid schedules those first), if their
success rate is below 0.3 that domain stops.
"""

import argparse
from collections import defaultdict

from eval.drift import wilson
from eval.stages import GROUPS, load

EARLY_N, EARLY_MIN = 15, 0.3


def anchors_ok(r):
    return r.get("completed") and all(v for k, v in r["constraint_ok"].items() if r["constraint_anchor"][k])


def cell(rs, f):
    k, n = sum(1 for r in rs if f(r)), len(rs)
    lo, hi = wilson(k, n)
    return f"{k}/{n}={k / n:.2f} [{lo:.2f},{hi:.2f}]" if n else "-"


def report(records):
    by = defaultdict(list)
    for r in records:
        by[(r["domain"], r["format"], GROUPS.get(r["language"], r["language"]))].append(r)
        by[("ALL", r["format"], GROUPS.get(r["language"], r["language"]))].append(r)
    lines = [f"{'domain':<10}{'format':<8}{'group':<12}{'success':<26}{'state':<26}{'anchors':<26}"]
    for key in sorted(by):
        rs = by[key]
        lines.append(f"{key[0]:<10}{key[1]:<8}{key[2]:<12}{cell(rs, lambda r: r['success']):<26}"
                     f"{cell(rs, lambda r: r['success_state']):<26}{cell(rs, anchors_ok):<26}")
    return "\n".join(lines)


def early_stop(records):
    en = [r for r in records if r["language"] == "en" and r["seed"] == 1]
    if len(en) < EARLY_N:
        return f"{len(en)}/{EARLY_N} English seed-1 episodes so far; the check runs when all are in"
    rate = sum(r["success"] for r in en) / len(en)
    verdict = "STOP this domain" if rate < EARLY_MIN else "continue"
    return f"English seed-1 success: {rate:.2f} over {len(en)} episodes -> {verdict}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--early-stop", action="store_true")
    a = ap.parse_args()
    recs = load(a.logs)
    print(early_stop(recs) if a.early_stop else report(recs))


if __name__ == "__main__":
    main()
