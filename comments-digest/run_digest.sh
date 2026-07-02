#!/bin/bash
# SHA weekly ad-comments digest -> ~/systems/comments-digest/out/digest-YYYY-MM-DD.md
# Served by CCC at /api/comments/digest (COMMENTS_DIGEST_DIR in .env.local).
# Runs Tuesdays 09:00 via com.tomas.comments-digest. Manual: bash run_digest.sh
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
command -v claude >/dev/null || { echo "FAIL: claude CLI not on PATH"; exit 2; }
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

# Assemble prompt
python3 - "$SCRIPT_DIR/digest_prompt.txt" "$WORK/_prompt.txt" "$FROM" "$TO" \
  "$WORK/01_comments.txt" "$WORK/02_page_replies.txt" "$WORK/03_top_posts.txt" <<'PY'
import sys, pathlib
tpl, out, frm, to, comments, replies, top = sys.argv[1:8]
read = lambda p: pathlib.Path(p).read_text() if pathlib.Path(p).exists() else "(none)"
text = pathlib.Path(tpl).read_text()
for k, v in {
    "{{FROM}}": frm, "{{TO}}": to,
    "{{COMMENTS}}": read(comments),
    "{{REPLIES}}": read(replies),
    "{{TOP_POSTS}}": read(top),
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
  if claude -p --model claude-sonnet-4-6 --output-format text < "$WORK/_prompt.txt" > "$RAW" 2>"$WORK/_claude.err"; then
    if [ -s "$RAW" ] && grep -q "^# SHA Ad Comments Digest" "$RAW"; then OK=1; break; fi
    echo "WARN: attempt $attempt invalid output ($(wc -c <"$RAW") bytes) — retrying"
  else
    echo "WARN: attempt $attempt claude errored: $(tail -1 "$WORK/_claude.err") — retrying"
  fi
  sleep 15
done
[ "$OK" = "1" ] || { echo "FAIL: claude output invalid after 3 attempts"; exit 3; }

cp -f "$RAW" "$OUT_DIR/digest-$TODAY.md"
# Keep last 12 digests
ls -t "$OUT_DIR"/digest-*.md 2>/dev/null | tail -n +13 | xargs rm -f 2>/dev/null || true

echo "DONE: $OUT_DIR/digest-$TODAY.md ($(wc -l <"$OUT_DIR/digest-$TODAY.md") lines)"
