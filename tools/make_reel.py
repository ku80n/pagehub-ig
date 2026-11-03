#!/usr/bin/env python3
"""
make_reel.py - turn a carousel spec into a short 9:16 Reel where the text types
itself out in a PageHub-style code editor, with original sound.

Two screens. First the carousel's cover, exactly as it is, on screen from the
very first frame (the hook) and long enough to read all of it. Then a bullet
list of the headings of the other slides, typed one by one, ending with
"reszta w opisie" and a single "ping". The recap and the call-to-action slides
are left out of the list: they are not points.
The window sits inside the Reels safe zone, away from the like/comment rail
and the caption.

Sound: real clicky-switch recordings (Kailh Box White, MIT licence, see
assets/sounds) played at a real typist's rhythm, a soft whoosh between the
screens, one ping at the very end, and a synthwave bed generated here, so there
is nothing to license and nothing Instagram can mute.

Usage
  python3 make_reel.py weeks/2026-11-02/k1.json                # -> weeks/.../k1/reel.mp4
  python3 make_reel.py weeks/2026-11-02/k1.json --out x.mp4
  python3 make_reel.py weeks/2026-11-02/k1.json --still 3.0    # one frame as PNG, for checking
"""

import argparse
import json
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
BG = (11, 15, 20)
WIN = (17, 22, 29)
BAR = (22, 29, 38)
LINE = (36, 48, 64)
FG = (230, 237, 243)
BODY = (201, 211, 222)
MUTED = (107, 120, 136)
GUTTER = (43, 55, 70)
ACCENT = (28, 152, 195)
INK = (11, 15, 20)

# window inside the Reels safe zone (top bar above y=230, caption below y=1440,
# action rail on the right)
WX, WY, WW, WH = 50, 300, 840, 1110
BAR_H = 76
TX = WX + 92                     # text left edge, right of the gutter
TW = WX + WW - 52 - TX           # text width
CONTENT_TOP, CONTENT_BOTTOM = WY + BAR_H + 40, WY + WH - 70

# pacing (characters per second, seconds)
CPS = {"kicker": 60, "title": 34, "subtitle": 70, "body": 78, "item": 70, "bullet": 30, "outro": 26}
BULLET_GAP = 0.18                # short pause between headings
OUTRO = "reszta w opisie \u2193"
HOLD, HOLD_LAST, CLEAR = 0.95, 2.2, 0.25


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


F = {
    "kicker": font("DejaVuSansMono-Bold.ttf", 28),
    "title": font("DejaVuSansMono-Bold.ttf", 62),
    "cover": font("DejaVuSansMono-Bold.ttf", 74),
    "subtitle": font("Inter-Regular.otf", 40),
    "body": font("Inter-Regular.otf", 42),
    "item": font("Inter-Regular.otf", 40),
    "num": font("DejaVuSansMono-Bold.ttf", 28),
    "dot": font("DejaVuSansMono-Bold.ttf", 44),
    "button": font("DejaVuSansMono-Bold.ttf", 36),
    "url": font("DejaVuSansMono.ttf", 26),
    "gutter": font("DejaVuSansMono.ttf", 22),
}


# ---------------------------------------------------------------- text layout

def runs(text, color):
    """'Ile *Twoja* strona' -> [(word, color), ...] with the accent applied."""
    out = []
    for i, part in enumerate(re.split(r"\*([^*]+)\*", text.replace("\n", " "))):
        for w in part.split():
            out.append((w, ACCENT if i % 2 else color))
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


def block(kind, text, color, fnt, indent=0, gap_before=0, lh=1.4, prefix=None):
    lines = wrap(runs(text, color), fnt, TW - indent)
    return {"kind": kind, "lines": lines, "font": fnt, "indent": indent, "gap": gap_before,
            "lh": int(fnt.size * lh), "prefix": prefix,
            "chars": sum(len(w) + 1 for ln in lines for _, w, _ in ln)}


def reel_slides(slides):
    """Cover as it is, then one screen listing the headings of the other slides."""
    heads = [s["title"] for s in slides[1:] if s.get("title") and s.get("type", "text") not in ("list", "cta")]
    return [slides[0], {"type": "bullets", "items": heads, "outro": OUTRO}]


