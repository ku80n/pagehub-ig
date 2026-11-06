#!/usr/bin/env python3
"""
report.py - weekly Instagram report, for Jakub and for the Monday planner.

Runs on Monday morning before the new week is planned (workflow mode "report",
dispatched by the Monday scheduled task). For every post from the last 28 days
it reads what Meta gives: reach, views, saves, shares, likes, comments, profile
visits and follows, for Reels also the average watch time. For the account:
followers, reach, profile visits, bio link taps. Leads come from the log that
leads.py keeps.

Saves state/raport/<data>.json and .md (WEEKLY.md reads the newest one before
planning) and sends a short summary to Telegram.

Without the instagram_manage_insights permission Meta returns only likes,
comments and followers. The report then says so and works with that.

Usage
  python3 tools/report.py              # save + Telegram
  python3 tools/report.py --dry-run    # print only, nothing saved or sent
  python3 tools/report.py --selftest   # offline check of the formatting
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from common import ROOT, STATE, ApiError, env, graph, load_state, telegram

TZ = ZoneInfo("Europe/Warsaw")
WINDOW = timedelta(days=28)
FEED = ["reach", "views", "saved", "shares", "likes", "comments", "total_interactions",
        "profile_visits", "follows"]
REELS = ["reach", "views", "saved", "shares", "likes", "comments", "total_interactions",
         "ig_reels_avg_watch_time"]
ACCOUNT = ["reach", "views", "accounts_engaged", "total_interactions", "profile_views",
           "profile_links_taps", "website_clicks", "follows_and_unfollows"]
DAYS = ["pn", "wt", "śr", "czw", "pt", "sob", "nd"]
NO_INSIGHTS = ("Meta nie daje mi zasięgu, wyświetleń i zapisów, bo token nie ma uprawnienia "
               "instagram_manage_insights. Przy najbliższej wymianie tokenu zaznacz też "
               "instagram_manage_insights i read_insights (SETUP.md, krok 2.3).")


class NoPermission(Exception):
    pass


def _denied(e):
    msg = str(e).lower()
    return "permission" in msg or "(#10)" in msg or "(#200)" in msg


def _values(resp):
    out = {}
    for item in resp.get("data", []):
        if item.get("total_value"):
            out[item["name"]] = item["total_value"].get("value")
        elif item.get("values"):
            out[item["name"]] = item["values"][0].get("value")
    return out


def insights(path, metrics, token, **params):
    """All metrics at once; when Meta rejects the set, one by one, dropping the
    ones it does not support for this object. A missing permission stops it."""
    try:
        return _values(graph("GET", f"{path}/insights", token, metric=",".join(metrics), **params))
    except ApiError as e:
        if _denied(e):
            raise NoPermission(str(e)) from None
    out = {}
    for m in metrics:
        try:
            out.update(_values(graph("GET", f"{path}/insights", token, metric=m, **params)))
        except ApiError as e:
            if _denied(e):
                raise NoPermission(str(e)) from None
    return out


def week_range(now):
    """The finished week before `now` (Monday 00:00 to Monday 00:00)."""
    start_today = now.astimezone(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    until = start_today - timedelta(days=start_today.weekday()) if start_today.weekday() else start_today
    return until - timedelta(days=7), until


def post_meta():
    """ig_media_id -> (key, kind, meta of the carousel file)"""
    out = {}
    for key, rec in load_state("published.json", {}).items():
        mid = rec.get("ig_media_id")
        if not mid or rec.get("status") != "published":
            continue
        base, _, kind = key.partition("#")
        path = ROOT / "weeks" / (base + ".json")
        meta = json.loads(path.read_text(encoding="utf-8")).get("meta", {}) if path.exists() else {}
        out[mid] = (key, kind or "carousel", meta)
    return out


def collect(now):
    token, ig = env("META_PAGE_TOKEN"), env("IG_USER_ID")
    since, until = week_range(now)
    known = post_meta()
    data = {"made_at": now.isoformat(timespec="seconds"), "week": [since.date().isoformat(),
            (until - timedelta(days=1)).date().isoformat()], "insights": True, "posts": [], "account": {}}

    acc = graph("GET", ig, token, fields="username,followers_count,follows_count,media_count")
    data["account"].update({k: acc.get(k) for k in ("followers_count", "follows_count", "media_count")})

    media = graph("GET", f"{ig}/media", token, limit=50,
                  fields="id,caption,media_type,media_product_type,timestamp,permalink,like_count,comments_count")
    for m in media.get("data", []):
        at = datetime.fromisoformat(m["timestamp"].replace("+0000", "+00:00"))
        if now - at > WINDOW:
            continue
        key, kind, meta = known.get(m["id"], ("", "", {}))
        reel = m.get("media_product_type") == "REELS"
        post = {"id": m["id"], "key": key or "ręcznie", "kind": "rolka" if reel else "karuzela",
                "at": at.astimezone(TZ).isoformat(timespec="minutes"), "permalink": m.get("permalink"),
                "topic": meta.get("topic") or (m.get("caption") or "").split("\n")[0][:80],
                "pillar": meta.get("pillar", ""), "cta_keyword": meta.get("cta_keyword", ""),
                "likes": m.get("like_count"), "comments": m.get("comments_count")}
        if data["insights"]:
            try:
                post.update({k: v for k, v in insights(m["id"], REELS if reel else FEED, token).items()
                             if v is not None})
            except NoPermission as e:
                data["insights"], data["insights_error"] = False, str(e)[:200]
        data["posts"].append(post)

    if data["insights"]:
        try:
            data["account"].update(insights(ig, ACCOUNT, token, period="day", metric_type="total_value",
                                            since=int(since.timestamp()), until=int(until.timestamp())))
        except NoPermission as e:
            data["insights"], data["insights_error"] = False, str(e)[:200]

    log = load_state("leads.json", {}).get("log", [])
    def in_week(e):
        try:
            return since <= datetime.fromisoformat(e["at"].replace("+0000", "+00:00")) < until
        except (KeyError, ValueError):
            return False
    week_leads = [e for e in log if in_week(e)]
    data["leads"] = {"komentarze": sum(e.get("kind") == "komentarz" for e in week_leads),
                     "wiadomości": sum(e.get("kind") == "wiadomość" for e in week_leads)}
    by_media = {}
    for e in log:
        if e.get("media"):
            by_media[e["media"]] = by_media.get(e["media"], 0) + 1
    for p in data["posts"]:
        p["leads"] = by_media.get(p["id"], 0)
    return data


# ---------------------------------------------------------------- formatting

def num(v):
    if isinstance(v, float):
        return f"{v:.1f}".replace(".", ",")
    return str(v)


def post_line(p, full=False):
    at = datetime.fromisoformat(p["at"])
    parts = []
    if p["kind"] == "rolka" and p.get("views") is not None:
        parts.append(f"wyświetlenia {num(p['views'])}")
    for k, label in (("reach", "zasięg"), ("saved", "zapisy"), ("shares", "udostępnienia"),
                     ("likes", "polubienia"), ("comments", "komentarze")):
        if p.get(k) is not None:
            parts.append(f"{label} {num(p[k])}")
    if p.get("ig_reels_avg_watch_time") is not None:
        parts.append(f"śr. oglądanie {num(p['ig_reels_avg_watch_time'] / 1000)} s")
    if full:
        for k, label in (("profile_visits", "wejścia na profil"), ("follows", "nowi obserwujący")):
            if p.get(k) is not None:
                parts.append(f"{label} {num(p[k])}")
    if p.get("leads"):
        parts.append(f"leady {p['leads']}")
    return f"{DAYS[at.weekday()]} {at:%d.%m} {p['kind']} \"{p['topic'][:60]}\": " + ", ".join(parts)


def score(p):
    """Saves and shares say most about value, comments next, likes least."""
    return 4 * (p.get("saved") or 0) + 4 * (p.get("shares") or 0) + 3 * (p.get("leads") or 0) \
        + 2 * (p.get("comments") or 0) + (p.get("likes") or 0)


def previous_followers(today):
    folder = STATE / "raport"
    for f in sorted(folder.glob("*.json"), reverse=True) if folder.exists() else []:
        if f.stem < today:
            return json.loads(f.read_text(encoding="utf-8")).get("account", {}).get("followers_count")
    return None


def summary(data, prev=None):
    a = data["account"]
    since, last = (datetime.fromisoformat(d) for d in data["week"])
    fol = a.get("followers_count")
    delta = f" ({'+' if fol - prev >= 0 else ''}{fol - prev})" if fol is not None and prev is not None else ""
    acc = [f"{fol} obserwujących{delta}"]
    for k, label in (("reach", "zasięg"), ("profile_views", "wejścia na profil"),
                     ("profile_links_taps", "kliknięcia w profilu"), ("website_clicks", "kliknięcia w link")):
        if a.get(k) is not None:
            acc.append(f"{label} {num(a[k])}")
    lines = [f"PageHub - raport tygodnia {since:%d.%m}-{last:%d.%m}", "",
             "Konto: " + ", ".join(acc),
             f"Leady: {data['leads']['komentarze']} z komentarzy, {data['leads']['wiadomości']} z wiadomości"]
    week = [p for p in data["posts"] if since.date() <= datetime.fromisoformat(p["at"]).date() <= last.date()]
    lines += ["", "Publikacje z tego tygodnia:" if week else "W tym tygodniu nie było publikacji."]
    lines += ["- " + post_line(p) for p in sorted(week, key=lambda p: p["at"])]
    if len(week) > 1 and max(map(score, week)) > 0:
        best = max(week, key=score)
        lines += ["", f"Najwięcej wartości (zapisy, udostępnienia, leady): {best['kind']} \"{best['topic'][:60]}\". "
                      "Przy tak małych liczbach to sygnał, nie wniosek."]
    if not data["insights"]:
        lines += ["", NO_INSIGHTS]
    return "\n".join(lines)


def markdown(data, text):
    rows = ["| data | format | filar | temat | zasięg | wyśw. | zapisy | udost. | polub. | kom. | leady |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for p in sorted(data["posts"], key=lambda p: p["at"]):
        cells = [p["at"][:10], p["kind"], p["pillar"] or "-", p["topic"][:50].replace("|", "/")]
        cells += [num(p[k]) if p.get(k) is not None else "-"
                  for k in ("reach", "views", "saved", "shares", "likes", "comments", "leads")]
        rows.append("| " + " | ".join(cells) + " |")
    return (text + "\n\n## Publikacje z ostatnich 28 dni\n\n" + "\n".join(rows) + "\n\n"
            "Wnioski wyciągaj z kilku tygodni i grup podobnych postów, nie z jednego posta.\n")


def save(data, text):
    folder = STATE / "raport"
    folder.mkdir(parents=True, exist_ok=True)
    day = data["made_at"][:10]
    (folder / f"{day}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (folder / f"{day}.md").write_text(markdown(data, text), encoding="utf-8")


def selftest():
    data = {"made_at": "2026-11-09T06:30:00+01:00", "week": ["2026-11-02", "2026-11-08"], "insights": True,
            "account": {"followers_count": 41, "reach": 512, "profile_views": 18, "profile_links_taps": 2},
            "leads": {"komentarze": 1, "wiadomości": 0},
            "posts": [{"id": "1", "key": "2026-11-02/k2", "kind": "karuzela", "at": "2026-11-05T19:51+01:00",
                       "topic": "Telefon klienta", "pillar": "Edukacja", "reach": 210, "saved": 4, "shares": 1,
                       "likes": 12, "comments": 2, "leads": 1, "permalink": ""},
                      {"id": "2", "key": "2026-11-02/k2#reel", "kind": "rolka", "at": "2026-11-06T14:00+01:00",
                       "topic": "Telefon klienta", "pillar": "Edukacja", "views": 380, "reach": 300, "saved": 1,
                       "likes": 9, "comments": 0, "ig_reels_avg_watch_time": 5230, "leads": 0, "permalink": ""}]}
    text = summary(data, prev=38)
    print(text)
    assert "41 obserwujących (+3)" in text and "śr. oglądanie 5,2 s" in text and "—" not in text
    data["insights"] = False
    assert "instagram_manage_insights" in summary(data)
    print("\n" + markdown(data, "x").split("\n\n", 1)[1])
    print("selftest OK")


def main():
    ap = argparse.ArgumentParser(description="Weekly Instagram report.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    now = datetime.now(timezone.utc).astimezone(TZ)
    try:
        data = collect(now)
    except ApiError as e:
        msg = f"PageHub: nie udało się zrobić raportu tygodnia.\n{e}"
        print(msg)
        if not args.dry_run:
            telegram(msg)
        return 1
    text = summary(data, previous_followers(data["made_at"][:10]))
    print(text)
    if args.dry_run:
        print("\n" + json.dumps(data, ensure_ascii=False, indent=1)[:3000])
        return 0
    save(data, text)
    telegram(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
