# Cotygodniowa paczka karuzel PageHub - instrukcja dla Claude

To zadanie działa samo w poniedziałek rano. Nikt nie patrzy na bieżąco, więc nie zadawaj pytań:
podejmij rozsądną decyzję, zapisz ją w `plan.md` i jedź dalej.

**Nikt tego nie przegląda przed publikacją.** To, co commitujesz do `main`, GitHub Actions
(`.github/workflows/instagram.yml`) samo opublikuje na Instagramie i Facebooku o godzinie z `publish_at`,
a dzień później rolkę "wahadło" do tej karuzeli.
Dlatego bramki jakości z kroku 4 są obowiązkowe, a w razie wątpliwości lepiej pominąć karuzelę niż ją wypuścić.
Ty sam niczego nie publikujesz.

Wynik: commit w repo (na nim działa publikacja) i strona z podglądem (archiwum, nikt jej nie musi oglądać).

Wszystkie ścieżki poniżej są względem katalogu repo.

## Zasady nadrzędne (audyt z 6.11.2026)
- **Profil prowadzi wyłącznie AI.** Nie planuj twarzy, nagrań właściciela, osobistych historii ani niczego, co wymaga obecności człowieka. Gdy poradnik albo pomysł mówi "pokaż człowieka", zamiast tego pokaż produkt, proces albo funkcję strony.
- Mówimy jako marka PageHub ("my", "w PageHub"). Nie udajemy człowieka i nie tworzymy persony AI z osobistymi doświadczeniami.
- **Każda publikacja wnosi konkretną wartość.** Nie publikuj po to, żeby wypełnić harmonogram. Lepiej mniej i lepiej: rolkę bez własnej wartości wyłącz (`"reel": false`).
- Najpierw problem klienta i jego skutek dla firmy, potem rozwiązanie. Technologia (Angular, Netlify) tylko jako uzasadnienie.
- Dowody zamiast deklaracji: prawdziwe funkcje, prawdziwa realizacja (Envision Studio), konkretne rozwiązania. Koncepcję albo makietę oznacz jako przykład.
- Lokalność (Przemyśl, Rzeszów, Podkarpacie) wtedy, gdy temat naprawdę jej dotyczy, bez upychania nazw miast.
- Każda publikacja ma w `plan.md` jeden mierzalny cel: zasięg, zapis, udostępnienie, wejście na profil, kliknięcie albo zapytanie.
- Nie powtarzaj za mocno ostatnich publikacji (tematy, kąty, pierwsze zdania z `log.md` i ostatnich tygodni w `weeks/`).
- Jeśli w `state/raport/` jest raport z ostatniego tygodnia, przeczytaj go przed planowaniem. Wnioski wyciągaj ostrożnie: porównuj grupy podobnych postów z kilku tygodni, nie zmieniaj strategii przez jeden post.

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
- Dla każdej: filar, temat, konkretny kąt (nie "SEO", tylko "3 rzeczy, przez które Google nie pokazuje Twojej firmy w Mapach"), termin, mierzalny cel i CTA.
- Dla każdej rolki: czym różni się od swojej karuzeli (jeden przykład, jedno rozwiązanie, jeden wniosek). Jeśli nie umiesz tego napisać jednym zdaniem, ta karuzela nie dostaje rolki.
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
    "when": "wtorek 10.11, 14:00",
    "publish_at": "2026-11-10T14:00:00+01:00",
    "pillar": "Edukacja i problemy klientów",
    "topic": "krótki opis tematu",
    "cta_keyword": "TELEFON",
    "reply_hint": "Proponowana pierwsza odpowiedź dla osoby, która napisze słowo-klucz",
    "caption_ig": "...",
    "caption_reel": "...",
    "reel_pendulum": {
      "questions": ["ROZJEŻDŻA SIĘ NA TELEFONIE?", "TEKST TRZEBA POWIĘKSZAĆ?", "NIE DA SIĘ ZADZWONIĆ?", "FORMULARZ NIE DZIAŁA?"],
      "answers": ["UKŁAD POD KAŻDY EKRAN.", "CZYTELNY OD RAZU.", "NUMER, KTÓRY DZWONI.", "WIADOMOŚCI DOCHODZĄ."],
      "closing": "TAK DZIAŁA DOBRA STRONA.",
      "url": "twoja-strona.pl"
    },
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
  Używaj **tylko** domyślnych terminów z `config/brand.md` (wtorek 14:00, czwartek 14:00, sobota 10:00): dokładnie wtedy osobne zadanie uruchamia publikację. Godzinny harmonogram GitHuba bywa spóźniony o kilka godzin, więc inna godzina oznacza spóźniony post.
  Rolka wychodzi sama dzień później o tej samej godzinie (środa 14:00, piątek 14:00, niedziela 10:00); gdy rolki próbne zostaną włączone, próbna wyjdzie godzinę przed nią. Nie ustawiaj `reel_at`, chyba że zmieniasz ten rytm.
