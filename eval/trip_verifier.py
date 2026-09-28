"""
Deterministic verifier for the trip domain (docs/TRIP_SPEC.md).

Every constraint in the request is checked on the confirmed trip and
reported with its class and the step at which the agent committed to it:

  early    outbound and return flight constraints, applied when each
           flight is chosen (the first steps of the chain)
  mid      hotel, room types, cab vehicle, ticket slot
  carried  facts the agent must copy from one tool output into a later
           call: cab pickup time = the booked flight's arrival, cab drop =
           the booked hotel
  late     per-traveller seat, meal and ticket category, and who sleeps in
           which room; committed only in confirm_trip, the last step

The return flight is judged against the best return given the outbound
the agent actually booked (the budget couples them), so one early mistake
is not counted twice.
"""

from collections import defaultdict

from env.trip.solver import RELATION_TO_ID, hotel, outbound_flight, return_flight, ticket_slot
from env.trip.world import FLIGHTS, HOTELS, MEAL_OPTIONS, room_options, seat_map

_MEAL_BY_CODE = {m["meal_code"]: m["meal"] for m in MEAL_OPTIONS}
_ID_KEYS = ("flight_id", "outbound_flight_id", "return_flight_id", "hotel_id", "room_id", "quote_id",
            "cab_quote_id", "slot_id", "ticket_slot_id", "traveller_id", "outbound_seat_id", "return_seat_id",
            "meal_code", "document_id", "payment_id", "price_token", "outbound_hold_token", "return_hold_token",
            "hotel_hold_token", "cab_hold_token", "ticket_hold_token", "fare_class")
CLASSES = ("early", "mid", "carried", "late")


def _flatten(value, out: set):
    if isinstance(value, dict):
        for v in value.values():
            _flatten(v, out)
    elif isinstance(value, list):
        for v in value:
            _flatten(v, out)
    else:
        out.add(str(value))


def _walk_ids(value, found: list):
    if isinstance(value, dict):
        for k, v in value.items():
            if k in _ID_KEYS and isinstance(v, str):
                found.append(v)
            else:
                _walk_ids(v, found)
    elif isinstance(value, list):
        for v in value:
            _walk_ids(v, found)


def _first_step_using(steps, value) -> int | None:
    for i, s in enumerate(steps, 1):
        if "result" in s:
            found = set()
            _flatten(s["args"], found)
            if value in found:
                return i
    return None


def _flight(fid):
    return next((f for f in FLIGHTS if f["flight_id"] == fid), None)


