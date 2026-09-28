"""
Scripted policy for the trip domain. It executes a complete, consistent
chain written by env.trip.chain for a plan: the gold plan, or one with a
single deliberate fault, so each fault is detected in isolation.

Modes:
  solve          the gold plan; stop at the first error
  recover        the gold plan; retry transient errors; if the outbound
                 flight is sold out, switch to the fallback and rebuild
  drop_early     outbound ignores its time window (early drift)
  drop_budget    return ignores the joint budget (early, coupled)
  wrong_hotel    hotel ignores the breakfast constraint (mid)
  wrong_pickup   cab pickup at departure instead of arrival time (carried)
  swap_seats     two travellers' seat types swapped (late binding)
  drop_late      mother's meal becomes the first listed meal (late)
"""

import copy

from env.trip.chain import chain, plan_from_answer
from env.trip.solver import RELATION_TO_ID, arrival_time, return_flight, rooms
from env.trip.world import FLIGHTS, MEAL_OPTIONS

MODES = ("solve", "recover", "drop_early", "drop_budget", "wrong_hotel", "wrong_pickup", "swap_seats", "drop_late")


def _departure(fid):
    return next(f["depart_time"] for f in FLIGHTS if f["flight_id"] == fid)


def _early_key(gold):
    return next(k for k in ("depart_before", "depart_after") if k in gold["constraints"]["outbound"])


def _hotel_key(gold):
    return next(k for k in ("max_price_per_night", "breakfast", "amenities", "max_distance_km")
                if k in gold["constraints"]["hotel"])


def _seat_pair(gold):
    t = gold["constraints"]["travellers"]
    return next((a, b) for a, b in (("father", "mother"), ("self", "father"), ("self", "mother"))
                if t[a]["seat"] != t[b]["seat"])


def faulty_plan(gold: dict, mode: str) -> dict:
    cons, plan = gold["constraints"], plan_from_answer(gold["answer"])
    plan = copy.deepcopy(plan)
    if mode == "drop_early":
        plan["outbound"] = gold["decoys"][f"outbound.{_early_key(gold)}"]
        plan["return"] = return_flight(cons, plan["outbound"])
        plan["cab"]["pickup_time"] = arrival_time(plan["outbound"])
    elif mode == "drop_budget":
        plan["return"] = gold["decoys"]["return.budget"]
    elif mode == "wrong_hotel":
        plan["hotel_id"] = gold["decoys"][f"hotel.{_hotel_key(gold)}"]
        plan["rooms"] = rooms(cons, plan["hotel_id"])
        plan["cab"]["drop_hotel"] = plan["hotel_id"]
    elif mode == "wrong_pickup":
        plan["cab"]["pickup_time"] = _departure(plan["outbound"])
    elif mode == "swap_seats":
        a, b = (RELATION_TO_ID[x] for x in _seat_pair(gold))
        t = plan["travellers"]
        t[a]["seat"], t[b]["seat"] = t[b]["seat"], t[a]["seat"]
    elif mode == "drop_late":
        plan["travellers"][RELATION_TO_ID["mother"]]["meal"] = MEAL_OPTIONS[0]["meal"]
    return plan


def expected_failures(gold: dict, mode: str) -> tuple[str, set]:
    """(constraint class, failed constraint names) each fault must produce."""
    if mode == "drop_early":
        return "early", {f"outbound.{_early_key(gold)}", "outbound.objective"}
    if mode == "drop_budget":
        return "early", {"return.budget", "return.objective"}
    if mode == "wrong_hotel":
        return "mid", {f"hotel.{_hotel_key(gold)}", "hotel.objective"}
    if mode == "wrong_pickup":
        return "carried", {"cab.pickup_time"}
    if mode == "swap_seats":
        return "late", {f"seat.{leg}.{rel}" for leg in ("outbound", "return") for rel in _seat_pair(gold)}
    if mode == "drop_late":
        return "late", {"meal.mother"}
    raise ValueError(mode)


class TripMockPolicy:
    def __init__(self, gold: dict, mode: str = "solve"):
        assert mode in MODES, mode
        self.gold, self.mode = gold, mode
        self.steps = chain(gold["constraints"], faulty_plan(gold, mode), gold["horizon"])
        self._i = 0
        self._last = None
        self._switched = False

    def reset(self, request: str, tool_schemas: list, context: dict | None = None):
        self._i, self._last, self._switched = 0, None, False

    def next_action(self, observations: list) -> dict:
        if observations and "error" in observations[-1]:
            kind = observations[-1]["error"]["error_type"]
            if self.mode != "recover":
                return {"final": True}
            if kind == "transient":
                return self._last
            if kind == "not_found" and not self._switched:
                self._switch_to_fallback()
            else:
                return {"final": True}
        if self._i >= len(self.steps):
            return {"final": True}
        self._last = {"tool": self.steps[self._i]["tool"], "args": self.steps[self._i]["args"]}
        self._i += 1
        return self._last

    def _switch_to_fallback(self):
        cons = self.gold["constraints"]
        plan = plan_from_answer(self.gold["answer"])
        old = plan["outbound"]
        plan["outbound"] = self.gold["recovery_fallback"]["outbound"]
        plan["return"] = return_flight(cons, plan["outbound"], {old})
        plan["cab"]["pickup_time"] = arrival_time(plan["outbound"])
        self.steps = chain(cons, plan, self.gold["horizon"])
        self._i = next(i for i, s in enumerate(self.steps) if plan["outbound"] in str(s["args"]))
        self._switched = True
