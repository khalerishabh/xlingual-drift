# Long-horizon domains: shop and pay (RQ1 final test, RQ3)

Status: design fixed 26 Oct 2026, before any model run on these domains.

## Why

The trip main run (500 episodes, Qwen3.6-27B) found no language x horizon
interaction (p = 0.63). This is the final RQ1 test, in two new domains
built to provoke the drift kinds the thesis names, at 30-40 steps per
episode: realistic agent load with deliberate pressure, not a harder
puzzle. If RQ1 is positive here, RQ2 (lenient interface, oracle plan) is
run on the same instances; if not, the thesis reports RQ1 as negative.

## Domains

**shop** (36 gold steps): Diwali shopping for four family members (self,
Papa, Mummy, Didi). Each person gets one item with a category, size, colour
and budget, the highest-rated that fits; two people's items go to Nani's
house in Pune, everything must arrive by a date, two items are gift-wrapped;
an item from the last order is exchanged for another size; the best
eligible coupon; pay by UPI.

**pay** (32 gold steps): month-end household payments. Six bills under an
amount rule (full if at most X, else minimum due) and a running-balance rule
(savings until a bill would breach a floor, then that bill and all later
ones from salary), a remark on each; rent by NEFT; pocket money to Didi by
IMPS; a monthly standing instruction to Mummy; a budget tag for every bill
payment; OTP-confirmed batch.

Ten instances per domain, generated from seeds taken in order and kept only
if they pass every rule (`tasks/build_long.py`). Each instance has its own
world. Requests are written once per language as a template
(`env/long/lexicon/*.json`) and filled with the instance's values, in a
list format that needs no inflection of slot values.

## Drift pressure built in

| Kind | shop | pay |
|---|---|---|
| Entity (binding) | four people with distinct sizes, colours, addresses, gift wrap | two electricity connections (home, Nani), two mobiles, account rule per bill, tag per transaction |
| Entity (near-identical ids) | the answer's product and variant each have a twin one digit-pair apart in the same listing | consumer numbers and mobile numbers one digit-pair apart; payees Kavya Sharma x2, Vinod Deshpande / Deshmukh, Sunita / Sunil Sharma |
| Semantic (label survives, value does not) | `confirm_size` / `confirm_colour` sit next to an opaque variant id | a remark sits next to the biller id |
| Carried state | addresses and gift recipients bound to cart lines created 10-30 steps earlier | the floor rule's running balance and its one-way switch; tags reference transaction ids 15-25 steps back |
| Re-grounding | at the first cart review one person's item goes out of stock; the replacement must re-apply that person's constraints (stated ~25 steps earlier) | the IMPS transfer to Didi fails with a limit error; the NEFT retry must keep amount, account and remark |

Authoring rules (enforced by each domain's `check_rules`): the answer is
never listed first; every trap row exists (over-budget top-rated item, item
missing the colour, item that arrives late, twin ids); the coupon optimum
is unique and is not the most generous-looking coupon; the floor rule
switches between the second and fifth bill; the amount rule binds both
ways.

## Drift definitions (eval/drift.py)

Unit: one scored constraint in one episode, with its class (selection,
attribute, binding, global), the step it was committed at, and its
distance (commit step / episode length). A failed constraint gets one type:

- **entity_swap**: the wrong value belongs to another entity in the task
- **neighbour_id**: the wrong id is the right one with one digit pair
  swapped, or a near-identical payee name
- **semantic**: the agent restated the user's value correctly (confirm
  label, remark) but bound it to the wrong item
- **other**

**Strict state drift** = a failed constraint where the agent had acted on
the right item earlier (tool-call evidence: it fetched the right variant,
bill or payee, then committed a different one).

## Decision rules (fixed before any run)

**RQ1** is positive for language L if, in the model
`fail ~ language x distance + class (+ domain)` (logistic, standard errors
clustered by episode, English reference, global constraints excluded), the
L x distance coefficient is > 0 with p < 0.05, **and** L's typed drift rate
(entity_swap + neighbour_id + semantic per 100 constraints) exceeds
English's. RQ1 is positive overall if it is positive for at least one of
hi, ta, hinglish. Then RQ2 runs on the same 20 instances.

**RQ3** (`configs/rq3_seams_qwen36_27b_fp8.yaml`, `notebooks/rq3_runner.ipynb`):
seams S1 (request in L), S2 (+ tool outputs in L), S3 (+ errors in L), with
English from the RQ1 run as S0. Contrasts are paired by instance (exact
McNemar). Every failed constraint gets a stage from the failure taxonomy:
entity handling, state carryover (semantic or not), recovery /
re-grounding, reasoning / comprehension. Hypotheses: removing the
tool-output crossing (S1 -> S2) helps; failures concentrate in entity
handling and state carryover rather than comprehension.

## Runs

| Config | Model | Episodes |
|---|---|---|
| `rq1_long_qwen36_27b_fp8.yaml` | Qwen3.6-27B-FP8, thinking on (same backbone as the trip runs) | 20 x 5 languages = 100 |
| `rq3_seams_qwen36_27b_fp8.yaml` | same | 20 x 4 languages x 3 seams = 240 |
| `rq1_long_sarvam30b.yaml` | Sarvam-30B (`sarvamai/sarvam-30b`), SGLang, `glm45` parsers | 100 |

Temperature 0.6 everywhere; 80-step limit; 64k context.

## Limits

- 10 instances per domain is small; the constraint-level model (about 35
  constraints per episode) carries the analysis, with episodes as clusters.
- Requests are templates; Rishabh verifies each language's template once
  (hi, ta, hinglish), zh by back-translation.
- Sarvam serving follows the model card (SGLang); the notebook checks one
  tool call before spending GPU time.
