"""
STUB -- required baseline, not our contribution (Section 15.1).

A TART-style static structured representation: the query is converted ONCE
into a fixed structured form (entities, sources, time, operation, answer
format) and that same representation is injected into the prompt at every
step, unchanged. This is the mitigation M1 (ledger.py) must beat at long
horizons to justify a "dynamic" state representation as anything more than
what TART already does.

Suggested shape:

    class TartStaticRepresentation:
        def __init__(self, request: str, constraints: dict):
            self.representation = self._extract_once(request, constraints)

        def render(self) -> str:
            return self.representation  # never updated after construction
"""

raise NotImplementedError("tart_static.py is a stub -- see module docstring. Phase 7 work.")
