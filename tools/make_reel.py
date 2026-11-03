#!/usr/bin/env python3
"""
make_reel.py - turn a carousel spec into a short 9:16 Reel with the text typing
itself into a clean PageHub browser window, with original sound.

Three screens, each starting empty:
  1. the cover - a small topic pill, then the headline (accent words in teal)
     and the subtitle type out, and stay long enough to read every word;
  2. a heading that says what the list is (meta.reel_heading), then the
     headings of the numbered slides as a numbered list, one row at a time;
  3. the sell: a big closing line (meta.reel_close), the call-to-action button
     ("Napisz KEYWORD w komentarzu" from meta.cta_keyword, or meta.reel_cta)
     with a single "ping", and "reszta w opisie" under it. Everything sits inside the Reels safe zone, away from the
like/comment rail and the caption.

Sound: real clicky-switch recordings (Kailh Box White, MIT licence, see
assets/sounds) at a real typist's rhythm, a soft whoosh between the screens,
one ping at the end, and a chill night-drive bed generated here, so there is
nothing to license and nothing Instagram can mute.

Narrator: when weeks/<data>/kN/voice-{cover,list,sell}.wav exist (tools/lektor.py),
each screen gets its line. The list rows type as the narrator says them, the button
pings when the narrator asks for the comment, every screen lasts until the voice is
done, and the music and keys duck under the voice.

Usage
  python3 make_reel.py weeks/2026-11-02/k1.json                # -> weeks/.../k1/reel.mp4
  python3 make_reel.py weeks/2026-11-02/k1.json --out x.mp4
  python3 make_reel.py weeks/2026-11-02/k1.json --still 3.0    # one frame as PNG, for checking
"""

import argparse
import json
import math
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"

W, H, FPS = 1080, 1920, 30
SR = 48000

# palette, same as the carousels
BG = (9, 12, 17)
SURFACE = (17, 22, 30)
BAR = (22, 29, 39)
LINE = (38, 50, 66)
FG = (240, 244, 248)
BODY = (172, 184, 198)
MUTED = (104, 118, 135)
ACCENT = (28, 152, 195)
ACCENT_SOFT = (21, 60, 78)
INK = (8, 12, 16)

# window inside the Reels safe zone (top bar above y=230, caption below y=1440,
# action rail on the right)
WX, WY, WW, WH = 50, 300, 840, 1110
BAR_H = 84
PAD = 64
TX, TW = WX + PAD, WW - 2 * PAD
BODY_TOP, BODY_BOTTOM = WY + BAR_H + 50, WY + WH - 110

# pacing
CPS = {"title": 22, "subtitle": 34, "item": 30, "heading": 24, "close": 24}
GAP_AFTER = {"title": 0.25, "subtitle": 0.2, "item": 0.22, "heading": 0.35, "close": 0.3}
HOLD_COVER, HOLD_LAST, CLEAR, START = 2.0, 2.6, 0.32, 0.45
VOICE_PARTS = ("cover", "list", "sell")
VOICE_LEAD, VOICE_TAIL, VOICE_TAIL_LAST = 0.1, 0.55, 1.6
NOTE = "reszta w opisie ↓"


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


F_PILL = font("Inter-SemiBold.otf", 26)
F_SUB = font("Inter-Regular.otf", 40)
F_NUM = font("Inter-Bold.otf", 30)
F_OUTRO = font("Inter-Bold.otf", 38)
F_NOTE = font("Inter-Medium.otf", 30)
F_URL = font("Inter-Medium.otf", 26)
F_HANDLE = font("Inter-Medium.otf", 26)


# ---------------------------------------------------------------- text layout

def runs(text, color, accent=ACCENT):
    """'Ile *Twoja* strona' -> [(word, color), ...] with the accent applied."""
    out, prev_part = [], ""
    for i, part in enumerate(re.split(r"\*([^*]+)\*", text.replace("\n", " "))):
        words = part.split()
        # glue only when there is no space at the boundary on either side:
        # "*Bez szablonu*: tak" -> "szablonu:", but "na *telefonie*" stays two words
        if out and words and prev_part and not prev_part[-1].isspace() and not part[0].isspace():
            prev, prev_color = out[-1]
            out[-1] = (prev + words.pop(0), prev_color)
        for w in words:
            out.append((w, accent if i % 2 else color))
        if part:
            prev_part = part
    shown = " ".join(w for w, _ in out)
    source = " ".join(text.replace("*", "").split())
    if shown != source:
        raise ValueError(f"tekst w rolce różni się od źródła: {shown!r} zamiast {source!r}")
    return out


