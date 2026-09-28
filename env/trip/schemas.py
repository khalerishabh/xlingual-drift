"""
Tool schemas for the trip domain, generated per horizon. Names and
descriptions are fixed; parameters and `required` change with the level.
Schemas stay English whatever the task language.
"""

from env.trip.levels import trip_level
from env.trip.world import TICKET_CATEGORIES

_FLIGHT_FILTERS = {
    "depart_after": {"type": "string", "description": "24h HH:MM; keep flights departing strictly after this time."},
    "depart_before": {"type": "string", "description": "24h HH:MM; keep flights departing strictly before this time."},
    "nonstop_only": {"type": "boolean", "description": "Keep only flights with no stops."},
}
_HOTEL_FILTERS = {
    "max_distance_km": {"type": "number", "description": "Maximum distance to Hawa Mahal in km."},
    "required_amenities": {"type": "array", "items": {"type": "string"},
                           "description": "Amenities the hotel must have, e.g. [\"lift\", \"pool\"]."},
    "breakfast": {"type": "string", "enum": ["veg", "veg_and_nonveg", "none"],
                  "description": "Breakfast offered by the hotel."},
}
_STR = {"type": "string"}

def _fn(name, description, properties, required):
    return {"name": name, "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required}}

def _optional(props: dict) -> dict:
    return {k: {**v, "description": "Optional. " + v["description"]} for k, v in props.items()}

def trip_tool_schemas(horizon: int) -> list[dict]:
    p = trip_level(horizon)
    city = ("Canonical 3-letter city code from resolve_city, e.g. MAA." if p["city_codes"]
            else "City name in English, e.g. Chennai.")

    search_props = {"origin": {"type": "string", "description": city},
                    "destination": {"type": "string", "description": city},
                    "date": {"type": "string", "description": "ISO 8601 date, YYYY-MM-DD."}}
    hotel_props = {"city": {"type": "string", "description": city},
                   "check_in": {"type": "string", "description": "YYYY-MM-DD."},
                   "check_out": {"type": "string", "description": "YYYY-MM-DD."}}
    if not p["separate_filters"]:
        search_props.update(_optional(_FLIGHT_FILTERS))
        hotel_props.update(_optional(_HOTEL_FILTERS))

    attraction = ({"attraction_id": {"type": "string", "description": "Attraction id from search_attractions."}}
                  if p["attraction_ids"] else
                  {"attraction_name": {"type": "string", "description": "Attraction name in English, e.g. City Palace."}})

    drop_desc = ("Location code from get_hotel_details." if p["checkout_extras"]
                 else "Hotel id from search_hotels.")

    passenger = {"traveller_id": {"type": "string", "description": "Traveller id from get_travellers."},
                 "outbound_seat_id": {"type": "string", "description": "Seat id from get_seat_map for the outbound flight."},
                 "return_seat_id": {"type": "string", "description": "Seat id from get_seat_map for the return flight."},
                 "meal_code": {"type": "string", "description": "Meal code from get_meal_options; served on both flights."},
                 "ticket_category": {"type": "string", "enum": list(TICKET_CATEGORIES),
                                     "description": "Attraction ticket category for this traveller."}}
    passenger_required = list(passenger)
    if p["checkout_extras"]:
        passenger["document_id"] = {"type": "string", "description": "This traveller's document id from get_travel_documents."}
        passenger_required.append("document_id")

    confirm = {
        "outbound_flight_id": _STR, "return_flight_id": _STR,
        "passengers": {"type": "array", "description": "One entry per traveller.",
                       "items": {"type": "object", "properties": passenger, "required": passenger_required}},
        "hotel_id": _STR,
        "rooms": {"type": "array", "description": "Each room booked and the travellers staying in it.",
                  "items": {"type": "object",
                            "properties": {"room_id": {"type": "string", "description": "Room id from get_room_options."},
                                           "traveller_ids": {"type": "array", "items": _STR}},
                            "required": ["room_id", "traveller_ids"]}},
        "cab_quote_id": {"type": "string", "description": "Quote id from get_cab_quotes."},
        "ticket_slot_id": {"type": "string", "description": "Slot id from get_ticket_slots."},
    }
    tokens = {"outbound_hold_token": "hold_flight for the outbound flight",
              "return_hold_token": "hold_flight for the return flight",
              "hotel_hold_token": "hold_rooms", "cab_hold_token": "hold_cab", "ticket_hold_token": "hold_tickets"}
    if p["holds"]:
        confirm.update({k: {"type": "string", "description": f"Hold token from {v}."} for k, v in tokens.items()})
    if p["checkout_extras"]:
        confirm["price_token"] = {"type": "string", "description": "Price token from price_itinerary."}
        confirm["payment_id"] = {"type": "string", "description": "Payment method id from get_payment_methods."}

    return [
        _fn("resolve_city", "Resolve a city name to its canonical 3-letter code.",
            {"name": {"type": "string", "description": "City name in English, e.g. Chennai."}}, ["name"]),
        _fn("search_flights", "Search available flights for all passengers (sold-out flights are not returned).",
            search_props, ["origin", "destination", "date"]),
        _fn("filter_flights", "Filter the most recent flight search results.",
            {**_FLIGHT_FILTERS, "max_price": {"type": "number", "description": "Maximum price per person in INR."}}, []),
        _fn("get_fare_rules", "Get the fare class, baggage and refund rules of a flight.", {"flight_id": _STR}, ["flight_id"]),
        _fn("hold_flight", "Hold seats on a flight for a number of passengers.",
            {"flight_id": _STR, "fare_class": {"type": "string", "description": "Fare class from get_fare_rules."},
             "passengers": {"type": "integer"}}, ["flight_id", "fare_class", "passengers"]),
        _fn("get_seat_map", "Get the seat map of a flight.", {"flight_id": _STR}, ["flight_id"]),
        _fn("get_meal_options", "Get the special meals offered on a flight.", {"flight_id": _STR}, ["flight_id"]),
        _fn("search_hotels", "Search hotels in a city for the given dates.", hotel_props, ["city", "check_in", "check_out"]),
        _fn("filter_hotels", "Filter the most recent hotel search results.", dict(_HOTEL_FILTERS), []),
        _fn("get_room_options", "List the room types of a hotel for the given dates.",
            {"hotel_id": _STR, "check_in": _STR, "check_out": _STR}, ["hotel_id", "check_in", "check_out"]),
        _fn("hold_rooms", "Hold rooms at a hotel.",
            {"hotel_id": _STR, "room_ids": {"type": "array", "items": _STR}}, ["hotel_id", "room_ids"]),
        _fn("get_hotel_details", "Get the address, location code and policies of a hotel.", {"hotel_id": _STR}, ["hotel_id"]),
        _fn("get_cab_quotes", "Get cab quotes for a transfer.",
            {"pickup_location": {"type": "string", "description": "Airport code (3 letters) or hotel location."},
             "drop_location": {"type": "string", "description": drop_desc},
             "date": {"type": "string", "description": "YYYY-MM-DD."},
             "pickup_time": {"type": "string", "description": "24h HH:MM."}},
            ["pickup_location", "drop_location", "date", "pickup_time"]),
        _fn("hold_cab", "Hold a cab quote.", {"quote_id": _STR}, ["quote_id"]),
        _fn("search_attractions", "List attractions in a city.",
            {"city": {"type": "string", "description": city}}, ["city"]),
        _fn("get_ticket_slots", "List entry slots and prices for an attraction on a date.",
            {**attraction, "date": _STR}, [next(iter(attraction)), "date"]),
        _fn("hold_tickets", "Hold tickets for an entry slot.",
            {"slot_id": _STR, "count": {"type": "integer"}}, ["slot_id", "count"]),
        _fn("get_travellers", "Get the travellers saved on the user's account.", {}, []),
        _fn("get_travel_documents", "Get the ID documents saved for each traveller.", {}, []),
        _fn("get_payment_methods", "Get the user's saved payment methods.", {}, []),
        _fn("price_itinerary", "Price the held itinerary and get a price token for checkout.",
            {k: {"type": "string"} for k in tokens}, list(tokens)),
        _fn("confirm_trip", "Confirm and pay for the whole trip in one booking.", confirm, list(confirm)),
    ]
