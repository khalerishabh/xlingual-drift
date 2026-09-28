"""
Writes out the tool-call chain that executes a trip plan at a given
horizon. The gold builder calls it with the correct plan; the mock policy
calls it with a deliberately wrong one, so every deviation is a complete,
self-consistent trajectory that fails only on the thing it changes.
"""

from env.trip.levels import trip_level
from env.trip.tools import _price_token
from env.trip.world import (CITIES, FLIGHTS, MEAL_OPTIONS, TRAVEL_DOCUMENTS, VEHICLES, hotel_location,
                            room_options, seat_map)

_VEHICLE_CODE = {v[1]: v[0] for v in VEHICLES}


def _flight(fid):
    return next(f for f in FLIGHTS if f["flight_id"] == fid)


def assign_seats(flight_id: str, wanted: dict) -> dict:
    """First available seat of each wanted type, in traveller-id order."""
    free = [s for s in seat_map(flight_id) if s["available"]]
    taken, out = set(), {}
    for tid in sorted(wanted):
        seat = next(s["seat_id"] for s in free if s["seat_type"] == wanted[tid] and s["seat_id"] not in taken)
        taken.add(seat)
        out[tid] = seat
    return out


def quote_id(vehicle, date, pickup_time, drop_hotel):
    return f"Q-{_VEHICLE_CODE[vehicle]}-{date[5:7]}{date[8:]}-{pickup_time.replace(':', '')}-{drop_hotel.split('-')[-1]}"


def chain(cons: dict, plan: dict, horizon: int) -> list[dict]:
    lv = trip_level(horizon)
    names = {code: CITIES[code] for code in (cons["outbound"]["origin"], cons["outbound"]["destination"])}
    city = (lambda code: code) if lv["city_codes"] else (lambda code: names[code])
    steps = []

    def add(tool, **args):
        steps.append({"tool": tool, "args": args})

    if lv["city_codes"]:
        for code in names:
            add("resolve_city", name=names[code])

    holds = {}
    for leg, fid in (("outbound", plan["outbound"]), ("return", plan["return"])):
        c = cons[leg]
        filters = {k: c[k] for k in ("depart_after", "depart_before") if k in c}
        if c.get("nonstop"):
            filters["nonstop_only"] = True
        search = {"origin": city(c["origin"]), "destination": city(c["destination"]), "date": c["date"]}
        if lv["separate_filters"]:
            add("search_flights", **search)
            add("filter_flights", **filters)
        else:
            add("search_flights", **search, **filters)
        f = _flight(fid)
        if lv["holds"]:
            add("get_fare_rules", flight_id=fid)
            add("hold_flight", flight_id=fid, fare_class=f["fare_class"], passengers=cons["passengers"])
            holds[f"{leg}_hold_token"] = f"FH-{fid}-{f['fare_class']}-{cons['passengers']}"
        add("get_seat_map", flight_id=fid)
        if leg == "outbound":
            add("get_meal_options", flight_id=fid)

    h = cons["hotel"]
    hfilters = {}
    if "max_distance_km" in h:
        hfilters["max_distance_km"] = h["max_distance_km"]
    if h.get("amenities"):
        hfilters["required_amenities"] = list(h["amenities"])
    if "breakfast" in h:
        hfilters["breakfast"] = h["breakfast"]
    hsearch = {"city": city(h["city"]), "check_in": h["check_in"], "check_out": h["check_out"]}
    if lv["separate_filters"]:
        add("search_hotels", **hsearch)
        add("filter_hotels", **hfilters)
    else:
        add("search_hotels", **hsearch, **hfilters)
    hid = plan["hotel_id"]
    add("get_room_options", hotel_id=hid, check_in=h["check_in"], check_out=h["check_out"])
    room_ids = [rid for rid, _ in plan["rooms"]]
    if lv["holds"]:
        add("hold_rooms", hotel_id=hid, room_ids=room_ids)
        holds["hotel_hold_token"] = f"HH-{hid[2:]}-" + "-".join(r.split("-")[-1] for r in sorted(room_ids))
    drop = hid
    if lv["checkout_extras"]:
        add("get_hotel_details", hotel_id=hid)
        drop = hotel_location(hid)

    cab = plan["cab"]
    add("get_cab_quotes", pickup_location=cab["pickup_location"], drop_location=drop, date=cab["date"],
        pickup_time=cab["pickup_time"])
    qid = quote_id(cab["vehicle_type"], cab["date"], cab["pickup_time"], hid)
    if lv["holds"]:
        add("hold_cab", quote_id=qid)
        holds["cab_hold_token"] = f"CH-{qid[2:]}"

    t = cons["tickets"]
    if lv["attraction_ids"]:
        add("search_attractions", city=city(h["city"]))
        add("get_ticket_slots", attraction_id=t["attraction_id"], date=t["date"])
    else:
        add("get_ticket_slots", attraction_name=t["attraction_name"], date=t["date"])
    if lv["holds"]:
        add("hold_tickets", slot_id=plan["ticket_slot_id"], count=cons["passengers"])
        holds["ticket_hold_token"] = f"TH-{plan['ticket_slot_id'][2:]}-{cons['passengers']}"

    add("get_travellers")
    pax_prefs = plan["travellers"]
    seats = {leg: assign_seats(plan[leg], {tid: p["seat"] for tid, p in pax_prefs.items()})
             for leg in ("outbound", "return")}
    meal_code = {m["meal"]: m["meal_code"] for m in MEAL_OPTIONS}
    docs = {d["traveller_id"]: d["document_id"] for d in TRAVEL_DOCUMENTS}
    passengers = []
    for tid in sorted(pax_prefs):
        p = {"traveller_id": tid, "outbound_seat_id": seats["outbound"][tid], "return_seat_id": seats["return"][tid],
             "meal_code": meal_code[pax_prefs[tid]["meal"]], "ticket_category": pax_prefs[tid]["ticket"]}
        if lv["checkout_extras"]:
            p["document_id"] = docs[tid]
        passengers.append(p)

    confirm = {"outbound_flight_id": plan["outbound"], "return_flight_id": plan["return"], "passengers": passengers,
               "hotel_id": hid, "rooms": [{"room_id": rid, "traveller_ids": tids} for rid, tids in plan["rooms"]],
               "cab_quote_id": qid, "ticket_slot_id": plan["ticket_slot_id"]}
    if lv["holds"]:
        confirm.update(holds)
    if lv["checkout_extras"]:
        add("get_travel_documents")
        add("get_payment_methods")
        add("price_itinerary", **holds)
        confirm["price_token"] = _price_token([holds[k] for k in sorted(holds)])
        confirm["payment_id"] = "PAY-UPI-01"
    add("confirm_trip", **confirm)
    return steps


def plan_from_answer(ans: dict) -> dict:
    return {"outbound": ans["outbound_flight_id"], "return": ans["return_flight_id"], "hotel_id": ans["hotel_id"],
            "rooms": [(rid, list(tids)) for rid, tids in ans["rooms"]], "ticket_slot_id": ans["ticket_slot_id"],
            "cab": dict(ans["cab"]), "travellers": {k: dict(v) for k, v in ans["travellers"].items()}}
