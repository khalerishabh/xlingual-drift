"""
Computes the correct trip from a template's constraints alone, and the
decoy each constraint guards against (the answer if that one constraint
were ignored). Shared by the gold builder and the verifier, so the answer
never depends on the gold chain.
"""

from env.trip.world import FLIGHTS, HOTELS, TRAVELLERS, room_options, ticket_slots

_PICK = {
    "min_price": lambda rows: min(rows, key=lambda f: f["price"]),
    "earliest_departure": lambda rows: min(rows, key=lambda f: f["depart_time"]),
    "latest_departure": lambda rows: max(rows, key=lambda f: f["depart_time"]),
    "max_rating": lambda rows: max(rows, key=lambda h: h["rating"]),
    "earliest": lambda rows: min(rows, key=lambda s: s["start_time"]),
}

FLIGHT_FILTERS = ("depart_after", "depart_before", "nonstop")
HOTEL_FILTERS = ("max_distance_km", "amenities", "breakfast")
RELATION_TO_ID = {t["relation"]: t["traveller_id"] for t in TRAVELLERS}


def _choose(rows, objective, key, drop):
    if not rows:
        return None
    if drop == "objective":
        best = _PICK[objective](rows)[key]
        others = [r for r in rows if r[key] != best]
        return others[0][key] if others else None
    return _PICK[objective](rows)[key]


def _flight_ok(f, c, drop):
    if "depart_after" in c and drop != "depart_after" and not f["depart_time"] > c["depart_after"]:
        return False
    if "depart_before" in c and drop != "depart_before" and not f["depart_time"] < c["depart_before"]:
        return False
    if c.get("nonstop") and drop != "nonstop" and f["stops"] != 0:
        return False
    return True


def _leg_rows(c, sold_out):
    return [f for f in FLIGHTS if f["origin"] == c["origin"] and f["destination"] == c["destination"]
            and f["date"] == c["date"] and f["seats"] > 0 and f["flight_id"] not in sold_out]


def outbound_flight(cons, sold_out=frozenset(), drop=None):
    c = cons["outbound"]
    rows = [f for f in _leg_rows(c, sold_out) if _flight_ok(f, c, drop)]
    return _choose(rows, c["objective"], "flight_id", drop)


def return_flight(cons, outbound_id, sold_out=frozenset(), drop=None):
    c = cons["return"]
    rows = [f for f in _leg_rows(c, sold_out) if _flight_ok(f, c, drop)]
    budget = cons.get("flight_budget_total")
    if budget is not None and drop != "budget" and outbound_id is not None:
        out_price = next(f["price"] for f in FLIGHTS if f["flight_id"] == outbound_id)
        rows = [f for f in rows if cons["passengers"] * (out_price + f["price"]) <= budget]
    return _choose(rows, c["objective"], "flight_id", drop)


def hotel(cons, drop=None):
    c = cons["hotel"]
    rows = [h for h in HOTELS if h["city"] == c["city"]
            and (drop == "max_distance_km" or h["distance_to_hawa_mahal_km"] <= c["max_distance_km"])
            and (drop == "amenities" or set(c["amenities"]) <= set(h["amenities"]))
            and (drop == "breakfast" or h["breakfast"] == c["breakfast"])]
    return _choose(rows, c["objective"], "hotel_id", drop)


def ticket_slot(cons, drop=None):
    c = cons["tickets"]
    rows = [s for s in ticket_slots(c["attraction_id"], c["date"])
            if drop == "slot_after" or s["start_time"] > c["slot_after"]]
    return _choose(rows, c["objective"], "slot_id", drop)


def rooms(cons, hotel_id):
    """[(room_id, sorted traveller ids)] for the requested room types."""
    opts = room_options(hotel_id)
    out = []
    for r in cons["rooms"]:
        rid = next(o["room_id"] for o in opts if o["room_type"] == r["room_type"])
        out.append((rid, sorted(RELATION_TO_ID[x] for x in r["occupants"])))
    return out


def arrival_time(flight_id):
    return next(f["arrive_time"] for f in FLIGHTS if f["flight_id"] == flight_id)


def answer(cons, sold_out=frozenset()) -> dict:
    out = outbound_flight(cons, sold_out)
    ret = return_flight(cons, out, sold_out)
    hid = hotel(cons)
    return {"outbound_flight_id": out, "return_flight_id": ret, "hotel_id": hid,
            "rooms": rooms(cons, hid) if hid else None, "ticket_slot_id": ticket_slot(cons),
            "cab": {"vehicle_type": cons["cab"]["vehicle_type"], "date": cons["cab"]["date"],
                    "pickup_time": arrival_time(out) if out else None, "drop_hotel": hid,
                    "pickup_location": cons["outbound"]["destination"]},
            "travellers": {RELATION_TO_ID[rel]: dict(v) for rel, v in cons["travellers"].items()}}


def decoys(cons) -> dict:
    out = outbound_flight(cons)
    ret = return_flight(cons, out)
    d = {}
    for k in [k for k in FLIGHT_FILTERS if k in cons["outbound"]] + ["objective"]:
        d[f"outbound.{k}"] = outbound_flight(cons, drop=k)
    for k in [k for k in FLIGHT_FILTERS if k in cons["return"]] + ["objective"]:
        d[f"return.{k}"] = return_flight(cons, out, drop=k)
    if "flight_budget_total" in cons:
        d["return.budget"] = return_flight(cons, out, drop="budget")
    for k in list(HOTEL_FILTERS) + ["objective"]:
        d[f"hotel.{k}"] = hotel(cons, drop=k)
    for k in ("slot_after", "objective"):
        d[f"tickets.{k}"] = ticket_slot(cons, drop=k)
    return d
