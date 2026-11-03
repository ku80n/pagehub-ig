#!/usr/bin/env python3
"""
make_reel.py - turn a carousel's slides into a 9:16 Reel (MP4) for Instagram.

Each 1080x1350 slide is placed inside the Reels safe zone of a 1080x1920 frame
(the like/comment rail sits on the right, the caption at the bottom), shown
long enough to read it, and cross-faded into the next. A silent AAC track is
added because some upload paths reject video without audio.

Usage
  python3 make_reel.py weeks/2026-11-02/k1.json            # -> weeks/.../k1/reel.mp4
  python3 make_reel.py weeks/2026-11-02/k1.json --out x.mp4
"""

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFilter

W, H = 1080, 1920
WINDOW = (60, 60, 1020, 1290)         # the browser window inside a 1080x1350 slide
RADIUS = 28
SWIPE_HINT = (760, 1195, 1000, 1262)  # "przesuń ->" on the cover, pointless in a video
WIN_BG = (17, 22, 29)
SLIDE_W, SLIDE_H = 820, 1051          # window scaled into the Reels safe zone
SLIDE_X, SLIDE_Y = 70, 330            # left of the like/comment rail, above the caption
FADE = 0.4                            # cross-fade length in seconds
FPS = 30
BG = (11, 15, 20)
ACCENT = (28, 152, 195)


def ffmpeg_bin():
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        sys.exit("brak ffmpeg: zainstaluj ffmpeg albo pip install imageio-ffmpeg")


def words_on(slide):
    text = " ".join(str(slide.get(k, "")) for k in ("kicker", "title", "subtitle", "body", "button"))
    text += " " + " ".join(slide.get("items", []))
    return len(text.replace("*", "").split())


def duration(slide, first):
    """Long enough to read the slide once, short enough to keep the swipe tempo."""
    if first:
        return 2.5
    return max(2.4, min(3.4, 1.0 + 0.12 * words_on(slide)))


def background():
    """Dark ground with the same soft teal glow as the slides."""
    bg = Image.new("RGB", (W, H), BG)
    glow = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(glow)
    d.ellipse((560, -260, 1460, 640), fill=(18, 58, 74))
    d.ellipse((-420, 1380, 520, 2260), fill=(15, 42, 54))
    return Image.blend(bg, glow.filter(ImageFilter.GaussianBlur(160)), 0.9)


def frames(spec_path, tmp):
    spec = json.loads(pathlib.Path(spec_path).read_text(encoding="utf-8"))
    slide_dir = pathlib.Path(spec_path).with_suffix("")
    pngs = sorted(slide_dir.glob("[0-9][0-9].png"))
    if len(pngs) != len(spec["slides"]):
        sys.exit(f"{spec_path}: {len(pngs)} PNG zamiast {len(spec['slides'])}, najpierw render_carousel.py")
    base = background()
    out = []
    for i, (png, slide) in enumerate(zip(pngs, spec["slides"])):
        frame = base.copy()
        src = Image.open(png).convert("RGB")
        if i == 0:
            ImageDraw.Draw(src).rectangle(SWIPE_HINT, fill=WIN_BG)
        win = src.crop(WINDOW)
        mask = Image.new("L", win.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, win.width - 1, win.height - 1), RADIUS, fill=255)
        win = win.resize((SLIDE_W, SLIDE_H), Image.LANCZOS)
        mask = mask.resize((SLIDE_W, SLIDE_H), Image.LANCZOS)
        frame.paste(win, (SLIDE_X, SLIDE_Y), mask)
        # thin progress bar above the slide: where you are in the story
        d = ImageDraw.Draw(frame)
        y = SLIDE_Y - 44
        d.rounded_rectangle((SLIDE_X, y, SLIDE_X + SLIDE_W, y + 8), 4, fill=(36, 48, 64))
        d.rounded_rectangle((SLIDE_X, y, SLIDE_X + int(SLIDE_W * (i + 1) / len(pngs)), y + 8), 4, fill=ACCENT)
        f = tmp / f"f{i:02d}.png"
        frame.save(f)
        out.append((f, duration(slide, i == 0)))
    return out


def build(spec_path, out_path=None):
    out_path = pathlib.Path(out_path or pathlib.Path(spec_path).with_suffix("") / "reel.mp4")
    with tempfile.TemporaryDirectory() as t:
        items = frames(spec_path, pathlib.Path(t))
        cmd = [ffmpeg_bin(), "-y", "-loglevel", "error"]
        for f, dur in items:
            cmd += ["-loop", "1", "-framerate", str(FPS), "-t", f"{dur + FADE:.2f}", "-i", str(f)]
        cmd += ["-f", "lavfi", "-t", "300", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
        # chain of cross-fades: each one starts FADE before the previous clip ends
        parts, prev, offset = [], "[0:v]", 0.0
        for i in range(1, len(items)):
            offset += items[i - 1][1]
            label = f"[v{i}]"
            parts.append(f"{prev}[{i}:v]xfade=transition=fade:duration={FADE}:offset={offset:.2f}{label}")
            prev = label
        total = sum(d for _, d in items) + FADE
        parts.append(f"{prev}format=yuv420p[vout]")
        cmd += ["-filter_complex", ";".join(parts), "-map", "[vout]", "-map", f"{len(items)}:a",
                "-t", f"{total:.2f}", "-r", str(FPS),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-movflags", "+faststart", str(out_path)]
        subprocess.run(cmd, check=True)
    return out_path, total


def main():
    ap = argparse.ArgumentParser(description="Carousel slides -> 9:16 Reel MP4.")
    ap.add_argument("spec")
    ap.add_argument("--out")
    a = ap.parse_args()
    path, total = build(a.spec, a.out)
    print(f"{path}  ({total:.1f} s, {path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
