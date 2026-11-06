#!/usr/bin/env python3
"""
pl_check.py - catch Polish that sounds translated, corporate or stiff, before it
goes out. Rules and phrase list: skills/pl-naturalnie/ (SKILL.md, kalki.json).

Checks every text of a week (slides, captions, Reel heading/close/points/voice):
  - calques and corporate phrases from kalki.json, with what to write instead,
  - the Reel screens, which the narrator reads word for word: no abbreviations,
    symbols, brackets, arrows or links (numbers are fine, they get spelled out).

Usage
  python3 tools/pl_check.py weeks/2026-11-02
  python3 tools/pl_check.py weeks/2026-11-02/k2.json
Exit code 1 when anything is flagged.
"""

import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from reel_text import PARTS, voice_script  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
RULES = json.loads((ROOT / "skills" / "pl-naturalnie" / "kalki.json").read_text(encoding="utf-8"))
PHRASES = [(re.compile(p["regex"], re.IGNORECASE), p["fix"]) for p in RULES["phrases"]]
VOICE_BANNED = re.compile(RULES["voice_banned"], re.IGNORECASE)
SLIDE_FIELDS = ("kicker", "title", "subtitle", "body", "button")
META_FIELDS = ("caption_ig", "caption_reel", "reel_heading", "reel_close", "reel_cta", "alt")


def texts(spec):
    """(where, text, is_social)"""
    meta = spec.get("meta", {})
    for f in META_FIELDS:
        if meta.get(f):
            yield f"meta.{f}", meta[f], True
    if meta.get("caption_fb"):
        yield "meta.caption_fb", meta["caption_fb"], True
    for i, p in enumerate(meta.get("reel_points") or []):
        yield f"meta.reel_points[{i}]", p, True
    rp = meta.get("reel_pendulum") or {}
    for i, q in enumerate(rp.get("questions") or []):
        yield f"meta.reel_pendulum.questions[{i}]", q, True
    if rp.get("answer"):
        yield "meta.reel_pendulum.answer", rp["answer"], True
    for i, a in enumerate(rp.get("answers") or []):
        yield f"meta.reel_pendulum.answers[{i}]", a, True
    if rp.get("closing"):
        yield "meta.reel_pendulum.closing", rp["closing"], True
    cover = meta.get("reel_cover") or {}
    for f in ("kicker", "title", "subtitle"):
        if cover.get(f):
            yield f"meta.reel_cover.{f}", cover[f], True
    for n, s in enumerate(spec.get("slides", []), 1):
        for f in SLIDE_FIELDS:
            if s.get(f):
                yield f"slajd {n}.{f}", s[f], True
        for i, it in enumerate(s.get("items", [])):
            yield f"slajd {n}.items[{i}]", it, True


def check_spec(path, published=False):
    spec = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for where, text, social in texts(spec):
        if published and where.startswith(("slajd", "meta.caption_ig", "meta.caption_fb", "meta.alt")):
            continue                                   # already on Instagram, nothing to fix
        clean = text.replace("*", "")
        for rx, fix in PHRASES:
            m = rx.search(clean)
            if m:
                out.append((where, m.group(0), fix))
    for part, script in zip(PARTS, voice_script(spec)):
        for m in VOICE_BANNED.finditer(script["text"]):
            out.append((f"rolka, ekran {part}", m.group(0),
                        "lektor czyta ekran rolki słowo w słowo: bez skrótów, symboli, nawiasów i linków"))
    return out


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    target = pathlib.Path(sys.argv[1])
    paths = sorted(target.glob("k*.json")) if target.is_dir() else [target]
    published = set()
    state = ROOT / "state" / "published.json"
    if state.exists():
        published = {k for k, v in json.loads(state.read_text(encoding="utf-8")).items()
                     if v.get("status") == "published"}
    total = 0
    for p in paths:
        key = f"{p.parent.name}/{p.stem}"
        for where, found, fix in check_spec(p, key in published):
            total += 1
            print(f"{p.parent.name}/{p.name}  {where}: \"{found}\"  ->  {fix}")
    print(f"\nnaturalny polski: {total} uwag w {len(paths)} plikach")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
