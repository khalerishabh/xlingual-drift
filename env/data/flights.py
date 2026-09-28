"""
Deterministic in-memory flight database. Same input -> same output, always.
Kept as plain Python data (not SQLite) for this scaffold; swap for SQLite in
Phase 2 if the tool count grows enough to need joins/indexing.
"""

# Canonical city codes. Non-English/aliased spellings are resolved to these
# via env/aliases/city_aliases.json, never handled here.
CITIES = {
    "MAA": "Chennai",
    "DEL": "Delhi",
    "BLR": "Bengaluru",
}

# Flight rows: deliberately includes a decoy (AI440 goes 0 seats after the
# gold path books it once) so failure injection has somewhere real to inject.
FLIGHTS = [
    {"flight_id": "AI440", "origin": "MAA", "destination": "DEL", "date": "2026-08-22",
     "depart_time": "06:30", "price": 7450, "seats": 3},
    {"flight_id": "6E212", "origin": "MAA", "destination": "DEL", "date": "2026-08-22",
     "depart_time": "09:10", "price": 7900, "seats": 5},
    {"flight_id": "SG118", "origin": "MAA", "destination": "DEL", "date": "2026-08-22",
     "depart_time": "11:45", "price": 6800, "seats": 0},
    {"flight_id": "AI552", "origin": "MAA", "destination": "DEL", "date": "2026-08-22",
     "depart_time": "14:20", "price": 6200, "seats": 8},
    # Over budget but still "morning" -- only reachable if the price cap is
    # dropped from filter_flights. Used to demonstrate a constraint-drift
    # failure: an agent that forgets the budget mid-execution can still
    # pick a flight that satisfies every OTHER constraint.
    {"flight_id": "AI999", "origin": "MAA", "destination": "DEL", "date": "2026-08-22",
     "depart_time": "08:00", "price": 8600, "seats": 4},
]

PASSENGERS = {
    "P001": {"name": "R. Khale"},
}
