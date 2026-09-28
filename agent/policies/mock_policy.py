"""
Scripted policy for testing the harness without a model. It walks the gold
tool sequence, but fills flight-dependent arguments from what the tools
actually returned, so it works at every horizon and can change course.

Modes:
  solve                    walk gold; stop at the first error.
  recover                  walk gold; retry transient errors; on not_found,
                           switch to the gold file's recovery_fallback flight
                           and redo the flight-specific steps.
  deviate_drop_constraint  drop the template's first early filter constraint
                           and book its decoy (early-constraint drift).
  deviate_wrong_flight     book the objective decoy: valid on every hard
                           constraint but not the best option.
  deviate_drop_late        book the right flight with a wrong seat type and
                           meal (late-constraint drift).
"""

from env.data.flights import MEAL_OPTIONS, SEAT_MAP, SEAT_TYPES

_FROM_RESULTS = ("hold_token", "fare_class", "passenger_id", "document_id")
_MODES = ("solve", "recover", "deviate_drop_constraint", "deviate_wrong_flight", "deviate_drop_late")


class MockPolicy:
    def __init__(self, gold: dict, mode: str = "solve"):
        assert mode in _MODES, mode
        self.gold_steps = gold["gold_steps"]
        self.mode = mode
        self.fallback = gold.get("recovery_fallback")
        self.decoys = gold.get("decoys", {})
        self.target = gold["terminal_state"]["booking.flight_id"]
        self.dropped = None
        if mode == "deviate_drop_constraint":
            self.dropped = next(k for k in self.decoys if k != "objective")
            self.target = self.decoys[self.dropped]
        late = gold.get("late_constraints", {})
        self.wrong_seat = next(s for s in SEAT_TYPES if s != late.get("seat_type"))
        self.wrong_meal = next(m["meal"] for m in MEAL_OPTIONS if m["meal"] != late.get("meal"))
        self._i = 0
        self._last_action = None

    def reset(self, request: str, tool_schemas: list, context: dict | None = None):
        self._i = 0
        self._last_action = None

    def next_action(self, observations: list) -> dict:
        if observations and "error" in observations[-1]:
            action = self._on_error(observations[-1]["error"]["error_type"])
            if action is not None:
                return action

        if self._i >= len(self.gold_steps):
            return {"final": True}
        step = self.gold_steps[self._i]
        self._i += 1
        action = {"tool": step["tool"], "args": self._fill(step, observations)}
        self._last_action = action
        return action

    def _on_error(self, error_type: str):
        if self.mode != "recover":
            return {"final": True}
        if error_type == "transient":
            return self._last_action
        if error_type == "not_found" and self.fallback and self.target != self.fallback:
            self.target = self.fallback
            self._i = next(i for i, s in enumerate(self.gold_steps) if "flight_id" in s["args"])
            return None
        return {"final": True}

    def _fill(self, step: dict, observations: list) -> dict:
        args = dict(step["args"])
        if self.dropped:
            args.pop(self.dropped, None)

        latest = {}
        for obs in observations:
            for key, value in obs.get("result", {}).items():
                if key in _FROM_RESULTS:
                    latest[key] = value
        if "flight_id" in args:
            args["flight_id"] = self.target
        for key in _FROM_RESULTS:
            if key in args and key in latest:
                args[key] = latest[key]

        if step["tool"] == "book_flight":
            if self.mode == "deviate_wrong_flight":
                args["flight_id"] = self.decoys["objective"]
            if self.mode == "deviate_drop_late":
                if "seat_type" in args:
                    args["seat_type"], args["meal"] = self.wrong_seat, self.wrong_meal
                else:
                    args["seat_id"] = next(s["seat_id"] for s in SEAT_MAP if s["seat_type"] == self.wrong_seat)
                    args["meal_code"] = next(m["meal_code"] for m in MEAL_OPTIONS if m["meal"] == self.wrong_meal)
        return args
