"""
Travel domain (Experiment 2). The family trip from the RQ1 trip experiment
(env/trip, tasks/trip_templates/trip_001..005), at one fixed tool level for
every format (the shortest trip level: English city names, separate filter
steps, no holds), so the formats differ only in how much is asked. The
terminal call is confirm_booking, which books only the components a format
asks for.

Stages (long format order):
  outbound   the outbound flight (filters plus an objective)
  return     the return flight
  budget     all six tickets within a total (coupled: changes the return pick)
  hotel      the hotel (filters plus an objective)
  rooms      room types and who sleeps where
  cab        airport pickup at the landing time of the chosen outbound flight
             (carried) to the chosen hotel (carried), right vehicle
  tickets    attraction slot (filter plus objective) and ticket categories
  submit     anchors: per-traveller seat type on every flight and meal,
             committed only in confirm_booking
"""

import json
from pathlib import Path

from env.exp2.core import S, check, step_of, summarize
from env.trip import solver
from env.trip.chain import assign_seats, quote_id
from env.trip.schemas import trip_tool_schemas
from env.trip.tools import TripTools
from env.trip.world import CITIES, FLIGHTS, MEAL_OPTIONS, TRAVELLERS, room_options, seat_map

DOMAIN = "travel"
ROOT = Path(__file__).resolve().parents[2]
LEVEL = 14
SCENARIOS = [{"id": i, "template": f"trip_00{i}"} for i in range(1, 6)]
FORMATS = {
    "short": ["outbound", "submit"],
    "medium": ["outbound", "return", "hotel", "rooms", "submit"],
    "long": ["outbound", "return", "budget", "hotel", "rooms", "cab", "tickets", "submit"],
}
ANCHOR_STAGE = "submit"
MEAL_CODE = {m["meal"]: m["meal_code"] for m in MEAL_OPTIONS}
TIDS = sorted(t["traveller_id"] for t in TRAVELLERS)


def generate(scenario):
    t = json.loads((ROOT / "tasks" / "trip_templates" / f"{scenario['template']}.json").read_text(encoding="utf-8"))
    return {"scenario": scenario["id"], "source_template": t["template_id"], "session_date": t["session_date"],
            "constraints": t["constraints"]}


def cons_for(world, stages):
    c = json.loads(json.dumps(world["constraints"]))
    if "budget" not in stages:
        c.pop("flight_budget_total", None)
    return c


def _flight(fid):
    return next(f for f in FLIGHTS if f["flight_id"] == fid)


def solve(world, stages):
    c = cons_for(world, stages)
    ans = solver.answer(c)
    prefs = ans["travellers"]
    plan = {"outbound": ans["outbound_flight_id"], "travellers": prefs}
    if "return" in stages:
        plan["return"] = ans["return_flight_id"]
    if "hotel" in stages:
        plan["hotel_id"] = ans["hotel_id"]
        plan["rooms"] = [(rid, list(tids)) for rid, tids in ans["rooms"]]
    if "cab" in stages:
        plan["cab"] = dict(ans["cab"])
    if "tickets" in stages:
        plan["ticket_slot_id"] = ans["ticket_slot_id"]
    return plan


def chain(world, stages, plan):
    c = cons_for(world, stages)
    steps = []

    def add(tool, **args):
        steps.append({"tool": tool, "args": args})

    legs = [("outbound", plan["outbound"])] + ([("return", plan["return"])] if "return" in plan else [])
    for leg, fid in legs:
        lc = c[leg]
        add("search_flights", origin=CITIES[lc["origin"]], destination=CITIES[lc["destination"]], date=lc["date"])
        filters = {k: lc[k] for k in ("depart_after", "depart_before") if k in lc}
        if lc.get("nonstop"):
            filters["nonstop_only"] = True
        add("filter_flights", **filters)
        add("get_seat_map", flight_id=fid)
        if leg == "outbound":
            add("get_meal_options", flight_id=fid)
    if "hotel_id" in plan:
        h = c["hotel"]
        add("search_hotels", city=CITIES[h["city"]], check_in=h["check_in"], check_out=h["check_out"])
        hf = {}
        if "max_distance_km" in h:
            hf["max_distance_km"] = h["max_distance_km"]
        if h.get("amenities"):
            hf["required_amenities"] = list(h["amenities"])
        if "breakfast" in h:
            hf["breakfast"] = h["breakfast"]
        add("filter_hotels", **hf)
        add("get_room_options", hotel_id=plan["hotel_id"], check_in=h["check_in"], check_out=h["check_out"])
    if "cab" in plan:
        cab = plan["cab"]
        add("get_cab_quotes", pickup_location=cab["pickup_location"], drop_location=plan["hotel_id"], date=cab["date"],
            pickup_time=cab["pickup_time"])
    if "ticket_slot_id" in plan:
        t = c["tickets"]
        add("get_ticket_slots", attraction_name=t["attraction_name"], date=t["date"])
    add("get_travellers")
    add("confirm_booking", **booking_args(plan))
    return steps


