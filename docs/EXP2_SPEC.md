# RQ1 Experiment 2: Multi-domain, multi-horizon evaluation (Qwen3.6-27B only)

Project: Cross-lingual state drift in LLM agents (repo: github.com/khalerishabh/xlingual-drift).
Read `claude/Project_Detail_Document.md` in the Project for full background. This spec defines the next experiment only.

## 0. Context and goal

- Already done: travel gates (travel_017-019, h2-h12), trip pilot, trip gate v1, trip main run v1 (trip_001-005, h14/17/24/28, 500 episodes, Qwen3.6-27B-FP8).
- Research questions in scope: RQ1 (performance and drift across languages and horizons), RQ2 (where failures arise), RQ4 (recovery). RQ3 (lenient interface / oracle plan controls) is out of scope.
- **Revised RQ1:** measure *overall* drift across three stages (planning, tool calling, execution) and compare English, Indic (Hindi, Tamil) and code-mixed (Hinglish, Tanglish) conditions across short, medium and long horizons.
- This experiment runs **before** any RQ3 work.

## 1. Design at a glance

| Factor | Levels |
|---|---|
| Domains (5) | Travel, Shopping/Commerce, Food Order, Payment, Banking |
| Scenarios | 5 per domain = 25 scenarios |
| Horizon formats (3) | Short (1-2 stages), Medium (4-5 stages), Long (6+ stages) |
| Languages (5) | English (en), Hindi (hi), Tamil (ta), Hinglish, Tanglish |
| Task instances | 25 x 3 x 5 = **375** |
| Model | Qwen3.6-27B-FP8 (the backbone of every earlier run) |
| Seeds | 3 per task instance |
| Episodes | 375 x 3 = **1,125** |

Interaction mode: **fully autonomous**. The agent gets one request and must finish without asking the user anything. There is no user simulator. Any reply to the user before the final commit counts as "premature stop" (a failure).

## 2. Definitions

- **Stage:** one sub-goal of the task (e.g. book the outbound flight, book the hotel, pay the bill). A stage needs one or more tool calls.
- **Horizon:** number of tool calls in the gold trajectory. Report both stage count and call count.
  - Short: 1-2 stages, about 2-6 calls
  - Medium: 4-5 stages, about 8-14 calls
  - Long: 6+ stages, about 17-28 calls (same scale as the existing trip domain)
- **Constraint:** any requirement in the request that changes the correct outcome (time window, budget, objective such as cheapest/earliest, per-person preference, account, amount).
- **Commitment:** the point where a constraint's value is sent in a state-changing call (book, order, pay, transfer, confirm).
- **Carry distance:** steps between when a value becomes available (request = step 0, or tool output at step j) and its commit step.

## 3. How the three horizon formats are built (important design choice)

Previous experiments held the **request text identical** across horizons and let the environment require more calls. In this experiment the formats differ in **number of stages**, so the request itself differs. That is more natural, but longer requests also mean more non-English text, which on its own lowers accuracy (MAPS). Control for it with a **nested design**:

1. Each scenario has a **Long** request with all stages.
2. **Medium** = a subset of the Long stages; **Short** = a subset of the Medium stages. Same entities, same wording for shared clauses.
3. **Anchor constraints:** 2-3 constraints appear in all three formats, worded identically, and are committed in the **final** state-changing call. Their carry distance grows with format. Drift analysis uses the anchor constraints, since only they are comparable across formats.
4. Log request length (tokens) per instance and use it as a covariate.
5. Optional, if time allows: also apply the old method (same request, environment-controlled horizon) to 1 scenario per domain, as a check.

## 4. Building the tasks from BabelArena

Source: `huggingface.co/datasets/Qwen/BabelArena` (Apache-2.0; cite BabelArena and the source benchmarks: VitaBench, DeepPlanning, tau-bench / tau2 / tau-knowledge).

