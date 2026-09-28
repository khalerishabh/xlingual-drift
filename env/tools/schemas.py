"""
BFCL-style JSON schemas for the travel tools (Section 8.1), generated per
horizon. Tool names and descriptions are fixed; only parameters and their
`required` lists change with the horizon profile. Schemas stay English
regardless of task language, as in real deployments.
"""

from env.data.flights import MEALS, SEAT_TYPES
from env.tools.horizons import travel_profile

_FILTERS = {
    "depart_after": {"type": "string", "description": "24h HH:MM; keep flights departing strictly after this time."},
    "depart_before": {"type": "string", "description": "24h HH:MM; keep flights departing strictly before this time."},
    "max_price": {"type": "number", "description": "Maximum price in INR."},
}


def _fn(name, description, properties, required):
    return {
        "name": name,
        "description": description,
        "parameters": {"type": "object", "properties": properties, "required": required},
    }


def travel_tool_schemas(horizon: int) -> list[dict]:
    p = travel_profile(horizon)

    if p["city_input"] == "name":
        city_desc = "City name in English, e.g. Chennai."
    else:
        city_desc = "Canonical 3-letter city code from resolve_city, e.g. MAA."

    search_props = {
        "origin": {"type": "string", "description": city_desc},
        "destination": {"type": "string", "description": city_desc},
        "date": {"type": "string", "description": "ISO 8601 date, YYYY-MM-DD."},
    }
    if p["inline_filters"]:
        search_props.update({k: {**v, "description": "Optional. " + v["description"]} for k, v in _FILTERS.items()})

    seat_props = {"flight_id": {"type": "string"}}
    seat_required = ["flight_id"]
    if p["fare_class_required"]:
        seat_props["fare_class"] = {"type": "string", "description": "Fare class from get_fare_rules."}
        seat_required.append("fare_class")

    book_props = {"flight_id": {"type": "string"}}
    book_required = ["flight_id"]
    if p["hold_required"]:
        book_props["hold_token"] = {"type": "string", "description": "Hold token from get_seat_availability for this flight."}
        book_required.append("hold_token")
    if p["passenger_required"]:
        book_props["passenger_id"] = {"type": "string", "description": "Passenger id from get_user_profile."}
        book_required.append("passenger_id")
    if p["addon_ids"]:
        book_props["seat_id"] = {"type": "string", "description": "Seat id from get_seat_map."}
        book_props["meal_code"] = {"type": "string", "description": "Meal code from get_meal_options."}
        book_required += ["seat_id", "meal_code"]
    else:
        book_props["seat_type"] = {"type": "string", "enum": list(SEAT_TYPES), "description": "Seat preference."}
        book_props["meal"] = {"type": "string", "enum": list(MEALS), "description": "Meal preference."}
        book_required += ["seat_type", "meal"]
    if p["docs_payment_required"]:
        book_props["document_id"] = {"type": "string", "description": "Travel document id from get_travel_documents."}
        book_props["payment_id"] = {"type": "string", "description": "Payment method id from get_payment_methods."}
        book_required += ["document_id", "payment_id"]

    return [
        _fn("resolve_city", "Resolve a city name to its canonical 3-letter code.",
            {"name": {"type": "string", "description": "City name in English, e.g. Chennai."}}, ["name"]),
        _fn("search_flights", "Search available flights (sold-out flights are not returned).",
            search_props, ["origin", "destination", "date"]),
        _fn("filter_flights", "Filter the most recent search results by departure time and/or max price.",
            dict(_FILTERS), []),
        _fn("get_fare_rules", "Get the fare class for a flight.",
            {"flight_id": {"type": "string"}}, ["flight_id"]),
        _fn("get_seat_availability", "Check seats on a flight and place a temporary hold.",
            seat_props, seat_required),
        _fn("get_user_profile", "Get the current user's profile, including passenger id.", {}, []),
        _fn("get_seat_map", "List the seats that can be assigned on a flight, with seat ids and types.",
            {"flight_id": {"type": "string"}}, ["flight_id"]),
        _fn("get_meal_options", "List the meals that can be ordered on a flight, with meal codes.",
            {"flight_id": {"type": "string"}}, ["flight_id"]),
        _fn("get_travel_documents", "Get the travel documents on file for a passenger.",
            {"passenger_id": {"type": "string"}}, ["passenger_id"]),
        _fn("get_payment_methods", "List the current user's saved payment methods.", {}, []),
        _fn("book_flight", "Book a flight with the chosen seat and meal. Terminal action.", book_props, book_required),
    ]
