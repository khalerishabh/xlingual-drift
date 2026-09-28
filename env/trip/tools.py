"""
Deterministic trip-domain tools (docs/TRIP_SPEC.md). Every id and token is
a pure function of its inputs, so the gold chain can be written out
exactly. Checkout validates that every id exists and was issued in this
episode, never that it matches the user's preferences: preference
survival is the verifier's job, and error messages must not leak it.
"""

import re

from env.tools.travel_tools import ToolError
from env.trip.levels import trip_level
from env.trip.schemas import trip_tool_schemas
from env.trip.world import (ATTRACTIONS, CAB_BASE_FARE, CITIES, FLIGHTS, HOTELS, MEAL_OPTIONS, PAYMENT_METHODS,
                            TICKET_CATEGORIES, TICKET_PRICES, TRAVEL_DOCUMENTS, TRAVELLERS, VEHICLES, hotel_location, room_options,
                            seat_map, ticket_slots)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_NAME_TO_CODE = {v: k for k, v in CITIES.items()}
_TRAVELLER_IDS = {t["traveller_id"] for t in TRAVELLERS}
_MEAL_CODES = {m["meal_code"] for m in MEAL_OPTIONS}


def _bad(msg: str):
    raise ToolError("validation", f"ValidationError: {msg}")


def _price_token(tokens: list[str]) -> str:
    return "PT-" + format(sum((i + 1) * ord(ch) for i, ch in enumerate("|".join(tokens))) % 99991, "05d")


