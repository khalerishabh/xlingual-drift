"""
Deterministic travel database. Same input -> same output, always.

Every non-gold flight row is a decoy for one specific early constraint of
its template, so a wrong booking points to the constraint that was lost.
Late constraints (seat type, meal) are forced choices among several
options, so forgetting them changes the terminal state as well.

travel_017  MAA -> DEL 2026-08-22, latest morning flight under Rs 8000
  6E212  09:10  7900  answer
  SG118  11:45  8900  answer if max_price is lost
  AI552  14:20  6200  answer if depart_before is lost
  AI440  06:30  7450  objective decoy; recovery fallback
  AI999  08:00  8600  never the answer
  6E050  10:30  7700  sold out: would be the answer, never returned by search

travel_018  DEL -> BLR 2026-08-25, cheapest flight leaving after 17:00
  AI803  18:05  5600  answer
  6E501  07:15  4200  answer if depart_after is lost
  UK811  20:40  6400  objective decoy; recovery fallback
  6E905  16:30  4900  boundary decoy for depart_after
  SG208  21:30  5300  sold out: would be the answer

travel_019  DEL -> MAA 2026-08-26, earliest flight under Rs 6000
  6E223  08:45  5900  answer
  AI439  06:10  6800  answer if max_price is lost
  SG136  13:20  5200  objective decoy; recovery fallback
  AI541  19:00  4800  never the answer
  6E077  07:30  5500  sold out: would be the answer
"""

CITIES = {
    "MAA": "Chennai",
    "DEL": "Delhi",
    "BLR": "Bengaluru",
}


def _f(fid, o, d, date, t, price, seats, fare):
    return {"flight_id": fid, "origin": o, "destination": d, "date": date,
            "depart_time": t, "price": price, "seats": seats, "fare_class": fare}


FLIGHTS = [
    _f("AI440", "MAA", "DEL", "2026-08-22", "06:30", 7450, 3, "Y-SAVER"),
    _f("6E212", "MAA", "DEL", "2026-08-22", "09:10", 7900, 5, "Y-FLEX"),
    _f("SG118", "MAA", "DEL", "2026-08-22", "11:45", 8900, 2, "Y-FLEX"),
    _f("AI552", "MAA", "DEL", "2026-08-22", "14:20", 6200, 8, "Y-SAVER"),
    _f("AI999", "MAA", "DEL", "2026-08-22", "08:00", 8600, 4, "Y-SAVER"),
    _f("6E050", "MAA", "DEL", "2026-08-22", "10:30", 7700, 0, "Y-FLEX"),

    _f("6E501", "DEL", "BLR", "2026-08-25", "07:15", 4200, 6, "Y-SAVER"),
    _f("6E905", "DEL", "BLR", "2026-08-25", "16:30", 4900, 4, "Y-SAVER"),
    _f("AI803", "DEL", "BLR", "2026-08-25", "18:05", 5600, 5, "Y-FLEX"),
    _f("UK811", "DEL", "BLR", "2026-08-25", "20:40", 6400, 3, "Y-FLEX"),
    _f("SG208", "DEL", "BLR", "2026-08-25", "21:30", 5300, 0, "Y-SAVER"),

    _f("AI439", "DEL", "MAA", "2026-08-26", "06:10", 6800, 4, "Y-FLEX"),
    _f("6E077", "DEL", "MAA", "2026-08-26", "07:30", 5500, 0, "Y-SAVER"),
    _f("6E223", "DEL", "MAA", "2026-08-26", "08:45", 5900, 5, "Y-SAVER"),
    _f("SG136", "DEL", "MAA", "2026-08-26", "13:20", 5200, 6, "Y-FLEX"),
    _f("AI541", "DEL", "MAA", "2026-08-26", "19:00", 4800, 7, "Y-SAVER"),
]

# Same seats on every flight, so a seat id stays valid if the agent has to
# switch flights during recovery. Listing order depends on the route: the
# requested seat type is never listed first, so an agent that forgot its
# preference and takes the first seat lands on a wrong type.
SEAT_MAP = [
    {"seat_id": "14A", "seat_type": "window"},
    {"seat_id": "14F", "seat_type": "window"},
    {"seat_id": "14B", "seat_type": "middle"},
    {"seat_id": "14E", "seat_type": "middle"},
    {"seat_id": "14C", "seat_type": "aisle"},
    {"seat_id": "14D", "seat_type": "aisle"},
]
SEAT_TYPES = ("window", "middle", "aisle")
AISLE_FIRST_ROUTES = {("DEL", "BLR")}


def seat_map_for(flight: dict) -> list[dict]:
    if (flight["origin"], flight["destination"]) in AISLE_FIRST_ROUTES:
        return list(reversed(SEAT_MAP))
    return list(SEAT_MAP)


# The standard meal is listed first for the same reason.
MEAL_OPTIONS = [
    {"meal_code": "NVML", "meal": "non_vegetarian"},
    {"meal_code": "VGML", "meal": "vegetarian"},
    {"meal_code": "JNML", "meal": "jain"},
    {"meal_code": "DBML", "meal": "diabetic"},
    {"meal_code": "VLML", "meal": "vegan"},
]
MEALS = tuple(m["meal"] for m in MEAL_OPTIONS)

USER_PROFILE = {"passenger_id": "P001", "name": "R. Khale"}
TRAVEL_DOCUMENTS = {"P001": {"document_id": "DOC-P001-AADHAAR"}}
PAYMENT_METHODS = [{"payment_id": "PAY-UPI-01", "type": "upi"}]