def booking_args(plan):
    prefs = plan["travellers"]
    seats = {leg: assign_seats(plan[leg], {tid: p["seat"] for tid, p in prefs.items()})
             for leg in ("outbound", "return") if leg in plan}
    pax = []
    for tid in sorted(prefs):
        p = {"traveller_id": tid, "outbound_seat_id": seats["outbound"][tid], "meal_code": MEAL_CODE[prefs[tid]["meal"]]}
        if "return" in seats:
            p["return_seat_id"] = seats["return"][tid]
        if "ticket_slot_id" in plan:
            p["ticket_category"] = prefs[tid]["ticket"]
        pax.append(p)
    out = {"outbound_flight_id": plan["outbound"], "passengers": pax}
    if "return" in plan:
        out["return_flight_id"] = plan["return"]
    if "hotel_id" in plan:
        out["hotel_id"] = plan["hotel_id"]
        out["rooms"] = [{"room_id": rid, "traveller_ids": tids} for rid, tids in plan["rooms"]]
    if "cab" in plan:
        cab = plan["cab"]
        out["cab_quote_id"] = quote_id(cab["vehicle_type"], cab["date"], cab["pickup_time"], plan["hotel_id"])
    if "ticket_slot_id" in plan:
        out["ticket_slot_id"] = plan["ticket_slot_id"]
    return out


def slots(world, stages):
    return {"_clause_prefix": f"s{world['scenario']}."}


def check_rules(world, stages):
    c = cons_for(world, stages)
    ans = solver.answer(c)
    assert ans["outbound_flight_id"] and ans["hotel_id"] and ans["ticket_slot_id"]
    if "return" in stages:
        assert ans["return_flight_id"]
    if "budget" in stages:
        d = solver.decoys(c)
        assert d["return.budget"] and d["return.budget"] != ans["return_flight_id"], "budget must change the return pick"


class Tools(TripTools):
    TERMINAL_TOOL = "confirm_booking"
    DOMAIN = DOMAIN

    def __init__(self, instance, language="en"):
        super().__init__("strict", LEVEL)
        self.instance, self.world, self.stages, self.language = instance, instance["world"], instance["stages"], language
        schemas = {s["name"]: s for s in trip_tool_schemas(LEVEL)}
        confirm = schemas.pop("confirm_trip")
        props = json.loads(json.dumps(confirm["parameters"]["properties"]))
        item = props["passengers"]["items"]
        item["required"] = ["traveller_id", "outbound_seat_id", "meal_code"]
        schemas["confirm_booking"] = {
            "name": "confirm_booking",
            "description": "Book and pay in one booking. Include only the components being booked: flights, hotel "
                           "rooms, airport cab and attraction tickets are each optional, except the outbound flight.",
            "parameters": {"type": "object", "properties": props, "required": ["outbound_flight_id", "passengers"]}}
        self.schemas = schemas
        self.booked = None

    def confirm_booking(self, **a):
        out = self._flight(a["outbound_flight_id"])
        ret = self._flight(a["return_flight_id"]) if a.get("return_flight_id") else None
        pax = a["passengers"]
        if not isinstance(pax, list) or sorted(p.get("traveller_id") for p in pax) != TIDS:
            self.bad("passengers must list each traveller from get_travellers exactly once")
        for leg, f in (("outbound", out), ("return", ret)):
            if f is None:
                continue
            smap = {s["seat_id"]: s for s in seat_map(f["flight_id"])}
            chosen = [p.get(f"{leg}_seat_id") for p in pax]
            for sid in chosen:
                if sid not in smap or not smap[sid]["available"]:
                    self.bad(f"seat '{sid}' is not an available seat on {f['flight_id']}")
            if len(set(chosen)) != len(chosen):
                self.bad(f"the same seat is assigned twice on {f['flight_id']}")
        for p in pax:
            if p.get("meal_code") not in set(MEAL_CODE.values()):
                self.bad(f"unknown meal_code '{p.get('meal_code')}'")
        if a.get("hotel_id"):
            self._hotel(a["hotel_id"])
            rooms = {r["room_id"]: r for r in room_options(a["hotel_id"])}
            if not a.get("rooms"):
                self.bad("rooms are required when booking a hotel")
            for r in a["rooms"]:
                if r.get("room_id") not in rooms:
                    self.bad(f"room '{r.get('room_id')}' is not a room at {a['hotel_id']}")
        if a.get("cab_quote_id") and a["cab_quote_id"] not in self._quotes:
            self.bad(f"unknown cab_quote_id '{a['cab_quote_id']}'")
        if a.get("ticket_slot_id"):
            if a["ticket_slot_id"] not in self._slots:
                self.bad(f"unknown ticket_slot_id '{a['ticket_slot_id']}'")
            if any("ticket_category" not in p for p in pax):
                self.bad("every passenger needs a ticket_category when booking tickets")
        self.booked = json.loads(json.dumps(a))
        self.confirmed = {"args": a}
        return {"status": "confirmed", "booking_id": "BK-" + out["flight_id"] + (ret["flight_id"] if ret else "")}

    @staticmethod
    def bad(msg):
        from env.tools.travel_tools import ToolError
        raise ToolError("validation", f"ValidationError: {msg}")

    def snapshot(self):
        return {"booked": self.booked, "quotes": {k: dict(v) for k, v in self._quotes.items()}}


