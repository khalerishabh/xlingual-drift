"""
JSON schemas for the travel-domain tools, in BFCL-style shape (Section 8.1).
These are what an API/local model actually sees as its function-calling
interface -- kept in English regardless of task language, as in real systems.
"""

TOOL_SCHEMAS = {
    "resolve_city": {
        "name": "resolve_city",
        "description": "Resolve a city name (any spelling/script) to its canonical 3-letter code.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "City name as written by the user."}
            },
            "required": ["name"],
        },
    },
    "search_flights": {
        "name": "search_flights",
        "description": "Search flights between two canonical city codes on a given date.",
        "parameters": {
            "type": "object",
            "properties": {
                "origin": {"type": "string", "description": "Canonical origin city code, e.g. MAA."},
                "destination": {"type": "string", "description": "Canonical destination city code, e.g. DEL."},
                "date": {"type": "string", "description": "ISO 8601 date, YYYY-MM-DD."},
            },
            "required": ["origin", "destination", "date"],
        },
    },
    "filter_flights": {
        "name": "filter_flights",
        "description": "Filter the most recent search results by departure time and/or max price.",
        "parameters": {
            "type": "object",
            "properties": {
                "depart_before": {"type": "string", "description": "24h HH:MM cutoff, exclusive."},
                "max_price": {"type": "number", "description": "Maximum price in INR."},
            },
            "required": [],
        },
    },
    "get_seat_availability": {
        "name": "get_seat_availability",
        "description": "Check remaining seats on a specific flight.",
        "parameters": {
            "type": "object",
            "properties": {
                "flight_id": {"type": "string"},
            },
            "required": ["flight_id"],
        },
    },
    "book_flight": {
        "name": "book_flight",
        "description": "Book a flight for a passenger. Terminal action.",
        "parameters": {
            "type": "object",
            "properties": {
                "flight_id": {"type": "string"},
                "passenger_id": {"type": "string"},
            },
            "required": ["flight_id", "passenger_id"],
        },
    },
}
