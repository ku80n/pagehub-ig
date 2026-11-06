#!/usr/bin/env python3
"""
make_pendulum.py - the "wahadło" Reel: the PageHub tag hangs on a cord and swings
across the screen. Wherever the cord has passed, the big text changes: a problem
("NUMER NIE DZWONI?") and the answer ("OGARNIEMY TO.") take turns, one swing each.
No narrator. The last swing brings back the first question, so the clip loops
without a seam when Instagram plays it again.

The look: the carousels' near-black with a faint 3D space behind it (a hint of
teal nebula, a few stars flying out of the horizon, a dim floor grid rolling
towards the camera), the big text inside a quiet browser window with an address
bar, so it is clear at a glance that this is about a website, white questions,
the answer in the brand teal, a white tag with the PageHub logo, the logo on top. The comment button ("Napisz TELEFON w komentarzu") pops in with a
"ping" only after the last answer and fades out before the loop point, so the
clip has no visible end: the tag just keeps swinging.
Sound: an upbeat club loop generated here (four-on-the-floor kick, claps, hats,
pumping chords, bass, arp) at the tempo of the swing, two beats per swing, and a
whoosh every time the cord sweeps over the text. Nothing to license.

Usage
  python3 tools/make_pendulum.py weeks/2026-11-02/wahadlo-k2.json --out /tmp/w.mp4
  python3 tools/make_pendulum.py spec.json --still 0.5 --out x.png

Spec
  {"questions": ["...?", ...], "answer": "OGARNIEMY TO.",
   "cta": "Napisz TELEFON w komentarzu", "site": "pagehub.pl"}
  Optional "palettes": [{"name": "GRAFIT I POMARAŃCZ", "bg": "#F2F3F5", "text": "#1D2126",
  "main": "#3E4A56", "accent": "#E4570F", "button": "Zadzwoń"}, ...], one per question:
  instead of a text answer the window turns into a small website in those colours.
"""

import argparse
import json
import math
import pathlib
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import make_reel as mr  # noqa: E402

W, H, FPS, SR = 1080, 1920, 30, 48000
FONTS = ROOT / "assets" / "fonts"
LOGO = ROOT / "assets" / "logo" / "pagehub_white_bg.svg"

DEFAULT = {
    "questions": ["POTRZEBUJESZ STRONY?", "WOLNA STRONA?", "STARA STRONA?", "NIE MA CIĘ W GOOGLE?"],
    "answer": "OGARNIEMY TO.",
    "cta": "Napisz do nas wiadomość",
    "site": "pagehub.pl",
}

# colours: the carousel palette
BG = (9, 12, 17)
GLOW = (28, 152, 195)
FG = (240, 244, 248)
ACCENT = (28, 152, 195)
INK = (8, 12, 16)
TAG = (240, 244, 248)
CORD = (150, 166, 182)

# timing: two beats per swing
BPM = 122
HALF = 2 * 60 / BPM
HORIZON = 1185                        # where the 3D floor grid meets the sky

# geometry
PIVOT = (540.0, -1150.0)
REST_Y = 1140.0                       # tag centre at rest
AMP_X = 420.0                         # how far the tag goes left and right
TEXT_Y = 820                          # centre of the big text
TEXT_W = 640                          # widest line of the big text
TAG_SIZE = 200
TEXT_BAND = (TEXT_Y - 230, TEXT_Y + 230)


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def svg_png(svg_text, width):
    with tempfile.TemporaryDirectory() as tmp:
        src, out = pathlib.Path(tmp) / "l.svg", pathlib.Path(tmp) / "l.png"
        src.write_text(svg_text, encoding="utf-8")
        subprocess.run(["rsvg-convert", "-w", str(width), "-o", str(out), str(src)], check=True)
        return Image.open(out).convert("RGBA")


LOGO_DARK = ROOT / "assets" / "logo" / "pagehub-dark.png"      # rendered from the SVG once,
LOGO_MARK = ROOT / "assets" / "logo" / "pagehub-mark.png"      # so GitHub Actions needs no rsvg


def logo_images():
    """(logo for a dark background: white "page" and globe, teal "hub" and arc;
    the mark in its own colours for the white tag) - both from the site's SVG."""
    if LOGO_DARK.exists() and LOGO_MARK.exists():
        return Image.open(LOGO_DARK).convert("RGBA"), Image.open(LOGO_MARK).convert("RGBA")
    svg = LOGO.read_text(encoding="utf-8")
    dark = svg.replace('fill="#333333"', 'fill="#F0F4F8"')
    word = svg_png(dark, 1200)
    word = word.crop(word.getbbox())
    mark_svg = svg.replace('viewBox="0 0 1200 600"', 'viewBox="-4 150 310 300"').replace(
        'width="1200px" height="600px"', 'width="310px" height="300px"')
    mark = svg_png(mark_svg, 620)
    return word, mark.crop(mark.getbbox())


