"""
reel_text.py - what a Reel shows on its three screens, and what the narrator says.

The narrator reads exactly the words on the screen, nothing else: the cover title
and subtitle, the list heading and every point, the closing line and the button.
The small topic pill and "reszta w opisie" are labels, so they are not read.
Only the form changes, never the words: a sentence gets its full stop, a heading's
colon becomes a full stop, and lektor.py spells numbers out ("3" -> "trzy") and says
the keyword in lower case, because a TTS model reads "TURBO" letter by letter.

Shared by make_reel.py (screens), lektor.py (recording) and pl_check.py (checks).
No heavy imports here: it must run everywhere.
"""

import re

NUMBERED = re.compile(r"\d+\s*/\s*\d+|krok\s*\d+|^\s*\d+\s*[.)]", re.IGNORECASE)
PARTS = ("cover", "list", "sell")
SPOKEN_KINDS = ("title", "subtitle", "heading", "item", "close", "outro")


def reel_points(spec):
    """(heading, points) for the list screen.

    The points are the numbered slides (kicker like "powód 2/5" or "krok 3"), so the
    list matches the number promised on the cover; meta.reel_points overrides.
    The heading says what the list is (meta.reel_heading, else the recap title)."""
    slides, meta = spec["slides"], spec.get("meta", {})
    points = meta.get("reel_points")
    if not points:
        body = [s for s in slides[1:] if s.get("title") and s.get("type", "text") not in ("list", "cta")]
        numbered = [s for s in body if NUMBERED.search(s.get("kicker", ""))]
        points = [s["title"] for s in (numbered or body[1:] or body)]
    heading = meta.get("reel_heading")
    if not heading:
        recap = next((s for s in slides if s.get("type") == "list" and s.get("title")), None)
        heading = (recap["title"].rstrip(":") + ":") if recap else ""
    return heading, points


def reel_sell(spec):
    """(closing line, button text). The button asks for the keyword when there is one,
    so every comment it brings lands on Jakub's Telegram as a lead."""
    meta = spec.get("meta", {})
    kw = meta.get("cta_keyword", "").strip()
    cta = meta.get("reel_cta") or (f"Napisz {kw} w komentarzu" if kw else "Napisz do nas wiadomość")
    return meta.get("reel_close", ""), cta


def screen_blocks(spec):
    """The spoken blocks of the three screens, in order, as [(kind, text), ...]."""
    cover = spec["slides"][0]
    heading, points = reel_points(spec)
    close, cta = reel_sell(spec)
    screens = [
        [("title", cover.get("title", "")), ("subtitle", cover.get("subtitle", ""))],
        [("heading", heading)] + [("item", p) for p in points],
        [("close", close), ("outro", cta)],
    ]
    return [[(k, t) for k, t in sc if t and t.strip()] for sc in screens]


def sentences(text):
    return [s.strip() for s in re.findall(r"[^.!?]+[.!?]*", text) if s.strip()]


def as_sentence(text):
    """Screen text as one or more full sentences - same words, same order."""
    t = " ".join(text.replace("*", "").split())
    t = re.sub(r"\s*:$", ".", t)
    if t and t[-1] not in ".!?":
        t += "."
    return t


def voice_script(spec):
    """For each screen: {"text": what the narrator reads, "starts": for every spoken
    block, the index of the sentence it begins with} - used to sync the screen."""
    out = []
    for blocks in screen_blocks(spec):
        parts, starts, n = [], [], 0
        for _, text in blocks:
            s = as_sentence(text)
            starts.append(n)
            n += len(sentences(s))
            parts.append(s)
        out.append({"text": " ".join(parts), "starts": starts})
    return out


def speakable(text, keyword=""):
    """The same sentence, ready for the TTS model: numbers as words, the keyword in
    lower case. Needs num2words (installed where lektor.py runs)."""
    from num2words import num2words
    text = re.sub(r"\d+", lambda m: num2words(int(m.group(0)), lang="pl"), text)
    if keyword:
        text = re.sub(rf"\b{re.escape(keyword)}\b", keyword.lower(), text)
    text = re.sub(r"\b[A-ZĄĆĘŁŃÓŚŹŻ]{4,}\b", lambda m: m.group(0).lower(), text)
    # a sentence that now starts with a spelled-out number starts with a capital again
    return re.sub(r"(^|[.!?]\s+)(\w)", lambda m: m.group(1) + m.group(2).upper(), text)
