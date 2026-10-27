"""
Checks an Experiment 2 mock run: the gold chain succeeds on every instance
and every scripted fault fails exactly the constraints it is meant to fail,
with each failed constraint attributed to its own stage.

    python -m eval.exp2_smoke runs/exp2_smoke_food.jsonl
"""

import json
import sys
from pathlib import Path

from env.exp2.registry import DOMAINS

ROOT = Path(__file__).resolve().parent.parent


def check(log_path):
    bad, n = [], 0
    for line in Path(log_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        n += 1
        failed = {k for k, v in (r.get("constraint_ok") or {}).items() if not v}
        if r["cell"] == "solve":
            if not r.get("success") or failed:
                bad.append((r["episode_key"], "gold failed", sorted(failed)))
            continue
        inst = json.loads((ROOT / "tasks" / "exp2" / f"{r['template_id']}.json").read_text(encoding="utf-8"))
        _, expect = DOMAINS[inst["domain"]].faulty_plan(inst["world"], inst["stages"], r["cell"])
        if failed != expect:
            bad.append((r["episode_key"], f"expected {sorted(expect)}", sorted(failed)))
        if r.get("success"):
            bad.append((r["episode_key"], "fault scored as success", []))
    return n, bad


def main():
    total = 0
    for path in sys.argv[1:]:
        n, bad = check(path)
        total += len(bad)
        print(f"{path}: {n} episodes, {len(bad)} problems")
        for b in bad[:20]:
            print("  ", *b)
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
