"""
The Jaipur world (docs/TRIP_SPEC.md): every flight, hotel, room, cab and
attraction the trip tools can return. Several templates share one world
and differ only in what the request asks for, so decoys are rows here that
a dropped constraint would select.

Listing order is deliberate: results are not sorted by any objective, so
the agent has to compute the answer, and no requested option is the one a
"take the first row" shortcut would pick.
"""

CITIES = {"MAA": "Chennai", "JAI": "Jaipur", "DEL": "Delhi"}


def _f(fid, airline, o, d, date, dep, arr, stops, price, fare, seats=9, baggage=15, refundable=False, via=None):
    return {"flight_id": fid, "airline": airline, "origin": o, "destination": d, "date": date,
            "depart_time": dep, "arrive_time": arr, "stops": stops, "via": via, "price": price,
            "fare_class": fare, "baggage_kg": baggage, "refundable": refundable, "seats": seats}


FLIGHTS = [
    _f("6E612", "IndiGo", "MAA", "JAI", "2026-10-14", "05:40", "08:25", 0, 5450, "R-SAVER"),
    _f("AI561", "Air India", "MAA", "JAI", "2026-10-14", "06:15", "10:55", 1, 3980, "T-ECO", via="DEL", baggage=25),
    _f("QP1402", "Akasa Air", "MAA", "JAI", "2026-10-14", "06:50", "09:40", 0, 4600, "S-LITE", seats=0),
    _f("SG305", "SpiceJet", "MAA", "JAI", "2026-10-14", "09:05", "11:50", 0, 5200, "Q-SAVER"),
    _f("6E621", "IndiGo", "MAA", "JAI", "2026-10-14", "07:30", "10:15", 0, 4870, "R-SAVER"),
    _f("UK818", "Vistara", "MAA", "JAI", "2026-10-14", "10:40", "13:30", 0, 6100, "V-ECO", baggage=20, refundable=True),
    _f("IX142", "Air India Express", "MAA", "JAI", "2026-10-14", "11:55", "14:35", 0, 5010, "X-VALUE"),
    _f("6E735", "IndiGo", "MAA", "JAI", "2026-10-14", "13:20", "16:05", 0, 4250, "R-SAVER"),
    _f("AI473", "Air India", "MAA", "JAI", "2026-10-14", "17:45", "22:30", 1, 3700, "T-ECO", via="DEL", baggage=25),
    _f("SG912", "SpiceJet", "MAA", "JAI", "2026-10-14", "19:10", "21:55", 0, 5600, "Q-SAVER"),

    _f("6E613", "IndiGo", "JAI", "MAA", "2026-10-16", "08:50", "11:35", 0, 4100, "R-SAVER"),
    _f("6E736", "IndiGo", "JAI", "MAA", "2026-10-16", "16:30", "19:15", 0, 4300, "R-SAVER"),
    _f("QP1403", "Akasa Air", "JAI", "MAA", "2026-10-16", "17:05", "19:50", 0, 4500, "S-LITE"),
    _f("SG306", "SpiceJet", "JAI", "MAA", "2026-10-16", "19:20", "22:05", 0, 5080, "Q-SAVER"),
    _f("AI474", "Air India", "JAI", "MAA", "2026-10-16", "18:10", "23:40", 1, 3900, "T-ECO", via="DEL", baggage=25),
    _f("6E622", "IndiGo", "JAI", "MAA", "2026-10-16", "18:35", "21:20", 0, 5890, "R-SAVER"),
    _f("UK819", "Vistara", "JAI", "MAA", "2026-10-16", "20:15", "23:05", 0, 4990, "V-ECO", baggage=20, refundable=True),
    _f("IX143", "Air India Express", "JAI", "MAA", "2026-10-16", "21:40", "00:25", 0, 4700, "X-VALUE"),
]

SEAT_TYPE_BY_LETTER = {"A": "window", "B": "middle", "C": "aisle", "D": "aisle", "E": "middle", "F": "window"}
SEAT_ROWS = (14, 15, 16, 17)
_OCCUPIED = {
    "odd": {"14A", "14B", "14D", "14E", "15A", "16C", "16F", "17D"},
    "even": {"14A", "14B", "14C", "14E", "15A", "15C", "16D", "17F"},
}


def seat_map(flight_id: str) -> list[dict]:
    occupied = _OCCUPIED["odd" if int(flight_id[-1]) % 2 else "even"]
    return [{"seat_id": f"{r}{c}", "seat_type": SEAT_TYPE_BY_LETTER[c], "available": f"{r}{c}" not in occupied,
             "extra_legroom": r == 14}
            for r in SEAT_ROWS for c in "ABCDEF"]


MEAL_OPTIONS = [
    {"meal_code": "NVML", "meal": "non_vegetarian", "description": "Chicken curry with rice"},
    {"meal_code": "VGML", "meal": "vegetarian", "description": "Paneer curry with rice"},
    {"meal_code": "JNML", "meal": "jain", "description": "No root vegetables, no onion or garlic"},
    {"meal_code": "DBML", "meal": "diabetic", "description": "Low sugar, high fibre"},
    {"meal_code": "VLML", "meal": "lacto_vegetarian", "description": "Vegetarian with dairy, no egg"},
    {"meal_code": "CHML", "meal": "child", "description": "Child meal"},
]
MEALS = tuple(m["meal"] for m in MEAL_OPTIONS)


