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
- `python3 -c "import playwright, spylls, numpy"` - czego brakuje, doinstaluj: `pip install playwright spylls numpy --break-system-packages`. Przeglądarka: `/usr/bin/google-chrome` (bez pobierania).
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
- Niczego nie wymyślaj o PageHub: klientów, wyników, opinii, terminów realizacji. Ceny tylko z `facts.md`, zawsze jako "od".
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
    "caption_reel": "...",
    "reel_heading": "...:",
    "reel_close": "...",
    "reel_points": ["...", "..."],
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
- `cta_keyword`: **każda** karuzela ma słowo-klucz WIELKIMI LITERAMI, bo rolka zawsze kończy się przyciskiem "Napisz SŁOWO w komentarzu", a każdy taki komentarz to powiadomienie o kliencie dla Jakuba. Słowo ma pasować do tematu i być rzadkie w zwykłych komentarzach (dobre: TURBO, TELEFON, WYCENA; złe: STRONA, SUPER). Inne w każdej karuzeli tygodnia.
- `reply_hint`: krótka odpowiedź w głosie PageHub dla osoby, która napisze słowo-klucz: o co dopytać + widełki z `facts.md`. Bez darmowych obietnic.
- Rolka pokazuje okładkę, potem `reel_heading` i numerowaną listę nagłówków slajdów z ponumerowanym kickerem (np. "powód 2/5", "sprawdź 3/5", "krok 4"), a na końcu "reszta w opisie". Dlatego:
  - główne punkty karuzeli mają kicker z numeracją, a ich liczba zgadza się z liczbą z okładki ("5 błędów" = 5 punktów),
  - `reel_heading`: krótka linia zakończona dwukropkiem, która mówi, czym jest lista i łączy ją z okładką (np. "Co spowalnia stronę:", "Sprawdź, czy Twoja strona ma:", "5 kroków do nowej strony:"). Przeczytaj ją razem z punktami: całość ma być zrozumiała dla kogoś, kto nie zna się na stronach,
  - każdy nagłówek musi mieć sens sam w sobie, a `caption_reel` zawiera resztę: krótko rozwinięte punkty i wezwanie do działania ze słowem-kluczem,
  - `reel_points` (opcjonalnie): punkty listy w rolce, gdy nagłówki slajdów brzmią dobrze na slajdzie, ale sztywno w rolce. Najlepiej pytania albo krótkie zdania z czasownikiem ("Numer od razu dzwoni?"), tyle samo co na okładce.
- **Lektor czyta ekrany rolki słowo w słowo**: tytuł i podtytuł okładki, `reel_heading` i każdy punkt listy, `reel_close` i przycisk ("Napisz TURBO w komentarzu"). Nie ma osobnego tekstu dla lektora. Dlatego te teksty piszesz tak, żeby dobrze brzmiały na głos (`skills/pl-naturalnie/SKILL.md`):
  - bez skrótów, symboli, nawiasów i linków (liczby są OK, lektor przeczyta je słownie),
  - emocje przez "?" i "!" w samym tekście ekranu, np. `reel_close` "Sprawdź, zanim znajdzie je Twój klient!",
  - pytania, które naprawdę są pytaniami, kończ "?", bo lektor wtedy podnosi głos,
  - całość czytana na głos: 15-25 sekund (około 200-330 znaków na wszystkich trzech ekranach razem),
  - nagrania robi automat w GitHub Actions po wypchnięciu tygodnia (nie Ty). Sprawdza każde rozpoznawaniem mowy i zapisuje w `kN/voice.json`, co usłyszał. Zdanie oznaczone tam `uwaga` przepisz prościej w następnym tygodniu i dopisz zbitkę do `skills/pl-naturalnie/SKILL.md`.
- **Rolka ma sprzedawać.** Ostatni ekran to `reel_close` (duże) + przycisk ze słowem-kluczem + "reszta w opisie". `reel_close` to jedno krótkie zdanie, które uderza w stratę albo pilność z punktu widzenia właściciela firmy (np. "Wolna strona oddaje klientów konkurencji.", "Sprawdź, zanim znajdzie je Twój klient!", "Chcesz stronę zrobioną od zera pod Twoją firmę?"). Bez wymyślonych liczb i bez obietnic czegokolwiek za darmo.
- **Rolki są wyłączone, dopóki Jakub ich nie zatwierdzi.** Nigdy nie twórz pliku `config/ROLKI` i nie zmieniaj ustawień publikacji rolek. Pola rolki (`caption_reel`, `reel_heading`, `reel_close`, `reel_points`) i tak uzupełniaj, żeby były gotowe. Nagrania lektora robi osobny automat w GitHub Actions, nie Ty.
- Gdy rolki zostaną włączone, każda karuzela wyjdzie też jako **rolka** zrobiona automatycznie ze slajdów, domyślnie dzień później o tej samej godzinie
  (opcjonalnie `reel_at`, żeby ustawić inny termin; `"reel": false`, żeby jej nie robić).
