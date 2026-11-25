#!/usr/bin/env bash
# Runs INSIDE android-emulator-runner, once the emulator is up. The job has
# already started the throwaway VELO stack on the runner (backend :8000, built
# app on `vite preview` :4173, fake bot token). This script:
#   1. applies the persona's phone settings (language, font scale, theme)
#   2. makes the soft keyboard appear and Chrome skip its first-run screens
#   3. maps the runner's :4173 into the emulator (adb reverse), so Chrome opens
#      http://localhost:4173 -- a secure origin, like the real app
#   4. opens the app in Chrome with freshly signed Telegram launch parameters
#   5. AGENT=true: hands the phone to Claude Code; otherwise runs the dry-run
#      smoke check (no key needed)
# Output goes to results/ (encrypted later), never to the public log.
set -uo pipefail

NAME="${PERSONA}-${SKIN}"
OUT="results/$NAME"
mkdir -p "$OUT"
PORT=${APP_PORT:-4173}
APP_ID=com.android.chrome
export APP_ID
FONT=${FONT_SCALE:-1.0}

adb wait-for-device
for i in $(seq 1 60); do [ "$(adb shell getprop sys.boot_completed | tr -d '\r')" = 1 ] && break; sleep 3; done

# 1. Phone language (the emulator boots in en-US; google_apis images allow adb root)
if [ "$(adb shell getprop persist.sys.locale | tr -d '\r')" != "$LOCALE" ]; then
  adb root >/dev/null 2>&1; sleep 3; adb wait-for-device
  adb shell "setprop persist.sys.locale $LOCALE; setprop ctl.restart zygote"; sleep 10; adb wait-for-device
  for i in $(seq 1 60); do [ "$(adb shell getprop sys.boot_completed | tr -d '\r')" = 1 ] && break; sleep 3; done
fi
adb root >/dev/null 2>&1; sleep 2; adb wait-for-device
adb shell settings put system font_scale "$FONT"
[ "${THEME:-light}" = dark ] && adb shell cmd uimode night yes
adb emu geo fix "${GEO#*,}" "${GEO%,*}" >/dev/null 2>&1   # longitude first

# 2. Soft keyboard + Chrome without its first-run screens
#    The AVD may report a hardware keyboard, which hides the on-screen one;
#    this secure setting shows it anyway, like on a real phone.
adb shell settings put secure show_ime_with_hard_keyboard 1
adb shell "echo '_ --disable-fre --no-first-run --no-default-browser-check --disable-notifications' > /data/local/tmp/chrome-command-line; chmod 755 /data/local/tmp/chrome-command-line"
adb shell am set-debug-app --persistent com.android.chrome >/dev/null 2>&1 || true
adb shell pm grant com.android.chrome android.permission.POST_NOTIFICATIONS >/dev/null 2>&1 || true   # Android 13+: no notification promo
if ! adb shell pm list packages com.android.chrome | grep -q chrome; then
  echo "ERROR: Chrome is not installed on this emulator image (target google_apis)." >&2
  exit 1
fi
echo "Chrome: $(adb shell dumpsys package com.android.chrome | grep -m1 versionName | tr -d '\r ')"
echo "WebView: $(adb shell dumpsys webviewupdate | grep -m1 'Current WebView package' | tr -d '\r')"

# 3. The runner's app, seen from the emulator as localhost
adb reverse "tcp:$PORT" "tcp:$PORT"

# 4. Sign right before opening: initData lives 300 s and works once
case "$LOCALE" in ru*) LANG_CODE=ru ;; uk*) LANG_CODE=uk ;; *) LANG_CODE=en ;; esac
START_PATH=${START_PATH:-/}
STUDENT_ID=${STUDENT_ID:-610001}
open_app() {  # $1 = path, $2 = telegram id
  local url
  url=$(python3 scripts/velo/sign_init_data.py url --id "$2" --first-name "${PERSONA^}" --lang "$LANG_CODE" \
        --base "http://localhost:$PORT" --path "$1" --platform android) || return 1
  adb shell am force-stop com.android.chrome
  adb shell "am start -a android.intent.action.VIEW -d '$url' com.android.chrome" >/dev/null
}

# 5a. Dry run: the lane is checked without a model
if [ "${AGENT:-true}" != "true" ]; then
  adb logcat -c
  SMOKE_OUT="$OUT" APP_PORT="$PORT" python3 scripts/velo/smoke.py
  CODE=$?
  echo "Smoke finished (exit $CODE), $(ls "$OUT" | wc -l) files"
  exit $CODE
fi

# 5b. The agent
open_app "$START_PATH" "$STUDENT_ID" || exit 1
sleep 12
python3 scripts/velo/chrome_ready.py   # close Chrome's own promo dialogs: the app must be what the agent sees
adb logcat -c
REC=""
if [ "${RECORD_VIDEO:-false}" = true ]; then
  adb shell settings put system show_touches 1
  rm -f /tmp/stop-rec
  ( i=0
    while [ ! -f /tmp/stop-rec ] && [ $i -lt 40 ]; do
      i=$((i + 1)); adb shell screenrecord --bit-rate 4000000 --time-limit 180 "/sdcard/rec_$(printf %02d $i).mp4"
    done ) &
  REC=$!
fi
source scripts/llm_env.sh || exit 1
# Tools: only these. Read/Write/Edit are limited to results/, the brief and the
# personas (the job's environment holds the Claude key; nothing else is readable).
claude -p "Read $BRIEF and personas.json, then do the mission until the final report. PERSONA=$PERSONA SKIN=$SKIN PLATFORM=android APP_ID=$APP_ID. Device: ${DEVICE}, font scale x${FONT}, theme ${THEME:-light}, phone language $LOCALE. The app is already open in Chrome. Write the report for the owner in Russian." \
  --model "${MODEL:-sonnet}" --max-turns 400 --output-format json \
  --allowedTools "Bash(adb:*),Bash(python3 scripts/android/screen.py:*),Bash(python3 scripts/android/type.py:*),Bash(sleep:*),Bash(ls:*),Bash(mkdir:*),Read(./results/**),Read(./briefs/**),Read(./personas.json),Write(./results/**),Edit(./results/**)" \
  > results/agent-output.json 2> results/agent-errors.txt
CODE=$?
python3 scripts/agent_status.py results/agent-output.json results/agent-errors.txt "$NAME" || true
if [ -n "$REC" ]; then
  touch /tmp/stop-rec; adb shell pkill -INT screenrecord; sleep 4; kill "$REC" 2>/dev/null
  mkdir -p "$OUT/video"
  for f in $(adb shell ls /sdcard/ | tr -d '\r' | grep '^rec_'); do adb pull "/sdcard/$f" "$OUT/video/" >/dev/null 2>&1; done
fi
echo "Agent finished (exit $CODE), $(ls "$OUT" | wc -l) files"
exit 0
