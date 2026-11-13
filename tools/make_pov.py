#!/usr/bin/env python3
"""
make_pov.py - the "reality" Reel: a phone screen recording, staged in HTML
(tools/pov/pov.html). A client looks for a barber in the evening, the first site
loads slowly and is unreadable on a phone, the second one shows everything at
once and ends in a call. The businesses are invented examples.
No people, no real footage: every frame is rendered here.

  python3 tools/make_pov.py --out x.mp4
  python3 tools/make_pov.py --still 5.5 --out x.png
"""
import argparse, pathlib, subprocess, sys, tempfile
import numpy as np
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import make_reel as mr          # noqa: E402
import make_pendulum as mp      # noqa: E402

FPS, SR, BARS = 30, 48000, 7
TOTAL = BARS * 4 * 60 / mp.BPM
TAPS = (2.55, 6.15, 7.05, 9.35)
TYPE = (0.3, 1.5, 15)           # typing: from, to, keys
PING = 11.7


def sound():
    rng = np.random.default_rng(5)
    l, r = mp.club_bed(BARS, rng)
    n = len(l)
    t = np.arange(n) / SR
    duck = 0.42 + 0.58 * np.clip((t - 10.6) / 0.6, 0, 1) * np.clip((TOTAL - t) / 0.4, 0.45, 1)   # quiet under the "recording"
    mix = np.stack([l * duck, r * duck], axis=1)
    rms = np.sqrt(np.mean(l ** 2 + r ** 2) / 2)

    def add(at, sig, gain):
        i = int(at * SR)
        seg = sig[: max(0, n - i)] * gain * rms
        mix[i:i + len(seg)] += seg[:, None]

    k = np.arange(int(0.05 * SR)) / SR
    key = np.sin(2 * np.pi * 1900 * k) * np.exp(-k / 0.006) + rng.standard_normal(len(k)) * np.exp(-k / 0.003) * 0.5
    for i in range(TYPE[2]):
        add(TYPE[0] + (TYPE[1] - TYPE[0]) * i / TYPE[2], key, 1.1 + 0.3 * rng.random())
    k = np.arange(int(0.09 * SR)) / SR
    tap = np.sin(2 * np.pi * (240 - 900 * k) * k) * np.exp(-k / 0.018) + rng.standard_normal(len(k)) * np.exp(-k / 0.004) * 0.4
    for at in TAPS:
        add(at, tap, 3.2)
    k = np.arange(int(1.2 * SR)) / SR                              # ringing tone while it dials
    add(9.75, np.sin(2 * np.pi * 425 * k) * mr._env(len(k), 0.02, 0.15), 1.3)
    k = np.arange(SR) / SR
    f0 = 440 * 2 ** ((88 - 69) / 12)
    ding = (np.sin(2 * np.pi * f0 * k) + 0.4 * np.sin(2 * np.pi * 2 * f0 * k) * np.exp(-k / 0.1)) * mr._env(len(k), 0.002, 0.35)
    for d, g in ((0, 1.0), (0.2, 0.42), (0.4, 0.2)):
        add(PING + d, ding, 2.4 * g)
    mix = np.tanh(mix / np.abs(mix).max() * 1.3) / np.tanh(1.3)
    return mix * 0.8


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--still", type=float)
    ap.add_argument("--cine", action="store_true", help="phone in a 3D scene with a handheld camera")
    a = ap.parse_args()
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        page = b.new_page(viewport={"width": 360, "height": 640}, device_scale_factor=3)
        page.goto((ROOT / "tools" / "pov" / "pov.html").as_uri() + ("?cine=1" if a.cine else ""))
        page.evaluate(f"TOTAL={TOTAL}; document.fonts.ready")
        page.wait_for_timeout(300)
        if a.still is not None:
            page.evaluate(f"render({a.still})")
            page.screenshot(path=a.out)
            return
        with tempfile.TemporaryDirectory() as tmp:
            wav = pathlib.Path(tmp) / "a.wav"
            mr.write_wav(wav, sound())
            cmd = [mr.ffmpeg_bin(), "-y", "-loglevel", "error", "-f", "image2pipe", "-c:v", "mjpeg", "-r", str(FPS), "-i", "-",
                   "-i", str(wav), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                   "-c:a", "aac", "-b:a", "192k", "-ar", str(SR), "-shortest", "-movflags", "+faststart", a.out]
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            for f in range(int(round(TOTAL * FPS))):
                page.evaluate(f"render({f / FPS})")
                proc.stdin.write(page.screenshot(type="jpeg", quality=95))
            proc.stdin.close()
            if proc.wait() != 0:
                raise RuntimeError("ffmpeg")
        print(a.out, f"({TOTAL:.1f} s)")


if __name__ == "__main__":
    main()
