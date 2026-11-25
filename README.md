# velo-mobile-agent-testers

AI agent testers for the VELO Telegram Mini App on Android emulators. A pilot
for Linear FE-276: can an agent that taps a real emulator with a real soft
keyboard find the keyboard, sheet and gesture bugs that today only the owner
finds by hand on a phone?

Vendored from [pierridotite/mobile-agent-testers](https://github.com/pierridotite/mobile-agent-testers)
(MIT), see [UPSTREAM.md](UPSTREAM.md). Not a fork of the whole template: only
the parts this lane uses, plus our own lane for VELO.

**Public repository: nothing secret lives here.** No Claude key, no Telegram
session, no personal data, no real bot token. See [Safety](#safety).

## What it does

```
velo-android.yml (workflow_dispatch)
  per cell = phone (personas.json) x skin (gold | goodo):
    throwaway VELO stack on the runner      <- built from VELO2026-app/velo at `velo_ref`
      Postgres + Redis + backend + comms stub, app built with the brand skin
      FAKE bot token (e2e:fake): the login the lane signs is worth nothing elsewhere
    Android emulator (KVM) + Chrome         <- app opened as http://localhost:4173 (adb reverse)
    agent=true : Claude Code drives the phone, writes report.md / findings.json / checklist.json
    agent=false: smoke check, no model, no key (scripts/velo/smoke.py)
  results are encrypted with results_public.pem before upload
```

The scenario is [briefs/velo-student.md](briefs/velo-student.md): onboarding,
the new-event form with the keyboard, sheets and their gestures, the diary
composer. Acceptance, by the manual checklists of PRs #187, #194, #205, #206:
[docs/acceptance.md](docs/acceptance.md).

No Telegram here: the app runs in plain Chrome with Telegram's launch
parameters. Telegram on a device is a separate lane:
[docs/telegram-lane.md](docs/telegram-lane.md).

## Status (2026-11-25)

Done and verified in GitHub Actions (free runners, no key):

- **Dry run, both skins, Pixel 7 / API 34 / dark**: green,
  [run 45580035237](https://github.com/VELO2026-app/velo-mobile-agent-testers/actions/runs/45580035237).
  The throwaway stack comes up, the app (gold and goodo builds) opens in Chrome at
  `http://localhost:4173`, the Telegram launch parameters log the synthetic student in, the
  accessibility tree is readable, and **the real Android soft keyboard opens**: Android reports the
  IME shown, `visualViewport` goes 783 -> 471 px and back to 783 px, and the app sets and clears
  `html.is-keyboard-open`. That is what Playwright's WebKit/Chromium emulation could not do
  (FE-276: focus left `visualViewport` at 667).
- **No key = a clear stop**: `agent=true` without a secret fails in the first job in about 20 s,
  the emulator job is skipped,
  [run 45580054201](https://github.com/VELO2026-app/velo-mobile-agent-testers/actions/runs/45580054201).
- Results travel encrypted and decrypt with the owner-side private key (`collect.sh`), checked end to end.
- **Telegram APK probe** (`telegram-probe.yml`, no key, no login):
  [run 45591293090](https://github.com/VELO2026-app/velo-mobile-agent-testers/actions/runs/45591293090).
  The official Telegram for Android (13.3.1) installs and runs on the emulator, but its login screen has no
  switch to Telegram's test environment (that exists only in debug builds, confirmed in the open source),
  so a Telegram lane on Android needs a real, dedicated account: [docs/telegram-lane.md](docs/telegram-lane.md).
- Offline tests (61) and the secret scan pass on every push, history included.

Waiting for the Claude key: the agent run itself, and the acceptance pairs on the commits before the
#205 and #206 fixes ([docs/acceptance.md](docs/acceptance.md)).

## Where the Claude key goes

The agent needs ONE of these **repository secrets** (Settings > Secrets and
variables > Actions). The owner puts it there; nobody commits it:

| Secret | What | How |
|---|---|---|
| `CLAUDE_CODE_OAUTH_TOKEN` | Claude subscription token | `claude setup-token`, then `gh secret set CLAUDE_CODE_OAUTH_TOKEN -R VELO2026-app/velo-mobile-agent-testers` |
| `ANTHROPIC_API_KEY` | API key (pay per token) | `gh secret set ANTHROPIC_API_KEY -R VELO2026-app/velo-mobile-agent-testers` |
| `LLM_API_KEY` | key of another Anthropic-compatible API, with the `llm_base_url` input | `gh secret set LLM_API_KEY -R ...` |

**Without a key the workflow stops in the first job (about 20 seconds) with an
error that says exactly this**, before any emulator is booted
([scripts/velo/preflight.sh](scripts/velo/preflight.sh)). Run with `agent=false`
to check everything else with no key.

On a subscription the runs count against the plan's usage window (5 hours); on
an API key a persona costs roughly $0.15-0.55 on Sonnet by the upstream's
numbers (not yet measured on VELO).

## Run it

```bash
# 1. Dry run, no key: stack + emulator + Chrome + soft keyboard proof
gh workflow run velo-android.yml -R VELO2026-app/velo-mobile-agent-testers -f agent=false

# 2. The agent: one phone, both skins (needs the key)
gh workflow run velo-android.yml -R VELO2026-app/velo-mobile-agent-testers \
  -f agent=true -f skins="gold goodo" -f personas=malik

# 3. A different velo commit (e.g. the acceptance runs, docs/acceptance.md)
gh workflow run velo-android.yml -R VELO2026-app/velo-mobile-agent-testers -f velo_ref=<sha>
```

Inputs: `agent`, `velo_ref` (branch, tag or SHA, default `deploy-machine`),
`skins` (`gold goodo`), `personas` (ids of personas.json: `malik` Pixel 7
API 34 dark, `anna` small phone API 30 font 1.3, `olga` ru-RU...), `brief`,
`start_path`, `model` (`sonnet`, `opus`, `haiku`), `llm_base_url`, `record_video`.

## Results

Reports, screenshots and videos are encrypted before upload (logs of a public
repository are public). Only the holder of the private key can read them. The
key pair is made on the owner's machine; the **private half stays in
`~/.mobile-agent-testers/VELO2026-app_velo-mobile-agent-testers.pem`**, never in
this repository; the public half is [results_public.pem](results_public.pem).

```bash
bash scripts/collect.sh <run id>      # downloads, decrypts, groups: runs/<id>/SUMMARY.md
```

`runs/` is git-ignored. Lost the private key: generate a new pair
(`openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:4096 -out key.pem`,
`openssl pkey -in key.pem -pubout -out results_public.pem`) and commit the new
public half; older runs stay unreadable.

## Safety

- The stack is throwaway and synthetic; its bot token is the fake `e2e:fake`.
  `sign_init_data.py` refuses a real-looking token (`<digits>:<secret>`).
- The Claude key exists only in the emulator step of an agent run, not in the
  plan job, the build steps or a dry run. The agent may read and write only
  `results/`, `briefs/` and `personas.json`, and run `adb`, `screen.py`,
  `type.py`, `sleep`, `ls`, `mkdir` (upstream also allowed `cat` and unrestricted `Read`).
  Residual risk: `adb push` reads runner files into the emulator; the agent only sees
  our synthetic app, so injection would have to come from our own pages.
- `tests.yml` runs [scripts/check_no_secrets.sh](scripts/check_no_secrets.sh) on every push:
  private keys, Claude/GitHub/Telegram token shapes, e-mail addresses.
- Never put a Telegram session, a real bot token or a personal account in
  this repository or in its secrets. The Telegram lane keeps those on the
  owner's machine only.

## Layout

| Path | What |
|---|---|
| `.github/workflows/velo-android.yml` | the lane |
| `.github/workflows/tests.yml` | offline tests + secret scan |
| `.github/workflows/telegram-probe.yml` | keyless probe of the official Telegram APK on an emulator |
| `scripts/velo/` | ours: `sign_init_data.py`, `preflight.sh`, `run_android.sh`, `smoke.py` |
| `scripts/android/`, `a11y.py`, `agent_status.py`, `summarize.py`, `collect.sh`, `encrypt_results.sh`, `llm_env.sh`, `matrix.py` | vendored from upstream |
| `briefs/velo-student.md` | the agent's mission |
| `docs/` | acceptance, Telegram lane |
