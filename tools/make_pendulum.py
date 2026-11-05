#!/usr/bin/env python3
"""
make_pendulum.py - the "wahadło" Reel: the PageHub tag hangs on a cord and swings
across the screen. Wherever the cord has passed, the big text changes: a problem
("NUMER NIE DZWONI?") and the answer ("OGARNIEMY TO.") take turns, one swing each.
No narrator. The last swing brings back the first question, so the clip loops
without a seam when Instagram plays it again.

The look is the carousels': near-black background with a soft teal glow, white
questions, the answer in the brand teal, a white tag with the PageHub logo, the
logo on top and the comment button ("Napisz TELEFON w komentarzu") at the bottom.
Sound: an upbeat club loop generated here (four-on-the-floor kick, claps, hats,
pumping chords, bass, arp) at the tempo of the swing, two beats per swing, and a
whoosh every time the cord sweeps over the text. Nothing to license.

Usage
  python3 tools/make_pendulum.py weeks/2026-11-02/wahadlo-k2.json --out /tmp/w.mp4
  python3 tools/make_pendulum.py spec.json --still 0.5 --out x.png

Spec
  {"questions": ["...?", ...], "answer": "OGARNIEMY TO.",
   "cta": "Napisz TELEFON w komentarzu", "site": "pagehub.pl"}
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
BPM = 110
HALF = 2 * 60 / BPM

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


def logo_images():
    """(logo for a dark background: white "page" and globe, teal "hub" and arc;
    the mark in its own colours for the white tag) - both from the site's SVG."""
    svg = LOGO.read_text(encoding="utf-8")
    dark = svg.replace('fill="#333333"', 'fill="#F0F4F8"')
    word = svg_png(dark, 1200)
    word = word.crop(word.getbbox())
    mark_svg = svg.replace('viewBox="0 0 1200 600"', 'viewBox="-4 150 310 300"').replace(
        'width="1200px" height="600px"', 'width="310px" height="300px"')
    mark = svg_png(mark_svg, 620)
    return word, mark.crop(mark.getbbox())


