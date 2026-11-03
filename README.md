# PageHub - Instagram

Automatyczna, cotygodniowa paczka 3 karuzel na Instagram PageHub.

W każdy poniedziałek rano Claude:
1. planuje 3 karuzele (filary z `config/pillars.md`, pomysły z `ideas.md`),
2. pisze slajdy i podpisy (IG + FB) w głosie z `config/voice.md`,
3. przepuszcza je przez bramki jakości (hook, podpis, styl, fakty),
4. renderuje grafiki 1080x1350 w stylu PageHub i commituje tydzień do `weeks/`.

Potem GitHub Actions (co godzinę, 6-23):
- publikuje karuzele na Instagramie i Facebooku o godzinie z `publish_at`,
- rolki (animacja pisanego tekstu z dźwiękiem) dzień po karuzeli, jeśli istnieje plik `config/ROLKI`,
- wysyła na Telegram potencjalnych klientów: komentarze ze słowem-kluczem lub pytaniem o stronę/cenę i nowe wiadomości DM.

Konfiguracja jednorazowa: `SETUP.md`. Pauza: plik `config/PAUZA`.

## Co możesz edytować
- `ideas.md` - wrzucaj tu pomysły w ciągu tygodnia, mają pierwszeństwo
- `config/facts.md` - nowe realizacje i fakty (tylko stąd biorą się konkrety o PageHub)
- `config/brand.md` - terminy publikacji, hashtagi, handle
- `config/voice.md` - styl pisania

## Zawartość
- `skills/` - pakiet [instagram-agent-skill](https://github.com/Jakeschincariol/instagram-agent-skill) (MIT) ze spolszczonymi skryptami
- `tools/render_carousel.py` - JSON -> slajdy PNG
- `tools/build_page.py` - strona z podglądem tygodnia
- `tools/publish.py` - publikacja przez API Instagrama i Facebooka
- `tools/make_reel.py` - rolka 9:16 ze slajdów karuzeli
- `tools/leads.py` - powiadomienia o potencjalnych klientach na Telegram
- `.github/workflows/instagram.yml` - harmonogram publikacji i powiadomień
- `WEEKLY.md` - instrukcja, którą wykonuje cotygodniowe zadanie
