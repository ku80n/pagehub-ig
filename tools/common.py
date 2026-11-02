"""Shared helpers for the GitHub Actions side: Graph API, Telegram, state files.

Everything here uses the standard library only, so the workflow needs nothing
but Pillow on top of a stock Python.
"""

import json
import os
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATE = ROOT / "state"
GRAPH_VERSION = os.environ.get("META_GRAPH_VERSION", "v23.0")
GRAPH = f"https://graph.facebook.com/{GRAPH_VERSION}"


class ApiError(RuntimeError):
    pass


def env(name, required=True):
    val = os.environ.get(name, "").strip()
    if required and not val:
        raise ApiError(f"brak sekretu {name} w GitHub Secrets")
    return val


# ---------------------------------------------------------------- state files

def load_state(name, default):
    p = STATE / name
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def save_state(name, data):
    STATE.mkdir(exist_ok=True)
    (STATE / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- http

def _request(method, url, data=None, headers=None, raw=None, timeout=60):
    body = raw
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        try:
            detail = json.loads(detail).get("error", {}).get("message", detail)
        except ValueError:
            pass
        raise ApiError(f"{method} {url.split('?')[0]} -> HTTP {e.code}: {detail[:300]}") from None
    return json.loads(text) if text else {}


def graph(method, path, token, **params):
    """Call the Graph API. Token goes in the body or query, never in logs."""
    params["access_token"] = token
    if method == "GET":
        return _request("GET", f"{GRAPH}/{path}?{urllib.parse.urlencode(params)}")
    return _request("POST", f"{GRAPH}/{path}", data=params)


def graph_pages(path, token, **params):
    """Follow Graph API paging and yield every item."""
    out = graph("GET", path, token, **params)
    while True:
        for item in out.get("data", []):
            yield item
        nxt = out.get("paging", {}).get("next")
        if not nxt:
            return
        out = _request("GET", nxt)


# ---------------------------------------------------------------- telegram

def telegram(text, dry_run=False):
    """Send a message to Jakub. Plain text, links stay clickable."""
    if dry_run:
        print("--- TELEGRAM (dry run) ---\n" + text + "\n---")
        return
    token = env("TELEGRAM_BOT_TOKEN")
    chat = env("TELEGRAM_CHAT_ID")
    _request("POST", f"https://api.telegram.org/bot{token}/sendMessage",
             data={"chat_id": chat, "text": text[:4000], "disable_web_page_preview": "true"})


def wait(seconds):
    time.sleep(seconds)
