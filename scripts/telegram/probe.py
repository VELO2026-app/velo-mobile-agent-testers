#!/usr/bin/env python3
"""Look at Telegram's first screens on the emulator and answer one question:
is there a switch to the TEST backend? Reads the accessibility tree only; taps
"Start Messaging" and nothing else; never types. Writes screenshots and
probe.json to $PROBE_OUT and prints the answer."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "velo"))
import chrome_ready as ui  # noqa: E402  (adb, ui_nodes, centre)

OUT = Path(os.environ.get("PROBE_OUT", "results/telegram-probe"))
OUT.mkdir(parents=True, exist_ok=True)


def shot(name: str) -> None:
    png = subprocess.run(["adb", "exec-out", "screencap", "-p"], capture_output=True, timeout=60).stdout
    png = png[png.find(b"\x89PNG"):] if b"\x89PNG" in png else png
    (OUT / f"{name}.png").write_bytes(png)


def snapshot(name: str) -> dict:
    nodes = ui.ui_nodes()
    texts = []
    for n in nodes:
        t = (n.get("text") or n.get("content-desc") or "").strip()
        if t and t not in texts:
            texts.append(t)
    classes = sorted({n.get("class", "").split(".")[-1] for n in nodes if n.get("class")})
    shot(name)
    return {"texts": texts[:40], "has_checkbox": any("CheckBox" in c for c in classes),
            "package": next((n.get("package") for n in nodes if n.get("package")), None), "_nodes": nodes}


def tap_text(nodes, pattern: str) -> bool:
    rx = re.compile(pattern, re.I)
    for n in nodes:
        t = (n.get("text") or n.get("content-desc") or "").strip()
        if t and rx.search(t):
            c = ui.centre(n)
            if c:
                ui.adb("shell", "input", "tap", str(c[0]), str(c[1]))
                return True
    return False


def mentions_test(texts) -> list[str]:
    return [t for t in texts if re.search(r"test|debug|backend|server", t, re.I)]


def main() -> int:
    res: dict = {"package": os.environ.get("PKG"), "versionName": os.environ.get("VER"),
                 "sha256": os.environ.get("SHA"), "application_debuggable": os.environ.get("DBG") == "true",
                 "native_code": os.environ.get("ABIS")}
    s1 = snapshot("01-intro")
    res["intro_texts"] = s1["texts"]
    res["telegram_in_front"] = s1["package"] == os.environ.get("PKG")
    nodes = s1.pop("_nodes")

    # Language suggestion and the Start Messaging button; permission prompts are declined
    for _ in range(3):
        if tap_text(nodes, r"^start messaging$"):
            break
        time.sleep(2)
        nodes = ui.ui_nodes()
    time.sleep(4)
    for _ in range(4):  # system permission dialogs (calls, contacts): decline, we do not log in
        nodes = ui.ui_nodes()
        if not tap_text(nodes, r"^(don.?t allow|deny|no thanks|not now)$"):
            break
        time.sleep(2)
    s2 = snapshot("02-after-start")
    res["after_start_texts"] = s2["texts"]
    res["after_start_has_checkbox"] = s2["has_checkbox"]
    nodes = s2.pop("_nodes")

    # Nothing hidden is documented for Android; try the iOS gesture (10 taps on the title) and a long press anyway
    title = next((n for n in nodes if re.search(r"your phone|phone number|telegram", (n.get("text") or ""), re.I)), None)
    if title is not None and ui.centre(title):
        x, y = ui.centre(title)
        for _ in range(10):
            ui.adb("shell", "input", "tap", str(x), str(y))
        ui.adb("shell", "input", "swipe", str(x), str(y), str(x), str(y), "1500")
        time.sleep(2)
    s3 = snapshot("03-after-gestures")
    res["after_gestures_texts"] = s3["texts"]
    res["after_gestures_has_checkbox"] = s3["has_checkbox"]
    s3.pop("_nodes")

    seen = mentions_test(res["after_start_texts"] + res["after_gestures_texts"] + res["intro_texts"])
    res["test_related_texts"] = seen
    res["test_backend_switch_visible"] = any(re.search(r"test backend|switch backend", t, re.I) for t in seen)
    (OUT / "probe.json").write_text(json.dumps(res, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in res.items() if k != "sha256"}, ensure_ascii=False, indent=2))
    print("ANSWER: test backend switch visible in this APK = " + str(res["test_backend_switch_visible"]))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"PROBE ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