def _seat_type(fid, sid):
    return next((s["seat_type"] for s in seat_map(fid) if s["seat_id"] == sid), None)


def verify(traj, instance, final_state):
    world, stages = instance["world"], instance["stages"]
    c = cons_for(world, stages)
    plan = solve(world, stages)
    d = solver.decoys(c)
    b = (final_state or {}).get("booked") or {}
    quotes = (final_state or {}).get("quotes") or {}
    final = step_of(traj.steps, "confirm_booking")
    checks = []

    def add(name, stage, cls, ok, want, got, decoy=None, anchor=False):
        checks.append(check(name, stage, cls, ok, final, want, got, decoy, anchor))

    add("outbound.flight", "outbound", "selection", b.get("outbound_flight_id") == plan["outbound"], plan["outbound"],
        b.get("outbound_flight_id"), d.get("outbound.objective"))
    if "return" in plan:
        add("return.flight", "return", "selection", b.get("return_flight_id") == plan["return"], plan["return"],
            b.get("return_flight_id"), d.get("return.budget") if "budget" in stages else d.get("return.objective"))
    if "budget" in stages:
        total = None
        if b.get("outbound_flight_id") and b.get("return_flight_id"):
            try:
                total = c["passengers"] * (_flight(b["outbound_flight_id"])["price"] + _flight(b["return_flight_id"])["price"])
            except StopIteration:
                total = None
        add("budget.total", "budget", "coupled", total is not None and total <= c["flight_budget_total"],
            c["flight_budget_total"], total)
    if "hotel_id" in plan:
        add("hotel.hotel", "hotel", "selection", b.get("hotel_id") == plan["hotel_id"], plan["hotel_id"],
            b.get("hotel_id"), d.get("hotel.objective"))
        want_types = sorted(r["room_type"] for r in c["rooms"])
        rid_type = {r["room_id"]: r["room_type"] for r in room_options(b["hotel_id"])} if b.get("hotel_id") else {}
        got_rooms = b.get("rooms") or []
        try:
            got_types = sorted(rid_type.get(r["room_id"]) or "?" for r in got_rooms)
        except (KeyError, TypeError):
            got_types = []
        add("rooms.types", "rooms", "attribute", got_types == want_types, want_types, got_types)
        want_occ = sorted((rt, sorted(occ)) for rt, occ in
                          ((r["room_type"], [solver.RELATION_TO_ID[x] for x in r["occupants"]]) for r in c["rooms"]))
        try:
            got_occ = sorted((rid_type.get(r["room_id"]) or "?", sorted(r.get("traveller_ids", []))) for r in got_rooms)
        except (KeyError, TypeError):
            got_occ = []
        add("rooms.occupants", "rooms", "binding", got_occ == want_occ, want_occ, got_occ)
    if "cab" in plan:
        q = quotes.get(b.get("cab_quote_id")) or {}
        add("cab.vehicle", "cab", "attribute", q.get("vehicle_type") == plan["cab"]["vehicle_type"],
            plan["cab"]["vehicle_type"], q.get("vehicle_type"))
        add("cab.pickup_time", "cab", "carried", q.get("pickup_time") == plan["cab"]["pickup_time"]
            and q.get("date") == plan["cab"]["date"], plan["cab"]["pickup_time"], q.get("pickup_time"),
            _flight(plan["outbound"])["depart_time"])
        add("cab.drop", "cab", "carried", q.get("drop_location") == plan["hotel_id"], plan["hotel_id"],
            q.get("drop_location"))
    if "ticket_slot_id" in plan:
        add("tickets.slot", "tickets", "selection", b.get("ticket_slot_id") == plan["ticket_slot_id"],
            plan["ticket_slot_id"], b.get("ticket_slot_id"), d.get("tickets.objective"))
        want = {tid: p["ticket"] for tid, p in plan["travellers"].items()}
        got = {p.get("traveller_id"): p.get("ticket_category") for p in b.get("passengers", [])}
        add("tickets.categories", "tickets", "binding", got == want, want, got)
    pax = {p.get("traveller_id"): p for p in b.get("passengers", []) if isinstance(p, dict)}
    seat_ok, got_seats = bool(pax), {}
    for leg in ("outbound", "return"):
        fid = b.get(f"{leg}_flight_id")
        if leg == "return" and "return" not in plan:
            continue
        for tid, pref in plan["travellers"].items():
            st = _seat_type(fid, pax.get(tid, {}).get(f"{leg}_seat_id")) if fid else None
            got_seats[f"{leg}:{tid}"] = st
            seat_ok = seat_ok and st == pref["seat"]
    want_seats = {f"{leg}:{tid}": p["seat"] for leg in ("outbound", "return") if leg in plan
                  for tid, p in plan["travellers"].items()}
    add("submit.seats", "submit", "anchor", seat_ok, want_seats, got_seats, anchor=True)
    want_meals = {tid: MEAL_CODE[p["meal"]] for tid, p in plan["travellers"].items()}
    got_meals = {tid: pax.get(tid, {}).get("meal_code") for tid in plan["travellers"]}
    add("submit.meals", "submit", "anchor", got_meals == want_meals, want_meals, got_meals, anchor=True)
    extra = [k for k, need in (("return_flight_id", "return"), ("hotel_id", "hotel"), ("cab_quote_id", "cab"),
                               ("ticket_slot_id", "tickets")) if b.get(k) and need not in stages]
    add("booking.no_extra", "submit", "global", bool(b) and not extra, [], extra)
    return summarize(traj, instance, checks, completed=bool(b))


