#!/usr/bin/env python3
"""Close Chrome's own first-run / promo dialogs so the app is what is on screen.

A fresh Chrome on an emulator can still show native dialogs ("Chrome
notifications make things easier", sign-in, default browser...). They cover the
page and swallow taps. Only NATIVE Chrome views are touched: the dialog's
buttons have a `com.android.chrome:id/...` resource id; the web page's own
buttons have none, so the app's buttons are never pressed by mistake.

Usage: chrome_ready.py          (needs adb on PATH; prints what it closed)
"""
from __future__ import annotations

import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

DECLINE = {"no thanks", "no, thanks", "not now", "skip", "got it", "dismiss", "no thank you", "later"}


def adb(*a: str, timeout: int = 60) -> str:
    return subprocess.run(["adb", *a], capture_output=True, timeout=timeout).stdout.decode("utf-8", "replace")


def ui_nodes() -> list[ET.Element]:
    adb("shell", "uiautomator", "dump", "/sdcard/ui.xml")
    xml = adb("exec-out", "cat", "/sdcard/ui.xml")
    try:
        return list(ET.fromstring(xml[xml.find("<"):]).iter("node"))
    except ET.ParseError:
        return []


def centre(node: ET.Element):
    b = re.findall(r"\d+", node.get("bounds", ""))
    if len(b) != 4:
        return None
    x1, y1, x2, y2 = map(int, b)
    return (x1 + x2) // 2, (y1 + y2) // 2


def dismiss_prompts(max_rounds: int = 6) -> list[str]:
    closed: list[str] = []
    quiet = 0
    for _ in range(max_rounds):
        hit = None
        for n in ui_nodes():
            text = (n.get("text") or n.get("content-desc") or "").strip()
            if n.get("resource-id", "").startswith("com.android.chrome:id/") and text.lower() in DECLINE:
                hit = (text, centre(n))
                break
        if hit and hit[1]:
            adb("shell", "input", "tap", str(hit[1][0]), str(hit[1][1]))
            closed.append(hit[0])
            quiet = 0
            time.sleep(1.5)
        else:
            quiet += 1
            if quiet >= 2:
                break
            time.sleep(1.5)
    return closed


if __name__ == "__main__":
    done = dismiss_prompts()
    print("chrome prompts closed: " + (", ".join(done) if done else "none"))
    sys.exit(0)
