# Cotygodniowa paczka karuzel PageHub - instrukcja dla Claude

To zadanie działa samo w poniedziałek rano. Nikt nie patrzy na bieżąco, więc nie zadawaj pytań:
podejmij rozsądną decyzję, zapisz ją w `plan.md` i jedź dalej.

**Nikt tego nie przegląda przed publikacją.** To, co commitujesz do `main`, GitHub Actions
(`.github/workflows/instagram.yml`) samo opublikuje na Instagramie i Facebooku o godzinie z `publish_at`.
Dlatego bramki jakości z kroku 4 są obowiązkowe, a w razie wątpliwości lepiej pominąć karuzelę niż ją wypuścić.
Ty sam niczego nie publikujesz.

Wynik: commit w repo (na nim działa publikacja) i strona z podglądem (archiwum, nikt jej nie musi oglądać).

Wszystkie ścieżki poniżej są względem katalogu repo.

## 0. Przygotowanie
- `python3 -c "import playwright"` - jeśli brak, `pip install playwright --break-system-packages`. Przeglądarka: `/usr/bin/google-chrome` (bez pobierania).
- Folder tygodnia: `weeks/<data poniedziałku tego tygodnia, RRRR-MM-DD>/`. Jeśli już istnieje i ma `index.html`, ten tydzień jest zrobiony: zakończ z krótką informacją.
- Jeśli istnieje `config/PAUZA`, publikacja jest wstrzymana: przygotuj tydzień normalnie, ale wspomnij o pauzie w końcowej wiadomości.

## 1. Przeczytaj
- `config/voice.md`, `config/brand.md`, `config/facts.md`, `config/pillars.md`
- `ideas.md` (pierwszeństwo), `log.md` (nie powtarzaj tematów z 4 ostatnich tygodni)
- `state/published.json` i `state/publish_failures.json`, jeśli są: co z zeszłego tygodnia nie wyszło
- `skills/ig-carousel/SKILL.md`, `skills/ig-caption/SKILL.md`, `skills/ig-human/SKILL.md`
- poprzedni tydzień w `weeks/` jako wzór formatu JSON

## 2. Zaplanuj 3 karuzele -> `weeks/<data>/plan.md`
- Podział według `config/pillars.md`, terminy z `config/brand.md`.
- Dla każdej: filar, temat, konkretny kąt (nie "SEO", tylko "3 rzeczy, przez które Google nie pokazuje Twojej firmy w Mapach"), termin.
- Każda liczba spoza `facts.md` musi mieć publiczne źródło: sprawdź ją wyszukiwarką i wpisz link w `plan.md`. Bez źródła nie ma liczby.
- Niczego nie wymyślaj o PageHub: klientów, wyników, opinii, terminów realizacji, cen.
- Bez tematów politycznych, kontrowersyjnych, o konkurencji z nazwy.

