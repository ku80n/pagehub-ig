#!/usr/bin/env python3
"""
make_reel.py - turn a carousel spec into a short 9:16 Reel: the carousel's text
typed out as syntax-highlighted code in an IDE window, with original sound.

Two screens, both starting from an empty editor:
  1. the cover - kicker as a comment, the title and subtitle as strings,
     typed out and left on screen long enough to read all of it;
  2. the headings of the other slides as a list of strings, then
     "// reszta w opisie", and a single "ping" when the last line is done.
The recap and call-to-action slides are left out of the list: they are not
points. The window sits inside the Reels safe zone, away from the
like/comment rail and the caption.

Sound: real clicky-switch recordings (Kailh Box White, MIT licence, see
assets/sounds) at a real typist's rhythm, a soft whoosh between the screens,
one ping at the end, and a relaxed Japanese lo-fi bed generated here (electric
piano, koto-like plucks on a hirajoshi scale, soft swung drums, vinyl crackle),
so there is nothing to license and nothing Instagram can mute.

Usage
  python3 make_reel.py weeks/2026-11-02/k1.json                # -> weeks/.../k1/reel.mp4
  python3 make_reel.py weeks/2026-11-02/k1.json --out x.mp4
  python3 make_reel.py weeks/2026-11-02/k1.json --still 3.0    # one frame as PNG, for checking
"""

import argparse
import bisect
import json
import pathlib
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

# IDE dark theme
BG = (11, 15, 20)
TITLE_BG = (50, 50, 51)
TAB_BG = (37, 37, 38)
TAB_IDLE = (45, 45, 45)
EDITOR = (30, 30, 30)
ACTIVITY = (44, 44, 44)
CUR_LINE = (40, 40, 40)
BORDER = (60, 60, 60)
GUTTER = (110, 118, 129)
GUTTER_CUR = (198, 198, 198)
ICON = (133, 133, 133)
TEXT = (212, 212, 212)
MUTED = (150, 150, 150)
CURSOR = (174, 175, 173)
ACCENT = (28, 152, 195)          # PageHub teal, used for the status bar
# syntax colours
KW = (86, 156, 214)              # const
VAR = (156, 220, 254)            # names
PUNC = (212, 212, 212)           # = ; [ ] ,
STR = (206, 145, 120)            # "strings"
COM = (106, 153, 85)             # // comments
TS_BLUE = (49, 120, 198)

# window inside the Reels safe zone (top bar above y=230, caption below y=1440,
# action rail on the right)
WX, WY, WW, WH = 40, 280, 860, 1150
TITLE_H, TAB_H, STATUS_H, ACT_W = 52, 64, 46, 66
ED_X0, ED_Y0 = WX + ACT_W, WY + TITLE_H + TAB_H
ED_Y1 = WY + WH - STATUS_H
GUT_R = ED_X0 + 64               # right edge of the line numbers
CODE_X = ED_X0 + 92
CODE_W = WX + WW - 28 - CODE_X
TOP_PAD = 34

FONT_SIZE = 40
LINE_H = int(FONT_SIZE * 1.55)
CPS = (30, 40)                   # typing speed on the cover / on the list screen
ENTER_PAUSE = 0.16
HOLD_COVER, HOLD_LAST, CLEAR = 2.2, 2.4, 0.3
OUTRO = "// reszta w opisie ↓"


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


