# Phase 1 Spec: Environment, Tasks, Gold, Injection

Status: **draft, 28 Sep 2026.** Travel domain implemented with late-binding constraints and
horizons 2–12; three templates with script-built gold; real-model policy; 106 tests. Shop and
records domains specified here, not yet built. Freeze this spec before Phase 3 (language
authoring); after that, changes to tools or templates invalidate authored text.

Cross-references are to `Project_Detail_Document.md`.

---

## 1. Decisions locked in this phase

| Decision | Choice | Why |
|---|---|---|
| High-resource control language | **Chinese (Simplified)** | Enables the DeepPlanning ZH/EN external check on RQ1 (Section 8.12). Verified by translator back-translation plus the answerability check, since the author does not read Chinese |
| Languages per template | en, zh, hi, ta, hinglish (+ optional tanglish) | Section 8.3 |
| Horizons | 2, 4, 6, 8, 10, 12 | Extended after gate v1 showed a ceiling at h8 (project doc 15.10) |
| Injection targeting | By tool (`at_tool`), not step index | A real model may take extra steps; a tool target hits the same logical point in every language |
| Thinking mode | ON | Gate v1 (Section 8) |
| Constraint classes | Early (applied when the flight is chosen) and late (committed in the final call) | Gate v1 showed every constraint was consumed by step ~5, so horizon added length but not constraint distance (project doc 15.10–15.11) |

---

## 2. How horizon grows without touching the request

Three things are held constant across horizons for a given template:

1. **The request text.** Byte-identical per language.
2. **The tool names and descriptions.** The agent sees the same 11 travel tools at every horizon.
3. **The final decision set.** The candidates visible when the agent chooses are the same at
   every horizon (`test_decision_set_identical_at_every_horizon`). Longer horizons are longer
   chains, not harder choices.

What changes is **which values each tool requires**. A value that only another tool can
produce forces that tool into the chain:

| Horizon | Required-value changes | Gold chain |
|---|---|---|
| 2 | search accepts city names and inline filters; book takes seat type and meal names | search_flights → book_flight |
| 4 | search requires city **codes** | resolve_city ×2 → search_flights → book_flight |
| 6 | search loses inline filters; book requires a **hold_token** | resolve ×2 → search → filter_flights → get_seat_availability → book |
| 8 | availability requires **fare_class**; book requires **passenger_id** | h6 + get_fare_rules + get_user_profile |
| 10 | book requires a **seat_id** and **meal_code** instead of names | h8 + get_seat_map + get_meal_options |
| 12 | book also requires a **document_id** and **payment_id** | h10 + get_travel_documents + get_payment_methods |

The agent learns requirements from the schemas, never from error messages, so horizon stays
separate from recovery (RQ4).

**Early vs late constraints (constraint distance).** Early constraints (time window, budget,
objective) are applied when the flight is chosen, around step 1–6. Late constraints (seat type,
meal) are committed only in the final booking call, at step *h*, so the number of steps they
must be carried grows with horizon (`test_late_constraints_committed_only_in_the_final_call`).
If state drift exists, late-constraint survival should fall with horizon faster in non-English
conditions than early-constraint survival does. The early constraints act as a within-episode
control for comprehension.

**Residual confound, to report as a covariate:** schema text grows slightly with horizon
(more required parameters). Log schema token count per horizon and include it in the mixed
model if it varies materially.

### Interface modes (RQ2 control)

- **Strict:** the exact canonical form (English name, or code).
- **Lenient:** spelling and script variants of *the same form* resolve via
  `env/aliases/city_aliases.json` (Chennai, चेन्नई, சென்னை, 钦奈 → Chennai; आइल सीट → aisle;
  ஜெயின் உணவு → jain).
- **Lenient never shortens the chain.** A name is never accepted where a code or id is required
  (`test_lenient_never_shortens_the_chain`). Otherwise the lenient control would change
  horizon and contaminate RQ2.

---

## 3. Template authoring rules

