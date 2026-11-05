#!/usr/bin/env python3
"""
make_pendulum.py - the "wahadło" Reel: the PageHub tag hangs on a cord and swings
across the screen. Wherever the cord has passed, the big text changes:
a question ("WOLNA STRONA?") and the answer ("OGARNIEMY TO.") take turns, one
swing each. No narrator. The last swing brings back the first question, so the
clip loops without a seam when Instagram plays it again.

The look follows the brand: teal background, dark questions, white answers, the
PageHub mark on a dark tag, the wordmark on top, "PROJEKT · KOD · SEO" and
pagehub.pl at the bottom. Sound: the night-drive bed from make_reel.py at the
tempo of the swing, and a soft whoosh every time the cord sweeps over the text.

Usage
  python3 tools/make_pendulum.py --out /tmp/wahadlo.mp4
  python3 tools/make_pendulum.py spec.json --out x.mp4      # own texts, see DEFAULT
  python3 tools/make_pendulum.py --still 0.6 --out x.png
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
    "tagline": "PROJEKT · KOD · SEO",
    "site": "pagehub.pl",
}

# colours
BG_IN, BG_OUT = (48, 168, 208), (10, 84, 112)      # teal, lighter in the middle
INK = (5, 30, 41)                                    # questions
WHITE = (255, 255, 255)                              # answers
TAG = (11, 17, 23)
CORD = (6, 14, 19)
ACCENT = "#1C98C3"

# geometry
PIVOT = (540.0, -1150.0)
REST_Y = 1150.0                       # tag centre at rest
HALF = 1.25                           # seconds per swing (one text change)
AMP_X = 420.0                         # how far the tag goes left and right
TEXT_Y = 830                          # centre of the big text
TEXT_W = 640                          # widest line of the big text
TAG_SIZE = 200
TEXT_BAND = (TEXT_Y - 230, TEXT_Y + 230)  # rows where the big text can be


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def svg_png(svg_text, width):
    with tempfile.TemporaryDirectory() as tmp:
        src, out = pathlib.Path(tmp) / "l.svg", pathlib.Path(tmp) / "l.png"
        src.write_text(svg_text, encoding="utf-8")
        subprocess.run(["rsvg-convert", "-w", str(width), "-o", str(out), str(src)], check=True)
        return Image.open(out).convert("RGBA")


def logo_images():
    """(wordmark in white, the mark: white globe + teal arc) from the site's SVG."""
    svg = LOGO.read_text(encoding="utf-8")
    white = svg.replace('fill="#333333"', 'fill="#FFFFFF"').replace('fill="#1C98C3"', 'fill="#FFFFFF"')
    word = svg_png(white, 1200)
    word = word.crop(word.getbbox())
    mark_svg = svg.replace('fill="#333333"', 'fill="#FFFFFF"').replace(
        'viewBox="0 0 1200 600"', 'viewBox="-4 150 310 300"').replace('width="1200px" height="600px"', 'width="310px" height="300px"')
    mark = svg_png(mark_svg, 620)
    return word, mark.crop(mark.getbbox())


def background():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - 540) / 820) ** 2 + ((yy - 860) / 1150) ** 2)
    k = np.clip(d, 0, 1)[..., None] ** 1.3
    img = np.array(BG_IN, np.float32) * (1 - k) + np.array(BG_OUT, np.float32) * k
    img += np.random.default_rng(3).normal(0, 1.2, img.shape)          # a little grain against banding
    return np.clip(img, 0, 255)


def two_lines(text, f):
    """Two lines (one for a single word), split where the longer line is shortest."""
    words = text.split()
    if len(words) < 2:
        return [text]
    splits = [(" ".join(words[:i]), " ".join(words[i:])) for i in range(1, len(words))]
    return list(min(splits, key=lambda p: max(f.getlength(p[0]), f.getlength(p[1]))))


def fit_size(text):
    """Largest size at which the text fits in two lines of TEXT_W."""
    for size in range(132, 60, -2):
        f = font("InterDisplay-Black.ttf", size)
        if max(f.getlength(s) for s in two_lines(text, f)) <= TEXT_W:
            return size
    return 60


