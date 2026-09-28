"""
Scripted policy that replays a gold trajectory, optionally with a
deliberate deviation or a scripted recovery. Has no idea what an LLM is --
it exists purely to prove the harness (loop -> tools -> injector ->
verifier -> run log) works before any real model is wired in. Each mode
demonstrates one thing the verifier/injector need to be able to catch:

  solve                     -- baseline: matches gold exactly.
  deviate_drop_constraint   -- state drift: "forgets" the budget partway
                               through and ends up booking an over-budget
                               flight. Should trip constraints_survived.
  deviate_wrong_flight      -- entity substitution: books a flight it
                               never checked availability for. Should trip
                               fact_displacements.
  recover_notfound          -- pairs with env/inject.py: when the gold
                               flight comes back "not found" (injected or
                               real), falls back to the next-best flight
                               and still completes the booking. Should trip
                               `recovered=True` even though the terminal
                               flight differs from gold (Section 8.6's
                               "recovery" is about reaching A correct
                               state, not necessarily the same one).
"""


class MockPolicy:
    def __init__(self, gold_steps: list, mode: str = "solve"):
        assert mode in (
            "solve",
            "deviate_drop_constraint",
            "deviate_wrong_flight",
            "recover_notfound",
        )
        self.gold_steps = gold_steps
        self.mode = mode

    def next_action(self, observations: list) -> dict:
        n = len(observations)

        # First four steps (resolve x2, search, filter) are shared by every
        # mode -- only deviate_drop_constraint touches the filter call.
        if n < 4:
            step = self.gold_steps[n]
            args = dict(step["args"])
            if self.mode == "deviate_drop_constraint" and step["tool"] == "filter_flights":
                args.pop("max_price", None)
            return {"tool": step["tool"], "args": args}

        if self.mode == "recover_notfound":
            return self._next_recover_notfound(observations)

        if n >= len(self.gold_steps):
            return {"final": True}

        step = self.gold_steps[n]
        args = dict(step["args"])
        if self.mode == "deviate_drop_constraint" and step["tool"] in (
            "get_seat_availability",
            "book_flight",
        ):
            args["flight_id"] = "AI999"  # the over-budget flight, only reachable post-drop
        if self.mode == "deviate_wrong_flight" and step["tool"] == "book_flight":
            args["flight_id"] = "6E212"  # never availability-checked -- fact displacement
        return {"tool": step["tool"], "args": args}

    def _next_recover_notfound(self, observations: list) -> dict:
        last = observations[-1] if observations else None

        if last is None or last.get("tool") == "filter_flights":
            return {"tool": "get_seat_availability", "args": {"flight_id": "AI440"}}

        if last.get("tool") == "get_seat_availability" and "error" in last:
            # Gold flight unavailable (injected or real) -- fall back.
            return {"tool": "get_seat_availability", "args": {"flight_id": "6E212"}}

        if last.get("tool") == "get_seat_availability" and "result" in last:
            flight_id = last["result"]["flight_id"]
            return {"tool": "book_flight", "args": {"flight_id": flight_id, "passenger_id": "P001"}}

        return {"final": True}
