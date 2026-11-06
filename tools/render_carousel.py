#!/usr/bin/env python3
"""
render_carousel.py - turn a carousel spec (JSON) into 1080x1350 PNG slides
in the PageHub style: a dark browser window, teal accent, monospace headlines.

Usage
  python3 render_carousel.py weeks/2026-11-03/karuzela-1.json
  python3 render_carousel.py spec.json --out some/dir

Spec
  {
    "handle": "pagehub.pl",          # shown in the address bar
    "ig": "@pagehub.pl",             # shown in the footer of every slide
    "slides": [
      {"type": "cover", "kicker": "wydajność", "title": "Strona, która *ucieka* klientom",
       "subtitle": "5 rzeczy do sprawdzenia w 10 minut"},
      {"type": "text",  "title": "...", "body": "..."},
      {"type": "list",  "title": "...", "items": ["...", "..."]},
      {"type": "cta",   "title": "...", "body": "..."},
      {"type": "palette", "kicker": "warsztat samochodowy", "title": "Grafit i *pomarańcz*",
       "palette": {"bg": "#F2F3F5", "text": "#1D2126", "main": "#3E4A56", "accent": "#E4570F",
                   "names": {"bg": "jasna stal", "text": "grafit", "main": "stal", "accent": "pomarańcz"}},
       "mock": {"headline": "Serwis i naprawa aut", "line": "Przeglądy, hamulce, opony", "button": "Zadzwoń"},
       "note": "Kojarzy się z techniką i porządkiem."}
    ]
  }

A "palette" slide shows a small website in those colours, the four swatches
with their codes and the measured contrast (WCAG): text on background and the
button text on the accent. The contrast is computed here, never typed by hand.

Wrap a word in *asterisks* to colour it with the accent. Text is shrunk to fit,
never cut, and the script fails loudly if a slide still overflows.
"""

import argparse
import html
import json
import pathlib
import re
import sys

ACCENT = "#1C98C3"
CHROME = "/usr/bin/google-chrome"
W, H = 1080, 1350

CSS = f"""
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: {W}px; height: {H}px; }}
body {{
  background: #0B0F14;
  background-image: radial-gradient(circle at 85% 8%, rgba(28,152,195,.18), transparent 45%),
                    radial-gradient(circle at 10% 95%, rgba(28,152,195,.10), transparent 40%);
  font-family: "Inter", "DejaVu Sans", sans-serif;
  color: #E6EDF3;
  display: flex; align-items: center; justify-content: center;
}}
.win {{
  width: 960px; height: 1230px;
  background: #11161D;
  border: 1px solid #243040;
  border-radius: 28px;
  box-shadow: 0 30px 80px rgba(0,0,0,.55);
  display: flex; flex-direction: column; overflow: hidden;
}}
.bar {{
  height: 84px; flex: none;
  background: #161D26; border-bottom: 1px solid #243040;
  display: flex; align-items: center; gap: 14px; padding: 0 32px;
}}
.dot {{ width: 18px; height: 18px; border-radius: 50%; background: #2B3746; }}
.dot.a {{ background: {ACCENT}; }}
.url {{
  flex: 1; margin-left: 18px; height: 46px; border-radius: 23px;
  background: #0E131A; border: 1px solid #243040;
  font: 500 24px "DejaVu Sans Mono", monospace; color: #8B98A8;
  display: flex; align-items: center; padding: 0 24px;
}}
.url b {{ color: #E6EDF3; font-weight: 500; }}
.count {{ font: 700 26px "DejaVu Sans Mono", monospace; color: {ACCENT}; min-width: 70px; text-align: right; }}
.body {{
  flex: 1; position: relative;
  padding: 90px 84px 120px 84px;
  display: flex; flex-direction: column; justify-content: center;
}}
.gutter {{
  position: absolute; left: 30px; top: 90px;
  font: 400 20px/1.9 "DejaVu Sans Mono", monospace; color: #2B3746;
  overflow: hidden; white-space: pre;
}}
.fit {{ overflow: hidden; display: flex; flex-direction: column; justify-content: center; height: 100%; }}
.kicker {{ font: 700 30px "DejaVu Sans Mono", monospace; color: {ACCENT}; margin-bottom: 34px; letter-spacing: .5px; }}
.title {{ font-family: "DejaVu Sans Mono", monospace; font-weight: 700; line-height: 1.12; letter-spacing: -1px; }}
.cover .title {{ font-size: 96px; }}
.text .title, .list .title, .cta .title {{ font-size: 68px; margin-bottom: 44px; }}
.subtitle {{ font-size: 40px; line-height: 1.35; color: #A9B4C2; margin-top: 44px; }}
.para {{ font-size: 44px; line-height: 1.45; color: #C9D3DE; }}
.para + .para {{ margin-top: 28px; }}
ul {{ list-style: none; }}
li {{ font-size: 42px; line-height: 1.35; color: #C9D3DE; padding-left: 62px; position: relative; }}
li + li {{ margin-top: 30px; }}
li::before {{
  content: attr(data-n); position: absolute; left: 0; top: 4px;
  font: 700 30px "DejaVu Sans Mono", monospace; color: {ACCENT};
}}
em {{ font-style: normal; color: {ACCENT}; }}
.foot {{
  position: absolute; left: 84px; right: 84px; bottom: 48px;
  display: flex; justify-content: space-between; align-items: center;
  font: 500 26px "DejaVu Sans Mono", monospace; color: #6B7888;
}}
.foot .swipe {{ color: {ACCENT}; }}
.mock {{
  border-radius: 22px; overflow: hidden; border: 1px solid #243040; margin: 6px 0 34px;
  padding: 26px 34px 34px; display: flex; flex-direction: column; gap: 16px; flex: none;
}}
.mock .nav {{ display: flex; align-items: center; gap: 14px; font: 600 22px "Inter", "DejaVu Sans", sans-serif; }}
.mock .logo {{ width: 30px; height: 30px; border-radius: 8px; }}
.mock .links {{ margin-left: auto; display: flex; gap: 18px; opacity: .55; }}
.mock .links span {{ width: 64px; height: 8px; border-radius: 4px; }}
.mock .h {{ font: 800 50px/1.1 "Inter", "DejaVu Sans", sans-serif; letter-spacing: -1px; margin-top: 14px; }}
.mock .l {{ font: 400 26px "Inter", "DejaVu Sans", sans-serif; opacity: .85; }}
.mock .row {{ display: flex; align-items: center; gap: 18px; margin-top: 8px; }}
.mock .btn {{ font: 700 26px "Inter", "DejaVu Sans", sans-serif; border-radius: 12px; padding: 14px 26px; }}
.mock .ghost {{ width: 150px; height: 52px; border-radius: 12px; }}
.sw {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; flex: none; }}
.sw .c {{ height: 104px; border-radius: 16px; border: 1px solid #2B3746; }}
.sw .r {{ font: 500 20px "DejaVu Sans Mono", monospace; color: #6B7888; margin-top: 12px; }}
.sw .x {{ font: 700 26px "DejaVu Sans Mono", monospace; color: #E6EDF3; margin-top: 4px; }}
.sw .n {{ font: 400 22px "Inter", "DejaVu Sans", sans-serif; color: #A9B4C2; margin-top: 2px; }}
.palette .title {{ font-size: 62px; margin-bottom: 30px; }}
.palette .para {{ font-size: 32px; margin-top: 30px; }}
.ratio {{ font: 500 22px "DejaVu Sans Mono", monospace; color: #6B7888; margin-top: 16px; }}
.ratio b {{ color: {ACCENT}; font-weight: 700; }}
.cta .button {{
  align-self: flex-start; margin-top: 56px;
  font: 700 38px "DejaVu Sans Mono", monospace; color: #0B0F14;
  background: {ACCENT}; border-radius: 18px; padding: 26px 40px;
}}
"""

