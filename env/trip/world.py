"""
The Jaipur world (docs/TRIP_SPEC.md): every flight, hotel, room, cab and
attraction the trip tools can return. Several templates share one world
and differ only in what the request asks for, so decoys are rows here that
a dropped constraint would select.

Listing order is deliberate: results are not sorted by any objective, so
the agent has to compute the answer, and no requested option is the one a
"take the first row" shortcut would pick.
"""

CITIES = {"MAA": "Chennai", "JAI": "Jaipur", "DEL": "Delhi", "BLR": "Bengaluru", "HYD": "Hyderabad",
          "BOM": "Mumbai", "CCU": "Kolkata"}


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

    _f("6E4512", "IndiGo", "BLR", "JAI", "2026-11-06", "06:10", "08:55", 0, 6200, "R-SAVER"),
    _f("SG411", "SpiceJet", "BLR", "JAI", "2026-11-06", "07:15", "10:00", 0, 6400, "Q-SAVER"),
    _f("6E4521", "IndiGo", "BLR", "JAI", "2026-11-06", "08:50", "11:35", 0, 6900, "R-SAVER"),
    _f("AI4510", "Air India", "BLR", "JAI", "2026-11-06", "09:40", "14:20", 1, 5100, "T-ECO", via="DEL", baggage=25),
    _f("UK401", "Vistara", "BLR", "JAI", "2026-11-06", "11:30", "14:15", 0, 7300, "V-ECO", baggage=20, refundable=True),
    _f("QP1260", "Akasa Air", "BLR", "JAI", "2026-11-06", "13:05", "15:50", 0, 5800, "S-LITE"),
    _f("IX410", "Air India Express", "BLR", "JAI", "2026-11-06", "18:20", "21:05", 0, 5600, "X-VALUE"),

    _f("6E4522", "IndiGo", "JAI", "BLR", "2026-11-08", "20:30", "23:15", 0, 7600, "R-SAVER"),
    _f("IX411", "Air India Express", "JAI", "BLR", "2026-11-08", "12:10", "14:55", 0, 5400, "X-VALUE"),
    _f("6E4513", "IndiGo", "JAI", "BLR", "2026-11-08", "15:20", "18:05", 0, 5900, "R-SAVER"),
    _f("QP1261", "Akasa Air", "JAI", "BLR", "2026-11-08", "17:45", "20:30", 0, 6300, "S-LITE"),
    _f("SG412", "SpiceJet", "JAI", "BLR", "2026-11-08", "19:05", "21:50", 0, 6700, "Q-SAVER"),
    _f("AI4511", "Air India", "JAI", "BLR", "2026-11-08", "20:50", "02:10", 1, 5200, "T-ECO", via="DEL", baggage=25),
    _f("UK402", "Vistara", "JAI", "BLR", "2026-11-08", "21:40", "00:25", 0, 6100, "V-ECO", baggage=20, refundable=True),

    _f("6E7132", "IndiGo", "HYD", "JAI", "2026-11-20", "05:55", "08:20", 0, 4300, "R-SAVER"),
    _f("AI7120", "Air India", "HYD", "JAI", "2026-11-20", "07:50", "12:30", 1, 4100, "T-ECO", via="DEL", baggage=25),
    _f("UK712", "Vistara", "HYD", "JAI", "2026-11-20", "08:25", "10:50", 0, 6200, "V-ECO", baggage=20, refundable=True),
    _f("6E7123", "IndiGo", "HYD", "JAI", "2026-11-20", "09:40", "12:05", 0, 4950, "R-SAVER"),
    _f("SG720", "SpiceJet", "HYD", "JAI", "2026-11-20", "11:15", "13:40", 0, 5300, "Q-SAVER"),
    _f("QP1470", "Akasa Air", "HYD", "JAI", "2026-11-20", "14:30", "16:55", 0, 5150, "S-LITE"),
    _f("IX713", "Air India Express", "HYD", "JAI", "2026-11-20", "19:45", "22:10", 0, 5600, "X-VALUE"),

    _f("6E7124", "IndiGo", "JAI", "HYD", "2026-11-22", "16:40", "19:05", 0, 7400, "R-SAVER"),
    _f("6E7133", "IndiGo", "JAI", "HYD", "2026-11-22", "13:10", "15:35", 0, 5200, "R-SAVER"),
    _f("AI7121", "Air India", "JAI", "HYD", "2026-11-22", "16:15", "21:00", 1, 4800, "T-ECO", via="DEL", baggage=25),
    _f("SG721", "SpiceJet", "JAI", "HYD", "2026-11-22", "17:25", "19:50", 0, 6300, "Q-SAVER"),
    _f("UK713", "Vistara", "JAI", "HYD", "2026-11-22", "18:50", "21:15", 0, 5900, "V-ECO", baggage=20, refundable=True),
    _f("QP1471", "Akasa Air", "JAI", "HYD", "2026-11-22", "20:10", "22:35", 0, 5500, "S-LITE"),
    _f("IX714", "Air India Express", "JAI", "HYD", "2026-11-22", "21:05", "23:30", 0, 5000, "X-VALUE"),

    _f("6E5051", "IndiGo", "BOM", "JAI", "2026-12-04", "06:30", "08:15", 0, 5200, "R-SAVER"),
    _f("AI5050", "Air India", "BOM", "JAI", "2026-12-04", "08:10", "12:40", 1, 3900, "T-ECO", via="DEL", baggage=25),
    _f("6E5015", "IndiGo", "BOM", "JAI", "2026-12-04", "09:20", "11:05", 0, 5600, "R-SAVER"),
    _f("SG505", "SpiceJet", "BOM", "JAI", "2026-12-04", "10:45", "12:30", 0, 5100, "Q-SAVER"),
    _f("UK515", "Vistara", "BOM", "JAI", "2026-12-04", "12:30", "14:15", 0, 6300, "V-ECO", baggage=20, refundable=True),
    _f("QP1505", "Akasa Air", "BOM", "JAI", "2026-12-04", "16:40", "18:25", 0, 4700, "S-LITE"),
    _f("IX515", "Air India Express", "BOM", "JAI", "2026-12-04", "20:15", "22:00", 0, 4500, "X-VALUE"),

    _f("6E5016", "IndiGo", "JAI", "BOM", "2026-12-06", "19:35", "21:20", 0, 5900, "R-SAVER"),
    _f("QP1506", "Akasa Air", "JAI", "BOM", "2026-12-06", "12:20", "14:05", 0, 4600, "S-LITE"),
    _f("6E5052", "IndiGo", "JAI", "BOM", "2026-12-06", "14:10", "15:55", 0, 4900, "R-SAVER"),
    _f("SG506", "SpiceJet", "JAI", "BOM", "2026-12-06", "18:05", "19:50", 0, 5300, "Q-SAVER"),
    _f("AI5051", "Air India", "JAI", "BOM", "2026-12-06", "19:50", "00:40", 1, 4200, "T-ECO", via="DEL", baggage=25),
    _f("UK516", "Vistara", "JAI", "BOM", "2026-12-06", "20:45", "22:30", 0, 5000, "V-ECO", baggage=20, refundable=True),
    _f("IX516", "Air India Express", "JAI", "BOM", "2026-12-06", "21:30", "23:15", 0, 4800, "X-VALUE"),

    _f("6E6211", "IndiGo", "CCU", "JAI", "2026-12-18", "05:50", "08:20", 0, 6400, "R-SAVER"),
    _f("AI6210", "Air India", "CCU", "JAI", "2026-12-18", "06:40", "11:50", 1, 4800, "T-ECO", via="DEL", baggage=25),
    _f("UK621", "Vistara", "CCU", "JAI", "2026-12-18", "07:05", "09:35", 0, 7200, "V-ECO", baggage=20, refundable=True),
    _f("6E6121", "IndiGo", "CCU", "JAI", "2026-12-18", "08:15", "10:45", 0, 5700, "R-SAVER"),
    _f("SG621", "SpiceJet", "CCU", "JAI", "2026-12-18", "09:55", "12:25", 0, 6100, "Q-SAVER"),
    _f("IX612", "Air India Express", "CCU", "JAI", "2026-12-18", "13:30", "16:00", 0, 5200, "X-VALUE"),
    _f("QP1612", "Akasa Air", "CCU", "JAI", "2026-12-18", "17:20", "19:50", 0, 5900, "S-LITE"),

    _f("6E6122", "IndiGo", "JAI", "CCU", "2026-12-20", "15:25", "17:55", 0, 7700, "R-SAVER"),
    _f("6E6212", "IndiGo", "JAI", "CCU", "2026-12-20", "11:40", "14:10", 0, 6000, "R-SAVER"),
    _f("AI6211", "Air India", "JAI", "CCU", "2026-12-20", "15:10", "20:30", 1, 5100, "T-ECO", via="DEL", baggage=25),
    _f("SG622", "SpiceJet", "JAI", "CCU", "2026-12-20", "16:50", "19:20", 0, 6800, "Q-SAVER"),
    _f("UK622", "Vistara", "JAI", "CCU", "2026-12-20", "18:30", "21:00", 0, 6500, "V-ECO", baggage=20, refundable=True),
    _f("IX613", "Air India Express", "JAI", "CCU", "2026-12-20", "20:45", "23:15", 0, 5900, "X-VALUE"),
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
    _h("H-JAI-145", "Chandpole Heritage", "Chandpole", 1.5, 4.4, 4200, ["wifi", "ac", "pool"], "veg"),
    _h("H-JAI-158", "Sindhi Camp Suites", "Sindhi Camp", 2.7, 4.4, 2900, ["lift", "wifi", "parking"], "veg_and_nonveg"),
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