BabelArena is evaluation-only: it translates 4 benchmarks into 23 languages, uses an LLM user simulator (Gemini-3.5-Flash) and LLM judges (GPT-5.6-Sol) for VitaBench, tau3 and ClawEval, and rule-based grading only for DeepPlanning. Its Hindi/Tamil translations were quality-rated by an LLM, not native speakers. We use it as a **source of realistic scenarios, entities, policies and data**, not as-is.

### 4.1 Where each domain's scenarios come from

| Our domain | BabelArena source to read |
|---|---|
| Travel | VitaBench online travel (OTA), DeepPlanning travel, tau3 airline |
| Shopping/Commerce | tau3 retail, DeepPlanning shopping, VitaBench in-store |
| Food Order | VitaBench delivery |
| Payment | No direct source. Build Indian-context flows: UPI transfer, bill pay, wallet top-up, merchant payment, refund. Borrow policy style from tau3 banking/retail |
| Banking | tau3 banking (+ banking_knowledge documents for policy rules) |

### 4.2 Conversion rules (BabelArena task -> our task)

1. Rewrite multi-turn simulated-user tasks as **one self-contained request**. All information the user would reveal over turns goes in the request.
2. Keep realistic entities and policies; replace foreign entities with Indian ones where natural (cities, restaurants, banks, rupee amounts).
3. Apply our authoring rules (enforced by the gold builder):
   - Every constraint changes the answer, and each has a **decoy** (the outcome if that constraint is lost).
   - A requested option is **never listed first** in any tool output; assigning options in listing order must be wrong.
   - At least one **coupled constraint** per long task (e.g. a joint budget across two items), since this was the main language-sensitive failure in trip gate v1.
   - Near-identical IDs next to the answer in long tasks (e.g. 6E4512 / 6E4521) to provoke carried-fact errors.
   - A **recovery fallback** for each task (needed for RQ4).
   - Tool errors never mention user preferences.
4. Do not copy BabelArena's LLM user simulator or LLM judges.

### 4.3 Language authoring (adopt BabelArena's field types)

- **PRESERVE** (identical in all languages): tool names, argument names, JSON keys, IDs, codes, enum values, dates, times, amounts.
- **TRANSLATE-CANONICAL:** cities, product names, dishes, seat/meal/room types, bank and account labels. Translate once into a shared table `tasks/canonical_terms.json` and reuse everywhere.
- **TRANSLATE-FREE:** request prose, written fresh per language.
- Authoring and checks:
  - hi, ta, Hinglish, Tanglish: written or rewritten by Rishabh (native authoring is the contribution; LLM drafts allowed, final text must be his).
  - Automatic checks before freezing: script hygiene (no stray characters from other scripts), every constraint present (answerability), canonical terms used consistently.
- Freeze each batch before any model sees it. Templates are never chosen or edited based on model results.
- Text-search tools: if a tool searches by name (products, dishes), decide deliberately whether it accepts Indic/Romanised queries. BabelArena found 54-69% empty searches in low-resource languages from lexical matching. Recommended: search takes canonical English names or IDs from a listing tool, so we measure the agent, not the search function.

## 5. Harness and environment

### 5.1 Components (reuse what exists; add domains)

| Component | Status | Notes |
|---|---|---|
| Tools per domain | Travel/trip built; 4 domains new | Deterministic Python over in-code tables, BFCL-style JSON schemas, strict argument validation |
| Gold builder | Exists for travel/trip | One per domain; derives answer and decoys from constraints alone; replays each chain; refuses templates that break rules |
| Agent loop | Built (`agent/react_loop.py`) | Plain ReAct: one tool call per turn, history is the only memory. No planner/memory/reflection modules |
| Policy | Built (`OpenAICompatPolicy`) | Unchanged |
| System prompt | `system_v1.txt` | Add a versioned `system_v2.txt` stating: complete the task without asking the user; if impossible, explain why. Same prompt for every language |
| Failure injector | Built | Errors needed in all 5 languages (add Tanglish messages; existing zh messages unused) |
| Verifier | Built for trip | Generalise: per-constraint outcome, class, commit step, decoy matched, fact displacement |
| Runner | Built (`eval/run_grid.py`) | Keep task-wise order (template -> horizon -> language -> seed), resumable, refuses mixed backbones |
| Event logger | To build (post-hoc) | Derived from raw logs; see 5.3 |