def background():
    """Near-black with a soft teal glow behind the text and in two corners."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    img = np.tile(np.array(BG, np.float32), (H, W, 1))
    for cx, cy, rx, ry, k in ((540, 820, 620, 520, 0.20), (1080, 0, 700, 600, 0.16), (0, 1920, 700, 650, 0.12)):
        g = np.exp(-(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2) * 1.6)[..., None] * k
        img = img * (1 - g) + np.array(GLOW, np.float32) * g
    img += np.random.default_rng(3).normal(0, 1.0, img.shape)        # a little grain against banding
    return np.clip(img, 0, 255)


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

    def cost(p):
        bad = p[0].split()[-1].lower() in NO_LINE_END
        return max(f.getlength(p[0]), f.getlength(p[1])) + (10000 if bad else 0)
    return list(min(splits, key=cost))


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


def static_layer(word, cta, site):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    wm = word.resize((380, int(word.height * 380 / word.width)), Image.LANCZOS)
    layer.alpha_composite(wm, ((W - wm.width) // 2, 262))
    d = ImageDraw.Draw(layer)
    if cta:                                                       # the comment button, as in the other Reels
        f = font("Inter-Bold.otf", 38)
        tw = f.getlength(cta)
        bw, bh = tw + 76, 92
        x0, y0 = (W - bw) / 2, 1282
        d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], radius=bh / 2, fill=ACCENT + (255,))
        d.text((x0 + 38, y0 + 21), cta, font=f, fill=INK + (255,))
    f2 = font("Inter-Medium.otf", 28)
    d.text(((W - f2.getlength(site)) / 2, 1398), site, font=f2, fill=FG + (150,))
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


def states(spec):
    seq = []
    for q in spec["questions"]:
        seq += [("q", q), ("a", spec["answer"])]
    return seq


def frame(t, spec, assets):
    bg, static, layers, sprite, anchor = assets
    seq = states(spec)
    t = t % (HALF * len(seq))
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
    size = min(fit_size(text) for _, text in states(spec))     # one size for every text, like a title card
    layers = {}
    for kind, text in states(spec):
        if (kind, text) not in layers:
            layers[(kind, text)] = text_layer(text, FG if kind == "q" else ACCENT, size, glow=kind == "a")
    static = np.asarray(static_layer(word, spec.get("cta", ""), spec["site"]), np.float32) / 255.0
    sprite, anchor = pendulum_sprite(mark)
    return background(), static, layers, sprite, anchor


# ---------------------------------------------------------------- music

def _hz(m):
    return 440 * 2 ** ((m - 69) / 12)


def _hp(x, cut, taps=63):
    return x - np.convolve(x, mr._fir(cut, taps), "same")


def club_bed(bars, rng, bpm=BPM):
    """An upbeat club loop, `bars` bars long and periodic: four-on-the-floor kick,
    claps on 2 and 4, 16th hats with open hats on the off-beats, an off-beat bass,
    wide chords pumping under the kick, a plucky 16th arp, a clap roll into the
    loop point. One chord per bar, so the loop closes on the dominant (E -> Am).
    Stereo (L, R)."""
    beat = 60 / bpm
    bar = 4 * beat
    total = bars * bar
    n = int((2 * total + 1.0) * SR)                        # rendered twice, the second copy is kept
    prog = [(57, [57, 60, 64, 69]), (53, [53, 57, 60, 65]), (48, [55, 60, 64, 67]), (55, [55, 59, 62, 67]),
            (52, [56, 59, 64, 68])]
    prog = (prog * 4)[:bars] if bars != 5 else prog
    kick_b, clap_b, hat_b, bass_b, arp_b = (np.zeros(n) for _ in range(5))
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
        # off-beat bass, octave jump on the last one
        ln = int(beat * 0.42 * SR)
        env = mr._env(ln, 0.003, 0.12)
        for q in range(4):
            note = root - 24 + (12 if q == 3 else 0)
            tone = np.convolve(saw(_hz(note), ln, 8), mr._fir(700, 63), "same")
            mr._put(bass_b, (tone + 0.6 * np.sin(2 * np.pi * _hz(note) * np.arange(ln) / SR)) * env, t_bar + (q + 0.5) * beat)
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
        if b % bars == bars - 1:                                  # clap roll into the loop point
            for r in range(8):
                mr._put(clap_b, clap * (0.25 + 0.09 * r), t_bar + 2 * beat + r * beat / 4)
        t_bar += bar
        b += 1

    # pump: everything but the drums ducks under each kick
    tt = np.arange(n) / SR
    since = np.mod(tt, beat)
    pump = 1 - 0.72 * np.exp(-since / 0.11)
    pad_l = np.convolve(pad_l, mr._fir(2600), "same") * pump
    pad_r = np.convolve(pad_r, mr._fir(2600), "same") * pump
    bass_b *= 0.6 + 0.4 * pump
    arp_b = np.convolve(arp_b, mr._fir(5000), "same") * (0.5 + 0.5 * pump)
    # a short room on claps and arp
    ir_len = int(0.9 * SR)
    irs = [np.convolve(rng.standard_normal(ir_len) * np.exp(-np.arange(ir_len) / SR / 0.25), mr._fir(6000, 63), "same")
           for _ in range(2)]
    irs = [ir / np.sqrt((ir ** 2).sum()) for ir in irs]
    wet_l = mr._fftconv(clap_b * 0.5 + arp_b * 0.6, irs[0])
    wet_r = mr._fftconv(clap_b * 0.5 + arp_b * 0.6, irs[1])
    drums = kick_b * 0.8 + clap_b * 0.55 + hat_b * 0.34
    left = drums + bass_b * 0.42 + pad_l * 0.36 + arp_b * 0.32 + wet_l * 0.12
    right = drums + bass_b * 0.42 + pad_r * 0.36 + arp_b * 0.24 + wet_r * 0.12
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
