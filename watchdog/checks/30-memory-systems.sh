#!/bin/bash
# Memory-system health: compiler daily logs, KB freshness, auto-memory index sync, gbrain.
# Portable Mac/box: compiler checks self-skip where claude-memory-compiler isn't deployed
# (the box uses gbrain as its memory layer, not the compiler).
set -uo pipefail
WD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$WD_DIR/lib/common.sh"

COMPILER="$HOME/.tools/claude-memory-compiler"
MEMDIR="$HOME/.claude/projects/-home-tomas/memory"

if [ -d "$COMPILER" ]; then
  # 1. Compiler daily log written in last 48h
  newest=$(newest_mtime_epoch "$COMPILER"/daily/*.md)
  age=$(age_hours "$newest")
  if [ "$age" -le 48 ]; then ok "memory:compiler-daily" "latest daily log ${age}h old"
  else fail "memory:compiler-daily" "no daily log for ${age}h — SessionEnd hook may be broken"; fi

  # 2. KB index compiled in last 4 days
  age=$(age_hours "$(newest_mtime_epoch "$COMPILER/knowledge/index.md")")
  if [ "$age" -le 96 ]; then ok "memory:kb-compile" "index.md ${age}h old"
  else warn "memory:kb-compile" "knowledge/index.md ${age}h old — compile may have stopped"; fi
else
  ok "memory:compiler" "compiler not deployed on this host — gbrain is the memory layer here"
fi

# 3. Auto-memory index drift: files vs MEMORY.md lines
files=$(ls "$MEMDIR"/*.md 2>/dev/null | grep -cv MEMORY.md)
indexed=$(grep -c '](.*\.md)' "$MEMDIR/MEMORY.md" 2>/dev/null || echo 0)
drift=$(( files - indexed )); [ "$drift" -lt 0 ] && drift=$(( -drift ))
if [ "$drift" -le 5 ]; then ok "memory:index-sync" "$files files / $indexed indexed"
else warn "memory:index-sync" "drift: $files memory files vs $indexed index entries"; fi

# 3b. MEMORY.md truncation cliff: index is loaded whole each session, ~200-line cap
memlines=$(wc -l < "$MEMDIR/MEMORY.md" 2>/dev/null | tr -d ' ')
if [ "${memlines:-0}" -lt 170 ]; then ok "memory:index-size" "MEMORY.md ${memlines} lines"
elif [ "${memlines:-0}" -lt 200 ]; then warn "memory:index-size" "MEMORY.md ${memlines} lines — approaching ~200-line truncation cliff, consolidate"
else fail "memory:index-size" "MEMORY.md ${memlines} lines — OVER the ~200-line cliff, entries are being dropped"; fi

# 4. gbrain reachable + embeddings complete (skip silently if CLI missing)
export PATH="$HOME/.bun/bin:$PATH"
if command -v gbrain >/dev/null; then
  stats=$(timeout 25 gbrain stats 2>/dev/null)
  if [ -z "$stats" ]; then
    warn "memory:gbrain" "gbrain stats timed out / unreachable"
  else
    pages=$(echo "$stats" | awk '/^Pages:/{print $2}')
    chunks=$(echo "$stats" | awk '/^Chunks:/{print $2}')
    embedded=$(echo "$stats" | awk '/^Embedded:/{print $2}')
    links=$(echo "$stats" | awk '/^Links:/{print $2}')
    if [ "${chunks:-0}" != "${embedded:-1}" ]; then
      warn "memory:gbrain" "embeddings stale: $embedded/$chunks chunks embedded"
    else
      # links=0 is expected for now: compiler-style pages carry no entity-link markup (checked 2026-06-10)
      ok "memory:gbrain" "$pages pages, $embedded/$chunks embedded, $links links"
    fi
  fi
fi