def _fractal(rng, octaves=5, base=6):
    """Soft cloudy noise in [0, 1], full frame."""
    acc = np.zeros((H, W), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        gh, gw = base * 2 ** o + 1, int(base * 2 ** o * W / H) + 2
        g = (rng.random((gh, gw)) * 255).astype(np.uint8)
        up = np.asarray(Image.fromarray(g).resize((W, H), Image.BICUBIC), np.float32) / 255
        acc += up * amp
        tot += amp
        amp *= 0.55
    acc /= tot
    return (acc - acc.min()) / (acc.max() - acc.min())


def make_space():
    """The still parts of the 3D space background: deep sky, teal and blue nebula,
    a darker pool behind the text, and the per-pixel geometry of the floor grid."""
    rng = np.random.default_rng(5)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    sky = np.zeros((H, W, 3), np.float32)
    top, low = np.array(BG, np.float32), np.array((10, 16, 24), np.float32)
    k = np.clip(yy / HORIZON, 0, 1)[..., None] ** 1.6
    sky[:] = top * (1 - k) + low * k
    neb = _fractal(rng)
    neb2 = _fractal(rng, base=4)
    teal = np.clip((neb - 0.45) * 2.4, 0, 1) ** 1.6 * np.exp(-((yy - 520) / 700) ** 2)
    blue = np.clip((neb2 - 0.5) * 2.2, 0, 1) ** 1.8 * np.exp(-((yy - 300) / 600) ** 2)
    sky += teal[..., None] * np.array(ACCENT, np.float32) * 0.13
    sky += blue[..., None] * np.array((30, 60, 160), np.float32) * 0.10
    # darker pool behind the big text, so it always reads
    pool = np.exp(-(((xx - 540) / 520) ** 2 + ((yy - TEXT_Y) / 300) ** 2) * 1.3)[..., None]
    sky *= 1 - 0.55 * pool
    # floor below the horizon: dark, a little lighter far away
    below = yy > HORIZON
    d = np.clip((yy - HORIZON) / (H - HORIZON), 0, 1)
    floor = np.array((10, 15, 22), np.float32) * (1 - d[..., None]) + np.array(BG, np.float32) * d[..., None]
    sky = np.where(below[..., None], floor, sky)
    # horizon glow
    glow = np.exp(-((yy - HORIZON) / 14) ** 2) * 0.22 + np.exp(-((yy - HORIZON) / 120) ** 2) * 0.08
    glow *= np.exp(-((xx - 540) / 700) ** 2)
    sky += glow[..., None] * np.array((60, 190, 235), np.float32)
    sky += rng.normal(0, 1.0, sky.shape)                          # grain against banding
    # grid geometry: camera over a flat floor, looking at the horizon
    gy = np.arange(HORIZON + 1, H, dtype=np.float32)[:, None]
    gx = np.arange(W, dtype=np.float32)[None, :]
    fh = 9000.0
    z = fh / (gy - HORIZON)                                       # depth of every row
    wx = (gx - 540) * z / 900.0                                   # floor x under every pixel
    cell = 1.6
    fpx = z / 900.0                                               # floor units per pixel, across
    fpz = fh / (gy - HORIZON) ** 2                                # floor units per pixel, along
    dist_x = np.abs((wx / cell + 0.5) % 1 - 0.5) * cell / fpx     # pixels to the nearest long line
    line_x = np.clip(1.3 - dist_x, 0, 1) + 0.22 * np.exp(-(dist_x / 4) ** 2)
    line_x *= np.clip(1 - fpx / (cell * 0.35), 0, 1)              # fade where lines get too dense
    fog = np.exp(-z / 260.0) * np.clip((gy - HORIZON) / 6, 0, 1)
    ns = 420
    stars = {"X": rng.uniform(-1, 1, ns) * 1400, "Y": -rng.uniform(0.03, 1, ns) ** 0.8 * 1500,
             "z0": rng.uniform(0, 1, ns), "tw": rng.uniform(0, 2 * np.pi, ns), "b": rng.uniform(0.5, 1, ns)}
    return {"sky": sky, "z": z, "fpz": fpz, "line_x": line_x, "fog": fog, "cell": cell, "stars": stars}


WIN = (110, 548, 970, 1100)           # browser window around the big text (x0, y0, x1, y1)
WIN_BAR = 70


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _lum(rgb):
    c = [v / 255 for v in rgb]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _contrast(a, b):
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


PANEL = (WIN[0] + 2, WIN[1] + WIN_BAR, WIN[2] - 2, WIN[3] - 2)   # the page area of the window


def palette_layer(pal):
    """The answer as a small website in the palette's colours, filling the window's
    page area: a nav bar, the palette name as the headline, the four swatches with
    their codes and the button in the accent colour. Drawn 2x for clean edges."""
    s2 = 2
    x0, y0, x1, y1 = PANEL
    w, h = (x1 - x0) * s2, (y1 - y0) * s2
    bg, fg, main, acc = (hex_rgb(pal[k]) for k in ("bg", "text", "main", "accent"))
    ink = max(((255, 255, 255), (17, 17, 17)), key=lambda c: _contrast(c, acc))
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=26 * s2, fill=bg + (255,), corners=(False, False, True, True))
    px = 46 * s2
    # nav: logo square, "Twoja firma", three link bars
    ny = 34 * s2
    d.rounded_rectangle([px, ny, px + 30 * s2, ny + 30 * s2], radius=8 * s2, fill=main + (255,))
    fn = font("Inter-SemiBold.otf", 24 * s2)
    d.text((px + 44 * s2, ny + 1 * s2), "Twoja firma", font=fn, fill=fg + (255,))
    for i in range(3):
        bx = w - px - (3 - i) * 82 * s2 + 18 * s2
        d.rounded_rectangle([bx, ny + 11 * s2, bx + 64 * s2, ny + 19 * s2], radius=4 * s2, fill=fg + (120,))
    # headline: the palette name
    fh = font("InterDisplay-Black.ttf", 70 * s2)
    lines = two_lines(pal["name"], fh)
    while max(fh.getlength(l) for l in lines) > w - 2 * px and fh.size > 40 * s2:
        fh = font("InterDisplay-Black.ttf", fh.size - 4)
        lines = two_lines(pal["name"], fh)
    hy = 100 * s2
    for i, line in enumerate(lines):
        d.text((px, hy + i * fh.size * 1.02), line, font=fh, fill=fg + (255,))
    # swatches with codes
    sy = hy + len(lines) * fh.size * 1.02 + 28 * s2
    gap, sw = 18 * s2, (w - 2 * px - 3 * 18 * s2) / 4
    fx = font("Inter-SemiBold.otf", 22 * s2)
    for i, (k, col) in enumerate((("bg", bg), ("text", fg), ("main", main), ("accent", acc))):
        sx = px + i * (sw + gap)
        d.rounded_rectangle([sx, sy, sx + sw, sy + 70 * s2], radius=14 * s2, fill=col + (255,),
                            outline=fg + (70,), width=2 * s2)
        d.text((sx + 2 * s2, sy + 80 * s2), pal[k].upper(), font=fx, fill=fg + (200,))
    # the button: the accent is for what the client should click
    by = sy + 128 * s2
    fb = font("Inter-Bold.otf", 28 * s2)
    label = pal.get("button", "Zadzwoń")
    bw = fb.getlength(label) + 56 * s2
    d.rounded_rectangle([px, by, px + bw, by + 64 * s2], radius=14 * s2, fill=acc + (255,))
    d.text((px + 28 * s2, by + 14 * s2), label, font=fb, fill=ink + (255,))
    small = img.resize((x1 - x0, y1 - y0), Image.LANCZOS)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    layer.alpha_composite(small, (x0, y0))
    return np.asarray(layer, np.float32) / 255.0


