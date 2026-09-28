"""
Failure injection (Section 8.6). Fires once, either on the Nth tool call
(`at_step`) or on the first call to a named tool (`at_tool`). Prefer
`at_tool`: a real model may take extra steps, so a fixed index can land on
different tools in different languages, while a tool target always hits
the same logical point in the task.

Error types:
  transient  one-shot; retrying the same call succeeds.
  not_found  persistent; the flight is marked sold out for the rest of the
             episode, so the only valid recovery is an alternative flight.
  validation one-shot for now. Phase 2 turns this into specification drift
             (the new format is enforced for the rest of the episode);
             until then it behaves like transient and should not be
             reported as a separate condition.

The message language is independent of the task language, which is what
lets RQ4 ask whether the English diagnostic itself is the bottleneck.
"""

import json
from pathlib import Path

from env.tools.travel_tools import ToolError

_MESSAGES = json.loads(
    (Path(__file__).resolve().parent / "data" / "error_messages.json").read_text(encoding="utf-8")
)


class FailureInjector:
    def __init__(self, error_type: str, message_language: str = "en",
                 at_step: int | None = None, at_tool: str | None = None):
        assert (at_step is None) != (at_tool is None), "set exactly one of at_step / at_tool"
        assert error_type in ("transient", "not_found", "validation")
        self.error_type = error_type
        self.message_language = message_language
        self.at_step = at_step
        self.at_tool = at_tool
        self.fired_at_step = None
        self._calls = 0

    def maybe_inject(self, tool_name: str, args: dict, tools) -> None:
        self._calls += 1
        if self.fired_at_step is not None:
            return
        if self.at_step is not None and self._calls != self.at_step:
            return
        if self.at_tool is not None and tool_name != self.at_tool:
            return

        self.fired_at_step = self._calls
        flight_id = args.get("flight_id", "")
        if self.error_type == "not_found" and flight_id:
            tools.mark_sold_out(flight_id)
        template = _MESSAGES[self.error_type].get(self.message_language, _MESSAGES[self.error_type]["en"])
        raise ToolError(self.error_type, template.format(flight_id=flight_id))
