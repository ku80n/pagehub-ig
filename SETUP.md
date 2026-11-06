# Jednorazowa konfiguracja (ok. 30 minut)

Potrzebujesz komputera i dostępu do konta Instagram, strony PageHub na Facebooku, Netlify i Telegrama.
Tokeny wpisujesz tylko w GitHub Secrets (krok 5). **Nie wklejaj ich do czatu z Claude** ani nigdzie indziej.
Nazwy przycisków u Meta czasem się zmieniają, więc mogą się trochę różnić od opisu.

## 1. Instagram jako konto firmowe (5 min)
1. Instagram: Ustawienia -> Typ konta i narzędzia -> przełącz na konto profesjonalne (Firma). Jeśli już jest, pomiń.
2. Połącz konto IG ze stroną PageHub na Facebooku: Meta Business Suite -> Ustawienia -> Konta -> Konta na Instagramie
   (albo w ustawieniach strony na Facebooku: Połączone konta -> Instagram).
3. W aplikacji Instagram na telefonie: Ustawienia i aktywność -> Wiadomości i odpowiedzi na relacje
   -> Kontrola wiadomości (ang. Message controls) -> Połączone narzędzia -> włącz **Zezwalaj na dostęp do wiadomości**.
   - Opcja pojawia się dopiero, gdy konto jest profesjonalne i połączone ze stroną na Facebooku (punkty 1 i 2).
   - Nie możesz znaleźć? Wpisz "połączone narzędzia" albo "dostęp do wiadomości" w wyszukiwarkę na górze ustawień.
   - Nadal brak? Pomiń. Publikacja i komentarze działają bez tego, a test z kroku 6 pokaże, czy DM-y są dostępne.

## 2. Aplikacja Meta i token (15 min)
1. Wejdź na https://developers.facebook.com -> Moje aplikacje -> Utwórz aplikację.
   Przypadek użycia: **Inne**, typ: **Firma**. Nazwa np. `PageHub Publisher`. Aplikacja może zostać w trybie deweloperskim:
   jako jej administrator publikujesz na własne konto bez weryfikacji przez Meta.
2. W panelu aplikacji dodaj produkt **Instagram** (wariant z logowaniem przez Facebooka).
3. Otwórz Graph API Explorer: https://developers.facebook.com/tools/explorer
   - po prawej wybierz swoją aplikację,
   - "Użytkownik lub strona" -> **Get User Access Token**,
   - zaznacz uprawnienia: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `pages_manage_metadata`,
     `business_management`, `instagram_basic`, `instagram_content_publish`, `instagram_manage_comments`, `instagram_manage_messages`, `instagram_manage_insights`, `read_insights`,
   - **Generate Access Token**, zaloguj się i zaznacz stronę PageHub oraz konto Instagram.
4. Przedłuż token: https://developers.facebook.com/tools/debug/accesstoken -> wklej token -> **Debug** -> na dole **Extend Access Token** -> skopiuj nowy token.
5. Wróć do Graph API Explorer, wklej przedłużony token w pole Access Token i wykonaj zapytanie GET:
   ```
   me/accounts?fields=name,access_token,instagram_business_account
   ```
   Przy stronie PageHub znajdziesz trzy wartości:
   - `access_token` -> to jest **META_PAGE_TOKEN**
   - `id` -> to jest **FB_PAGE_ID**
   - `instagram_business_account.id` -> to jest **IG_USER_ID**
6. Wklej `access_token` strony do Access Token Debuggera i sprawdź, że **Expires: Never**. Jeśli ma datę, powtórz krok 4 i 5.

## 3. Netlify na grafiki (3 min)
Instagram pobiera zdjęcia z publicznego adresu, więc grafiki lądują na małej, osobnej stronie (Netlify nazywa ją teraz "projektem").
1. Rozpakuj `pagehub-media.zip` (z czatu) - dostaniesz folder `pagehub-media` z jednym plikiem `index.html`.
2. Zaloguj się i otwórz https://app.netlify.com/drop -> przeciągnij folder `pagehub-media` na pole do upuszczania.
   (To samo jest w Projects -> **Add new project** -> **Deploy manually**.) Nazwa projektu nie ma znaczenia.
3. W nowym projekcie: **Project configuration** -> General -> Project details -> skopiuj **Project ID** -> to jest **NETLIFY_SITE_ID**.
   W tym samym miejscu: **Visitor access** -> Project visibility -> Edit visibility -> **Public** -> Save.
   Nowe projekty bywają domyślnie prywatne, a wtedy Instagram nie pobierze grafik (błąd 401).
4. Avatar -> **User settings** -> **OAuth** (albo Applications) -> Personal access tokens -> **New access token**,
   opis `pagehub-ig`, ważność: bez wygasania (albo najdłuższa) -> Generate -> skopiuj od razu (pokazuje się raz) -> to jest **NETLIFY_AUTH_TOKEN**.

## 4. Telegram (3 min)
1. Napisz do **@BotFather**: `/newbot`, podaj nazwę (np. PageHub Klienci) i login bota. Dostaniesz token -> **TELEGRAM_BOT_TOKEN**.
2. Otwórz swojego nowego bota i wyślij mu `/start`. Bez tego bot nie może do Ciebie pisać.
3. Napisz do **@userinfobot** - odpisze Twoim `Id` -> to jest **TELEGRAM_CHAT_ID**.

## 5. Sekrety w GitHubie (3 min)
https://github.com/ku80n/pagehub-ig -> Settings -> Secrets and variables -> Actions -> **New repository secret**.
Dodaj 7 sekretów (nazwa dokładnie taka jak niżej):

| nazwa | skąd |
| --- | --- |
| META_PAGE_TOKEN | krok 2.5, `access_token` strony |
| IG_USER_ID | krok 2.5, `instagram_business_account.id` |
| FB_PAGE_ID | krok 2.5, `id` strony |
| NETLIFY_AUTH_TOKEN | krok 3.4 |
| NETLIFY_SITE_ID | krok 3.3 |
| TELEGRAM_BOT_TOKEN | krok 4.1 |
| TELEGRAM_CHAT_ID | krok 4.3 |

## 6. Test (1 min)
Repo -> **Actions** -> Instagram PageHub -> **Run workflow** -> mode: `check` -> Run workflow.
Po minucie dostaniesz na Telegramie raport: każda linia OK albo BŁĄD z opisem. Jeśli wszystko OK - gotowe.

Od tej chwili workflow działa co godzinę od 6 do 23: publikuje karuzele o ich godzinie i przysyła Ci potencjalnych klientów.
Pierwsze uruchomienie tylko oznacza istniejące komentarze jako przeczytane, więc nie dostaniesz zaległości.

## Na co dzień
- **Nic nie musisz robić.** Na Telegram przychodzą tylko klienci i ewentualne błędy publikacji.
- **Pauza:** w repo Add file -> Create new file -> nazwa `config/PAUZA` -> Commit. Usuń plik, żeby wznowić.
- **Pomysły:** dopisuj do `ideas.md`. **Nowe realizacje:** do `config/facts.md`.
- **Wyłączenie Facebooka:** dodaj zmienną repo `PUBLISH_FB` = `false` (Settings -> Secrets and variables -> Actions -> zakładka Variables).