def text_layer(text, color, size, shadow=False):
    """Big centred text, two balanced lines when needed, as an RGBA layer."""
    f = font("InterDisplay-Black.ttf", size)
    lines = two_lines(text, f)
    lh = int(size * 1.0)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    top = TEXT_Y - lh * len(lines) // 2
    for i, s in enumerate(lines):
        x = (W - f.getlength(s)) / 2
        d.text((x, top + i * lh - size * 0.12), s, font=f, fill=color + (255,))
    if shadow:
        a = layer.split()[3].filter(ImageFilter.GaussianBlur(10))
        sh = Image.new("RGBA", (W, H), (4, 40, 56, 0))
        sh.putalpha(a.point(lambda v: int(v * 0.35)))
        layer = Image.alpha_composite(sh, layer)
    return np.asarray(layer, np.float32) / 255.0


def static_layer(word, tagline, site):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    wm = word.resize((360, int(word.height * 360 / word.width)), Image.LANCZOS)
    a = wm.split()[3].point(lambda v: int(v * 0.92))
    wm.putalpha(a)
    layer.alpha_composite(wm, ((W - wm.width) // 2, 262))
    d = ImageDraw.Draw(layer)
    f = font("InterDisplay-ExtraBold.ttf", 30)
    spaced = tagline
    tw = sum(f.getlength(c) for c in spaced) + 5 * (len(spaced) - 1)
    x = (W - tw) / 2
    for c in spaced:
        d.text((x, 1318), c, font=f, fill=(255, 255, 255, 225))
        x += f.getlength(c) + 5
    f2 = font("Inter-Medium.otf", 28)
    d.text(((W - f2.getlength(site)) / 2, 1366), site, font=f2, fill=(255, 255, 255, 170))
    return layer


def pendulum_sprite(mark):
    """Cord + tag hanging straight down; the pivot is at (cx, 0)."""
    length = REST_Y - PIVOT[1] - TAG_SIZE / 2
    sw, sh = TAG_SIZE + 120, int(length + TAG_SIZE + 120)
    cx = sw // 2
    s = 3                                                     # draw 3x, downsample: smooth edges
    big = Image.new("RGBA", (sw * s, sh * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    d.line([(cx * s, 0), (cx * s, (length + 14) * s)], fill=CORD + (255,), width=6 * s)
    tx, ty = cx - TAG_SIZE / 2, length
    shadow = Image.new("RGBA", big.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([(tx + 14) * s, (ty + 20) * s, (tx + TAG_SIZE + 14) * s, (ty + TAG_SIZE + 20) * s],
                                             radius=46 * s, fill=(0, 20, 30, 120))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14 * s))
    big = Image.alpha_composite(shadow, big)
    d = ImageDraw.Draw(big)
    d.rounded_rectangle([tx * s, ty * s, (tx + TAG_SIZE) * s, (ty + TAG_SIZE) * s], radius=46 * s, fill=TAG + (255,),
                        outline=(40, 58, 70, 255), width=2 * s)
    d.ellipse([(cx - 9) * s, (ty + 12) * s, (cx + 9) * s, (ty + 30) * s], fill=(30, 44, 54, 255))    # the hole
    m = mark.resize((int(128 * s), int(128 * s * mark.height / mark.width)), Image.LANCZOS)
    big.alpha_composite(m, (int((cx - 64) * s - 6 * s), int((ty + TAG_SIZE / 2) * s - m.height / 2 + 8 * s)))
    sprite = big.resize((sw, sh), Image.LANCZOS)
    return sprite, (cx, 0)


def angle(t):
    """Swing angle (radians, + = to the right). Left extreme at t=0, right at t=HALF."""
    tmax = math.asin(AMP_X / (REST_Y - PIVOT[1]))
    return -tmax * math.cos(math.pi * t / HALF)


def pendulum_box(t0, t1):
    """Screen box that holds the cord and the tag for every angle between t0 and t1."""
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
    # screen (x, y) -> sprite (u, v) = anchor + R(-theta) * ((x, y) - pivot)
    a, b, d, e = c, -s_, s_, c
    cc = anchor[0] - a * px - b * py
    ff = anchor[1] - d * px - e * py
    img = sprite.transform((x1 - x0, y1 - y0), Image.AFFINE, (a, b, cc, d, e, ff), resample=Image.BICUBIC)
    arr = np.asarray(img, np.float32) / 255.0
    arr[..., :3] *= arr[..., 3:4]
    return arr


def states(spec):
    seq = []
    for q in spec["questions"]:
        seq += [("q", q), ("a", spec["answer"])]
    return seq


def frame(t, spec, assets):
    bg, static, layers, sprite, anchor = assets
    seq = states(spec)
    total = HALF * len(seq)
    t = t % total
    k = int(t // HALF)
    old, new = layers[seq[k]], layers[seq[(k + 1) % len(seq)]]
    theta = angle(t)
    out = bg.copy()
    # the big text: where the cord line has already swept, the next text shows
    y0, y1 = TEXT_BAND
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
    layers = {}
    size = min(fit_size(text) for _, text in states(spec))          # one size for every text, like a title card
    for kind, text in states(spec):
        if (kind, text) not in layers:
            layers[(kind, text)] = text_layer(text, INK if kind == "q" else WHITE, size, shadow=kind == "a")
    static = np.asarray(static_layer(word, spec["tagline"], spec["site"]), np.float32) / 255.0
    sprite, anchor = pendulum_sprite(mark)
    return background(), static, layers, sprite, anchor


def soundtrack(spec, total):
    """Night-drive bed at the swing's tempo (2 beats a swing) and a whoosh per sweep.
    The bed is rendered twice as long and the second half kept, so reverb tails run
    over the loop point and the clip loops without a click."""
    rng = np.random.default_rng(11)
    bpm = 60 / (HALF / 2)
    l, r = mr.night_drive(total * 2, rng, bpm=bpm)
    n = int(total * SR)
    l, r = l[n:2 * n], r[n:2 * n]
    fx_l, fx_r = np.zeros(n), np.zeros(n)
    for k in range(len(states(spec))):
        t = k * HALF + HALF / 2
        ln = int(0.62 * SR)
        x = np.arange(ln) / ln
        noise = rng.standard_normal(ln)
        sweep = np.convolve(noise, mr._fir(900 + 2600 * math.sin(math.pi * 0.5), 63), "same")
        body = np.convolve(noise, mr._fir(420, 127), "same")
        w = (sweep * 0.5 + body) * np.sin(np.pi * x) ** 2
        direction = 1 if k % 2 == 0 else -1
        pan = direction * (x - 0.5) * 1.2
        i0 = int((t - 0.31) * SR)
        for buf, sgn in ((fx_l, -1), (fx_r, 1)):
            seg = w * (1 + sgn * pan) * 0.5
            i = i0 % n
            end = min(n, i + ln)
            buf[i:end] += seg[: end - i]
            if end - i < ln:                                    # wraps round the loop point
                buf[: ln - (end - i)] += seg[end - i:]
    # whoosh about as loud as the music while it lasts: clearly there, not a jump scare
    bed_rms = np.sqrt(np.mean(l ** 2 + r ** 2) / 2)
    on = np.abs(fx_l) + np.abs(fx_r) > 1e-4
    fx_rms = np.sqrt(np.mean((fx_l[on] ** 2 + fx_r[on] ** 2) / 2))
    g = 0.9 * bed_rms / max(fx_rms, 1e-9)
    mix = np.stack([l + fx_l * g, r + fx_r * g], axis=1)
    mix *= 0.9 / max(np.abs(mix).max(), 1e-6)
    return mix


def build(spec, out_path):
    assets = prepare(spec)
    total = HALF * len(states(spec))
    with tempfile.TemporaryDirectory() as tmp:
        wav = pathlib.Path(tmp) / "a.wav"
        mr.write_wav(wav, soundtrack(spec, total))
        cmd = [mr.ffmpeg_bin(), "-y", "-loglevel", "error",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
               "-i", str(wav), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "160k", "-ar", str(SR), "-shortest", "-movflags", "+faststart", str(out_path)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for f in range(int(round(total * FPS))):
            proc.stdin.write(frame(f / FPS, spec, assets).tobytes())
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg nie zbudował rolki")
    return out_path, total


def main():
    ap = argparse.ArgumentParser(description="Rolka z wahadłem PageHub.")
    ap.add_argument("spec", nargs="?")
    ap.add_argument("--out", required=True)
    ap.add_argument("--still", type=float)
    a = ap.parse_args()
    spec = dict(DEFAULT)
    if a.spec:
        spec.update(json.loads(pathlib.Path(a.spec).read_text(encoding="utf-8")))
    if a.still is not None:
        Image.fromarray(frame(a.still, spec, prepare(spec))).save(a.out)
        print(a.out)
        return
    path, total = build(spec, a.out)
    print(f"{path}  ({total:.1f} s)")


if __name__ == "__main__":
    main()
