"""
Shared machinery for Experiment 2 (docs/EXP2_SPEC.md).

A scenario is a generated world plus an ordered list of stages. A format
(short, medium, long) is a nested subset of those stages: medium is a subset
of long and short a subset of medium, with shared clauses worded identically.
Anchor constraints are stated in every format and committed only in the
final state-changing call, so their carry distance grows with the format.

Every domain module provides:
  SCENARIOS      five scenario specs
  FORMATS        {"short": [...], "medium": [...], "long": [...]} stage names
  ANCHOR_STAGE   the stage whose constraints are committed at the final call
  generate(scenario) -> world
  solve(world, stages) -> plan
  chain(world, stages, plan) -> gold steps
  slots(world, stages) -> values for the request clauses
  check_rules(world, stages)
  Tools(instance)  with TERMINAL_TOOL and snapshot()
  verify(traj, instance, final_state) -> record (via summarize)
  FAULTS, faulty_plan(world, stages, mode) -> (plan, expected failed names)

The verifier records, for every constraint, the exact value expected and
the value committed, so the stage-attribution pass (eval/stages.py) can
check whether the agent held the right value before it committed a wrong
one, without reading free text.
"""

import json
from pathlib import Path

from env.tools.travel_tools import ToolError

LANGS = ("en", "hi", "ta", "hinglish", "tanglish")
FORMATS = ("short", "medium", "long")
LEXICON_DIR = Path(__file__).resolve().parent / "lexicon"
CLASSES = ("selection", "attribute", "binding", "carried", "coupled", "anchor", "global")


def load_lexicon(domain: str) -> dict:
    return json.loads((LEXICON_DIR / f"{domain}.json").read_text(encoding="utf-8"))


def fn(name, description, properties, required=None):
    return {"name": name, "description": description,
            "parameters": {"type": "object", "properties": properties,
                           "required": list(properties) if required is None else required}}


S = {"type": "string"}
I = {"type": "integer"}
N = {"type": "number"}
B = {"type": "boolean"}


def enum(values, description=None):
    out = {"type": "string", "enum": list(values)}
    if description:
        out["description"] = description
    return out


def arr(item):
    return {"type": "array", "items": item}


class Exp2Tools:
    TERMINAL_TOOL = None
    DOMAIN = None

    def __init__(self, instance: dict, language: str = "en"):
        self.instance = instance
        self.world = instance["world"]
        self.stages = instance["stages"]
        self.language = language
        self._sold_out = set()
        self.committed = None
        self.schemas = {s["name"]: s for s in self.tool_schemas()}

    def tool_schemas(self) -> list[dict]:
        raise NotImplementedError

    def schema_list(self) -> list[dict]:
        return list(self.schemas.values())

    def mark_sold_out(self, item_id: str):
        self._sold_out.add(item_id)

    @staticmethod
    def bad(msg: str):
        raise ToolError("validation", f"ValidationError: {msg}")

    @staticmethod
    def not_found(msg: str):
        raise ToolError("not_found", f"NotFound: {msg}")

    def call(self, tool_name: str, args: dict) -> dict:
        schema = self.schemas.get(tool_name)
        if schema is None:
            self.bad(f"unknown tool '{tool_name}'")
        if not isinstance(args, dict):
            self.bad(f"arguments for {tool_name} must be an object")
        params = schema["parameters"]
        for key in args:
            if key not in params["properties"]:
                self.bad(f"unexpected argument '{key}' for {tool_name}")
        for key in params["required"]:
            if key not in args:
                self.bad(f"missing required argument '{key}' for {tool_name}")
        for key, spec in params["properties"].items():
            if key in args and "enum" in spec and args[key] not in spec["enum"]:
                self.bad(f"'{key}' must be one of {spec['enum']}")
        return getattr(self, tool_name)(**args)

    def snapshot(self) -> dict:
        raise NotImplementedError


# --- request rendering -----------------------------------------------------

def term(group: str, key: str):
    """A slot value that is translated through the lexicon's canonical-term
    table (TRANSLATE-CANONICAL in the spec)."""
    return ("term", group, key)