MONO = font("DejaVuSansMono.ttf", FONT_SIZE)
MONO_B = font("DejaVuSansMono-Bold.ttf", FONT_SIZE)
UI = font("Inter-Regular.otf", 24)
UI_S = font("Inter-SemiBold.otf", 24)
UI_SMALL = font("DejaVuSansMono-Bold.ttf", 17)
CHAR_W = MONO.getlength("M")
COLS = int(CODE_W // CHAR_W)


# ---------------------------------------------------------------- code

def plain(text):
    return " ".join(text.replace("*", "").replace('"', "'").split())


def tok(text, color):
    return [(ch, color) for ch in text]


def code_screens(slides):
    """Two screens of code lines. A line is a list of (char, colour)."""
    cover = slides[0]
    lines = []
    if cover.get("kicker"):
        lines.append(tok("// " + plain(cover["kicker"]), COM))
    lines.append(tok("const ", KW) + tok("temat", VAR) + tok(" = ", PUNC))
    lines.append(tok("  ", PUNC) + tok('"' + plain(cover.get("title", "")) + '"', STR) + tok(";", PUNC))
    if cover.get("subtitle"):
        lines.append(tok("const ", KW) + tok("opis", VAR) + tok(" = ", PUNC))
        lines.append(tok("  ", PUNC) + tok('"' + plain(cover["subtitle"]) + '"', STR) + tok(";", PUNC))
    heads = [s["title"] for s in slides[1:] if s.get("title") and s.get("type", "text") not in ("list", "cta")]
    lst = [tok("const ", KW) + tok("punkty", VAR) + tok(" = [", PUNC)]
    for i, h in enumerate(heads):
        lst.append(tok("  ", PUNC) + tok('"' + plain(h) + '"', STR) + tok("," if i < len(heads) - 1 else "", PUNC))
    lst.append(tok("];", PUNC))
    lst.append(tok(OUTRO, COM))
    return [{"file": "temat.ts", "lines": lines, "cps": CPS[0]},
            {"file": "punkty.ts", "lines": lst, "cps": CPS[1]}]


def wrap_line(line):
    """Soft-wrap a code line at spaces. Continuation rows are indented to sit
    inside the string, the way an IDE's soft wrap does. Returns rows of
    (indent, [(char, colour), ...])."""
    rows, start = [], 0
    text = "".join(c for c, _ in line)
    lead = len(text) - len(text.lstrip(" "))
    indent_next = lead + (1 if text.lstrip().startswith('"') else 0)
    while start < len(line):
        width = COLS - (0 if not rows else indent_next)
        if len(line) - start <= width:
            rows.append((0 if not rows else indent_next, line[start:]))
            break
        cut = text.rfind(" ", start, start + width + 1)
        if cut <= start:
            cut = start + width
        rows.append((0 if not rows else indent_next, line[start:cut + 1]))
        start = cut + 1
    return rows or [(0, [])]


# ---------------------------------------------------------------- timeline

def timeline(screens):
    """Lay every screen out in rows and give every character the time it is typed."""
    plan, events, t = [], [], 0.0
    for si, sc in enumerate(screens):
        first, last = si == 0, si == len(screens) - 1
        start = t
        t += 0.45                                   # a beat of empty editor before typing
        rows = []
        for li, line in enumerate(sc["lines"]):
            for ri, (indent, chars) in enumerate(wrap_line(line)):
                times = []
                for ch, _ in chars:
                    times.append(t)
                    events.append((t, "space" if ch == " " else "key"))
                    t += 1 / sc["cps"]
                rows.append({"line": li, "first": ri == 0, "indent": indent, "chars": chars, "times": times})
            events.append((t, "space"))             # Enter
            t += ENTER_PAUSE
        end_typing = t
        if last:
            events.append((t, "ping"))
            t += HOLD_LAST
        else:
            t += HOLD_COVER
        plan.append({"file": sc["file"], "rows": rows, "start": start, "typed": end_typing, "end": t})
        if not last:
            events.append((t, "whoosh"))
            t += CLEAR
    return plan, events, t


# ---------------------------------------------------------------- drawing

def background():
    bg = Image.new("RGB", (W, H), BG)
    glow = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(glow)
    d.ellipse((560, -260, 1460, 640), fill=(18, 58, 74))
    d.ellipse((-420, 1380, 520, 2260), fill=(15, 42, 54))
    return Image.blend(bg, glow.filter(ImageFilter.GaussianBlur(160)), 0.9)


def _icon(d, kind, cx, cy, color):
    if kind == "files":
        d.rectangle((cx - 11, cy - 14, cx + 7, cy + 12), outline=color, width=3)
        d.rectangle((cx - 5, cy - 18, cx + 13, cy + 6), outline=color, width=3)
    elif kind == "search":
        d.ellipse((cx - 13, cy - 13, cx + 5, cy + 5), outline=color, width=3)
        d.line((cx + 3, cy + 3, cx + 13, cy + 13), fill=color, width=4)
    elif kind == "branch":
        for x, y in ((cx - 8, cy - 12), (cx - 8, cy + 12), (cx + 9, cy - 4)):
            d.ellipse((x - 5, y - 5, x + 5, y + 5), outline=color, width=3)
        d.line((cx - 8, cy - 7, cx - 8, cy + 7), fill=color, width=3)
        d.line((cx + 9, cy + 1, cx - 6, cy + 9), fill=color, width=3)
    elif kind == "blocks":
        for x, y in ((cx - 12, cy - 2), (cx + 2, cy - 2), (cx - 12, cy - 16)):
            d.rectangle((x, y, x + 11, y + 11), outline=color, width=3)
        d.rectangle((cx + 4, cy - 18, cx + 15, cy - 7), outline=color, width=3)


def chrome(base, file):
    """IDE window: title bar, activity bar, tabs, empty editor and status bar."""
    img = base.copy()
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((WX, WY, WX + WW, WY + WH), 18, fill=EDITOR, outline=BORDER, width=2)
    d.rounded_rectangle((WX + 1, WY + 1, WX + WW - 1, WY + TITLE_H), 17, fill=TITLE_BG)
    d.rectangle((WX + 1, WY + TITLE_H - 18, WX + WW - 1, WY + TITLE_H), fill=TITLE_BG)
    for k, c in enumerate(((255, 95, 87), (254, 188, 46), (40, 200, 64))):
        cx = WX + 30 + k * 26
        d.ellipse((cx - 8, WY + TITLE_H // 2 - 8, cx + 8, WY + TITLE_H // 2 + 8), fill=c)
    d.text((WX + WW / 2, WY + TITLE_H / 2), "pagehub.pl", font=UI, fill=MUTED, anchor="mm")
    # activity bar
    d.rectangle((WX + 1, WY + TITLE_H, ED_X0, ED_Y1), fill=ACTIVITY)
    for k, kind in enumerate(("files", "search", "branch", "blocks")):
        cy = WY + TITLE_H + 50 + k * 72
        _icon(d, kind, WX + ACT_W // 2, cy, TEXT if k == 0 else ICON)
    d.rectangle((WX + 1, WY + TITLE_H + 26, WX + 4, WY + TITLE_H + 74), fill=TEXT)
    # tabs
    d.rectangle((ED_X0, WY + TITLE_H, WX + WW - 1, ED_Y0), fill=TAB_BG)
    tw = 230
    d.rectangle((ED_X0, WY + TITLE_H, ED_X0 + tw, ED_Y0), fill=EDITOR)
    d.line((ED_X0, WY + TITLE_H, ED_X0 + tw, WY + TITLE_H), fill=ACCENT, width=3)
    d.text((ED_X0 + 22, WY + TITLE_H + TAB_H / 2), "TS", font=UI_SMALL, fill=TS_BLUE, anchor="lm")
    d.text((ED_X0 + 56, WY + TITLE_H + TAB_H / 2), file, font=UI, fill=TEXT, anchor="lm")
    d.rectangle((ED_X0 + tw, WY + TITLE_H, ED_X0 + tw + 210, ED_Y0 - 1), fill=TAB_IDLE)
    d.text((ED_X0 + tw + 22, WY + TITLE_H + TAB_H / 2), "README.md", font=UI, fill=ICON, anchor="lm")
    d.line((ED_X0, ED_Y0, WX + WW, ED_Y0), fill=BORDER, width=1)
    # status bar
    d.rounded_rectangle((WX + 1, ED_Y1, WX + WW - 1, WY + WH - 1), 17, fill=ACCENT)
    d.rectangle((WX + 1, ED_Y1, WX + WW - 1, ED_Y1 + 18), fill=ACCENT)
    d.text((WX + 24, ED_Y1 + STATUS_H / 2), "main", font=UI_S, fill=(255, 255, 255), anchor="lm")
    d.text((WX + WW - 24, ED_Y1 + STATUS_H / 2), "UTF-8   TypeScript", font=UI, fill=(235, 245, 250),
           anchor="rm")
    return img


def draw_code(img, screen, t, alpha=1.0, cursor_on=True):
    d = ImageDraw.Draw(img, "RGBA")
    a = int(255 * alpha)
    rows = screen["rows"]
    visible = []                                    # (row, chars shown so far)
    for r in rows:
        n = bisect.bisect_right(r["times"], t)
        if n == 0:
            break
        visible.append((r, n))
    # the line being typed gets the current-line highlight, the IDE way
    cur_line = visible[-1][0]["line"] if visible else 0
    cur_rows = [i for i, (r, _) in enumerate(visible) if r["line"] == cur_line] or [0]
    y0 = ED_Y0 + TOP_PAD
    if alpha > 0.5:
        d.rectangle((ED_X0 + 1, y0 + cur_rows[0] * LINE_H - 8, WX + WW - 2, y0 + (cur_rows[-1] + 1) * LINE_H - 8),
                    fill=CUR_LINE + (a,))
    for i, (r, n) in enumerate(visible):
        y = y0 + i * LINE_H
        if r["first"]:
            num = r["line"] + 1
            d.text((GUT_R, y), str(num), font=MONO, fill=(GUTTER_CUR if r["line"] == cur_line else GUTTER) + (a,),
                   anchor="ra")
        x = CODE_X + r["indent"] * CHAR_W
        run, run_color = "", None
        for ch, color in r["chars"][:n]:
            if color != run_color and run:
                d.text((x, y), run, font=MONO, fill=run_color + (a,))
                x += MONO.getlength(run)
                run = ""
            run_color = color
            run += ch
        if run:
            d.text((x, y), run, font=MONO, fill=run_color + (a,))
            x += MONO.getlength(run)
        if i == len(visible) - 1 and cursor_on and alpha > 0.5:
            d.rectangle((x + 1, y - 2, x + 4, y + FONT_SIZE + 4), fill=CURSOR + (a,))
    if not visible and cursor_on:
        d.text((GUT_R, y0), "1", font=MONO, fill=GUTTER_CUR + (a,), anchor="ra")
        d.rectangle((CODE_X + 1, y0 - 2, CODE_X + 4, y0 + FONT_SIZE + 4), fill=CURSOR + (a,))
    # live cursor position in the status bar
    if visible:
        r, n = visible[-1]
        col = r["indent"] + n + 1
    else:
        col = 1
    d.text((WX + WW - 290, ED_Y1 + STATUS_H / 2), f"Ln {cur_line + 1}, Col {col}", font=UI,
           fill=(235, 245, 250, 255), anchor="rm")


def frame_at(plan, chromes, t):
    for i, s in enumerate(plan):
        if t < s["end"] or i == len(plan) - 1:
            img = chromes[i].copy()
            typing = s["start"] + 0.45 <= t < s["typed"]
            draw_code(img, s, t, 1.0, typing or int(t * 1.8) % 2 == 0)
            return img
        if t < s["end"] + CLEAR:
            img = chromes[i].copy()
            draw_code(img, s, s["end"], 1 - (t - s["end"]) / CLEAR, False)
            return img
    return chromes[-1].copy()


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


def japan_lofi(total, rng):
    """Relaxed Japanese lo-fi in the JDM-night-drive mood, 76 BPM, swung:
    a warm FM electric piano on Dm9 - G13 - Cmaj9 - Am9, round sub bass,
    koto-like plucks on an A hirajoshi scale with an echo, soft kick, rim and
    hats, a little vinyl crackle, everything warm and rolled off. Stereo (L, R)."""
    n = int((total + 1.0) * SR)
    beat = 60 / 76
    bar = 4 * beat
    swing = 0.12 * beat
    chords = [([53, 57, 60, 64], 38), ([53, 59, 64, 69], 43), ([52, 55, 59, 62], 36), ([55, 59, 60, 64], 45)]
    scale = [69, 71, 72, 76, 77, 81, 83, 84]          # A B C E F (hirajoshi on A), two octaves

    def hz(m):
        return 440 * 2 ** ((m - 69) / 12)

    ep_l, ep_r, bass, pluck, drums = (np.zeros(n) for _ in range(5))
    lk = int(0.25 * SR)
    kk = np.arange(lk) / SR
    kick = np.sin(2 * np.pi * np.cumsum(46 + 50 * np.exp(-kk / 0.03)) / SR) * np.exp(-kk / 0.14)
    lr = int(0.12 * SR)
    kr = np.arange(lr) / SR
    rim = (np.sin(2 * np.pi * 1700 * kr) * np.exp(-kr / 0.012) * 0.5
           + _lowpass(rng.standard_normal(lr), 6) * np.exp(-kr / 0.03) * 0.5)
    lh = int(0.04 * SR)
    hat = np.diff(rng.standard_normal(lh), prepend=0) * _env(lh, 0.0005, 0.01)

    def ep_note(m, length):
        ln = int(length * SR)
        k = np.arange(ln) / SR
        f = hz(m)
        index = 1.8 * np.exp(-k / 0.35)
        tone = np.sin(2 * np.pi * f * k + index * np.sin(2 * np.pi * f * k))
        tone += 0.15 * np.sin(2 * np.pi * 4 * f * k) * np.exp(-k / 0.05)      # tine bell
        return tone * _env(ln, 0.004, 2.2) * (1 + 0.12 * np.sin(2 * np.pi * 4.2 * k))

    def koto(m):
        ln = int(1.4 * SR)
        k = np.arange(ln) / SR
        f = hz(m)
        sig = sum(np.sin(2 * np.pi * h * f * (1 + 0.0004 * h * h) * k) * np.exp(-k / (0.9 / h)) / h ** 1.1
                  for h in range(1, 9))
        sig[: int(0.003 * SR)] += rng.standard_normal(int(0.003 * SR)) * 0.4
        return sig * np.minimum(1, k / 0.001) * 0.6

    t_bar, b = 0.0, 0
    motif = [0, None, 2, 4, None, 3, 2, None, 1, None, 0, None, None, 2, None, None]
    while t_bar < total + 0.5:
        notes, root = chords[b % 4]
        for at, length in ((0.0, 1.6 * beat), (2.5 * beat + swing, 1.3 * beat)):   # syncopated EP stabs
            for v, m in enumerate(notes):
                s = ep_note(m, length + 0.8) / len(notes)
                _put(ep_l, s * (1.0 if v % 2 else 0.7), t_bar + at + v * 0.012)
                _put(ep_r, s * (0.7 if v % 2 else 1.0), t_bar + at + v * 0.012)
        for at, m, ln_ in ((0, root, 1.4), (1.5 * beat + swing, root + 12, 0.4), (3 * beat, root + 7, 0.7)):
            ln = int(ln_ * beat * SR)
            k = np.arange(ln) / SR
            sig = np.tanh(1.6 * np.sin(2 * np.pi * hz(m) * k)) * _env(ln, 0.006, 0.9 * beat)
            _put(bass, sig, t_bar + at)
        shift = (b % 2) * 2
        for e, deg in enumerate(motif):                                         # koto line, 8ths
            if deg is None or (b % 4 == 3 and e > 8):
                continue
            at = t_bar + e * beat / 2 + (swing if e % 2 else 0)
            _put(pluck, koto(scale[(deg + shift) % len(scale)]), at)
        for q in range(4):
            tq = t_bar + q * beat
            if q in (0, 2):
                _put(drums, kick, tq)
            if q == 2 and b % 2:
                _put(drums, kick * 0.6, tq + 1.5 * beat / 2 + swing)
            if q in (1, 3):
                _put(drums, rim * 0.6, tq)
            _put(drums, hat * 0.10, tq)
            _put(drums, hat * 0.16, tq + beat / 2 + swing)
        t_bar += bar
        b += 1
    warm = _fir(4200)
    ep_l, ep_r = np.convolve(ep_l, warm, "same"), np.convolve(ep_r, warm, "same")
    bass = np.convolve(bass, _fir(500), "same")
    pluck = np.convolve(pluck, _fir(5000), "same")
    drums = np.convolve(drums, _fir(6000), "same")
    d = int(0.75 * beat * SR)                                                   # dotted-eighth echo
    pl, pr = pluck.copy(), pluck.copy()
    for r in range(1, 4):
        (pr if r % 2 else pl)[d * r:] += pluck[: -d * r] * 0.38 ** r
    crackle = np.zeros(n)                                                       # vinyl
    for _ in range(int(total * 7)):
        i = rng.integers(0, n - 200)
        crackle[i:i + 60] += np.diff(rng.standard_normal(60), prepend=0) * rng.uniform(0.02, 0.08) \
            * np.exp(-np.arange(60) / 12)
    hiss = np.convolve(rng.standard_normal(n), _fir(3000, 63), "same") * 0.006
    core = bass * 0.45 + drums * 0.42 + crackle + hiss
    left = core + ep_l * 0.38 + pl * 0.16
    right = core + ep_r * 0.38 + pr * 0.2
    return left, right


def sound(events, total, seed=7):
    rng = np.random.default_rng(seed)
    n = int((total + 0.5) * SR)
    left, right = np.zeros(n), np.zeros(n)

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
            # one soft bell with a short stereo echo, to close the reel
            ln = int(1.4 * SR)
            k = np.arange(ln) / SR
            f0 = 440 * 2 ** ((88 - 69) / 12)                 # E6
            ding = (np.sin(2 * np.pi * f0 * k) + 0.4 * np.sin(2 * np.pi * 2 * f0 * k) * np.exp(-k / 0.1)
                    + 0.2 * np.sin(2 * np.pi * 3.01 * f0 * k) * np.exp(-k / 0.06)) * _env(ln, 0.002, 0.4)
            add(ding * 0.3, t, 0.0)
            add(ding * 0.13, t + 0.2, -0.6)
            add(ding * 0.06, t + 0.4, 0.6)

    bed_l, bed_r = japan_lofi(total, rng)
    bed_l, bed_r = bed_l[:n], bed_r[:n]
    fade = np.ones(n)
    fi, fo, end = int(0.4 * SR), int(1.6 * SR), min(n, int(total * SR))
    fade[:fi] = np.linspace(0, 1, fi)
    fade[end - fo:end] = np.linspace(1, 0, fo)
    fade[end:] = 0
    music = 0.5
    mix = np.stack([(left + bed_l * music) * fade, (right + bed_r * music) * fade], axis=1)
    if not np.isfinite(mix).all():
        raise RuntimeError("dźwięk rolki zawiera błędne próbki, nie publikuję cichej rolki")
    mix *= 0.89 / max(np.abs(mix).max(), 1e-6)
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
    screens = code_screens(spec["slides"])
    plan, events, total = timeline(screens)
    base = background()
    chromes = [chrome(base, s["file"]) for s in screens]
    return plan, events, total, chromes


def build(spec_path, out_path=None):
    out_path = pathlib.Path(out_path or pathlib.Path(spec_path).with_suffix("") / "reel.mp4")
    plan, events, total, chromes = prepare(spec_path)
    with tempfile.TemporaryDirectory() as tmp:
        wav = pathlib.Path(tmp) / "audio.wav"
        write_wav(wav, sound(events, total))
        cmd = [ffmpeg_bin(), "-y", "-loglevel", "error",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
               "-i", str(wav),
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "160k", "-ar", str(SR), "-shortest",
               "-movflags", "+faststart", str(out_path)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for f in range(int(total * FPS)):
            proc.stdin.write(frame_at(plan, chromes, f / FPS).tobytes())
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg nie zbudował rolki")
    return out_path, total


def main():
    ap = argparse.ArgumentParser(description="Carousel spec -> IDE typing Reel MP4.")
    ap.add_argument("spec")
    ap.add_argument("--out")
    ap.add_argument("--still", type=float, help="write one frame at this second as PNG instead")
    a = ap.parse_args()
    if a.still is not None:
        plan, _, total, chromes = prepare(a.spec)
        out = pathlib.Path(a.out or "still.png")
        frame_at(plan, chromes, min(a.still, total - 0.01)).save(out)
        print(f"{out}  (z {total:.1f} s)")
        return
    path, total = build(a.spec, a.out)
    print(f"{path}  ({total:.1f} s, {path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
