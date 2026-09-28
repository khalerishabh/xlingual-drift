"""
STUB -- not implemented yet. Wire this up in Phase 2/3 once the full tool
set and prompt template exist (Section 8.7: frontier API models run here,
never on Colab -- no GPU needed for these).

Interface it must satisfy (see agent/react_loop.py):

    class ApiPolicy:
        def next_action(self, observations: list) -> dict:
            ...  # {"tool": name, "args": {...}} or {"final": True}

Suggested shape once implemented:
  - One system prompt shared across ALL conditions (Section 8.7: identical
    prompt format everywhere is load-bearing, per MASSIVE-Agents' finding
    that prompt format alone can move accuracy >20 points).
  - Tool schemas from env/tools/schemas.py passed as-is (English, matching
    real deployments).
  - `observations` (the trajectory so far) rendered into the conversation
    each turn; the model's structured tool call parsed back into
    {"tool": ..., "args": ...}.
  - Model client chosen by config (configs/*.yaml `model.provider`): the
    anthropic / openai / google-genai SDKs are commented out in
    requirements.txt -- uncomment whichever you wire up first.
"""

raise NotImplementedError(
    "api_policy is a stub. See the module docstring for the interface to implement."
)
