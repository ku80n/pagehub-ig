# PageHub - Instagram

Automatyczna, cotygodniowa paczka 3 karuzel na Instagram PageHub.

W każdy poniedziałek rano Claude:
1. planuje 3 karuzele (filary z `config/pillars.md`, pomysły z `ideas.md`),
2. pisze slajdy i podpisy (IG + FB) w głosie z `config/voice.md`,
3. sprawdza je skryptami (hook, podpis, wykrywanie "AI-owego" stylu),
4. renderuje grafiki 1080x1350 w stylu PageHub,
5. odświeża stronę z podglądem i wrzuca ZIP do czatu,
6. commituje tydzień do `weeks/`.

Nic nie jest publikowane automatycznie. Przeglądasz, poprawiasz i planujesz w Meta Business Suite.

## Co możesz edytować
- `ideas.md` - wrzucaj tu pomysły w ciągu tygodnia, mają pierwszeństwo
- `config/facts.md` - nowe realizacje i fakty (tylko stąd biorą się konkrety o PageHub)
- `config/brand.md` - terminy publikacji, hashtagi, handle
- `config/voice.md` - styl pisania

## Zawartość
- `skills/` - pakiet [instagram-agent-skill](https://github.com/Jakeschincariol/instagram-agent-skill) (MIT) ze spolszczonymi skryptami
- `tools/render_carousel.py` - JSON -> slajdy PNG
- `tools/build_page.py` - strona z podglądem tygodnia
- `WEEKLY.md` - instrukcja, którą wykonuje cotygodniowe zadanie