def wrap(words, fnt, width):
    """Greedy wrap of (word, color) runs into lines of (x, word, color)."""
    lines, line, x = [], [], 0
    space = fnt.getlength(" ")
    for w, c in words:
        wl = fnt.getlength(w)
        if line and x + wl > width:
            lines.append(line)
            line, x = [], 0
        line.append((x, w, c))
        x += wl + space
    if line:
        lines.append(line)
    return lines


def balanced(words, fnt, width):
    """Same number of lines as a greedy wrap, but evened out, so a headline never
    ends on one lonely word ("ma:", "klient!")."""
    lines = wrap(words, fnt, width)
    if len(lines) < 2:
        return lines
    lo, hi = int(width * 0.5), int(width)
    while lo < hi:
        mid = (lo + hi) // 2
        if len(wrap(words, fnt, mid)) <= len(lines):
            hi = mid
        else:
            lo = mid + 1
    return wrap(words, fnt, lo)


def text_block(kind, text, color, fnt, width, lh):
    words = runs(text, color)
    lines = balanced(words, fnt, width) if kind in ("title", "heading", "close", "item") else wrap(words, fnt, width)
    return {"kind": kind, "lines": lines, "font": fnt, "lh": int(fnt.size * lh),
            "chars": sum(len(w) + 1 for ln in lines for _, w, _ in ln)}


def cover_screen(slide):
    blocks = []
    if slide.get("kicker"):
        blocks.append({"kind": "pill", "text": slide["kicker"].replace("*", "").upper(), "gap": 0, "h": 52})
    for size in (86, 78, 70, 62):
        title = text_block("title", slide.get("title", ""), FG, font("Inter-Bold.otf", size), TW, 1.08)
        if len(title["lines"]) <= 4:
            break
    title["gap"] = 34 if blocks else 0
    blocks.append(title)
    if slide.get("subtitle"):
        sub = text_block("subtitle", slide["subtitle"], BODY, F_SUB, TW, 1.4)
        sub["gap"] = 38
        blocks.append(sub)
    return {"blocks": blocks, "url": ""}


def list_screen(heading, heads):
    """A heading that says what the list is, then numbered rows, sized to fit."""
    for size in (46, 42, 38, 34):
        fnt = font("Inter-SemiBold.otf", size)
        blocks = []
        if heading:
            hb = text_block("heading", heading, FG, font("Inter-Bold.otf", int(size * 1.3)), TW, 1.12)
            hb["gap"] = 0
            blocks.append(hb)
        for i, h in enumerate(heads):
            b = text_block("item", h, FG, fnt, TW - 92, 1.22)
            b.update(num=i + 1, gap=(int(size * 1.1) if heading else 0) if i == 0 else int(size * 0.95))
            blocks.append(b)
        if height(blocks) <= BODY_BOTTOM - BODY_TOP:
            break
    return {"blocks": blocks, "url": "/w-skrocie"}


def sell_screen(close, cta):
    """The last screen sells: the closing line big, the button, "reszta w opisie"."""
    blocks = []
    if close:
        for size in (78, 70, 62, 56):
            cb = text_block("close", close, FG, font("Inter-Bold.otf", size), TW, 1.1)
            if len(cb["lines"]) <= 4:
                break
        cb["gap"] = 0
        blocks.append(cb)
    blocks.append({"kind": "outro", "text": cta, "gap": 64 if close else 0, "h": 96})
    blocks.append({"kind": "note", "text": NOTE, "gap": 26, "h": 40})
    return {"blocks": blocks, "url": "/kontakt"}


def block_h(b):
    if b["kind"] in ("pill", "outro", "note"):
        return b["h"]
    return b["lh"] * len(b["lines"])


def height(blocks):
    return sum(b["gap"] + block_h(b) for b in blocks)


