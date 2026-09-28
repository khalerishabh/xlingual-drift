"""
Minimal aggregation over a run log. This is scaffolding for eyeballing the
smoke test -- the real mixed-effects / survival analysis (Section 8.9)
belongs in eval/stats/ and is Phase 5+ work, not implemented here.
"""


def summarize(records: list[dict]) -> dict:
    n = len(records)
    if n == 0:
        return {"n": 0}
    n_success = sum(1 for r in records if r["success"])
    n_recovered = sum(1 for r in records if r.get("recovered") is True)
    n_injected = sum(1 for r in records if r.get("injected_error") is not None)
    return {
        "n": n,
        "success_rate": n_success / n,
        "recovery_rate": (n_recovered / n_injected) if n_injected else None,
    }
