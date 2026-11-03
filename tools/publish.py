#!/usr/bin/env python3
"""
publish.py - publish the carousels (and their Reels) whose time has come.

Runs hourly from GitHub Actions. A carousel is due when its meta.publish_at is
in the past but less than LATE_LIMIT ago, it is not marked "skip", and it is
not in state/published.json yet. Each carousel also becomes a Reel built from
its slides (tools/make_reel.py), due at meta.reel_at, by default one day later.
Everything it does is recorded in state/ so a rerun never posts twice.

The Instagram API only takes JPEG from a public URL and cannot schedule, so:
  1. slides are converted to JPEG,
  2. deployed to a small Netlify site (the public URL),
  3. published through the Graph API at the hour they are due.

Usage
  python3 tools/publish.py              # publish what is due
  python3 tools/publish.py --dry-run    # show what would happen, no network
  python3 tools/publish.py --check      # verify every secret and connection
  python3 tools/publish.py --dry-run --now 2026-11-03T19:05:00+01:00

Pause everything: create the file config/PAUZA. Delete it to resume.
"""

import argparse
import io
import json
import sys
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from common import ROOT, ApiError, _request, env, graph, load_state, save_state, telegram, wait

TZ = ZoneInfo("Europe/Warsaw")
LATE_LIMIT = timedelta(hours=12)     # older than this and the slot is gone
MAX_ATTEMPTS = 3                     # hourly retries before giving up
NETLIFY = "https://api.netlify.com/api/v1"


def now_local(override=None):
    if override:
        return datetime.fromisoformat(override).astimezone(TZ)
    return datetime.now(timezone.utc).astimezone(TZ)


def all_posts():
    for spec_path in sorted(ROOT.glob("weeks/*/k*.json")):
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        key = f"{spec_path.parent.name}/{spec_path.stem}"
        yield key, spec_path, spec


def schedule(spec):
    """[(kind, when)] for one carousel spec: the carousel itself and, unless off, its Reel."""
    meta = spec.get("meta", {})
    if meta.get("skip") or not meta.get("publish_at"):
        return []
    at = datetime.fromisoformat(meta["publish_at"]).astimezone(TZ)
    out = [("carousel", at)]
    # Reels are opt-in: on only when the repo variable PUBLISH_REELS is "true".
    reels_on = env("PUBLISH_REELS", required=False) == "true" and meta.get("reel", True) is not False
    if reels_on:
        reel_at = (datetime.fromisoformat(meta["reel_at"]).astimezone(TZ) if meta.get("reel_at")
                   else at + timedelta(days=1))
        out.append(("reel", reel_at))
    return out


def media_prefix(key):
    """Folder on the media site. '#' would end a URL, so the reel gets '-reel'."""
    return key.replace("#", "-")


def due_posts(now, published, failures):
    due, missed = [], []
    for base, path, spec in all_posts():
        for kind, at in schedule(spec):
            key = base if kind == "carousel" else f"{base}#reel"
            if key in published or failures.get(key, {}).get("count", 0) >= MAX_ATTEMPTS:
                continue
            item = (key, kind, path, spec)
            if at <= now < at + LATE_LIMIT:
                due.append(item)
            elif now >= at + LATE_LIMIT:
                missed.append(item + (at,))
    return due, missed


def reel_bytes(path):
    """Build the Reel MP4 for a carousel spec and return its bytes."""
    import tempfile
    from make_reel import build
    with tempfile.TemporaryDirectory() as tmp:
        out, _ = build(path, f"{tmp}/reel.mp4")
        return out.read_bytes()


def jpegs(path, spec):
    """Slides as JPEG bytes, in order. The API refuses PNG."""
    from PIL import Image
    slide_dir = path.with_suffix("")
    pngs = sorted(slide_dir.glob("*.png"))
    if len(pngs) != len(spec["slides"]):
        raise ApiError(f"{path.name}: {len(pngs)} plików PNG zamiast {len(spec['slides'])}")
    if not 2 <= len(pngs) <= 10:
        raise ApiError(f"{path.name}: karuzela przez API musi mieć 2-10 slajdów, ma {len(pngs)}")
    out = []
    for p in pngs:
        buf = io.BytesIO()
        Image.open(p).convert("RGB").save(buf, "JPEG", quality=92, optimize=True)
        out.append((p.stem + ".jpg", buf.getvalue()))
    return out


# ---------------------------------------------------------------- netlify

