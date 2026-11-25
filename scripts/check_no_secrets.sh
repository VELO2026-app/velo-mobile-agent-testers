#!/usr/bin/env bash
# Fails when a tracked file (or the history) looks like it holds a secret or a
# personal address. A public repository: a leak here is permanent.
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"
bad=0
PAT_PRIVATE='-----BEGIN ([A-Z]+ )?PRIVATE KEY-----'
PAT_TOKENS='sk-ant-[A-Za-z0-9_-]{10,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|[0-9]{8,10}:AA[A-Za-z0-9_-]{30,}|xox[abp]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}'
PAT_EMAIL='[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
SELF=scripts/check_no_secrets.sh
scan() {  # $1 = label, $2 = pattern, rest = grep options
  local label=$1 pat=$2; shift 2
  if git grep -nIE "$@" -e "$pat" -- . ":(exclude)$SELF" ":(exclude)LICENSE" >/tmp/scan.out 2>/dev/null; then
    echo "FOUND $label:"; sed 's/^\(.\{140\}\).*/\1.../' /tmp/scan.out | head -5; bad=1
  fi
}
scan "a private key" "$PAT_PRIVATE"
scan "a token-shaped string" "$PAT_TOKENS"
# e-mail addresses: only noreply and example ones are allowed
if git grep -nIhoE -e "$PAT_EMAIL" -- . ":(exclude)$SELF" ":(exclude)LICENSE" | grep -viE '@(users\.noreply\.github\.com|example\.(com|org)|anthropic\.com|simulator\.amazonses\.com)$' >/tmp/scan.out; then
  echo "FOUND an e-mail address:"; head -3 /tmp/scan.out; bad=1
fi
# the history too: every commit's author must be a noreply identity
if git rev-parse HEAD >/dev/null 2>&1; then
  if git log --format='%ae%n%ce' | sort -u | grep -v 'noreply' | grep -q .; then
    echo "FOUND a commit by a non-noreply e-mail (history is public)"; bad=1
  fi
  if git log -p --all -G"$PAT_PRIVATE|$PAT_TOKENS" --format= -- . ":(exclude)$SELF" ":(exclude)LICENSE" | grep -q .; then
    echo "FOUND a secret-shaped string in the history"; bad=1
  fi
fi
[ "$bad" = 0 ] && echo "no secrets or personal addresses found"
exit $bad