### 5.2 Planning observability (decision needed)

There is no separate planner. To attribute failures to the planning stage deterministically, choose one:
- **(a) Plan tool:** add `submit_plan(stages: [...], constraints: {...})` that must be called first; the verifier checks the plan against gold. Most measurable, but changes agent behaviour (identically for all conditions).
- **(b) Infer from behaviour:** planning error = first deviation in tool order / missing stage, plus constraints absent from the first reasoning turn. No behaviour change, weaker evidence.
Recommendation: (b) for the main run; (a) on a small subset as a check.

### 5.3 Execution logger (events derived from raw logs)

One event per line, keyed by episode and turn:
`episode_start, reasoning, tool_call, observation, error, state_update, recovery_attempt, language_transition, final, episode_end`.
- `reasoning`: text, tokens, script mix, values mentioned (IDs, times, amounts)
- `tool_call`: tool, args, gold tool at this step, args diff vs gold
- `observation`: result size, new values introduced
- `state_update`: values committed and values learned so far (derived from actions, never asked of the model)
- `recovery_attempt`: retry same / modified args / alternative / give up
- `language_transition`: request -> reasoning -> tool output -> reply language changes (word-level language ID needed for Hinglish/Tanglish)
Raw logs are never modified; a versioned script derives events.

### 5.4 Colab runners: one notebook per domain (5 files)

| Travel | Shopping | Food Order | Payment | Banking |
|---|---|---|---|---|
| `exp2_travel_qwen.ipynb` | `exp2_shopping_qwen.ipynb` | `exp2_food_qwen.ipynb` | `exp2_payment_qwen.ipynb` | `exp2_banking_qwen.ipynb` |

All in `notebooks/exp2/`. Each domain notebook runs 5 scenarios x 3 formats x 5 languages x 3 seeds = **225 episodes**.

Rules so the 5 notebooks stay comparable:
1. **Notebooks are thin.** They only: clone/pull the repo, check the GPU, start the server, run `eval/run_grid.py` with one config, summarise, and save logs. All environment, agent, prompt and verifier code lives in the repo, never in a notebook.
2. **One serving config shared by all 5 notebooks:** `configs/models/qwen36_27b_fp8.yaml` pins model id, weights revision, precision, server version, parsers, context length, thinking setting, temperature and minimum GPU memory. Domain notebooks import this file and never override it, so all 5 domains run on the identical backbone.
3. **One run config per notebook:** `configs/exp2/<domain>_qwen.yaml` lists only the domain's templates, the 3 formats, 5 languages and seeds.
4. **One log per notebook:** `runs/exp2/<domain>_qwen.jsonl` on Drive. The runner stamps the serving fingerprint on every episode and refuses to extend a log produced under a different backbone; the analysis also refuses to merge logs with different fingerprints across domains.
5. **Same order inside each notebook:** task-wise (scenario -> format -> language -> seed), resumable with `--resume` across Colab disconnects.
6. Every notebook starts with a serving check (one tool call parsed, reasoning separated) and stops if it fails.
7. A shared summary step (`eval/exp2_summary.py`) merges the 5 logs into one results table for analysis.

Optional, not counted in the 5: one BabelArena notebook, `babelarena_qwen.ipynb` (section 6.5).

## 6. Metrics

### 6.1 Primary (fix before running)
1. **Task accuracy** (all constraints correct) by language x format.
2. **Drift slope:** language x horizon interaction on **anchor-constraint** drift (held then lost), mixed-effects logistic:
   `drift ~ language * horizon + domain + log_request_tokens + (1|scenario) + (1|episode) + (1|seed)`.

