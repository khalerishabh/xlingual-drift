"""
Failure injection hooks (Section 8.6). Wraps a TravelTools instance so that
at a chosen step index, the next tool call raises a specific error instead
of executing normally -- regardless of whether that call would otherwise
have succeeded. The error message is available in English or localised,
so RQ4 (recovery) can test whether the *language* of the diagnostic is the
bottleneck, independent of the underlying task language.
"""

from env.tools.travel_tools import ToolError


# Minimal starter set. Extend as the Appendix C catalogue grows in Phase 2.
_LOCALISED_MESSAGES = {
    "not_found": {
        "en": "NotFound: flight {flight_id} has 0 seats available",
        "hi": "नहीं मिला: उड़ान {flight_id} में 0 सीट उपलब्ध हैं",
    },
    "validation": {
        "en": "ValidationError: 'date' must be ISO 8601 (YYYY-MM-DD)",
        "hi": "मान्यता त्रुटि: 'date' ISO 8601 (YYYY-MM-DD) में होनी चाहिए",
    },
}


class FailureInjector:
    def __init__(self, inject_at_step: int | None, error_type: str | None,
                 message_language: str = "en", flight_id: str | None = None):
        self.inject_at_step = inject_at_step
        self.error_type = error_type
        self.message_language = message_language
        self.flight_id = flight_id
        self._step_count = 0

    def maybe_inject(self):
        """Call once per step, before executing the real tool call."""
        self._step_count += 1
        if self.inject_at_step is None:
            return
        if self._step_count != self.inject_at_step:
            return
        template = _LOCALISED_MESSAGES.get(self.error_type, {})
        message = template.get(self.message_language, template.get("en", "InjectedError"))
        message = message.format(flight_id=self.flight_id or "AI440")
        raise ToolError(self.error_type, message)
