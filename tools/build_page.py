#!/usr/bin/env python3
"""
build_page.py - build the weekly review page from a week folder.

Reads weeks/RRRR-MM-DD/k*.json (rendered slides in k*/NN.png next to each
spec) and writes index.html plus files.json, the map the Artifact publish
call takes as `files`.

Usage
  python3 tools/build_page.py weeks/2026-11-02
"""

import html
import json
import pathlib
import sys
from datetime import date, timedelta

MONTHS = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca",
          "sierpnia", "września", "października", "listopada", "grudnia"]


def week_label(monday):
    d0 = date.fromisoformat(monday)
    d1 = d0 + timedelta(days=6)
    if d0.month == d1.month:
        return f"{d0.day}-{d1.day} {MONTHS[d1.month - 1]} {d1.year}"
    return f"{d0.day} {MONTHS[d0.month - 1]} - {d1.day} {MONTHS[d1.month - 1]} {d1.year}"


def esc(t):
    return html.escape(t or "")


STYLE = """
<title>PageHub Instagram</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
/* layout: one column of posts in publishing order; each post = slide strip + two caption panes */
:root {
  --bg: #0B0F14; --panel: #121821; --line: #243040; --fg: #E6EDF3;
  --muted: #8B98A8; --accent: #1C98C3; --accent-ink: #0B0F14; --ok: #3FB68B;
  --display: "IBM Plex Mono", "DejaVu Sans Mono", ui-monospace, monospace;
  --body: "IBM Plex Sans", "Segoe UI", system-ui, sans-serif;
  color-scheme: dark;
}
@media (prefers-color-scheme: light) { :root:not([data-theme="dark"]) {
  --bg: #F3F6F8; --panel: #FFFFFF; --line: #D5DEE6; --fg: #0F1720;
  --muted: #5A6878; --accent: #13789C; --accent-ink: #FFFFFF; --ok: #1F8A63; color-scheme: light } }
:root[data-theme="light"] {
  --bg: #F3F6F8; --panel: #FFFFFF; --line: #D5DEE6; --fg: #0F1720;
  --muted: #5A6878; --accent: #13789C; --accent-ink: #FFFFFF; --ok: #1F8A63; color-scheme: light }
body { background: var(--bg); color: var(--fg); font: 16px/1.55 var(--body); }
.wrap { max-width: 1000px; margin: 0 auto; padding-block: 40px 72px;
  padding-left: max(16px, env(safe-area-inset-left, 0px));
  padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: flex; flex-direction: column; gap: 56px; }
header { display: flex; flex-direction: column; gap: 10px; }
.eyebrow { font: 500 13px var(--display); letter-spacing: .08em; text-transform: uppercase; color: var(--accent); }
h1 { font: 700 clamp(28px, 5vw, 40px)/1.15 var(--display); letter-spacing: -.02em; text-wrap: balance; margin: 0; }
.how { color: var(--muted); max-width: 62ch; margin: 0; }
.how b { color: var(--fg); font-weight: 600; }
article { display: flex; flex-direction: column; gap: 18px; }
.meta { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.chip { font: 500 13px var(--display); padding: 4px 10px; border-radius: 6px; border: 1px solid var(--line); color: var(--muted); }
.chip.when { background: var(--accent); border-color: var(--accent); color: var(--accent-ink); }
h2 { font: 700 clamp(20px, 3.4vw, 26px)/1.25 var(--display); margin: 0; text-wrap: balance; }
.strip { display: flex; gap: 12px; overflow-x: auto; scroll-snap-type: x mandatory; padding-bottom: 8px; }
.strip img { flex: none; width: min(300px, 72vw); aspect-ratio: 4 / 5; height: auto; max-width: 100%;
  border-radius: 10px; border: 1px solid var(--line); scroll-snap-align: start; background: #0B0F14; }
.hint { font-size: 13px; color: var(--muted); margin: -6px 0 0; }
.panes { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 380px), 1fr)); gap: 14px; }
.pane { background: var(--panel); border: 1px solid var(--line); border-radius: 12px;
  padding: 16px 18px; display: flex; flex-direction: column; gap: 10px; min-width: 0; }
.pane-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.pane-title { font: 500 13px var(--display); letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }
.copy { font: 600 14px var(--body); color: var(--accent-ink); background: var(--accent); border: 0;
  border-radius: 8px; padding: 7px 14px; cursor: pointer; }
.copy:focus-visible { outline: 2px solid var(--fg); outline-offset: 2px; }
.copy.done { background: var(--ok); }
.text { white-space: pre-wrap; overflow-wrap: anywhere; margin: 0; font: 15px/1.55 var(--body); }
.alt { font-size: 14px; color: var(--muted); }
.alt b { color: var(--fg); font-weight: 600; }
footer { color: var(--muted); font-size: 13px; border-top: 1px solid var(--line); padding-top: 18px; }
@media (prefers-reduced-motion: reduce) { .strip { scroll-behavior: auto; } }
</style>
"""

