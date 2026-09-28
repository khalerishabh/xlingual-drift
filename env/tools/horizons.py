"""
How the same request needs 2 to 12 tool calls (Section 8.2).

The request text is identical at every horizon, and so is the set of tool
names the agent sees. What changes is the data each tool requires: a value
that only another tool can produce forces that tool into the chain. The
agent learns what is required from the schemas, never from error messages,
so horizon stays separate from recovery (RQ4).

Early constraints (time window, budget, objective) are applied when the
flight is chosen. Late constraints (seat type, meal) are committed only in
the final booking call, so the number of steps they must be carried grows
with the horizon (Section 15.11).

Gold chains:
  h2   search_flights(names, filters) -> book_flight
  h4   resolve_city x2 -> search_flights(codes, filters) -> book_flight
  h6   resolve x2 -> search -> filter_flights -> get_seat_availability
       -> book_flight(hold_token)
  h8   h6 + get_fare_rules (fare_class) + get_user_profile (passenger_id)
  h10  h8 + get_seat_map (seat_id) + get_meal_options (meal_code);
       booking takes ids instead of seat type / meal names
  h12  h10 + get_travel_documents (document_id) + get_payment_methods
       (payment_id)
"""

_BASE = {"city_input": "code", "inline_filters": False, "hold_required": False,
         "fare_class_required": False, "passenger_required": False,
         "addon_ids": False, "docs_payment_required": False}

TRAVEL_PROFILES = {
    2: {**_BASE, "city_input": "name", "inline_filters": True},
    4: {**_BASE, "inline_filters": True},
    6: {**_BASE, "hold_required": True},
    8: {**_BASE, "hold_required": True, "fare_class_required": True, "passenger_required": True},
    10: {**_BASE, "hold_required": True, "fare_class_required": True, "passenger_required": True,
         "addon_ids": True},
    12: {**_BASE, "hold_required": True, "fare_class_required": True, "passenger_required": True,
         "addon_ids": True, "docs_payment_required": True},
}

HORIZONS = tuple(sorted(TRAVEL_PROFILES))


def travel_profile(horizon: int) -> dict:
    if horizon not in TRAVEL_PROFILES:
        raise ValueError(f"no travel profile for horizon {horizon}; have {list(HORIZONS)}")
    return TRAVEL_PROFILES[horizon]
