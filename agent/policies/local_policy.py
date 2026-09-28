"""
STUB -- not implemented yet. This is the ONE policy that needs a GPU, so it
is the one that only ever runs on Colab Pro (A100, 80GB VRAM), never
locally (Section 8.7, Section 15.8).

Interface it must satisfy (see agent/react_loop.py):

    class LocalPolicy:
        def next_action(self, observations: list) -> dict:
            ...  # {"tool": name, "args": {...}} or {"final": True}

Suggested shape once implemented:
  - Load an open-weight model (Qwen3 8B/14B/32B, Llama 3.1 8B, Granite 4)
    via transformers or vllm, 4-bit quantized if it's the 32B end of that
    range, so it fits comfortably in 80GB VRAM alongside everything else.
  - Same prompt template and tool schemas as api_policy.py -- the whole
    point of Section 8.7 is that only the model backbone changes.
  - Do NOT try to load Llama 3.1 70B / Qwen3-Next-80B-A3B / Qwen3-VL-235B-A22B
    here -- those were dropped from the shortlist (Section 8.7, Section
    15.8) precisely because they don't fit a single 80GB A100.
"""

raise NotImplementedError(
    "local_policy is a stub. See the module docstring for the interface to implement. "
    "This policy is Colab-only (needs a GPU) -- see notebooks/colab_runner.ipynb."
)
