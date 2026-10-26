"""
Re-scores a long-horizon log without a GPU: replays each episode's tool
calls through fresh, deterministic tools to rebuild the end state, then runs
the current verifier on it. Used when a verifier fix must apply to episodes
already run (it changes the scoring, never the agent's actions).

    python -m eval.rescore_long runs/rq1_long_qwen36_27b_fp8.jsonl runs/rq1_long_qwen36_27b_fp8.rescored.jsonl
"""

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from env.long.registry import DOMAINS
from env.tools.travel_tools import ToolError

ROOT = Path(__file__).resolve().parent.parent


def rescore(rec: dict) -> dict:
    if rec.get("infra_error") or rec.get("domain") not in DOMAINS:
        return rec
    inst = json.loads((ROOT / f"tasks/long/{rec['template_id']}.json").read_text(encoding="utf-8"))
    d = DOMAINS[rec["domain"]]
    tools = d["tools"](inst, rec["language"], rec.get("seam") or "S1")
    terminal = {}
    for s in rec["steps"]:
        try:
            out = tools.call(s["tool"], s["args"])
            if s["tool"] == tools.TERMINAL_TOOL:
                terminal = dict(out)
        except (ToolError, TypeError, AttributeError):
            pass
    traj = SimpleNamespace(steps=rec["steps"], terminal_state=terminal, first_error_step=rec.get("first_error_step"),
                           injected_error=None, injected_at_step=None)
    fresh = d["module"].verify(traj, inst, set(tools._sold_out), final_state=tools.snapshot())
    keep = {k: v for k, v in rec.items() if k not in fresh}
    return {**keep, **fresh, "rescored": True}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("out")
    args = ap.parse_args()
    rows = [json.loads(l) for l in open(args.log, encoding="utf-8") if l.strip()]
    with open(args.out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(rescore(r), ensure_ascii=False) + "\n")
    print(f"rescored {len(rows)} rows -> {args.out}")


if __name__ == "__main__":
    main()
