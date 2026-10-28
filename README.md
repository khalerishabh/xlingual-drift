# xlingual-drift

Research code for the M.Tech Dissertation I project **"Cross-Lingual State Drift and Error Recovery in
LLM Agents for Indic and Code-Mixed Tasks"** (Rishabh Shailendra Khale, 25MAI0046, VIT Vellore; guide:
Dr. Vijayasherly V).

The project asks what happens to an LLM agent's task state while it carries out a long, multi-step
task that a user wrote in **Hindi, Tamil, Hinglish or Tanglish**, compared with the same task in
English:

- **RQ1:** how much does the agent drift, and does the gap to English grow as tasks get longer?
- **RQ2:** where do the failures come from (tool calling, planning, execution or termination), and in
  which kind of constraint?
- **RQ4:** when a tool fails mid-task, is recovery harder in a non-English task?

RQ3 (localising tool outputs and error messages) and RQ5 (mitigation) were moved out of scope on
28 Oct 2026. The code for RQ3 exists; the mitigations are stubs.

Everything is measured in a **deterministic tool environment written for this project**. Every task
has a known correct answer, a deliberate wrong answer (a "decoy") for every constraint, and a
verifier that checks every constraint against the final state. No LLM judge and no human annotation
are used anywhere.

---

## Contents