def bullet_blocks(items, outro=None):
    """Biggest font size at which every heading (and the outro line) still fits."""
    for size in (46, 42, 38, 34, 30):
        fnt = font("DejaVuSansMono-Bold.ttf", size)
        blocks = [block("bullet", it, FG, fnt, indent=int(size * 1.1), gap_before=0 if i == 0 else int(size * 0.75),
                        lh=1.22, prefix="\u2022") for i, it in enumerate(items)]
        if outro:
            blocks.append(block("outro", outro, ACCENT, F["kicker"], gap_before=int(size * 1.4), lh=1.3))
        if sum(b["gap"] + b["lh"] * len(b["lines"]) for b in blocks) <= CONTENT_BOTTOM - CONTENT_TOP - 40:
            return blocks
    return blocks


def layout(slide, first):
    kind = slide.get("type", "text")
    blocks = []
    if kind == "bullets":
        blocks = bullet_blocks(slide["items"], slide.get("outro"))
    if slide.get("kicker") and kind != "bullets":
        blocks.append(block("kicker", "// " + slide["kicker"], ACCENT, F["kicker"], lh=1.3))
    if slide.get("title") and kind != "bullets":
        blocks.append(block("title", slide["title"], FG, F["cover" if first else "title"],
                            gap_before=22 if blocks else 0, lh=1.16))
    if kind == "cover" and slide.get("subtitle"):
        blocks.append(block("subtitle", slide["subtitle"], BODY, F["subtitle"], gap_before=40, lh=1.38))
    if kind in ("text", "cta") and slide.get("body"):
        for i, para in enumerate(p for p in slide["body"].split("\n\n") if p.strip()):
            blocks.append(block("body", para, BODY, F["body"], gap_before=40 if i == 0 else 26, lh=1.42))
    if kind == "list":
        for i, item in enumerate(slide.get("items", []), 1):
            blocks.append(block("item", item, BODY, F["item"], indent=62, gap_before=40 if i == 1 else 22,
                                lh=1.36, prefix=f"{i:02d}"))
    if kind == "cta" and slide.get("button"):
        blocks.append({"kind": "button", "text": slide["button"], "gap": 48, "chars": 0, "lines": [],
                       "lh": 92, "font": F["button"], "indent": 0, "prefix": None})
    # vertical centring inside the window
    height = sum(b["gap"] + (b["lh"] if b["kind"] == "button" else b["lh"] * len(b["lines"])) for b in blocks)
    y = CONTENT_TOP + max(0, (CONTENT_BOTTOM - CONTENT_TOP - height) // 2) - 20
    for b in blocks:
        y += b["gap"]
        b["y"] = y
        y += b["lh"] if b["kind"] == "button" else b["lh"] * len(b["lines"])
    return blocks


# ---------------------------------------------------------------- timeline

def timeline(slides):
    """Per slide: when each block types, how long it all takes, and the sound events."""
    plan, events, t = [], [], 0.0
    for i, slide in enumerate(slides):
        first, last = i == 0, i == len(slides) - 1
        blocks = layout(slide, first)
        start = t
        for b in blocks:
            if b["kind"] == "button":
                b["t0"] = b["t1"] = t + 0.15
                events.append((t + 0.15, "pop"))
                t += 0.35
                continue
            instant = first and b["kind"] in ("kicker", "title")
            dur = 0.0 if instant else b["chars"] / CPS[b["kind"]]
            b["t0"], b["t1"] = t, t + dur
            if not instant:
                text = " ".join(w for ln in b["lines"] for _, w, _ in ln) + " "
                for k, ch in enumerate(text):
                    events.append((t + k / CPS[b["kind"]], "space" if ch == " " else "key"))
                t += dur + (BULLET_GAP if b["kind"] == "bullet" else 0.12)
        if last:
            events.append((t, "ping"))                    # one ping, when the last line is done
            t += HOLD_LAST
        elif first:
            # the cover is the hook: keep it up long enough to read every word of it
            words = sum(len(ln) for b in blocks for ln in b["lines"])
            t = max(t + 1.0, start + 1.2 + 0.3 * words)
        else:
            t += HOLD
        plan.append({"blocks": blocks, "start": start, "end": t})
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


def chrome(base, idx, total, handle):
    """Window, title bar, gutter and progress bar for slide idx (0-based)."""
    img = base.copy()
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((WX, WY, WX + WW, WY + WH), 26, fill=WIN, outline=LINE, width=2)
    d.rounded_rectangle((WX + 2, WY + 2, WX + WW - 2, WY + BAR_H), 24, fill=BAR)
    d.rectangle((WX + 2, WY + BAR_H - 26, WX + WW - 2, WY + BAR_H), fill=BAR)
    d.line((WX, WY + BAR_H, WX + WW, WY + BAR_H), fill=LINE, width=2)
    for k, c in enumerate((ACCENT, GUTTER, GUTTER)):
        cx = WX + 34 + k * 30
        d.ellipse((cx - 8, WY + BAR_H // 2 - 8, cx + 8, WY + BAR_H // 2 + 8), fill=c)
    path = "" if idx == 0 else f"/{idx + 1:02d}"
    px = WX + 140
    d.rounded_rectangle((px, WY + 17, WX + WW - 110, WY + BAR_H - 17), 21, fill=(14, 19, 26), outline=LINE)
    d.text((px + 22, WY + BAR_H // 2), handle, font=F["url"], fill=FG, anchor="lm")
    d.text((px + 22 + F["url"].getlength(handle), WY + BAR_H // 2), path, font=F["url"], fill=MUTED, anchor="lm")
    d.text((WX + WW - 34, WY + BAR_H // 2), f"{idx + 1}/{total}", font=F["num"], fill=ACCENT, anchor="rm")
    y, n = CONTENT_TOP - 10, 1
    while y < WY + WH - 80:
        d.text((WX + 58, y), str(n), font=F["gutter"], fill=GUTTER, anchor="rt")
        y, n = y + 40, n + 1
    d.text((TX, WY + WH - 44), "@" + handle, font=F["url"], fill=MUTED, anchor="lm")
    by = WY - 46
    d.rounded_rectangle((WX, by, WX + WW, by + 8), 4, fill=LINE)
    d.rounded_rectangle((WX, by, WX + int(WW * (idx + 1) / total), by + 8), 4, fill=ACCENT)
    return img


def draw_content(img, blocks, t, alpha=1.0, cursor_on=True):
    """Draw every block as typed by time t, in place."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a = int(255 * alpha)
    cursor = None
    for b in blocks:
        if t < b["t0"]:
            break
        if b["kind"] == "button":
            fnt, label = b["font"], b["text"]
            grow = min(1.0, (t - b["t0"]) / 0.18)
            w = fnt.getlength(label) + 76
            pad = (1 - grow) * 10
            d.rounded_rectangle((TX + pad, b["y"] + pad, TX + w - pad, b["y"] + 80 - pad), 18, fill=ACCENT + (a,))
            if grow > 0.6:
                d.text((TX + w / 2, b["y"] + 40), label, font=fnt, fill=INK + (a,), anchor="mm")
            cursor = None
            continue
        span = max(b["t1"] - b["t0"], 1e-6)
        shown = b["chars"] if t >= b["t1"] else int(b["chars"] * (t - b["t0"]) / span)
        fnt, left = b["font"], TX + b["indent"]
        if b["prefix"] == "\u2022":
            if shown > 0:
                d.text((TX, b["y"]), "\u2022", font=fnt, fill=ACCENT + (a,))
        elif b["prefix"]:
            d.text((TX, b["y"] + 4), b["prefix"], font=F["num"], fill=ACCENT + (a,))
        count = 0
        for li, line in enumerate(b["lines"]):
            ly = b["y"] + li * b["lh"]
            for x, word, color in line:
                if count >= shown:
                    break
                part = word[: max(0, shown - count)]
                d.text((left + x, ly), part, font=fnt, fill=color + (a,))
                cursor = (left + x + fnt.getlength(part) + 4, ly, fnt.size)
                count += len(word) + 1
            if count >= shown:
                break
    if cursor and cursor_on and alpha > 0.5:
        x, y, size = cursor
        d.rectangle((x, y + size * 0.12, x + max(4, size // 12), y + size * 1.08), fill=ACCENT + (a,))
    img.paste(layer, (0, 0), layer)


def frame_at(plan, chromes, t):
    for i, s in enumerate(plan):
        if t < s["end"] or i == len(plan) - 1:
            img = chromes[i].copy()
            typing = any(b["t0"] <= t < b["t1"] for b in s["blocks"])
            draw_content(img, s["blocks"], t, 1.0, typing or int(t * 2) % 2 == 0)
            return img
        if t < s["end"] + CLEAR:
            # clearing: the old text fades out quickly before the next slide types
            img = chromes[i + 1].copy()
            draw_content(img, s["blocks"], s["end"], 1 - (t - s["end"]) / CLEAR, False)
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


def _fftconv(x, h):
    size = len(x) + len(h) - 1
    nfft = 1 << (size - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(h, nfft), nfft)[: len(x)]


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


def synthwave(total, rng):
    """Retro synthwave bed in A minor at 100 BPM: pulsing octave bass, detuned saw
    pads, a 16th-note arpeggio with a dotted-eighth echo, kick, gated-reverb snare
    and hats, with the bass and pads ducking under the kick. Stereo (L, R)."""
    n = int((total + 1.0) * SR)
    beat = 60 / 100
    bar = 4 * beat
    prog = [(57, [57, 60, 64]), (53, [53, 57, 60]), (48, [48, 52, 55]), (55, [55, 59, 62])]  # Am F C G

    def hz(m):
        return 440 * 2 ** ((m - 69) / 12)

    def saw(f, k):
        return 2 * ((f * k + rng.uniform()) % 1.0) - 1

    bass, pad_l, pad_r, arp, drums, snare_bus = (np.zeros(n) for _ in range(6))
    lk = int(0.3 * SR)
    kk = np.arange(lk) / SR
    kick = np.sin(2 * np.pi * np.cumsum(45 + 105 * np.exp(-kk / 0.035)) / SR) * np.exp(-kk / 0.16)
    kick[: int(0.002 * SR)] += np.linspace(0.6, 0, int(0.002 * SR))
    ls = int(0.25 * SR)
    ks = np.arange(ls) / SR
    snare = (_lowpass(rng.standard_normal(ls), 3) * np.exp(-ks / 0.09) * 0.8
             + np.sin(2 * np.pi * 185 * ks) * np.exp(-ks / 0.05) * 0.6)
    lh = int(0.05 * SR)
    hat = np.diff(rng.standard_normal(lh), prepend=0) * _env(lh, 0.0005, 0.012)
    kicks, t_bar, b = [], 0.0, 0
    while t_bar < total + 0.5:
        root, triad = prog[b % 4]
        for e in range(8):                                  # bass: octave-pulsing eighths
            ln = int(beat / 2 * SR * 0.92)
            k = np.arange(ln) / SR
            note = root - 24 + (12 if e % 2 else 0)
            _put(bass, saw(hz(note), k) * np.minimum(1, k / 0.003) * np.exp(-k / 0.22), t_bar + e * beat / 2)
        ln = int(bar * SR)                                  # pads: three detuned saws per note
        k = np.arange(ln) / SR
        shape = np.minimum(1, k / 0.35) * np.minimum(1, (bar - k) / 0.12)
        pl, pr = np.zeros(ln), np.zeros(ln)
        for m in triad:
            pl += saw(hz(m + 12 - 0.08), k) + saw(hz(m + 12), k) * 0.7
            pr += saw(hz(m + 12 + 0.08), k) + saw(hz(m + 12), k) * 0.7
        _put(pad_l, pl * shape / 6, t_bar)
        _put(pad_r, pr * shape / 6, t_bar)
        tones = [triad[0] + 12, triad[1] + 12, triad[2] + 12, triad[0] + 24]
        for e in range(16):                                 # arpeggio: plucked square 16ths
            ln = int(beat / 4 * SR)
            k = np.arange(ln) / SR
            sq = np.sign(np.sin(2 * np.pi * hz(tones[e % 4] + 12) * k))
            _put(arp, sq * np.minimum(1, k / 0.002) * np.exp(-k / 0.05), t_bar + e * beat / 4)
        for q in range(4):                                  # drums
            tq = t_bar + q * beat
            kicks.append(tq)
            _put(drums, kick, tq)
            if q in (1, 3):
                _put(snare_bus, snare, tq)
            _put(drums, hat * 0.18, tq + beat / 2)
            _put(drums, hat * 0.08, tq)
        t_bar += bar
        b += 1
    bass = np.convolve(bass, _fir(700), "same")
    pad_l = np.convolve(pad_l, _fir(2000), "same")
    pad_r = np.convolve(pad_r, _fir(2000), "same")
    arp = np.convolve(arp, _fir(3200), "same")
    d = int(0.75 * beat * SR)                               # dotted-eighth echo on the arp
    arp_l, arp_r = arp.copy(), arp.copy()
    for r in range(1, 4):
        (arp_r if r % 2 else arp_l)[d * r:] += arp[: -d * r] * 0.4 ** r
    gate = int(0.3 * SR)                                    # 80s gated reverb on the snare
    ir = rng.standard_normal(gate) * np.exp(-np.arange(gate) / SR / 0.22)
    ir[-int(0.01 * SR):] *= np.linspace(1, 0, int(0.01 * SR))
    ir /= np.sqrt((ir ** 2).sum())
    wet = _fftconv(snare_bus, ir)
    duck = np.ones(n)                                       # sidechain pump from the kick
    for tk in kicks:
        i = int(tk * SR)
        seg = np.arange(min(int(0.3 * SR), max(0, n - i))) / SR
        duck[i:i + len(seg)] = np.minimum(duck[i:i + len(seg)], 1 - 0.55 * np.exp(-seg / 0.12))
    core = bass * 0.5 * duck + drums * 0.55 + snare_bus * 0.35 + wet * 0.35
    left = core + pad_l * 0.32 * duck + arp_l * 0.1
    right = core + pad_r * 0.32 * duck + arp_r * 0.1
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
            add(_lowpass(rng.standard_normal(ln), 24) * np.sin(np.linspace(0, np.pi, ln)) ** 2 * 0.25, t - 0.1)
        elif kind == "ping":
            # one bright ding with a short stereo echo, to close the reel
            ln = int(1.2 * SR)
            k = np.arange(ln) / SR
            f0 = 440 * 2 ** ((88 - 69) / 12)                 # E6
            ding = (np.sin(2 * np.pi * f0 * k) + 0.4 * np.sin(2 * np.pi * 2 * f0 * k) * np.exp(-k / 0.1)
                    + 0.2 * np.sin(2 * np.pi * 3.01 * f0 * k) * np.exp(-k / 0.06)) * _env(ln, 0.002, 0.35)
            add(ding * 0.32, t, 0.0)
            add(ding * 0.14, t + 0.18, -0.6)
            add(ding * 0.07, t + 0.36, 0.6)
        elif kind == "pop":
            ln = int(0.18 * SR)
            k = np.arange(ln) / SR
            freq = 660 + 440 * np.exp(-k / 0.03)
            add(np.sin(2 * np.pi * np.cumsum(freq) / SR) * _env(ln, 0.002, 0.05) * 0.3, t)

    bed_l, bed_r = synthwave(total, rng)
    bed_l, bed_r = bed_l[:n], bed_r[:n]
    fade = np.ones(n)
    fi, fo, end = int(0.3 * SR), int(1.5 * SR), min(n, int(total * SR))
    fade[:fi] = np.linspace(0, 1, fi)
    fade[end - fo:end] = np.linspace(1, 0, fo)
    fade[end:] = 0
    music = 0.42
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
    slides = reel_slides(spec["slides"])
    plan, events, total = timeline(slides)
    base = background()
    chromes = [chrome(base, i, len(slides), spec.get("handle", "pagehub.pl")) for i in range(len(slides))]
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
    ap = argparse.ArgumentParser(description="Carousel spec -> typing-animation Reel MP4.")
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
