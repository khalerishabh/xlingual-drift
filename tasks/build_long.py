"""
Builds the long-horizon task instances, tasks/long/<domain>_<NN>.json:
ten per domain, each with its own generated world, the request in every
language, and a gold chain that is replayed through the tools before it is
written (docs/LONG_SPEC.md). Seeds are taken in order and kept only if the
world passes every design rule, so instances are never chosen by results.

    python -m tasks.build_long          # rebuild
    python -m tasks.build_long --check  # fail if a committed file is stale
"""

import argparse
import json
import sys
from pathlib import Path

from env.long.base import load_lexicon
from env.long.registry import DOMAINS
from env.tools.travel_tools import ToolError

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tasks" / "long"
LANGS = ("en", "zh", "hi", "ta", "hinglish")
PER_DOMAIN = 10


def build_instance(domain: str, seed: int, index: int) -> dict:
    mod = DOMAINS[domain]["module"]
    world = mod.generate(seed)
    mod.check_rules(world)
    lex = load_lexicon(domain)
    steps = mod.chain(world, mod.plan_from_answer(world))
    inst = {"template_id": f"{domain}_{index:02d}", "domain": domain, "seed": seed, "session_date": world["session_date"],
            "world": world, "requests": {l: mod.render_request(world, lex, l) for l in LANGS}}
    tools = DOMAINS[domain]["tools"](inst, "en")
    result = None
    for st in steps:
        try:
            result = tools.call(st["tool"], st["args"])
        except ToolError as e:
            st["expect_error"] = e.error_type
    assert result and result.get("status") in ("placed", "executed"), (domain, seed, result)
    inst["gold_steps"] = steps
    inst["horizon"] = len(steps)
    inst["verification"] = {"en": "author", "zh": "pending: translator back-translation",
                            "hi": "pending: author", "ta": "pending: author", "hinglish": "pending: author"}
    return inst


def build_all():
    out = {}
    for domain in DOMAINS:
        seed, n = 0, 0
        while n < PER_DOMAIN:
            seed += 1
            try:
                inst = build_instance(domain, seed, n + 1)
            except AssertionError:
                continue
            n += 1
            out[f"{inst['template_id']}.json"] = json.dumps(inst, indent=1, ensure_ascii=True) + "\n"
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    files = build_all()
    stale = []
    OUT.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        path = OUT / name
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(name)
        else:
            path.write_text(text, encoding="utf-8")
    for name, text in sorted(files.items()):
        inst = json.loads(text)
        print(f"{name}: seed {inst['seed']}, {inst['horizon']} steps")
    if stale:
        sys.exit(f"stale: {stale}")


if __name__ == "__main__":
    main()
