"""
STUB -- M3, error localisation (Section 8.10, Section 8.6).

Translates a tool's English error message into the task language before
the agent sees it, to test RQ4's hypothesis that the English-language
diagnostic itself is (part of) the recovery bottleneck, independent of the
task's own language.

Suggested shape:

    class ErrorLocaliser:
        def __init__(self, target_language: str):
            ...

        def localise(self, error_type: str, message_en: str) -> str:
            ...  # deterministic lookup table first (see env/inject.py's
                 # _LOCALISED_MESSAGES), falling back to MT only for error
                 # types/messages not yet catalogued
"""

raise NotImplementedError("error_localise.py is a stub -- see module docstring. Phase 7 work.")
