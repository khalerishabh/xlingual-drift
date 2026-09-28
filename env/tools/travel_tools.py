"""
Deterministic travel-domain tools (Section 8.1), parameterised by horizon
(env/tools/horizons.py) and interface mode (Section 8.4).

Interface modes:
  strict   values must be the canonical form the schema asks for
           (English city name or 3-letter code; English enum values).
  lenient  spelling/script variants of that same form are accepted via
           env/aliases/city_aliases.json. Lenient never lets a name stand
           in for a code or an id, so it removes MLCL's language-mismatch
           failure without removing a step from the chain.
"""

import json
import re
from pathlib import Path

from env.data.flights import (CITIES, FLIGHTS, MEAL_OPTIONS, MEALS, PAYMENT_METHODS, SEAT_MAP,
                              SEAT_TYPES, TRAVEL_DOCUMENTS, USER_PROFILE, seat_map_for)
from env.tools.horizons import travel_profile
from env.tools.schemas import travel_tool_schemas

_ALIASES = json.loads(
    (Path(__file__).resolve().parent.parent / "aliases" / "city_aliases.json").read_text(encoding="utf-8")
)


def _invert(table: dict) -> dict:
    return {alias: canon for canon, aliases in table.items() for alias in aliases}


_NAME_TO_CODE = {name: code for code, name in CITIES.items()}
_NAME_ALIASES = _invert(_ALIASES["names"])
_CODE_ALIASES = _invert(_ALIASES["codes"])
_SEAT_ALIASES = _invert(_ALIASES["seat_types"])
_MEAL_ALIASES = _invert(_ALIASES["meals"])
_SEATS_BY_ID = {s["seat_id"]: s["seat_type"] for s in SEAT_MAP}
_MEALS_BY_CODE = {m["meal_code"]: m["meal"] for m in MEAL_OPTIONS}
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ToolError(Exception):
    """`error_type` follows the Section 8.6 taxonomy, so injected and organic
    errors look identical to the agent and the verifier."""

    def __init__(self, error_type: str, message: str):
        super().__init__(message)
        self.error_type = error_type
        self.message = message


