"""
Builds Experiment 2 task instances, tasks/exp2/<domain>_s<N>_<format>.json:
five scenarios per domain, each in three nested formats. Every instance
carries its generated world, the stage list, the request in every language
that has authored text, and a gold chain replayed through the tools before
it is written. Lexicons are assembled from env/exp2/lexicon_src/<domain>_<lang>.py.

    python -m tasks.build_exp2          # rebuild
    python -m tasks.build_exp2 --check  # fail if a committed file is stale
"""

import argparse
import importlib
import json
import sys
from pathlib import Path

from env.exp2.core import FORMATS, LANGS, LEXICON_DIR, render_request
from env.exp2.registry import DOMAINS
from env.tools.travel_tools import ToolError

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tasks" / "exp2"
SRC = "env.exp2.lexicon_src"


def assemble_lexicon(domain: str) -> dict:
    lex = {"intro": {}, "clauses": {}, "terms": {}, "stage_clause": {}, "verification": {}}
    for lang in LANGS:
        try:
            mod = importlib.import_module(f"{SRC}.{domain}_{lang}")
        except ModuleNotFoundError:
            continue
        src = mod.LEX
        lex["intro"][lang] = src.get("intro", "")
        for k, v in src["clauses"].items():
            lex["clauses"].setdefault(k, {})[lang] = v
        for g, entries in src["terms"].items():
            for k, v in entries.items():
                lex["terms"].setdefault(g, {}).setdefault(k, {})[lang] = v
        lex["verification"][lang] = getattr(mod, "VERIFICATION", "author" if lang == "en" else "pending: Rishabh")
    return lex


def build_instance(domain, mod, scenario, fmt, lex):
    world = mod.generate(scenario)
    stages = mod.FORMATS[fmt]
    mod.check_rules(world, stages)
    plan = mod.solve(world, stages)
    steps = mod.chain(world, stages, plan)
    values = mod.slots(world, stages)
    inst = {"template_id": f"{domain}_s{scenario['id']}_{fmt}", "experiment": "exp2", "domain": domain, "scenario": scenario["id"],
            "format": fmt, "stages": stages, "anchor_stage": mod.ANCHOR_STAGE, "session_date": world["session_date"],
            "world": world,
            "requests": {l: render_request(lex, l, stages, values) for l in LANGS if l in lex["intro"]},
            "verification": lex["verification"]}
    tools = mod.Tools(inst, "en")
    result = None
    for st in steps:
        try:
            result = tools.call(st["tool"], st["args"])
        except ToolError as e:
            raise AssertionError(f"{inst['template_id']}: gold step {st['tool']} failed: {e.message}")
    assert result and result.get("status") in ("placed", "confirmed", "submitted", "executed"), (inst["template_id"], result)
    inst["gold_steps"] = steps
    inst["horizon"] = len(steps)
    return inst


def build_all():
    out = {}
    for domain, mod in DOMAINS.items():
        lex = assemble_lexicon(domain)
        (LEXICON_DIR / f"{domain}.json").write_text(json.dumps(lex, indent=1, ensure_ascii=True) + "\n", encoding="utf-8")
        for scenario in mod.SCENARIOS:
            for fmt in FORMATS:
                inst = build_instance(domain, mod, scenario, fmt, lex)
                out[f"{inst['template_id']}.json"] = json.dumps(inst, indent=1, ensure_ascii=True) + "\n"
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    files = build_all()
    OUT.mkdir(parents=True, exist_ok=True)
    stale = []
    for name, text in files.items():
        path = OUT / name
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(name)
        else:
            path.write_text(text, encoding="utf-8")
    for name, text in sorted(files.items()):
        inst = json.loads(text)
        print(f"{name}: {len(inst['stages'])} stages, {inst['horizon']} calls, languages {sorted(inst['requests'])}")
    if stale:
        sys.exit(f"stale: {stale}")


if __name__ == "__main__":
    main()
