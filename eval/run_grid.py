"""
Single CLI entrypoint, used identically locally and in Colab. Runs every
horizon x language x cell x seed combination in a config, verifies each
episode against its gold file, and appends one JSON line per episode to
runs/<run_name>.jsonl (or --out).

    python -m eval.run_grid --config configs/smoke_test.yaml
    python -m eval.run_grid --config configs/capability_gate.yaml --resume

--resume skips episodes already in the log, so a disconnected Colab session
picks up where it stopped. Episodes whose endpoint failed are logged with
`infra_error` and no score, and are retried on the next --resume.
"""

import argparse
import itertools
import json
import time
from pathlib import Path

import yaml

from agent.policies.mock_policy import MockPolicy
from agent.policies.openai_compat_policy import InfraError, OpenAICompatPolicy
from agent.react_loop import run_episode
from env.inject import FailureInjector
from eval.metrics import summarize
from eval.verifier import verify

REPO_ROOT = Path(__file__).resolve().parent.parent
_POLICY_KEYS = ("model", "base_url", "api_key_env", "temperature", "max_tokens", "extra_body",
                "prompt_version", "max_retries")


def load_json(rel_path: str) -> dict:
    return json.loads((REPO_ROOT / rel_path).read_text(encoding="utf-8"))


def build_policy(cell: dict, gold: dict, seed):
    kind = cell["policy"]
    if kind == "mock":
        return MockPolicy(gold, mode=cell.get("mock_mode", "solve"))
    if kind == "openai_compat":
        return OpenAICompatPolicy(seed=seed, **{k: cell[k] for k in _POLICY_KEYS if k in cell})
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


def episode_key(horizon, language, cell_name, seed) -> str:
    return f"h{horizon}|{language}|{cell_name}|s{seed}"


def completed_keys(log_path: Path) -> set:
    if not log_path.exists():
        return set()
    done = set()
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            if not rec.get("infra_error"):
                done.add(rec["episode_key"])
    return done


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--out", help="log path; defaults to runs/<run_name>.jsonl")
    args = parser.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))

    template = load_json(cfg["template"])
    interface_mode = cfg.get("interface_mode", "strict")
    log_path = Path(args.out) if args.out else REPO_ROOT / "runs" / f"{cfg['run_name']}.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    done = completed_keys(log_path) if args.resume else set()
    context = {"session_date": template["session_date"]}

    cells = []
    for i, cell in enumerate(cfg["cells"]):
        name = cell.get("name") or cell.get("mock_mode") or f"cell{i}"
        for seed in cell.get("seeds", [cell.get("seed")]):
            cells.append((name, cell, seed))

    records, skipped = [], 0
    with open(log_path, "a" if args.resume else "w", encoding="utf-8") as log:
        for horizon, language, (name, cell, seed) in itertools.product(cfg["horizons"], cfg["languages"], cells):
            key = episode_key(horizon, language, name, seed)
            if key in done:
                skipped += 1
                continue
            gold = load_json(f"tasks/gold/{template['template_id']}_h{horizon}.json")
            policy = build_policy(cell, gold, seed)
            inject = cell.get("inject") or {}
            base = {
                "episode_key": key, "run_name": cfg["run_name"], "task_id": gold["task_id"],
                "template_id": template["template_id"], "horizon": horizon, "language": language,
                "interface_mode": interface_mode, "cell": name, "policy": cell["policy"],
                "model": cell.get("model"), "extra_body": cell.get("extra_body"), "seed": seed,
                "error_type": inject.get("error_type"), "inject_at_tool": inject.get("at_tool"),
                "message_language": inject.get("message_language"),
            }
            start = time.perf_counter()
            try:
                traj = run_episode(
                    task_id=gold["task_id"], horizon=horizon, request=template["requests"][language],
                    policy=policy, interface_mode=interface_mode, max_steps=cfg.get("max_steps", 20),
                    injector=build_injector(cell), context=context,
                )
            except InfraError as e:
                record = {**base, "infra_error": str(e), "latency_s": round(time.perf_counter() - start, 3)}
            else:
                record = {
                    **base,
                    **verify(traj, gold, traj.sold_out),
                    "hit_step_limit": traj.hit_step_limit,
                    "final_text": traj.final_text,
                    "latency_s": round(time.perf_counter() - start, 3),
                    "steps": traj.steps,
                }
                if hasattr(policy, "transcript"):
                    record["transcript"] = policy.transcript()
            records.append(record)
            log.write(json.dumps(record, ensure_ascii=False) + "\n")
            log.flush()
            _print_line(record)

    print(f"Wrote {len(records)} episode(s) to {log_path}" + (f", skipped {skipped} already done" if skipped else ""))
    print("Summary:", summarize(records))


def _print_line(r: dict):
    head = f"  h{r['horizon']} {r['language']:<8} {r['cell']:<24} s{r['seed']}"
    if r.get("infra_error"):
        print(f"{head} INFRA_ERROR {r['infra_error'][:80]}")
        return
    inj = f" inject={r['error_type']}/{r['message_language']}" if r["error_type"] else ""
    print(f"{head}{inj:<24} success={r['success']!s:<5} survived={r['all_constraints_survived']!s:<5} "
          f"booked={r['booked_flight']} steps={r['num_steps_taken']} recovered={r['recovered']}")


if __name__ == "__main__":
    main()
