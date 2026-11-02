# Cotygodniowa paczka karuzel PageHub - instrukcja dla Claude

To zadanie działa samo w poniedziałek rano. Nikt nie patrzy na bieżąco, więc nie zadawaj pytań:
podejmij rozsądną decyzję, zapisz ją w `plan.md` i jedź dalej. Na Instagram NIC nie publikujesz.
Wynik: strona z podglądem (Artifact), paczka ZIP w czacie, commit w repo.

Wszystkie ścieżki poniżej są względem katalogu repo.

## 0. Przygotowanie
- `python3 -c "import playwright"` - jeśli brak, `pip install playwright --break-system-packages`. Przeglądarka: `/usr/bin/google-chrome` (bez pobierania).
- Folder tygodnia: `weeks/<data poniedziałku tego tygodnia, RRRR-MM-DD>/`. Jeśli już istnieje i ma `index.html`, ten tydzień jest zrobiony: zakończ z krótką informacją.

## 1. Przeczytaj
- `config/voice.md`, `config/brand.md`, `config/facts.md`, `config/pillars.md`
- `ideas.md` (pierwszeństwo), `log.md` (nie powtarzaj tematów z 4 ostatnich tygodni)
- `skills/ig-carousel/SKILL.md`, `skills/ig-caption/SKILL.md`, `skills/ig-human/SKILL.md`
- poprzedni tydzień w `weeks/` jako wzór formatu JSON

## 2. Zaplanuj 3 karuzele -> `weeks/<data>/plan.md`
- Podział według `config/pillars.md`, terminy z `config/brand.md`.
- Dla każdej: filar, temat, konkretny kąt (nie "SEO", tylko "3 rzeczy, przez które Google nie pokazuje Twojej firmy w Mapach"), termin.
- Każda liczba spoza `facts.md` musi mieć publiczne źródło: sprawdź ją wyszukiwarką i wpisz link w `plan.md`. Bez źródła nie ma liczby.
- Niczego nie wymyślaj o PageHub: klientów, wyników, opinii.

## 3. Napisz -> `weeks/<data>/k1.json`, `k2.json`, `k3.json`
Format (jak w `tools/render_carousel.py`):
```json
{
  "handle": "pagehub.pl",
  "ig": "@pagehub.pl",
  "meta": {
    "when": "wtorek 19:00",
    "pillar": "Edukacja",
    "topic": "krótki opis tematu",
    "caption_ig": "...",
    "caption_fb": "...",
    "alt": "tekst alternatywny okładki"
  },
  "slides": [
    {"type": "cover", "kicker": "...", "title": "...", "subtitle": "..."},
    {"type": "text", "title": "...", "body": "..."},
    {"type": "list", "title": "...", "items": ["..."]},
    {"type": "cta", "title": "...", "body": "...", "button": "..."}
  ]
}
```
Zasady:
- 6-8 slajdów: okładka, stawka (slajd 2 musi działać sam), jedna myśl na slajd, podsumowanie (lista), CTA.
- Okładka: tytuł do 6 słów. Nagłówki slajdów 3-7 słów, tekst pod spodem do 25 słów.
- `*słowo*` = kolor akcentu, max 1-2 na slajd.
- Podpis IG: pierwsza linia z konkretem, jedno wezwanie do działania, 3-5 hashtagów na końcu.
- Podpis FB: osobna wersja, swobodniejsza, może mieć link https://pagehub.pl.
- CTA różne w różnych karuzelach (zapisz / skomentuj słowo / napisz DM).
- Zero długich myślników (— i –) w czymkolwiek.

## 4. Sprawdź tekst (skrypty muszą przejść)
- Okładka: `python3 skills/ig-reel/hookscore.py --hook "<tytuł okładki bez gwiazdek>"`. Cel 60+. Poniżej 50 = napisz okładkę od nowa.
- Podpis IG: zapisz do pliku tymczasowego, `python3 skills/ig-caption/caption.py plik.txt` -> wynik READY.
- Każdy podpis (IG i FB) i cały tekst slajdów: `python3 skills/ig-human/humanize.py plik.txt --report`. Wprowadź poprawki do JSON, flagowane słowa przepisz ręcznie.
- Podpisy IG i FB: `python3 skills/ig-human/detect.py plik.txt` -> PASS (70+). Najczęstsza przyczyna REVIEW to zbyt równe zdania (BURSTINESS): dodaj jedno bardzo krótkie i jedno dłuższe.
- Tekst slajdów to krótkie hasła, więc detect daje mu niski wynik z natury. Wystarczy, że humanize nic nie zmienia i nic nie flaguje.
- Żadnych liczb z powietrza, także retorycznych ("co drugi", "sto innych"). Liczba = fakt ze źródłem albo `facts.md`.
- `grep -nP "[—–]" weeks/<data>/*.json` nie może nic znaleźć.

## 5. Grafiki
- `python3 tools/render_carousel.py weeks/<data>/kN.json` dla każdej karuzeli.
- Ostrzeżenie o zmniejszeniu tekstu lub błąd "nie mieści się" = skróć tekst i wyrenderuj ponownie.
- Obejrzyj każdą okładkę i co najmniej jeden slajd środkowy (Read na PNG). Popraw, jeśli coś jest ucięte lub nieczytelne.

## 6. Strona z podglądem
- `python3 tools/build_page.py weeks/<data>` -> `index.html` + `files.json`.
- Opublikuj narzędziem Artifact: `file_path` = `weeks/<data>/index.html`, `files` = zawartość `files.json`.
- Jeśli `config/delivery.md` ma adres strony: najpierw `Artifact action:"read"` z tym `url`, potem publish z tym samym `url` (podmień całą stronę i pliki). Jeśli adresu nie ma: opublikuj nową (icon: `calendar`) i wpisz adres do `config/delivery.md`.

## 7. Paczka ZIP
- `weeks/<data>/pagehub-<data>.zip`: foldery k1, k2, k3 z PNG + `podpisy.txt` (dla każdej karuzeli: termin, podpis IG, podpis FB, alt).
- Wyślij SendUserFile (status proactive, display attach). Nie commituj ZIP-a.

## 8. Zapisz i wypchnij
- `ideas.md`: użyte pomysły oznacz `[x]`.
- `log.md`: po wierszu na karuzelę.
- `git add -A weeks/<data> ideas.md log.md config/delivery.md && git commit -m "Karuzele na tydzień <data>" && git push`.

## 9. Koniec
Jedna wiadomość: trzy tematy z terminami, wynik detect/hookscore w jednej linii, co wymaga uwagi (np. {{liczba}} do uzupełnienia). Bez opisu kroków.
