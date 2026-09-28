# xlingual-drift

Research code for *Cross-Lingual State Drift and Error Recovery in Long-Horizon LLM Agents*
(M.Tech Dissertation I, Rishabh Khale, VIT Vellore). Full design lives in the project's
`Project_Detail_Document.md` — this repo is the implementation of Section 8 and Appendix D
of that document.

## What's here right now

Phase 1 is in progress. The design spec is **`docs/PHASE1_SPEC.md`**, so read that first.

- **Travel domain, complete:** 11 deterministic tools where the *same request* needs 2 to 12
  steps depending on which values each tool requires. Three templates (travel_017–019) in
  en / zh / hi / ta / hinglish / tanglish, each with early constraints (applied when the
  flight is chosen) and late constraints (seat and meal, committed in the final call, so the
  distance they must be carried grows with horizon). Gold for every template and horizon is
  built and checked by `python -m tasks.build_gold`. Strict and lenient interface modes, and
  failure injection with localised error messages.
- **Verifier:** success given episode state, early and late constraint survival with the step
  each was used at, fact displacement, recovery. No LLM judge anywhere.
- **Mock policy:** walks gold with real tool outputs, so the harness runs end to end with
  **no API key and no GPU**. It can also deviate or recover on purpose.
- **Real-model policy:** `agent/policies/openai_compat_policy.py` talks to any
  OpenAI-compatible endpoint: vLLM on Colab for real runs, Ollama on a laptop for
  debugging, or a hosted API. Open-source models are the primary setup; APIs are optional.
- **Runner:** resumable after a disconnect; endpoint failures are logged but never scored;
  full transcripts (messages, reasoning, token usage) saved per episode.
- **Tests:** 106 pytest checks covering gold replay, horizon invariance, load-bearing
  constraints, script hygiene, lenient-mode safety, recovery, and the model-policy plumbing.
- **Stubs:** the four mitigations in `agent/mitigations/` (Section 8.10).

Next: run the capability gate on Colab (`notebooks/colab_runner.ipynb`), then the shop
domain and the remaining templates (spec Section 8).

## Development workflow

Decided 28 Sep 2026 (Section 15.8 of the project doc):

- **GitHub is the source of truth for code.** Nothing here should live only on someone's
  laptop or only in a Colab session.
- **Anything that doesn't need a GPU** — writing/debugging the environment, the verifier,
  the stats pipeline, and any run against an **API** model (Claude, GPT, Gemini) — is done
  locally (or in this session). No GPU required for any of that.
- **Anything that needs a GPU** — running an **open-weight** model (Qwen3, Llama 3.1 8B,
  Granite 4, ≤~32B) or the optional SFT ablation — runs on **Google Colab Pro**
  (A100, 80GB VRAM, ~150GB system RAM). There is no institutional lab GPU behind this
  project; Colab Pro is the only GPU available.
- In Colab: `git clone`/`git pull` this repo at the start of the session (not a Drive sync
  of loose files). Mount Google Drive only for bulky, disposable artifacts — raw
  `runs/*.jsonl` logs and downloaded model weights — that shouldn't go into git. At the end
  of the session, commit the condensed results (metrics tables, not raw logs) back to
  GitHub. See `notebooks/colab_runner.ipynb`.
- Keep API keys out of git entirely: copy `.env.example` to `.env` locally (gitignored); in
  Colab, use the Secrets manager (`google.colab.userdata`) instead of pasting keys into
  cells.

## Quickstart (no API key needed)

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows; on Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q                 # expect: 106 passed
python -m eval.run_grid --config configs/smoke_test.yaml
```

The smoke test runs 7 mock cells on 3 templates at 6 horizons (126 episodes): a clean solve,
three deliberate deviations (lost early constraint, wrong objective, lost seat and meal), two
recovery runs (not_found with an English message, transient with a Chinese message), and one
non-recovering run. Add `--workers 8` to run episodes concurrently. Every `solve` and
`recover` line should show `success=True`, and every deviation `success=False`.

## Running a real model

- **On Colab (real runs):** open `notebooks/colab_runner.ipynb` on an 80GB A100 runtime
  and run top to bottom. It starts vLLM, runs `configs/capability_gate_v2.yaml`, writes raw
  logs to Drive, and prints early vs late constraint survival by language and horizon. Rerun from the top after a disconnect.
- **On a laptop (debugging only):** with Ollama installed, `ollama pull qwen3:8b`, then
  `python -m eval.run_grid --config configs/local_ollama_debug.yaml`.

Thinking mode, temperature and seeds are set per cell in the config and must stay fixed
across every language, horizon and control being compared.

## Repository layout

See Appendix D of `Project_Detail_Document.md` for the full description. Short version:

```
env/        deterministic tools + data + multilingual alias tables + failure injection
tasks/      task templates (all languages) and gold trajectories
agent/      the ReAct loop, pluggable policies (mock / api / local), mitigation methods
eval/       CLI entrypoint, verifier, metrics, stats
configs/    YAML configs — which model, which languages, which controls, per run
docs/       PHASE1_SPEC.md — environment, template, gold and injection design
tests/      pytest suite (python -m pytest -q)
notebooks/  colab_runner.ipynb — the Colab-side entrypoint
runs/       raw run logs (gitignored)
```

## Next steps

See `docs/PHASE1_SPEC.md` Section 8 (open items before freezing).
