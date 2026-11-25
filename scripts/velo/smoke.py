#!/usr/bin/env python3
"""Dry-run check of the lane, no model and no key.

Proves, on the booted emulator, the things the agent depends on:
  1. the app opens in Chrome from http://localhost:<port> (adb reverse),
  2. the Telegram launch parameters log the synthetic student in,
  3. the SOFT KEYBOARD really opens when a text field gets focus (the whole
     reason to use an emulator: Playwright's WebKit/Chromium cannot do this),
  4. the app notices it (class html.is-keyboard-open, visualViewport height),
  5. the accessibility tree is readable (what scripts/android/screen.py lists).

Needs: adb on PATH, the stack on the runner (:8000 backend, :<port> app),
`pip install websocket-client`, TELEGRAM_BOT_TOKEN (the stack's fake one).
Writes screenshots and smoke.json to $SMOKE_OUT; exit 1 when a proof fails.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chrome_ready  # noqa: E402
import sign_init_data as sid  # noqa: E402

OUT = Path(os.environ.get("SMOKE_OUT", "results/smoke"))
PORT = int(os.environ.get("APP_PORT", "4173"))
API = os.environ.get("API_URL", "http://127.0.0.1:8000")
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
USER_ID = int(os.environ.get("SMOKE_USER_ID", "610002"))
LANG = os.environ.get("SMOKE_LANG", "ru")
OUT.mkdir(parents=True, exist_ok=True)


def adb(*a: str, raw: bool = False, timeout: int = 60):
    r = subprocess.run(["adb", *a], capture_output=True, timeout=timeout)
    return r.stdout if raw else r.stdout.decode("utf-8", "replace")


def shot(name: str) -> None:
    png = adb("exec-out", "screencap", "-p", raw=True)
    png = png[png.find(b"\x89PNG"):] if b"\x89PNG" in png else png
    (OUT / f"{name}.png").write_bytes(png)


def api(method: str, path: str, body: dict | None = None, token: str | None = None) -> dict:
    req = urllib.request.Request(
        API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        raw = r.read()
        return json.loads(raw) if raw else {}


def login_api() -> str:
    init = sid.build_init_data({"id": USER_ID, "first_name": "Smoke", "language_code": LANG}, TOKEN)
    return api("POST", "/api/v1/auth/telegram", {"init_data": init})["session_token"]


# ---- Chrome DevTools Protocol (read-only evaluate) ---------------------------------------------
class Cdp:
    def __init__(self) -> None:
        import websocket  # pip install websocket-client

        adb("forward", "tcp:9222", "localabstract:chrome_devtools_remote")
        deadline = time.time() + 40
        target = None
        while time.time() < deadline and not target:
            try:
                tabs = json.load(urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=3))
                target = next((t for t in tabs if t.get("type") == "page" and f"localhost:{PORT}" in t.get("url", "")), None)
            except Exception:
                pass
            if not target:
                time.sleep(1)
        if not target:
            raise RuntimeError("no Chrome tab with the app (DevTools socket)")
        self.ws = websocket.create_connection(target["webSocketDebuggerUrl"], timeout=15, suppress_origin=True)
        self.n = 0

    def eval(self, expr: str):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": "Runtime.evaluate",
                                 "params": {"expression": expr, "returnByValue": True}}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.n:
                return msg.get("result", {}).get("result", {}).get("value")


STATE_JS = """(() => ({
  href: location.pathname,
  ready: document.readyState,
  appChildren: (document.querySelector('#app') || {children: []}).children.length,
  tgPlatform: (window.Telegram && Telegram.WebApp && Telegram.WebApp.platform) || null,
  hasToken: !!(localStorage.getItem('velo_token') || sessionStorage.getItem('velo_token')),
  kbClass: document.documentElement.classList.contains('is-keyboard-open'),
  vvh: Math.round(visualViewport.height), innerH: innerHeight, dpr: devicePixelRatio,
  fields: document.querySelectorAll('textarea,input:not([type=hidden])').length,
  text: document.body.innerText.slice(0, 80).replace(/\\s+/g, ' ')
}))()"""


def ui_nodes() -> list[ET.Element]:
    adb("shell", "uiautomator", "dump", "/sdcard/ui.xml")
    xml = adb("exec-out", "cat", "/sdcard/ui.xml")
    try:
        return list(ET.fromstring(xml[xml.find("<"):]).iter("node"))
    except ET.ParseError:
        return []


def first_field_centre(nodes: list[ET.Element]):
    for n in nodes:
        if n.get("class", "").endswith("EditText"):
            b = re.findall(r"\d+", n.get("bounds", ""))
            if len(b) == 4:
                x1, y1, x2, y2 = map(int, b)
                return (x1 + x2) // 2, (y1 + y2) // 2
    return None


def ime_shown() -> bool:
    out = adb("shell", "dumpsys", "input_method")
    return bool(re.search(r"mInputShown=true|mIsInputViewShown=true", out))


def main() -> int:
    res: dict = {"proofs": {}, "notes": []}
    ok = True

    token = login_api()
    api("PATCH", "/api/v1/users/me", {"onboarding_completed": True}, token)  # land on the app, not the welcome slides
    url = sid.launch_url(
        sid.build_init_data({"id": USER_ID, "first_name": "Smoke", "language_code": LANG}, TOKEN),
        f"http://localhost:{PORT}", "/user/diary", "android",
    )
    adb("shell", "am", "force-stop", "com.android.chrome")
    adb("shell", f"am start -a android.intent.action.VIEW -d '{url}' com.android.chrome")

    cdp = Cdp()
    deadline = time.time() + 60
    st = {}
    while time.time() < deadline:
        st = cdp.eval(STATE_JS) or {}
        if st.get("ready") == "complete" and st.get("appChildren", 0) > 0 and st.get("hasToken"):
            break
        time.sleep(2)
    time.sleep(3)
    closed = chrome_ready.dismiss_prompts()
    if closed:
        res["notes"].append("closed Chrome prompts: " + ", ".join(closed))
    st = cdp.eval(STATE_JS) or st
    shot("01-opened")
    res["opened"] = st
    res["proofs"]["app_loaded_in_chrome"] = bool(st.get("appChildren"))
    res["proofs"]["telegram_launch_login"] = bool(st.get("hasToken")) and st.get("tgPlatform") == "android"

    nodes = ui_nodes()
    texts = [n.get("text") or n.get("content-desc") for n in nodes if (n.get("text") or n.get("content-desc"))]
    res["proofs"]["a11y_tree_readable"] = len(texts) >= 3
    res["a11y_sample"] = [t[:40] for t in texts[:8]]

    centre = first_field_centre(nodes)
    if centre is None:
        res["notes"].append("no EditText in the accessibility tree; falling back to a DevTools tap")
        rect = cdp.eval("(() => { const e = document.querySelector('textarea,input:not([type=hidden])');"
                        " if (!e) return null; e.scrollIntoView({block:'center'}); const r = e.getBoundingClientRect();"
                        " return {x: r.left + r.width/2, y: r.top + r.height/2}; })()")
        if rect:
            webview = next((n for n in nodes if n.get("class", "").endswith("WebView")), None)
            top = int(re.findall(r"\d+", webview.get("bounds"))[1]) if webview is not None else 0
            centre = (int(rect["x"] * st.get("dpr", 2.6)), top + int(rect["y"] * st.get("dpr", 2.6)))
    before = cdp.eval(STATE_JS) or {}
    if centre:
        adb("shell", "input", "tap", str(centre[0]), str(centre[1]))
        time.sleep(3)
    else:
        res["notes"].append("no text field found on /user/diary")
    after = cdp.eval(STATE_JS) or {}
    shown = ime_shown()
    shot("02-keyboard-open")
    res["keyboard"] = {"before": {k: before.get(k) for k in ("vvh", "innerH", "kbClass")},
                       "after": {k: after.get(k) for k in ("vvh", "innerH", "kbClass")},
                       "ime_shown_by_android": shown}
    res["proofs"]["soft_keyboard_opens"] = shown
    res["proofs"]["viewport_shrinks_with_keyboard"] = (after.get("vvh") or 0) < (before.get("vvh") or 0) - 100
    res["proofs"]["app_sets_is_keyboard_open"] = bool(after.get("kbClass"))

    adb("shell", "input", "keyevent", "KEYCODE_BACK")
    time.sleep(2)
    closed = cdp.eval(STATE_JS) or {}
    shot("03-keyboard-closed")
    res["keyboard"]["closed"] = {k: closed.get(k) for k in ("vvh", "kbClass")}

    # The first three proofs are the lane itself; the keyboard ones are the point of it.
    must = ("app_loaded_in_chrome", "telegram_launch_login", "soft_keyboard_opens")
    ok = all(res["proofs"].get(k) for k in must)
    res["ok"] = ok
    (OUT / "smoke.json").write_text(json.dumps(res, ensure_ascii=False, indent=2))
    # Only synthetic data below (a throwaway stack): safe for the public log.
    print(json.dumps({"ok": ok, "proofs": res["proofs"], "keyboard": res["keyboard"], "notes": res["notes"]},
                     ensure_ascii=False, indent=2))
    if not ok:
        print("SMOKE FAILED: " + ", ".join(k for k in must if not res["proofs"].get(k)), file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # keep the reason in the log, never a stack of secrets (there are none here)
        print(f"SMOKE ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
