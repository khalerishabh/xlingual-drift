"""
Scripted policy for Experiment 2. Executes the gold chain, or the chain of a
plan with one deliberate fault from the domain's FAULTS, so the verifier
and the stage attribution can be checked fault by fault without a GPU.
"""

from env.exp2.registry import DOMAINS


class Exp2MockPolicy:
    def __init__(self, instance: dict, mode: str = "solve"):
        mod = DOMAINS[instance["domain"]]
        if mode == "solve":
            self.steps = instance["gold_steps"]
            self.expected_failures = set()
        else:
            plan, self.expected_failures = mod.faulty_plan(instance["world"], instance["stages"], mode)
            self.steps = mod.chain(instance["world"], instance["stages"], plan)
        self.mode = mode
        self._i = 0

    def reset(self, request: str, tool_schemas: list, context: dict | None = None):
        self._i = 0

    def next_action(self, observations: list) -> dict:
        if observations and "error" in observations[-1]:
            return {"final": True}
        if self._i >= len(self.steps):
            return {"final": True}
        st = self.steps[self._i]
        self._i += 1
        return {"tool": st["tool"], "args": st["args"]}