1. **Every constraint must change the answer.** Dropping any single constraint must change the
   correct terminal state. Otherwise constraint survival cannot be read off the outcome and a
   drifted agent looks correct. Each gold file lists a `decoys` map (constraint → the answer
   an agent would reach by losing it), checked by `test_every_constraint_changes_the_answer`.
   - Found by this rule: "cheapest morning flight under ₹8000" fails it. The budget never binds
     when minimising price. travel_017 is now "latest morning flight under ₹8000".
2. **One decoy per constraint in the data.** Each non-gold row in the domain data should exist
   to catch one specific lost constraint (see `env/data/flights.py` header).
3. **Per-item lookups only for the chosen item.** Never require a lookup per candidate
   (e.g. availability for every flight). That makes horizon depend on catalogue size.
   Comparison fields come from one list call; tokens come from per-item calls on the chosen
   item only.
4. **Request text is authored, not translated, for hi / ta / hinglish / tanglish.** zh is
   translated, then back-translated and answerability-checked.
5. **Script hygiene is tested.** Every non-Latin request must contain only its own script plus
   ₹ and CJK punctuation (`test_template_languages_present_and_script_clean`). This test
   exists because the first Tamil draft silently contained three Gujarati vowel signs.
6. **Record verification status per language** in the template's `verification` field.
   Freeze a template only when every language is `verified`.
7. **A valid recovery path must exist for every injection point.** Recorded as
   `recovery_fallback` in gold (ToolBench-X discipline, Section 8.6).
8. **Late constraints must be real choices, never listed first.** The requested seat type and
   meal must exist among several options and must not be the first one listed, so "took the
   first option" never looks like survival. Seat listing order is route-dependent for this reason.
   Found while building travel_018 (window seat, which was listed first).
9. **Gold is built by script, never by hand.** `python -m tasks.build_gold` derives the answer
   from the constraints alone, replays the chain, and refuses to write a file that breaks rules
   1, 2, 7 or 8. `test_gold_files_are_current` fails if a committed gold file is stale.

---

## 4. Tool inventory (19 tools, 3 domains)

### Travel: implemented

| Tool | Returns | Required from horizon |
|---|---|---|
| resolve_city(name) | code | 4 |
| search_flights(origin, destination, date, [depart_after, depart_before, max_price]) | flights (sold-out excluded) | 2 |
| filter_flights(depart_after, depart_before, max_price) | flights | 6 |
| get_fare_rules(flight_id) | fare_class | 8 |
| get_seat_availability(flight_id, [fare_class]) | seats, hold_token | 6 |
| get_user_profile() *(shared across domains)* | passenger_id (+ address_id, customer_id in other domains) | 8 |
| get_seat_map(flight_id) | seats with seat_id and seat_type | 10 |
| get_meal_options(flight_id) | meals with meal_code | 10 |
| get_travel_documents(passenger_id) | document_id | 12 |
| get_payment_methods() | payment_id | 12 |
| book_flight(flight_id, seat_type+meal or seat_id+meal_code, [hold_token, passenger_id, document_id, payment_id]) | booking with flight, price, seat type, meal (terminal) | 2 |

Templates built: **travel_017** (latest morning flight under ₹8000; aisle seat, Jain meal),
**travel_018** (cheapest flight after 17:00; window seat, vegetarian meal), **travel_019**
(earliest flight under ₹6000; aisle seat, diabetic meal).

### Shop / orders: to build

Example template (shop_004): *"Order the highest-rated A4 paper ream under ₹400 that can reach
my home by Friday."* Constraints: max_price, deliver_by, objective = max rating. Decoys: a
higher-rated ream over budget; a higher-rated ream that arrives late; a lower-rated ream
(objective).

| Tool | Returns | Dependency token |
|---|---|---|
| search_products(query, [max_price], [deliver_by]) | products with price, rating, and a delivery estimate at h2 only | |
| get_product_details(product_id) | variant_id, rating | variant_id |
| check_delivery(variant_id, address_id) | delivery_date, reservation_token | reservation_token |
| add_to_cart(variant_id, quantity) | cart_id | cart_id |
| place_order(cart_id, reservation_token, address_id) | order (terminal) | |

Chains: h2 search → place_order · h4 + get_product_details, get_user_profile · h6 +
check_delivery, add_to_cart · h8 + filter/sort step and a second profile field.
**To check when building:** the delivery estimate must reach the decision at every horizon
without a per-candidate lookup (rule 3). Options: search returns delivery estimates at all
horizons, or deliver_by becomes a search parameter at h≥4.