def verify_trip(traj, gold: dict, sold_out: set) -> dict:
    cons = gold["constraints"]
    steps = traj.steps
    confirm_step = next((i for i, s in enumerate(steps, 1) if s["tool"] == "confirm_trip" and "result" in s), None)
    a = steps[confirm_step - 1]["args"] if confirm_step else None

    checks, commit, cls = {}, {}, {}

    def put(name, klass, ok, step):
        checks[name], cls[name], commit[name] = bool(ok), klass, step

    swaps = 0
    if a is not None:
        out, ret = _flight(a["outbound_flight_id"]), _flight(a["return_flight_id"])
        oc, rc = cons["outbound"], cons["return"]
        s_out, s_ret = _first_step_using(steps, out["flight_id"]), _first_step_using(steps, ret["flight_id"])
        put("outbound.route_date", "early", (out["origin"], out["destination"], out["date"]) == (oc["origin"], oc["destination"], oc["date"]), s_out)
        if "depart_before" in oc:
            put("outbound.depart_before", "early", out["depart_time"] < oc["depart_before"], s_out)
        if "depart_after" in oc:
            put("outbound.depart_after", "early", out["depart_time"] > oc["depart_after"], s_out)
        if oc.get("nonstop"):
            put("outbound.nonstop", "early", out["stops"] == 0, s_out)
        put("outbound.objective", "early", out["flight_id"] == outbound_flight(cons, sold_out), s_out)
        put("return.route_date", "early", (ret["origin"], ret["destination"], ret["date"]) == (rc["origin"], rc["destination"], rc["date"]), s_ret)
        if "depart_after" in rc:
            put("return.depart_after", "early", ret["depart_time"] > rc["depart_after"], s_ret)
        if "depart_before" in rc:
            put("return.depart_before", "early", ret["depart_time"] < rc["depart_before"], s_ret)
        if rc.get("nonstop"):
            put("return.nonstop", "early", ret["stops"] == 0, s_ret)
        if "flight_budget_total" in cons:
            put("return.budget", "early", cons["passengers"] * (out["price"] + ret["price"]) <= cons["flight_budget_total"], s_ret)
        put("return.objective", "early", ret["flight_id"] == return_flight(cons, out["flight_id"], sold_out), s_ret)

        hc = cons["hotel"]
        h = next((x for x in HOTELS if x["hotel_id"] == a["hotel_id"]), None)
        s_h = _first_step_using(steps, a["hotel_id"])
        put("hotel.max_distance_km", "mid", h["distance_to_hawa_mahal_km"] <= hc["max_distance_km"], s_h)
        put("hotel.amenities", "mid", set(hc["amenities"]) <= set(h["amenities"]), s_h)
        put("hotel.breakfast", "mid", h["breakfast"] == hc["breakfast"], s_h)
        put("hotel.objective", "mid", h["hotel_id"] == hotel(cons), s_h)
        types = {r["room_id"]: r["room_type"] for r in room_options(h["hotel_id"])}
        booked_types = sorted(types.get(r["room_id"]) for r in a["rooms"])
        s_rooms = next((i for i, s in enumerate(steps, 1) if s["tool"] == "hold_rooms" and "result" in s), confirm_step)
        put("rooms.types", "mid", booked_types == sorted(r["room_type"] for r in cons["rooms"]), s_rooms)
        want_rooms = sorted((r["room_type"], sorted(RELATION_TO_ID[x] for x in r["occupants"])) for r in cons["rooms"])
        got_rooms = sorted((types.get(r["room_id"]), sorted(r["traveller_ids"])) for r in a["rooms"])
        put("rooms.assignment", "late", got_rooms == want_rooms, confirm_step)

        quote, s_q = None, None
        for i, s in enumerate(steps, 1):
            for q in s.get("result", {}).get("quotes", []) if s["tool"] == "get_cab_quotes" else []:
                if q["quote_id"] == a["cab_quote_id"]:
                    quote, s_q = q, i
        cc = cons["cab"]
        put("cab.vehicle_type", "mid", quote["vehicle_type"] == cc["vehicle_type"], s_q)
        put("cab.date", "mid", quote["date"] == cc["date"], s_q)
        put("cab.pickup_location", "carried", quote["pickup_location"] == out["destination"], s_q)
        put("cab.pickup_time", "carried", quote["pickup_time"] == out["arrive_time"], s_q)
        put("cab.drop", "carried", quote["drop_location"].split("-")[-1] == a["hotel_id"].split("-")[-1], s_q)

        tc = cons["tickets"]
        slot = a["ticket_slot_id"]
        s_slot = _first_step_using(steps, slot)
        start = slot.split("-")[-1]
        put("tickets.attraction_date", "mid", slot.split("-")[1] == tc["attraction_id"].split("-")[-1]
            and slot.split("-")[2] == tc["date"][5:7] + tc["date"][8:], s_slot)
        put("tickets.slot_after", "mid", start > tc["slot_after"].replace(":", ""), s_slot)
        put("tickets.objective", "mid", slot == ticket_slot(cons), s_slot)

        pax = {p["traveller_id"]: p for p in a["passengers"]}
        want = {RELATION_TO_ID[rel]: v for rel, v in cons["travellers"].items()}
        smaps = {leg: {s["seat_id"]: s["seat_type"] for s in seat_map(f["flight_id"])}
                 for leg, f in (("outbound", out), ("return", ret))}
        rel_of = {v: k for k, v in RELATION_TO_ID.items()}
        for tid, w in sorted(want.items()):
            p, rel = pax[tid], rel_of[tid]
            got = {"seat.outbound": smaps["outbound"].get(p["outbound_seat_id"]),
                   "seat.return": smaps["return"].get(p["return_seat_id"]),
                   "meal": _MEAL_BY_CODE.get(p["meal_code"]), "ticket": p["ticket_category"]}
            wanted = {"seat.outbound": w["seat"], "seat.return": w["seat"], "meal": w["meal"], "ticket": w["ticket"]}
            for attr in got:
                ok = got[attr] == wanted[attr]
                put(f"{attr}.{rel}", "late", ok, confirm_step)
                others = {wanted_o[attr] for t2, wanted_o in
                          ((t2, {"seat.outbound": w2["seat"], "seat.return": w2["seat"], "meal": w2["meal"], "ticket": w2["ticket"]})
                           for t2, w2 in want.items() if t2 != tid)}
                if not ok and got[attr] in others:
                    swaps += 1

    by_class = defaultdict(list)
    for name, ok in checks.items():
        by_class[cls[name]].append(ok)
    class_ok = {k: (all(by_class[k]) if by_class[k] else None) for k in CLASSES}

    seen, displaced = set(), 0
    for s in steps:
        ids = []
        _walk_ids(s["args"], ids)
        displaced += sum(1 for v in ids if v not in seen)
        if "result" in s:
            _flatten(s["result"], seen)

    ok = a is not None and all(checks.values())
    return {
        "success": ok,
        "flight_correct": a is not None and all(v for k, v in checks.items() if cls[k] == "early"),
        "booked_flight": a["outbound_flight_id"] if a else None,
        "booked_return": a["return_flight_id"] if a else None,
        "booked_hotel": a["hotel_id"] if a else None,
        "constraint_ok": checks or None,
        "constraint_class": cls or None,
        "constraint_commit_step": commit or None,
        "all_early_survived": class_ok["early"], "all_mid_survived": class_ok["mid"],
        "all_carried_survived": class_ok["carried"], "all_late_survived": class_ok["late"],
        "binding_swaps": swaps if a is not None else None,
        "fact_displacements": displaced,
        "late_commit_step": confirm_step,
        "first_error_step": traj.first_error_step,
        "num_steps_taken": len(steps),
        "extra_steps": len(steps) - len(gold["gold_steps"]),
        "injected": traj.injected_error is not None,
        "injected_at_step": traj.injected_at_step,
        "recovered": ok if traj.injected_error is not None else None,
    }
