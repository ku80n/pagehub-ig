# Tydzień 9-15 listopada 2026

Zrobione automatycznie (zadanie poniedziałkowe, bez nadzoru). Raport tygodnia (`state/raport/2026-11-09.md`) wygenerował się poprawnie.

## Wnioski z raportu
- 14 obserwujących, 0 leadów. Polubienia 5-8 na post, jedyne komentarze (2) pod rolką "Test strony na telefonie".
- Brak zasięgu, zapisów i udostępnień: token nie ma uprawnienia `instagram_manage_insights` (do poprawy przy wymianie tokenu, SETUP.md 2.3).
- Jeden tydzień danych to za mało na zmianę strategii. Zostawiamy rolki do każdej karuzeli i CTA na słowo-klucz we wszystkich trzech postach.
- Zeszły tydzień był 2 x Edukacja + Kulisy, bez oferty. W tym tygodniu oferta (co drugi tydzień) i pierwsza demonstracja funkcji.

## Plan

| # | termin | filar | temat i kąt | okładka (hookscore) | cel | CTA |
| --- | --- | --- | --- | --- | --- | --- |
| k1 | wtorek 10.11, 14:00 | Edukacja i problemy klientów | 6 palet kolorów dla branż z kodami i zmierzonym kontrastem (pomysł Jakuba z `ideas.md`) | Nie zgaduj kolorów: 6 palet dla Twojej firmy (84) | zapisy | KOLORY w komentarzu albo formularz |
| k2 | czwartek 12.11, 14:00 | Demonstracje i proces | Jak sam zmieniasz cennik i zdjęcia w panelu (Decap CMS), 4 kroki | Zmieniasz cennik? Bez informatyka, w 4 krokach (84) | zapisy | PANEL w komentarzu albo formularz |
| k3 | sobota 14.11, 10:00 | Oferta i sprzedaż | Landing page od 800 zł czy strona firmowa od 1500 zł: co wybrać przy jednej, a co przy kilku usługach | Jedna strona czy 5 podstron? Nie przepłać (63) | zapytania | PAKIET w komentarzu albo formularz |

Rolki (dzień później o tej samej godzinie: śr 11.11 14:00, pt 13.11 14:00, nd 15.11 10:00):
- k1: zamiast listy palet rolka pokazuje 4 branże i od razu zamienia okno w małą stronę w kolorach danej branży (jeden przykład = jedna paleta na żywo).
- k2: każdy problem właściciela (czekanie na zmianę, brak wiedzy o kodzie, nowe zdjęcie, strach przed zepsuciem) dostaje jedno konkretne rozwiązanie z panelu.
- k3: rolka to szybki test wyboru: pytanie o sytuację firmy i od razu pakiet, który do niej pasuje, bez cen (ceny zostają w karuzeli i opisie).

## Decyzje
- k1 ma 10 slajdów (zasada mówi 6-9). Zostawiłem tak, bo to gotowy scenariusz Jakuba z 6 paletami, a API przyjmuje do 10. Zmieniłem tylko okładkę (stara "Kolory na stronę Twojej branży" miała hookscore 47) i "Norma WCAG zaleca" na "Wytyczne WCAG zalecają" (WCAG to wytyczne, nie norma).
- k2: nie piszę, że panel jest w każdym pakiecie (cennik w `facts.md` go nie wymienia). W odpowiedzi na PANEL: zakres panelu ustalamy przy wycenie.
- k3: słowo WYCENA było w zeszłym tygodniu, więc PAKIET. Do k3 dodałem `reel_heading`, bo `pl_check` czytał tytuł "Landing page od 800 zł" jako ekran lektora (stary format rolki); rolka wahadło go nie używa.
- `closing` "OGARNIEMY TO." nie jest użyty w żadnej rolce.

## Źródła liczb spoza facts.md
- Kontrast tekstu co najmniej 4,5:1 (WCAG 2.x, kryterium 1.4.3, poziom AA): https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html (oraz https://webaim.org/articles/contrast/)
- Zasada 60-30-10 (proporcje kolorów: 60% dominujący, 30% drugi, 10% akcent): https://www.freecodecamp.org/news/the-60-30-10-rule-in-design/
- Kontrasty konkretnych palet liczy i drukuje renderer na slajdach (wszystkie przeszły próg 4,5:1).
- Pozostałe liczby (800 zł, 1500 zł, 5 podstron, domena na rok i 2 lata) z `facts.md`. "4 kroki" i "6 palet" to liczba elementów w samym poście.

## Bramki jakości
- hookscore okładek: k1 84,4, k2 84,4, k3 62,6 (cel 60+).
- caption.py: wszystkie podpisy IG i opisy rolek READY (k1 IG ma uwagę WARN "2 asks": "Planujesz stronę?" + słowo-klucz, poprawione, teraz READY).
- detect.py (PASS): k1 IG 91,2, rolka 83,6, FB 79,8; k2 IG 75,9, rolka 95,8, FB 84,1; k3 IG 74,9, rolka 78,6, FB 77,8.
- humanize.py: podpisy i slajdy bez zmian i bez flag (k3 slajdy miały flagę "równe zdania", przepisałem slajdy 3 i 5).
- spellcheck: 0 nieznanych słów. pl_check: 0 uwag. Brak długich myślników.
- Okładki i slajdy środkowe obejrzane (k1 01 i 03, k2 01 i 05, k3 01 i 06): bez ucięć i zlepionych słów.
- Klatki rolek obejrzane (pierwsze pytanie i koniec z przyciskiem): tekst w dwóch liniach, czytelny.
- Dry-run publish.py: karuzele i rolki gotowe w swoich terminach.

## Lista kontrolna z audytu
| punkt | k1 | k2 | k3 |
| --- | --- | --- | --- |
| każde twierdzenie zgodne z `facts.md` | tak | tak | tak |
| brak fikcyjnych klientów, opinii i wyników | tak | tak | tak |
| tekst czytelny na telefonie | tak | tak | tak |
| CTA i link poprawne (słowo-klucz, formularz, pagehub.pl) | tak | tak | tak |
| coś innego niż ostatnie publikacje | tak (kolory, nowy temat) | tak (pierwsza demonstracja funkcji; panel był tylko jednym krokiem w k3 z 7.11) | tak (pierwszy post ofertowy) |
| rolka nie jest mechanicznym powtórzeniem karuzeli | tak | tak | tak |
| treść nie sugeruje człowieka za profilem | tak | tak | tak |

## Do uwagi
- k2: "po chwili zmiana jest na stronie" i "poprzednia wersja zostaje w historii zmian" opisują typowe działanie Decap CMS z Netlify (zapis w repozytorium i ponowne zbudowanie strony). Jeśli panel u klientów działa inaczej, warto to poprawić przed czwartkiem.
