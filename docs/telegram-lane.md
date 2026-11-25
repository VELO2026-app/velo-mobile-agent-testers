# Telegram lane: the Mini App inside Telegram on an Android emulator

Status: **a plan; nothing is installed on the owner's Mac.** One fact is
verified (below) and it changes the plan: on Android there is no safe
"test account" route, so this lane needs a real Telegram account.

## What it adds over the CI lane

The CI lane opens the app in plain Chrome with Telegram's launch parameters.
Inside Telegram the app also gets Telegram's own chrome: the top inset of the
header buttons, the BackButton and MainButton, the way the WebView resizes
around the keyboard, `disableVerticalSwipes`. Those are the items the manual
checklists of PRs #187, #194, #205, #206 mention. Android only: Telegram for
iOS cannot run on the Simulator (its App Store build is for devices), so
iPhone stays a manual check.

## Verified: Telegram's test environment is NOT reachable on Android

Telegram runs a separate test server with fake accounts (phone `99966XYYYY`,
code `XXXXX`, data wiped periodically; a bot made with @BotFather on that
server; Mini App URLs may be plain `http://`) - from
[Telegram's docs](https://core.telegram.org/bots/webapps#testing-mini-apps) and
[test accounts](https://core.telegram.org/api/auth#test-accounts). That would
have made the emulator session worthless to an attacker. The docs give the way
in only for iOS, Desktop and macOS. For Android, two independent checks:

1. **The open source** ([DrKLO/Telegram](https://github.com/DrKLO/Telegram), master).
   The "Test backend" checkbox on the login screen
   (`LoginActivity`: `allowTestBackend = BuildVars.DEBUG_VERSION || TEST_BACKEND_IN_STORE && !BuildConfig.BUNDLE || isTestBackend()`,
   with `TEST_BACKEND_IN_STORE = false`) and the "Switch Backend" row in Settings
   (`ProfileActivity`, `if (BuildVars.DEBUG_VERSION)`) exist **only in debug builds**.
2. **The real APK, on an emulator**
   ([run 45591293090](https://github.com/VELO2026-app/velo-mobile-agent-testers/actions/runs/45591293090),
   workflow `telegram-probe.yml`, no key, no login, nothing typed): the official
   APK `org.telegram.messenger.web` 13.3.1 from telegram.org (not debuggable) installs and runs
   on the x86_64 emulator; its "Your phone number" screen has **no checkbox and no
   test-server text**; ten taps on the title and a long press change nothing.

So with the stock Android app the only way in is a real account.

## Options

| Option | Verdict |
|---|---|
| **B. A real, dedicated account in the emulator, local only** | The only working route. Rules below |
| Build Telegram from source as a debug build (the switch appears) | Not recommended: needs an `api_id`/`api_hash` from my.telegram.org (a Telegram app registration, with a real account) and a heavy Gradle/NDK build |
| iPhone test environment (documented: tap Settings 10 times > Accounts > Login to another account > Test) | Works on the owner's own iPhone as a manual check; the Simulator cannot run Telegram |
| Skip the lane | Keep the Telegram-only items (top inset, BackButton, vertical-swipe collapse, iPhone) as the owner's manual checks. Reasonable if the CI lane finds enough |

**Suggested order:** run the CI lane's agent first (README). If its reports are
useful, decide then whether Telegram's own chrome is worth a real account on an
emulator. That decision belongs to the owner.

## Option B: real account, the rules

A login puts a key to that account on the Mac:

- the session lives in the AVD (`~/.android/avd/<name>.avd/userdata-qemu.img`
  and any quick-boot snapshot, which also holds RAM). Treat both as the
  account's password;
- **the agent's screenshots go to the model provider.** Anything on screen
  (chat list, messages) is sent. The account must have **no other chats than the
  bot's**;
- Telegram may flag a login from an emulator and ask to re-confirm.

Rules: a **dedicated account** (a second number, nothing in the chat list but the
bot), cloud password (2FA) on, the AVD folder excluded from Time Machine
(`tmutil addexclusion ~/.android`), FileVault on, quick-boot snapshot **off**
(`-no-snapshot-save`: no RAM with the session on disk; the session itself
survives in the data partition, boot is 60-90 s), never copied, zipped,
committed, uploaded or synced. **Local only, never CI and never a server**: a CI
secret or a remote disk that holds an account session is the account. When done:
Telegram > Settings > Devices > terminate the emulator's session, and
`avdmanager delete avd -n velo-tg`.

## Disk: how much, what to install

The Mac had **6.9 GB free of 228 GB (97 % full)** on 2026-11-25. Sizes are the
archive sizes in Google's repository metadata
(`dl.google.com/android/repository/repository2-3.xml` and
`sys-img/google_apis/sys-img2-3.xml`); unpacked sizes are estimates, marked `~`.

| What | Download | On disk |
|---|---|---|
| JDK 17 (for `sdkmanager`/`avdmanager`) | ~200 MB~ | ~300 MB~ |
| Android command-line tools 23.0 (arm64 macOS) | 148 MB | ~250 MB~ |
| platform-tools 37.0.3 (adb) | 16 MB | ~40 MB~ |
| emulator 37.3.10 (arm64 macOS) | 401 MB | ~900 MB~ |
| system image Android 14, `google_apis`, arm64 | 1 536 MB | ~3 GB~ |
| Telegram APK (universal: arm64-v8a included, checked) | ~80 MB~ | ~80 MB~ |
| AVD data partition (grows with use) | | 2-6 GB~ |
| **Total** | **~2.4 GB** | **~7-10 GB~** |

**Free at least 15 GB before starting.** Measured candidates (`du`, not touched
except the old `node_modules` already removed): `~/Downloads` 13.1 GB;
`~/Library/Containers/com.docker.docker` 12.7 GB (`docker image prune -a` and
`docker builder prune` only: the goodo-dev stand's RustFS volume lives here);
`~/.cache` 7.5 GB; `~/Library/pnpm` 7.0 GB (`pnpm store prune`);
`~/Library/Caches` 6.4 GB; `~/.npm` 4.3 GB.

A server is not an option: the tested VPS has no `/dev/kvm` (no nested
virtualization), and an account session must not live on a remote disk anyway.
GitHub's runners do have KVM, which is why the CI lane needs no server.

## Steps (if the owner chooses B)

**Owner, by hand**

1. Free disk to 15 GB or more. Make or choose a dedicated Telegram account
   (nothing in its chat list). Tell the agent "ставь".
2. Be at the Mac for two things: the Android SDK licence prompt (read and accept it
   yourself) and, if the JDK installer asks, the macOS password.

**Agent, after "ставь"** (all under `~/android-sdk`, nothing global, nothing in a repo)

3. `brew install openjdk@17` (or the Temurin cask), `JAVA_HOME` for the shell session only.
4. Download `https://dl.google.com/android/repository/commandlinetools-mac_arm64-16111833_latest.zip`
   (sha1 `ad03dc49bfacfd52c110b14104ea548b8a07e830`, from Google's metadata), verify, unpack to
   `~/android-sdk/cmdline-tools/latest`.
5. `sdkmanager --licenses` **(owner accepts)**, then
   `sdkmanager "platform-tools" "emulator" "system-images;android-34;google_apis;arm64-v8a"`.
6. `avdmanager create avd -n velo-tg -k "system-images;android-34;google_apis;arm64-v8a" -d pixel_7`;
   in `config.ini`: `hw.keyboard=no` (on-screen keyboard), `hw.ramSize=3072`.
7. Telegram for Android from https://telegram.org/android (the official APK; the probe
   used `org.telegram.messenger.web`); `adb install`.
8. Start the emulator with a window: `emulator -avd velo-tg -no-snapshot-save`.

**Owner, by hand, in the emulator window (nobody else sees this)**

9. Log in with the dedicated account (phone, the code from Telegram, 2FA). **The agent
   takes no screenshots during login.** Open the bot's chat and its Mini App once.

**Agent: a stack the emulator can reach, and the run**

10. A local stack with the skin under test on `0.0.0.0:<port>` and the bot's token. **The bot is a
    real bot, so its Mini App URL must be HTTPS** (a tunnel, as the goodo-dev stand has):
    only Telegram's test server accepts `http://`. Use a dedicated test bot, not the
    production dev bot, and keep its token out of every repository and CI.
11. Run [briefs/velo-student.md](../briefs/velo-student.md) with the differences: the app is opened
    from the bot's chat; Telegram's own chrome is present and in scope; stay in this chat.
    `claude -p` locally with the same allowed tools as `scripts/velo/run_android.sh`, results into a
    local, git-ignored folder.

## What this lane will and will not tell

It will show the real Telegram Android WebView, Telegram's header inset and
BackButton, and the keyboard resize inside Telegram. It will not show iOS
(manual), Telegram's vertical-swipe collapse of a sheet on iPhone, or anything
under the reduced-motion setting unless the brief asks for it.
