import json
import subprocess
import sys
import unicodedata
from pathlib import Path

import pytest

from agent.policies.mock_policy import MockPolicy
from agent.react_loop import run_episode
from env.data.flights import MEAL_OPTIONS, seat_map_for, FLIGHTS
from env.inject import FailureInjector
from env.tools.horizons import HORIZONS
from env.tools.travel_tools import ToolError, TravelTools
from eval.verifier import optimal_flight, verify

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_IDS = sorted(p.stem for p in (ROOT / "tasks/templates").glob("*.json"))
CHENNAI_HI = "चेन्नई"
DELHI_HI = "दिल्ली"
AISLE_HI = "आइल सीट"
JAIN_TA = "ஜெயின் உணவு"


def template(tid):
    return json.loads((ROOT / f"tasks/templates/{tid}.json").read_text(encoding="utf-8"))


def gold(tid, h):
    return json.loads((ROOT / f"tasks/gold/{tid}_h{h}.json").read_text(encoding="utf-8"))


ALL = [(t, h) for t in TEMPLATE_IDS for h in HORIZONS]


def test_gold_files_are_current():
    result = subprocess.run([sys.executable, "-m", "tasks.build_gold", "--check"], cwd=ROOT,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("tid,h", ALL)
def test_gold_replays_exactly(tid, h):
    g = gold(tid, h)
    assert len(g["gold_steps"]) == h
    tools, result = TravelTools("strict", h), None
    for step in g["gold_steps"]:
        result = tools.call(step["tool"], step["args"])
        for key, value in step.get("returns", {}).items():
            assert result[key] == value, (step["tool"], key)
    assert result == g["terminal_state"]


def test_tool_names_identical_at_every_horizon():
    names = {h: [s["name"] for s in TravelTools("strict", h).schema_list()] for h in HORIZONS}
    assert len({tuple(v) for v in names.values()}) == 1


@pytest.mark.parametrize("tid", TEMPLATE_IDS)
def test_every_early_constraint_changes_the_answer(tid):
    g = gold(tid, 2)
    answer = g["terminal_state"]["booking.flight_id"]
    for constraint, decoy in g["decoys"].items():
        assert optimal_flight(g, set(), drop=constraint) == decoy != answer


@pytest.mark.parametrize("tid", TEMPLATE_IDS)
def test_late_constraints_are_real_choices_never_listed_first(tid):
    g = gold(tid, 10)
    flight = next(f for f in FLIGHTS if f["flight_id"] == g["terminal_state"]["booking.flight_id"])
    seats = [s["seat_type"] for s in seat_map_for(flight)]
    meals = [m["meal"] for m in MEAL_OPTIONS]
    for wanted, listing in ((g["late_constraints"]["seat_type"], seats), (g["late_constraints"]["meal"], meals)):
        assert wanted in listing and listing[0] != wanted and len(set(listing)) > 1


@pytest.mark.parametrize("tid", TEMPLATE_IDS)
def test_decision_set_identical_at_every_horizon(tid):
    seen = {}
    for h in HORIZONS:
        tools, last = TravelTools("strict", h), None
        for step in gold(tid, h)["gold_steps"]:
            result = tools.call(step["tool"], step["args"])
            if "flights" in result:
                last = frozenset(f["flight_id"] for f in result["flights"])
        seen[h] = last
    assert len(set(seen.values())) == 1, seen


@pytest.mark.parametrize("tid", TEMPLATE_IDS)
def test_late_constraints_committed_only_in_the_final_call(tid):
    for h in HORIZONS:
        steps = gold(tid, h)["gold_steps"]
        late_keys = {"seat_type", "meal", "seat_id", "meal_code"}
        assert all(not (late_keys & set(s["args"])) for s in steps[:-1])
        assert late_keys & set(steps[-1]["args"])


def test_sold_out_flights_never_returned():
    for tid, sold in (("travel_017", "6E050"), ("travel_018", "SG208"), ("travel_019", "6E077")):
        g = gold(tid, 6)
        args = next(s["args"] for s in g["gold_steps"] if s["tool"] == "search_flights")
        flights = TravelTools("strict", 6).call("search_flights", args)["flights"]
        assert sold not in {f["flight_id"] for f in flights}


def test_lenient_accepts_script_variants_strict_does_not():
    args = {"origin": CHENNAI_HI, "destination": DELHI_HI, "date": "2026-08-22"}
    assert TravelTools("lenient", 2).call("search_flights", args)["flights"]
    with pytest.raises(ToolError):
        TravelTools("strict", 2).call("search_flights", args)
    book = {"flight_id": "6E212", "seat_type": AISLE_HI, "meal": JAIN_TA}
    result = TravelTools("lenient", 2).call("book_flight", book)
    assert (result["booking.seat_type"], result["booking.meal"]) == ("aisle", "jain")
    with pytest.raises(ToolError):
        TravelTools("strict", 2).call("book_flight", book)


@pytest.mark.parametrize("mode", ("strict", "lenient"))
def test_lenient_never_shortens_the_chain(mode):
    with pytest.raises(ToolError):
        TravelTools(mode, 4).call("search_flights", {"origin": "Chennai", "destination": "Delhi", "date": "2026-08-22"})
    book = {"flight_id": "6E212", "hold_token": "x", "passenger_id": "P001", "seat_type": "aisle", "meal": "jain"}
    with pytest.raises(ToolError):
        TravelTools(mode, 10).call("book_flight", book)


def test_inline_filters_rejected_where_horizon_requires_filter_step():
    args = {"origin": "MAA", "destination": "DEL", "date": "2026-08-22", "max_price": 8000}
    with pytest.raises(ToolError, match="unexpected argument"):
        TravelTools("strict", 6).call("search_flights", args)


@pytest.mark.parametrize("tid", TEMPLATE_IDS)
def test_template_languages_present_and_script_clean(tid):
    t = template(tid)
    assert {"en", "zh", "hi", "ta", "hinglish"} <= set(t["requests"])
    expected = {"zh": "CJK", "hi": "DEVANAGARI", "ta": "TAMIL"}
    allowed = {"₹", "，", "。", "、"}
    for lang, script in expected.items():
        foreign = {c for c in t["requests"][lang]
                   if ord(c) > 0x7F and c not in allowed and script not in unicodedata.name(c, "")}
        assert not foreign, (lang, [hex(ord(c)) for c in foreign])
    for lang in ("en", "hinglish", "tanglish"):
        assert all(ord(c) < 0x7F or c == "₹" for c in t["requests"][lang])


def _episode(tid, h, mode, injector=None, lang="en"):
    g, t = gold(tid, h), template(tid)
    traj = run_episode(g["task_id"], h, t["requests"][lang], MockPolicy(g, mode), injector=injector,
                       max_steps=24, context={"session_date": t["session_date"]})
    return verify(traj, g, traj.sold_out)


@pytest.mark.parametrize("tid,h", ALL)
def test_mock_solve_succeeds(tid, h):
    r = _episode(tid, h, "solve")
    assert r["success"] and r["matches_gold_terminal"] and r["extra_steps"] == 0
    assert r["late_commit_step"] == h


@pytest.mark.parametrize("tid,h", ALL)
def test_early_and_late_drift_are_detected_separately(tid, h):
    early = _episode(tid, h, "deviate_drop_constraint")
    assert not early["success"] and not early["all_early_survived"] and early["all_late_survived"]
    late = _episode(tid, h, "deviate_drop_late")
    assert not late["success"] and late["flight_correct"] and not late["all_late_survived"]


@pytest.mark.parametrize("tid,h", ALL)
def test_not_found_recovery_counts_only_correct_fallback(tid, h):
    r = _episode(tid, h, "recover", FailureInjector("not_found", "en", at_tool="book_flight"))
    assert r["injected"] and r["recovered"] and r["booked_flight"] == gold(tid, h)["recovery_fallback"]
    assert _episode(tid, h, "solve", FailureInjector("not_found", "en", at_tool="book_flight"))["recovered"] is False


@pytest.mark.parametrize("lang", ("en", "zh", "hi", "ta", "hinglish"))
def test_injected_message_language(lang):
    inj = FailureInjector("transient", lang, at_tool="search_flights")
    g, t = gold("travel_017", 4), template("travel_017")
    traj = run_episode(g["task_id"], 4, t["requests"][lang], MockPolicy(g, "recover"), injector=inj,
                       context={"session_date": t["session_date"]})
    msg = traj.injected_error["message"]
    assert msg.startswith("HTTP 429")
    assert (lang in ("en", "hinglish")) == msg.isascii()
