---
name: pl-naturalnie
description: >-
  Pisanie i poprawianie polskich tekstów do social mediów i lektora tak, żeby
  brzmiały jak człowiek, a nie jak tłumaczenie z angielskiego albo korpo-ulotka.
  Używaj zawsze przed publikacją karuzeli, rolki, opisu, DM-a i tekstu lektora.
---

# pl-naturalnie

Tekst ma brzmieć tak, jak Jakub powiedziałby to właścicielowi firmy przy kawie:
krótko, konkretnie, po ludzku, z kulturą. Nie jak broszura i nie jak tłumaczenie.

Narzędzie, które sprawdza to automatycznie (kalki, korpomowa, tekst lektora):

```bash
python3 tools/pl_check.py weeks/<data>        # wszystkie kN.json tygodnia
```

Wynik musi być czysty. Każde ostrzeżenie poprawiasz w tekście albo, jeśli to fałszywy alarm, zostawiasz i opisujesz w `plan.md` dlaczego.

## Zasady

1. **Przeczytaj na głos.** Jeśli zdanie brzmi dziwnie powiedziane do kogoś, przepisz je. Szczególnie tekst lektora.
2. **"Twój", "Twoja", "Ci" wielką literą**, jak pisze Jakub ("Sprawdź, zanim znajdzie je Twój klient!"). Spójnie w całym tekście. W tekście lektora wielkość liter nie ma znaczenia.
3. **Czasownik, nie rzeczownik.** "Da się czytać bez powiększania" zamiast "Tekst bez powiększania". "Sprawdź, czy..." zamiast "Weryfikacja...".
4. **Pytanie zamiast hasła**, gdy to możliwe. "Strona ładuje się dłużej niż 3 sekundy?" działa lepiej niż "Wolne ładowanie strony".
5. **Krótkie zdania.** Jedno zdanie, jedna myśl. Kropka zamiast trzeciego przecinka.
6. **Bez kalek z angielskiego** (pełna lista w `kalki.json`): "Oto...", "zanim zrobi to on", "na start", "pod kciuk", "dedykowany", "zaadresować problem", "robić różnicę", "na koniec dnia", "w temacie", "finalnie", "dostarczać wartość".
7. **Bez korpomowy:** kompleksowy, innowacyjny, szyte na miarę, na najwyższym poziomie, profesjonalne podejście, przenieś biznes na wyższy poziom.
8. **Konkret zamiast przymiotnika.** "Ładuje się w 1 sekundę" zamiast "błyskawiczna strona".
9. **Mówimy "my" o PageHub** (robimy, odezwiemy się), a do klienta na "ty".

## Tekst lektora (rolki)

Lektor czyta ekrany rolki słowo w słowo (okładka, nagłówek listy i punkty, zdanie końcowe, przycisk),
więc każdy z tych tekstów musi brzmieć dobrze na głos:
- bez skrótów (np., itd., zł, www), symboli (%, &, /), nawiasów, strzałek i linków; liczby są OK, lektor czyta je słownie,
- emocje robi interpunkcja na ekranie: pytanie kończy się "?", mocne zdanie "!",
- unikaj zbitek, które lektor połyka (sprawdzone na nagraniach): "a odezwiemy się z wyceną" -> "a przygotujemy wycenę",
- `pl_check.py` sprawdza ekrany rolki pod tym kątem, a automat lektora zapisuje w `voice.json`, co usłyszało rozpoznawanie mowy.

## Przed i po

| przed | po |
| --- | --- |
| Tekst bez powiększania | Da się czytać bez powiększania |
| Przyciski pod kciuk | Przyciski łatwo trafić palcem |
| Oto 5 najczęstszych powodów, przez które strona jest wolna. | Najczęściej winne jest jedno z tych pięciu. |
| Wolna strona oddaje klientów konkurencji. | Wolna strona? Klient pójdzie do konkurencji. |
| Chcesz stronę zrobioną od zera pod Twoją firmę? | Chcesz stronę zrobioną specjalnie dla Twojej firmy? |
| Film w tle na start | Film w tle na stronie głównej |
| Sprawdź swoją stronę, zanim zrobi to on. | Sprawdź swoją stronę, zanim zrobi to klient. |

## Jak pisze Jakub (wzór tonu)

Wiadomość, którą sam zatwierdził do potencjalnego klienta:

> Cześć! Przeglądałem Waszą stronę (carlovers.me) i zauważyłem, że przy wejściu przeglądarka wyświetla
> ostrzeżenie "Połączenie nie jest prywatne". To problem z certyfikatem SSL, przez który część osób może
> rezygnować z wejścia. [...] Czy bylibyście zainteresowani jej odświeżeniem? Dajcie znać :)

Luźno, ale z kulturą. Konkret na początku, jedno pytanie na końcu, zero nadęcia.
