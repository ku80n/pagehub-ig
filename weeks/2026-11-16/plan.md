# Tydzień 16-22 listopada 2026

Zrobione automatycznie (zadanie poniedziałkowe, bez nadzoru). Raport tygodnia (`state/raport/2026-11-16.md`) wygenerował się poprawnie.

## Wnioski z raportu
- 14 obserwujących (+0), 0 leadów z komentarzy i wiadomości. Polubienia 0-6 na post.
- Najlepiej wypadła rolka i karuzela o kolorach (Edukacja, 6 i 4 polubienia). Panel (Demonstracje) i oferta słabo (0-2). Przy tak małych liczbach to sygnał, nie wniosek: po 2 tygodniach Edukacja z gotową listą do sprawdzenia radzi sobie lepiej niż demonstracja i oferta.
- Nadal brak zasięgu, zapisów i udostępnień (token bez `instagram_manage_insights`, SETUP.md 2.3).
- Decyzja: w tym tygodniu bez oferty (była w zeszłym, wychodzi co drugi tydzień). Wszystkie trzy posty to praktyczne listy do sprawdzenia na własnej stronie lub domenie, każdy z innego obszaru. `state/publish_failures.json` pusty, wszystko z zeszłego tygodnia wyszło.
- `ideas.md` nie ma otwartych pomysłów, więc tematy z filarów.

## Plan

| # | termin | filar | temat i kąt | okładka (hookscore) | cel | CTA |
| --- | --- | --- | --- | --- | --- | --- |
| k1 | wtorek 17.11, 14:00 | Edukacja i problemy klientów | Strona główna z samym "Witamy": 4 pytania, na które pierwszy ekran musi odpowiedzieć (co, gdzie, za ile, jak się umówić) | Tylko Witamy? Klient nie wie, co robisz (100) | zapisy | WITAMY w komentarzu albo formularz |
| k2 | czwartek 19.11, 14:00 | Lokalność | "mechanik Przemyśl": 4 rzeczy na stronie, dzięki którym Google wie, co robisz i gdzie (tytuł, słowa klientów, podstrona na usługę, Search Console) | Google nie wie, gdzie działasz? Sprawdź 4 rzeczy (84) | zapisy i udostępnienia | MIASTO w komentarzu albo formularz |
| k3 | sobota 21.11, 10:00 | Demonstracje i proces | Czyja jest Twoja domena: abonent, własny login, odnowienie, zmiana wykonawcy + jak ustawiamy domenę po stronie klienta | Domena nie na Ciebie? Możesz stracić adres (100) | zapisy | DOMENA w komentarzu albo formularz |

Rolki (dzień później o tej samej godzinie: śr 18.11 14:00, pt 20.11 14:00, nd 22.11 10:00):
- k1: zamiast listy pytań i wyjaśnień rolka daje do każdego braku jedno konkretne rozwiązanie na stronie (usługa w nagłówku, miasto na wierzchu, cena od, jeden przycisk).
- k2: każdy objaw ("Google Cię nie pokazuje", żargon, wszystko na jednej stronie) dostaje jedną konkretną poprawkę, bez tłumaczenia, jak działa Google.
- k3: każda nerwowa sytuacja z domeną (na wykonawcę, brak dostępu, wygasła, zmiana wykonawcy) dostaje jedną odpowiedź; rolka nie mówi o OVH, Netlify ani pakietach.

