import copy
import json
import subprocess
import sys
import unicodedata
from pathlib import Path

import pytest

from agent.policies.trip_mock_policy import TripMockPolicy, expected_failures
from agent.react_loop import run_episode
from env.inject import FailureInjector
from env.tools.travel_tools import ToolError
from env.trip.levels import TRIP_HORIZONS
from env.trip.schemas import trip_tool_schemas
from env.trip.tools import TripTools
from eval.trip_verifier import verify_trip
from tasks.build_trip_gold import build

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_IDS = sorted(p.stem for p in (ROOT / "tasks/trip_templates").glob("*.json"))
ALL = [(t, h) for t in TEMPLATE_IDS for h in TRIP_HORIZONS]


def template(tid):
    return json.loads((ROOT / f"tasks/trip_templates/{tid}.json").read_text(encoding="utf-8"))


def gold(tid, h):
    return json.loads((ROOT / f"tasks/trip_gold/{tid}_h{h}.json").read_text(encoding="utf-8"))


def episode(tid, h, mode="solve", injector=None):
    g = gold(tid, h)
    traj = run_episode(g["task_id"], h, template(tid)["requests"]["en"], TripMockPolicy(g, mode),
                       injector=injector, max_steps=60, tools=TripTools("strict", h))
    return verify_trip(traj, g, traj.sold_out)


def failed(result):
    return {k for k, v in result["constraint_ok"].items() if not v}


