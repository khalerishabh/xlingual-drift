"""
Deterministic travel-domain tools (Section 8.1). Every call with the same
arguments returns the same result -- that determinism is what lets the
verifier grade a trajectory by diffing against a gold trajectory instead of
using a human or an LLM judge.

Two interface modes (Section 8.4):
  - strict:  the canonical city code is required exactly.
  - lenient: env/aliases/city_aliases.json is consulted first, so
             "Chennai" / "chennai" / "चेन्नई" / "சென்னை"
             all resolve. This is what neutralises MLCL's parameter-value
             language mismatch failure for RQ2.
"""

import json
from pathlib import Path

from env.data.flights import CITIES, FLIGHTS, PASSENGERS

_ALIASES_PATH = Path(__file__).resolve().parent.parent / "aliases" / "city_aliases.json"
with open(_ALIASES_PATH, "r", encoding="utf-8") as f:
    _RAW_ALIASES = json.load(f)

# Build alias -> canonical code lookup, skipping the "_comment" key.
_ALIAS_TO_CODE = {}
for code, spellings in _RAW_ALIASES.items():
    if code.startswith("_"):
        continue
    for spelling in spellings:
        _ALIAS_TO_CODE[spelling] = code
    _ALIAS_TO_CODE[code] = code  # the code itself always resolves


class ToolError(Exception):
    """
    Raised by a tool. `error_type` matches the Section 8.6 injection
    taxonomy (transient / validation / not_found) so injected and organic
    errors look identical to the agent and to the verifier.
    """

    def __init__(self, error_type: str, message: str):
        super().__init__(message)
        self.error_type = error_type
        self.message = message


class TravelTools:
    """
    Holds mutable per-run state (last search results) so tool calls can
    depend on prior calls, exactly like a real multi-step API session.
    One instance per run -- never shared across runs or seeds.
    """

    def __init__(self, interface_mode: str = "strict"):
        assert interface_mode in ("strict", "lenient")
        self.interface_mode = interface_mode
        self._last_results = None
        self._bookings = []

    # -- tools -------------------------------------------------------

    def resolve_city(self, name: str) -> dict:
        if self.interface_mode == "lenient" and name in _ALIAS_TO_CODE:
            return {"code": _ALIAS_TO_CODE[name]}
        if name in CITIES:
            return {"code": name}
        raise ToolError("validation", f"UnknownCity: '{name}' is not a recognised city")

    def search_flights(self, origin: str, destination: str, date: str) -> dict:
        if origin not in CITIES or destination not in CITIES:
            raise ToolError(
                "validation",
                "ValidationError: 'origin'/'destination' must be canonical city codes",
            )
        results = [
            f for f in FLIGHTS
            if f["origin"] == origin and f["destination"] == destination and f["date"] == date
        ]
        self._last_results = results
        return {"flights": results}

    def filter_flights(self, depart_before: str = None, max_price: float = None) -> dict:
        if self._last_results is None:
            raise ToolError("validation", "ValidationError: call search_flights before filter_flights")
        results = self._last_results
        if depart_before is not None:
            results = [f for f in results if f["depart_time"] < depart_before]
        if max_price is not None:
            results = [f for f in results if f["price"] <= max_price]
        self._last_results = results
        return {"flights": results}

    def get_seat_availability(self, flight_id: str) -> dict:
        flight = next((f for f in FLIGHTS if f["flight_id"] == flight_id), None)
        if flight is None:
            raise ToolError("validation", f"ValidationError: unknown flight_id '{flight_id}'")
        if flight["seats"] <= 0:
            raise ToolError("not_found", f"NotFound: flight {flight_id} has 0 seats available")
        return {"flight_id": flight_id, "seats": flight["seats"]}

    def book_flight(self, flight_id: str, passenger_id: str) -> dict:
        if passenger_id not in PASSENGERS:
            raise ToolError("validation", f"ValidationError: unknown passenger_id '{passenger_id}'")
        flight = next((f for f in FLIGHTS if f["flight_id"] == flight_id), None)
        if flight is None:
            raise ToolError("validation", f"ValidationError: unknown flight_id '{flight_id}'")
        if flight["seats"] <= 0:
            raise ToolError("not_found", f"NotFound: flight {flight_id} has 0 seats available")
        booking = {"flight_id": flight_id, "price": flight["price"], "passenger_id": passenger_id}
        self._bookings.append(booking)
        return {"booking.flight_id": flight_id, "booking.price": flight["price"]}

    # -- dispatch ------------------------------------------------------

    def call(self, tool_name: str, args: dict) -> dict:
        method = getattr(self, tool_name, None)
        if method is None:
            raise ToolError("validation", f"ValidationError: unknown tool '{tool_name}'")
        return method(**args)
