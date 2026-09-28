# xlingual-drift

Research code for *Cross-Lingual State Drift and Error Recovery in Long-Horizon LLM Agents*
(M.Tech Dissertation I, Rishabh Khale, VIT Vellore). Full design lives in the project's
`Project_Detail_Document.md` — this repo is the implementation of Section 8 and Appendix D
of that document.

## What's here right now

This is a **scaffold**, not the finished harness. It has:

- A working example task (flight booking, horizon 6) with a real deterministic tool
  environment, a gold trajectory, and a verifier that can grade a trajectory against it.
- A `mock` agent policy that follows the gold trajectory (or deliberately deviates), so the
  whole pipeline runs end-to-end with **no API key and no GPU**, to prove the harness works
  before any real model is wired in.
- Stubs for the real agent policies (`agent/policies/api_policy.py`, `local_policy.py`) and
  for the mitigation methods (`agent/mitigations/`), matching Section 8.10.
- One CLI entrypoint, `eval/run_grid.py`, used identically on a laptop and in Colab.

Everything else in Appendix D's tree (the other 39 templates, the real error-injection
catalogue, the stats pipeline) is Phase 1–2 work and comes next.

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

## Quickstart (local, no API key needed)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m eval.run_grid --config configs/smoke_test.yaml
```

This runs the one example task through the mock policy five ways — solving it cleanly,
two deliberate deviations (a dropped budget constraint, a substituted flight), and two
failure-injection-and-recovery runs (English vs. Hindi error message) — verifies each
trajectory against gold, and writes a run log to `runs/smoke_test.jsonl`. Expected output:

```
  [solve] success=True constraints_survived=True fact_displacements=0 injected=False recovered=None
  [deviate_drop_constraint] success=False constraints_survived=False fact_displacements=0 injected=False recovered=None
  [deviate_wrong_flight] success=False constraints_survived=True fact_displacements=1 injected=False recovered=None
  [recover_notfound] success=False constraints_survived=True fact_displacements=0 injected=True recovered=True
  [recover_notfound] success=False constraints_survived=True fact_displacements=0 injected=True recovered=True
```

If this passes, the harness (environment → failure injection → agent loop → verifier → run
log) is working end-to-end — this is the thing to keep passing as you build out the real
policies and the other 39 templates.

## Repository layout

See Appendix D of `Project_Detail_Document.md` for the full description. Short version:

```
env/        deterministic tools + data + multilingual alias tables + failure injection
tasks/      task templates (all languages) and gold trajectories
agent/      the ReAct loop, pluggable policies (mock / api / local), mitigation methods
eval/       CLI entrypoint, verifier, metrics, stats
configs/    YAML configs — which model, which languages, which controls, per run
notebooks/  colab_runner.ipynb — the Colab-side entrypoint
runs/       raw run logs (gitignored)
```

## Next steps (Phase 1, per Section 17 of the project doc)

1. Design the remaining ~9 tools and their JSON schemas (this scaffold has 4: `resolve_city`,
   `search_flights`, `filter_flights`, `get_seat_availability`, `book_flight` — 5, covering
   the travel domain end of Section 8.1's "10-15 tools across 2-3 domains").
2. Author the other ~39 task templates across all horizons and languages (Appendix A shows
   the pattern for one).
3. Wire up `api_policy.py` against a real API model and re-run the smoke test.
4. Build the lenient-interface alias tables and the oracle-plan mode (Section 8.4).
