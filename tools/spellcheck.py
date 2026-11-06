#!/usr/bin/env python3
"""
spellcheck.py - check every word of a week's carousels against a Polish dictionary
before anything is published: slide text, captions, the Reel heading and alt text.

Skipped on purpose: hashtags, @handles, links and domains, words with digits,
ALL-CAPS keywords (TELEFON, SSL) and the brand/tech words in config/words.txt.
A capitalised word also passes if its lower-case form is in the dictionary.

Usage
  python3 tools/spellcheck.py weeks/2026-11-02           # every k*.json in the week
  python3 tools/spellcheck.py weeks/2026-11-02/k2.json
Exit code 1 when something is unknown, with suggestions next to each word.
Fix the copy, or add a real proper name to config/words.txt. Never add a typo there.
"""

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DICT = ROOT / "assets" / "dict" / "pl_PL"
ALLOW = ROOT / "config" / "words.txt"

SLIDE_FIELDS = ("kicker", "title", "subtitle", "body", "button")
META_FIELDS = ("topic", "caption_ig", "caption_fb", "caption_reel", "reel_heading", "reel_close", "alt")
SKIP = re.compile(r"(?:#|@)\S+|https?://\S+|\b\S+\.(?:pl|com|dev|app|io|net|org|eu)\S*", re.IGNORECASE)
WORD = re.compile(r"[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż]+(?:-[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż]+)*")


def texts(spec):
    meta = spec.get("meta", {})
    for f in META_FIELDS:
        if meta.get(f):
            yield f"meta.{f}", meta[f]
    for i, p in enumerate(meta.get("reel_points") or []):
        yield f"meta.reel_points[{i}]", p
    rp = meta.get("reel_pendulum") or {}                 # written in capitals: check them in lower case
    for i, q in enumerate(rp.get("questions") or []):
        yield f"meta.reel_pendulum.questions[{i}]", q.lower()
    if rp.get("answer"):
        yield "meta.reel_pendulum.answer", rp["answer"].lower()
    for i, a in enumerate(rp.get("answers") or []):
        yield f"meta.reel_pendulum.answers[{i}]", a.lower()
    if rp.get("closing"):
        yield "meta.reel_pendulum.closing", rp["closing"].lower()
    for i, pal in enumerate(rp.get("palettes") or []):
        for f in ("name", "button"):
            if pal.get(f):
                yield f"meta.reel_pendulum.palettes[{i}].{f}", pal[f].lower()
    for n, s in enumerate(spec.get("slides", []), 1):
        for f in SLIDE_FIELDS:
            if s.get(f):
                yield f"slajd {n}.{f}", s[f]
        for i, it in enumerate(s.get("items", [])):
            yield f"slajd {n}.items[{i}]", it
        for f, v in [("note", s.get("note"))] + [(f"mock.{k}", v) for k, v in (s.get("mock") or {}).items()] \
                + [(f"palette.names.{k}", v) for k, v in ((s.get("palette") or {}).get("names") or {}).items()]:
            if v:
                yield f"slajd {n}.{f}", v


def allowlist():
    if not ALLOW.exists():
        return set()
    return {w.strip().lower() for w in ALLOW.read_text(encoding="utf-8").splitlines()
            if w.strip() and not w.startswith("#")}


def check(paths):
    from spylls.hunspell import Dictionary
    d = Dictionary.from_files(str(DICT))
    allowed = allowlist()
    problems = []
    for path in paths:
        spec = json.loads(path.read_text(encoding="utf-8"))
        for where, text in texts(spec):
            clean = SKIP.sub(" ", text.replace("*", ""))
            for word in WORD.findall(clean):
                if (len(word) < 2 or word.isupper() or word.lower() in allowed
                        or d.lookup(word) or d.lookup(word.lower())
                        or all(d.lookup(p) or d.lookup(p.lower()) for p in word.split("-"))):
                    continue
                problems.append((path, where, word))
    for path, where, word in problems:
        sugg = ", ".join(list(d.suggest(word))[:3]) or "brak podpowiedzi"
        print(f"{path.parent.name}/{path.name}  {where}: \"{word}\"  ->  {sugg}")
    return problems


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    target = pathlib.Path(sys.argv[1])
    paths = sorted(target.glob("k*.json")) if target.is_dir() else [target]
    problems = check(paths)
    print(f"\npisownia: {len(problems)} nieznanych słów w {len(paths)} plikach")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
