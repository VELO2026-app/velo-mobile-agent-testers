#!/usr/bin/env bash
# Runs INSIDE android-emulator-runner. NO LOGIN, NO PHONE NUMBER, NO TELEGRAM ACCOUNT.
# Question: does the official Telegram for Android APK offer a way to switch to
# Telegram's TEST environment (fake accounts 99966XYYYY)? In the open source it
# only exists in DEBUG builds (LoginActivity: "Test backend" checkbox,
# ProfileActivity: "Switch Backend" row). This checks the real APK.
# Facts it prints are static UI strings and build metadata: safe for a public log.
set -uo pipefail
OUT=results/telegram-probe
mkdir -p "$OUT"
APK_URL=${APK_URL:-https://telegram.org/dl/android/apk}

adb wait-for-device
for i in $(seq 1 60); do [ "$(adb shell getprop sys.boot_completed | tr -d '\r')" = 1 ] && break; sleep 3; done

echo "== Download the official APK"
curl -fsSL --max-time 300 -o telegram.apk "$APK_URL" || { echo "ERROR: download failed"; exit 1; }
SHA=$(sha256sum telegram.apk | cut -d' ' -f1)
echo "apk_url=$APK_URL size_bytes=$(stat -c %s telegram.apk) sha256=$SHA"

echo "== Build metadata (aapt2 dump badging)"
AAPT2=$(ls "${ANDROID_HOME:-/usr/local/lib/android/sdk}"/build-tools/*/aapt2 2>/dev/null | sort -V | tail -1)
"$AAPT2" dump badging telegram.apk > "$OUT/badging.txt" 2>&1 || true
PKG=$(sed -n "s/^package: name='\([^']*\)'.*/\1/p" "$OUT/badging.txt" | head -1)
VER=$(sed -n "s/^package:.*versionName='\([^']*\)'.*/\1/p" "$OUT/badging.txt" | head -1)
if grep -q "^application-debuggable" "$OUT/badging.txt"; then DBG=true; else DBG=false; fi
ABIS=$(sed -n "s/^native-code: //p" "$OUT/badging.txt" | head -1)
echo "package=$PKG versionName=$VER application_debuggable=$DBG native_code=$ABIS"
[ -n "$PKG" ] || { echo "ERROR: not a readable APK"; head -5 "$OUT/badging.txt"; exit 1; }

echo "== Install and launch (nothing is typed)"
adb install -r -g telegram.apk 2>&1 | tail -2
adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1
sleep 10
export PKG VER SHA DBG ABIS PROBE_OUT="$OUT"
python3 scripts/telegram/probe.py
CODE=$?
echo "Probe finished (exit $CODE)"
exit $CODE
