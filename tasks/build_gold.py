"""
Builds tasks/gold/<template>_h<N>.json for every template and horizon, and
refuses to write anything that breaks a design rule (docs/PHASE1_SPEC.md):

  1. The answer is computed from the constraints alone (eval.verifier),
     independently of the chain, and the replayed chain must reach it.
  2. Every early constraint changes the answer: dropping it leads to a
     distinct, bookable decoy flight.
  3. Every late constraint is a real choice: the requested option exists,
     at least one other option does too, and the requested option is not
     listed first (so "take the first one" does not look like survival).
  4. A recovery fallback exists (the best flight once the answer is sold out).

    python -m tasks.build_gold          # rebuild all gold files
    python -m tasks.build_gold --check  # fail if any committed file is stale
"""

import argparse
import json
import sys
from pathlib import Path

from env.data.flights import CITIES, FLIGHTS, MEAL_OPTIONS, SEAT_MAP, seat_map_for
from env.tools.horizons import HORIZONS
from env.tools.travel_tools import TravelTools
from eval.verifier import EARLY_FILTERS, optimal_flight

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "tasks" / "templates"
GOLD = ROOT / "tasks" / "gold"


def _chain(t: dict, h: int, flight: dict) -> list[dict]:
    c, late = t["constraints"], t["late_constraints"]
    filters = {k: c[k] for k in EARLY_FILTERS if k in c}
    names, codes = t["city_names"], t["entities"]
    fid, fare = flight["flight_id"], flight["fare_class"]
    seat_id = next(s["seat_id"] for s in seat_map_for(flight) if s["seat_type"] == late["seat_type"])
    meal_code = next(m["meal_code"] for m in MEAL_OPTIONS if m["meal"] == late["meal"])

    resolve = [{"tool": "resolve_city", "args": {"name": names["origin"]}},
               {"tool": "resolve_city", "args": {"name": names["destination"]}}]
    by_name = {"origin": names["origin"], "destination": names["destination"], "date": c["date"]}
    by_code = {"origin": codes["origin"], "destination": codes["destination"], "date": c["date"]}
    prefs = {"seat_type": late["seat_type"], "meal": late["meal"]}

    if h == 2:
        return [{"tool": "search_flights", "args": {**by_name, **filters}},
                {"tool": "book_flight", "args": {"flight_id": fid, **prefs}}]
    if h == 4:
        return resolve + [{"tool": "search_flights", "args": {**by_code, **filters}},
                          {"tool": "book_flight", "args": {"flight_id": fid, **prefs}}]

    steps = resolve + [{"tool": "search_flights", "args": by_code},
                       {"tool": "filter_flights", "args": filters}]
    if h == 6:
        hold = f"H-{fid}-STD"
        return steps + [{"tool": "get_seat_availability", "args": {"flight_id": fid}},
                        {"tool": "book_flight", "args": {"flight_id": fid, "hold_token": hold, **prefs}}]

    hold = f"H-{fid}-{fare}"
    steps += [{"tool": "get_fare_rules", "args": {"flight_id": fid}},
              {"tool": "get_seat_availability", "args": {"flight_id": fid, "fare_class": fare}},
              {"tool": "get_user_profile", "args": {}}]
    book = {"flight_id": fid, "hold_token": hold, "passenger_id": "P001"}
    if h == 8:
        return steps + [{"tool": "book_flight", "args": {**book, **prefs}}]

    if h == 12:
        steps += [{"tool": "get_travel_documents", "args": {"passenger_id": "P001"}},
                  {"tool": "get_payment_methods", "args": {}}]
        book.update({"document_id": "DOC-P001-AADHAAR", "payment_id": "PAY-UPI-01"})
    steps += [{"tool": "get_seat_map", "args": {"flight_id": fid}},
              {"tool": "get_meal_options", "args": {"flight_id": fid}}]
    return steps + [{"tool": "book_flight", "args": {**book, "seat_id": seat_id, "meal_code": meal_code}}]


_RETURN_KEYS = ("code", "hold_token", "fare_class", "passenger_id", "document_id")


def build(t: dict, h: int) -> dict:
    spec = {"entities": t["entities"], "constraints": t["constraints"]}
    answer_id = optimal_flight(spec, set())
    assert answer_id, f"{t['template_id']}: no flight satisfies the constraints"
    flight = next(f for f in FLIGHTS if f["flight_id"] == answer_id)
    assert set(t["entities"].values()) <= set(CITIES), t["template_id"]

    decoys = {}
    droppable = [k for k in EARLY_FILTERS if k in t["constraints"]] + ["objective"]
    for k in droppable:
        d = optimal_flight(spec, set(), drop=k)
        assert d and d != answer_id, f"{t['template_id']}: dropping {k} does not change the answer"
        decoys[k] = d
    assert len(set(decoys.values())) == len(decoys), f"{t['template_id']}: decoys not distinct {decoys}"

    for key, listing in (("seat_type", [s["seat_type"] for s in seat_map_for(flight)]),
                         ("meal", [m["meal"] for m in MEAL_OPTIONS])):
        wanted = t["late_constraints"][key]
        assert wanted in listing and len(set(listing) - {wanted}) >= 1, f"{t['template_id']}: {key} is not a real choice"
        assert listing[0] != wanted, f"{t['template_id']}: requested {key} '{wanted}' is listed first"

    fallback = optimal_flight(spec, {answer_id})
    assert fallback and fallback != answer_id, f"{t['template_id']}: no recovery fallback"

    steps = _chain(t, h, flight)
    assert len(steps) == h, (t["template_id"], h, len(steps))
    tools, result = TravelTools("strict", h), None
    for step in steps:
        result = tools.call(step["tool"], step["args"])
        returns = {k: v for k, v in result.items() if k in _RETURN_KEYS}
        if returns:
            step["returns"] = returns
    expected = {"booking.flight_id": answer_id, "booking.price": flight["price"],
                "booking.seat_type": t["late_constraints"]["seat_type"], "booking.meal": t["late_constraints"]["meal"]}
    assert result == expected, (t["template_id"], h, result, expected)

    return {
        "task_id": f"{t['template_id']}_h{h}", "template_id": t["template_id"], "horizon": h,
        "entities": t["entities"], "constraints": t["constraints"], "late_constraints": t["late_constraints"],
        "terminal_state": expected, "recovery_fallback": fallback, "decoys": decoys, "gold_steps": steps,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stale = []
    for path in sorted(TEMPLATES.glob("*.json")):
        t = json.loads(path.read_text(encoding="utf-8"))
        for h in HORIZONS:
            gold = build(t, h)
            text = json.dumps(gold, indent=2) + "\n"
            out = GOLD / f"{gold['task_id']}.json"
            if args.check:
                if not out.exists() or out.read_text(encoding="utf-8") != text:
                    stale.append(out.name)
            else:
                out.write_text(text, encoding="utf-8")
        print(f"{t['template_id']}: answer {gold['terminal_state']['booking.flight_id']}, "
              f"decoys {gold['decoys']}, fallback {gold['recovery_fallback']}, "
              f"late {t['late_constraints']}")
    if stale:
        sys.exit(f"stale gold files: {stale}")


if __name__ == "__main__":
    main()
