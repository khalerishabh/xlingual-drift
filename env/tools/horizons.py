"""
How the same request needs 2, 4, 6 or 8 tool calls (Section 8.2).

The request text is identical at every horizon, and so is the set of tool
names the agent sees. What changes is the data each tool requires: a
value that only another tool can produce (a city code, a hold token, a
fare class, a passenger id) forces that tool into the chain. The agent
learns what is required from the schemas, never from error messages, so
horizon stays separate from recovery (RQ4).

Travel chains for travel_017:
  h2  search_flights(names, filters) -> book_flight
  h4  resolve_city x2 -> search_flights(codes, filters) -> book_flight
  h6  resolve_city x2 -> search_flights(codes) -> filter_flights
      -> get_seat_availability -> book_flight(hold_token)
  h8  h6 + get_fare_rules before availability (fare_class) and
      get_user_profile before booking (passenger_id)
"""

TRAVEL_PROFILES = {
    2: {"city_input": "name", "inline_filters": True, "hold_required": False,
        "fare_class_required": False, "passenger_required": False},
    4: {"city_input": "code", "inline_filters": True, "hold_required": False,
        "fare_class_required": False, "passenger_required": False},
    6: {"city_input": "code", "inline_filters": False, "hold_required": True,
        "fare_class_required": False, "passenger_required": False},
    8: {"city_input": "code", "inline_filters": False, "hold_required": True,
        "fare_class_required": True, "passenger_required": True},
}


def travel_profile(horizon: int) -> dict:
    if horizon not in TRAVEL_PROFILES:
        raise ValueError(f"no travel profile for horizon {horizon}; have {sorted(TRAVEL_PROFILES)}")
    return TRAVEL_PROFILES[horizon]
