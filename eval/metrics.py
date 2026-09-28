"""
Quick aggregation for eyeballing a run log. The real analysis
(mixed-effects model, survival analysis; Section 8.9) goes in eval/stats/.

Episodes with an infra_error are excluded everywhere. Recovery rate is not
yet conditioned on the clean cell succeeding (Section 8.6); that happens
in the stats pipeline once real runs exist.
"""

from collections import defaultdict


def summarize(records: list[dict]) -> dict:
    scored = [r for r in records if not r.get("infra_error")]
    clean = [r for r in scored if not r["injected"]]
    injected = [r for r in scored if r["injected"]]
    return {
        "n": len(records),
        "infra_errors": len(records) - len(scored),
        "success_rate_clean": round(sum(r["success"] for r in clean) / len(clean), 3) if clean else None,
        "recovery_rate": round(sum(bool(r["recovered"]) for r in injected) / len(injected), 3) if injected else None,
    }


def success_table(records: list[dict]) -> dict:
    """Clean-episode success rate keyed by (cell, language, horizon)."""
    cells = defaultdict(list)
    for r in records:
        if not r.get("infra_error") and not r["injected"]:
            cells[(r["cell"], r["language"], r["horizon"])].append(r["success"])
    return {k: (sum(v) / len(v), len(v)) for k, v in sorted(cells.items())}