def browser_window(url):
    """A quiet browser window, as on the carousels: dark surface, thin border,
    three dots and an address bar with a lock and `url`. Drawn 2x for clean edges."""
    s2 = 2
    x0, y0, x1, y1 = WIN
    w, h = (x1 - x0) * s2, (y1 - y0) * s2
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = 28 * s2
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=(14, 19, 26, 215), outline=(38, 50, 66, 255), width=2 * s2)
    d.rounded_rectangle([0, 0, w - 1, WIN_BAR * s2], radius=r, fill=(20, 27, 36, 230), outline=(38, 50, 66, 255), width=2 * s2,
                        corners=(True, True, False, False))
    for i, col in enumerate((ACCENT, (60, 74, 90), (60, 74, 90))):
        cx = (34 + i * 26) * s2
        d.ellipse([cx - 7 * s2, (WIN_BAR / 2 - 7) * s2, cx + 7 * s2, (WIN_BAR / 2 + 7) * s2], fill=col + (255,))
    bx0, bx1 = 120 * s2, w - 40 * s2
    by0, by1 = 16 * s2, (WIN_BAR - 16) * s2
    d.rounded_rectangle([bx0, by0, bx1, by1], radius=(by1 - by0) / 2, fill=(10, 14, 19, 255))
    f = font("Inter-Medium.otf", 25 * s2)
    lx, ly = bx0 + 22 * s2, (by0 + by1) / 2
    d.rounded_rectangle([lx, ly - 4 * s2, lx + 14 * s2, ly + 8 * s2], radius=2 * s2, fill=(120, 136, 152, 255))    # lock
    d.arc([lx + 2 * s2, ly - 12 * s2, lx + 12 * s2, ly + 2 * s2], 180, 360, fill=(120, 136, 152, 255), width=2 * s2)
    d.text((lx + 26 * s2, ly - 16 * s2), url, font=f, fill=(150, 166, 182, 255))
    return img.resize((x1 - x0, y1 - y0), Image.LANCZOS)


def space_frame(t, total, sp):
    """The sky at time t: the floor grid rolls towards the camera and the stars fly
    out of the horizon. Both run a whole number of cycles per loop, so it loops."""
    img = sp["sky"].copy()
    cell = sp["cell"]
    off = cell * 4 * (t / total)                                  # four grid cells per loop
    dist_z = np.abs(((sp["z"] + off) / cell + 0.5) % 1 - 0.5) * cell / sp["fpz"]
    line_z = np.clip(1.3 - dist_z, 0, 1) + 0.22 * np.exp(-(dist_z / 4) ** 2)
    line_z *= np.clip(1 - sp["fpz"] / (cell * 0.35), 0, 1)
    grid = np.maximum(sp["line_x"], line_z) * sp["fog"]
    img[HORIZON + 1:] += grid[..., None] * np.array((40, 175, 225), np.float32) * 0.26
    st = sp["stars"]
    zmax = 1.0
    z = (st["z0"] - t / total) % zmax + 0.02                      # every star flies the whole way once per loop
    f = 900.0
    xs = 540 + st["X"] / (z * 10) * f / 100
    ys = HORIZON + st["Y"] / (z * 10) * f / 100
    near = np.clip(1 - z, 0, 1)
    size = 0.9 + 3.4 * near ** 2.0
    bright = st["b"] * 0.55 * np.clip(near * 3, 0, 1) * np.clip((z - 0.03) / 0.12, 0, 1)
    bright *= 0.8 + 0.2 * np.sin(2 * np.pi * 3 * t / total + st["tw"])
    for x, y, r, bv in zip(xs, ys, size, bright):
        if bv < 0.03 or not (-6 < x < W + 6 and -6 < y < HORIZON):
            continue
        rad = int(r * 2.5) + 1
        x0, x1 = max(0, int(x) - rad), min(W, int(x) + rad + 1)
        y0, y1 = max(0, int(y) - rad), min(HORIZON, int(y) + rad + 1)
        if x0 >= x1 or y0 >= y1:
            continue
        gy, gx = np.mgrid[y0:y1, x0:x1]
        spot = np.exp(-((gx - x) ** 2 + (gy - y) ** 2) / (2 * (r * 0.55) ** 2)) * bv
        if "star_mask" in sp:
            spot *= sp["star_mask"][y0:y1, x0:x1]
        img[y0:y1, x0:x1] += spot[..., None] * np.array((200, 235, 255), np.float32)
    return img


