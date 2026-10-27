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
import json
from collections import Counter, defaultdict

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


def first_attempts(paths):
    """First logged attempt per episode, in log order, including episodes
    that ended on a truncated reply (unscored rows). Other infra errors are
    left out: they say nothing about the agent."""
    first = {}
    for p in paths:
        for line in open(p, encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                if r.get("experiment") != "exp2" or r.get("policy") == "mock":
                    continue
                trunc = str(r.get("infra_error", "")).startswith("truncated")
                if r.get("infra_error") and not trunc:
                    continue
                first.setdefault(r["episode_key"], dict(r, _truncated=trunc))
    return list(first.values())


def strict_report(rows):
    """Truncation counted as a failure: the reply ran past max_tokens
    (16384) without a tool call, nearly always a reasoning loop."""
    by = defaultdict(Counter)
    for r in rows:
        for key in ((r["language"], r["format"]), (r["language"], "all"), (GROUPS.get(r["language"]), "all")):
            c = by[key]
            c["n"] += 1
            c["trunc"] += r["_truncated"]
            c["ok"] += bool(not r["_truncated"] and r.get("success"))
    lines = [f"{'language':<12}{'format':<8}{'strict success':<28}{'truncated':<26}"]
    for key in sorted(by, key=lambda k: (str(k[0]), k[1])):
        c = by[key]
        lo, hi = wilson(c["ok"], c["n"])
        tlo, thi = wilson(c["trunc"], c["n"])
        lines.append(f"{str(key[0]):<12}{key[1]:<8}{c['ok']}/{c['n']}={c['ok'] / c['n']:.2f} [{lo:.2f},{hi:.2f}]".ljust(48)
                     + f"{c['trunc']}/{c['n']}={c['trunc'] / c['n']:.2f} [{tlo:.2f},{thi:.2f}]")
    return "\n".join(lines)


def early_stop(rows):
    en = [r for r in rows if r["language"] == "en" and r["seed"] == 1]
    if len(en) < EARLY_N:
        return f"{len(en)}/{EARLY_N} English seed-1 episodes so far; the check runs when all are in"
    rate = sum(bool(r.get("success")) and not r["_truncated"] for r in en) / len(en)
    verdict = "STOP this domain" if rate < EARLY_MIN else "continue"
    return f"English seed-1 success (truncation = failure): {rate:.2f} over {len(en)} episodes -> {verdict}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--early-stop", action="store_true")
    a = ap.parse_args()
    recs = load(a.logs)
    if a.early_stop:
        print(early_stop(first_attempts(a.logs)))
        return
    print(report(recs))
    print("\nFirst attempt per episode, truncation counted as failure")
    print(strict_report(first_attempts(a.logs)))


if __name__ == "__main__":
    main()
