"""
Re-scores an Experiment 2 log with the current verifier, without the model:
each episode's logged tool calls are replayed through a fresh copy of its
environment (deterministic), and the verifier runs on the rebuilt state.
Used when a verifier bug is fixed after a run. Rows that ended on an
infra error or a truncated reply are copied unchanged.

    python -m eval.rescore_exp2 runs/exp2_payment_qwen36_27b_fp8.jsonl runs/exp2_payment_qwen36_27b_fp8.rescored.jsonl

--waive domain:format:constraint drops a constraint from scoring (it is
kept in the row under waived_ok), for checks found invalid after a run.
"""

import argparse
import json

from agent.react_loop import Trajectory
from env.exp2.registry import DOMAINS
from env.tools.travel_tools import ToolError
from eval.run_grid import REPO_ROOT


def replay(inst, steps):
    tools = DOMAINS[inst["domain"]].Tools(inst, "en")
    traj = Trajectory(task_id=inst["template_id"], horizon=inst["horizon"])
    for st in steps:
        rec = dict(st)
        if "result" in st:
            try:
                rec["result"] = tools.call(st["tool"], st["args"])
            except (ToolError, TypeError) as e:
                raise AssertionError(f"{inst['template_id']}: logged success of {st['tool']} does not replay: {e}")
        traj.steps.append(rec)
    return traj, tools.snapshot()


def rescore(rec, waive):
    if rec.get("infra_error") or rec.get("experiment") != "exp2":
        return rec
    inst = json.loads((REPO_ROOT / "tasks" / "exp2" / f"{rec['template_id']}.json").read_text(encoding="utf-8"))
    traj, state = replay(inst, rec["steps"])
    traj.injected_error = None
    out = DOMAINS[inst["domain"]].verify(traj, inst, state)
    drop = {c for d, f, c in waive if d == inst["domain"] and f == inst["format"]}
    if drop:
        out["waived_ok"] = {c: out["constraint_ok"].pop(c) for c in drop if c in out["constraint_ok"]}
        out["success"] = out["completed"] and all(out["constraint_ok"].values())
        anchors = out["constraint_anchor"]
        out["success_state"] = all(v for k, v in out["constraint_ok"].items() if not anchors[k])
    keep = {k: rec[k] for k in ("episode_key", "run_name", "task_id", "template_id", "horizon", "language",
                                "interface_mode", "cell", "policy", "model", "extra_body", "domain", "seam",
                                "experiment", "format", "scenario", "seed", "error_type", "inject_at_tool",
                                "message_language", "serving", "hit_step_limit", "final_text", "latency_s",
                                "steps", "transcript") if k in rec}
    return {**keep, **out, "rescored": True}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--waive", action="append", default=[])
    a = ap.parse_args()
    waive = [tuple(w.split(":")) for w in a.waive]
    n, changed = 0, 0
    with open(a.dst, "w", encoding="utf-8") as f:
        for line in open(a.src, encoding="utf-8"):
            if not line.strip():
                continue
            rec = json.loads(line)
            new = rescore(rec, waive)
            n += 1
            changed += new.get("success") != rec.get("success")
            f.write(json.dumps(new, ensure_ascii=False) + "\n")
    print(f"{n} rows, success changed on {changed}")


if __name__ == "__main__":
    main()