### Records / support: to build (optional third domain)

Example: *"Return the headphones I ordered last week, they stopped charging."* Constraints:
correct order (entity + time), request type (return, not replace), reason code.

| Tool | Returns |
|---|---|
| find_orders(customer_id, [query]) | orders |
| get_order(order_id) | items, status, return_window |
| file_request(order_id, item_id, request_type, reason_code) | ticket (terminal) |

Build shop first. Records only if the pilot shows two domains are not enough.

---

## 5. Gold file format

```json
{
  "task_id": "travel_017_h6", "template_id": "travel_017", "horizon": 6,
  "entities":    {"origin": "MAA", "destination": "DEL"},
  "constraints": {"date": "2026-08-22", "depart_before": "12:00", "max_price": 8000,
                  "objective": "latest_departure"},
  "late_constraints": {"seat_type": "aisle", "meal": "jain"},
  "terminal_state": {"booking.flight_id": "6E212", "booking.price": 7900,
                     "booking.seat_type": "aisle", "booking.meal": "jain"},
  "recovery_fallback": "AI440",
  "decoys": {"depart_before": "AI552", "max_price": "SG118", "objective": "AI440"},
  "gold_steps": [{"tool": "...", "args": {}, "returns": {}}]
}
```

Generated by `python -m tasks.build_gold` from `tasks/templates/*.json` (rule 9).

- `returns` is optional and only for values later steps depend on. The replay test checks them.
- One file per (template, horizon). The gate for Phase 2 is that every gold file replays exactly
  (`test_gold_replays_exactly`).

---

## 6. Verifier outputs (per episode)

| Field | Meaning |
|---|---|
| success | Correct flight **given the episode state** (with not_found injection, the best remaining option) *and* the requested seat type and meal |
| flight_correct | Early constraints only: the right flight |
| matches_gold_terminal | Booked exactly the gold terminal state |
| early_survival | Per early constraint: route, date, time window, budget, objective |
| late_survival | Per late constraint: seat_type, meal |
| early_first_use_step, late_commit_step | Step at which the flight choice was first acted on; step at which seat and meal were committed. Their difference over horizon is the constraint-distance axis |
| fact_displacements | Arguments (flight_id, hold_token, fare_class, passenger_id, seat_id, meal_code, document_id, payment_id) whose value never appeared in an earlier tool output |
| first_error_step, extra_steps | Deviation timing; steps beyond gold length |
| injected, injected_at_step, recovered | recovered = success on an injected episode |

Recovery rate must be conditioned on the same (template, horizon, language, model) cell
succeeding without injection (Section 8.6). `eval/metrics.py` does not condition yet. That
waits for real policies.

---

## 7. Error-injection catalogue

| Type | Behaviour | Eligible tools | Valid recovery | Status |
|---|---|---|---|---|
| transient | HTTP 429, one-shot | any | retry the same call | implemented |
| not_found | 0 seats; flight marked sold out for the rest of the episode | get_seat_availability, book_flight | switch to `recovery_fallback`, redo flight-specific steps | implemented |
| validation | spec drift: date format changes and **stays** changed | search_flights | reformat the argument | **one-shot placeholder; do not report as its own condition until built** |

**Injection positions** (by tool, per horizon):

| Position | h2 | h4 | h6 | h8 | h10 | h12 |
|---|---|---|---|---|---|---|
| early | search_flights | resolve_city | resolve_city | resolve_city | resolve_city | resolve_city |
| mid | search_flights | search_flights | get_seat_availability | get_seat_availability | get_seat_availability | get_seat_availability |
| late | book_flight | book_flight | book_flight | book_flight | book_flight | book_flight |

At h2, early and mid collapse, so report position only for h≥4.

**Message language:** 2 levels per task language, English (realistic) vs the task language
(localised). Catalogue in `env/data/error_messages.json` covers en, zh, hi, ta, hinglish.

---

## 8. Models and the policy interface

