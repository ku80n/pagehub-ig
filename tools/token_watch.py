#!/usr/bin/env python3
"""
token_watch.py - warn Jakub on Telegram before the Meta token stops working.

Runs hourly with the rest of the workflow. Asks Meta when the page token and
its data access expire, and sends one Telegram warning (repeated at most every
3 days) when either is under two weeks away or the token is already invalid.
It never fails the workflow: a problem here must not block publishing.
"""

import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from common import ApiError, env, graph, load_state, save_state, telegram

WARN_DAYS = 14
REPEAT_HOURS = 72
FIX = ("Wygeneruj nowy token: SETUP.md, kroki 2.3-2.6, i podmień sekret META_PAGE_TOKEN w GitHubie. "
       "Albo napisz do Claude, przeprowadzi Cię przez to.")


def fmt(ts):
    return datetime.fromtimestamp(ts, timezone.utc).astimezone(ZoneInfo("Europe/Warsaw")).strftime("%d.%m.%Y %H:%M")


def status(now=None):
    """Return (problems, summary) for the current META_PAGE_TOKEN."""
    now = now or datetime.now(timezone.utc).timestamp()
    token = env("META_PAGE_TOKEN")
    d = graph("GET", "debug_token", token, input_token=token).get("data", {})
    problems = []
    if not d.get("is_valid", False):
        problems.append("token Meta jest nieważny")
    exp, data_exp = d.get("expires_at", 0) or 0, d.get("data_access_expires_at", 0) or 0
    if exp and exp - now < WARN_DAYS * 86400:
        problems.append(f"token Meta wygasa {fmt(exp)}")
    if data_exp and data_exp - now < WARN_DAYS * 86400:
        problems.append(f"dostęp do danych Meta wygasa {fmt(data_exp)}")
    summary = ("bez wygasania" if not exp else f"wygasa {fmt(exp)}") + \
              (f", dostęp do danych do {fmt(data_exp)}" if data_exp else "")
    return problems, summary


def main():
    state = load_state("token_watch.json", {})
    now = datetime.now(timezone.utc)
    try:
        problems, summary = status(now.timestamp())
    except ApiError as e:
        problems, summary = [f"nie mogę sprawdzić tokenu Meta ({e})"], "nieznany"
    print("token:", summary)
    if not problems:
        if state:
            save_state("token_watch.json", {})
        return 0
    last = state.get("warned_at")
    if last and (now - datetime.fromisoformat(last)).total_seconds() < REPEAT_HOURS * 3600:
        return 0
    try:
        telegram("PageHub: " + "; ".join(problems) + ".\n\n" + FIX)
        save_state("token_watch.json", {"warned_at": now.isoformat(), "problems": problems})
    except Exception as e:  # noqa: BLE001 - never block the workflow
        print("nie udało się wysłać ostrzeżenia:", e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
