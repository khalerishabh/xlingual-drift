"""
Shared machinery for the long-horizon domains (docs/LONG_SPEC.md).

Each task instance carries its own world, so a domain's tools are built
from the instance. Seams (RQ3, Section 8.5 of the project doc) decide which
parts of the trajectory are in the task language:

  S0  request en, tool outputs en, errors en   (English episodes)
  S1  request L,  tool outputs en, errors en   (the realistic default)
  S2  request L,  tool outputs L,  errors en
  S3  request L,  tool outputs L,  errors L

Only human-readable text is localised (notices, labels, addresses,
relations); ids, numbers, keys and enum values stay as they are, as in real
APIs.
"""

import json
import random
from pathlib import Path

from env.tools.travel_tools import ToolError

LEXICON_DIR = Path(__file__).resolve().parent / "lexicon"
SEAMS = {"S0": (False, False), "S1": (False, False), "S2": (True, False), "S3": (True, True)}


def load_lexicon(domain: str) -> dict:
    return json.loads((LEXICON_DIR / f"{domain}.json").read_text(encoding="utf-8"))


def neighbour_id(value: str, rng: random.Random) -> str:
    """Same characters with two adjacent digits swapped: the kind of id a
    reader confuses with the original."""
    digits = [i for i, ch in enumerate(value) if ch.isdigit()]
    pairs = [(a, b) for a, b in zip(digits, digits[1:]) if b == a + 1 and value[a] != value[b]]
    a, b = rng.choice(pairs)
    chars = list(value)
    chars[a], chars[b] = chars[b], chars[a]
    return "".join(chars)


def is_neighbour(a: str, b: str) -> bool:
    if a == b or len(a) != len(b):
        return False
    diff = [i for i in range(len(a)) if a[i] != b[i]]
    return len(diff) == 2 and diff[1] == diff[0] + 1 and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]]


class LongTools:
    """Base class: schema validation, seam-aware text, localised errors."""

    TERMINAL_TOOL = None
    DOMAIN = None

    def __init__(self, instance: dict, language: str = "en", seam: str = "S1"):
        self.instance = instance
        self.world = instance["world"]
        self.language = language
        self.seam = "S0" if language == "en" else seam
        self.local_outputs, self.local_errors = SEAMS[self.seam]
        self.lex = load_lexicon(self.DOMAIN)
        self._sold_out = set()
        self.schemas = {s["name"]: s for s in self.tool_schemas()}

    def tool_schemas(self) -> list[dict]:
        raise NotImplementedError

    def schema_list(self) -> list[dict]:
        return list(self.schemas.values())

    def mark_sold_out(self, item_id: str):
        self._sold_out.add(item_id)

    def text(self, key: str, **kw) -> str:
        lang = self.language if self.local_outputs else "en"
        table = self.lex["outputs"][key]
        return table.get(lang, table["en"]).format(**kw)

    def label(self, group: str, value: str) -> str:
        if not self.local_outputs:
            return self.lex["labels"][group][value]["en"]
        entry = self.lex["labels"][group][value]
        return entry.get(self.language, entry["en"])

    def fail(self, error_type: str, key: str, **kw):
        lang = self.language if self.local_errors else "en"
        table = self.lex["errors"][key]
        raise ToolError(error_type, table.get(lang, table["en"]).format(**kw))

    def bad(self, msg: str):
        raise ToolError("validation", f"ValidationError: {msg}")

    def call(self, tool_name: str, args: dict) -> dict:
        schema = self.schemas.get(tool_name)
        if schema is None:
            self.bad(f"unknown tool '{tool_name}'")
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


def fn(name, description, properties, required=None):
    return {"name": name, "description": description,
            "parameters": {"type": "object", "properties": properties,
                           "required": list(properties) if required is None else required}}


S = {"type": "string"}
I = {"type": "integer"}
N = {"type": "number"}