def netlify_deploy(files):
    """Deploy {path: bytes} as the whole media site. Returns the public base URL."""
    token, site = env("NETLIFY_AUTH_TOKEN"), env("NETLIFY_SITE_ID")
    auth = {"Authorization": f"Bearer {token}"}
    info = _request("GET", f"{NETLIFY}/sites/{site}", headers=auth)
    base = (info.get("ssl_url") or info.get("url")).rstrip("/")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("index.html", "<!doctype html><title>media</title>")
        z.writestr("robots.txt", "User-agent: *\nDisallow: /\n")
        for name, data in files.items():
            z.writestr(name, data)
    dep = _request("POST", f"{NETLIFY}/sites/{site}/deploys", raw=buf.getvalue(),
                   headers={**auth, "Content-Type": "application/zip"}, timeout=180)
    for _ in range(60):
        state = _request("GET", f"{NETLIFY}/deploys/{dep['id']}", headers=auth).get("state")
        if state == "ready":
            break
        if state == "error":
            raise ApiError("Netlify: deploy zakończony błędem")
        wait(5)
    else:
        raise ApiError("Netlify: deploy nie skończył się w 5 minut")
    # Meta fetches the files itself, so make sure they are really public first.
    public_check(f"{base}/{next(iter(files))}")
    return base


def public_check(url):
    """Fetch a URL anonymously, the way Meta will. Raise ApiError with a fix if it fails."""
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=30) as r:
            r.read(1)
            return r.status
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise ApiError(
                f"Netlify zwraca {e.code}, bo projekt jest prywatny. W Netlify: projekt -> Project configuration "
                "-> General -> Visitor access -> Project visibility -> Public -> Save.") from None
        raise ApiError(f"Netlify zwraca HTTP {e.code} dla {url}") from None
    except urllib.error.URLError as e:
        raise ApiError(f"Netlify: brak połączenia z {url.split('/')[2]} ({e.reason})") from None


# ---------------------------------------------------------------- instagram / facebook

def _norm(text):
    return " ".join((text or "").split())[:120]


def find_existing(caption, kind="carousel", hours=36):
    """A post with this caption published recently, if any: (media_id, permalink) or None.

    Instagram sometimes answers media_publish with an error and publishes anyway,
    so every retry checks the profile first instead of risking a double post.
    """
    token, ig = env("META_PAGE_TOKEN"), env("IG_USER_ID")
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    want = _norm(caption)
    fields = "id,caption,permalink,timestamp,media_type,media_product_type"
    for m in graph("GET", f"{ig}/media", token, fields=fields, limit=15).get("data", []):
        if datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z") < since:
            break
        is_reel = m.get("media_product_type") == "REELS" or m.get("media_type") == "VIDEO"
        if (kind == "reel") != is_reel:
            continue
        if _norm(m.get("caption")) == want:
            return m["id"], m.get("permalink", "")
    return None


def wait_ready(container, token, what, tries=40):
    """Poll a media container until Instagram has finished processing it."""
    status = None
    for _ in range(tries):
        status = graph("GET", container, token, fields="status_code").get("status_code")
        if status in ("FINISHED", "PUBLISHED"):
            return status
        if status in ("ERROR", "EXPIRED"):
            raise ApiError(f"Instagram: {what} w stanie {status}")
        wait(5)
    raise ApiError(f"Instagram: {what} nadal w stanie {status} po {tries * 5} s")


def publish_instagram(urls, caption):
    token, ig = env("META_PAGE_TOKEN"), env("IG_USER_ID")
    children = [graph("POST", f"{ig}/media", token, image_url=u, is_carousel_item="true")["id"]
                for u in urls]
    for i, child in enumerate(children, 1):
        wait_ready(child, token, f"slajd {i}")
    carousel = graph("POST", f"{ig}/media", token, media_type="CAROUSEL",
                     children=",".join(children), caption=caption)["id"]
    wait_ready(carousel, token, "karuzela")
    return publish_container(carousel, caption, "carousel")


def publish_reel(url, caption, to_feed=False):
    """Video Reel from a public MP4 URL. Video takes longer to process than photos."""
    token, ig = env("META_PAGE_TOKEN"), env("IG_USER_ID")
    container = graph("POST", f"{ig}/media", token, media_type="REELS", video_url=url,
                      caption=caption, share_to_feed="true" if to_feed else "false")["id"]
    wait_ready(container, token, "rolka", tries=120)
    return publish_container(container, caption, "reel")


