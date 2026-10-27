import json
from pathlib import Path

import pytest

from agent.react_loop import Trajectory
from env.exp2.core import FORMATS
from env.exp2.registry import DOMAINS
from env.tools.travel_tools import ToolError

ROOT = Path(__file__).resolve().parent.parent
INSTANCES = sorted((ROOT / "tasks" / "exp2").glob("*.json"))


def _load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def _run(inst, steps):
    mod = DOMAINS[inst["domain"]]
    tools = mod.Tools(inst, "en")
    traj = Trajectory(task_id=inst["template_id"], horizon=inst["horizon"])
    for st in steps:
        rec = {"tool": st["tool"], "args": st["args"]}
        try:
            rec["result"] = tools.call(st["tool"], st["args"])
        except ToolError as e:
            rec["error"] = {"error_type": e.error_type, "message": e.message}
        traj.steps.append(rec)
    return mod.verify(traj, inst, tools.snapshot())


def test_grid_is_complete():
    assert len(INSTANCES) == 75
    for d, mod in DOMAINS.items():
        assert len(mod.SCENARIOS) == 5
        assert tuple(mod.FORMATS) == FORMATS


@pytest.mark.parametrize("path", INSTANCES, ids=lambda p: p.stem)
def test_gold_succeeds(path):
    inst = _load(path)
    r = _run(inst, inst["gold_steps"])
    assert r["success"], [k for k, v in r["constraint_ok"].items() if not v]


@pytest.mark.parametrize("path", INSTANCES, ids=lambda p: p.stem)
def test_each_fault_fails_only_its_constraints(path):
    inst = _load(path)
    mod = DOMAINS[inst["domain"]]
    for mode in mod.FAULTS:
        plan, expect = mod.faulty_plan(inst["world"], inst["stages"], mode)
        r = _run(inst, mod.chain(inst["world"], inst["stages"], plan))
        assert {k for k, v in r["constraint_ok"].items() if not v} == expect, mode


@pytest.mark.parametrize("domain", sorted(DOMAINS))
def test_formats_are_nested_and_share_wording(domain):
    mod = DOMAINS[domain]
    f = mod.FORMATS
    assert set(f["short"]) <= set(f["medium"]) <= set(f["long"])
    assert f["short"][-1] == f["medium"][-1] == f["long"][-1] == mod.ANCHOR_STAGE
    for sc in mod.SCENARIOS:
        req = {fmt: _load(ROOT / "tasks" / "exp2" / f"{domain}_s{sc['id']}_{fmt}.json")["requests"] for fmt in f}
        for lang in req["short"]:
            lines = {fmt: req[fmt][lang].split("\n") for fmt in f}
            assert set(lines["short"]) <= set(lines["medium"]) <= set(lines["long"])


def test_committed_instances_are_current():
    from tasks.build_exp2 import OUT, build_all
    for name, text in build_all().items():
        assert (OUT / name).read_text(encoding="utf-8") == text, name


def test_lexicon_drafts_pass_hygiene():
    import importlib
    import pkgutil

    from tasks.check_lexicon import problems
    pkg = importlib.import_module("env.exp2.lexicon_drafts")
    for info in pkgutil.iter_modules(pkg.__path__):
        domain, _, lang = info.name.rpartition("_")
        lex = importlib.import_module(f"env.exp2.lexicon_drafts.{info.name}").LEX
        en = importlib.import_module(f"env.exp2.lexicon_src.{domain}_en").LEX
        assert problems(domain, lang, lex, en) == [], info.name
