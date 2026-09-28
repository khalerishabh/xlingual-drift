"""
Single CLI entrypoint, used identically locally and in Colab. Runs every
combination of horizon x language x run cell in a config, verifies each
episode against its gold file, and writes one JSON line per episode
(Appendix E fields) to runs/<run_name>.jsonl.

    python -m eval.run_grid --config configs/smoke_test.yaml
"""

import argparse
import itertools
import json
import time
from pathlib import Path

import yaml

from agent.policies.mock_policy import MockPolicy
from agent.react_loop import run_episode
from env.inject import FailureInjector
from eval.metrics import summarize
from eval.verifier import verify

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_json(rel_path: str) -> dict:
    return json.loads((REPO_ROOT / rel_path).read_text(encoding="utf-8"))


def build_policy(cell: dict, gold: dict):
    kind = cell["policy"]
    if kind == "mock":
        return MockPolicy(gold, mode=cell.get("mock_mode", "solve"))
    if kind in ("api", "local"):
        raise NotImplementedError(f"{kind} policy is a stub; see agent/policies/{kind}_policy.py")
    raise ValueError(f"unknown policy type: {kind}")


def build_injector(cell: dict):
    spec = cell.get("inject")
    if not spec:
        return None
    return FailureInjector(
        error_type=spec["error_type"],
        message_language=spec.get("message_language", "en"),
        at_step=spec.get("at_step"),
        at_tool=spec.get("at_tool"),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))

    template = load_json(cfg["template"])
    interface_mode = cfg.get("interface_mode", "strict")
    runs_dir = REPO_ROOT / "runs"
    runs_dir.mkdir(exist_ok=True)
    log_path = runs_dir / f"{cfg['run_name']}.jsonl"

    records = []
    with open(log_path, "w", encoding="utf-8") as log:
        grid = itertools.product(cfg["horizons"], cfg["languages"], cfg["cells"])
        for horizon, language, cell in grid:
            gold = load_json(f"tasks/gold/{template['template_id']}_h{horizon}.json")
            injector = build_injector(cell)
            start = time.perf_counter()
            traj = run_episode(
                task_id=gold["task_id"],
                horizon=horizon,
                request=template["requests"][language],
                policy=build_policy(cell, gold),
                interface_mode=interface_mode,
                max_steps=cfg.get("max_steps", 20),
                injector=injector,
            )
            record = {
                "run_name": cfg["run_name"],
                "task_id": gold["task_id"],
                "template_id": template["template_id"],
                "horizon": horizon,
                "language": language,
                "interface_mode": interface_mode,
                "policy": cell["policy"],
                "mock_mode": cell.get("mock_mode"),
                "seed": cell.get("seed"),
                "error_type": (cell.get("inject") or {}).get("error_type"),
                "message_language": (cell.get("inject") or {}).get("message_language"),
                **verify(traj, gold, traj.sold_out),
                "latency_s": round(time.perf_counter() - start, 4),
                "steps": traj.steps,
            }
            records.append(record)
            log.write(json.dumps(record, ensure_ascii=True) + "\n")

    print(f"Wrote {len(records)} episode(s) to {log_path}")
    for r in records:
        label = r["mock_mode"] or r["policy"]
        inj = f" inject={r['error_type']}/{r['message_language']}" if r["error_type"] else ""
        print(f"  h{r['horizon']} {r['language']:<8} {label:<24}{inj:<24} success={r['success']!s:<5} "
              f"survived={r['all_constraints_survived']!s:<5} displacements={r['fact_displacements']} "
              f"steps={r['num_steps_taken']} recovered={r['recovered']}")
    print("Summary:", summarize(records))


if __name__ == "__main__":
    main()