def _h(hid, name, area, dist, rating, price, amenities, breakfast):
    return {"hotel_id": hid, "name": name, "city": "JAI", "area": area, "distance_to_hawa_mahal_km": dist,
            "rating": rating, "price_from_per_night": price, "amenities": amenities, "breakfast": breakfast}


HOTELS = [
    _h("H-JAI-104", "Umaid Courtyard", "Bani Park", 1.2, 4.6, 3900, ["wifi", "ac", "parking"], "veg"),
    _h("H-JAI-121", "Hawa Sadan", "Badi Chaupar", 0.6, 4.7, 4400, ["lift", "wifi", "ac"], "veg_and_nonveg"),
    _h("H-JAI-112", "Johari Haveli", "Johari Bazaar", 0.9, 4.3, 3100, ["lift", "wifi", "ac"], "veg"),
    _h("H-JAI-118", "Amer View Palace", "Amer Road", 8.5, 4.8, 5600, ["lift", "pool", "wifi", "ac"], "veg"),
    _h("H-JAI-136", "City Square Suites", "MI Road", 1.8, 4.2, 3500, ["lift", "ac"], "veg"),
    _h("H-JAI-140", "Pink Pearl Residency", "C-Scheme", 2.4, 4.5, 3800, ["lift", "wifi", "ac", "parking"], "veg"),
    _h("H-JAI-127", "Nahargarh Stay", "Brahmpuri", 2.9, 4.1, 2400, ["wifi"], "none"),
    _h("H-JAI-133", "Jal Mahal Inn", "Amer Road", 4.1, 4.4, 3300, ["lift", "wifi"], "veg"),
    _h("H-JAI-109", "Bapu Bazaar Lodge", "Bapu Bazaar", 0.4, 3.9, 1900, ["lift"], "veg"),
    _h("H-JAI-150", "Rambagh Grand", "Bhawani Singh Road", 5.6, 4.9, 9800, ["lift", "pool", "spa", "wifi", "ac"], "veg_and_nonveg"),
]

_ROOM_LAYOUT = [("6", "family", 4, 1.9), ("2", "twin", 2, 1.1), ("5", "suite", 2, 2.2),
                ("3", "double", 2, 1.2), ("1", "single", 1, 0.7)]


def room_options(hotel_id: str) -> list[dict]:
    hotel = next(h for h in HOTELS if h["hotel_id"] == hotel_id)
    n = hotel_id.split("-")[-1]
    return [{"room_id": f"R-{n}-{k}", "room_type": t, "max_guests": g,
             "price_per_night": int(round(hotel["price_from_per_night"] * m, -2))}
            for k, t, g, m in _ROOM_LAYOUT]


ROOM_TYPES = tuple(t for _, t, _, _ in _ROOM_LAYOUT)


def hotel_location(hotel_id: str) -> str:
    return "LOC-" + hotel_id[2:]


VEHICLES = [("HB", "hatchback", 3, 2, 0.5), ("SD", "sedan", 4, 2, 0.65),
            ("SUV", "suv", 6, 5, 1.0), ("TT", "tempo_traveller", 12, 10, 1.8)]
VEHICLE_TYPES = tuple(v[1] for v in VEHICLES)
CAB_BASE_FARE = 1450

ATTRACTIONS = [
    {"attraction_id": "A-JAI-01", "name": "City Palace", "city": "JAI"},
    {"attraction_id": "A-JAI-02", "name": "Amber Fort", "city": "JAI"},
    {"attraction_id": "A-JAI-03", "name": "Hawa Mahal", "city": "JAI"},
    {"attraction_id": "A-JAI-04", "name": "Jantar Mantar", "city": "JAI"},
    {"attraction_id": "A-JAI-05", "name": "Nahargarh Fort", "city": "JAI"},
]
SLOT_TIMES = ("08:00", "10:30", "13:00", "15:30", "17:30")
TICKET_CATEGORIES = ("child", "student", "adult", "senior", "foreign_national")
TICKET_PRICES = {"child": 50, "student": 100, "adult": 200, "senior": 100, "foreign_national": 1100}


def ticket_slots(attraction_id: str, date: str) -> list[dict]:
    n = attraction_id.split("-")[-1]
    return [{"slot_id": f"S-{n}-{date[5:7]}{date[8:]}-{t.replace(':', '')}", "start_time": t,
             "remaining": 40 - 7 * i, "prices": dict(TICKET_PRICES)}
            for i, t in enumerate(SLOT_TIMES)]


TRAVELLERS = [
    {"traveller_id": "T-01", "name": "Arjun Sharma", "relation": "self", "age": 29},
    {"traveller_id": "T-02", "name": "Sunita Sharma", "relation": "mother", "age": 62},
    {"traveller_id": "T-03", "name": "Ramesh Sharma", "relation": "father", "age": 66},
]
TRAVEL_DOCUMENTS = [
    {"traveller_id": "T-01", "document_id": "DOC-T01-AADHAAR", "type": "aadhaar"},
    {"traveller_id": "T-02", "document_id": "DOC-T02-AADHAAR", "type": "aadhaar"},
    {"traveller_id": "T-03", "document_id": "DOC-T03-PAN", "type": "pan"},
]
PAYMENT_METHODS = [{"payment_id": "PAY-UPI-01", "type": "upi"}, {"payment_id": "PAY-CARD-07", "type": "credit_card"}]
