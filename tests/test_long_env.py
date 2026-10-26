import json
import subprocess
import sys
import unicodedata
from pathlib import Path

import pytest

from agent.policies.long_mock_policy import LongMockPolicy
from agent.react_loop import run_episode
from env.long.registry import DOMAINS

ROOT = Path(__file__).resolve().parent.parent
IDS = sorted(p.stem for p in (ROOT / "tasks/long").glob("*.json"))


def inst(tid):
    return json.loads((ROOT / f"tasks/long/{tid}.json").read_text(encoding="utf-8"))


def episode(tid, mode="solve", lang="en", seam="S1"):
    i = inst(tid)
    d = DOMAINS[i["domain"]]
    tools = d["tools"](i, lang, seam)
    traj = run_episode(tid, i["horizon"], i["requests"][lang], LongMockPolicy(i, mode), max_steps=80, tools=tools)
    return d["module"].verify(traj, i, traj.sold_out), traj


def failed(r):
    return {k for k, v in r["constraint_ok"].items() if not v}


def test_instances_are_current():
    r = subprocess.run([sys.executable, "-m", "tasks.build_long", "--check"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_ten_instances_per_domain_with_30_to_40_steps():
    for d in DOMAINS:
        ids = [t for t in IDS if t.startswith(d + "_")]
        assert len(ids) == 10
        for t in ids:
            assert 30 <= inst(t)["horizon"] <= 40


@pytest.mark.parametrize("tid", IDS)
@pytest.mark.parametrize("lang,seam", [("en", "S0"), ("hi", "S1"), ("ta", "S2"), ("zh", "S3"), ("hinglish", "S3")])
def test_gold_solves_in_every_language_and_seam(tid, lang, seam):
    r, _ = episode(tid, lang=lang, seam=seam)
    assert r["success"], failed(r)


@pytest.mark.parametrize("tid", [t for t in IDS if t.startswith("shop")])
def test_shop_faults_are_typed(tid):
    r, _ = episode(tid, "swap_recipients")
    assert not r["success"] and "entity_swap" in {r["drift_type"][k] for k in failed(r)}
    r, _ = episode(tid, "neighbour_variant")
    k = next(iter(failed(r)))
    assert failed(r) == {k} and r["drift_type"][k] == "neighbour_id"
    r, _ = episode(tid, "semantic_label")
    k = next(iter(failed(r)))
    assert failed(r) == {k} and r["drift_type"][k] == "semantic"
    r, _ = episode(tid, "reground_wrong_colour")
    bad = failed(r)
    assert len(bad) == 1 and r["regrounding"][next(iter(bad))]


@pytest.mark.parametrize("tid", [t for t in IDS if t.startswith("pay")])
def test_pay_faults_are_typed(tid):
    r, _ = episode(tid, "wrong_electricity")
    assert r["drift_type"].get("bill.elec_nani.paid") in ("semantic", "neighbour_id")
    r, _ = episode(tid, "swap_tags")
    assert failed(r) == {"bill.elec_home.tag", "bill.broadband.tag"}
    assert {r["drift_type"][k] for k in failed(r)} == {"entity_swap"}
    r, _ = episode(tid, "retry_wrong_account")
    assert failed(r) == {"transfer.pocket.account"} and r["regrounding"]["transfer.pocket.account"]
    r, _ = episode(tid, "floor_rule_forgotten")
    assert not r["success"]


@pytest.mark.parametrize("domain", list(DOMAINS))
def test_seams_localise_outputs_and_errors_only_where_asked(domain):
    tid = f"{domain}_01"

    def scripts(seam, part):
        _, traj = episode(tid, lang="hi", seam=seam)
        text = json.dumps([s.get(part) for s in traj.steps], ensure_ascii=False)
        return any("DEVANAGARI" in unicodedata.name(c, "") for c in text)

    assert not scripts("S1", "result")
    assert scripts("S2", "result")
    if domain == "pay":
        assert not scripts("S2", "error")
        assert scripts("S3", "error")


@pytest.mark.parametrize("tid", IDS)
def test_requests_script_clean(tid):
    t = inst(tid)
    expected = {"zh": "CJK", "hi": "DEVANAGARI", "ta": "TAMIL"}
    allowed = set("₹，。、：（）'·")
    for lang, script in expected.items():
        foreign = {c for c in t["requests"][lang] if ord(c) > 0x7F and c not in allowed and script not in unicodedata.name(c, "")}
        assert not foreign, (lang, foreign)
    for lang in ("en", "hinglish"):
        assert all(ord(c) < 0x7F or c == "₹" for c in t["requests"][lang])
