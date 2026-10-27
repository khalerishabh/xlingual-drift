"""
Script-hygiene and slot check for Experiment 2 lexicons, run before a
language is frozen. For every <domain>_<lang> module in lexicon_src (and,
with --drafts, lexicon_drafts) against its English source:

  - the same clause keys and term keys as English
  - the same {slot} placeholders in every clause
  - hi and ta: every letter is in the language's script, except Latin
    words on the allow-list (brands, acronyms, ids)
  - hinglish and tanglish: ASCII only, plus the rupee sign

    python -m tasks.check_lexicon            # frozen sources
    python -m tasks.check_lexicon --drafts   # drafts awaiting review
"""

import argparse
import importlib
import pkgutil
import re
import string
import sys

SCRIPTS = {"hi": (0x0900, 0x097F), "ta": (0x0B80, 0x0BFF)}
LATIN_OK = {"HDFC", "ICICI", "SBI", "NEFT", "IMPS", "UPI", "SUV", "SMS", "Amazon", "Pay", "Paytm", "PhonePe",
            "km"}
RUPEE = "\u20b9"


def slots_of(text):
    return {f for _, f, _, _ in string.Formatter().parse(text) if f}


def problems(domain, lang, lex, en):
    out = []
    if set(lex["clauses"]) != set(en["clauses"]):
        out.append(f"clause keys differ: missing {sorted(set(en['clauses']) - set(lex['clauses']))}, "
                   f"extra {sorted(set(lex['clauses']) - set(en['clauses']))}")
    for g, entries in en.get("terms", {}).items():
        if set(lex.get("terms", {}).get(g, {})) != set(entries):
            out.append(f"term keys differ in '{g}'")
    texts = {"intro": lex.get("intro", "")} if "intro" in en else {}
    texts.update(lex["clauses"])
    for k, text in texts.items():
        ref = en["intro"] if k == "intro" else en["clauses"].get(k, "")
        if slots_of(text) != slots_of(ref):
            out.append(f"{k}: slots {sorted(slots_of(text))} != English {sorted(slots_of(ref))}")
    for g, entries in lex.get("terms", {}).items():
        for k, v in entries.items():
            texts[f"term {g}.{k}"] = v
    for k, text in texts.items():
        bare = re.sub(r"\{[^}]*\}", "", text)
        if lang in SCRIPTS:
            lo, hi = SCRIPTS[lang]
            for word in re.findall(r"[A-Za-z]+", bare):
                if word not in LATIN_OK:
                    out.append(f"{k}: Latin word '{word}' in {lang}")
            for ch in bare:
                if ch.isalpha() and not ch.isascii() and not lo <= ord(ch) <= hi:
                    out.append(f"{k}: character {ch!r} outside the {lang} script")
        else:
            bad = {ch for ch in bare if not ch.isascii() and ch != RUPEE}
            if bad:
                out.append(f"{k}: non-ASCII characters {sorted(bad)} in {lang}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drafts", action="store_true")
    a = ap.parse_args()
    pkg = "env.exp2.lexicon_drafts" if a.drafts else "env.exp2.lexicon_src"
    mod = importlib.import_module(pkg)
    total = 0
    for info in sorted(pkgutil.iter_modules(mod.__path__), key=lambda i: i.name):
        domain, _, lang = info.name.rpartition("_")
        if lang == "en":
            continue
        lex = importlib.import_module(f"{pkg}.{info.name}").LEX
        en = importlib.import_module(f"env.exp2.lexicon_src.{domain}_en").LEX
        found = problems(domain, lang, lex, en)
        total += len(found)
        print(f"{info.name}: {'ok' if not found else f'{len(found)} problems'}")
        for p in found[:15]:
            print("   ", p)
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
