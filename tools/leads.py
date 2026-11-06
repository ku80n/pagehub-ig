#!/usr/bin/env python3
"""
leads.py - tell Jakub on Telegram when somebody looks like a potential client.

Runs hourly from GitHub Actions, after publish.py. Reads the comments under
PageHub's posts from the last 30 days and the Instagram DMs, and sends one
Telegram message per lead with a link and a suggested first reply. Nothing is
answered automatically: Jakub replies himself in the Instagram app.

A lead is:
  - a comment containing the post's keyword (meta.cta_keyword, e.g. TELEFON),
  - a comment that asks about a website, a price or working together,
  - any new direct message.
Everything else (emoji, "super", spam) is ignored.

The first run only marks what already exists as seen, so turning this on does
not flood the phone with old comments.

Usage
  python3 tools/leads.py
  python3 tools/leads.py --selftest     # offline check of the lead filter
"""

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone

from common import ROOT, ApiError, env, graph, graph_pages, load_state, save_state, telegram

WINDOW = timedelta(days=30)          # how far back to look at our own posts
DM_WINDOW = timedelta(days=7)
KEEP_IDS = 3000                      # seen-id memory, newest kept

INTENT = re.compile(
    r"\b(?:ile\s+(?:kosztuje|kosztowałaby|to\s+kosztuje|bierzecie|za)|cen[aęyie]\w*|cennik\w*"
    r"|koszt\w*|wycen\w*|ofert\w*|zlec\w*|potrzebuj\w*|szukam\w*|chciał(?:a|)by\w*|chcę\s+stron\w*"
    r"|zrobi(?:cie|łbyś|libyście|sz)\w*|stron[aęyie]?\s+(?:dla|do|na)|now(?:ą|a)\s+stron\w*"
    r"|kontakt\w*|współprac\w*|termin\w*|napisz(?:cie)?\s+do\s+mnie|priv|pw|dm)\b",
    re.IGNORECASE)

DEFAULT_REPLY = ("Cześć! Dzięki za wiadomość. Napisz proszę, czego potrzebujesz i jaki jest adres "
                 "Twojej obecnej strony (jeśli jest), a odezwiemy się z konkretami.")


def is_lead(text, keywords):
    """Return a short reason if the text looks like a potential client, else None."""
    t = (text or "").strip()
    if not t:
        return None
    for kw in keywords:
        if kw and re.search(rf"(?<!\w){re.escape(kw)}(?!\w)", t, re.IGNORECASE):
            return f"słowo-klucz {kw.upper()}"
    if INTENT.search(t):
        return "pyta o stronę, cenę lub kontakt"
    return None


