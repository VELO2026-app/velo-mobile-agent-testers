# Telegram lane: the Mini App inside Telegram on an Android emulator

Status: **a plan, nothing installed.** It needs disk space, two licence clicks
and a login that only the owner can do. The CI lane (README) has no Telegram;
this one adds it, locally.

## What it adds over the CI lane

The CI lane opens the app in plain Chrome with Telegram's launch parameters.
Inside Telegram the app also gets Telegram's own chrome: the top inset of the
header buttons, the BackButton and MainButton, the way the WebView resizes
around the keyboard, `disableVerticalSwipes`. Those are exactly the items the
manual checklists of PRs #187, #194, #205, #206 mention. Android only: Telegram
for iOS cannot run on the Simulator (its App Store build is for devices), so
iPhone stays a manual check.

## Two ways to log in, one recommended

Both are local only. **Neither the session nor a bot token goes into this
repository, its secrets or any CI.**

### A. Telegram's test environment (recommended): nothing real to lose

Telegram runs a separate server for developers. Verified in Telegram's docs
([Mini Apps: testing](https://core.telegram.org/bots/webapps#testing-mini-apps),
[auth: test accounts](https://core.telegram.org/api/auth#test-accounts)):

- accounts there are fake: phone `99966XYYYY` (`X` = a datacentre digit, `YYYY`
  random), the login code is `XXXXX` (the digit repeated five times); nothing
  real is stored and Telegram wipes the data periodically;
- it is "completely separate" from the real network: a new account and a new bot
  made with @BotFather **on the test server**, the Bot API called as
  `https://api.telegram.org/bot<token>/test/METHOD`;
- a Mini App there may use a plain `http://` URL, even an IP, so the
  emulator can open the owner's Mac as `http://10.0.2.2:<port>`.

So the session in the emulator is a throwaway test account, and the AVD
snapshot is worth nothing to anyone. The bot token is a test-environment token
(not the production dev bot's) and is only used by a local stack.

**Open question that decides A: how to switch Telegram for Android to the test
server.** The docs list the way in only for iOS (tap Settings 10 times >
Accounts > Login to another account > Test), Desktop (Shift+Alt+right-click
"Add Account") and macOS. For Android they only describe the debug menu
(Settings > scroll down > press and hold the version number twice) for WebView
debugging; whether it has a backend switch is **not confirmed**. Step 4 below
checks it in two minutes, before anything else is spent. If there is no switch,
use B.

### B. A real account in the emulator (the owner's offer): only with a dedicated account

A login on a real account puts a key to that account on the Mac:

- the session lives in the AVD (`~/.android/avd/<name>.avd/userdata-qemu.img`
  and any quick-boot snapshot, which also holds RAM). Treat both as the
  account's password;
- **the agent's screenshots go to the model provider.** Anything on screen
  (chat list, messages) is sent. The account must have no other chats than the
  bot's;
- Telegram may flag a login from an emulator and ask to re-confirm;
- if the owner's main account is used, secret chats stay on the phone, but
  every other chat is exposed to the screenshots.

Rules if B is used: a **dedicated account** (a second number, nothing in the
chat list but the bot), cloud password (2FA) on, the AVD folder excluded from
Time Machine (`tmutil addexclusion ~/.android`), FileVault on, never copied,
zipped, committed, uploaded or synced; when done: Telegram > Settings > Devices
> terminate the emulator's session, and `avdmanager delete avd -n velo-tg`.

### Snapshot or not

A quick-boot snapshot only makes boot faster (about 10 s against 60-90 s); the
session survives without it, in the data partition. Under A keep it. Under B
turn it off (`-no-snapshot-save`) so RAM with the session is not written to
disk on exit; pay the longer boot.

### Local only, never CI

Under B: never (a CI secret that holds an account session is the account).
Under A: possible later (download the APK per run, a scripted debug-menu login,
the test bot's token as a secret) but fragile and unproven. Prove the local run
first.

## Disk: how much, what to install

The Mac has **6.9 GB free of 228 GB (97 % full)** after the old `node_modules`
were removed (it was 5.4 GB). Sizes below are the archive sizes in Google's own
repository metadata (`dl.google.com/android/repository/repository2-3.xml`
and `sys-img/google_apis/sys-img2-3.xml`, read on 2026-11-25); unpacked sizes are
estimates, marked `~`.

| What | Download | On disk |
|---|---|---|
| JDK 17 (for `sdkmanager`/`avdmanager`) | ~200 MB | ~300 MB (estimate) |
| Android command-line tools 23.0 (arm64 macOS) | 148 MB | ~250 MB~ |
| platform-tools 37.0.3 (adb) | 16 MB | ~40 MB~ |
| emulator 37.3.10 (arm64 macOS) | 401 MB | ~900 MB~ |
| system image Android 14, `google_apis`, arm64 | 1 536 MB | ~3 GB~ |
| Telegram APK | ~80 MB (estimate) | ~80 MB |
| AVD data partition (grows with use) | | 2-6 GB~ |
| quick-boot snapshot (A only) | | 1-2 GB~ |
| **Total** | **~2.4 GB** | **~8-12 GB~** |

**Free at least 15 GB before starting** (the Mac is at 97 %; macOS and the
emulator both misbehave with a nearly full disk). That is about 8 GB more than
now. Measured candidates (`du`, not touched):

| Where | Size | Note |
|---|---|---|
| `~/Downloads` | 13.1 GB | look through it |
| `~/Library/Containers/com.docker.docker` | 12.7 GB | `docker image prune -a` and `docker builder prune` only: the goodo-dev stand's RustFS volume lives here, do not prune volumes |
| `~/.cache` | 7.5 GB | caches, safe to clear per tool |
| `~/Library/pnpm` | 7.0 GB | `pnpm store prune` drops packages no project uses (many are unused since the old `node_modules` went) |
| `~/Library/Caches` | 6.4 GB | includes `ms-playwright` 1.4 GB (re-downloads when needed) |
| `~/.npm` | 4.3 GB | `npm cache clean --force` |

## Steps

**Owner, by hand**

1. Free disk to 15 GB or more (above). Tell the agent "ставь".
2. Decide A or B. For B: a dedicated Telegram account.
3. Be at the Mac for two things: the Android SDK licence prompt (read and accept it
   yourself) and, if the JDK installer asks, the macOS password.

**Agent, after "ставь"** (all under `~/android-sdk`, nothing global, nothing in a repo)

4. `brew install openjdk@17` (or the Temurin cask), `JAVA_HOME` set for the shell session only.
5. Download `https://dl.google.com/android/repository/commandlinetools-mac_arm64-16111833_latest.zip`
   (sha1 `ad03dc49bfacfd52c110b14104ea548b8a07e830`, from Google's metadata), verify, unpack to
   `~/android-sdk/cmdline-tools/latest`.
6. `sdkmanager --licenses` **(owner accepts)**, then
   `sdkmanager "platform-tools" "emulator" "system-images;android-34;google_apis;arm64-v8a"`.
7. `avdmanager create avd -n velo-tg -k "system-images;android-34;google_apis;arm64-v8a" -d pixel_7`;
   in `config.ini`: `hw.keyboard=no` (on-screen keyboard), `hw.ramSize=3072`.
8. Telegram for Android from https://telegram.org/android (the official APK); `adb install`.
9. Start the emulator with a window: `emulator -avd velo-tg` (A: with snapshot; B: `-no-snapshot-save`).

**Owner, by hand, in the emulator window (nobody else sees this)**

10. A: open the debug menu (press and hold the version number at the bottom of
    Settings, twice) and look for a backend switch to the test server. Found:
    log in with `99966XYYYY` / `XXXXX`. Not found: use B.
    B: log in with the dedicated account (phone, the code from Telegram, 2FA).
    **The agent takes no screenshots during login.**
11. A only: on Telegram Desktop with a test account (Shift+Alt+right-click "Add
    Account" > Test Server), talk to @BotFather: `/newbot`, then set the bot's Mini App
    URL to `http://10.0.2.2:<port>` (menu button or `/newapp`). Give the agent the
    bot's username (not the token).
12. Open the bot's chat and the Mini App once to confirm the stand shows up.

**Agent: a stack the emulator can reach and the run**

13. Run a local stack with the **test bot's token** (A) and the skin under test,
    on `0.0.0.0:<port>` (the existing goodo-dev scripts take the token from their
    own `secrets.env`; this run uses a separate copy, never the production dev bot's).
14. Run the same brief as CI ([briefs/velo-student.md](../briefs/velo-student.md)) with the
    differences: the app is opened from the bot's chat; Telegram's own chrome is
    present and in scope; stay in this chat. `claude -p` locally with the same allowed
    tools as `scripts/velo/run_android.sh`, results into a local, git-ignored folder.

## What this lane will and will not tell

It will show the real Telegram Android WebView, Telegram's header inset and
BackButton, and the keyboard resize inside Telegram. It will not show iOS
(manual), Telegram's vertical-swipe collapse of a sheet on iPhone, or anything
under the reduced-motion setting unless the brief asks for it.