def render_request(lex: dict, lang: str, stages: list[str], values: dict) -> str:
    def fill(template: str) -> str:
        vals = {}
        for k, v in values.items():
            if k.startswith("_"):
                continue
            if isinstance(v, tuple) and v and v[0] == "term":
                entry = lex["terms"][v[1]][v[2]]
                vals[k] = entry.get(lang, entry["en"])
            else:
                vals[k] = v
        return template.format(**vals)

    prefix = values.get("_clause_prefix", "")
    parts = [fill(lex["clauses"][prefix + "intro"][lang] if prefix else lex["intro"][lang])]
    for st in stages:
        key = prefix + lex["stage_clause"].get(st, st)
        parts.append(fill(lex["clauses"][key][lang]))
    if "outro" in lex:
        parts.append(fill(lex["outro"][lang]))
    return "\n".join(p for p in parts if p)


# --- verification ----------------------------------------------------------

def check(name, stage, cls, ok, step, expected=None, got=None, decoy=None, anchor=False):
    assert cls in CLASSES, cls
    return {"name": name, "stage": stage, "class": cls, "ok": bool(ok), "step": step,
            "expected": None if expected is None else str(expected),
            "got": None if got is None else str(got),
            "decoy_hit": bool(decoy is not None and got is not None and str(got) == str(decoy)),
            "decoy": None if decoy is None else str(decoy), "anchor": bool(anchor)}


def step_of(steps, tool, pred=lambda a: True):
    """1-based index of the last successful call to `tool` whose args satisfy pred."""
    found = None
    for i, s in enumerate(steps, 1):
        if s["tool"] == tool and "result" in s and isinstance(s.get("args"), dict):
            try:
                if pred(s["args"]):
                    found = i
            except (KeyError, TypeError, AttributeError):
                continue
    return found


def summarize(traj, instance: dict, checks: list[dict], completed: bool) -> dict:
    """`success` needs every constraint and the final commit; `success_state`
    scores what was built even if the final commit never happened, leaving
    out the anchors (which only the final commit can satisfy)."""
    by_name = {c["name"]: c for c in checks}
    ok = completed and all(c["ok"] for c in checks)
    state_ok = all(c["ok"] for c in checks if not c["anchor"])
    by_class = {}
    for c in checks:
        by_class.setdefault(c["class"], []).append(c["ok"])
    return {
        "success": ok,
        "success_state": state_ok,
        "completed": completed,
        "constraint_ok": {n: c["ok"] for n, c in by_name.items()},
        "constraint_class": {n: c["class"] for n, c in by_name.items()},
        "constraint_stage": {n: c["stage"] for n, c in by_name.items()},
        "constraint_commit_step": {n: c["step"] for n, c in by_name.items()},
        "constraint_expected": {n: c["expected"] for n, c in by_name.items()},
        "constraint_got": {n: c["got"] for n, c in by_name.items()},
        "constraint_decoy": {n: c["decoy"] for n, c in by_name.items()},
        "constraint_decoy_hit": {n: c["decoy_hit"] for n, c in by_name.items()},
        "constraint_anchor": {n: c["anchor"] for n, c in by_name.items()},
        **{f"all_{k}_ok": all(v) for k, v in by_class.items()},
        "format": instance["format"],
        "scenario": instance["scenario"],
        "n_stages": len(instance["stages"]),
        "validation_errors": sum(1 for s in traj.steps if s.get("error", {}).get("error_type") == "validation"),
        "first_error_step": traj.first_error_step,
        "num_steps_taken": len(traj.steps),
        "extra_steps": len(traj.steps) - len(instance["gold_steps"]),
        "injected": traj.injected_error is not None,
        "injected_at_step": traj.injected_at_step,
        "recovered": ok if traj.injected_error is not None else None,
        "booked": completed,
    }


def assert_never_first(listing: list, answer_id, key: str, where: str):
    if listing and listing[0][key] == answer_id:
        raise AssertionError(f"never-first rule: the answer {answer_id} is listed first in {where}")
