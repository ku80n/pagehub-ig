"""Compose the Blender POV Reel: upscale the CG frames (rendered every STEP-th
frame; the ones between are re-aimed with the phone's own homography), put the
sharp phone screen into its place, add captions/end card and the sound.

  python3 compose.py WORKDIR out.mp4 [--still N out.png]
"""
import json, pathlib, subprocess, sys, tempfile
import cv2, numpy as np
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
W, H, FPS, STEP = 1080, 1920, 30, 4
work = pathlib.Path(sys.argv[1])
corners = {int(k): (np.float32(v) * (W, H)).astype(np.float32) for k, v in json.loads((work / "corners.json").read_text()).items()}
N = len(corners)
SW, SH, R = 720, 1560, 110
src = np.float32([[0, 0], [SW, 0], [SW, SH], [0, SH]])
mask0 = np.zeros((SH, SW), np.float32)
cv2.rectangle(mask0, (R, 0), (SW - R, SH), 1, -1); cv2.rectangle(mask0, (0, R), (SW, SH - R), 1, -1)
for c in ((R, R), (SW - R, R), (R, SH - R), (SW - R, SH - R)):
    cv2.circle(mask0, c, R, 1, -1, cv2.LINE_AA)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - 0.42 * np.clip(((xx / W - 0.5) ** 2 + (yy / H - 0.5) ** 2) / 0.5, 0, 1) ** 1.3)[..., None]
rng = np.random.default_rng(3)


def frame(f):
    k = 1 + STEP * ((f - 1) // STEP)
    cg = cv2.imread(str(work / f"cg{k:04d}.png"))
    cg = cv2.resize(cg, (W, H), interpolation=cv2.INTER_CUBIC)
    if k != f:                                             # same render, re-aimed to this frame's camera
        cg = cv2.warpPerspective(cg, cv2.getPerspectiveTransform(corners[k], corners[f]), (W, H),
                                 flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    M = cv2.getPerspectiveTransform(src, corners[f])
    scr = cv2.imread(str(work / "screen" / f"{f:04d}.jpg"))
    warped = cv2.warpPerspective(scr, M, (W, H), flags=cv2.INTER_AREA).astype(np.float32)
    m = cv2.GaussianBlur(cv2.warpPerspective(mask0, M, (W, H), flags=cv2.INTER_LINEAR), (0, 0), 1.2)[..., None]
    out = cg.astype(np.float32)
    warped = cv2.GaussianBlur(warped, (0, 0), 0.7)          # as soft as the lens, not pasted-on sharp
    lit = 255 * (1 - (1 - warped * 0.97 / 255) * (1 - np.clip(out, 0, 255) * 0.75 / 255))   # screen under the glass reflections
    out = out * (1 - m) + lit * m
    glow = cv2.GaussianBlur(np.clip(out - 185, 0, 255), (0, 0), 22)
    out = (out + glow * 0.45) * VIG
    out += cv2.GaussianBlur(rng.standard_normal((H, W, 1)).astype(np.float32), (0, 0), 0.6)[..., None] * 5.0   # film grain
    t = (f - 1) / FPS
    if t > 10.7:
        s = min(1, (t - 10.7) / 0.5)
        out = cv2.GaussianBlur(out, (0, 0), 0.1 + 14 * s) * (1 - 0.35 * s)
    ov = cv2.imread(str(work / "overlay" / f"{f:04d}.png"), cv2.IMREAD_UNCHANGED).astype(np.float32)
    a = ov[..., 3:] / 255
    out = out * (1 - a) + ov[..., :3] * a
    return np.clip(out, 0, 255).astype(np.uint8)


if "--still" in sys.argv:
    i = sys.argv.index("--still")
    cv2.imwrite(sys.argv[i + 2], frame(int(sys.argv[i + 1])))
    sys.exit()
import make_reel as mr, make_pov          # noqa: E402
with tempfile.TemporaryDirectory() as tmp:
    wav = pathlib.Path(tmp) / "a.wav"
    mr.write_wav(wav, make_pov.sound())
    cmd = [mr.ffmpeg_bin(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", str(wav), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", sys.argv[2]]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(1, N + 1):
        p.stdin.write(frame(f).tobytes())
    p.stdin.close(); p.wait()
print(sys.argv[2])
