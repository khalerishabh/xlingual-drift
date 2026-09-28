"""
Deterministic flight database. Same input -> same output, always.

travel_017 asks for the latest morning flight under Rs 8000. The table is
built so that every constraint changes the answer when it is dropped,
which is what lets constraint survival be read off the outcome:

  6E212  09:10  7900  gold answer
  SG118  11:45  8900  answer if max_price is lost
  AI552  14:20  6200  answer if depart_before is lost
  AI440  06:30  7450  valid but not latest (objective lost); also the
                      recovery fallback when 6E212 becomes unavailable
  AI999  08:00  8600  over budget, never the answer
  6E050  10:30  7700  would be the answer, but sold out, so search never
                      returns it; guards against leaking sold-out flights
"""

CITIES = {
    "MAA": "Chennai",
    "DEL": "Delhi",
    "BLR": "Bengaluru",
}

FLIGHTS = [
    {"flight_id": "AI440", "origin": "MAA", "destination": "DEL", "date": "2026-08-22",
     "depart_time": "06:30", "price": 7450, "seats": 3, "fare_class": "Y-SAVER"},
    {"flight_id": "6E212", "origin": "MAA", "destination": "DEL", "date": "2026-08-22",
     "depart_time": "09:10", "price": 7900, "seats": 5, "fare_class": "Y-FLEX"},
    {"flight_id": "SG118", "origin": "MAA", "destination": "DEL", "date": "2026-08-22",
     "depart_time": "11:45", "price": 8900, "seats": 2, "fare_class": "Y-FLEX"},
    {"flight_id": "AI552", "origin": "MAA", "destination": "DEL", "date": "2026-08-22",
     "depart_time": "14:20", "price": 6200, "seats": 8, "fare_class": "Y-SAVER"},
    {"flight_id": "AI999", "origin": "MAA", "destination": "DEL", "date": "2026-08-22",
     "depart_time": "08:00", "price": 8600, "seats": 4, "fare_class": "Y-SAVER"},
    {"flight_id": "6E050", "origin": "MAA", "destination": "DEL", "date": "2026-08-22",
     "depart_time": "10:30", "price": 7700, "seats": 0, "fare_class": "Y-FLEX"},
]

USER_PROFILE = {"passenger_id": "P001", "name": "R. Khale"}
