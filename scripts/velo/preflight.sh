#!/usr/bin/env bash
# Fails FAST, before any runner minute is spent, with a message that says what
# to do. Reads the environment the workflow passes (secrets arrive as env).
#   AGENT        "true" when the agent will run, "false" for a dry run
#   LLM_BASE_URL optional: another Anthropic-compatible API
# Secrets: CLAUDE_CODE_OAUTH_TOKEN | ANTHROPIC_API_KEY | LLM_API_KEY
set -euo pipefail

REPO=${GITHUB_REPOSITORY:-VELO2026-app/velo-mobile-agent-testers}
fail() { echo "::error title=$1::$2"; echo "ERROR: $2" >&2; exit 1; }

[ -s results_public.pem ] || fail "results_public.pem missing" \
  "results_public.pem is empty or missing. It is the PUBLIC key that encrypts results; its private half stays on the owner's machine (README: Results)."
grep -q "BEGIN PUBLIC KEY" results_public.pem || fail "results_public.pem is not a public key" \
  "results_public.pem must start with BEGIN PUBLIC KEY. Never commit a private key."

if [ "${AGENT:-true}" != "true" ]; then
  echo "Dry run (agent=false): no Claude key needed."
  exit 0
fi

if [ -n "${LLM_BASE_URL:-}" ]; then
  [ -n "${LLM_API_KEY:-}" ] || fail "LLM_API_KEY is empty" \
    "llm_base_url is set, so the key must be the LLM_API_KEY secret: gh secret set LLM_API_KEY -R $REPO"
  echo "Key found: LLM_API_KEY (for $LLM_BASE_URL)."
  exit 0
fi

if [ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]; then
  echo "Key found: CLAUDE_CODE_OAUTH_TOKEN (Claude subscription)."
elif [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  echo "Key found: ANTHROPIC_API_KEY."
else
  fail "No Claude key in the repository secrets" \
"The agent needs a Claude key and none is set. Add ONE of these secrets to $REPO (Settings > Secrets and variables > Actions, or the gh command), then run again:
  CLAUDE_CODE_OAUTH_TOKEN  a subscription token: run 'claude setup-token' on your machine, then 'gh secret set CLAUDE_CODE_OAUTH_TOKEN -R $REPO'
  ANTHROPIC_API_KEY        an API key: 'gh secret set ANTHROPIC_API_KEY -R $REPO'
To check everything else without a key, run the workflow with agent=false (dry run: stack, emulator, Chrome, keyboard)."
fi