## Decyzje
- add_repo nie było dostępne jako narzędzie w tej sesji, ale repo było już podpięte i sklonowane w katalogu roboczym (push przez origin), więc pracowałem na nim.
- Case study (Envision Studio) odłożone: nie udało się otworzyć envisionstudio.pl, a `facts.md` ma tylko jedno zdanie o tej realizacji. Bez sprawdzenia, co jest na stronie, nie piszę o jej funkcjach. Warto dopisać do `facts.md` 3-4 konkretne funkcje tej strony, wtedy case study wejdzie w kolejnym tygodniu.
- k2 oznaczony jako Lokalność (wyszukiwania typu "usługa + miasto"), bo temat naprawdę dotyczy lokalnych firm. Nie obiecujemy pierwszego miejsca ani wyników, piszemy wprost, że nikt uczciwy tego nie robi. Map Google i wizytówki nie poruszamy, bo tego nie ma w ofercie.
- k3: "Domeny i DNS ustawiamy po Twojej stronie, w OVH albo Netlify" to sformułowanie z `facts.md` ("po stronie klienta"). Odpowiedź rolki "ABONENTEM JESTEŚ TY." to rada dla widza, nie obietnica, ale jeśli w PageHub domena bywa rejestrowana inaczej, warto poprawić przed sobotą.
- Słowa-klucze WITAMY, MIASTO, DOMENA: nowe, inne niż w poprzednich tygodniach, pasują do tematu. Po CTA w opisach IG jest też formularz na pagehub.pl.
- Okładki przepisane po pierwszym hookscore (pierwsze wersje: 28, 50, 50).
- `closing` "OGARNIEMY TO." nie jest użyty.
- Kontrola klatek rolek: `--still 99` zawija się w pętli (czas modulo długość rolki) i pokazuje przejście, więc klatkę z przyciskiem zrobiłem przy `--still 8.4`. Wszystkie trzy przyciski i puenty czytelne.

## Źródła (brak liczb spoza facts.md)
- Tytuł strony jako niebieski link w wynikach i zalecenie opisowych tytułów: https://developers.google.com/search/docs/appearance/title-link
- Słowa, których szukają ludzie, w treści i nagłówkach; porządek treści na stronie: https://developers.google.com/search/docs/fundamentals/seo-starter-guide
- Search Console: sprawdzenie, czy strona jest w indeksie, prośba o ponowne zindeksowanie: https://support.google.com/webmasters/answer/9012289 oraz https://developers.google.com/search/docs/crawling-indexing/ask-google-to-recrawl
- Liczby w postach: 800 zł, 1500 zł, domena na rok i na 2 lata z `facts.md`. "4 pytania", "4 rzeczy" to liczba elementów w samym poście. Żadnych statystyk.

## Bramki jakości
- hookscore okładek: k1 100, k2 84,4, k3 100.
- caption.py: wszystkie podpisy IG i opisy rolek READY (k1 i k3 IG miały WARN "2 asks" z "zapisz" + słowo-klucz, w podpisach zostało jedno wezwanie).
- detect.py (PASS): k1 IG 100, rolka 99,5, FB 100; k2 IG 79,5, rolka 88,6, FB 89,5; k3 IG 88,9, rolka 92,3, FB 77,1. Wcześniej REVIEW przez niską konkretność i równe zdania, przepisane.
- humanize.py: podpisy i slajdy bez zmian i bez flag.
- spellcheck: 0 nieznanych słów. pl_check: 0 uwag. Brak długich myślników (sprawdzone w Pythonie, grep bez UTF-8 dawał fałszywe trafienia na polskich literach).
- Usunięte retoryczne liczby z wersji roboczych ("Zero.", "Pięć minut").
- Okładki i slajdy środkowe obejrzane (k1 01 i 03, k2 01 i 05, k3 01 i 07): bez ucięć i zlepionych słów.
- Klatki rolek obejrzane (pierwsze pytanie, środek, koniec z przyciskiem): tekst w dwóch liniach, czytelny. W k2 najdłuższe pytanie ("WSZYSTKO NA JEDNEJ STRONIE?") lekko zmniejsza tekst, nadal czytelny.
- Dry-run publish.py: karuzele gotowe 17.11 14:00, 19.11 14:00, 21.11 10:00; rolki gotowe 18.11 14:05, 20.11 14:05, 22.11 10:05.

## Lista kontrolna z audytu
| punkt | k1 | k2 | k3 |
| --- | --- | --- | --- |
| każde twierdzenie zgodne z `facts.md` | tak | tak | tak (patrz uwaga o domenie) |
| brak fikcyjnych klientów, opinii i wyników | tak (przykłady usług opisane jako przykłady) | tak | tak |
| tekst czytelny na telefonie | tak | tak | tak |
| CTA i link poprawne (słowo-klucz, formularz, pagehub.pl) | tak | tak | tak |
| coś innego niż ostatnie publikacje | tak (treść strony głównej, wcześniej był wygląd na telefonie i szybkość) | tak (pierwszy post o widoczności w Google) | tak (pierwszy post o domenie) |
| rolka nie jest mechanicznym powtórzeniem karuzeli | tak | tak | tak |
| treść nie sugeruje człowieka za profilem | tak | tak | tak |
