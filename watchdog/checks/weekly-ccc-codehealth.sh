#!/bin/bash
# CCC steward (weekly): vitest + tsc in the live dir.
# Both are safe alongside a running dev server; `npm run build` is NOT (corrupts .next) — never add it here.
set -uo pipefail
WD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$WD_DIR/lib/common.sh"

CCC="$HOME/creative-command-center"
cd "$CCC" || { fail "ccc:codehealth" "project dir missing: $CCC"; exit 0; }

out=$(npm run test 2>&1 | tail -15)
if echo "$out" | grep -qE 'failed|FAIL'; then
  fail "ccc:vitest" "tests failing: $(echo "$out" | grep -E 'failed|FAIL' | head -1)"
else
  passed=$(echo "$out" | grep -oE 'Tests +[0-9]+ passed' | head -1)
  [ -z "$passed" ] && passed=$(echo "$out" | grep -oE '[0-9]+ passed' | tail -1)
  ok "ccc:vitest" "${passed:-tests pass}"
fi

if npx tsc --noEmit >/tmp/ccc-tsc.log 2>&1; then
  ok "ccc:tsc" "typecheck clean"
else
  fail "ccc:tsc" "tsc errors: $(head -1 /tmp/ccc-tsc.log)"
fi

# Uncommitted work older than a week tends to get lost — nudge
dirty=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
if [ "$dirty" -gt 0 ]; then warn "ccc:git" "$dirty uncommitted change(s) on $(git branch --show-current)"
else ok "ccc:git" "tree clean on $(git branch --show-current)"; fi