## 3. Napisz -> `weeks/<data>/k1.json`, `k2.json`, `k3.json`
Format (jak w `tools/render_carousel.py`):
```json
{
  "handle": "pagehub.pl",
  "ig": "@pagehub.pl",
  "meta": {
    "when": "wtorek 10.11, 19:00",
    "publish_at": "2026-11-10T19:00:00+01:00",
    "pillar": "Edukacja",
    "topic": "krótki opis tematu",
    "cta_keyword": "TELEFON",
    "reply_hint": "Proponowana pierwsza odpowiedź dla osoby, która napisze słowo-klucz",
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
- `publish_at`: data i godzina w czasie polskim z właściwym przesunięciem (+01:00 zimą, +02:00 latem). Musi być w przyszłości.
- `cta_keyword`: jedno nietypowe słowo WIELKIMI LITERAMI, jeśli CTA to "napisz SŁOWO w komentarzu" (Jakub dostaje wtedy powiadomienie). Pusty string, jeśli CTA jest inne.
- `reply_hint`: krótka odpowiedź w głosie PageHub dla takiej osoby. Pusty string, jeśli brak słowa-klucza.

Zasady:
- 6-9 slajdów (API przyjmuje maksymalnie 10): okładka, stawka (slajd 2 musi działać sam), jedna myśl na slajd, podsumowanie (lista), CTA.
- Okładka: tytuł do 6-7 słów. Nagłówki slajdów 3-7 słów, tekst pod spodem do 25 słów.
- `*słowo*` = kolor akcentu, max 1-2 na slajd.
- Podpis IG: pierwsza linia z konkretem, jedno wezwanie do działania, 3-5 hashtagów na końcu.
- Podpis FB: osobna wersja, swobodniejsza, może mieć link https://pagehub.pl.
- W tygodniu przynajmniej jedna karuzela z CTA na słowo-klucz w komentarzu (to źródło klientów), pozostałe: zapisz / napisz DM.
- Obietnice w CTA tylko zgodne z `facts.md` (np. sprawdzenie strony, odświeżenie wyglądu). Bez cen i terminów.
- Zero długich myślników (— i –) w czymkolwiek.

## 4. Bramki jakości (wszystkie muszą przejść)
- Okładka: `python3 skills/ig-reel/hookscore.py --hook "<tytuł okładki bez gwiazdek>"`. Cel 60+. Poniżej 50 = napisz okładkę od nowa.
- Podpis IG: zapisz do pliku tymczasowego, `python3 skills/ig-caption/caption.py plik.txt` -> wynik READY.
- Każdy podpis (IG i FB) i cały tekst slajdów: `python3 skills/ig-human/humanize.py plik.txt --report`. Wprowadź poprawki do JSON, flagowane słowa przepisz ręcznie.
- Podpisy IG i FB: `python3 skills/ig-human/detect.py plik.txt` -> PASS (70+). Najczęstsza przyczyna REVIEW to zbyt równe zdania (BURSTINESS): dodaj jedno bardzo krótkie i jedno dłuższe.
- Tekst slajdów to krótkie hasła, więc detect daje mu niski wynik z natury. Wystarczy, że humanize nic nie zmienia i nic nie flaguje.
- Żadnych liczb z powietrza, także retorycznych ("co drugi", "sto innych"). Liczba = fakt ze źródłem albo `facts.md`.
- `grep -nP "[—–]" weeks/<data>/*.json` nie może nic znaleźć.
- Przeczytaj każdą karuzelę od początku do końca jak klient: polski poprawny, sens jasny, nic, czego PageHub nie robi.
- Karuzela, która po dwóch poprawkach nadal nie przechodzi: ustaw w niej `"skip": true` w `meta`, opisz powód w `plan.md`. Lepiej 2 dobre posty niż 3 z jednym słabym.

## 5. Grafiki
- `python3 tools/render_carousel.py weeks/<data>/kN.json` dla każdej karuzeli.
- Ostrzeżenie o zmniejszeniu tekstu lub błąd "nie mieści się" = skróć tekst i wyrenderuj ponownie.
- Obejrzyj każdą okładkę i co najmniej jeden slajd środkowy (Read na PNG). Popraw, jeśli coś jest ucięte lub nieczytelne.
- Sprawdzenie na sucho: `cd tools && python3 publish.py --dry-run --now <publish_at karuzeli>` musi pokazać karuzelę jako gotową do publikacji.

## 6. Strona z podglądem (archiwum)
- `python3 tools/build_page.py weeks/<data>` -> `index.html` + `files.json`.
- Opublikuj narzędziem Artifact: `file_path` = `weeks/<data>/index.html`, `files` = zawartość `files.json`.
- Jeśli `config/delivery.md` ma adres strony: najpierw `Artifact action:"read"` z tym `url`, potem publish z tym samym `url`. Jeśli adresu nie ma: opublikuj nową (icon: `calendar`) i wpisz adres do `config/delivery.md`.

## 7. Zapisz i wypchnij
- `ideas.md`: użyte pomysły oznacz `[x]`.
- `log.md`: po wierszu na karuzelę.
- `git add -A weeks/<data> ideas.md log.md config/delivery.md && git commit -m "Karuzele na tydzień <data>" && git pull --rebase && git push`
  (GitHub Actions commituje do `state/`, więc zawsze rób `pull --rebase` przed push).
- Sprawdź, że push przeszedł. Bez niego nic się nie opublikuje: wtedy w końcowej wiadomości napisz to wprost.

## 8. Koniec
Jedna krótka wiadomość: trzy tematy z terminami i nic więcej, chyba że coś wymaga uwagi
(pominięta karuzela, nieudany push, problem z zeszłego tygodnia ze `state/`). Bez opisu kroków.
