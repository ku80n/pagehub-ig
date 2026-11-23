# Tydzień 23-29 listopada 2026

Zrobione automatycznie (zadanie poniedziałkowe, bez nadzoru). Raport tygodnia (`state/raport/2026-11-23.md`) wygenerował się poprawnie.

## UWAGA: publikacja nie działa od soboty 21.11
- Każdy przebieg publikacji od 21.11 09:03 kończy się błędem HTTP 403 przy wgrywaniu plików na Netlify (`netlify_deploy` w `tools/publish.py`). Dotyczy dispatchy z zadań w Claude i godzinnego harmonogramu.
- Skutek: karuzela o domenie (sob 21.11) i jej rolka (nd 22.11) mają w `state/published.json` status `missed`.
- Najpewniej wygasł lub został cofnięty `NETLIFY_AUTH_TOKEN` albo zmieniło się `NETLIFY_SITE_ID` (sekrety repo). Bez poprawki wtorkowa karuzela też nie wyjdzie. Jakub dostał powiadomienie.
- Przy okazji: `tools/common.py` (linia 59) wywraca się przy odczycie błędu, gdy Netlify odpowiada tekstem zamiast JSON (`'str' object has no attribute 'get'`), więc w logu nie widać treści błędu Netlify. Nie zmieniałem kodu.

## Wnioski z raportu
- 14 obserwujących (+0), 0 leadów. Polubienia w zeszłym tygodniu po 1 na post, wyraźnie mniej niż w pierwszych dwóch tygodniach (4-8).
- Zasięgu, zapisów i udostępnień nadal brak (token bez `instagram_manage_insights`, SETUP.md 2.3).
- Przy tak małych liczbach to szum, nie wniosek. Po 3 tygodniach widać tylko tyle, że najwięcej polubień miały posty z gotową, praktyczną listą (szybkość, telefon, kolory, kulisy). Zostajemy przy tym formacie, bez zmian strategii.

## Plan

| # | termin | filar | temat i kąt | okładka (hookscore) | cel | CTA |
| --- | --- | --- | --- | --- | --- | --- |
| k1 | wtorek 24.11, 14:00 | Edukacja i problemy klientów | "Połączenie nie jest prywatne": 4 rzeczy, przez które przeglądarka ostrzega przed stroną firmy (https, ważny certyfikat, przekierowanie z http, zdjęcia przez https) + jak to działa na Netlify | Połączenie nie jest prywatne? Tracisz klienta (87) | zapisy | HTTPS w komentarzu albo formularz |
| k2 | czwartek 26.11, 14:00 | Demonstracje i proces | Czyja jest Twoja domena (powtórka niewydanej karuzeli z 21.11, treść bez zmian) | Domena nie na Ciebie? Możesz stracić adres (100) | zapisy | DOMENA w komentarzu albo formularz |
| k3 | sobota 28.11, 10:00 | Oferta i sprzedaż | Zanim zamówisz stronę: 4 pytania do wykonawcy (szablon czy od zera, kto zmieni cennik, ile kosztuje utrzymanie, co po wdrożeniu) i nasze odpowiedzi + ceny "od" | Zanim zapłacisz za stronę, zadaj 4 pytania (81) | zapytania | OFERTA w komentarzu albo formularz |

Rolki (dzień później o tej samej godzinie: śr 25.11 14:00, pt 27.11 14:00, nd 29.11 10:00):
- k1: karuzela uczy, jak sprawdzić adres; rolka do każdego objawu (brak kłódki, wygasły certyfikat, stary link, zdjęcia) daje jedno rozwiązanie, bez instrukcji sprawdzania.
- k2: jak w planie z 16.11: każda nerwowa sytuacja z domeną dostaje jedną odpowiedź, bez OVH, Netlify i pakietów.
- k3: karuzela to lista pytań do dowolnego wykonawcy; rolka pokazuje tylko nasze odpowiedzi (kod od zera, panel, hosting bez opłat, wsparcie po wdrożeniu).

