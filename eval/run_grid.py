"""
Single CLI entrypoint, used identically locally and in Colab (Appendix D,
README). Reads a YAML config, runs each configured cell, verifies it
against gold, appends one JSON line per run to runs/<run_name>.jsonl, and
prints a summary.

Usage:
    python -m eval.run_grid --config configs/smoke_test.yaml
"""

import argparse
import json
from pathlib import Path

import yaml

from agent.policies.mock_policy import MockPolicy
from agent.react_loop import run_episode
from env.inject import FailureInjector
from eval.metrics import summarize
from eval.verifier import verify

REPO_ROOT = Path(__file__).resolve().parent.parent


def build_policy(run_cfg: dict, gold: dict):
    policy_type = run_cfg["policy"]
    if policy_type == "mock":
        return MockPolicy(gold["gold_steps"], mode=run_cfg.get("mock_mode", "solve"))
    if policy_type == "api":
        from agent.policies.api_policy import ApiPolicy  # noqa: F401  (stub, will raise)
        raise NotImplementedError("api policy is a stub -- see agent/policies/api_policy.py")
    if policy_type == "local":
        from agent.policies.local_policy import LocalPolicy  # noqa: F401  (stub, will raise)
        raise NotImplementedError("local policy is a stub -- see agent/policies/local_policy.py")
    raise ValueError(f"unknown policy type: {policy_type}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    config_path = Path(args.config)
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    with open(REPO_ROOT / cfg["gold_file"], "r", encoding="utf-8") as f:
        gold = json.load(f)

    runs_dir = REPO_ROOT / "runs"
    runs_dir.mkdir(exist_ok=True)
    log_path = runs_dir / f"{cfg['run_name']}.jsonl"

    records = []
    with open(log_path, "w", encoding="utf-8") as log_file:
        for i, run_cfg in enumerate(cfg["runs"]):
            policy = build_policy(run_cfg, gold)
            inject_cfg = run_cfg.get("inject")
            injector = (
                FailureInjector(
                    inject_at_step=inject_cfg["at_step"],
                    error_type=inject_cfg["error_type"],
                    message_language=inject_cfg.get("message_language", "en"),
                    flight_id=inject_cfg.get("flight_id"),
                )
                if inject_cfg
                else None
            )
            traj = run_episode(
                task_id=gold["task_id"],
                policy=policy,
                interface_mode=cfg.get("interface_mode", "strict"),
                max_steps=cfg.get("max_steps", 20),
                injector=injector,
            )
            record = verify(traj, gold)
            record["run_index"] = i
            record["policy"] = run_cfg["policy"]
            record["mock_mode"] = run_cfg.get("mock_mode")
            record["seed"] = run_cfg.get("seed")
            records.append(record)
            log_file.write(json.dumps(record) + "\n")

    print(f"Wrote {len(records)} run(s) to {log_path}")
    for r in records:
        print(f"  [{r['mock_mode'] or r['policy']}] success={r['success']} "
              f"constraints_survived={r['constraints_survived']} "
              f"fact_displacements={r['fact_displacements']} "
              f"injected={r['injected_error'] is not None} recovered={r['recovered']}")
    print("Summary:", summarize(records))


if __name__ == "__main__":
    main()