### 6.2 Stage attribution (deterministic, one primary stage per failed constraint)
| Stage | Rule |
|---|---|
| Comprehension / planning | Constraint never held: absent from first reasoning turn and never used correctly before commit; or a required stage is skipped / tool order deviates from gold |
| Tool calling | Schema error, unparseable call, hallucinated tool, argument value in wrong language/script, wrong tool for the stage |
| Execution (drift) | Constraint held (correct value in reasoning or an earlier correct call), then committed wrong. Subtypes: request-constraint drift, observation drift (value differs from what the tool returned), binding drift (right value, wrong person/item), fabrication (value never seen in any output), execution gap (reasoning at commit turn names right value, action sends another) |
| Termination | Asked the user, stopped early, looped, hit step limit |

"Held" is checked only on exact values (IDs, codes, times, amounts), never on free-text words, so labels are reproducible.

### 6.3 Secondary
- Constraint satisfaction rate (partial credit)
- Gap metrics: absolute and relative gap vs English; code-mixing penalty (hi - Hinglish, ta - Tanglish); script effect (Hinglish vs Devanagari Hindi, Tanglish vs Tamil script)
- Pass^3 (all three seeds succeed)
- First-error step; extra steps; tokens per episode by language
- Register defection rate (needs a final reply turn after commit): reply language/script differs from the user's; for Hinglish/Tanglish, a pure English or pure native-script reply is a defection. Do not reuse BabelArena's consistency metric, which counts code-mixing as an error.
- RQ4: recovery rate after injected errors (English vs localised error message), conditioned on tasks solved without injection

### 6.4 Two evaluation layers on our tasks

Every episode is scored twice from the same log:
1. **Our evaluation (existing):** deterministic verifier: task accuracy, per-constraint outcome with decoys, constraint class and commit step, fact displacement, stage attribution and drift (6.1-6.3).
2. **BabelArena-style evaluation:** the metrics BabelArena reports, computed on our tasks so results are directly comparable to theirs:
   - **Pass^1** (average success over the 3 seeds) and **Pass^3** (all 3 seeds succeed)
   - **Language consistency (LC):** whether all user-visible agent text stays in the user's language. BabelArena uses an LLM judge (Gemini-3.7-Flash, prompt in their Appendix A). We report LC two ways: (a) a deterministic version (script ratios plus word-level language ID), primary; (b) their judge prompt with an open model, secondary, labelled as such. For Hinglish/Tanglish, mixed-language text is the *correct* target, so their definition (which counts code-switching as an error) is reported only for en/hi/ta; code-mixed conditions use our register defection rate instead.
   - **Token cost relative to English** on the same task (their Table 6 style): constant input, total input, total output, turns.
   - **Error taxonomy mapping:** map our deterministic stage labels onto BabelArena's taxonomy (Outcome, Reasoning, Planning, Tool Use, Control Flow, Memory, Multilingual) so the distributions can be compared. Our labels come from rules, theirs from an LLM annotator; say so.

### 6.5 External evaluation on the BabelArena benchmark itself

Run Qwen on a subset of BabelArena **as released**, through their harness (`github.com/QwenLM/BabelArena`, `./bench run -b <family> -l <lang> --agent-model <model>`), pointing it at our vLLM endpoint.
- **Languages:** en, hi, ta only (BabelArena has no Hinglish or Tanglish).
- **Family:** DeepPlanning first (rule-based grading, no user simulator; only an LLM step that converts free-text plans to the required format). tau3-Bench and VitaBench need an LLM user simulator and an LLM judge; add them only if a judge/simulator model is available, and report that dependency.
- **Size:** DeepPlanning standard subset (travel 60 + shopping 60 tasks) x 3 languages x 3 trials. Use a smaller stratified sample if compute is short.
- **Metrics:** their Pass^1, Pass^3 and LC, exactly as their harness computes them, plus our token-cost ratios.
- **Purpose:** (1) shows the model's en/hi/ta gap on an established benchmark, (2) positions our results next to BabelArena's frontier-model numbers, (3) answers the "synthetic environment" criticism. It does not test drift (no gold trajectories, horizon not controlled).
- **Order:** after the main run on our tasks.

