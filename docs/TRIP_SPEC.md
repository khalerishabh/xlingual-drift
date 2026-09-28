# Trip domain: long-horizon family trip organiser

Status: design fixed 28 Sep 2026, before any model run on this domain.
Everything below the "Fixed in advance" heading is not changed after
results are seen, except through the English-only difficulty rule.

## Why a second domain

Gate v2 on the travel domain (Project Detail Document 15.12) showed the
first drift-shaped failure, but the task was too light to measure a slope:
English and Chinese at 1.00 everywhere, at most ~5 steps between choosing a
value and committing it, 2 carried values, small tool outputs, and the
switch from seat words to seat ids at h10 confounded with horizon. The trip
domain adds realistic agent load: more steps, more constraints, several
people, verbose outputs with near-identical ids, and facts that must be
copied from one tool output into a later call.

## Task

One request books a whole family trip: Chennai to Jaipur and back for the
user and both parents. Outbound and return flights under a joint budget, a
hotel with filters and two rooms, an airport cab timed to the landing,
attraction tickets, and per-traveller seats, meals and ticket categories.
Everything is confirmed in one final `confirm_trip` call.

trip_001 (English): cheapest non-stop outbound before noon; earliest
non-stop return after 6 pm with all six tickets within 30,000; highest-rated
hotel within 3 km of Hawa Mahal with a lift and veg breakfast; a double
room for the parents and a single for the user; an SUV from the airport at
landing time to the hotel; Amber Fort tickets on the 15th for the first
slot after 9 am, senior for the parents and adult for the user; seats
window / aisle / middle and meals diabetic / Jain / vegetarian for father /
mother / self.

## Fixed in advance

**Horizon.** 22 tools, identical names at every horizon. The request and
the correct trip never change; the horizon is set by which values only
another tool can produce (env/trip/levels.py):

| h | Adds |
|---|---|
| 11 | English names and inline filters; seat maps, meal options, rooms, cab quotes, ticket slots, travellers, checkout |
| 17 | city codes, separate filter steps (2 flights, 1 hotel), attraction id |
| 24 | fare rules, and holds for both flights, rooms, cab and tickets; checkout needs every token |
| 28 | hotel location code for the cab, travel documents, payment method, price token |

Seat ids, meal codes, room ids, quote ids and slot ids are required at
**every** horizon, so the checkout interface for late constraints is the
same at h11 and h28. This removes the gate v2 confound by design.

**Constraint classes** (eval/trip_verifier.py), each reported with the
step at which the agent committed to it:

- early: outbound (route/date, before 12:00, non-stop, cheapest) and
  return (route/date, after 18:00, non-stop, joint budget, earliest)
- mid: hotel (distance, lift, breakfast, highest rating), room types,
  cab vehicle and date, ticket attraction/date, after 09:00, first slot
- carried: cab pickup location and time (the booked flight's arrival) and
  cab drop (the booked hotel): facts from tool outputs, not the request
- late: 3 travellers x (outbound seat, return seat, meal, ticket
  category), and who sleeps in which room; committed only at checkout

Also reported: binding swaps (a traveller got a value another traveller
asked for), fact displacements (an id never seen in any earlier output),
steps taken.

**Authoring rules** (tasks/build_trip_gold.py refuses to write gold that
breaks them):

1. The answer comes from the constraints alone; the gold chain replays.
2. Every selecting constraint changes the answer: ignoring it selects a
   distinct, bookable decoy (13 decoys in trip_001).
3. No requested option is listed first, and filling travellers in listing
   order gets every traveller wrong, for seats, meals and ticket
   categories.
4. The outbound flight has a recovery fallback.
5. Tool errors validate ids and formats only, never preferences.

**Difficulty is set on English only.** Pilot: trip_001, English, h11-h28,
5 seeds. If English success at h11 is below 0.8, the task is simplified and
the pilot rerun; no other language is run until it passes. Once it passes
the design is frozen and the gate runs in all five languages unchanged.
Additional templates are authored under the same rules and are not
selected by their results.

**Serving.** Same backbone as gate v2 (Qwen3.6-27B-FP8 @ e89b16eb, vLLM
0.30.0, thinking on); context raised to 65,536 tokens.

## Measures that answer the research questions

- RQ1: success and late survival by language x horizon; the interaction.
- RQ3: which class fails (early / mid / carried / late), the commit step of
  each failed constraint, binding swaps; request seam (late) vs tool-output
  seam (carried).
- RQ4: injection on the trip domain (not_found on the outbound flight,
  transient on any tool) is built and smoke-tested; runs come after the
  gate.

## Known limits

- One world (Jaipur) so far; templates 2+ reuse it with different
  constraints. A second world is needed before the main runs.
- At h11 and h17 there are no holds, so rooms and tickets are committed at
  checkout; their commit step is reported, not assumed.
- No lenient interface yet (RQ2 control).