def publish_container(container, caption, kind):
    """media_publish with retries.

    "Media ID is not available" means Instagram is still finishing the container,
    even after it reported FINISHED. Publishing the same container twice is
    impossible, so retrying here can never create a duplicate.
    """
    token, ig = env("META_PAGE_TOKEN"), env("IG_USER_ID")
    last_error = None
    for _ in range(8):
        try:
            media_id = graph("POST", f"{ig}/media_publish", token, creation_id=container)["id"]
            break
        except ApiError as e:
            last_error = e
            if graph("GET", container, token, fields="status_code").get("status_code") == "PUBLISHED":
                found = find_existing(caption, kind)
                if found:
                    return found
            if "not available" not in str(e) and "not ready" not in str(e).lower():
                raise
            wait(15)
    else:
        raise ApiError(f"Instagram nie przyjął posta przez 2 minuty: {last_error}")
    permalink = graph("GET", media_id, token, fields="permalink").get("permalink", "")
    return media_id, permalink


def publish_facebook(urls, message):
    token, page = env("META_PAGE_TOKEN"), env("FB_PAGE_ID")
    photo_ids = [graph("POST", f"{page}/photos", token, url=u, published="false")["id"] for u in urls]
    attached = {f"attached_media[{i}]": json.dumps({"media_fbid": pid}) for i, pid in enumerate(photo_ids)}
    return graph("POST", f"{page}/feed", token, message=message, **attached)["id"]


# ---------------------------------------------------------------- check mode

def check():
    """Touch every connection once and report in plain Polish."""
    ok, bad = [], []

    def step(name, fn):
        try:
            ok.append(f"{name}: {fn()}")
        except Exception as e:  # noqa: BLE001 - report every failure, keep going
            bad.append(f"{name}: {e}")

    token = env("META_PAGE_TOKEN", required=False)
    step("Token Meta", lambda: graph("GET", "me", token, fields="name")["name"])
    step("Konto Instagram", lambda: "@" + graph("GET", env("IG_USER_ID"), token, fields="username")["username"])
    step("Limit publikacji", lambda: json.dumps(graph("GET", f"{env('IG_USER_ID')}/content_publishing_limit",
                                                       token, fields="quota_usage").get("data", [{}])[0]))
    step("Strona Facebook", lambda: graph("GET", env("FB_PAGE_ID"), token, fields="name")["name"])
    step("Wiadomości IG", lambda: "dostęp jest" + (", widać rozmowy" if graph(
        "GET", env("FB_PAGE_ID") + "/conversations", token, platform="instagram", limit=1).get("data") else ""))

    def token_validity():
        from token_watch import status
        problems, summary = status()
        if problems:
            raise ApiError("; ".join(problems))
        return summary
    step("Ważność tokenu", token_validity)
    def netlify_status():
        info = _request("GET", f"{NETLIFY}/sites/{env('NETLIFY_SITE_ID')}",
                        headers={"Authorization": f"Bearer {env('NETLIFY_AUTH_TOKEN')}"})
        base = (info.get("ssl_url") or info.get("url")).rstrip("/")
        public_check(base + "/")
        return base + " (publiczny)"
    step("Netlify", netlify_status)
    try:
        telegram("PageHub: test połączenia.\n\n" + "\n".join(["OK  " + o for o in ok] + ["BŁĄD  " + b for b in bad]))
        ok.append("Telegram: wiadomość testowa wysłana")
    except Exception as e:  # noqa: BLE001
        bad.append(f"Telegram: {e}")
    print("\n".join(["OK    " + o for o in ok] + ["BŁĄD  " + b for b in bad]))
    return 0 if not bad else 1


# ---------------------------------------------------------------- watchdog

def week_watch(now, dry_run=False):
    """From Monday noon on, warn once if this week has no carousels at all.

    That is the one failure nothing else reports: the Monday task did not run,
    so there is nothing to publish and no error to send.
    """
    monday = (now - timedelta(days=now.weekday())).date()
    if now.weekday() == 0 and now.hour < 12:
        return
    if any(ROOT.glob(f"weeks/{monday.isoformat()}/k*.json")):
        return
    state = load_state("week_watch.json", {})
    if state.get("warned_week") == monday.isoformat():
        return
    telegram(f"PageHub: na tydzień od {monday:%d.%m} nie ma nowych karuzel, poniedziałkowe zadanie "
             "chyba nie zadziałało. Uruchom ręcznie zadanie \"Karuzele PageHub\" w Claude "
             "albo napisz do Claude.", dry_run)
    if not dry_run:
        save_state("week_watch.json", {"warned_week": monday.isoformat()})


# ---------------------------------------------------------------- main