- `caption_reel`: osobny, krótszy opis do rolki. Pierwsza linia to hook do 125 znaków, potem 1-2 zdania, jedno wezwanie do działania
  (to samo słowo-klucz co w karuzeli, jeśli jest), 3 hashtagi. Nie pisz "przesuń" ani "zapisz karuzelę" - to film.

Zasady:
- 6-9 slajdów (API przyjmuje maksymalnie 10): okładka, stawka (slajd 2 musi działać sam), jedna myśl na slajd, podsumowanie (lista), CTA.
- Okładka: tytuł do 6-7 słów. Nagłówki slajdów 3-7 słów, tekst pod spodem do 25 słów.
- `*słowo*` = kolor akcentu, max 1-2 na slajd.
- Podpis IG: pierwsza linia z konkretem, jedno wezwanie do działania, 3-5 hashtagów na końcu.
- Podpis FB: osobna wersja, swobodniejsza, może mieć link https://pagehub.pl.
- W tygodniu przynajmniej jedna karuzela z CTA na słowo-klucz w komentarzu (to źródło klientów), pozostałe: zapisz / napisz DM.
- Obietnice w CTA tylko zgodne z `facts.md` (np. wycena, rozmowa o stronie). Nigdy nic za darmo: bez darmowych audytów, sprawdzeń ani poprawek.
- Zero długich myślników (— i –) w czymkolwiek.

## 4. Bramki jakości (wszystkie muszą przejść)
- Okładka: `python3 skills/ig-reel/hookscore.py --hook "<tytuł okładki bez gwiazdek>"`. Cel 60+. Poniżej 50 = napisz okładkę od nowa.
- Podpis IG i opis rolki: zapisz do plików tymczasowych, `python3 skills/ig-caption/caption.py plik.txt` -> wynik READY.
- Każdy podpis (IG i FB) i cały tekst slajdów: `python3 skills/ig-human/humanize.py plik.txt --report`. Wprowadź poprawki do JSON, flagowane słowa przepisz ręcznie.
- Podpisy IG, FB i opis rolki: `python3 skills/ig-human/detect.py plik.txt` -> PASS (70+). Najczęstsza przyczyna REVIEW to zbyt równe zdania (BURSTINESS): dodaj jedno bardzo krótkie i jedno dłuższe.
- Tekst slajdów to krótkie hasła, więc detect daje mu niski wynik z natury. Wystarczy, że humanize nic nie zmienia i nic nie flaguje.
- Żadnych liczb z powietrza, także retorycznych ("co drugi", "sto innych"). Liczba = fakt ze źródłem albo `facts.md`.
- `grep -nP "[—–]" weeks/<data>/*.json` nie może nic znaleźć.
- **Pisownia:** `python3 tools/spellcheck.py weeks/<data>` musi dać 0 nieznanych słów (sprawdza też tekst lektora). Literówkę poprawiasz w tekście.
  Do `config/words.txt` dopisujesz tylko prawdziwą nazwę własną lub markę, nigdy literówkę.
- **Zlepione lub zgubione słowa:** po wyrenderowaniu przeczytaj każdą okładkę i jeden slajd słowo po słowie (Read na PNG), a w rolce
  sprawdź klatkę końcową: `python3 tools/make_reel.py weeks/<data>/kN.json --still 99 --out /tmp/kN.png`. Skrypt rolki sam
  przerywa pracę, gdy pokazany tekst różni się od źródła.
- **Naturalny polski:** przeczytaj `skills/pl-naturalnie/SKILL.md` przed pisaniem. `python3 tools/pl_check.py weeks/<data>` musi dać 0 uwag (kalki z angielskiego, korpomowa, tekst lektora). Przeczytaj na głos każde zdanie lektora i każdy punkt rolki: jeśli brzmi jak tłumaczenie, przepisz.
- Przeczytaj każdą karuzelę od początku do końca jak klient: polski poprawny, sens jasny, nic, czego PageHub nie robi.
- Karuzela, która po dwóch poprawkach nadal nie przechodzi: ustaw w niej `"skip": true` w `meta`, opisz powód w `plan.md`. Lepiej 2 dobre posty niż 3 z jednym słabym.

## 5. Grafiki
- `python3 tools/render_carousel.py weeks/<data>/kN.json` dla każdej karuzeli.
- Ostrzeżenie o zmniejszeniu tekstu lub błąd "nie mieści się" = skróć tekst i wyrenderuj ponownie.
- Obejrzyj każdą okładkę i co najmniej jeden slajd środkowy (Read na PNG). Popraw, jeśli coś jest ucięte lub nieczytelne.
- Sprawdzenie na sucho: `cd tools && python3 publish.py --dry-run --now <publish_at karuzeli>` musi pokazać karuzelę jako gotową do publikacji.
- Rolka: `python3 tools/make_reel.py weeks/<data>/k1.json --out /tmp/reel.mp4` musi się zbudować (nie commituj MP4, automat robi go sam przy publikacji).

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