## 7. Model

### 7.1 Serving (one backbone = model + weights revision + precision + serving stack; never mixed)
| Model | Notes |
|---|---|
| Qwen/Qwen3.6-27B-FP8 @ e89b16eb | vLLM 0.30.0 in a Python 3.12 venv, `--tool-call-parser qwen3_coder --reasoning-parser qwen3`, thinking on, temperature 0.6, max_tokens 16384 |

The same backbone as every earlier run, so Experiment 2 results are directly comparable with the travel gates, trip main run and RQ1 long run.

### 7.2 Scope decisions (27 Oct 2026)
- **One model: Qwen3.6-27B-FP8.** Sarvam-30B was dropped after its first long-horizon run (rq1_long_sarvam30b, 27 Oct 2026): 0/99 episodes in every language including English. It stopped to ask the user for ids the tools provide (63/99 episodes made no tool call), described calls in text instead of making them, gave up after one empty search, and invented ids. Reported as a capability-floor result, with Qwen3.5-4B. Gemma 4 31B also dropped.
- **Chinese dropped.** Consequence to state in the paper: without a high-resource non-English control, a gap cannot be split into a "non-English" part and a "low-resource" part. Hindi partly fills that role, and earlier Chinese results from the travel, trip and long runs are cited as context.
- **Language groups for Qwen:** native = English; non-native = Hindi, Tamil; code-mixed = Hinglish, Tanglish.
- **No pilot.** The design goes straight to the main run (section 8). Earlier runs already established that the task scale (trip, 14-28 calls; shop and pay, 30-40 calls) is within this model's range in English (trip 84%, long 65% on state). The safeguard is an early-stop rule inside the main run instead of a separate pilot (step 7).

### 7.3 Open decisions
- Planning observability: option (a) or (b) in 5.2 (recommended: b).
- Whether to add the final reply turn now (needed for register defection) or in a follow-up run.

## 8. Evaluation steps (in order)

Freezing follows the same practice as every earlier run: design, decision rules and task texts are fixed before the model sees any of them, and never edited because of a result.

1. **Spec freeze:** write this design into `docs/EXP2_SPEC.md` with metric definitions, the primary analysis and the early-stop rule, dated, before any run.
2. **Environment build:** tools for Shopping, Food Order, Payment, Banking; extend Travel. Reuse the trip, shop and pay environments as the base. Unit tests per tool.
3. **Full English authoring:** 25 scenarios x 3 formats; gold for all 75; the gold builder enforces every authoring rule; replay tests pass.
4. **Mock smoke test:** scripted policy injects each fault type; each must be caught only in its own class/stage. This tests the harness, not the model.
5. **Language authoring:** canonical-term table first, then hi/ta/Hinglish/Tanglish by Rishabh; automatic checks; **freeze**.
6. **Serving check:** one tool call parsed and reasoning separated before the run starts (built into each notebook).
7. **Main run:** 5 notebooks, one per domain, each 225 episodes; 375 instances x 3 seeds; task-wise order, resumable across Colab sessions. **Early-stop rule (proposed 27 Oct 2026, awaiting approval):** each domain notebook first runs English, seed 1, on all 15 instances (all scenarios and formats; run_grid schedules them first). If their success rate is below 0.3, stop the domain and report it. (The earlier wording, "first 45 episodes", would have covered one scenario only under task-wise order.) Tasks are never simplified in response.
8. **Verify and derive events:** verifier output + event logs from raw logs; merge the 5 logs (fingerprints checked).
9. **Analysis, our evaluation:** primary metrics first (as pre-specified), then stage attribution, then secondary metrics.
10. **Analysis, BabelArena-style evaluation on our tasks:** Pass^1, Pass^3, LC, token ratios, taxonomy mapping (section 6.4).
11. **External BabelArena run:** DeepPlanning subset, en/hi/ta, through their harness (section 6.5).
12. **RQ4 run:** failure injection (transient, not-found, validation) at early/mid/late positions on the long format, English vs localised error messages.

