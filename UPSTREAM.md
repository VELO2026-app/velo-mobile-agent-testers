# Upstream

Vendored from https://github.com/pierridotite/mobile-agent-testers (MIT,
Copyright (c) 2026 Pierre Raffalli; the licence text is kept in LICENSE).

- Commit vendored: `d610b95a1670aa6031aa23cfa8cd8987ce478abf` (2026-11-24)
- Unchanged copies: `scripts/a11y.py`, `scripts/agent_status.py`, `scripts/collect.sh`,
  `scripts/encrypt_results.sh`, `scripts/llm_env.sh`, `scripts/summarize.py`,
  `scripts/matrix.py`, `scripts/android/screen.py`, `scripts/android/type.py`
- `personas.json`: only the 10 Android personas.
- Not taken: iOS (macOS runners, Simulator), the app build jobs, the demo app,
  other languages of the docs, the assets, the Claude Code plugin.
- Ours: `.github/workflows/velo-android.yml` (replaces upstream's
  `agent-testers.yml`), `scripts/velo/*`, `briefs/velo-student.md`, `docs/*`, `tests/*`.
  `scripts/velo/run_android.sh` is derived from upstream's `scripts/android/run_agent.sh`
  (Chrome instead of an installed APK, no analytics-host blocking, narrower tool permissions).

The project is a week old with one author. We pin this commit and do not track
upstream; to take a change, diff against the commit above.