# short words that must not end a line in Polish typography ("NUMER NIE / DZWONI?")
NO_LINE_END = {"a", "i", "o", "u", "w", "z", "na", "do", "po", "za", "od", "ze", "we", "nie", "czy", "to", "bez"}


def two_lines(text, f):
    """Two lines (one for a single word), split where the longer line is shortest,
    never after a short preposition, conjunction or "nie". A "|" in the text forces the break."""
    if "|" in text:
        return [part.strip() for part in text.split("|", 1)]
    words = text.split()
    if len(words) < 2:
        return [text]
    splits = [(" ".join(words[:i]), " ".join(words[i:])) for i in range(1, len(words))]

    def bad(p):
        return p[0].split()[-1].lower() in NO_LINE_END

    if all(bad(p) for p in splits) and f.getlength(text) <= TEXT_W:
        return [text]                                         # "BEZ SZABLONU?" stays on one line
    return list(min(splits, key=lambda p: max(f.getlength(p[0]), f.getlength(p[1])) + (10000 if bad(p) else 0)))


def fit_size(text):
    for size in range(132, 60, -2):
        f = font("InterDisplay-Black.ttf", size)
        if max(f.getlength(s) for s in two_lines(text, f)) <= TEXT_W:
            return size
    return 60


def text_layer(text, color, size, glow=False):
    f = font("InterDisplay-Black.ttf", size)
    lines = two_lines(text, f)
    lh = int(size * 1.0)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    top = TEXT_Y - lh * len(lines) // 2
    for i, s in enumerate(lines):
        d.text(((W - f.getlength(s)) / 2, top + i * lh - size * 0.12), s, font=f, fill=color + (255,))
    if glow:                                                      # the teal answer gets a soft light around it
        a = layer.split()[3].filter(ImageFilter.GaussianBlur(18))
        g = Image.new("RGBA", (W, H), color + (0,))
        g.putalpha(a.point(lambda v: int(v * 0.45)))
        layer = Image.alpha_composite(g, layer)
    return np.asarray(layer, np.float32) / 255.0


CTA_Y = 1328                         # centre of the comment button
TOPIC_Y = 640                        # centre of the topic pill over the big text


def cta_image(cta):
    """The comment button, as in the other Reels (drawn 2x for a clean pop-in)."""
    s = 2
    f = font("Inter-Bold.otf", 38 * s)
    bw, bh = int(f.getlength(cta) + 76 * s), 92 * s
    img = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, bw - 1, bh - 1], radius=bh / 2, fill=ACCENT + (255,))
    d.text((38 * s, 21 * s), cta, font=f, fill=INK + (255,))
    return img


def cta_state(t, total, t0):
    """(scale, opacity) of the button: hidden until the last answer is up (t0), then
    a quick pop with the ping, and gone again just before the loop point."""
    if t < t0:
        return 0.0, 0.0
    u = t - t0
    pop = min(1.0, u / 0.22)
    scale = 1 + 0.12 * math.sin(math.pi * pop) if pop < 1 else 1.0
    scale *= 0.7 + 0.3 * (1 - (1 - pop) ** 3)
    alpha = min(1.0, u / 0.08) * min(1.0, max(0.0, (total - 0.02 - t) / 0.3))
    return scale, alpha