def run(now, dry_run=False):
    if (ROOT / "config" / "PAUZA").exists():
        print("config/PAUZA istnieje - publikacja wstrzymana")
        return 0
    try:
        week_watch(now, dry_run)
    except Exception as e:  # noqa: BLE001 - the watchdog must never block publishing
        print("week_watch:", e)
    published = load_state("published.json", {})
    failures = load_state("publish_failures.json", {})
    due, missed = due_posts(now, published, failures)

    for key, kind, _, spec, at in missed:
        published[key] = {"status": "missed", "noted_at": now.isoformat()}
        what = "rolka" if kind == "reel" else "karuzela"
        telegram(f"PageHub: {what} {key} ({at:%d.%m %H:%M}) nie wyszła na czas "
                 "i została pominięta. Sprawdź zakładkę Actions w repo.", dry_run)
    if not due:
        print(f"{now:%Y-%m-%d %H:%M}: nic do publikacji")
        if missed and not dry_run:
            save_state("published.json", published)
        return 0

    media = {}
    for key, kind, path, spec in due:
        if kind == "carousel":
            for name, data in jpegs(path, spec):
                media[f"{media_prefix(key)}/{name}"] = data
        elif not dry_run:
            media[f"{media_prefix(key)}/reel.mp4"] = reel_bytes(path)
    if dry_run:
        for key, kind, _, spec in due:
            if kind == "carousel":
                n = len([m for m in media if m.startswith(media_prefix(key) + "/")])
                print(f"[dry-run] {key}: {n} JPEG -> Netlify -> karuzela IG + post FB")
                print("          podpis IG:", spec["meta"]["caption_ig"].splitlines()[0])
            else:
                print(f"[dry-run] {key}: rolka MP4 ze slajdów -> Netlify -> Reels IG")
                print("          podpis:", (spec["meta"].get("caption_reel") or spec["meta"]["caption_ig"]).splitlines()[0])
        return 0

    try:
        base = netlify_deploy(media)
    except ApiError as e:
        # Nothing reached Instagram: count it as a failed attempt for every due post.
        for key, _, _, spec in due:
            f = failures.setdefault(key, {"count": 0})
            f["count"] += 1
            f["last_error"] = str(e)
            if f["count"] in (1, MAX_ATTEMPTS):
                last = " To była ostatnia próba." if f["count"] == MAX_ATTEMPTS else " Spróbuję ponownie za godzinę."
                telegram(f"PageHub: nie udało się opublikować {key} ({spec['meta'].get('when', '')}).\n{e}{last}")
        save_state("publish_failures.json", failures)
        print("BŁĄD:", e)
        return 1
    code = 0
    for key, kind, _, spec in due:
        meta = spec["meta"]
        urls = [f"{base}/{m}" for m in sorted(media) if m.startswith(media_prefix(key) + "/")]
        caption = meta["caption_ig"] if kind == "carousel" else (meta.get("caption_reel") or meta["caption_ig"])
        try:
            found = find_existing(caption, kind) if key in failures else None
            if found:
                print(f"{key}: już jest na profilu po wcześniejszej próbie, nie publikuję drugi raz")
            if kind == "carousel":
                media_id, link = found or publish_instagram(urls, caption)
            else:
                media_id, link = found or publish_reel(urls[0], caption, bool(meta.get("reel_to_feed")))
            published[key] = {"status": "published", "ig_media_id": media_id, "permalink": link,
                              "cta_keyword": meta.get("cta_keyword", ""), "at": now.isoformat()}
            save_state("published.json", published)
            failures.pop(key, None)
            print(f"{key}: opublikowano na Instagramie {link}")
            if kind == "reel":
                continue
        except ApiError as e:
            code = 1
            f = failures.setdefault(key, {"count": 0})
            f["count"] += 1
            f["last_error"] = str(e)
            if f["count"] in (1, MAX_ATTEMPTS):
                last = " To była ostatnia próba." if f["count"] == MAX_ATTEMPTS else " Spróbuję ponownie za godzinę."
                telegram(f"PageHub: nie udało się opublikować {key} na Instagramie.\n{e}{last}")
            save_state("publish_failures.json", failures)
            continue
        if env("FB_PAGE_ID", required=False) and env("PUBLISH_FB", required=False) != "false":
            try:
                post_id = publish_facebook(urls, meta.get("caption_fb") or meta["caption_ig"])
                published[key]["fb_post_id"] = post_id
            except ApiError as e:
                published[key]["fb_error"] = str(e)
                telegram(f"PageHub: {key} jest na Instagramie, ale Facebook odrzucił post.\n{e}")
            save_state("published.json", published)
    save_state("publish_failures.json", failures)
    return code


def main():
    ap = argparse.ArgumentParser(description="Publish due carousels.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--now", help="ISO time override, for testing")
    args = ap.parse_args()
    if args.check:
        sys.exit(check())
    sys.exit(run(now_local(args.now), dry_run=args.dry_run))


if __name__ == "__main__":
    main()