## 9. Workload estimate

- Gold trajectories: 75 (25 scenarios x 3 formats).
- Texts to author: 75 English + 75 x 4 other languages = 375 request texts (300 non-English).
- Episodes: 1,125 (main run only, RQ4 extra); 225 per notebook across 5 notebooks.
- External BabelArena run: about 120 tasks x 3 languages x 3 trials = 1,080 episodes (DeepPlanning standard subset), or less with a stratified sample.
- Colab notebooks: 5 for our tasks + 1 optional for BabelArena.
- New tools: roughly 8-15 per new domain.

## 10. Build record (27 Oct 2026)

Steps 2-4 done; step 5 drafted. Everything below is in the repo and covered by `tests/test_exp2_env.py`.

### 10.1 Per-domain stage layout

| Domain | Short | Medium | Long | Gold calls (S/M/L) | Anchors (final call) |
|---|---|---|---|---|---|
| Travel | outbound, submit | + return, hotel, rooms | + budget (coupled), cab (carried), tickets | 6 / 12 / 14 | per-traveller seat type, meal |
| Shopping | item_self, checkout | + item_mother, coupon | + item_father, item_sister (coupled pair budget), gift, exchange | 7 / 12 / 24 | payment card, delivery slot |
| Food Order | restaurant, dish_self, checkout | + dish_papa, dish_mummy, offer | + dish_didi, sides, dessert (coupled total), slot | 7 / 13 / 18 | delivery address, payment card |
| Payment | bill_1, submit | + bill_2, bill_3, rent | + bill_4-6, pocket, wallet (carried), merchant | 7 / 13 / 25 | processing date, notify contact |
| Banking | dispute, submit | + card_block, fd_open | + card_replace (carried), card_limit, rd_open (coupled), nominee (carried), cheque_stop | 6 / 10 / 18 | confirmation channel, home branch |

Travel long is 14 calls, below the 17-28 target in section 2, because every travel format uses the shortest trip tool level (English city names, no holds). Moving all three travel formats to the 17-call level adds `resolve_city` and attraction-id lookups (+3 calls each) without changing the request.

### 10.2 Files
- Environments: `env/exp2/{travel,shopping,food,payment,banking}.py`, shared machinery `env/exp2/core.py`, registry `env/exp2/registry.py`.
- Instances: `tasks/exp2/<domain>_s<N>_<format>.json` (75), built by `python -m tasks.build_exp2`; `--check` fails on stale files.
- English lexicons: `env/exp2/lexicon_src/<domain>_en.py`. Drafts for hi, ta, Hinglish, Tanglish: `env/exp2/lexicon_drafts/<domain>_<lang>.py` (LLM drafts, not loaded). After review, move a file to `lexicon_src/`, set its `VERIFICATION`, run `python -m tasks.check_lexicon` and `python -m tasks.build_exp2`, then freeze.
- Runner: `eval/run_grid.py` (exp2 instances, refuses to start if a configured language has no authored request), mock policy `agent/policies/exp2_mock_policy.py`, prompt `agent/prompts/system_v2.txt`.
- Configs: `configs/exp2/<domain>_qwen.yaml` (225 episodes each), `configs/exp2/smoke_<domain>.yaml`, `configs/models/qwen36_27b_fp8.yaml`.
- Notebooks: `notebooks/exp2/exp2_<domain>.ipynb` (phase 1 = English seed 1, early-stop check, phase 2 = full grid).
- Analysis: `eval/stages.py` (stage attribution, 6.2), `eval/exp2_summary.py` (outcomes, early-stop check), `eval/exp2_smoke.py` (mock smoke check).

### 10.3 Checks passed
- Gold succeeds on all 75 instances; each domain has 4 scripted faults and each fails exactly its own constraints (300 fault replays), through the real runner as well as in unit tests.
- Formats are nested: short request lines are a subset of medium, medium of long, in every language.
- Never-first and lookalike rules asserted by each domain's `check_rules`; coupled constraints are asserted to change the answer.