class TravelTools:
    TERMINAL_TOOL = "book_flight"

    def __init__(self, interface_mode: str = "strict", horizon: int = 6):
        assert interface_mode in ("strict", "lenient")
        self.interface_mode = interface_mode
        self.horizon = horizon
        self.profile = travel_profile(horizon)
        self.schemas = {s["name"]: s for s in travel_tool_schemas(horizon)}
        self._last_results = None
        self._holds = {}
        self._sold_out = set()
        self.bookings = []

    def schema_list(self) -> list[dict]:
        return list(self.schemas.values())

    def mark_sold_out(self, flight_id: str):
        self._sold_out.add(flight_id)

    def _seats(self, flight: dict) -> int:
        return 0 if flight["flight_id"] in self._sold_out else flight["seats"]

    def _flight(self, flight_id: str) -> dict:
        flight = next((f for f in FLIGHTS if f["flight_id"] == flight_id), None)
        if flight is None:
            raise ToolError("validation", f"ValidationError: unknown flight_id '{flight_id}'")
        return flight

    def _lenient(self, value, aliases: dict):
        return aliases.get(value) if self.interface_mode == "lenient" else None

    def _canonical_name(self, value: str):
        return value if value in _NAME_TO_CODE else self._lenient(value, _NAME_ALIASES)

    def _canonical_code(self, value: str):
        return value if value in CITIES else self._lenient(value, _CODE_ALIASES)

    def _enum(self, value, allowed, aliases: dict, field: str) -> str:
        if value in allowed:
            return value
        mapped = self._lenient(value, aliases)
        if mapped is not None:
            return mapped
        raise ToolError("validation", f"ValidationError: '{field}' must be one of {list(allowed)}, got '{value}'")

    def _city_to_code(self, value: str, field: str) -> str:
        code = self._canonical_code(value)
        if code is not None:
            return code
        if self.profile["city_input"] == "name":
            name = self._canonical_name(value)
            if name is not None:
                return _NAME_TO_CODE[name]
            raise ToolError("validation", f"ValidationError: '{field}' must be an English city name, got '{value}'")
        raise ToolError("validation", f"ValidationError: '{field}' must be a city code from resolve_city, got '{value}'")

    @staticmethod
    def _apply_filters(results, depart_after=None, depart_before=None, max_price=None):
        if depart_after is not None:
            results = [f for f in results if f["depart_time"] > depart_after]
        if depart_before is not None:
            results = [f for f in results if f["depart_time"] < depart_before]
        if max_price is not None:
            results = [f for f in results if f["price"] <= max_price]
        return results

    def resolve_city(self, name: str) -> dict:
        canon = self._canonical_name(name)
        if canon is None:
            raise ToolError("validation", f"UnknownCity: '{name}' is not a recognised city")
        return {"code": _NAME_TO_CODE[canon]}

    def search_flights(self, origin, destination, date, depart_after=None, depart_before=None, max_price=None) -> dict:
        o = self._city_to_code(origin, "origin")
        d = self._city_to_code(destination, "destination")
        if not _DATE_RE.match(str(date)):
            raise ToolError("validation", "ValidationError: 'date' must be ISO 8601 (YYYY-MM-DD)")
        results = [
            {"flight_id": f["flight_id"], "depart_time": f["depart_time"], "price": f["price"]}
            for f in FLIGHTS
            if f["origin"] == o and f["destination"] == d and f["date"] == date and self._seats(f) > 0
        ]
        self._last_results = self._apply_filters(results, depart_after, depart_before, max_price)
        return {"flights": self._last_results}

    def filter_flights(self, depart_after=None, depart_before=None, max_price=None) -> dict:
        if self._last_results is None:
            raise ToolError("validation", "ValidationError: call search_flights before filter_flights")
        self._last_results = self._apply_filters(self._last_results, depart_after, depart_before, max_price)
        return {"flights": self._last_results}

    def get_fare_rules(self, flight_id) -> dict:
        return {"flight_id": flight_id, "fare_class": self._flight(flight_id)["fare_class"]}

    def get_seat_availability(self, flight_id, fare_class=None) -> dict:
        flight = self._flight(flight_id)
        if fare_class is not None and fare_class != flight["fare_class"]:
            raise ToolError("validation", f"ValidationError: fare_class '{fare_class}' does not apply to {flight_id}")
        seats = self._seats(flight)
        if seats <= 0:
            raise ToolError("not_found", f"NotFound: flight {flight_id} has 0 seats available")
        token = f"H-{flight_id}-{fare_class or 'STD'}"
        self._holds[token] = flight_id
        return {"flight_id": flight_id, "seats": seats, "hold_token": token}

    def get_user_profile(self) -> dict:
        return dict(USER_PROFILE)

    def get_seat_map(self, flight_id) -> dict:
        return {"flight_id": flight_id, "seats": [dict(s) for s in seat_map_for(self._flight(flight_id))]}

    def get_meal_options(self, flight_id) -> dict:
        self._flight(flight_id)
        return {"flight_id": flight_id, "meals": [dict(m) for m in MEAL_OPTIONS]}

    def get_travel_documents(self, passenger_id) -> dict:
        if passenger_id not in TRAVEL_DOCUMENTS:
            raise ToolError("validation", f"ValidationError: unknown passenger_id '{passenger_id}'")
        return {"passenger_id": passenger_id, **TRAVEL_DOCUMENTS[passenger_id]}

    def get_payment_methods(self) -> dict:
        return {"payment_methods": [dict(p) for p in PAYMENT_METHODS]}

    def book_flight(self, flight_id, hold_token=None, passenger_id=None, seat_type=None, meal=None,
                    seat_id=None, meal_code=None, document_id=None, payment_id=None) -> dict:
        p = self.profile
        flight = self._flight(flight_id)
        if p["hold_required"] and self._holds.get(hold_token) != flight_id:
            raise ToolError("validation", f"ValidationError: hold_token is not valid for flight {flight_id}")
        if p["passenger_required"] and passenger_id != USER_PROFILE["passenger_id"]:
            raise ToolError("validation", f"ValidationError: unknown passenger_id '{passenger_id}'")
        if p["addon_ids"]:
            if seat_id not in _SEATS_BY_ID:
                raise ToolError("validation", f"ValidationError: unknown seat_id '{seat_id}' for {flight_id}")
            if meal_code not in _MEALS_BY_CODE:
                raise ToolError("validation", f"ValidationError: unknown meal_code '{meal_code}' for {flight_id}")
            seat_type, meal = _SEATS_BY_ID[seat_id], _MEALS_BY_CODE[meal_code]
        else:
            seat_type = self._enum(seat_type, SEAT_TYPES, _SEAT_ALIASES, "seat_type")
            meal = self._enum(meal, MEALS, _MEAL_ALIASES, "meal")
        if p["docs_payment_required"]:
            if document_id != TRAVEL_DOCUMENTS.get(passenger_id, {}).get("document_id"):
                raise ToolError("validation", f"ValidationError: document_id is not valid for passenger '{passenger_id}'")
            if payment_id not in {m["payment_id"] for m in PAYMENT_METHODS}:
                raise ToolError("validation", f"ValidationError: unknown payment_id '{payment_id}'")
        if self._seats(flight) <= 0:
            raise ToolError("not_found", f"NotFound: flight {flight_id} has 0 seats available")
        self.bookings.append({"flight_id": flight_id, "price": flight["price"]})
        return {"booking.flight_id": flight_id, "booking.price": flight["price"],
                "booking.seat_type": seat_type, "booking.meal": meal}

    def call(self, tool_name: str, args: dict) -> dict:
        schema = self.schemas.get(tool_name)
        if schema is None:
            raise ToolError("validation", f"ValidationError: unknown tool '{tool_name}'")
        params = schema["parameters"]
        for key in args:
            if key not in params["properties"]:
                raise ToolError("validation", f"ValidationError: unexpected argument '{key}' for {tool_name}")
        for key in params["required"]:
            if key not in args:
                raise ToolError("validation", f"ValidationError: missing required argument '{key}' for {tool_name}")
        return getattr(self, tool_name)(**args)