- `cta_keyword`: **każda** karuzela ma słowo-klucz WIELKIMI LITERAMI, bo rolka kończy się przyciskiem "Napisz SŁOWO w komentarzu", a każdy taki komentarz to powiadomienie o kliencie dla Jakuba. To jedna z dwóch dróg kontaktu: w opisach, gdzie pasuje, dodaj drugą ("albo wypełnij formularz na pagehub.pl"). CTA ma pasować do intencji posta: post edukacyjny może prosić o zapis, oferta o wycenę. Słowo ma pasować do tematu i być rzadkie w zwykłych komentarzach (dobre: TURBO, TELEFON, WYCENA; złe: STRONA, SUPER). Inne w każdej karuzeli tygodnia.
- `reply_hint`: krótka odpowiedź w głosie PageHub dla osoby, która napisze słowo-klucz: o co dopytać + widełki z `facts.md`. Bez darmowych obietnic.
- **Rolka "wahadło"** (`reel_pendulum`, render: `tools/make_pendulum.py`). Karuzela dostaje rolkę na ten sam temat, publikowaną dzień po karuzeli, ale rolka nie jest jej skrótem: pokazuje problem i jego konkretne rozwiązanie, para po parze. Wygląd jest stały i nie zmieniasz go: ciemne tło jak na karuzelach z ledwo widocznym kosmosem 3D (mgławica, gwiazdy, siatka), duży tekst w ciemnym oknie przeglądarki z paskiem adresu, biały znaczek z logo PageHub na sznurku, logo na górze, pagehub.pl na dole, energiczna muzyka bez lektora. Wahadło kołysze się w rytm muzyki i tam, gdzie przejdzie sznurek, tekst zmienia się na następny: pytanie (białe), odpowiedź (w kolorze marki), pytanie, odpowiedź... Na końcu pojawia się przycisk "Napisz SŁOWO w komentarzu" z dźwiękiem "ping", znika przed końcem pętli i rolka kręci się bez widocznego końca.
  - `questions`: 4 pytania (najwyżej 5) z punktów **tej** karuzeli, w tej samej kolejności, WIELKIMI LITERAMI, każde kończy się "?". To problem albo potrzeba właściciela firmy, którą PageHub załatwia (np. "NIE DA SIĘ ZADZWONIĆ?", "BEZ SZABLONU?", "WIDOCZNA W GOOGLE?").
  - Krótko: 2-4 słowa, najwyżej dwie linie po około 13 znaków ("ROZJEŻDŻA SIĘ / NA TELEFONIE?"). Dłuższe zmniejszają tekst w całej rolce.
  - **Od razu jasne, o co chodzi.** Okno przeglądarki i adres już mówią, że chodzi o stronę internetową, ale każde pytanie musi być zrozumiałe samo, bez karuzeli. Złe: "NUMER NIE DZWONI?" (nie wiadomo, co z tym numerem). Dobre: "NIE DA SIĘ ZADZWONIĆ?". Pierwsze pytanie to hak: najmocniejszy problem z karuzeli.
  - `answers`: **do każdego pytania jego konkretne rozwiązanie**, 2-4 słowa, kropka na końcu, prawdziwe według `facts.md` ("NUMER, KTÓRY DZWONI.", "KOD PISANY OD ZERA.", "ZGŁASZAMY JĄ DO GOOGLE."). Nie powtarzaj w kółko tej samej odpowiedzi: "OGARNIEMY TO." to deklaracja, a nie dowód.
  - `closing`: puenta na koniec, przy której pojawia się przycisk, np. "TAK DZIAŁA DOBRA STRONA.", "TAK POWSTAJE TWOJA STRONA.". Może być "OGARNIEMY TO.", ale najwyżej w jednej rolce na tydzień.
  - `answer`: zapasowa wspólna odpowiedź, gdy któregoś z `answers` brakuje.
  - `url`: adres w pasku okna, domyślnie "twoja-strona.pl".
  - Przycisk robi się sam z `cta_keyword` ("Napisz TELEFON w komentarzu"). Nie dopisuj go do pytań.
  - Bez cen, liczb i obietnic spoza `facts.md`. Bez skrótów i symboli. Zasady `skills/pl-naturalnie/SKILL.md` obowiązują też tutaj.
  - Rolka próbna (dla osób, które nie obserwują profilu) zaczyna się od drugiego pytania. Nic nie musisz dla niej pisać.