def static_layer(word, site, topic=""):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    wm = word.resize((380, int(word.height * 380 / word.width)), Image.LANCZOS)
    layer.alpha_composite(wm, ((W - wm.width) // 2, 262))
    d = ImageDraw.Draw(layer)
    if topic:                                                     # what it is about, all the time (like the carousel kicker)
        f = font("Inter-SemiBold.otf", 30)
        label = topic.upper()
        tw = sum(f.getlength(c) for c in label) + 3 * (len(label) - 1)
        pw, ph = tw + 56, 60
        x0, y0 = (W - pw) / 2, TOPIC_Y - ph / 2
        d.rounded_rectangle([x0, y0, x0 + pw, y0 + ph], radius=ph / 2, fill=(14, 44, 60, 235),
                            outline=ACCENT + (255,), width=2)
        x = x0 + 28
        for c in label:
            d.text((x, y0 + 13), c, font=f, fill=ACCENT + (255,))
            x += f.getlength(c) + 3
    f2 = font("Inter-Medium.otf", 28)
    d.text(((W - f2.getlength(site)) / 2, 1398), site, font=f2, fill=FG + (215,))
    return layer


def pendulum_sprite(mark):
    """Cord + white tag hanging straight down; the pivot is at (cx, 0)."""
    length = REST_Y - PIVOT[1] - TAG_SIZE / 2
    sw, sh = TAG_SIZE + 120, int(length + TAG_SIZE + 120)
    cx = sw // 2
    s = 3                                                         # draw 3x, downsample: smooth edges
    big = Image.new("RGBA", (sw * s, sh * s), (0, 0, 0, 0))
    tx, ty = cx - TAG_SIZE / 2, length
    shadow = Image.new("RGBA", big.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([(tx + 10) * s, (ty + 18) * s, (tx + TAG_SIZE + 10) * s, (ty + TAG_SIZE + 18) * s],
                                             radius=46 * s, fill=(0, 0, 0, 150))
    big = Image.alpha_composite(big, shadow.filter(ImageFilter.GaussianBlur(16 * s)))
    d = ImageDraw.Draw(big)
    d.line([(cx * s, 0), (cx * s, (length + 22) * s)], fill=CORD + (255,), width=5 * s)
    d.rounded_rectangle([tx * s, ty * s, (tx + TAG_SIZE) * s, (ty + TAG_SIZE) * s], radius=46 * s, fill=TAG + (255,))
    d.ellipse([(cx - 9) * s, (ty + 12) * s, (cx + 9) * s, (ty + 30) * s], fill=(190, 202, 214, 255))      # the hole
    m = mark.resize((int(128 * s), int(128 * s * mark.height / mark.width)), Image.LANCZOS)
    big.alpha_composite(m, (int((cx - 64) * s - 6 * s), int((ty + TAG_SIZE / 2) * s - m.height / 2 + 8 * s)))
    return big.resize((sw, sh), Image.LANCZOS), (cx, 0)


def angle(t):
    """Swing angle (radians, + = to the right). Left extreme at t=0, right at t=HALF."""
    tmax = math.asin(AMP_X / (REST_Y - PIVOT[1]))
    return -tmax * math.cos(math.pi * t / HALF)


def pendulum_box(t0, t1):
    xs = []
    for t in np.linspace(t0, t1, 6):
        th = angle(t)
        for r in (-PIVOT[1], REST_Y - PIVOT[1] + TAG_SIZE * 0.9):
            xs.append(PIVOT[0] + r * math.sin(th))
    x0 = int(max(0, min(xs) - TAG_SIZE * 0.85))
    x1 = int(min(W, max(xs) + TAG_SIZE * 0.85))
    return x0, 0, x1, int(min(H, REST_Y + TAG_SIZE * 0.95))


def place(sprite, anchor, theta, box):
    """The sprite rotated by theta (+ = to the right) about the pivot, rendered
    into `box` of the screen, premultiplied RGBA."""
    c, s_ = math.cos(theta), math.sin(theta)
    x0, y0, x1, y1 = box
    px, py = PIVOT[0] - x0, PIVOT[1] - y0
    a, b, d, e = c, -s_, s_, c
    cc = anchor[0] - a * px - b * py
    ff = anchor[1] - d * px - e * py
    img = sprite.transform((x1 - x0, y1 - y0), Image.AFFINE, (a, b, cc, d, e, ff), resample=Image.BICUBIC)
    arr = np.asarray(img, np.float32) / 255.0
    arr[..., :3] *= arr[..., 3:4]
    return arr


END_HOLD = 2                          # extra swings on the last answer, so the button can be read


def answer_for(spec, i):
    """The answer to question i: its own one from `answers` (the concrete fix), or
    the one shared `answer`."""
    answers = spec.get("answers") or []
    return answers[i] if i < len(answers) and answers[i] else spec["answer"]


def palette_for(spec, i):
    pals = spec.get("palettes") or []
    return pals[i] if i < len(pals) and pals[i] else None


def states(spec):
    """Question, its answer, question, its answer, ... then, when there is a button,
    the closing line (or the last answer) stays for END_HOLD swings while the button
    is up (an even count keeps the swing and the music loop whole)."""
    seq = []
    for i, q in enumerate(spec["questions"]):
        pal = palette_for(spec, i)
        seq += [("q", q), ("p", pal["name"]) if pal else ("a", answer_for(spec, i))]
    if spec.get("cta"):
        last = ("a", spec["closing"]) if spec.get("closing") else seq[-1]
        seq += [last] * END_HOLD
    return seq


def cta_start(spec):
    """The button pops up as soon as the closing line (or the last answer) is fully on screen."""
    held = END_HOLD if spec.get("closing") else END_HOLD + 1
    return HALF * (len(states(spec)) - held)


def frame(t, spec, assets):
    space, static, layers, sprite, anchor, button = assets
    seq = states(spec)
    total = HALF * len(seq)
    t = t % total
    k = int(t // HALF)
    old, new = layers[seq[k]], layers[seq[(k + 1) % len(seq)]]
    theta = angle(t)
    out = space_frame(t, total, space)
    # the big text: where the cord line has already swept, the next text shows
    y0, y1 = space.get("band", TEXT_BAND)
    ys = np.arange(y0, y1, dtype=np.float32)[:, None]
    xs = np.arange(W, dtype=np.float32)[None, :]
    line_x = PIVOT[0] + (ys - PIVOT[1]) * math.tan(theta)
    side = (line_x - xs) if k % 2 == 0 else (xs - line_x)
    mix = np.clip(side / 1.6 + 0.5, 0, 1)[..., None]
    band = out[y0:y1]
    for lay, w in ((old[y0:y1], 1 - mix), (new[y0:y1], mix)):
        a = lay[..., 3:4] * w
        band = band * (1 - a) + lay[..., :3] * 255 * a
    out[y0:y1] = band
    st = static
    out = out * (1 - st[..., 3:4]) + st[..., :3] * 255 * st[..., 3:4]
    scale, alpha = cta_state(t, total, cta_start(spec))
    if alpha > 0 and button is not None:
        bw, bh = max(2, int(button.width / 2 * scale)), max(2, int(button.height / 2 * scale))
        b = np.asarray(button.resize((bw, bh), Image.LANCZOS), np.float32) / 255.0
        x0, y0 = (W - bw) // 2, CTA_Y - bh // 2
        a = b[..., 3:4] * alpha
        out[y0:y0 + bh, x0:x0 + bw] = out[y0:y0 + bh, x0:x0 + bw] * (1 - a) + b[..., :3] * 255 * a
    # the swinging tag, with a light motion blur (7 samples over a quarter of a frame)
    n, shutter = 7, 0.25 / FPS
    times = [t + shutter * (j / (n - 1) - 0.5) for j in range(n)]
    box = pendulum_box(times[0], times[-1])
    acc = sum(place(sprite, anchor, angle(tt), box) for tt in times) / n
    bx0, by0, bx1, by1 = box
    region = out[by0:by1, bx0:bx1]
    out[by0:by1, bx0:bx1] = region * (1 - acc[..., 3:4]) + acc[..., :3] * 255
    return np.clip(out, 0, 255).astype(np.uint8)


def prepare(spec):
    word, mark = logo_images()
    size = min(fit_size(text) for kind, text in states(spec) if kind != "p")   # one size for every text
    pals = {p["name"]: p for p in spec.get("palettes") or [] if p}
    layers = {}
    for kind, text in states(spec):
        if (kind, text) in layers:
            continue
        if kind == "p":
            layers[(kind, text)] = palette_layer(pals[text])
        else:
            layers[(kind, text)] = text_layer(text, FG if kind == "q" else ACCENT, size, glow=kind == "a")
    static = np.asarray(static_layer(word, spec["site"], spec.get("topic_label", "")), np.float32) / 255.0
    sprite, anchor = pendulum_sprite(mark)
    button = cta_image(spec["cta"]) if spec.get("cta") else None
    space = make_space()
    if pals:                                                      # the wipe has to cover the whole page area
        space["band"] = (min(TEXT_BAND[0], PANEL[1]), max(TEXT_BAND[1], PANEL[3]))
    if spec.get("url"):                                           # the window sits in the background, under the text
        win = np.asarray(browser_window(spec["url"]), np.float32) / 255.0
        x0, y0, x1, y1 = WIN
        a = win[..., 3:4]
        space["sky"][y0:y1, x0:x1] = space["sky"][y0:y1, x0:x1] * (1 - a) + win[..., :3] * 255 * a
        mask = np.ones((H, W), np.float32)
        mask[y0:y1, x0:x1] = 1 - 0.9 * a[..., 0]                  # stars stay behind the window
        space["star_mask"] = mask
    return space, static, layers, sprite, anchor, button


# ---------------------------------------------------------------- music

def _hz(m):
    return 440 * 2 ** ((m - 69) / 12)


def _hp(x, cut, taps=63):
    return x - np.convolve(x, mr._fir(cut, taps), "same")


# the lead hook over two bars: (beat, MIDI note, length in beats) - A minor pentatonic
HOOK = [(0.0, 76, 0.5), (0.75, 76, 0.5), (1.5, 79, 0.75), (2.5, 76, 0.5), (3.0, 74, 0.75),
        (4.0, 72, 0.5), (4.75, 72, 0.5), (5.5, 74, 0.75), (6.5, 76, 1.25)]


def club_bed(bars, rng, bpm=BPM):
    """An upbeat club loop, `bars` bars long and periodic: four-on-the-floor kick,
    claps on 2 and 4, 16th hats with open hats on the off-beats, an off-beat bass,
    a rolling 16th bass, shaker, wide chords pumping under the kick, a plucky 16th
    arp and a short lead hook every two bars. No fill or break, so
    nothing marks the loop point. One chord per bar, so the loop closes on the dominant (E -> Am).
    Stereo (L, R)."""
    beat = 60 / bpm
    bar = 4 * beat
    total = bars * bar
    n = int((2 * total + 1.0) * SR)                        # rendered twice, the second copy is kept
    prog = [(57, [57, 60, 64, 69]), (53, [53, 57, 60, 65]), (48, [55, 60, 64, 67]), (55, [55, 59, 62, 67]),
            (52, [56, 59, 64, 68])]
    prog = (prog * 4)[:bars] if bars != 5 else prog
    kick_b, clap_b, hat_b, bass_b, arp_b, shk_b, lead_b = (np.zeros(n) for _ in range(7))
    pad_l, pad_r = np.zeros(n), np.zeros(n)

    lk = int(0.32 * SR)
    k = np.arange(lk) / SR
    kick = np.sin(2 * np.pi * np.cumsum(48 + 130 * np.exp(-k / 0.028)) / SR) * np.exp(-k / 0.16)
    kick += np.convolve(rng.standard_normal(lk), mr._fir(5000, 31), "same") * np.exp(-k / 0.003) * 0.5
    lc = int(0.32 * SR)
    kc = np.arange(lc) / SR
    burst = sum(np.exp(-np.maximum(kc - o, 0) / 0.007) * (kc >= o) for o in (0.0, 0.011, 0.022))
    clap = _hp(np.convolve(rng.standard_normal(lc), mr._fir(4200, 63), "same"), 900) * (burst + 0.35 * np.exp(-kc / 0.09))
    lh = int(0.04 * SR)
    hat = _hp(rng.standard_normal(lh), 7000, 31) * mr._env(lh, 0.0005, 0.012)
    lo = int(0.22 * SR)
    ohat = _hp(rng.standard_normal(lo), 6500, 31) * mr._env(lo, 0.001, 0.08)
    ls = int(0.05 * SR)
    shaker = _hp(np.convolve(rng.standard_normal(ls), mr._fir(9000, 31), "same"), 4500, 31) * mr._env(ls, 0.004, 0.02)
    lsn = int(0.18 * SR)
    ksn = np.arange(lsn) / SR
    snare = (np.sin(2 * np.pi * 190 * ksn) * np.exp(-ksn / 0.05) * 0.6
             + _hp(rng.standard_normal(lsn), 1500) * np.exp(-ksn / 0.06) * 0.5)

    def saw(f, ln, harm=14):
        tt = np.arange(ln) / SR
        return sum(np.sin(2 * np.pi * h * f * tt) / h for h in range(1, harm + 1))

    t_bar = 0.0
    b = 0
    while t_bar < 2 * total + 0.2:
        root, chord = prog[b % bars]
        for q in range(4):
            mr._put(kick_b, kick, t_bar + q * beat)
        for q in (1, 3):
            mr._put(clap_b, clap, t_bar + q * beat)
        for e in range(16):
            if e % 4 != 2:
                mr._put(hat_b, hat * (0.9 if e % 2 else 0.55), t_bar + e * beat / 4)
        for q in range(4):
            mr._put(hat_b, ohat * 0.8, t_bar + (q + 0.5) * beat)
        # rolling 16th bass: strong on the off-beat, ghost notes around it, octave up at the end
        ln = int(beat / 4 * 0.9 * SR)
        env = mr._env(ln, 0.002, 0.07)
        for e in range(16):
            if e % 4 == 0:
                continue                                          # leave room for the kick
            q, pos = divmod(e, 4)
            note = root - 24 + (12 if (q == 3 and pos == 3) else 0)
            gain = 1.0 if pos == 2 else 0.55
            tone = np.convolve(saw(_hz(note), ln, 8), mr._fir(900, 63), "same")
            mr._put(bass_b, (tone + 0.6 * np.sin(2 * np.pi * _hz(note) * np.arange(ln) / SR)) * env * gain,
                    t_bar + e * beat / 4)
        # shaker on every 16th, accented off the beat
        for e in range(16):
            mr._put(shk_b, shaker * (1.0 if e % 2 else 0.45), t_bar + e * beat / 4 + (0.012 if e % 2 else 0))
        # snare body under the clap
        for q in (1, 3):
            mr._put(clap_b, snare, t_bar + q * beat)
        # lead hook, two bars long
        if b % 2 == 0:
            for at, m, ln_b in HOOK:
                ln = int(ln_b * beat * SR)
                tt_ = np.arange(ln) / SR
                vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * tt_) * np.clip(tt_ / 0.15, 0, 1)
                ph = 2 * np.pi * np.cumsum(_hz(m) * vib) / SR
                tone = sum(np.sin(h * ph) / h for h in (1, 2, 3, 4, 5, 6)) * mr._env(ln, 0.004, 0.35)
                mr._put(lead_b, tone, t_bar + at * beat)
        # wide chords for the whole bar
        ln = int(bar * SR)
        for m in chord:
            for det, dst in ((-0.12, pad_l), (0.12, pad_r), (-0.04, pad_r), (0.04, pad_l)):
                mr._put(dst, saw(_hz(m + det), ln, 10) * mr._env(ln, 0.01, 6.0) / len(chord), t_bar)
        # plucky 16th arp over the chord, an octave up
        lp = int(beat / 4 * 0.9 * SR)
        kp = np.arange(lp) / SR
        pattern = [0, 1, 2, 3, 2, 1, 2, 3]
        for e in range(16):
            m = chord[pattern[e % 8]] + 12
            f = _hz(m)
            pluck = (np.sin(2 * np.pi * f * kp) + 0.35 * np.sin(2 * np.pi * 2 * f * kp)) * mr._env(lp, 0.002, 0.07)
            mr._put(arp_b, pluck * (1.0 if e % 4 == 0 else 0.7), t_bar + e * beat / 4)
        t_bar += bar
        b += 1

    # pump: everything but the drums ducks under each kick
    tt = np.arange(n) / SR
    since = np.mod(tt, beat)
    pump = 1 - 0.72 * np.exp(-since / 0.11)
    pad_l = np.convolve(pad_l, mr._fir(4200), "same") * pump
    pad_r = np.convolve(pad_r, mr._fir(4200), "same") * pump
    lead_b = np.convolve(lead_b, mr._fir(5200), "same") * (0.75 + 0.25 * pump)
    bass_b *= 0.6 + 0.4 * pump
    arp_b = np.convolve(arp_b, mr._fir(5000), "same") * (0.5 + 0.5 * pump)
    # a short room on claps and arp
    ir_len = int(0.9 * SR)
    irs = [np.convolve(rng.standard_normal(ir_len) * np.exp(-np.arange(ir_len) / SR / 0.25), mr._fir(6000, 63), "same")
           for _ in range(2)]
    irs = [ir / np.sqrt((ir ** 2).sum()) for ir in irs]
    wet_l = mr._fftconv(clap_b * 0.5 + arp_b * 0.6 + lead_b * 0.5, irs[0])
    wet_r = mr._fftconv(clap_b * 0.5 + arp_b * 0.6 + lead_b * 0.5, irs[1])
    drums = kick_b * 0.85 + clap_b * 0.55 + hat_b * 0.34
    left = drums + shk_b * 0.16 + bass_b * 0.40 + pad_l * 0.30 + arp_b * 0.26 + lead_b * 0.24 + wet_l * 0.13
    right = drums + shk_b * 0.12 + bass_b * 0.40 + pad_r * 0.30 + arp_b * 0.20 + lead_b * 0.24 + wet_r * 0.13
    a, z = int(total * SR), int(2 * total * SR)
    return left[a:z], right[a:z]


def soundtrack(spec, total):
    rng = np.random.default_rng(11)
    bars = int(round(total / (4 * 60 / BPM)))
    l, r = club_bed(bars, rng)
    n = len(l)
    fx_l, fx_r = np.zeros(n), np.zeros(n)
    for k in range(len(states(spec))):
        t = k * HALF + HALF / 2                                # the cord crosses the middle on the beat between
        ln = int(0.5 * SR)
        x = np.arange(ln) / ln
        noise = rng.standard_normal(ln)
        w = (np.convolve(noise, mr._fir(2600, 63), "same") * 0.5 + np.convolve(noise, mr._fir(500, 127), "same")) \
            * np.sin(np.pi * x) ** 2
        pan = (1 if k % 2 == 0 else -1) * (x - 0.5) * 1.2
        i0 = int((t - 0.25) * SR)
        for buf, sgn in ((fx_l, -1), (fx_r, 1)):
            seg = w * (1 + sgn * pan) * 0.5
            i = i0 % n
            end = min(n, i + ln)
            buf[i:end] += seg[: end - i]
            if end - i < ln:
                buf[: ln - (end - i)] += seg[end - i:]
    bed_rms = np.sqrt(np.mean(l ** 2 + r ** 2) / 2)
    on = np.abs(fx_l) + np.abs(fx_r) > 1e-4
    g = 0.55 * bed_rms / max(np.sqrt(np.mean((fx_l[on] ** 2 + fx_r[on] ** 2) / 2)), 1e-9)
    mix = np.stack([l + fx_l * g, r + fx_r * g], axis=1)
    if spec.get("cta"):                                        # the same "ping" as in the other Reels
        ln = int(1.0 * SR)
        k = np.arange(ln) / SR
        f0 = 440 * 2 ** ((88 - 69) / 12)                       # E6
        ding = (np.sin(2 * np.pi * f0 * k) + 0.4 * np.sin(2 * np.pi * 2 * f0 * k) * np.exp(-k / 0.1)
                + 0.2 * np.sin(2 * np.pi * 3.01 * f0 * k) * np.exp(-k / 0.06)) * mr._env(ln, 0.002, 0.35)
        t0 = int(cta_start(spec) * SR)
        for delay, gain, pan in ((0.0, 1.0, 0.0), (0.2, 0.42, -0.6), (0.4, 0.2, 0.6)):
            i = t0 + int(delay * SR)
            seg = ding[: max(0, n - i)] * gain * bed_rms * 2.4
            mix[i:i + len(seg), 0] += seg * (1 - pan)
            mix[i:i + len(seg), 1] += seg * (1 + pan)
    mix = np.tanh(mix / np.abs(mix).max() * 1.3) / np.tanh(1.3)       # glue it like a limiter would
    return mix * 0.8


def build(spec, out_path):
    assets = prepare(spec)
    total = HALF * len(states(spec))
    with tempfile.TemporaryDirectory() as tmp:
        wav = pathlib.Path(tmp) / "a.wav"
        mr.write_wav(wav, soundtrack(spec, total))
        cmd = [mr.ffmpeg_bin(), "-y", "-loglevel", "error",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
               "-i", str(wav), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "192k", "-ar", str(SR), "-shortest", "-movflags", "+faststart", str(out_path)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for f in range(int(round(total * FPS))):
            proc.stdin.write(frame(f / FPS, spec, assets).tobytes())
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg nie zbudował rolki")
    return out_path, total


def pendulum_spec(carousel, trial=False):
    """The Reel of a carousel spec (kN.json): meta.reel_pendulum + the comment
    button from meta.cta_keyword. The trial Reel starts with the second question,
    so Instagram gets a different video and it tests another opening."""
    meta = carousel.get("meta", {})
    rp = meta.get("reel_pendulum") or {}
    if not rp.get("questions"):
        return None
    kw = meta.get("cta_keyword", "").strip()
    spec = dict(DEFAULT)
    spec.update({"questions": list(rp["questions"]), "answer": rp.get("answer", "OGARNIEMY TO."),
                 "answers": list(rp.get("answers") or []), "closing": rp.get("closing", ""),
                 "palettes": list(rp.get("palettes") or []),
                 "url": rp.get("url", "twoja-strona.pl"),
                 "cta": rp.get("cta") or (f"Napisz {kw} w komentarzu" if kw else "Napisz do nas wiadomość")})
    if trial and len(spec["questions"]) > 1:
        spec["questions"] = spec["questions"][1:] + spec["questions"][:1]
        for k in ("answers", "palettes"):
            if spec[k]:
                spec[k] = spec[k][1:] + spec[k][:1]
    return spec


def main():
    ap = argparse.ArgumentParser(description="Rolka z wahadłem PageHub.")
    ap.add_argument("spec", nargs="?", help="kN.json karuzeli (meta.reel_pendulum) albo własny spec")
    ap.add_argument("--out", required=True)
    ap.add_argument("--still", type=float)
    ap.add_argument("--trial", action="store_true", help="wersja próbna (zaczyna od drugiego pytania)")
    a = ap.parse_args()
    spec = dict(DEFAULT)
    if a.spec:
        data = json.loads(pathlib.Path(a.spec).read_text(encoding="utf-8"))
        if "meta" in data:
            spec = pendulum_spec(data, a.trial)
            if spec is None:
                sys.exit(f"{a.spec}: brak meta.reel_pendulum.questions")
        else:
            spec.update(data)
    if a.still is not None:
        Image.fromarray(frame(a.still, spec, prepare(spec))).save(a.out)
        print(a.out)
        return
    path, total = build(spec, a.out)
    print(f"{path}  ({total:.1f} s)")


if __name__ == "__main__":
    main()