SCRIPT = """
<script>
document.addEventListener('click', async (e) => {
  const btn = e.target.closest('.copy');
  if (!btn) return;
  const src = document.getElementById(btn.dataset.target);
  const text = src.innerText;
  const done = () => { btn.textContent = 'Skopiowano'; btn.classList.add('done');
    setTimeout(() => { btn.textContent = 'Kopiuj'; btn.classList.remove('done'); }, 1800); };
  try { await navigator.clipboard.writeText(text); done(); }
  catch (_) {
    const r = document.createRange(); r.selectNodeContents(src);
    const s = getSelection(); s.removeAllRanges(); s.addRange(r);
    btn.textContent = 'Zaznaczono, skopiuj ręcznie';
  }
});
</script>
"""


def pane(pid, title, text):
    return f"""<div class="pane">
  <div class="pane-head"><span class="pane-title">{esc(title)}</span>
  <button class="copy" type="button" data-target="{pid}">Kopiuj</button></div>
  <p class="text" id="{pid}">{esc(text)}</p>
</div>"""


def build(week_dir):
    week = pathlib.Path(week_dir)
    specs = sorted(week.glob("k*.json"))
    if not specs:
        sys.exit(f"brak plików k*.json w {week}")
    files, posts = {}, []
    for n, spec_path in enumerate(specs, 1):
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        meta = spec.get("meta", {})
        slide_dir = spec_path.with_suffix("")
        pngs = sorted(slide_dir.glob("*.png"))
        if len(pngs) != len(spec["slides"]):
            sys.exit(f"{spec_path.name}: {len(pngs)} plików PNG, a slajdów {len(spec['slides'])}. Wyrenderuj ponownie.")
        imgs = []
        for i, png in enumerate(pngs, 1):
            pub = f"{slide_dir.name}/{png.name}"
            files[pub] = str(png)
            alt = meta.get("alt", "") if i == 1 else f"Slajd {i} z {len(pngs)}"
            imgs.append(f'<img src="{pub}" alt="{esc(alt)}" loading="lazy" width="1080" height="1350">')
        posts.append(f"""<article>
  <div class="meta"><span class="chip when">{esc(meta.get('when', ''))}</span>
  <span class="chip">{esc(meta.get('pillar', ''))}</span><span class="chip">{len(pngs)} slajdów</span></div>
  <h2>{esc(meta.get('topic') or spec['slides'][0].get('title', '').replace('*', ''))}</h2>
  <div class="strip">{''.join(imgs)}</div>
  <p class="hint">Przewiń w bok. Przytrzymaj grafikę (telefon) albo kliknij prawym (komputer), żeby zapisać.</p>
  <div class="panes">
    {pane(f'ig{n}', 'Podpis Instagram', meta.get('caption_ig', ''))}
    {pane(f'fb{n}', 'Podpis Facebook', meta.get('caption_fb', ''))}
  </div>
  <p class="alt"><b>Tekst alternatywny okładki:</b> {esc(meta.get('alt', ''))}</p>
</article>""")
    page = f"""{STYLE}
<div class="wrap">
  <header>
    <span class="eyebrow">PageHub · Instagram</span>
    <h1>Karuzele na {week_label(week.name)}</h1>
    <p class="how">Przejrzyj, popraw co chcesz i zaplanuj w <b>Meta Business Suite</b>: wgraj slajdy w kolejności, wklej podpis, ustaw godzinę z etykiety. Wszystkie pliki są też w paczce ZIP w czacie.</p>
  </header>
  {''.join(posts)}
  <footer>Wygenerowano automatycznie. Nic nie zostało opublikowane. Źródła i plan tygodnia: plan.md w repo.</footer>
</div>
{SCRIPT}"""
    (week / "index.html").write_text(page, encoding="utf-8")
    (week / "files.json").write_text(json.dumps(files, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"index.html + files.json ({len(files)} grafik) -> {week}")


if __name__ == "__main__":
    build(sys.argv[1])