## Decyzje
- add_repo nie było dostępne jako narzędzie, ale repo było już sklonowane w katalogu roboczym z originem na ku80n/pagehub-ig, więc pracowałem na nim.
- k2 to karuzela o domenie z 16.11, która przez błąd Netlify nie wyszła. Nikt jej nie widział, więc to nie powtórka tematu. Zmienione tylko `when` i `publish_at`. Klucz w stanie jest nowy (`2026-11-23/k2`), stary wpis zostaje jako `missed`, więc nie ma ryzyka podwójnej publikacji.
- Oferta po tygodniu przerwy (była 14.11), zgodnie z rytmem "co drugi tydzień". Kąt inny niż 14.11 (tam: który pakiet wybrać); tu pytania, które warto zadać każdemu wykonawcy. Częściowo dotyka tematów z 7.11 (kod od zera, panel), ale z perspektywy porównania ofert.
- Case study (Envision Studio) nadal odłożone: `facts.md` ma tylko jedno zdanie o tej realizacji. Warto dopisać 3-4 konkretne funkcje tej strony.
- Słowa-klucze: HTTPS, DOMENA, OFERTA. Bez polskich znaków (np. KŁÓDKA), bo `tools/leads.py` dopasowuje słowo dokładnie i "klodka" by nie zadziałało.
- k3 slajd o panelu: "Do naszych stron podpinamy prosty panel" opiera się na `facts.md` (Decap CMS, "prosty panel, w którym klient sam zmienia teksty i zdjęcia") i na karuzeli z 7.11. Jeśli panel nie jest w każdym pakiecie, warto to poprawić przed sobotą.
- k1: "Netlify sam wystawia i odnawia certyfikat oraz przenosi z http na https" to fakt o Netlify ze źródła poniżej, nie nowa obietnica PageHub.
- `config/words.txt`: dopisane "https" (nazwa protokołu, spellcheck zgłaszał ją 20 razy). Żadnych literówek.
- Okładki przepisane po hookscore (pierwsze wersje: k1 59,6, k3 54,8). "Nie przepłać" odrzucone, bo było na okładce 14.11.
- `closing` "OGARNIEMY TO." nie jest użyty.
- Klatka z przyciskiem przy `--still 8.4` (jak w zeszłym tygodniu, 99 zawija się w pętli).

## Źródła (brak liczb spoza facts.md)
- Chrome oznacza strony HTTP jako niezabezpieczone: https://blog.google/products/chrome/milestone-chrome-security-marking-http-not-secure/ oraz https://security.googleblog.com/2018/02/a-secure-web-is-here-to-stay.html
- Netlify: automatyczny certyfikat Let's Encrypt, odnawianie, przekierowanie na https: https://docs.netlify.com/manage/domains/secure-domains-with-https/https-ssl/ oraz https://www.netlify.com/blog/2018/07/02/all-new-sites-on-netlify-are-https-by-default/
- Treści mieszane (pliki http na stronie https, blokowanie przez przeglądarkę): https://web.dev/articles/what-is-mixed-content
- Ostrzeżenie "Połączenie nie jest prywatne" przy wygasłym certyfikacie: https://www.ssl.com/guide/troubleshooting-ssl-tls-browser-errors-and-warnings/
- Liczby w postach: 800 zł, 1500 zł, domena na rok i na 2 lata, do 5 podstron z `facts.md`. "4 rzeczy", "4 pytania" to liczba elementów w samym poście. Żadnych statystyk.

## Bramki jakości
- hookscore okładek: k1 87, k2 100, k3 81,4.
- caption.py: podpisy IG i opisy rolek READY (wszystkie 6).
- detect.py (PASS): k1 IG 86,2, rolka 84,9, FB 77,0; k2 IG 88,9, rolka 92,3, FB 77,1; k3 IG 86,9, rolka 93,3, FB 72,6. k1 przepisany po pierwszym REVIEW (równe zdania, mało konkretów).
- humanize.py: podpisy i slajdy bez zmian i bez flag.
- spellcheck: 0 nieznanych słów. pl_check: 0 uwag. Brak długich myślników (sprawdzone w Pythonie).
- Okładki i slajdy środkowe obejrzane (k1 01 i 06, k3 01 i 07; k2 bez zmian od zeszłego tygodnia). k3 slajd 7 miał niezręczny nagłówek "Nasze pakiety: od", zmieniony na "Ile to kosztuje?".
- Klatki rolek obejrzane (pierwsze pytanie i koniec z przyciskiem): tekst w dwóch liniach, czytelny, przyciski HTTPS, DOMENA, OFERTA.
- Dry-run publish.py: karuzele gotowe 24.11 14:00, 26.11 14:00, 28.11 10:00; rolki gotowe 25.11 14:05, 27.11 14:05, 29.11 10:05. Dry-run nie sprawdza Netlify, więc nie wykrywa błędu 403.

## Lista kontrolna z audytu
| punkt | k1 | k2 | k3 |
| --- | --- | --- | --- |
| każde twierdzenie zgodne z `facts.md` | tak (Netlify i https ze źródłem) | tak | tak (patrz uwaga o panelu) |
| brak fikcyjnych klientów, opinii i wyników | tak | tak | tak |
| tekst czytelny na telefonie | tak | tak | tak |
| CTA i link poprawne (słowo-klucz, formularz, pagehub.pl) | tak | tak | tak |
| coś innego niż ostatnie publikacje | tak (pierwszy post o https i certyfikacie) | tak (nie wyszedł 21.11) | tak (pytania do wykonawcy, nie wybór pakietu) |
| rolka nie jest mechanicznym powtórzeniem karuzeli | tak | tak | tak |
| treść nie sugeruje człowieka za profilem | tak | tak | tak |