class TripTools:
    TERMINAL_TOOL = "confirm_trip"

    def __init__(self, interface_mode: str = "strict", horizon: int = 28):
        assert interface_mode == "strict", "the trip domain has no lenient interface yet"
        self.interface_mode = interface_mode
        self.horizon = horizon
        self.level = trip_level(horizon)
        self.schemas = {s["name"]: s for s in trip_tool_schemas(horizon)}
        self._flight_results = None
        self._hotel_results = None
        self._sold_out = set()
        self._quotes = {}
        self._slots = {}
        self._holds = {}
        self._price_tokens = {}
        self.confirmed = None

    def schema_list(self) -> list[dict]:
        return list(self.schemas.values())

    def mark_sold_out(self, flight_id: str):
        self._sold_out.add(flight_id)

    def _flight(self, flight_id) -> dict:
        f = next((x for x in FLIGHTS if x["flight_id"] == flight_id), None)
        if f is None:
            _bad(f"unknown flight_id '{flight_id}'")
        return f

    def _hotel(self, hotel_id) -> dict:
        h = next((x for x in HOTELS if x["hotel_id"] == hotel_id), None)
        if h is None:
            _bad(f"unknown hotel_id '{hotel_id}'")
        return h

    def _available(self, f) -> bool:
        return f["seats"] > 0 and f["flight_id"] not in self._sold_out

    def _city(self, value, field) -> str:
        if value in CITIES:
            return value
        if not self.level["city_codes"] and value in _NAME_TO_CODE:
            return _NAME_TO_CODE[value]
        _bad(f"'{field}' must be " + ("a city code from resolve_city" if self.level["city_codes"]
                                        else "an English city name") + f", got '{value}'")

    @staticmethod
    def _date(value, field):
        if not _DATE_RE.match(str(value)):
            _bad(f"'{field}' must be ISO 8601 (YYYY-MM-DD)")

    @staticmethod
    def _filter_flights(rows, depart_after=None, depart_before=None, nonstop_only=None, max_price=None):
        if depart_after is not None:
            rows = [f for f in rows if f["depart_time"] > depart_after]
        if depart_before is not None:
            rows = [f for f in rows if f["depart_time"] < depart_before]
        if nonstop_only:
            rows = [f for f in rows if f["stops"] == 0]
        if max_price is not None:
            rows = [f for f in rows if f["price"] <= max_price]
        return rows

    @staticmethod
    def _filter_hotels(rows, max_distance_km=None, required_amenities=None, breakfast=None):
        if max_distance_km is not None:
            rows = [h for h in rows if h["distance_to_hawa_mahal_km"] <= max_distance_km]
        if required_amenities:
            rows = [h for h in rows if set(required_amenities) <= set(h["amenities"])]
        if breakfast is not None:
            rows = [h for h in rows if h["breakfast"] == breakfast]
        return rows

    def resolve_city(self, name):
        if name not in _NAME_TO_CODE:
            raise ToolError("validation", f"UnknownCity: '{name}' is not a recognised city")
        return {"code": _NAME_TO_CODE[name]}

    def search_flights(self, origin, destination, date, **filters):
        o, d = self._city(origin, "origin"), self._city(destination, "destination")
        self._date(date, "date")
        rows = [{k: v for k, v in f.items() if k != "seats"} | {"seats_left": f["seats"]}
                for f in FLIGHTS if f["origin"] == o and f["destination"] == d and f["date"] == date
                and self._available(f)]
        self._flight_results = self._filter_flights(rows, **filters)
        return {"flights": self._flight_results}

    def filter_flights(self, **filters):
        if self._flight_results is None:
            _bad("call search_flights before filter_flights")
        self._flight_results = self._filter_flights(self._flight_results, **filters)
        return {"flights": self._flight_results}

    def get_fare_rules(self, flight_id):
        f = self._flight(flight_id)
        return {"flight_id": flight_id, "fare_class": f["fare_class"], "baggage_kg": f["baggage_kg"],
                "refundable": f["refundable"], "change_fee": 0 if f["refundable"] else 2250}

    def hold_flight(self, flight_id, fare_class, passengers):
        f = self._flight(flight_id)
        if fare_class != f["fare_class"]:
            _bad(f"fare_class '{fare_class}' does not apply to {flight_id}")
        if not self._available(f) or passengers > f["seats"]:
            raise ToolError("not_found", f"NotFound: flight {flight_id} does not have {passengers} seats available")
        token = f"FH-{flight_id}-{fare_class}-{passengers}"
        self._holds[token] = ("flight", flight_id, passengers)
        return {"hold_token": token, "flight_id": flight_id, "passengers": passengers, "expires_in_min": 20}

    def get_seat_map(self, flight_id):
        self._flight(flight_id)
        return {"flight_id": flight_id, "seats": seat_map(flight_id)}

    def get_meal_options(self, flight_id):
        self._flight(flight_id)
        return {"flight_id": flight_id, "meals": [dict(m) for m in MEAL_OPTIONS]}

    def search_hotels(self, city, check_in, check_out, **filters):
        c = self._city(city, "city")
        self._date(check_in, "check_in")
        self._date(check_out, "check_out")
        rows = [dict(h) for h in HOTELS if h["city"] == c]
        self._hotel_results = self._filter_hotels(rows, **filters)
        return {"hotels": self._hotel_results}

    def filter_hotels(self, **filters):
        if self._hotel_results is None:
            _bad("call search_hotels before filter_hotels")
        self._hotel_results = self._filter_hotels(self._hotel_results, **filters)
        return {"hotels": self._hotel_results}

    def get_room_options(self, hotel_id, check_in, check_out):
        self._hotel(hotel_id)
        self._date(check_in, "check_in")
        self._date(check_out, "check_out")
        return {"hotel_id": hotel_id, "check_in": check_in, "check_out": check_out, "rooms": room_options(hotel_id)}

    def hold_rooms(self, hotel_id, room_ids):
        valid = {r["room_id"] for r in room_options(self._hotel(hotel_id)["hotel_id"])}
        for rid in room_ids:
            if rid not in valid:
                _bad(f"room '{rid}' is not a room at {hotel_id}")
        token = f"HH-{hotel_id[2:]}-" + "-".join(r.split("-")[-1] for r in sorted(room_ids))
        self._holds[token] = ("rooms", hotel_id, tuple(sorted(room_ids)))
        return {"hold_token": token, "hotel_id": hotel_id, "room_ids": sorted(room_ids), "expires_in_min": 30}

    def get_hotel_details(self, hotel_id):
        h = self._hotel(hotel_id)
        return {"hotel_id": hotel_id, "name": h["name"], "address": f"{h['area']}, Jaipur",
                "location_code": hotel_location(hotel_id), "check_in_time": "12:00", "check_out_time": "11:00",
                "phone": "+91-141-555-0" + hotel_id[-3:]}

    def get_cab_quotes(self, pickup_location, drop_location, date, pickup_time):
        if pickup_location not in CITIES:
            _bad(f"pickup_location must be an airport code, got '{pickup_location}'")
        if self.level["checkout_extras"]:
            if drop_location not in {hotel_location(h["hotel_id"]) for h in HOTELS}:
                _bad(f"drop_location must be a location code from get_hotel_details, got '{drop_location}'")
        elif drop_location not in {h["hotel_id"] for h in HOTELS}:
            _bad(f"drop_location must be a hotel id, got '{drop_location}'")
        self._date(date, "date")
        if not _TIME_RE.match(str(pickup_time)):
            _bad("'pickup_time' must be 24h HH:MM")
        hotel = drop_location.split("-")[-1]
        quotes = []
        for code, vehicle, seats, bags, mult in VEHICLES:
            qid = f"Q-{code}-{date[5:7]}{date[8:]}-{pickup_time.replace(':', '')}-{hotel}"
            quote = {"quote_id": qid, "vehicle_type": vehicle, "seats": seats, "luggage_bags": bags,
                     "fare": int(round(CAB_BASE_FARE * mult, -1)), "pickup_location": pickup_location,
                     "drop_location": drop_location, "date": date, "pickup_time": pickup_time}
            self._quotes[qid] = quote
            quotes.append(quote)
        return {"quotes": quotes}

    def hold_cab(self, quote_id):
        if quote_id not in self._quotes:
            _bad(f"unknown quote_id '{quote_id}'")
        token = f"CH-{quote_id[2:]}"
        self._holds[token] = ("cab", quote_id, None)
        return {"hold_token": token, "quote_id": quote_id, "expires_in_min": 15}

    def search_attractions(self, city):
        c = self._city(city, "city")
        return {"attractions": [dict(a, open_time="08:00", close_time="18:00") for a in ATTRACTIONS if a["city"] == c]}

    def get_ticket_slots(self, date, attraction_id=None, attraction_name=None):
        if attraction_name is not None:
            a = next((x for x in ATTRACTIONS if x["name"] == attraction_name), None)
            if a is None:
                _bad(f"unknown attraction '{attraction_name}'")
        else:
            a = next((x for x in ATTRACTIONS if x["attraction_id"] == attraction_id), None)
            if a is None:
                _bad(f"unknown attraction_id '{attraction_id}'")
        self._date(date, "date")
        slots = ticket_slots(a["attraction_id"], date)
        for s in slots:
            self._slots[s["slot_id"]] = {"attraction_id": a["attraction_id"], "date": date, "start_time": s["start_time"]}
        return {"attraction_id": a["attraction_id"], "name": a["name"], "date": date, "slots": slots}

    def hold_tickets(self, slot_id, count):
        if slot_id not in self._slots:
            _bad(f"unknown slot_id '{slot_id}'")
        token = f"TH-{slot_id[2:]}-{count}"
        self._holds[token] = ("tickets", slot_id, count)
        return {"hold_token": token, "slot_id": slot_id, "count": count, "expires_in_min": 15}

    def get_travellers(self):
        return {"travellers": [dict(t) for t in TRAVELLERS]}

    def get_travel_documents(self):
        return {"documents": [dict(d) for d in TRAVEL_DOCUMENTS]}

    def get_payment_methods(self):
        return {"payment_methods": [dict(p) for p in PAYMENT_METHODS]}

    def price_itinerary(self, **tokens):
        for k, v in tokens.items():
            if v not in self._holds:
                _bad(f"{k} '{v}' is not an active hold")
        token = _price_token([tokens[k] for k in sorted(tokens)])
        self._price_tokens[token] = dict(tokens)
        return {"price_token": token, "valid_for_min": 10}

    def _check_holds(self, a: dict, rooms: list):
        expect = {"outbound_hold_token": ("flight", a["outbound_flight_id"], 3),
                  "return_hold_token": ("flight", a["return_flight_id"], 3),
                  "hotel_hold_token": ("rooms", a["hotel_id"], tuple(sorted(rooms))),
                  "cab_hold_token": ("cab", a["cab_quote_id"], None),
                  "ticket_hold_token": ("tickets", a["ticket_slot_id"], 3)}
        for key, want in expect.items():
            if self._holds.get(a[key]) != want:
                _bad(f"{key} '{a[key]}' does not hold what is being booked")

    def confirm_trip(self, **a):
        out, ret = self._flight(a["outbound_flight_id"]), self._flight(a["return_flight_id"])
        for f in (out, ret):
            if not self._available(f):
                raise ToolError("not_found", f"NotFound: flight {f['flight_id']} has no seats available")
        pax = a["passengers"]
        if not isinstance(pax, list) or sorted(p.get("traveller_id") for p in pax) != sorted(_TRAVELLER_IDS):
            _bad("passengers must list each traveller from get_travellers exactly once")
        docs = {d["traveller_id"]: d["document_id"] for d in TRAVEL_DOCUMENTS}
        for leg, f in (("outbound", out), ("return", ret)):
            smap = {s["seat_id"]: s for s in seat_map(f["flight_id"])}
            chosen = [p.get(f"{leg}_seat_id") for p in pax]
            for sid in chosen:
                if sid not in smap or not smap[sid]["available"]:
                    _bad(f"seat '{sid}' is not an available seat on {f['flight_id']}")
            if len(set(chosen)) != len(chosen):
                _bad(f"the same seat is assigned twice on {f['flight_id']}")
        for p in pax:
            if p.get("meal_code") not in _MEAL_CODES:
                _bad(f"unknown meal_code '{p.get('meal_code')}'")
            if p.get("ticket_category") not in TICKET_CATEGORIES:
                _bad(f"ticket_category must be one of {list(TICKET_CATEGORIES)}")
            if self.level["checkout_extras"] and p.get("document_id") != docs[p["traveller_id"]]:
                _bad(f"document_id is not valid for traveller '{p['traveller_id']}'")

        hotel = self._hotel(a["hotel_id"])
        rooms = {r["room_id"]: r for r in room_options(hotel["hotel_id"])}
        occupants = []
        for r in a["rooms"]:
            if r.get("room_id") not in rooms:
                _bad(f"room '{r.get('room_id')}' is not a room at {hotel['hotel_id']}")
            if len(r.get("traveller_ids", [])) > rooms[r["room_id"]]["max_guests"]:
                _bad(f"too many guests for room '{r['room_id']}'")
            occupants += r.get("traveller_ids", [])
        if sorted(occupants) != sorted(_TRAVELLER_IDS):
            _bad("rooms must place each traveller exactly once")
        room_ids = [r["room_id"] for r in a["rooms"]]
        if len(set(room_ids)) != len(room_ids):
            _bad("the same room is listed twice")

        if a["cab_quote_id"] not in self._quotes:
            _bad(f"unknown cab_quote_id '{a['cab_quote_id']}'")
        if a["ticket_slot_id"] not in self._slots:
            _bad(f"unknown ticket_slot_id '{a['ticket_slot_id']}'")
        if self.level["holds"]:
            self._check_holds(a, room_ids)
        if self.level["checkout_extras"]:
            if a["payment_id"] not in {m["payment_id"] for m in PAYMENT_METHODS}:
                _bad(f"unknown payment_id '{a['payment_id']}'")
            tokens = self._price_tokens.get(a["price_token"])
            if tokens is None or any(tokens.get(k) != a[k] for k in tokens):
                _bad("price_token does not match the held itinerary")

        nights = 2
        total = (3 * (out["price"] + ret["price"]) + nights * sum(rooms[r]["price_per_night"] for r in room_ids)
                 + self._quotes[a["cab_quote_id"]]["fare"]
                 + sum(TICKET_PRICES[p["ticket_category"]] for p in pax))
        self.confirmed = {"args": a, "quote": self._quotes[a["cab_quote_id"]], "slot": self._slots[a["ticket_slot_id"]]}
        return {"status": "confirmed", "confirmation_id": "TRIP-" + _price_token(sorted(room_ids) + [out["flight_id"], ret["flight_id"]])[3:],
                "total_price_inr": total}

    def call(self, tool_name: str, args: dict) -> dict:
        schema = self.schemas.get(tool_name)
        if schema is None:
            _bad(f"unknown tool '{tool_name}'")
        params = schema["parameters"]
        for key in args:
            if key not in params["properties"]:
                _bad(f"unexpected argument '{key}' for {tool_name}")
        for key in params["required"]:
            if key not in args:
                _bad(f"missing required argument '{key}' for {tool_name}")
        return getattr(self, tool_name)(**args)
