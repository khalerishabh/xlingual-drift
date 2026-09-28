"""
Single CLI entrypoint, used identically locally and in Colab. Runs every
template x horizon x language x cell x seed combination in a config,
verifies each episode against its gold file, and appends one JSON line per
episode to runs/<run_name>.jsonl (or --out).

    python -m eval.run_grid --config configs/smoke_test.yaml
    python -m eval.run_grid --config configs/capability_gate_v2.yaml --resume --workers 16

--resume skips episodes already in the log, so a disconnected Colab session
picks up where it stopped. Episodes whose endpoint failed are logged with
`infra_error` and no score, and are retried on the next --resume.
--workers runs episodes concurrently; vLLM batches the requests, so this is
the main speed-up on a single GPU. Each episode is still fully independent.
--serving points at the serving.json the notebook writes when it starts
vLLM. Every episode is stamped with it, and a log is never extended with
episodes from a different model, weights revision or vLLM version: a
backbone must be identical across every condition it is compared on.
"""

import argparse
import itertools
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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


FINGERPRINT_KEYS = ("model", "revision", "vllm_version")


class ServingMismatch(RuntimeError):
    pass


def check_cells_match_server(serving: dict, cfg: dict) -> None:
    pinned = cfg.get("serving", {}).get("model")
    if pinned and pinned != serving["model"]:
        raise ServingMismatch(f"config pins {pinned} but the server runs {serving['model']}")
    for cell in cfg["cells"]:
        if cell["policy"] == "openai_compat" and cell.get("model") != serving["model"]:
            raise ServingMismatch(f"cell {cell.get('name')} asks for {cell.get('model')}, server runs {serving['model']}")


def check_log_matches_server(log_path: Path, serving: dict | None) -> None:
    """Refuse to mix backbones in one log. GPU differences only produce a
    note: the same weights and kernels on another card of the same family
    do not change the backbone."""
    if not log_path.exists():
        return
    other_gpus = set()
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("policy") == "mock":
            continue
        prior = rec.get("serving")
        if prior is None and serving is None:
            continue
        if prior is None or serving is None:
            raise ServingMismatch("log mixes episodes with and without a serving fingerprint")
        diff = {k: (prior.get(k), serving.get(k)) for k in FINGERPRINT_KEYS if prior.get(k) != serving.get(k)}
        if diff:
            raise ServingMismatch(f"{log_path.name} was produced under a different backbone setup: {diff}. "
                                  f"Use a new --out log or restore the original setup.")
        if prior.get("gpu_name") != serving.get("gpu_name"):
            other_gpus.add(prior.get("gpu_name"))
    if other_gpus:
        print(f"note: log also has episodes from {sorted(other_gpus)}; this session runs {serving.get('gpu_name')}")


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


def run_one(cfg: dict, serving, template: dict, horizon: int, language: str, name: str, cell: dict, seed) -> dict:
    gold = load_json(f"tasks/gold/{template['template_id']}_h{horizon}.json")
    policy = build_policy(cell, gold, seed)
    inject = cell.get("inject") or {}
    interface_mode = cfg.get("interface_mode", "strict")
    base = {
        "episode_key": f"{template['template_id']}|h{horizon}|{language}|{name}|s{seed}",
        "run_name": cfg["run_name"], "task_id": gold["task_id"], "template_id": template["template_id"],
        "horizon": horizon, "language": language, "interface_mode": interface_mode, "cell": name,
        "policy": cell["policy"], "model": cell.get("model"), "extra_body": cell.get("extra_body"),
        "seed": seed, "error_type": inject.get("error_type"), "inject_at_tool": inject.get("at_tool"),
        "message_language": inject.get("message_language"),
        "serving": serving if cell["policy"] != "mock" else None,
    }
    start = time.perf_counter()
    try:
        traj = run_episode(
            task_id=gold["task_id"], horizon=horizon, request=template["requests"][language],
            policy=policy, interface_mode=interface_mode, max_steps=cfg.get("max_steps", 24),
            injector=build_injector(cell), context={"session_date": template["session_date"]},
        )
    except InfraError as e:
        return {**base, "infra_error": str(e), "latency_s": round(time.perf_counter() - start, 3)}
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
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--out", help="log path; defaults to runs/<run_name>.jsonl")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--serving", help="serving.json written by the notebook when it started vLLM")
    args = parser.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    serving = json.loads(Path(args.serving).read_text(encoding="utf-8")) if args.serving else None
    if serving is None and any(c["policy"] == "openai_compat" for c in cfg["cells"]):
        print("warning: no --serving given; episodes will carry no backbone fingerprint")

    template_paths = cfg.get("templates") or [cfg["template"]]
    templates = [load_json(p) for p in template_paths]
    log_path = Path(args.out) if args.out else REPO_ROOT / "runs" / f"{cfg['run_name']}.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if serving is not None:
        check_cells_match_server(serving, cfg)
    if args.resume:
        check_log_matches_server(log_path, serving)
    done = completed_keys(log_path) if args.resume else set()

    cells = []
    for i, cell in enumerate(cfg["cells"]):
        name = cell.get("name") or cell.get("mock_mode") or f"cell{i}"
        for seed in cell.get("seeds", [cell.get("seed")]):
            cells.append((name, cell, seed))

    jobs = [
        (t, h, lang, name, cell, seed)
        for t, h, lang, (name, cell, seed) in itertools.product(templates, cfg["horizons"], cfg["languages"], cells)
        if f"{t['template_id']}|h{h}|{lang}|{name}|s{seed}" not in done
    ]
    skipped = len(templates) * len(cfg["horizons"]) * len(cfg["languages"]) * len(cells) - len(jobs)

    records, lock = [], threading.Lock()
    with open(log_path, "a" if args.resume else "w", encoding="utf-8") as log:
        def write(record):
            with lock:
                records.append(record)
                log.write(json.dumps(record, ensure_ascii=False) + "\n")
                log.flush()
                _print_line(record, len(records), len(jobs))

        if args.workers <= 1:
            for job in jobs:
                write(run_one(cfg, serving, *job))
        else:
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                futures = [pool.submit(run_one, cfg, serving, *job) for job in jobs]
                for fut in as_completed(futures):
                    write(fut.result())

    print(f"Wrote {len(records)} episode(s) to {log_path}" + (f", skipped {skipped} already done" if skipped else ""))
    print("Summary:", summarize(records))


def _print_line(r: dict, i: int, n: int):
    head = f"  [{i}/{n}] {r['template_id']} h{r['horizon']:<2} {r['language']:<8} {r['cell']:<22} s{r['seed']}"
    if r.get("infra_error"):
        print(f"{head} INFRA_ERROR {r['infra_error'][:80]}")
        return
    inj = f" inject={r['error_type']}/{r['message_language']}" if r["error_type"] else ""
    print(f"{head}{inj} success={r['success']!s:<5} flight={r['booked_flight']} "
          f"seat={r['booked_seat_type']} meal={r['booked_meal']} steps={r['num_steps_taken']} recovered={r['recovered']}")


if __name__ == "__main__":
    main()