FIT_JS = """
() => {
  const box = document.querySelector('.fit');
  const nodes = [...box.querySelectorAll('.title, .subtitle, .para, li, .kicker, .button')];
  const base = nodes.map(n => parseFloat(getComputedStyle(n).fontSize));
  let k = 1.0;
  while (box.scrollHeight > box.clientHeight + 1 && k > 0.55) {
    k -= 0.03;
    nodes.forEach((n, i) => n.style.fontSize = (base[i] * k) + 'px');
  }
  return {scale: k, overflow: box.scrollHeight > box.clientHeight + 1};
}
"""


def rich(text):
    """Escape, then turn *word* into the accent colour and newlines into breaks."""
    t = html.escape(text.strip())
    t = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", t)
    return t.replace("\n", "<br>")


def _lum(hex_):
    c = [int(hex_.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    """WCAG contrast ratio of two #RRGGBB colours."""
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def button_ink(pal):
    """Text colour for the accent button: the more readable of white and near-black."""
    return max(("#FFFFFF", "#111111"), key=lambda c: contrast(c, pal["accent"]))


def ratio(x):
    return f"{x:.1f}".replace(".", ",") + ":1"


ROLES = (("bg", "tło"), ("text", "tekst"), ("main", "główny"), ("accent", "akcent"))


def palette_html(slide):
    pal, mock = slide["palette"], slide.get("mock", {})
    names, ink = pal.get("names", {}), button_ink(pal)
    e = html.escape
    site = (f'<div class="mock" style="background:{pal["bg"]};color:{pal["text"]}">'
            f'<div class="nav"><span class="logo" style="background:{pal["main"]}"></span>Twoja firma'
            f'<div class="links">' + f'<span style="background:{pal["text"]}"></span>' * 3 + '</div></div>'
            f'<div class="h">{e(mock.get("headline", "Twoja strona"))}</div>'
            f'<div class="l">{e(mock.get("line", ""))}</div>'
            f'<div class="row"><span class="btn" style="background:{pal["accent"]};color:{ink}">'
            f'{e(mock.get("button", "Zadzwoń"))}</span>'
            f'<span class="ghost" style="border:3px solid {pal["main"]}"></span></div></div>')
    cells = "".join(f'<div><div class="c" style="background:{pal[k]}"></div><div class="r">{label}</div>'
                    f'<div class="x">{pal[k].upper()}</div><div class="n">{e(names.get(k, ""))}</div></div>'
                    for k, label in ROLES)
    meas = (f'<div class="ratio">kontrast tekstu <b>{ratio(contrast(pal["text"], pal["bg"]))}</b>, '
            f'przycisku <b>{ratio(contrast(ink, pal["accent"]))}</b> (WCAG AA od 4,5:1)</div>')
    return site + f'<div class="sw">{cells}</div>' + meas


def gutter(n=24):
    return "\n".join(f"{i:>2}" for i in range(1, n + 1))


def slide_html(slide, idx, total, handle, ig):
    kind = slide.get("type", "text")
    path = slide.get("path") or ("" if kind == "cover" else f"/{idx:02d}")
    parts = []
    if slide.get("kicker"):
        parts.append(f'<div class="kicker">// {rich(slide["kicker"])}</div>')
    if slide.get("title"):
        parts.append(f'<div class="title">{rich(slide["title"])}</div>')
    if kind == "cover" and slide.get("subtitle"):
        parts.append(f'<div class="subtitle">{rich(slide["subtitle"])}</div>')
    if kind in ("text", "cta") and slide.get("body"):
        for para in [p for p in slide["body"].split("\n\n") if p.strip()]:
            parts.append(f'<div class="para">{rich(para)}</div>')
    if kind == "list":
        items = "".join(f'<li data-n="{i:02d}">{rich(it)}</li>'
                        for i, it in enumerate(slide.get("items", []), 1))
        parts.append(f"<ul>{items}</ul>")
    if kind == "cta" and slide.get("button"):
        parts.append(f'<div class="button">{rich(slide["button"])}</div>')
    if kind == "palette":
        parts.append(palette_html(slide))
        if slide.get("note"):
            parts.append(f'<div class="para">{rich(slide["note"])}</div>')
    swipe = '<span class="swipe">przesuń &rarr;</span>' if idx == 1 and total > 1 else "<span></span>"
    return f"""<!doctype html><html lang="pl"><head><meta charset="utf-8">
<style>{CSS}</style></head><body>
<div class="win {kind}">
  <div class="bar">
    <span class="dot a"></span><span class="dot"></span><span class="dot"></span>
    <div class="url"><b>{html.escape(handle)}</b>{html.escape(path)}</div>
    <div class="count">{idx}/{total}</div>
  </div>
  <div class="body">
    <div class="gutter">{gutter()}</div>
    <div class="fit">{''.join(parts)}</div>
    <div class="foot"><span>{html.escape(ig)}</span>{swipe}</div>
  </div>
</div></body></html>"""


def render(spec_path, out_dir=None):
    from playwright.sync_api import sync_playwright

    spec_path = pathlib.Path(spec_path)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    handle = spec.get("handle", "pagehub.pl")
    ig = spec.get("ig", handle)
    slides = spec["slides"]
    out = pathlib.Path(out_dir) if out_dir else spec_path.with_suffix("")
    out.mkdir(parents=True, exist_ok=True)
    problems, files = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        for i, slide in enumerate(slides, 1):
            page.set_content(slide_html(slide, i, len(slides), handle, ig), wait_until="load")
            page.evaluate("document.fonts.ready")
            fit = page.evaluate(FIT_JS)
            pal = slide.get("palette")
            if pal:
                ink = button_ink(pal)
                for what, a, b in (("tekstu", pal["text"], pal["bg"]), ("przycisku", ink, pal["accent"])):
                    if contrast(a, b) < 4.5:
                        problems.append(f"slajd {i}: kontrast {what} {ratio(contrast(a, b))} jest poniżej 4,5:1, "
                                        "zmień kolory, nie pokazuj nieczytelnej palety")
            if fit["overflow"]:
                problems.append(f"slajd {i}: tekst się nie mieści nawet po zmniejszeniu, skróć go")
            elif fit["scale"] < 0.8:
                problems.append(f"slajd {i}: tekst zmniejszony do {fit['scale']:.0%}, rozważ skrócenie")
            f = out / f"{i:02d}.png"
            page.screenshot(path=str(f), full_page=False)
            files.append(str(f))
        browser.close()
    return files, problems


def main():
    ap = argparse.ArgumentParser(description="Render a carousel spec to PNG slides.")
    ap.add_argument("spec")
    ap.add_argument("--out")
    args = ap.parse_args()
    files, problems = render(args.spec, args.out)
    print(f"{len(files)} slajdów -> {pathlib.Path(files[0]).parent}")
    for pr in problems:
        print("  UWAGA", pr)
    sys.exit(1 if any("nie mieści" in p or "kontrast" in p for p in problems) else 0)


if __name__ == "__main__":
    main()
