"""
Quick aggregation for eyeballing a run log. The real analysis
(mixed-effects model, survival analysis; Section 8.9) goes in eval/stats/.

Recovery rate follows Section 8.6: only injected episodes whose cell is
solved without injection count toward the denominator. The caller is
responsible for that conditioning once real policies exist; here every
injected episode is counted.
"""


def summarize(records: list[dict]) -> dict:
    n = len(records)
    if n == 0:
        return {"n": 0}
    clean = [r for r in records if not r["injected"]]
    injected = [r for r in records if r["injected"]]
    return {
        "n": n,
        "success_rate_clean": round(sum(r["success"] for r in clean) / len(clean), 3) if clean else None,
        "recovery_rate": round(sum(bool(r["recovered"]) for r in injected) / len(injected), 3) if injected else None,
    }
