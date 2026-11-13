"""Render the two 2D layers of the Blender POV Reel: the phone screen (texture)
and the captions/end card (transparent overlay).  python3 parts.py OUTDIR"""
import pathlib, sys
from playwright.sync_api import sync_playwright
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
FPS, TOTAL = 30, 7 * 4 * 60 / 122
out = pathlib.Path(sys.argv[1])
ONLY = sys.argv[2] if len(sys.argv) > 2 else ""
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for part, dsf, kw, ext in (("screen", 2, {"type": "jpeg", "quality": 95}, "jpg"),
                               ("overlay", 3, {"type": "png", "omit_background": True}, "png")):
        if ONLY and part != ONLY:
            continue
        (out / part).mkdir(parents=True, exist_ok=True)
        page = b.new_page(viewport={"width": 360, "height": 780 if part == "screen" else 640}, device_scale_factor=dsf)
        page.goto((HERE / "pov.html").as_uri() + f"?part={part}")
        page.evaluate(f"TOTAL={TOTAL}; document.fonts.ready"); page.wait_for_timeout(300)
        for f in range(round(TOTAL * FPS)):
            page.evaluate(f"render({f / FPS})")
            page.screenshot(path=str(out / part / f"{f + 1:04d}.{ext}"), **kw)
        page.close()
print("ok")
