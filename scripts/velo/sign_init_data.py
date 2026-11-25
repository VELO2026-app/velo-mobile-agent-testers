#!/usr/bin/env python3
"""Sign Telegram WebApp initData for the throwaway VELO stack of a CI job.

The stack runs with a FAKE bot token (TELEGRAM_BOT_TOKEN=e2e:fake, the same one
velo's own e2e-stack job uses), so the signing key is not a secret: it only
exists inside one runner for the minutes the job lives. A real bot token must
never be given to this script.

initData lives 300 s on the backend and is single-use (anti-replay), so a URL
is minted right before the browser opens it, never earlier and never reused.

Usage:
  sign_init_data.py url   --id 610001 --first-name Test --lang ru --path /user/diary
  sign_init_data.py data  --id 610001 --first-name Test           (raw initData)
The token comes from the environment (TELEGRAM_BOT_TOKEN), never from argv.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.parse

DEFAULT_BASE = "http://localhost:4173"


def build_init_data(user: dict, token: str, now: int | None = None, query_id: str | None = None) -> str:
    """Same scheme as Telegram (and velo's frontend/e2e/stack/auth.ts)."""
    params = {
        "user": json.dumps(user, ensure_ascii=False),
        "auth_date": str(int(time.time()) if now is None else now),
        "query_id": query_id or f"mat{time.time_ns()}",  # unique per call: replay is refused
    }
    check = "\n".join(f"{k}={params[k]}" for k in sorted(params))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return "&".join(f"{k}={urllib.parse.quote(v, safe='')}" for k, v in params.items())


def launch_url(init_data: str, base: str, path: str, platform: str = "android") -> str:
    """A page URL carrying the Telegram launch parameters in the hash, so the
    app runs its Telegram code path (frontend/src/platform/launch.ts)."""
    hash_ = (
        f"tgWebAppData={urllib.parse.quote(init_data, safe='')}"
        f"&tgWebAppVersion=8.0&tgWebAppPlatform={platform}&tgWebAppThemeParams=%7B%7D"
    )
    return f"{base.rstrip('/')}{path}#{hash_}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["url", "data"])
    ap.add_argument("--id", type=int, required=True, help="synthetic Telegram id (610001+)")
    ap.add_argument("--first-name", default="Test")
    ap.add_argument("--lang", default="ru")
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--path", default="/")
    ap.add_argument("--platform", default="android")
    a = ap.parse_args()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        sys.exit("sign_init_data: TELEGRAM_BOT_TOKEN is not set (the stack's fake token, e2e:fake)")
    if ":" in token and token.split(":", 1)[0].isdigit():
        # A real bot token is "<digits>:<secret>"; the fake one is not.
        sys.exit("sign_init_data: refusing a real-looking bot token; this lane signs with the stack's fake token only")
    user = {"id": a.id, "first_name": a.first_name, "language_code": a.lang}
    data = build_init_data(user, token)
    print(data if a.mode == "data" else launch_url(data, a.base, a.path, a.platform))


if __name__ == "__main__":
    main()