def parse_time(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S%z")


def keywords_by_media():
    """ig_media_id -> (keyword, reply hint, topic) from what publish.py recorded."""
    published = load_state("published.json", {})
    specs = {}
    for path in ROOT.glob("weeks/*/k*.json"):
        specs[f"{path.parent.name}/{path.stem}"] = json.loads(path.read_text(encoding="utf-8")).get("meta", {})
    out = {}
    for key, rec in published.items():
        if rec.get("ig_media_id"):
            meta = specs.get(key.split("#")[0], {})
            out[rec["ig_media_id"]] = (meta.get("cta_keyword") or rec.get("cta_keyword", ""),
                                       meta.get("reply_hint", ""), meta.get("topic", key))
    return out


def fetch_comments(token, ig, own):
    since = datetime.now(timezone.utc) - WINDOW
    for m in graph_pages(f"{ig}/media", token, fields="id,permalink,timestamp", limit=25):
        if parse_time(m["timestamp"]) < since:
            break
        fields = "id,text,username,timestamp,replies{id,text,username,timestamp}"
        for c in graph_pages(f"{m['id']}/comments", token, fields=fields, limit=50):
            for item in [c] + c.get("replies", {}).get("data", []):
                if item.get("username", "").lower() != own.lower():
                    yield m, item


def fetch_dms(token, page, ig):
    since = datetime.now(timezone.utc) - DM_WINDOW
    fields = "id,updated_time,messages.limit(10){id,message,from,created_time}"
    for conv in graph_pages(f"{page}/conversations", token, platform="instagram", fields=fields, limit=25):
        if parse_time(conv["updated_time"]) < since:
            break
        for msg in conv.get("messages", {}).get("data", []):
            sender = msg.get("from", {})
            if sender.get("id") != ig:
                yield conv, msg, sender.get("username", "ktoś")


def run():
    token, ig, page = env("META_PAGE_TOKEN"), env("IG_USER_ID"), env("FB_PAGE_ID")
    state = load_state("leads.json", {"initialized": False, "comments": [], "messages": []})
    seen_c, seen_m = set(state["comments"]), set(state["messages"])
    first_run = not state["initialized"]
    own = graph("GET", ig, token, fields="username")["username"]
    kw_map = keywords_by_media()
    all_kw = sorted({v[0] for v in kw_map.values() if v[0]})
    alerts = []
    log = state.get("log", [])       # what was sent, for the weekly report (no usernames)

    for media, c in fetch_comments(token, ig, own):
        if c["id"] in seen_c:
            continue
        seen_c.add(c["id"])
        kw, hint, topic = kw_map.get(media["id"], ("", "", ""))
        reason = is_lead(c.get("text"), [kw] + all_kw)
        if reason and not first_run:
            log.append({"at": c.get("timestamp", ""), "kind": "komentarz", "media": media["id"], "reason": reason})
            user = c.get("username", "")
            alerts.append(
                f"Potencjalny klient: komentarz ({reason})\n"
                f"@{user}: \"{c.get('text', '').strip()[:300]}\"\n\n"
                f"Post: {media.get('permalink', '')}\n"
                f"Profil: https://www.instagram.com/{user}/\n\n"
                f"Proponowana odpowiedź (w DM):\n{hint or DEFAULT_REPLY}")

    try:
        new_by_conv = {}
        for conv, msg, user in fetch_dms(token, page, ig):
            if msg["id"] in seen_m:
                continue
            seen_m.add(msg["id"])
            new_by_conv.setdefault(conv["id"], (user, []))[1].append(msg.get("message") or "(załącznik)")
        if not first_run:
            for user, texts in new_by_conv.values():
                log.append({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "kind": "wiadomość"})
                alerts.append(
                    f"Nowa wiadomość na Instagramie\n@{user}: \"{' / '.join(reversed(texts))[:400]}\"\n\n"
                    f"Odpowiedz w aplikacji Instagram, w Wiadomościach.\n"
                    f"Proponowana odpowiedź:\n{DEFAULT_REPLY}")
    except ApiError as e:
        alerts.append(f"PageHub: nie mogę odczytać wiadomości DM ({e}). Komentarze działają dalej.")

    for a in alerts:
        telegram(a)
    if first_run:
        telegram("PageHub: śledzenie komentarzy i wiadomości jest włączone. "
                 "Od teraz dostaniesz tu każdego potencjalnego klienta.")
    state.update(initialized=True, comments=sorted(seen_c)[-KEEP_IDS:], messages=sorted(seen_m)[-KEEP_IDS:],
                 log=log[-500:])
    save_state("leads.json", state)
    print(f"leady: {len(alerts)} powiadomień" + (" (pierwsze uruchomienie, tylko oznaczono)" if first_run else ""))
    return 0


def selftest():
    cases = [
        ("TELEFON", ["TELEFON"], True), ("telefon 🙏", ["TELEFON"], True),
        ("Ile kosztuje taka strona?", [], True), ("Zrobicie stronę dla salonu?", [], True),
        ("Potrzebuję nowej strony", [], True), ("szukam kogoś do strony www", [], True),
        ("Napiszcie do mnie", [], True), ("pw", [], True),
        ("Super post 🔥", ["TELEFON"], False), ("Dzięki, przydatne", [], False),
        ("🔥🔥🔥", [], False), ("Mój telefonik ma 5 lat", ["TELEFON"], False),
    ]
    bad = [(t, exp) for t, kws, exp in cases if bool(is_lead(t, kws)) != exp]
    for t, exp in bad:
        print(f"BŁĄD: {t!r} -> oczekiwano {'lead' if exp else 'brak'}")
    print(f"selftest: {len(cases) - len(bad)}/{len(cases)} OK")
    return 1 if bad else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    sys.exit(selftest() if a.selftest else run())
