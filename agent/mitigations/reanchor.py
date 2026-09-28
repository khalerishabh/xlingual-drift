"""
STUB -- M2, re-anchoring (Section 8.10).

Every k steps, re-check accumulated state against the original request
(not against tool outputs -- that's the ledger's job). Cheaper than M1 to
implement; a useful ablation to isolate how much of the gain, if any, is
"remind the agent of the request" vs "carry structured state forward".

Suggested shape:

    class Reanchor:
        def __init__(self, original_request: str, every_k: int = 3):
            ...

        def maybe_reanchor(self, step_index: int) -> str | None:
            ...  # returns a re-anchoring prompt fragment, or None
"""

raise NotImplementedError("reanchor.py is a stub -- see module docstring. Phase 7 work.")
