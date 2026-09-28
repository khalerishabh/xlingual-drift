# xlingual-drift

Research code for *Cross-Lingual State Drift and Error Recovery in Long-Horizon LLM Agents*
(M.Tech Dissertation I, Rishabh Khale, VIT Vellore). Full design lives in the project's
`Project_Detail_Document.md` — this repo is the implementation of Section 8 and Appendix D
of that document.

## What's here right now

Phase 1 is in progress. The design spec is **`docs/PHASE1_SPEC.md`**, so read that first.

- **Travel domain, complete:** 7 deterministic tools where the *same request* needs 2, 4, 6
  or 8 steps depending on which values each tool requires. One template (travel_017) in
  en / zh / hi / ta / hinglish / tanglish, gold trajectories at all four horizons,
  strict and lenient interface modes, and failure injection with localised error messages.
- **Verifier:** success given episode state, per-constraint survival, fact displacement,
  recovery. No LLM judge anywhere.
- **Mock policy:** walks gold with real tool outputs, so the harness runs end to end with
  **no API key and no GPU**. It can also deviate or recover on purpose.
- **Tests:** 33 pytest checks covering gold replay, horizon invariance, load-bearing
  constraints, script hygiene, lenient-mode safety, and recovery.
- **Stubs:** `agent/policies/api_policy.py`, `local_policy.py`, and the four mitigations in
  `agent/mitigations/` (Section 8.10).

Next: the shop domain, the remaining templates, and wiring a real API model
(spec Section 8).

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
python -m pytest -q                 # expect: 33 passed
python -m eval.run_grid --config configs/smoke_test.yaml
```

The smoke test runs 6 mock cells at each of the 4 horizons (24 episodes): a clean solve, two
deliberate deviations (lost budget, wrong objective), two recovery runs (not_found with an
English message, transient with a Chinese message), and one non-recovering run. Every
`solve` and `recover` line should show `success=True`, and every deviation `success=False`.

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
