"""
Builds tasks/trip_gold/<template>_h<N>.json for every trip template and
horizon, and refuses to write anything that breaks a design rule
(docs/TRIP_SPEC.md):

  1. The answer is computed from the constraints alone (env.trip.solver);
     the chain written for it must replay to a confirmed trip.
  2. Every constraint that selects an item changes the answer: ignoring it
     leads to a distinct, bookable decoy.
  3. No requested option is listed first (flights, hotel, room types,
     vehicle, slot, meal, ticket category), and assigning options to
     travellers in listing order gets every traveller wrong, so neither
     shortcut can pass for survival.
  4. A recovery fallback exists for the outbound flight.

    python -m tasks.build_trip_gold          # rebuild all gold files
    python -m tasks.build_trip_gold --check  # fail if any committed file is stale
"""

import argparse
import json
import sys
from pathlib import Path

from env.trip.chain import assign_seats, chain, plan_from_answer
from env.trip.levels import TRIP_HORIZONS
from env.trip.solver import RELATION_TO_ID, answer, decoys, outbound_flight
from env.trip.tools import TripTools
from env.trip.world import (FLIGHTS, HOTELS, MEAL_OPTIONS, TICKET_CATEGORIES, TRAVELLERS, VEHICLES, room_options,
                            seat_map, ticket_slots)

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "tasks" / "trip_templates"
GOLD = ROOT / "tasks" / "trip_gold"


def check_rules(t: dict, ans: dict) -> dict:
    tid, cons = t["template_id"], t["constraints"]
    assert all(v is not None for v in (ans["outbound_flight_id"], ans["return_flight_id"], ans["hotel_id"],
                                       ans["ticket_slot_id"])), f"{tid}: constraints are unsatisfiable"
    d = decoys(cons)
    for name, value in d.items():
        part = name.split(".")[0]
        right = {"outbound": ans["outbound_flight_id"], "return": ans["return_flight_id"],
                 "hotel": ans["hotel_id"], "tickets": ans["ticket_slot_id"]}[part]
        assert value is not None and value != right, f"{tid}: ignoring {name} does not change the answer"
    for part in ("outbound", "return", "hotel", "tickets"):
        vals = [v for k, v in d.items() if k.startswith(part + ".")]
        assert len(set(vals)) == len(vals), f"{tid}: {part} decoys are not distinct {vals}"

    def not_first(listing, wanted, what):
        assert listing[0] not in wanted, f"{tid}: requested {what} {listing[0]} is listed first"

    for leg, fid in (("outbound", ans["outbound_flight_id"]), ("return", ans["return_flight_id"])):
        c = cons[leg]
        listing = [f["flight_id"] for f in FLIGHTS if (f["origin"], f["destination"], f["date"]) ==
                   (c["origin"], c["destination"], c["date"]) and f["seats"] > 0]
        not_first(listing, {fid}, f"{leg} flight")
    not_first([h["hotel_id"] for h in HOTELS if h["city"] == cons["hotel"]["city"]], {ans["hotel_id"]}, "hotel")
    not_first([r["room_type"] for r in room_options(ans["hotel_id"])], {r["room_type"] for r in cons["rooms"]}, "room type")
    not_first([v[1] for v in VEHICLES], {cons["cab"]["vehicle_type"]}, "vehicle")
    not_first([s["slot_id"] for s in ticket_slots(cons["tickets"]["attraction_id"], cons["tickets"]["date"])],
              {ans["ticket_slot_id"]}, "slot")

    prefs = ans["travellers"]
    order = [tr["traveller_id"] for tr in TRAVELLERS]
    listings = {"meal": [m["meal"] for m in MEAL_OPTIONS], "ticket": list(TICKET_CATEGORIES)}
    for leg in ("outbound_flight_id", "return_flight_id"):
        listings[f"seat@{leg}"] = [s["seat_type"] for s in seat_map(ans[leg]) if s["available"]]
    for key, listing in listings.items():
        attr = key.split("@")[0]
        for i, trav in enumerate(order):
            assert listing[i] != prefs[trav][attr], \
                f"{tid}: assigning {key} in listing order gets {trav} right ({listing[i]})"
        if attr != "seat":
            not_first(listing, {p[attr] for p in prefs.values()}, attr)
    for leg in ("outbound_flight_id", "return_flight_id"):
        assign_seats(ans[leg], {k: v["seat"] for k, v in prefs.items()})

    fallback = outbound_flight(cons, {ans["outbound_flight_id"]})
    assert fallback and fallback != ans["outbound_flight_id"], f"{tid}: no recovery fallback"
    return {"decoys": d, "recovery_fallback": {"outbound": fallback}}


def build(t: dict, h: int) -> dict:
    cons = t["constraints"]
    assert set(cons["travellers"]) == set(RELATION_TO_ID), t["template_id"]
    ans = answer(cons)
    extra = check_rules(t, ans)
    steps = chain(cons, plan_from_answer(ans), h)
    assert len(steps) == h, (t["template_id"], h, len(steps))
    tools = TripTools("strict", h)
    for step in steps:
        result = tools.call(step["tool"], step["args"])
    assert result["status"] == "confirmed", result
    return {"task_id": f"{t['template_id']}_h{h}", "template_id": t["template_id"], "domain": "trip", "horizon": h,
            "constraints": cons, "answer": ans, **extra, "terminal_state": result, "gold_steps": steps}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stale = []
    for path in sorted(TEMPLATES.glob("*.json")):
        t = json.loads(path.read_text(encoding="utf-8"))
        for h in TRIP_HORIZONS:
            gold = build(t, h)
            text = json.dumps(gold, indent=2) + "\n"
            out = GOLD / f"{gold['task_id']}.json"
            if args.check:
                if not out.exists() or out.read_text(encoding="utf-8") != text:
                    stale.append(out.name)
            else:
                out.write_text(text, encoding="utf-8")
        a = gold["answer"]
        print(f"{t['template_id']}: {a['outbound_flight_id']} / {a['return_flight_id']} / {a['hotel_id']} "
              f"{a['rooms']} / {a['ticket_slot_id']} / cab {a['cab']['vehicle_type']} {a['cab']['pickup_time']}")
        print(f"  decoys {gold['decoys']}")
    if stale:
        sys.exit(f"stale gold files: {stale}")


if __name__ == "__main__":
    main()
