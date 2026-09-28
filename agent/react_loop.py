"""
Minimal ReAct-style execution loop. The behaviour under test lives in the
policy (what to do next) and the tools; this loop only moves data between
them. A policy needs `reset(request, tool_schemas)` and
`next_action(observations)`, which returns {"tool": name, "args": {...}}
or {"final": True}.
"""

from dataclasses import dataclass, field

from env.inject import FailureInjector
from env.tools.travel_tools import ToolError, TravelTools


@dataclass
class Trajectory:
    task_id: str
    horizon: int
    steps: list = field(default_factory=list)
    terminal_state: dict = field(default_factory=dict)
    injected_error: dict | None = None
    injected_at_step: int | None = None
    first_error_step: int | None = None
    sold_out: set = field(default_factory=set)


def run_episode(task_id: str, horizon: int, request: str, policy,
                interface_mode: str = "strict", max_steps: int = 20,
                injector: FailureInjector | None = None) -> Trajectory:
    tools = TravelTools(interface_mode=interface_mode, horizon=horizon)
    policy.reset(request=request, tool_schemas=tools.schema_list())
    traj = Trajectory(task_id=task_id, horizon=horizon)

    for _ in range(max_steps):
        action = policy.next_action(traj.steps)
        if action.get("final"):
            break

        tool_name, args = action["tool"], action.get("args", {})
        record = {"tool": tool_name, "args": args}
        try:
            if injector is not None:
                injector.maybe_inject(tool_name, args, tools)
            record["result"] = tools.call(tool_name, args)
        except ToolError as e:
            record["error"] = {"error_type": e.error_type, "message": e.message}
            if traj.first_error_step is None:
                traj.first_error_step = len(traj.steps) + 1
            if injector is not None and injector.fired_at_step == len(traj.steps) + 1:
                traj.injected_error = record["error"]
                traj.injected_at_step = injector.fired_at_step
        except TypeError as e:
            record["error"] = {"error_type": "validation", "message": f"ValidationError: {e}"}
            if traj.first_error_step is None:
                traj.first_error_step = len(traj.steps) + 1

        traj.steps.append(record)
        if tool_name == tools.TERMINAL_TOOL and "result" in record:
            traj.terminal_state = dict(record["result"])
            break

    traj.sold_out = set(tools._sold_out)
    return traj
