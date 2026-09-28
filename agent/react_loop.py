"""
Minimal ReAct-style execution loop (Section 8, glossary: Agent, Trajectory).
Deliberately thin: the interesting behaviour lives in the policy (what to do
next) and the tools (env/tools/travel_tools.py), not in this loop. Any
policy -- mock, api, or local -- just needs a `.next_action(state)` method.
"""

from dataclasses import dataclass, field

from env.inject import FailureInjector
from env.tools.travel_tools import ToolError, TravelTools


@dataclass
class Trajectory:
    task_id: str
    steps: list = field(default_factory=list)   # [{tool, args, result_or_error}, ...]
    terminal_state: dict = field(default_factory=dict)
    injected_error: dict | None = None
    recovered_after_injection: bool | None = None
    first_error_step: int | None = None


def run_episode(
    task_id: str,
    policy,
    interface_mode: str = "strict",
    max_steps: int = 20,
    injector: FailureInjector | None = None,
) -> Trajectory:
    """
    Runs one agent episode against a fresh TravelTools instance.

    `policy.next_action(observations)` must return either:
      {"tool": <name>, "args": {...}}                     -- take an action
      {"final": True}                                     -- stop
    `observations` is the list of {tool, args, result|error} dicts so far.
    """
    tools = TravelTools(interface_mode=interface_mode)
    traj = Trajectory(task_id=task_id)
    saw_injected_error = False

    for _ in range(max_steps):
        action = policy.next_action(traj.steps)
        if action.get("final"):
            break

        tool_name, args = action["tool"], action.get("args", {})
        step_record = {"tool": tool_name, "args": args}

        try:
            if injector is not None:
                injector.maybe_inject()
            result = tools.call(tool_name, args)
            step_record["result"] = result
            if "booking.flight_id" in result:
                traj.terminal_state.update(result)
        except ToolError as e:
            step_record["error"] = {"error_type": e.error_type, "message": e.message}
            if traj.first_error_step is None:
                traj.first_error_step = len(traj.steps) + 1
            if injector is not None and injector.inject_at_step == len(traj.steps) + 1:
                saw_injected_error = True
                traj.injected_error = step_record["error"]

        traj.steps.append(step_record)

        if "booking.flight_id" in traj.terminal_state:
            break

    if saw_injected_error:
        traj.recovered_after_injection = "booking.flight_id" in traj.terminal_state

    return traj
