#!/bin/bash
# SHA weekly ad-comments digest -> ~/systems/comments-digest/out/digest-YYYY-MM-DD.md
# Served by CCC at /api/comments/digest (COMMENTS_DIGEST_DIR in .env.local).
# Runs Tuesdays 04:00 via comments-digest.timer (systemd user). Manual: bash run_digest.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="$SCRIPT_DIR/out"
mkdir -p "$OUT_DIR"

# Load env (BQ creds)
if [ -f "$HOME/.hermes/.env" ]; then
  set -o allexport; source "$HOME/.hermes/.env"; set +o allexport
fi
export GOOGLE_APPLICATION_CREDENTIALS="${GOOGLE_APPLICATION_CREDENTIALS/#\~/$HOME}"
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"

command -v bq >/dev/null || { echo "FAIL: bq CLI not on PATH"; exit 2; }
# claude-max = Max OAuth wrapper (unsets the empty ANTHROPIC_API_KEY sourced above, honors usage-guard pause).
CLAUDE_BIN="/usr/local/bin/claude-max"
[ -x "$CLAUDE_BIN" ] || { echo "FAIL: $CLAUDE_BIN missing"; exit 2; }
# shellcheck source=/dev/null
[ -f "$SCRIPT_DIR/../lib/hermes_fallback.sh" ] && . "$SCRIPT_DIR/../lib/hermes_fallback.sh"
[ -f "$GOOGLE_APPLICATION_CREDENTIALS" ] || { echo "FAIL: SA file missing"; exit 2; }

TO=$(date +%Y-%m-%d)
FROM=$(date -d "-7 days" +%Y-%m-%d)
TODAY=$(date +%Y-%m-%d)

echo "=== comments-digest $FROM -> $TO ($(date)) ==="

WORK=$(mktemp -d /tmp/comments-digest.XXXXXX)
trap 'rm -rf "$WORK"' EXIT

run_query() {
  local sql_file="$1" out_name
  out_name="$(basename "$sql_file" .sql)"
  echo ">> $out_name.sql"
  # Pipe via stdin so bq doesn't parse leading -- comments as flags
  sed -e "s|{{FROM}}|$FROM|g" -e "s|{{TO}}|$TO|g" "$sql_file" \
  | bq query --use_legacy_sql=false --format=pretty --max_rows=400 \
    > "$WORK/$out_name.txt" 2>"$WORK/$out_name.err" || {
      echo "WARN: $out_name failed: $(tail -1 "$WORK/$out_name.err")"
    }
}
for q in "$SCRIPT_DIR/queries/"*.sql; do run_query "$q"; done

# Need actual customer comments to digest. No-data is NOT a job failure (exit 0):
# the upstream BQ comments feed can legitimately be empty/dead (e.g. dead since 2026-06-22,
# data-team issue) and a nonzero exit here parks the unit in 'failed', polluting the watchdog.
if ! grep -q "|" "$WORK/01_comments.txt" 2>/dev/null; then
  echo "WARN: no comments returned for $FROM..$TO — skipping digest (upstream facebook_dashboard_comments feed empty; check with data team if this persists)"
  exit 0
fi

# Laya pass: yes/no flags (adverse, order problem, subscription, price) over every comment.
# Fail-soft: a dead laya.service only costs the {{FLAGS}} block, never the digest.
echo ">> laya flags"
sed -e "s|{{FROM}}|$FROM|g" -e "s|{{TO}}|$TO|g" "$SCRIPT_DIR/queries/01_comments.sql" \
  | bq query --use_legacy_sql=false --format=json --max_rows=400 > "$WORK/01_comments.json" 2>/dev/null \
  && timeout 2400 python3 "$SCRIPT_DIR/flag_comments.py" "$WORK/01_comments.json" "$OUT_DIR/flags-$TODAY.jsonl" \
     > "$WORK/_flags.md" 2>"$WORK/_flags.err" \
  || echo "(Laya flagger failed this run; estimate from the sample as usual.)" > "$WORK/_flags.md"
echo "   $(head -1 "$WORK/_flags.md" | cut -c1-120)"

# Assemble prompt
python3 - "$SCRIPT_DIR/digest_prompt.txt" "$WORK/_prompt.txt" "$FROM" "$TO" \
  "$WORK/01_comments.txt" "$WORK/02_page_replies.txt" "$WORK/03_top_posts.txt" "$WORK/_flags.md" <<'PY'
import sys, pathlib
tpl, out, frm, to, comments, replies, top, flags = sys.argv[1:9]
read = lambda p: pathlib.Path(p).read_text() if pathlib.Path(p).exists() else "(none)"
text = pathlib.Path(tpl).read_text()
for k, v in {
    "{{FROM}}": frm, "{{TO}}": to,
    "{{COMMENTS}}": read(comments),
    "{{REPLIES}}": read(replies),
    "{{TOP_POSTS}}": read(top),
    "{{FLAGS}}": read(flags),
}.items():
    text = text.replace(k, v)
pathlib.Path(out).write_text(text)
PY

# Claude pass: prompt via stdin, output to LOCAL temp, validate H1, retry 3x
echo ">> claude -p (digesting)"
RAW="$WORK/_raw.md"
OK=0
for attempt in 1 2 3; do
  : > "$RAW"
  if timeout 900 "$CLAUDE_BIN" -p --model claude-sonnet-4-6 --output-format text < "$WORK/_prompt.txt" > "$RAW" 2>"$WORK/_claude.err"; then
    if [ -s "$RAW" ] && grep -q "^# SHA Ad Comments Digest" "$RAW"; then OK=1; break; fi
    echo "WARN: attempt $attempt invalid output ($(wc -c <"$RAW") bytes): $(head -c 200 "$RAW") — retrying"
  else
    # claude prints auth/limit errors on stdout, not stderr — log both (2026-09-29 failed with an empty reason)
    echo "WARN: attempt $attempt claude errored: $(tail -1 "$WORK/_claude.err") $(head -c 200 "$RAW") — retrying"
  fi
  sleep 15
done
if [ "$OK" != "1" ] && command -v hermes_fallback >/dev/null 2>&1 \
   && hermes_fallback "$WORK/_prompt.txt" "$RAW" "$WORK/_claude.err" \
   && grep -q "^# SHA Ad Comments Digest" "$RAW"; then
  OK=1; echo ">> recovered via hermes"
fi
[ "$OK" = "1" ] || { echo "FAIL: claude output invalid after 3 attempts"; exit 3; }

cp -f "$RAW" "$OUT_DIR/digest-$TODAY.md"
# Keep last 12 digests
ls -t "$OUT_DIR"/digest-*.md 2>/dev/null | tail -n +13 | xargs rm -f 2>/dev/null || true
ls -t "$OUT_DIR"/flags-*.jsonl 2>/dev/null | tail -n +13 | xargs rm -f 2>/dev/null || true

echo "DONE: $OUT_DIR/digest-$TODAY.md ($(wc -l <"$OUT_DIR/digest-$TODAY.md") lines)"
