#!/usr/bin/env bash
# canon-drift scan — alerts when brand FACTS appear baked into skill/command
# instruction surfaces. Facts belong ONLY in the canon memory files
# (shameless_brand_canon.md / shameless_compliance_language.md); skills carry
# craft and read canon at runtime (memory: feedback_canon_single_source).
#
# Scope: SKILL.md files under ~/.claude/skills + ~/.hermes/skills (symlinks
# followed), ~/.claude/commands/*.md, and (since 2026-08-05, after a stale
# "Fiber = default angle" line in a workflow memory shipped fiber-first copy)
# the memory dir ~/brain/memory/*.md — EXCLUDING the sanctioned fact carriers
# (brand canon, compliance language, CTA doctrine, MEMORY.md index) and
# sync-conflict files. references/ docs, .bak files, memory archive/, and
# compliance-eval (the sanctioned machine mirror) are out of scope.
# NOTE: memory hits were baseline-seeded into state.txt on 2026-08-05 —
# only NEW bakes alert.
# State-file dedupe: ntfy only on NEW hits (launch-details-scan pattern).
set -uo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
STATE="$DIR/state.txt"; LOG="$DIR/scan.log"
NTFY_TOPIC="tomas-ph-1ea8ac8e"
touch "$STATE"

# Fact signatures that must never live in an instruction surface. Keep this
# list SHAPE-based (banned-term literals + stat signatures), not a copy of the
# canon lists — it only needs to catch baked copies, not adjudicate copy.
PATTERNS='prebiotic|pooping every day|eat the whole bag|allulose|appetite suppressant|only [0-9]+ ?g (of )?(sugar|net ?carbs?|carbs?|fiber)|only [0-9]+ calories|26g/70/3/3|26g fiber / 70 cal|daily-fiber CTA convention'

targets=$( { find -L "$HOME/.claude/skills" "$HOME/.hermes/skills" "$HOME/brain/.claude/skills" -maxdepth 4 -name 'SKILL.md' 2>/dev/null; \
             find "$HOME/.claude/commands" "$HOME/brain/.claude/commands" "$HOME/brain/.claude/agents" -maxdepth 1 -name '*.md' 2>/dev/null; \
             find "$HOME/brain/memory" -maxdepth 1 -name '*.md' 2>/dev/null \
               | grep -vE 'shameless_brand_canon\.md|shameless_compliance_language\.md|feedback_shameless_cta_daily_fiber\.md|MEMORY(\.sync-conflict[^/]*)?\.md|sync-conflict'; } | sort -u )
[ -z "$targets" ] && { echo "$(date '+%F %T') no targets found" >> "$LOG"; exit 0; }

hits=$(echo "$targets" | xargs grep -HniE "$PATTERNS" 2>/dev/null | grep -v '\.bak' || true)

ts="$(date '+%F %T')"
if [ -z "$hits" ]; then
  echo "$ts clean ($(echo "$targets" | wc -l | tr -d ' ') files)" >> "$LOG"
  exit 0
fi

new=$(echo "$hits" | grep -Fxv -f "$STATE" || true)
echo "$ts HITS: $(echo "$hits" | wc -l | tr -d ' ') (new: $(echo "$new" | grep -c . || true))" >> "$LOG"
echo "$hits" >> "$LOG"
{ cat "$STATE"; echo "$hits"; } | sort -u > "$STATE.tmp" && mv "$STATE.tmp" "$STATE"

if [ -n "$new" ]; then
  body="Canon facts baked into skill/command surfaces (fix: move to canon memory files, leave a pointer):
$(echo "$new" | cut -c1-160 | head -10)"
  curl -s -m 15 -H "Title: Canon drift detected ($(hostname -s))" -H "Priority: default" -H "Tags: warning" \
    -d "$body" "https://ntfy.sh/$NTFY_TOPIC" >/dev/null 2>&1 || echo "$ts ntfy push failed" >> "$LOG"
fi