def test_gold_files_are_current():
    result = subprocess.run([sys.executable, "-m", "tasks.build_trip_gold", "--check"], cwd=ROOT,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("tid,h", ALL)
def test_gold_chain_has_horizon_length_and_confirms(tid, h):
    g = gold(tid, h)
    assert len(g["gold_steps"]) == h
    assert g["gold_steps"][-1]["tool"] == "confirm_trip"
    assert g["terminal_state"]["status"] == "confirmed"


def test_tool_names_identical_at_every_horizon():
    names = {h: [s["name"] for s in trip_tool_schemas(h)] for h in TRIP_HORIZONS}
    assert len({tuple(v) for v in names.values()}) == 1


def test_late_constraint_interface_identical_at_every_horizon():
    def late_fields(h):
        confirm = next(s for s in trip_tool_schemas(h) if s["name"] == "confirm_trip")["parameters"]["properties"]
        pax = dict(confirm["passengers"]["items"]["properties"])
        pax.pop("document_id", None)
        return json.dumps({"passengers": pax, "rooms": confirm["rooms"]}, sort_keys=True)
    assert len({late_fields(h) for h in TRIP_HORIZONS}) == 1


@pytest.mark.parametrize("tid", TEMPLATE_IDS)
def test_answer_identical_at_every_horizon(tid):
    assert len({json.dumps(gold(tid, h)["answer"], sort_keys=True) for h in TRIP_HORIZONS}) == 1


@pytest.mark.parametrize("tid", TEMPLATE_IDS)
def test_rule_listing_order_assignment_is_wrong_for_everyone(tid):
    t = copy.deepcopy(template(tid))
    t["constraints"]["travellers"]["mother"]["seat"] = "window"
    with pytest.raises(AssertionError, match="listing order"):
        build(t, TRIP_HORIZONS[0])


@pytest.mark.parametrize("tid", TEMPLATE_IDS)
def test_rule_every_constraint_changes_the_answer(tid):
    t = copy.deepcopy(template(tid))
    t["constraints"]["hotel"]["max_distance_km"] = 20
    with pytest.raises(AssertionError, match="does not change the answer"):
        build(t, TRIP_HORIZONS[0])


@pytest.mark.parametrize("tid", TEMPLATE_IDS)
def test_template_languages_present_and_script_clean(tid):
    t = template(tid)
    assert {"en", "zh", "hi", "ta", "hinglish"} <= set(t["requests"])
    expected = {"zh": "CJK", "hi": "DEVANAGARI", "ta": "TAMIL"}
    allowed = set("₹，。、：（）·")
    for lang, script in expected.items():
        foreign = {c for c in t["requests"][lang]
                   if ord(c) > 0x7F and c not in allowed and script not in unicodedata.name(c, "")}
        assert not foreign, (lang, [hex(ord(c)) for c in foreign])
    for lang in ("en", "hinglish"):
        assert all(ord(c) < 0x7F or c == "₹" for c in t["requests"][lang])


@pytest.mark.parametrize("tid,h", ALL)
def test_mock_solve_succeeds(tid, h):
    r = episode(tid, h)
    assert r["success"] and r["binding_swaps"] == 0 and r["fact_displacements"] == 0


FAULTS = ("drop_early", "drop_budget", "wrong_hotel", "wrong_pickup", "swap_seats", "drop_late")


@pytest.mark.parametrize("mode", FAULTS)
@pytest.mark.parametrize("tid,h", ALL)
def test_each_fault_is_caught_only_in_its_class(tid, h, mode):
    klass, expected = expected_failures(gold(tid, h), mode)
    r = episode(tid, h, mode)
    assert not r["success"] and failed(r) == expected
    assert {r["constraint_class"][k] for k in failed(r)} == {klass}
    assert r[f"all_{klass}_survived"] is False
    assert (r["binding_swaps"] > 0) == (mode == "swap_seats")


@pytest.mark.parametrize("tid,h", ALL)
def test_not_found_recovery_counts_only_the_fallback(tid, h):
    inj = lambda: FailureInjector("not_found", at_tool="get_seat_map")
    assert episode(tid, h, "recover", inj())["recovered"] is True
    assert episode(tid, h, "solve", inj())["recovered"] is False


def test_late_constraints_are_committed_in_the_last_step():
    for h in TRIP_HORIZONS:
        r = episode(TEMPLATE_IDS[0], h)
        late = [k for k, c in r["constraint_class"].items() if c == "late"]
        assert {r["constraint_commit_step"][k] for k in late} == {h}
        step = lambda klass: [r["constraint_commit_step"][k] for k, c in r["constraint_class"].items() if c == klass]
        assert max(step("early")) < min(step("mid")) and max(step("mid") + step("carried")) <= h


def _confirm_args(h):
    return copy.deepcopy(gold(TEMPLATE_IDS[0], h)["gold_steps"][-1]["args"])


def _tools_ready(h):
    tools = TripTools("strict", h)
    for s in gold(TEMPLATE_IDS[0], h)["gold_steps"][:-1]:
        tools.call(s["tool"], s["args"])
    return tools


@pytest.mark.parametrize("mutate", ["dup_seat", "taken_seat", "missing_traveller", "bad_quote", "bad_meal"])
def test_checkout_validates_ids_without_leaking_preferences(mutate):
    h = TRIP_HORIZONS[-1]
    a = _confirm_args(h)
    p = a["passengers"]
    if mutate == "dup_seat":
        p[1]["outbound_seat_id"] = p[0]["outbound_seat_id"]
    elif mutate == "taken_seat":
        p[0]["outbound_seat_id"] = "14A"
    elif mutate == "missing_traveller":
        a["passengers"] = p[:2]
    elif mutate == "bad_quote":
        a["cab_quote_id"] = "Q-SUV-1014-0000-140"
    elif mutate == "bad_meal":
        p[0]["meal_code"] = "XXML"
    with pytest.raises(ToolError) as e:
        _tools_ready(h).call("confirm_trip", a)
    for word in ("window", "aisle", "middle", "jain", "diabetic", "vegetarian", "senior"):
        assert word not in e.value.message.lower()


def test_wrong_preferences_are_accepted_at_checkout():
    r = episode(TEMPLATE_IDS[0], TRIP_HORIZONS[-1], "swap_seats")
    assert r["late_commit_step"] is not None and r["booked_flight"] is not None