def place(screen):
    y = BODY_TOP + max(0, (BODY_BOTTOM - BODY_TOP - height(screen["blocks"])) // 2)
    for b in screen["blocks"]:
        y += b["gap"]
        b["y"] = y
        y += block_h(b)


NUMBERED = re.compile(r"\d+\s*/\s*\d+|krok\s*\d+|^\s*\d+\s*[.)]", re.IGNORECASE)


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


def screens_for(spec):
    heading, heads = reel_points(spec)
    close, cta = reel_sell(spec)
    out = [cover_screen(spec["slides"][0]), list_screen(heading, heads), sell_screen(close, cta)]
    for s in out:
        place(s)
    return out


# ---------------------------------------------------------------- timeline

def sync_targets(sc, voice):
    """When (seconds into the voice) each block should start, so the screen follows
    the narrator: list rows start with their sentence, the button with the last one."""
    if not voice:
        return {}
    segs, kinds = voice["segments"], [b["kind"] for b in sc["blocks"]]
    if "item" in kinds:
        idx = [i for i, k in enumerate(kinds) if k in ("heading", "item")]
        if len(segs) == len(idx):
            return {i: segs[j][0] for j, i in enumerate(idx)}
        items = [i for i in idx if kinds[i] == "item"]
        if len(segs) == len(items):
            return {i: segs[j][0] for j, i in enumerate(items)}
        return {}
    if "outro" in kinds and len(segs) >= 2:
        return {kinds.index("outro"): segs[-1][0]}
    return {}


def timeline(screens, voices=None):
    """When every block appears or types, how long each screen lasts, sound events."""
    plan, events, t = [], [], 0.0
    voices = voices or [None] * len(screens)
    for si, sc in enumerate(screens):
        first, last = si == 0, si == len(screens) - 1
        start = t
        t += START
        voice = voices[si] if si < len(voices) else None
        v0 = t + VOICE_LEAD
        if voice:
            events.append((v0, f"voice:{si}"))
        targets = sync_targets(sc, voice)
        for bi, b in enumerate(sc["blocks"]):
            if bi in targets:
                t = max(t, v0 + targets[bi] - 0.05)
            if b["kind"] in ("pill", "outro", "note"):
                b["t0"] = b["t1"] = t
                if b["kind"] == "outro":
                    events.append((t, "ping"))
                t += 0.35 if b["kind"] != "outro" else 0.25
                continue
            cps = CPS[b["kind"]]
            b["t0"], b["t1"] = t, t + b["chars"] / cps
            text = " ".join(w for ln in b["lines"] for _, w, _ in ln) + " "
            for k, ch in enumerate(text):
                events.append((t + k / cps, "space" if ch == " " else "key"))
            t = b["t1"] + GAP_AFTER[b["kind"]]
        typed = t
        t += HOLD_LAST if last else HOLD_COVER
        if voice:
            t = max(t, v0 + voice["seconds"] + (VOICE_TAIL_LAST if last else VOICE_TAIL))
        plan.append({**sc, "start": start, "typed": typed, "end": t})
        if not last:
            events.append((t, "whoosh"))
            t += CLEAR
    return plan, events, t


# ---------------------------------------------------------------- drawing

def glow_layers():
    """Two background states; the frame breathes slowly between them."""
    out = []
    for shift in (0, 1):
        bg = Image.new("RGB", (W, H), BG)
        glow = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(glow)
        d.ellipse((520 + shift * 90, -300 + shift * 60, 1500 + shift * 90, 680 + shift * 60), fill=(20, 70, 90))
        d.ellipse((-480 - shift * 60, 1300 - shift * 80, 560 - shift * 60, 2300 - shift * 80), fill=(16, 48, 62))
        out.append(Image.blend(bg, glow.filter(ImageFilter.GaussianBlur(170)), 0.95))
    return out


def window_layer(url, handle):
    """The browser window with its soft shadow, as an RGBA layer."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((WX + 10, WY + 40, WX + WW - 10, WY + WH + 40), 40,
                                            fill=(0, 0, 0, 150))
    layer.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(40)))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((WX, WY, WX + WW, WY + WH), 34, fill=SURFACE + (255,), outline=LINE + (255,), width=2)
    d.rounded_rectangle((WX + 2, WY + 2, WX + WW - 2, WY + BAR_H), 32, fill=BAR + (255,))
    d.rectangle((WX + 2, WY + BAR_H - 32, WX + WW - 2, WY + BAR_H), fill=BAR + (255,))
    d.line((WX, WY + BAR_H, WX + WW, WY + BAR_H), fill=LINE + (255,), width=2)
    for k in range(3):
        cx = WX + 40 + k * 30
        d.ellipse((cx - 8, WY + BAR_H // 2 - 8, cx + 8, WY + BAR_H // 2 + 8),
                  fill=(ACCENT if k == 0 else LINE) + (255,))
    px0, px1 = WX + 150, WX + WW - 40
    d.rounded_rectangle((px0, WY + 20, px1, WY + BAR_H - 20), 22, fill=(13, 17, 23, 255), outline=LINE + (255,))
    lock_x = px0 + 26
    d.rounded_rectangle((lock_x, WY + BAR_H // 2 - 2, lock_x + 16, WY + BAR_H // 2 + 11), 3, fill=MUTED + (255,))
    d.arc((lock_x + 2, WY + BAR_H // 2 - 12, lock_x + 14, WY + BAR_H // 2 + 2), 180, 360, fill=MUTED + (255,), width=3)
    d.text((lock_x + 30, WY + BAR_H // 2), handle, font=F_URL, fill=FG + (255,), anchor="lm")
    d.text((lock_x + 30 + F_URL.getlength(handle), WY + BAR_H // 2), url, font=F_URL, fill=MUTED + (255,),
           anchor="lm")
    d.text((TX, WY + WH - 56), "@" + handle, font=F_HANDLE, fill=MUTED + (255,), anchor="lm")
    return layer


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def draw_screen(img, sc, t, alpha, cursor_on):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a = int(255 * alpha)
    cursor = None
    for b in sc["blocks"]:
        if t < b["t0"]:
            break
        k = b["kind"]
        if k == "pill":
            p = ease((t - b["t0"]) / 0.3)
            w = F_PILL.getlength(b["text"]) + 44
            y = b["y"] + (1 - p) * 14
            d.rounded_rectangle((TX, y, TX + w, y + b["h"]), b["h"] // 2, fill=ACCENT_SOFT + (int(a * p),),
                                outline=ACCENT + (int(a * p),), width=2)
            d.text((TX + 22, y + b["h"] / 2), b["text"], font=F_PILL, fill=ACCENT + (int(a * p),), anchor="lm")
            continue
        if k == "outro":
            p = ease((t - b["t0"]) / 0.28)
            w = F_OUTRO.getlength(b["text"]) + 68
            s = 0.85 + 0.15 * p
            cx, cy = TX + w / 2, b["y"] + b["h"] / 2
            d.rounded_rectangle((cx - w * s / 2, cy - b["h"] * s / 2, cx + w * s / 2, cy + b["h"] * s / 2),
                                int(b["h"] * s / 2), fill=ACCENT + (int(a * p),))
            d.text((cx, cy), b["text"], font=F_OUTRO, fill=INK + (int(a * p),), anchor="mm")
            cursor = None
            continue
        if k == "note":
            p = ease((t - b["t0"]) / 0.35)
            d.text((TX + 4, b["y"] + b["h"] / 2 + (1 - p) * 8), b["text"], font=F_NOTE, fill=MUTED + (int(a * p),),
                   anchor="lm")
            continue
        span = max(b["t1"] - b["t0"], 1e-6)
        shown = b["chars"] if t >= b["t1"] else int(b["chars"] * (t - b["t0"]) / span)
        fnt = b["font"]
        left = TX
        if k == "item":
            p = ease((t - b["t0"]) / 0.22)
            r = 30 * (0.6 + 0.4 * p)
            cy = b["y"] + fnt.size * 0.62
            d.ellipse((TX + 30 - r, cy - r, TX + 30 + r, cy + r), fill=ACCENT_SOFT + (int(a * p),),
                      outline=ACCENT + (int(a * p),), width=2)
            d.text((TX + 30, cy), str(b["num"]), font=F_NUM, fill=ACCENT + (int(a * p),), anchor="mm")
            left = TX + 92
            if b["num"] > 1:
                ly = b["y"] - b["gap"] / 2
                d.line((TX, ly, TX + TW, ly), fill=LINE + (int(a * 0.8),), width=2)
        count = 0
        for li, line in enumerate(b["lines"]):
            ly = b["y"] + li * b["lh"]
            for x, word, color in line:
                if count >= shown:
                    break
                part = word[: max(0, shown - count)]
                d.text((left + x, ly), part, font=fnt, fill=color + (a,))
                cursor = (left + x + fnt.getlength(part) + 5, ly, fnt.size)
                count += len(word) + 1
            if count >= shown:
                break
    if cursor_on and alpha > 0.5:
        if cursor is None and not any(t >= b["t0"] for b in sc["blocks"] if b["kind"] not in ("pill",)):
            cursor = (TX, sc["blocks"][0]["y"] + (60 if sc["blocks"][0]["kind"] == "pill" else 0), 70)
        if cursor:
            x, y, size = cursor
            d.rounded_rectangle((x, y + size * 0.1, x + max(5, size // 14), y + size * 1.08), 2, fill=ACCENT + (a,))
    img.alpha_composite(layer)


def frame_at(plan, assets, t):
    g0, g1, windows = assets[:3]
    mix = 0.5 + 0.5 * math.sin(t * 0.5)
    for i, s in enumerate(plan):
        if t < s["end"] or i == len(plan) - 1:
            idx, alpha, at = i, 1.0, t
            typing = s["start"] + START <= t < s["typed"]
            cursor_on = typing or int(t * 1.8) % 2 == 0
            break
        if t < s["end"] + CLEAR:
            idx, alpha, at, cursor_on = i, 1 - (t - s["end"]) / CLEAR, s["end"], False
            break
    img = Image.blend(g0, g1, mix).convert("RGBA")
    img.alpha_composite(windows[min(idx + (1 if alpha < 1 else 0), len(windows) - 1)])
    draw_screen(img, plan[idx], at, alpha, cursor_on)
    # two-segment progress bar, like stories
    d = ImageDraw.Draw(img)
    gap, y = 16, WY - 48
    seg_w = (WW - gap * (len(plan) - 1)) / len(plan)
    for k, s in enumerate(plan):
        x0 = WX + k * (seg_w + gap)
        d.rounded_rectangle((x0, y, x0 + seg_w, y + 8), 4, fill=LINE)
        span = max(s["end"] - s["start"], 1e-6)
        p = 1.0 if t >= s["end"] else max(0.0, (t - s["start"]) / span)
        if p > 0:
            d.rounded_rectangle((x0, y, x0 + seg_w * p, y + 8), 4, fill=ACCENT)
    return img.convert("RGB")


# ---------------------------------------------------------------- sound

SOUNDS = ROOT / "assets" / "sounds" / "kailh_box_white"


def _env(n, attack, decay):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(attack, 1e-4)) * np.exp(-t / decay)


def _lowpass(x, taps):
    k = np.hanning(taps + 2)[1:-1]          # drop the zero end points, so small taps still work
    return np.convolve(x, k / k.sum(), mode="same")


def _fir(cut, taps=129):
    """Windowed-sinc low-pass at `cut` Hz."""
    m = np.arange(taps) - (taps - 1) / 2
    h = np.sinc(2 * cut / SR * m) * np.hamming(taps)
    return h / h.sum()


def _put(buf, sig, t):
    i = int(t * SR)
    if 0 <= i < len(buf):
        s = sig[: len(buf) - i]
        buf[i:i + len(s)] += s


def _ring(k, freq, decay, phase=0.0):
    """A damped resonance: what a keycap, plate or case does when it is hit."""
    return np.sin(2 * np.pi * freq * k + phase) * np.exp(-k / decay)


def _read_wav(path):
    with wave.open(str(path)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(float) / 32768
        x = x.reshape(-1, w.getnchannels()).mean(axis=1)
        if w.getframerate() != SR:
            x = np.interp(np.arange(0, len(x), w.getframerate() / SR), np.arange(len(x)), x)
    return x


def _samples():
    downs = [_read_wav(p) for p in sorted(SOUNDS.glob("down*.wav"))]
    ups = [_read_wav(p) for p in sorted(SOUNDS.glob("up*.wav"))]
    if not downs or not ups:
        raise RuntimeError(f"brak nagrań klawiszy w {SOUNDS}")
    soften = _fir(9500, 31)                 # the raw clicks are very bright; take the sting off
    return [np.convolve(d, soften, "same") for d in downs], [np.convolve(u, soften, "same") for u in ups]


def key_sound(rng, downs, ups, space=False):
    """One keystroke from real clicky-switch recordings (Kailh Box White): the click
    going down, a soft bottom-out knock under it, and the click coming back up.
    Pitch and level vary a little, so it never sounds like one sample on repeat."""
    ln = int(0.16 * SR)
    out = np.zeros(ln)
    rate = rng.uniform(0.94, 1.06) * (0.88 if space else 1.0)

    def warp(x):
        return np.interp(np.arange(0, len(x) - 1, rate), np.arange(len(x)), x)

    down = warp(downs[rng.integers(len(downs))])
    out[: len(down)] += down * rng.uniform(0.9, 1.15)
    k = np.arange(ln) / SR
    bo = int(rng.uniform(0.008, 0.012) * SR)
    low = rng.uniform(150, 180) if space else rng.uniform(300, 380)
    out[bo:] += (_ring(k[: ln - bo], low, 0.014 if space else 0.007) * (0.10 if space else 0.05)) \
        * np.minimum(1, k[: ln - bo] / 0.0005)
    up = warp(ups[rng.integers(len(ups))])
    j = int(rng.uniform(0.06, 0.09) * SR)
    out[j:j + len(up)] += up[: ln - j] * rng.uniform(0.45, 0.6)
    return out


def _resample(x, sr_in, sr_out):
    """Band-limited resampling (FFT), clean enough for a voice."""
    if sr_in == sr_out:
        return x
    n_out = int(round(len(x) * sr_out / sr_in))
    spec = np.fft.rfft(x)
    out = np.zeros(n_out // 2 + 1, dtype=complex)
    k = min(len(spec), len(out))
    out[:k] = spec[:k]
    return np.fft.irfft(out, n_out) * (n_out / len(x))


def _segments(x, sr, count):
    """Split a voice clip into `count` sentences at its `count - 1` longest pauses."""
    hop = int(0.01 * sr)
    frames = len(x) // hop
    rms = np.sqrt(np.mean(x[: frames * hop].reshape(frames, hop) ** 2, axis=1))
    quiet = rms < max(rms.max() * 0.04, 1e-4)
    pauses, i = [], 0
    while i < frames:
        if quiet[i]:
            j = i
            while j < frames and quiet[j]:
                j += 1
            if i > 0 and j < frames and j - i >= 6:
                pauses.append((j - i, i, j))
            i = j
        else:
            i += 1
    cut = sorted(sorted(pauses, reverse=True)[: max(0, count - 1)], key=lambda p: p[1])
    edges = [0.0] + [c[2] * hop / sr - 0.04 for c in cut] + [len(x) / sr]
    segs = list(zip(edges[:-1], edges[1:]))
    if len(segs) != count or min(b - a for a, b in segs) < 0.3:
        return [(0.0, len(x) / sr)]
    return segs


def load_voices(spec_path):
    """The narrator clips of one Reel (or Nones), at SR, with their sentences."""
    folder = pathlib.Path(spec_path).with_suffix("")
    meta = json.loads(pathlib.Path(spec_path).read_text(encoding="utf-8")).get("meta", {})
    texts = meta.get("reel_voice") or {}
    out = []
    for part in VOICE_PARTS:
        path = folder / f"voice-{part}.wav"
        if not path.exists():
            out.append(None)
            continue
        with wave.open(str(path)) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(float) / 32768
            x = x.reshape(-1, w.getnchannels()).mean(axis=1)
        x = _resample(x, sr, SR)
        rms = np.sqrt(np.mean(x[np.abs(x) > 0.02] ** 2)) if (np.abs(x) > 0.02).any() else 0.1
        x = np.clip(x * (0.16 / max(rms, 1e-4)), -0.98, 0.98)       # same loudness on every screen
        sentences = len([s for s in re.split(r"[.!?]+", texts.get(part, "")) if s.strip()]) or 1
        out.append({"samples": x, "seconds": len(x) / SR, "segments": _segments(x, SR, sentences)})
    return out if any(out) else None


def _fftconv(x, h):
    size = len(x) + len(h) - 1
    nfft = 1 << (size - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(h, nfft), nfft)[: len(x)]


def night_drive(total, rng):
    """Chill night-drive bed with a Japanese touch, 72 BPM half-time: lush detuned
    pads in a long reverb, deep sub bass, a soft bell melody on an A hirajoshi
    scale, a gentle kick and rim, crisp hats with the odd roll, light rain
    ambience. Warm and in the background. Stereo (L, R)."""
    n = int((total + 1.0) * SR)
    beat = 60 / 72
    bar = 4 * beat
    chords = [([57, 60, 64, 67, 71], 45), ([53, 57, 60, 64, 67], 41), ([55, 59, 62, 66], 43), ([52, 55, 59, 62], 40)]
    scale = [69, 71, 72, 76, 77, 81, 83, 84, 88]      # A B C E F (hirajoshi on A)

    def hz(m):
        return 440 * 2 ** ((m - 69) / 12)

    pad_l, pad_r, sub, bell, drums = (np.zeros(n) for _ in range(5))
    lk = int(0.35 * SR)
    kk = np.arange(lk) / SR
    kick = np.sin(2 * np.pi * np.cumsum(42 + 60 * np.exp(-kk / 0.04)) / SR) * np.exp(-kk / 0.2)
    lr = int(0.14 * SR)
    kr = np.arange(lr) / SR
    rim = (np.sin(2 * np.pi * 1550 * kr) * np.exp(-kr / 0.01) * 0.45
           + _lowpass(rng.standard_normal(lr), 5) * np.exp(-kr / 0.04) * 0.55)
    lh = int(0.035 * SR)
    hat = np.diff(rng.standard_normal(lh), prepend=0) * _env(lh, 0.0004, 0.008)

    def pad_voice(m, length, detune):
        ln = int(length * SR)
        k = np.arange(ln) / SR
        f = hz(m + detune)
        saw = sum(np.sin(2 * np.pi * h * f * k) / h for h in range(1, 7))
        return saw * np.minimum(1, k / 0.9) * np.minimum(1, (length - k) / 0.6)

    def bell_note(m):
        ln = int(1.8 * SR)
        k = np.arange(ln) / SR
        f = hz(m)
        tone = (np.sin(2 * np.pi * f * k) + 0.45 * np.sin(2 * np.pi * 2.76 * f * k) * np.exp(-k / 0.25)
                + 0.2 * np.sin(2 * np.pi * 5.4 * f * k) * np.exp(-k / 0.08))
        return tone * _env(ln, 0.003, 0.7)

    melody = [(0.0, 4), (1.5, 2), (2.0, 3), (3.0, 1), (5.0, 2), (6.0, 4), (6.5, 5), (7.5, 3)]  # (beat, degree)
    t_bar, b = 0.0, 0
    while t_bar < total + 0.5:
        notes, root = chords[b % 4]
        for v, m in enumerate(notes):
            for det, dst, g in ((-0.07, pad_l, 1.0), (0.07, pad_r, 1.0), (0.0, pad_l, 0.5), (0.0, pad_r, 0.5)):
                _put(dst, pad_voice(m, bar + 0.7, det) * g / len(notes), t_bar)
        ln = int(bar * SR)
        k = np.arange(ln) / SR
        glide = hz(root - 12) * (1 + 0.03 * np.exp(-k / 0.05))
        _put(sub, np.sin(2 * np.pi * np.cumsum(glide) / SR) * _env(ln, 0.01, 2.5), t_bar)
        if b % 2 == 0:
            for at, deg in melody:
                _put(bell, bell_note(scale[deg]), t_bar + at * beat)
        _put(drums, kick, t_bar)
        _put(drums, kick * 0.7, t_bar + 2.5 * beat)
        _put(drums, rim * 0.55, t_bar + 2 * beat)
        for e in range(8):
            _put(drums, hat * (0.13 if e % 2 else 0.08), t_bar + e * beat / 2)
        if b % 2 == 1:                                     # a small hat roll at the end of every other bar
            for r in range(4):
                _put(drums, hat * 0.07, t_bar + 3.5 * beat + r * beat / 8)
        t_bar += bar
        b += 1
    pad_l = np.convolve(pad_l, _fir(1800), "same")
    pad_r = np.convolve(pad_r, _fir(1800), "same")
    sub = np.convolve(sub, _fir(300), "same")
    drums = np.convolve(drums, _fir(7000), "same")
    # long, soft reverb on pads and bell: decaying noise impulse, different per side
    ir_len = int(2.4 * SR)
    decay = np.exp(-np.arange(ir_len) / SR / 0.9)
    irs = [np.convolve(rng.standard_normal(ir_len) * decay, _fir(5000, 63), "same") for _ in range(2)]
    irs = [ir / np.sqrt((ir ** 2).sum()) for ir in irs]
    bell_dry = np.convolve(bell, _fir(6000), "same")
    wet_l = _fftconv(pad_l * 0.6 + bell_dry, irs[0])
    wet_r = _fftconv(pad_r * 0.6 + bell_dry, irs[1])
    rain = np.convolve(rng.standard_normal(n), _fir(2500, 63), "same") * 0.012
    core = sub * 0.55 + drums * 0.42 + rain
    left = core + pad_l * 0.22 + bell_dry * 0.12 + wet_l * 0.10
    right = core + pad_r * 0.22 + bell_dry * 0.12 + wet_r * 0.10
    return left, right


def sound(events, total, seed=7, voices=None):
    rng = np.random.default_rng(seed)
    n = int((total + 0.5) * SR)
    left, right = np.zeros(n), np.zeros(n)
    voice = np.zeros(n)

    def add(sig, t, pan=0.0):
        _put(left, sig * (1 - pan), t)
        _put(right, sig * (1 + pan), t)

    downs, ups = _samples()
    # The text types faster than a person could, so a sound per character would be
    # a buzz: keystrokes play at a real typist's rhythm (about 9-13 a second)
    # for as long as text is being typed.
    last_key, gap = -1.0, rng.uniform(0.075, 0.11)
    for t, kind in events:
        if kind in ("key", "space"):
            if t - last_key < gap:
                continue
            last_key, gap = t, rng.uniform(0.075, 0.11)
            add(key_sound(rng, downs, ups, kind == "space") * 1.6, t + rng.uniform(-0.006, 0.006),
                rng.uniform(-0.25, 0.25))
        elif kind == "whoosh":
            ln = int(0.45 * SR)
            add(_lowpass(rng.standard_normal(ln), 24) * np.sin(np.linspace(0, np.pi, ln)) ** 2 * 0.22, t - 0.1)
        elif kind == "ping":
            ln = int(1.4 * SR)
            k = np.arange(ln) / SR
            f0 = 440 * 2 ** ((88 - 69) / 12)                 # E6
            ding = (np.sin(2 * np.pi * f0 * k) + 0.4 * np.sin(2 * np.pi * 2 * f0 * k) * np.exp(-k / 0.1)
                    + 0.2 * np.sin(2 * np.pi * 3.01 * f0 * k) * np.exp(-k / 0.06)) * _env(ln, 0.002, 0.4)
            add(ding * 0.3, t, 0.0)
            add(ding * 0.13, t + 0.2, -0.6)
            add(ding * 0.06, t + 0.4, 0.6)
        elif kind.startswith("voice:") and voices:
            clip = voices[int(kind.split(":")[1])]
            if clip:
                _put(voice, clip["samples"], t)

    bed_l, bed_r = night_drive(total, rng)
    bed_l, bed_r = bed_l[:n], bed_r[:n]
    fade = np.ones(n)
    fi, fo, end = int(0.4 * SR), int(1.6 * SR), min(n, int(total * SR))
    fade[:fi] = np.linspace(0, 1, fi)
    fade[end - fo:end] = np.linspace(1, 0, fo)
    fade[end:] = 0
    music = 0.55
    mix = np.stack([(left + bed_l * music) * fade, (right + bed_r * music) * fade], axis=1)
    if not np.isfinite(mix).all() or not np.isfinite(voice).all():
        raise RuntimeError("dźwięk rolki zawiera błędne próbki, nie publikuję cichej rolki")
    mix *= 0.89 / max(np.abs(mix).max(), 1e-6)
    if np.abs(voice).max() > 0:
        # duck music and keys while the narrator talks: fast down, slow back up
        hop = int(0.01 * SR)
        frames = n // hop
        talk = (np.sqrt(np.mean(voice[: frames * hop].reshape(frames, hop) ** 2, axis=1)) > 0.01).astype(float)
        talk = np.convolve(talk, np.ones(25), "same") > 0             # bridge the gaps between words
        env, g = np.zeros(frames), 0.0
        for i in range(frames):
            g = g + (talk[i] - g) * (0.35 if talk[i] > g else 0.06)
            env[i] = g
        duck = 1 - 0.68 * np.repeat(env, hop)
        duck = np.concatenate([duck, np.full(n - len(duck), duck[-1] if len(duck) else 1.0)])
        mix *= (0.5 * duck)[:, None]
        mix += np.stack([voice, voice], axis=1)
        mix = np.tanh(mix * 1.1) / np.tanh(1.1)                     # soft limiter
        mix *= 0.93 / max(np.abs(mix).max(), 1e-6)
    return mix[: int(total * SR)]


def write_wav(path, stereo):
    data = (np.clip(stereo, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


# ---------------------------------------------------------------- build

def ffmpeg_bin():
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        sys.exit("brak ffmpeg: zainstaluj ffmpeg albo pip install imageio-ffmpeg")


def prepare(spec_path):
    spec = json.loads(pathlib.Path(spec_path).read_text(encoding="utf-8"))
    screens = screens_for(spec)
    voices = load_voices(spec_path)
    plan, events, total = timeline(screens, voices)
    handle = spec.get("handle", "pagehub.pl")
    g0, g1 = glow_layers()
    windows = [window_layer(s["url"], handle) for s in screens]
    return plan, events, total, (g0, g1, windows, voices)


def build(spec_path, out_path=None):
    out_path = pathlib.Path(out_path or pathlib.Path(spec_path).with_suffix("") / "reel.mp4")
    plan, events, total, assets = prepare(spec_path)
    with tempfile.TemporaryDirectory() as tmp:
        wav = pathlib.Path(tmp) / "audio.wav"
        write_wav(wav, sound(events, total, voices=assets[3]))
        cmd = [ffmpeg_bin(), "-y", "-loglevel", "error",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
               "-i", str(wav),
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "160k", "-ar", str(SR), "-shortest",
               "-movflags", "+faststart", str(out_path)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for f in range(int(total * FPS)):
            proc.stdin.write(frame_at(plan, assets, f / FPS).tobytes())
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg nie zbudował rolki")
    return out_path, total


def main():
    ap = argparse.ArgumentParser(description="Carousel spec -> typing Reel MP4.")
    ap.add_argument("spec")
    ap.add_argument("--out")
    ap.add_argument("--still", type=float, help="write one frame at this second as PNG instead")
    a = ap.parse_args()
    if a.still is not None:
        plan, _, total, assets = prepare(a.spec)
        out = pathlib.Path(a.out or "still.png")
        frame_at(plan, assets, min(a.still, total - 0.01)).save(out)
        print(f"{out}  (z {total:.1f} s)")
        return
    path, total = build(a.spec, a.out)
    print(f"{path}  ({total:.1f} s, {path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
