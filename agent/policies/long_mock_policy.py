"""
Scripted policy for the long-horizon domains. Executes the chain written
for a plan: the gold plan, or one with a single deliberate fault from the
domain's FAULTS, so the verifier can be checked fault by fault. Errors the
gold chain expects (the IMPS limit in pay) are stepped over.
"""

from env.long.registry import DOMAINS


class LongMockPolicy:
    def __init__(self, instance: dict, mode: str = "solve"):
        mod = DOMAINS[instance["domain"]]["module"]
        world = instance["world"]
        if mode == "solve":
            self.steps = instance["gold_steps"]
        else:
            plan, _ = mod.faulty_plan(world, mode)
            self.steps = mod.chain(world, plan)
            gold_errors = {i for i, s in enumerate(instance["gold_steps"]) if s.get("expect_error")}
            for i in gold_errors:
                if i < len(self.steps):
                    self.steps[i]["expect_error"] = instance["gold_steps"][i]["expect_error"]
        self.mode = mode
        self._i = 0

    def reset(self, request: str, tool_schemas: list, context: dict | None = None):
        self._i = 0

    def next_action(self, observations: list) -> dict:
        if observations and "error" in observations[-1] and not self.steps[self._i - 1].get("expect_error"):
            return {"final": True}
        if self._i >= len(self.steps):
            return {"final": True}
        st = self.steps[self._i]
        self._i += 1
        return {"tool": st["tool"], "args": st["args"]}
