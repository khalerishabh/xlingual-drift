"""
Scripted policy for testing the harness without a model. It walks the gold
tool sequence, but fills flight-dependent arguments (flight_id, hold_token,
fare_class, passenger_id) from what the tools actually returned, so it
works at every horizon and can change course.

Modes:
  solve                    walk gold; stop at the first error.
  recover                  walk gold; retry transient errors; on not_found,
                           switch to the gold file's recovery_fallback flight
                           and redo the flight-specific steps.
  deviate_drop_constraint  drop max_price and pursue the gold file's
                           max_price decoy (state drift on the budget).
  deviate_wrong_flight     book the gold file's objective decoy: valid on
                           every hard constraint but not the best option
                           (at h6+ also a hold mismatch).
"""

_FLIGHT_KEYS = ("flight_id", "hold_token", "fare_class", "passenger_id")


class MockPolicy:
    def __init__(self, gold: dict, mode: str = "solve"):
        assert mode in ("solve", "recover", "deviate_drop_constraint", "deviate_wrong_flight")
        self.gold_steps = gold["gold_steps"]
        self.mode = mode
        self.fallback = gold.get("recovery_fallback")
        self.target = gold["terminal_state"]["booking.flight_id"]
        self.decoys = gold.get("decoys", {})
        if mode == "deviate_drop_constraint":
            self.target = self.decoys["max_price"]
        self._i = 0
        self._last_action = None

    def reset(self, request: str, tool_schemas: list):
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
        if self.mode == "deviate_drop_constraint":
            args.pop("max_price", None)
            if step["tool"] == "filter_flights" and not args:
                args["depart_before"] = step["args"].get("depart_before", "12:00")

        latest = {}
        for obs in observations:
            for key, value in obs.get("result", {}).items():
                if key in _FLIGHT_KEYS:
                    latest[key] = value

        for key in _FLIGHT_KEYS:
            if key not in args:
                continue
            if key == "flight_id":
                args[key] = self.target
            elif key in latest:
                args[key] = latest[key]

        if self.mode == "deviate_wrong_flight" and step["tool"] == "book_flight":
            args["flight_id"] = self.decoys["objective"]
        return args
