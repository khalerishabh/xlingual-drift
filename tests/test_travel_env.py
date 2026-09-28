import json
import unicodedata
from pathlib import Path

import pytest

from agent.policies.mock_policy import MockPolicy
from agent.react_loop import run_episode
from env.inject import FailureInjector
from env.tools.travel_tools import ToolError, TravelTools
from eval.verifier import optimal_flight, verify

ROOT = Path(__file__).resolve().parent.parent
HORIZONS = (2, 4, 6, 8)
TEMPLATE = json.loads((ROOT / "tasks/templates/travel_017.json").read_text(encoding="utf-8"))
CHENNAI_HI = "चेन्नई"
DELHI_HI = "दिल्ली"


def gold(h):
    return json.loads((ROOT / f"tasks/gold/travel_017_h{h}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("h", HORIZONS)
def test_gold_replays_exactly(h):
    g = gold(h)
    assert len(g["gold_steps"]) == h
    tools = TravelTools("strict", h)
    result = None
    for step in g["gold_steps"]:
        result = tools.call(step["tool"], step["args"])
        for key, value in step.get("returns", {}).items():
            assert result[key] == value, (step["tool"], key)
    assert result == g["terminal_state"]


def test_tool_names_identical_at_every_horizon():
    names = {h: [s["name"] for s in TravelTools("strict", h).schema_list()] for h in HORIZONS}
    assert len({tuple(v) for v in names.values()}) == 1


@pytest.mark.parametrize("h", HORIZONS)
def test_every_constraint_changes_the_answer(h):
    g = gold(h)
    answer = g["terminal_state"]["booking.flight_id"]
    for constraint, decoy in g["decoys"].items():
        assert optimal_flight(g, set(), drop=constraint) == decoy
        assert decoy != answer


def test_sold_out_flights_never_returned():
    tools = TravelTools("strict", 6)
    flights = tools.call("search_flights", {"origin": "MAA", "destination": "DEL", "date": "2026-08-22"})["flights"]
    assert "6E050" not in {f["flight_id"] for f in flights}


def test_lenient_accepts_script_variants_strict_does_not():
    args = {"origin": CHENNAI_HI, "destination": DELHI_HI, "date": "2026-08-22"}
    assert TravelTools("lenient", 2).call("search_flights", args)["flights"]
    with pytest.raises(ToolError):
        TravelTools("strict", 2).call("search_flights", args)
    assert TravelTools("lenient", 4).call("resolve_city", {"name": CHENNAI_HI}) == {"code": "MAA"}


@pytest.mark.parametrize("mode", ("strict", "lenient"))
def test_lenient_never_shortens_the_chain(mode):
    with pytest.raises(ToolError):
        TravelTools(mode, 4).call("search_flights", {"origin": "Chennai", "destination": "Delhi", "date": "2026-08-22"})


def test_inline_filters_rejected_where_horizon_requires_filter_step():
    args = {"origin": "MAA", "destination": "DEL", "date": "2026-08-22", "max_price": 8000}
    with pytest.raises(ToolError, match="unexpected argument"):
        TravelTools("strict", 6).call("search_flights", args)


def test_template_languages_present_and_script_clean():
    assert {"en", "zh", "hi", "ta", "hinglish"} <= set(TEMPLATE["requests"])
    expected = {"zh": "CJK", "hi": "DEVANAGARI", "ta": "TAMIL"}
    allowed = {"₹", "，", "。"}
    for lang, script in expected.items():
        foreign = {c for c in TEMPLATE["requests"][lang]
                   if ord(c) > 0x7F and c not in allowed and script not in unicodedata.name(c, "")}
        assert not foreign, (lang, [hex(ord(c)) for c in foreign])
    for lang in ("en", "hinglish", "tanglish"):
        assert all(ord(c) < 0x7F or c == "₹" for c in TEMPLATE["requests"][lang])


def _episode(h, mode, injector=None):
    g = gold(h)
    traj = run_episode(g["task_id"], h, TEMPLATE["requests"]["en"], MockPolicy(g, mode), injector=injector)
    return verify(traj, g, traj.sold_out)


@pytest.mark.parametrize("h", HORIZONS)
def test_mock_solve_succeeds(h):
    r = _episode(h, "solve")
    assert r["success"] and r["matches_gold_terminal"] and r["extra_steps"] == 0


@pytest.mark.parametrize("h", HORIZONS)
def test_budget_drift_is_detected(h):
    r = _episode(h, "deviate_drop_constraint")
    assert not r["success"]
    assert r["constraint_survival"]["max_price"] is False
    assert r["constraint_survival"]["depart_before"] is True


@pytest.mark.parametrize("h", HORIZONS)
def test_not_found_recovery_counts_only_correct_fallback(h):
    inj = FailureInjector("not_found", "en", at_tool="book_flight")
    r = _episode(h, "recover", inj)
    assert r["injected"] and r["recovered"] and r["booked_flight"] == gold(h)["recovery_fallback"]
    inj = FailureInjector("not_found", "en", at_tool="book_flight")
    assert _episode(h, "solve", inj)["recovered"] is False


@pytest.mark.parametrize("lang", ("en", "zh", "hi", "ta", "hinglish"))
def test_injected_message_language(lang):
    inj = FailureInjector("transient", lang, at_tool="search_flights")
    g = gold(4)
    traj = run_episode(g["task_id"], 4, TEMPLATE["requests"][lang], MockPolicy(g, "recover"), injector=inj)
    msg = traj.injected_error["message"]
    assert msg.startswith("HTTP 429")
    assert (lang in ("en", "hinglish")) == msg.isascii()


def test_decision_set_identical_at_every_horizon():
    seen = {}
    for h in HORIZONS:
        tools, last_list = TravelTools("strict", h), None
        for step in gold(h)["gold_steps"]:
            result = tools.call(step["tool"], step["args"])
            if "flights" in result:
                last_list = frozenset(f["flight_id"] for f in result["flights"])
        seen[h] = last_list
    assert len(set(seen.values())) == 1, seen
