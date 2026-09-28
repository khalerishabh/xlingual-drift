"""
How the same trip request needs 11, 17, 24 or 28 tool calls
(docs/TRIP_SPEC.md). The request, the tool names and the correct trip are
identical at every horizon; each level adds values that only another tool
can produce. Seat ids, meal codes, room ids, quote ids and slot ids are
required at every level, so the checkout interface for the late
constraints never changes with the horizon (the gate v2 confound).

  11  searches take English names and inline filters; seat maps, meal
      options, rooms, cab quotes, ticket slots, travellers, checkout
  17  + city codes from resolve_city, separate filter steps for both
      flight searches and the hotel search, attraction id lookup
  24  + fare rules and holds for both flights, rooms, cab and tickets;
      checkout needs every hold token
  28  + hotel location code for the cab drop, travel documents, payment
      method, and a price token from price_itinerary
"""

_L1 = {"city_codes": False, "separate_filters": False, "attraction_ids": False,
       "holds": False, "checkout_extras": False}
_L2 = {**_L1, "city_codes": True, "separate_filters": True, "attraction_ids": True}
_L3 = {**_L2, "holds": True}
_L4 = {**_L3, "checkout_extras": True}

TRIP_LEVELS = {11: _L1, 17: _L2, 24: _L3, 28: _L4}
TRIP_HORIZONS = tuple(sorted(TRIP_LEVELS))


def trip_level(horizon: int) -> dict:
    if horizon not in TRIP_LEVELS:
        raise ValueError(f"no trip level for horizon {horizon}; have {list(TRIP_HORIZONS)}")
    return TRIP_LEVELS[horizon]