1. [Status and results](#1-status-and-results)
2. [How the project works](#2-how-the-project-works)
3. [Key terms](#3-key-terms)
4. [Quickstart on a laptop (no GPU)](#4-quickstart-on-a-laptop-no-gpu)
5. [Running a real model on Colab](#5-running-a-real-model-on-colab)
6. [Analysing a run](#6-analysing-a-run)
7. [What every file does](#7-what-every-file-does)
8. [How to add or change things](#8-how-to-add-or-change-things)
9. [Rules this repo follows](#9-rules-this-repo-follows)

---

## 1. Status and results

All main runs use **Qwen/Qwen3.6-27B-FP8** (weights revision `e89b16eb`) served with **vLLM 0.30.0** on
one Colab A100, thinking on and temperature 0.6. About 2,000 episodes have been scored in total.

| # | Experiment | Config | Summary in `results/` | Outcome |
|---|---|---|---|---|
| 1 | Travel capability gate v1 | `configs/capability_gate.yaml` | `capability_gate_qwen36_27b.json` | No tool-interface errors; English, Chinese and Hindi at ceiling |
| 2 | Gate v2, late-binding constraints | `configs/capability_gate_v2.yaml` | `capability_gate_v2_qwen36_27b_fp8.json` | Hindi lead at 10-12 steps, confounded with a change of interface |
| 3 | Trip pilots (English only) and trip gate | `configs/trip_pilot_en.yaml`, `configs/trip_gate_v1.yaml` | `trip_pilot_en_qwen36_27b_fp8.json`, `trip_gate_v1_qwen36_27b_fp8.json` | Difficulty rule set on English; one ambiguous Tamil phrase found and fixed |
| 4 | Trip main run (500 episodes) | `configs/trip_main_v1.yaml` | `trip_main_v1_qwen36_27b_fp8.json` | No language x horizon interaction (p = 0.63) |
| 5 | Small model, Qwen3.5-4B | `configs/trip_small_qwen35_4b.yaml` | - | Below the capability floor (4 of 117 solved) |
| 6 | Long-horizon domains, 30-40 steps | `configs/rq1_long_qwen36_27b_fp8.yaml` | `rq1_long_qwen36_27b_fp8.json` | Pre-registered drift test negative for every language |
| 7 | Sarvam-30B (Indic-native model) | `configs/rq1_long_sarvam30b.yaml` | - | Below the floor (0 of 99 solved, English included) |
| 8 | **Experiment 2** (675 episodes) | `configs/exp2/*_qwen.yaml` | `exp2_rq1_rq2.json` | Answers RQ1 and RQ2 (below) |

**Experiment 2 findings** (Food, Shopping and Payment; Travel and Banking are built and frozen but not run):

- The gap to English is 1-3 points on short and medium tasks and **11-13 points on long tasks**
  (27 points in Pass^3 consistency). The widening is clear in direction but not statistically
  significant (difference-in-differences -10.6 points, p = 0.17).
- Values stated in the request are never lost: 1,260 of 1,262 "anchors" were committed correctly.
- No failures at planning or tool calling. Reasoning loops (the model announces a tool call and
  never makes it) hit all languages alike. Wrong committed values are almost only non-English
  (28 of 29), late in long tasks, in **running state the agent derives** (a rule switch, the best
  coupon for a cart), not entity confusion.

Full write-ups: `docs/EXP2_SPEC.md` (section 10), `proj_detail_doc.md`, and the Dissertation I report.

---

## 2. How the project works

```
  1. BUILD TASKS (laptop)        2. RUN EPISODES (Colab A100)        3. SCORE (laptop)          4. ANALYSE (laptop)
  ------------------------       ----------------------------        -----------------          -------------------
  env/<domain>  world + tools    eval/run_grid.py                    verifier per domain        eval/exp2_summary.py
  solve(): answer + decoys  -->  for each task x language x seed --> every constraint:     -->  eval/stages.py
  chain(): gold tool calls       agent/react_loop.py                 expected vs committed      eval/exp2_report.py
  lexicons: 5 languages          agent/policies/openai_compat        eval/stages.py labels      results/*.json
  tasks/build_*.py replays gold  vLLM serves the pinned model        each failure               (tables, models)
  -> tasks/**/*.json (frozen)    -> runs/<run>.jsonl (one line       eval/rescore_*.py fixes
                                    per episode, full transcript)    by replaying logged calls
```

**Step 1: build tasks.** Each domain module (for example `env/exp2/payment.py`) generates a small world
from a seed (bills, accounts, products, restaurants, flights). `solve()` computes the correct answer
and one decoy per constraint *from the constraints alone*. `chain()` writes the gold sequence of tool
calls. A builder script (`tasks/build_exp2.py` and others) replays the gold chain through the real
tools, checks every design rule (each constraint must change the answer; the requested option is never
listed first; look-alike ids sit next to every answer; a recovery path exists), renders the request in
every language from frozen lexicons, and only then writes the task file. Task files are committed and
never edited because of a result.

**Step 2: run episodes.** `eval/run_grid.py` reads a YAML config and expands it into episodes
(task x language x cell x seed). For each episode it creates fresh tools, and `agent/react_loop.py`
runs the agent: the policy sends the conversation and tool schemas to the model, gets back exactly
one tool call, the loop executes it and returns the JSON result or an error message, until the
terminal call (for example `confirm_batch`), a text reply, or the step limit. A failure injector can
make a named tool fail (RQ4). Each episode is appended to `runs/<run_name>.jsonl` with its full
trajectory, reasoning and token counts. Runs resume after a disconnect, and the runner refuses to mix
episodes from a different model, revision or vLLM version in one log.

**Step 3: score.** The domain's `verify()` reads the end state (`snapshot()`) and records, for every
constraint, whether it holds, its class, the step it was committed at, the expected and committed
values, and whether the decoy was hit. `eval/stages.py` gives each failed constraint one label:
loop, tool calling, planning, or execution (E1A, E1B, E2, E3). If a verifier bug is found later,
`eval/rescore_*.py` replays the logged tool calls through fresh tools; the model is not called again
and the agent's actions are unchanged.

**Step 4: analyse.** The summary and report scripts reduce each episode to its first attempt, count a
reply cut off at the token limit as a failure, and write tables, Wilson intervals, logistic models
(standard errors clustered by task) and Pass^3 to `results/*.json`.

Only step 2 needs a GPU. Everything else runs on a laptop, and the 631 tests check that a wrong number
cannot come from the harness instead of the model.

---

## 3. Key terms

| Term | Meaning |
|---|---|
| Episode | One agent run on one task, in one language, with one seed |
| Domain | A family of tasks with its own tools: travel, trip, shop/pay (long), and the five Experiment 2 domains (travel, shopping, food, payment, banking) |
| Scenario / instance | One generated world plus a request. Experiment 2 has 5 scenarios per domain |
| Format | Experiment 2 task length: short, medium, long. Nested: short is a subset of medium, medium of long, with shared clauses worded identically |
| Horizon (h) | Number of tool calls in the gold chain (travel h2-h12, trip h14-h28, Exp 2 about 6-25) |
| Language condition | `en` (native), `hi`, `ta` (non-native), `hinglish`, `tanglish` (code-mixed); `zh` in earlier experiments |
| Constraint | A requirement in the request that changes the correct outcome; each has a decoy |
| Constraint class | selection, attribute, binding, carried, coupled, anchor, global (Exp 2); early, mid, carried, late (trip) |
| Anchor | A value stated in every format and committed only in the final call, so its carry distance grows with length |
| Cell | A model setting inside a config (policy, model, temperature, thinking, seeds) |
| Serving fingerprint | Model, revision, vLLM version and GPU written to `serving.json` and stamped on every episode |
| First attempt | The unit of analysis: the first logged run of each episode. Endpoint errors are retried and never scored |
| Loop | A reply that hit `max_tokens` (16,384) without a tool call; counted as a termination failure |
| E1A / E1B / E2 / E3 | Execution sub-labels: state lost after the right value was used in a call (E1A) or written in reasoning (E1B); wrong value right after a tool error (E2); right value never held (E3) |
| Pass^3 | Share of task-language cells solved by all three seeds |

---

## 4. Quickstart on a laptop (no GPU)

```bash
python -m venv .venv
.venv\Scripts\activate             # Windows; on Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
pip install pandas statsmodels      # only needed for eval/exp2_report.py and eval/drift.py

python -m pytest -q                 # expect: 631 passed
```

Mock runs exercise the whole pipeline with a scripted policy instead of a model (no API key, no GPU):

```bash
python -m eval.run_grid --config configs/smoke_test.yaml          # travel: gold, 3 deviations, recovery
python -m eval.run_grid --config configs/smoke_test_trip.yaml     # trip: one fault per constraint class
python -m eval.run_grid --config configs/smoke_test_long.yaml     # shop and pay, 30-40 steps

python -m eval.run_grid --config configs/exp2/smoke_payment.yaml --out runs/exp2_smoke_payment.jsonl --workers 8
python -m eval.exp2_smoke runs/exp2_smoke_payment.jsonl           # gold succeeds, each fault fails only its own constraints
```

Add `--workers N` to run episodes in parallel.

Debugging against a local model (results from this are never reported):

```bash
ollama pull qwen3:8b
python -m eval.run_grid --config configs/local_ollama_debug.yaml
```

---

## 5. Running a real model on Colab

Each Experiment 2 domain has its own notebook in `notebooks/exp2/`. Open it on an A100 runtime and run
the cells in order:

| Cell | What it does |
|---|---|
| 1 | Shows the GPU; the config decides whether it is large enough |
| 2 | Clones or updates this private repo with the `GITHUB_TOKEN` stored in **Colab Secrets** |
| 3 | Installs the harness, and vLLM 0.30.0 in a separate Python 3.12 venv |
| 4 | Mounts Google Drive; logs go to `MyDrive/xlingual-drift-runs/` so a disconnect loses nothing |
| 5 | Starts vLLM with exactly the model the config pins and writes `serving.json` |
| 6 | Runs the tests and the domain's mock smoke test |
| 7 | Phase 1: English, seed 1, all 15 tasks |
| 8 | Early-stop check: stop the domain if English success is below 0.3 |
| 9 | Phase 2: the full 225-episode grid with `--resume` |
| 10 | Outcome table and stage attribution |
| 11 | Downloads the log; put it in `runs/` on your laptop |

After a disconnect, rerun cells 1-5 and then cell 9; finished episodes are skipped.
Do not save the notebook back to GitHub from Colab.

The older runs use `notebooks/colab_runner.ipynb` (travel, trip and long-horizon configs, chosen by
`CONFIG` in the notebook), `notebooks/rq3_runner.ipynb` (seams) and `notebooks/sarvam_runner.ipynb`
(Sarvam-30B served with SGLang).

The runner command the notebooks use:

```bash
python -m eval.run_grid --config configs/exp2/payment_qwen.yaml --serving serving.json --resume --workers 16 --out <drive>/exp2_payment_qwen36_27b_fp8.jsonl
```

---

## 6. Analysing a run

```bash
# outcome tables by domain x format x language group (first attempts, loop = failure)
python -m eval.exp2_summary runs/exp2_food_qwen36_27b_fp8.jsonl runs/exp2_shopping_qwen36_27b_fp8.jsonl

# one stage label per failed constraint (add --rows out.jsonl to dump every constraint)
python -m eval.stages runs/exp2_payment_qwen36_27b_fp8.rescored_waive.jsonl

# after a verifier fix: replay logged calls through fresh tools and rescore
python -m eval.rescore_exp2 runs/exp2_payment_qwen36_27b_fp8.jsonl runs/exp2_payment_qwen36_27b_fp8.rescored.jsonl
python -m eval.rescore_exp2 runs/exp2_payment_qwen36_27b_fp8.jsonl runs/exp2_payment_qwen36_27b_fp8.rescored_waive.jsonl --waive payment:short:batch.no_extra

# the full RQ1/RQ2 evaluation that produced results/exp2_rq1_rq2.json
python -m eval.exp2_report runs/exp2_food_qwen36_27b_fp8.jsonl \
    runs/exp2_shopping_qwen36_27b_fp8.jsonl \
    runs/exp2_payment_qwen36_27b_fp8.rescored_waive.jsonl --out results/exp2_rq1_rq2.json

# long-horizon runs: drift types and the pre-registered RQ1 decision
python -m eval.rescore_long runs/rq1_long_qwen36_27b_fp8.jsonl runs/rq1_long_qwen36_27b_fp8.rescored.jsonl
python -m eval.drift runs/rq1_long_qwen36_27b_fp8.rescored.jsonl
```

The `--waive payment:short:batch.no_extra` option exists because the Payment short request said
"for every bill" while naming one bill; the check is dropped for that format in every language and the
original scores are reported alongside (see `docs/EXP2_SPEC.md` section 10).

---

## 7. What every file does

### Top level

| File | Purpose |
|---|---|
| `README.md` | This file |
| `requirements.txt` | Packages for the harness and tests: pyyaml, pydantic, jsonschema, pytest, openai. Analysis also needs pandas and statsmodels |
| `pytest.ini` | Points pytest at `tests/` |
| `.gitignore` | Keeps `.venv`, caches, `.env` and raw `runs/*.jsonl` logs out of git |
| `.env.example` | Template for local API keys; copy to `.env` (never committed). In Colab use Secrets instead |
| `proj_detail_doc.md` | Snapshot of the project detail document (background, decisions, literature). The current version lives in the claude.ai Project |

### `agent/`: the agent loop, policies and prompts

| File | Purpose |
|---|---|
| `react_loop.py` | The ReAct loop: asks the policy for one action, executes it against the tools (with optional failure injection), records each step, stops at the terminal tool, a text reply or the step limit. Returns a `Trajectory` |
| `policies/openai_compat_policy.py` | The real-model policy for any OpenAI-compatible endpoint (vLLM, SGLang, Ollama, hosted APIs). Sends messages and tool schemas, keeps only the first tool call, records reasoning and token usage, resamples empty replies, raises `InfraError` for endpoint failures and for replies cut off at `max_tokens` |
| `policies/mock_policy.py` | Scripted policy for the travel domain: solves, deviates on purpose (drops a constraint, wrong objective, drops seat and meal) or recovers from injected errors |
| `policies/trip_mock_policy.py` | Scripted policy for the trip domain, with one fault per constraint class (dropped time window, broken budget, wrong hotel, wrong pickup time, swapped seats and more) |
| `policies/long_mock_policy.py` | Scripted policy for the shop and pay long-horizon domains (gold or one fault from each domain's `FAULTS`) |
| `policies/exp2_mock_policy.py` | Scripted policy for Experiment 2 (gold or one fault), used by the smoke configs |
| `prompts/system_v1.txt` | System prompt for the travel and trip runs (allows a reply to the user if the task cannot be done) |
| `prompts/system_v1_noask.txt` | v1 plus "do not ask the user, look it up"; used only for the Sarvam diagnostic |
| `prompts/system_v2.txt` | Experiment 2 prompt: fully autonomous, no questions to the user. `{session_date}` is filled per task |
| `mitigations/ledger.py`, `reanchor.py`, `error_localise.py`, `tart_static.py` | Stubs with the intended design of the RQ5 mitigations (dynamic state ledger, periodic re-anchoring, localised error messages, TART-style static baseline). Out of scope for now |

### `env/`: deterministic tool environments

**Travel domain (Phase 1, capability gates)**

| File | Purpose |
|---|---|
| `tools/travel_tools.py` | 11 travel tools (search, filter, seat map, meals, booking and more); strict or lenient interface; raises `ToolError` |
| `tools/horizons.py` | How the same request needs 2 to 12 calls: which values each tool requires at each horizon |
| `tools/schemas.py` | JSON schemas of the travel tools per horizon (English, BFCL style) |
| `data/flights.py` | The flight table and seat maps; every non-answer row is a decoy for one constraint |
| `aliases/city_aliases.json` | Spelling and script variants of city names, used only in lenient mode |
| `data/error_messages.json` | Tool error messages (transient, not_found, validation) in en, zh, hi, ta and Hinglish, for failure injection |
| `inject.py` | `FailureInjector`: makes one call fail, at a step number or (preferred) at the first call to a named tool, with the message in English or the task language |

**Trip domain (family trip organiser, 14-28 calls)**

| File | Purpose |
|---|---|
| `trip/world.py` | The Jaipur world: flights, hotels, rooms, cabs, attractions, deliberately unsorted |
| `trip/tools.py` | 22 trip tools; checkout validates ids but never preferences, so errors cannot leak the answer |
| `trip/levels.py` | The four horizon levels (14, 17, 24, 28 calls) and what each adds |
| `trip/schemas.py` | Tool schemas per level |
| `trip/solver.py` | Correct trip and one decoy per constraint, from the constraints alone |
| `trip/chain.py` | Writes the tool-call chain for a plan (gold or deliberately wrong) |

**Long-horizon domains (shop and pay, 30-40 calls; RQ1 final test and RQ3)**

| File | Purpose |
|---|---|
| `long/base.py` | Shared tools base, look-alike id helpers, and the seams S0-S3 (which parts are localised) |
| `long/shop.py` | Festive shopping for four people plus an exchange; mid-episode stock-out; entity and semantic drift pressure |
| `long/pay.py` | Month-end bills with an amount rule and a savings-floor rule, transfers with a designed IMPS error, standing instruction, budget tags |
| `long/registry.py` | Maps `shop` and `pay` to their modules |
| `long/lexicon/shop.json`, `pay.json` | Request text and localised tool-output text per language |

**Experiment 2 (five domains, three nested formats)**

| File | Purpose |
|---|---|
| `exp2/core.py` | Shared machinery: `Exp2Tools` base class (schema validation, `snapshot()`), request rendering from lexicons, constraint records, the never-first rule |
| `exp2/food.py` | Food Order: restaurant, four dishes with spice or Jain, bread, dessert under a total, best offer, slot, card and address |
| `exp2/shopping.py` | Shopping: items for four family members, joint budget, gift wrap, exchange, best coupon, card and slot |
| `exp2/payment.py` | Payment: six bills (amount and savings-floor rules, remarks), NEFT rent, IMPS pocket money, wallet top-up, UPI merchant, date and contact |
| `exp2/banking.py` | Banking: dispute, card block and replacement, card limit, FD, RD, nominee, stop cheque, channel and branch |
| `exp2/travel.py` | Travel: the trip domain at one fixed tool level, booking only what each format asks for |
| `exp2/registry.py` | Maps domain names to modules |
| `exp2/lexicon_src/<domain>_<lang>.py` | Request templates and terms per domain and language. English is the source; hi, ta, Hinglish and Tanglish were LLM-drafted, then reviewed and frozen by the author (the task files record "author: Rishabh, 2026-10-28") |
| `exp2/lexicon/<domain>.json` | Assembled lexicons used by the builder |
| `exp2/lexicon_drafts/` | Holding area for drafts awaiting review (currently empty) |

Every Experiment 2 domain module provides the same interface: `SCENARIOS`, `FORMATS`, `ANCHOR_STAGE`,
`generate()`, `solve()`, `chain()`, `check_rules()`, `Tools`, `verify()` and `faulty_plan()` with
four scripted `FAULTS`.

### `tasks/`: builders and frozen task files

| File or folder | Purpose |
|---|---|
| `build_gold.py` | Builds `gold/travel_*_h*.json` for the three travel templates at six horizons; enforces the design rules |
| `build_trip_gold.py` | Builds `trip_gold/trip_*_h*.json` for five trip templates at four horizons |
| `build_long.py` | Builds `long/shop_*.json` and `long/pay_*.json` (10 each) |
| `build_exp2.py` | Builds `exp2/<domain>_s<N>_<format>.json` (75 files); `--check` fails if a committed file is stale |
| `check_lexicon.py` | Checks a lexicon before freezing: same keys and `{slots}` as English, Hindi and Tamil in their own script only, Hinglish and Tanglish ASCII only (plus the rupee sign). `--drafts` checks the drafts folder |
| `templates/` | Travel templates `travel_017`-`019` with requests in every language |
| `gold/` | Travel gold chains per template and horizon |
| `trip_templates/`, `trip_gold/` | Trip templates `trip_001`-`005` and their gold per horizon |
| `long/` | The 20 long-horizon instances |
| `exp2/` | The 75 Experiment 2 instances: world, stages, requests in five languages, verification record, gold chain |

### `eval/`: running, scoring and analysis

| File | Purpose |
|---|---|
| `run_grid.py` | **The single entry point for every run.** Expands a config into episodes, builds the right tools and policy, checks the serving fingerprint, runs episodes in parallel, verifies them and appends JSON lines. Options: `--config`, `--resume`, `--workers`, `--out`, `--serving` |
| `verifier.py` | Travel verifier: early and late constraint survival with the step each was used, recovery |
| `trip_verifier.py` | Trip verifier: early, mid, carried and late constraints, binding swaps |
| `stages.py` | Stage attribution for Experiment 2 (loop, tool calling, planning, E1A, E1B, E2, E3) and per-episode outcomes |
| `exp2_summary.py` | Experiment 2 outcome tables with Wilson intervals; `--early-stop` applies the early-stop rule |
| `exp2_smoke.py` | Checks a mock run: gold succeeds and each fault fails exactly its constraints |
| `exp2_report.py` | Full RQ1/RQ2 evaluation: outcomes, logistic model, anchors, Pass^3, cost, constraint classes, cases |
| `rescore_exp2.py` | Rescores an Experiment 2 log by replaying its tool calls; `--waive` drops an invalid check |
| `rescore_long.py` | The same for the long-horizon logs |
| `drift.py` | Long-horizon drift types (entity swap, look-alike id, semantic), the RQ1 decision rule, RQ3 seam analysis, Wilson intervals |
| `metrics.py` | Quick aggregation helpers and handling of truncated and infra-error rows |

### `configs/`: one YAML file per run

A config names the tasks (`templates`), `languages`, `horizons` (travel and trip), `max_steps`, the
pinned `serving` block, `retry_truncated`, and one or more `cells` (policy, model, temperature,
`max_tokens`, `prompt_version`, thinking switch, `seeds`, optional `inject`).

| File | Run |
|---|---|
| `smoke_test.yaml`, `smoke_test_trip.yaml`, `smoke_test_long.yaml` | Mock runs of the travel, trip and long harnesses |
| `local_ollama_debug.yaml` | Laptop debugging with Ollama |
| `capability_gate.yaml`, `capability_gate_v2.yaml` | Travel gates v1 and v2 |
| `trip_pilot_en.yaml`, `trip_gate_v1.yaml`, `trip_main_v1.yaml` | Trip pilot, gate and 500-episode main run |
| `trip_small_qwen35_4b.yaml`, `trip_small_qwen35_9b.yaml` | Small-model runs (4B run; 9B not run) |
| `rq1_long_qwen36_27b_fp8.yaml` | Long-horizon RQ1 test on Qwen |
| `rq1_long_sarvam30b.yaml`, `diag_sarvam30b_noask.yaml` | Sarvam-30B run and a no-ask diagnostic (not run) |
| `rq3_seams_qwen36_27b_fp8.yaml` | RQ3 seams S1-S3 (built, not run) |
| `models/qwen36_27b_fp8.yaml` | The pinned Experiment 2 backbone |
| `exp2/<domain>_qwen.yaml` | Experiment 2 main runs, 225 episodes each, `retry_truncated: false` |
| `exp2/smoke_<domain>.yaml` | Experiment 2 mock runs (gold plus four faults on all 15 tasks) |

### `notebooks/`: Colab entry points

| File | Purpose |
|---|---|
| `exp2/exp2_<domain>.ipynb` | One notebook per Experiment 2 domain (cells in section 5) |
| `colab_runner.ipynb` | Runner for the travel, trip and long-horizon configs |
| `rq3_runner.ipynb` | RQ3 seam runs |
| `sarvam_runner.ipynb` | Sarvam-30B with SGLang |

### `tests/`: 631 pytest tests

| File | What it checks |
|---|---|
| `test_travel_env.py` | Gold files current and replaying; identical tool names and decisions at every horizon; every constraint changes the answer; never-first; lenient mode; injection and recovery |
| `test_trip_env.py` | Trip gold, horizon invariance, design rules, each fault caught only in its own class, checkout does not leak preferences |
| `test_long_env.py` | Long-horizon instances current, gold solves in every language and seam, faults typed correctly, seams localise only what they should, rescoring reproduces live scoring |
| `test_exp2_env.py` | Experiment 2 grid complete, gold succeeds, each fault fails only its constraints, formats nested with identical wording, files current, lexicon hygiene |
| `test_openai_compat_policy.py` | The real-model policy with a fake client: parsing, parallel calls, malformed arguments, empty and truncated replies, retries, step limit |
| `test_serving_guard.py` | The runner refuses to mix backbones in one log |

### `docs/`: design specifications (written before each experiment)

| File | Covers |
|---|---|
| `PHASE1_SPEC.md` | Travel environment, templates, gold, injection |
| `TRIP_SPEC.md` | Trip domain, horizon levels, pilot rule, small-model runs |
| `LONG_SPEC.md` | Shop and pay domains, drift definitions, RQ1 decision rule, RQ3 seams |
| `EXP2_SPEC.md` | Experiment 2 design, stage attribution, scoring rules and every dated deviation (sections 10.1-10.5) |

### `results/` and `runs/`

| Folder | Contents |
|---|---|
| `results/*.json` | Condensed results per experiment (committed); see section 1 |
| `runs/*.jsonl` | Raw episode logs, one JSON line per episode with the full transcript (gitignored; kept on Drive and the laptop). `*.rescored.jsonl` and `*.rescored_waive.jsonl` are rescored copies |

---

## 8. How to add or change things

**A new Experiment 2 language or wording fix (before a run only)**
1. Edit or add `env/exp2/lexicon_src/<domain>_<lang>.py`.
2. `python -m tasks.check_lexicon` until it reports no problems.
3. `python -m tasks.build_exp2`, then `python -m pytest -q`.
4. Never change a frozen task after a model has seen it; record any deviation with a date in the spec.

**A verifier fix after a run**
1. Fix the domain's `verify()` and add a test.
2. Rescore with `eval/rescore_exp2.py` (or `rescore_long.py`); never rerun the model to fix scoring.
3. Apply the fix to every language and report the original numbers alongside.

**A new run**
1. Copy the closest config, change `run_name`, and keep the `serving` block pinned.
2. Run the matching smoke config first, then the real config on Colab.

**A failure-injection run (RQ4)**
Add an `inject` block to a cell, for example
`inject: {error_type: not_found, at_tool: pay_bill, message_language: hi}`. Error types are
`transient`, `not_found` and `validation`; prefer `at_tool` over `at_step`.

---

## 9. Rules this repo follows

- **Secrets:** the GitHub token is kept in Colab Secrets as `GITHUB_TOKEN`; API keys go in `.env` or
  Colab Secrets. Never paste a key into a cell or commit it.
- **Pre-specification:** tasks, rules and analyses are frozen before the model sees them, and every
  later change is dated in the spec.
- **One backbone per log:** the serving fingerprint is checked on every resume.
- **Scoring:** first attempt only; a cut-off reply is a failure, never retried; endpoint errors are
  retried and never scored.
- **Code style:** ASCII-only source files; comments only where the logic is not obvious.
- **Workflow:** GitHub is the source of truth for code. Raw logs live on Drive and the laptop, and
  condensed results are committed to `results/`.
