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
- Domyślne terminy karuzel: wtorek 14:00, czwartek 14:00, sobota 10:00
- Rolka do karuzeli: dzień później o tej samej godzinie (środa 14:00, piątek 14:00, niedziela 10:00). Rolki próbne (godzinę wcześniej) są gotowe, ale wyłączone: Instagram odrzuca je dla tego konta (zwykle trzeba 200 obserwujących). Włączenie: plik config/ROLKI_PROBNE + zadania w Claude także na 13:02 (śr, pt) i 9:02 (nd)
- Publikacja: automatycznie przez GitHub Actions o godzinie z `publish_at` (Instagram + Facebook). Dokładnie o czasie (wt i czw 14:02, sob 10:02, rolki śr i pt 14:02, nd 10:02) uruchamiają ją zaplanowane zadania w Claude; godzinny harmonogram GitHuba to tylko zapas, bo bywa spóźniony o kilka godzin
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
