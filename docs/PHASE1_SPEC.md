# Phase 1 Spec: Environment, Tasks, Gold, Injection

Status: **draft, 28 Sep 2026.** Travel domain implemented and tested (33 tests). Shop and
records domains specified here, not yet built. Freeze this spec before Phase 3 (language
authoring); after that, changes to tools or templates invalidate authored text.

Cross-references are to `Project_Detail_Document.md`.

---

## 1. Decisions locked in this phase

| Decision | Choice | Why |
|---|---|---|
| High-resource control language | **Chinese (Simplified)** | Enables the DeepPlanning ZH/EN external check on RQ1 (Section 8.12). Verified by translator back-translation plus the answerability check, since the author does not read Chinese |
| Languages per template | en, zh, hi, ta, hinglish (+ optional tanglish) | Section 8.3 |
| Horizons | 2, 4, 6, 8 | Section 8.2; extend to 10/12 only if the pilot needs it |
| Injection targeting | By tool (`at_tool`), not step index | A real model may take extra steps; a tool target hits the same logical point in every language |

---

## 2. How horizon grows without touching the request

Three things are held constant across horizons for a given template:

1. **The request text.** Byte-identical per language.
2. **The tool names and descriptions.** The agent sees the same 7 travel tools at every horizon.
3. **The final decision set.** The candidates visible when the agent chooses are the same at
   every horizon (`test_decision_set_identical_at_every_horizon`). Longer horizons are longer
   chains, not harder choices.

What changes is **which values each tool requires**. A value that only another tool can
produce forces that tool into the chain:

| Horizon | Required-value changes | Gold chain (travel_017) |
|---|---|---|
| 2 | search accepts city names and inline filters | search_flights → book_flight |
| 4 | search requires city **codes** | resolve_city ×2 → search_flights → book_flight |
| 6 | search loses inline filters; book requires a **hold_token** | resolve ×2 → search → filter_flights → get_seat_availability → book |
| 8 | availability requires **fare_class**; book requires **passenger_id** | h6 + get_fare_rules + get_user_profile |

The agent learns requirements from the schemas, never from error messages, so horizon stays
separate from recovery (RQ4).

**Residual confound, to report as a covariate:** schema text grows slightly with horizon
(more required parameters). Log schema token count per horizon and include it in the mixed
model if it varies materially.

### Interface modes (RQ2 control)

- **Strict:** the exact canonical form (English name, or code).
- **Lenient:** spelling and script variants of *the same form* resolve via
  `env/aliases/city_aliases.json` (Chennai, चेन्नई, சென்னை, 钦奈 → Chennai).
- **Lenient never shortens the chain.** A name is never accepted where a code is required
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

---

## 4. Tool inventory (15 tools, 3 domains)

### Travel: implemented

| Tool | Returns | Required from horizon |
|---|---|---|
| resolve_city(name) | code | 4 |
| search_flights(origin, destination, date, [depart_before, max_price]) | flights (sold-out excluded) | 2 |
| filter_flights(depart_before, max_price) | flights | 6 |
| get_fare_rules(flight_id) | fare_class | 8 |
| get_seat_availability(flight_id, [fare_class]) | seats, hold_token | 6 |
| get_user_profile() *(shared across domains)* | passenger_id (+ address_id, customer_id in other domains) | 8 |
| book_flight(flight_id, [hold_token], [passenger_id]) | booking (terminal) | 2 |

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
  "terminal_state": {"booking.flight_id": "6E212", "booking.price": 7900},
  "recovery_fallback": "AI440",
  "decoys": {"max_price": "SG118", "depart_before": "AI552", "objective": "AI440"},
  "gold_steps": [{"tool": "...", "args": {}, "returns": {}}]
}
```

- `returns` is optional and only for values later steps depend on. The replay test checks them.
- One file per (template, horizon). The gate for Phase 2 is that every gold file replays exactly
  (`test_gold_replays_exactly`).

---

## 6. Verifier outputs (per episode)

| Field | Meaning |
|---|---|
| success | Booked the correct answer **given the episode state** (with not_found injection, the best remaining option) |
| matches_gold_terminal | Booked exactly the gold answer |
| constraint_survival | Per constraint: route, date, depart_before, max_price, objective |
| fact_displacements | Arguments (flight_id, hold_token, fare_class, passenger_id) whose value never appeared in an earlier tool output |
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

| Position | h2 | h4 | h6 | h8 |
|---|---|---|---|---|
| early | search_flights | resolve_city | resolve_city | resolve_city |
| mid | search_flights | search_flights | get_seat_availability | get_seat_availability |
| late | book_flight | book_flight | book_flight | book_flight |

At h2, early and mid collapse, so report position only for h≥4.

**Message language:** 2 levels per task language, English (realistic) vs the task language
(localised). Catalogue in `env/data/error_messages.json` covers en, zh, hi, ta, hinglish.

---

## 8. Open items before freezing

1. Build the shop domain to the spec above. Resolve the delivery-estimate question (rule 3).
2. Implement validation as persistent spec drift.
3. Author the remaining templates. Target: 40 across domains, 20 in travel if records is dropped.
4. Rishabh to verify hi / ta / hinglish text; zh via translator back-translation.
5. Log schema token counts per horizon (confound check, Section 2).
6. Wire `api_policy.py` so the capability gate (h2, English) can run on real models.
