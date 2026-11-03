#!/usr/bin/env python3
"""
make_reel.py - turn a carousel spec into a 9:16 Reel where the text types itself
out in a PageHub-style code editor, with original sound.

Picture: the browser-window look from the carousels, a line-number gutter and
a blinking cursor. The cover title is on screen from the very first frame (the
hook), everything after it types out at a readable pace, then the slide clears
and the next one starts. The window sits inside the Reels safe zone, away from
the like/comment rail and the caption.

Sound: synthesised here, so there is nothing to license and nothing Instagram
can mute. A key click per typed character, a soft whoosh between slides, a pop
for the button, and a quiet lo-fi chord bed with a light beat underneath.

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
CPS = {"kicker": 60, "title": 34, "subtitle": 70, "body": 78, "item": 70}
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


def layout(slide, first):
    kind = slide.get("type", "text")
    blocks = []
    if slide.get("kicker"):
        blocks.append(block("kicker", "// " + slide["kicker"], ACCENT, F["kicker"], lh=1.3))
    if slide.get("title"):
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
                t += dur + 0.12
        t += HOLD_LAST if last else HOLD
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
        if b["prefix"]:
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

def _env(n, attack, decay):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(attack, 1e-4)) * np.exp(-t / decay)


def _lowpass(x, taps):
    k = np.hanning(taps)
    return np.convolve(x, k / k.sum(), mode="same")


def sound(events, total, seed=7):
    rng = np.random.default_rng(seed)
    n = int((total + 0.5) * SR)
    left, right = np.zeros(n), np.zeros(n)

    def add(sig, t, pan=0.0, dst=(left, right)):
        i = max(0, int(t * SR))
        if i >= n:
            return
        sig = sig[: n - i]
        dst[0][i:i + len(sig)] += sig * (1 - pan)
        dst[1][i:i + len(sig)] += sig * (1 + pan)

    # key clicks: a short bright tick plus a small wooden body, varied every time
    for t, kind in events:
        if kind in ("key", "space"):
            ln = int(0.035 * SR)
            k = np.arange(ln) / SR
            noise = np.diff(rng.standard_normal(ln), prepend=0)
            tone = np.sin(2 * np.pi * rng.uniform(1800, 2600) * k)
            body = np.sin(2 * np.pi * rng.uniform(170, 250) * k)
            sig = (0.5 * noise * _env(ln, 0.0005, 0.004) + 0.2 * tone * _env(ln, 0.0003, 0.003)
                   + (0.55 if kind == "space" else 0.25) * body * _env(ln, 0.001, 0.012))
            add(sig * rng.uniform(0.09, 0.14), t + rng.uniform(-0.004, 0.004), rng.uniform(-0.3, 0.3))
        elif kind == "whoosh":
            ln = int(0.45 * SR)
            sweep = _lowpass(rng.standard_normal(ln), 24)
            add(sweep * np.sin(np.linspace(0, np.pi, ln)) ** 2 * 0.3, t - 0.1)
        elif kind == "pop":
            ln = int(0.18 * SR)
            k = np.arange(ln) / SR
            freq = 660 + 440 * np.exp(-k / 0.03)
            add(np.sin(2 * np.pi * np.cumsum(freq) / SR) * _env(ln, 0.002, 0.05) * 0.3, t)

    # music bed: Am9 - Fmaj7 - Cmaj7 - G6 at 84 BPM, soft keys, bass, kick and hat
    bed = (np.zeros(n), np.zeros(n))
    beat = 60 / 84
    chords = [[57, 60, 64, 67, 71], [53, 57, 60, 64], [48, 55, 59, 64], [55, 59, 62, 64]]
    t, bar = 0.0, 0
    while t < total + 0.5:
        notes = chords[bar % 4]
        ln = int(4 * beat * SR)
        k = np.arange(ln) / SR
        chord = np.zeros(ln)
        for m in notes:
            f = 440 * 2 ** ((m - 69) / 12)
            chord += np.sin(2 * np.pi * f * k) + 0.3 * np.sin(4 * np.pi * f * k) * np.exp(-k / 0.4)
        chord *= np.minimum(1, k / 0.25) * np.exp(-k / 3.5) / len(notes)
        add(chord, t, -0.1, bed)
        bass_f = 440 * 2 ** ((notes[0] - 12 - 69) / 12)
        add(np.sin(2 * np.pi * bass_f * k) * np.minimum(1, k / 0.02) * np.exp(-k / 1.2) * 0.6, t, 0, bed)
        for b in range(4):
            bt = t + b * beat
            if b in (0, 2):
                lk = int(0.22 * SR)
                kk = np.arange(lk) / SR
                kick = np.sin(2 * np.pi * np.cumsum(50 + 70 * np.exp(-kk / 0.03)) / SR) * np.exp(-kk / 0.09)
                add(kick * 0.7, bt, 0, bed)
            lh = int(0.04 * SR)
            hat = np.diff(rng.standard_normal(lh), prepend=0) * _env(lh, 0.0005, 0.008) * 0.12
            add(hat, bt + beat / 2, 0.15, bed)
        t += 4 * beat
        bar += 1
    bed = tuple(_lowpass(ch, 9) for ch in bed)          # warm, out of the way of the clicks

    fade = np.ones(n)
    fi, fo, end = int(0.6 * SR), int(1.2 * SR), min(n, int(total * SR))
    fade[:fi] = np.linspace(0, 1, fi)
    fade[end - fo:end] = np.linspace(1, 0, fo)
    fade[end:] = 0
    mix = np.stack([(left + bed[0] * 0.22) * fade, (right + bed[1] * 0.22) * fade], axis=1)
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
    slides = spec["slides"]
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
