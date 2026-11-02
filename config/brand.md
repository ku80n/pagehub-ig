# Marka PageHub - ustawienia

## Konto
- Instagram: @pagehub.pl  <!-- popraw, jeśli handle jest inny -->
- Strona: pagehub.pl
- Facebook: strona PageHub (podpis FB robimy osobno)

## Wygląd karuzel
- Styl: ciemne okno przeglądarki, numery linii jak w edytorze kodu
- Akcent: #1C98C3 (teal), tło #0B0F14
- Nagłówki: DejaVu Sans Mono, tekst: Inter
- Format: 1080x1350 (4:5), PNG
- Generator: `python3 tools/render_carousel.py weeks/RRRR-MM-DD/kN.json`
- Słowo w `*gwiazdkach*` dostaje kolor akcentu. Jedno, maksymalnie dwa na slajd.

## Publikacja
- 3 karuzele tygodniowo
- Domyślne terminy: wtorek 19:00, czwartek 19:00, sobota 10:00
- Publikacja: automatycznie przez GitHub Actions o godzinie z `publish_at` (Instagram + Facebook)
- Pauza: plik `config/PAUZA` w repo

## Podpisy
- Po polsku
- Pierwsza linia mieści się w 125 znakach i ma konkret (liczba, nazwa, problem)
- Jedno wezwanie do działania na post
- Hashtagi: 3-5 (Instagram liczy maksymalnie 5), tematyczne, na końcu
- Nigdy: #pozycjonowanie, #viral, #fyp, #explore
- Pula na start: #stronywww #stronainternetowa #webdesign #przemyśl #rzeszów #podkarpacie #małybiznes #lokalnybiznes #angular #stronadlafirmy
- Emoji: 0-2 na podpis, nigdy jako wypunktowanie
- Bez długich myślników (— i –). Tylko krótki: -
- Wersja na Facebooka: osobny podpis, może być dłuższy, może mieć klikalny link do pagehub.pl