- **Rolki są włączone** (`config/ROLKI`). Nie usuwaj i nie zmieniaj tego pliku. Rolki próbne są na razie wyłączone (Instagram odrzuca je dla tego konta, zwykle wymagają co najmniej 200 obserwujących); nie twórz `config/ROLKI_PROBNE`, włączy je Jakub. Karuzela bez `reel_pendulum` nie dostanie rolki. `"reel": false` wyłącza rolkę jednej karuzeli, `"reel_trial": false` tylko jej rolkę próbną.
- `caption_reel`: osobny, krótszy opis do rolki, zgodny z tym, co pokazuje rolka (pary problem - rozwiązanie). Pierwsza linia to hook do 125 znaków, potem 1-2 zdania, wezwanie do działania
  (słowo-klucz, a gdzie pasuje także formularz na pagehub.pl), 3 hashtagi. Nie pisz "przesuń" ani "zapisz karuzelę" - to film. Ten sam opis dostaje rolka próbna.

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
- **Pisownia:** `python3 tools/spellcheck.py weeks/<data>` musi dać 0 nieznanych słów (sprawdza też pytania i odpowiedź rolki). Literówkę poprawiasz w tekście.
  Do `config/words.txt` dopisujesz tylko prawdziwą nazwę własną lub markę, nigdy literówkę.
- **Zlepione lub zgubione słowa:** po wyrenderowaniu przeczytaj każdą okładkę i jeden slajd słowo po słowie (Read na PNG).
- **Rolka:** dla każdej karuzeli zrób dwie klatki i obejrzyj je (Read): pierwsze pytanie
  `python3 tools/make_pendulum.py weeks/<data>/kN.json --still 0 --out /tmp/kN-a.png` i koniec z przyciskiem
  `python3 tools/make_pendulum.py weeks/<data>/kN.json --still 99 --out /tmp/kN-b.png`. Tekst ma być czytelny, w dwóch liniach, bez ucięć.
- **Naturalny polski:** przeczytaj `skills/pl-naturalnie/SKILL.md` przed pisaniem. `python3 tools/pl_check.py weeks/<data>` musi dać 0 uwag (kalki z angielskiego, korpomowa). Przeczytaj na głos każde pytanie rolki razem z odpowiedzią: ma brzmieć naturalnie i być jasne dla kogoś, kto nie zna się na stronach.
- Przeczytaj każdą karuzelę od początku do końca jak klient: polski poprawny, sens jasny, nic, czego PageHub nie robi.
- **Lista kontrolna z audytu** (każdy punkt w `plan.md` z odpowiedzią tak/nie): każde twierdzenie zgodne z `facts.md`; brak fikcyjnych klientów, opinii i wyników; tekst czytelny na telefonie; CTA i link poprawne; materiał wnosi coś innego niż ostatnie publikacje; rolka nie jest mechanicznym powtórzeniem karuzeli; treść nie sugeruje, że za profilem stoi człowiek. Wynik "czy brzmi jak AI" to tylko jedna z bramek: ważniejsze, czy tekst jest konkretny, prawdziwy i przydatny.
- Karuzela, która po dwóch poprawkach nadal nie przechodzi: ustaw w niej `"skip": true` w `meta`, opisz powód w `plan.md`. Lepiej 2 dobre posty niż 3 z jednym słabym.

## 5. Grafiki
- `python3 tools/render_carousel.py weeks/<data>/kN.json` dla każdej karuzeli.
- Ostrzeżenie o zmniejszeniu tekstu lub błąd "nie mieści się" = skróć tekst i wyrenderuj ponownie.
- Obejrzyj każdą okładkę i co najmniej jeden slajd środkowy (Read na PNG). Popraw, jeśli coś jest ucięte lub nieczytelne.
- Sprawdzenie na sucho: `cd tools && python3 publish.py --dry-run --now <publish_at karuzeli>` musi pokazać karuzelę jako gotową do publikacji.
- Sprawdzenie rolek na sucho: `cd tools && python3 publish.py --dry-run --now <dzień po publish_at, ta sama godzina, +5 min>` musi pokazać rolkę. Nie commituj MP4, automat renderuje rolki sam przy publikacji.

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
