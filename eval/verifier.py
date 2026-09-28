"""
Deterministic verifier (Sections 8.8 and 9). Every check is a plain
comparison against the gold file and the flight table; nothing here calls
a model.

`success` means the booked flight is the correct answer given the state of
the episode: the cheapest flight that satisfies every constraint among the
flights still bookable. Without injection that is the gold flight. With a
not_found injection it is the best remaining flight, which is what makes
`recovered` a measure of correct recovery rather than of booking anything.
"""

from env.data.flights import FLIGHTS

_GROUNDED_KEYS = ("flight_id", "hold_token", "fare_class", "passenger_id")


def _flatten(value, out: set):
    if isinstance(value, dict):
        for v in value.values():
            _flatten(v, out)
    elif isinstance(value, list):
        for v in value:
            _flatten(v, out)
    else:
        out.add(str(value))


_OBJECTIVES = {
    "min_price": lambda fs: min(fs, key=lambda f: f["price"]),
    "latest_departure": lambda fs: max(fs, key=lambda f: f["depart_time"]),
}


def optimal_flight(gold: dict, sold_out: set, drop: str | None = None):
    """Correct answer given the episode state. `drop` names one constraint
    to ignore, used to check that every constraint changes the answer."""
    c, e = gold["constraints"], gold["entities"]
    candidates = [
        f for f in FLIGHTS
        if f["origin"] == e["origin"] and f["destination"] == e["destination"]
        and f["date"] == c["date"] and f["seats"] > 0 and f["flight_id"] not in sold_out
        and (drop == "depart_before" or f["depart_time"] < c["depart_before"])
        and (drop == "max_price" or f["price"] <= c["max_price"])
    ]
    if not candidates:
        return None
    if drop == "objective":
        others = [f for f in candidates if f["flight_id"] != optimal_flight(gold, sold_out)]
        return others[0]["flight_id"] if others else None
    return _OBJECTIVES[c["objective"]](candidates)["flight_id"]


def verify(traj, gold: dict, sold_out: set) -> dict:
    c, e = gold["constraints"], gold["entities"]
    booked_id = traj.terminal_state.get("booking.flight_id")
    optimal_id = optimal_flight(gold, sold_out)

    survival = None
    if booked_id is not None:
        f = next(x for x in FLIGHTS if x["flight_id"] == booked_id)
        survival = {
            "route": f["origin"] == e["origin"] and f["destination"] == e["destination"],
            "date": f["date"] == c["date"],
            "depart_before": f["depart_time"] < c["depart_before"],
            "max_price": f["price"] <= c["max_price"],
            "objective": booked_id == optimal_id,
        }

    seen = set()
    fact_displacements = 0
    for step in traj.steps:
        for key in _GROUNDED_KEYS:
            if key in step["args"] and str(step["args"][key]) not in seen:
                fact_displacements += 1
        if "result" in step:
            _flatten(step["result"], seen)

    success = booked_id is not None and booked_id == optimal_id
    return {
        "success": success,
        "matches_gold_terminal": traj.terminal_state == gold["terminal_state"],
        "booked_flight": booked_id,
        "constraint_survival": survival,
        "all_constraints_survived": None if survival is None else all(survival.values()),
        "fact_displacements": fact_displacements,
        "first_error_step": traj.first_error_step,
        "num_steps_taken": len(traj.steps),
        "extra_steps": len(traj.steps) - len(gold["gold_steps"]),
        "injected": traj.injected_error is not None,
        "injected_at_step": traj.injected_at_step,
        "recovered": (success if traj.injected_error is not None else None),
    }