**Open-source models are the primary setup; hosted APIs are optional** (decided 28 Sep 2026).
Reasons: the gap-widening question needs models above the capability gate, not frontier
models; recent open models already run as multi-step multilingual agents (OmnilingualGAIA2
ran Gemma 4 31B and Qwen 3.6 27B / 35B-A3B); open weights are reproducible, free on Colab,
and required for the SFT ablation and any hidden-state probing. A frontier API model on a
stratified subset remains an optional robustness check.

One policy (`agent/policies/openai_compat_policy.py`) serves every model through an
OpenAI-compatible endpoint:

| Setting | Behaviour |
|---|---|
| System prompt | Versioned file `agent/prompts/system_v1.txt`, English, identical across languages; includes the session date so "tomorrow" is resolvable |
| Parallel tool calls | Only the first call is executed and kept in history |
| Unparseable arguments | Recorded as a validation error step; the model sees the error and continues |
| Text reply without a tool call | Ends the episode (`final_text` logged) |
| Endpoint failure | `InfraError` after retries; episode logged with `infra_error`, never scored, retried on `--resume` |
| Tool output encoding | JSON with real script (`ensure_ascii=False`), so localised errors reach the model as text, not escapes |
| Logged per episode | Full message history, per-turn reasoning, token usage, prompt version |

**Serving (vLLM, verified against the vLLM recipes, Sep 2026):**

| Model | Parsers | GPU memory |
|---|---|---|
| Qwen/Qwen3.6-27B-FP8 (official FP8) — **gate v2 backbone** | `--tool-call-parser qwen3_coder --reasoning-parser qwen3` | fits 40GB and 80GB A100 |
| Qwen/Qwen3.6-27B (BF16) — gate v1 only | same | 80GB only |
| google/gemma-4-31B-it | `--tool-call-parser gemma4 --reasoning-parser gemma4` + Gemma 4 tool chat template | 80GB (BF16) |

**A backbone is a model plus its exact weights, precision and serving stack.** Every condition a
backbone is compared on (languages, horizons, controls) must run on the identical backbone. Different
backbones are fine: the study uses several, and model is a random effect in the analysis. Precision
matters specifically here: quantization degrades non-Latin-script languages most (Marchisio et al.,
EMNLP 2024), so mixing BF16 and FP8 episodes of "the same model" would manufacture a language effect.

Enforcement: the run config's `serving` block pins model, revision, parsers and minimum GPU memory; the
notebook serves exactly that, refuses an undersized GPU, resolves the revision to a commit hash, and writes
`serving.json`. `run_grid --serving` stamps every episode with it and refuses to resume a log produced
under a different model, revision or vLLM version (GPU model differences only produce a note).
Colab's GPU varies by session (L4 24GB, A100 40GB, A100 80GB); choose each backbone's precision so it
fits every GPU it will run on, and never switch precision mid-study. Gate v1 (BF16) was a design pilot
and is not pooled with later runs.

**Thinking mode is a study-wide constant.** Both settings run in the capability gate; the one
chosen must then be fixed across every language, horizon and control. **Decided: ON** (first
gate, 28 Sep 2026: more Tamil/Hinglish episodes solved, fewer unneeded steps, reasoning traces
needed to locate failures; ~1,400 vs ~400 completion tokens per episode).

**Reading logs:** a key can appear more than once (infra failures followed by a successful
retry). Analyses keep the last scored row per `episode_key`.

---

## 9. Open items before freezing

1. Build the shop domain to the spec above. Resolve the delivery-estimate question (rule 3).
2. Implement validation as persistent spec drift.
3. Author the remaining templates (target 40 across domains), each with early and late
   constraints. Gate v2 decides whether the late-binding design works before scaling.
4. Rishabh to verify hi / ta / hinglish text, including the new seat and meal clauses; zh via
   translator back-translation.
5. Log schema token counts per horizon (confound check, Section 2). Schema text grows more at
   h10/h12, so this matters more now.
6. ~~Run the capability gate and fix the thinking setting~~ done (ON). Run gate v2
   (`configs/capability_gate_v2.yaml`).
7. Collect a final user-facing reply after the terminal tool call (needed for RQ5 output
   language fidelity); the loop currently ends at the booking.