FAULTS = ("outbound_decoy", "swap_seats", "wrong_meal", "extra_component")


def faulty_plan(world, stages, mode):
    plan = solve(world, stages)
    c = cons_for(world, stages)
    if mode == "outbound_decoy":
        plan["outbound"] = solver.decoys(c)["outbound.objective"]
        failed = {"outbound.flight"}
        if "cab" in plan:
            plan["cab"]["pickup_time"] = solver.arrival_time(plan["outbound"])
            failed.add("cab.pickup_time")
        if "budget" in stages:
            p = c["passengers"] * (_flight(plan["outbound"])["price"] + _flight(plan["return"])["price"])
            if p > c["flight_budget_total"]:
                failed.add("budget.total")
        return plan, failed
    if mode == "swap_seats":
        tids = sorted(plan["travellers"])
        pref = plan["travellers"]
        a, b = next((x, y) for x in tids for y in tids if pref[x]["seat"] != pref[y]["seat"])
        pref[a]["seat"], pref[b]["seat"] = pref[b]["seat"], pref[a]["seat"]
        return plan, {"submit.seats"}
    if mode == "wrong_meal":
        tid = sorted(plan["travellers"])[0]
        cur = plan["travellers"][tid]["meal"]
        plan["travellers"][tid]["meal"] = "non_vegetarian" if cur != "non_vegetarian" else "vegetarian"
        return plan, {"submit.meals"}
    if mode == "extra_component":
        if "hotel_id" not in plan:
            full = solve(world, FORMATS["long"])
            plan["return"] = full["return"]
            return plan, {"booking.no_extra"}
        if "ticket_slot_id" not in plan:
            plan["ticket_slot_id"] = solve(world, FORMATS["long"])["ticket_slot_id"]
            return plan, {"booking.no_extra"}
        pref = plan["travellers"]
        a, b = next((x, y) for x in sorted(pref) for y in sorted(pref) if pref[x]["ticket"] != pref[y]["ticket"])
        pref[a]["ticket"], pref[b]["ticket"] = pref[b]["ticket"], pref[a]["ticket"]
        return plan, {"tickets.categories"}
    raise ValueError(mode)
