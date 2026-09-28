"""
Deterministic verifier (Sections 8.8 and 9). Every check is a plain
comparison against the gold file and the flight table; nothing here calls
a model.

`success` means the terminal booking is correct given the state of the
episode: the right flight among those still bookable (the gold flight
without injection, the best remaining one after a not_found injection),
with the requested seat type and meal.

Constraints come in two classes (Section 15.11):
  early  route, date, time window, budget, objective: applied when the
         flight is chosen.
  late   seat type, meal: committed only in the booking call, so they
         are carried for as many steps as the horizon adds.
For each constraint the verifier reports whether it survived to the
terminal state and the step at which the agent first acted on it, which
is what the constraint-distance analysis uses.
"""

from env.data.flights import FLIGHTS

_GROUNDED_KEYS = ("flight_id", "hold_token", "fare_class", "passenger_id",
                  "seat_id", "meal_code", "document_id", "payment_id")
_OBJECTIVES = {
    "min_price": lambda fs: min(fs, key=lambda f: f["price"]),
    "latest_departure": lambda fs: max(fs, key=lambda f: f["depart_time"]),
    "earliest_departure": lambda fs: min(fs, key=lambda f: f["depart_time"]),
}
EARLY_FILTERS = ("depart_after", "depart_before", "max_price")


def _flatten(value, out: set):
    if isinstance(value, dict):
        for v in value.values():
            _flatten(v, out)
    elif isinstance(value, list):
        for v in value:
            _flatten(v, out)
    else:
        out.add(str(value))


def _passes(f: dict, c: dict, drop: str | None) -> bool:
    if "depart_after" in c and drop != "depart_after" and not f["depart_time"] > c["depart_after"]:
        return False
    if "depart_before" in c and drop != "depart_before" and not f["depart_time"] < c["depart_before"]:
        return False
    if "max_price" in c and drop != "max_price" and not f["price"] <= c["max_price"]:
        return False
    return True


def optimal_flight(gold: dict, sold_out: set, drop: str | None = None):
    """Correct flight given the episode state. `drop` names one early
    constraint (or "objective") to ignore; used to derive decoys."""
    c, e = gold["constraints"], gold["entities"]
    candidates = [
        f for f in FLIGHTS
        if f["origin"] == e["origin"] and f["destination"] == e["destination"]
        and f["date"] == c["date"] and f["seats"] > 0 and f["flight_id"] not in sold_out
        and _passes(f, c, drop)
    ]
    if not candidates:
        return None
    if drop == "objective":
        best = optimal_flight(gold, sold_out)
        others = [f for f in candidates if f["flight_id"] != best]
        return others[0]["flight_id"] if others else None
    return _OBJECTIVES[c["objective"]](candidates)["flight_id"]


def _first_use_step(steps: list, keys: tuple) -> int | None:
    for i, step in enumerate(steps, 1):
        if "result" in step and any(k in step["args"] for k in keys):
            return i
    return None


def verify(traj, gold: dict, sold_out: set) -> dict:
    c, e = gold["constraints"], gold["entities"]
    late = gold.get("late_constraints", {})
    term = traj.terminal_state
    booked_id = term.get("booking.flight_id")
    optimal_id = optimal_flight(gold, sold_out)

    early = late_surv = None
    if booked_id is not None:
        f = next(x for x in FLIGHTS if x["flight_id"] == booked_id)
        early = {
            "route": f["origin"] == e["origin"] and f["destination"] == e["destination"],
            "date": f["date"] == c["date"],
            **{k: _passes(f, {k: c[k]}, None) for k in EARLY_FILTERS if k in c},
            "objective": booked_id == optimal_id,
        }
        late_surv = {k: term.get(f"booking.{k}") == v for k, v in late.items()}

    seen, fact_displacements = set(), 0
    for step in traj.steps:
        for key in _GROUNDED_KEYS:
            if key in step["args"] and str(step["args"][key]) not in seen:
                fact_displacements += 1
        if "result" in step:
            _flatten(step["result"], seen)

    flight_ok = booked_id is not None and booked_id == optimal_id
    late_ok = late_surv is not None and all(late_surv.values())
    booking_step = len(traj.steps) if term else None
    return {
        "success": flight_ok and late_ok,
        "flight_correct": flight_ok,
        "matches_gold_terminal": term == gold["terminal_state"],
        "booked_flight": booked_id,
        "booked_seat_type": term.get("booking.seat_type"),
        "booked_meal": term.get("booking.meal"),
        "early_survival": early,
        "late_survival": late_surv,
        "all_early_survived": None if early is None else all(early.values()),
        "all_late_survived": None if late_surv is None else all(late_surv.values()),
        "early_first_use_step": _first_use_step(traj.steps, ("flight_id",)),
        "late_commit_step": booking_step,
        "fact_displacements": fact_displacements,
        "first_error_step": traj.first_error_step,
        "num_steps_taken": len(traj.steps),
        "extra_steps": len(traj.steps) - len(gold["gold_steps"]),
        "injected": traj.injected_error is not None,
        "injected_at_step": traj.injected_at_step,
        "recovered": (flight_ok and late_ok) if traj.injected_error is not None else None,
    }
