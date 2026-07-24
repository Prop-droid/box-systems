#!/usr/bin/env bash
# ccc-leaderboard — Friday-morning creative leaderboard snapshot.
# Pulls the CCC /api/leaderboards (live BQ, dedup + $500 floor), saves a dated
# markdown snapshot, and pushes a compact digest to the phone with the page URL.
set -euo pipefail
cd "$(dirname "$0")"
# ${VAR-default} (not :-) so NTFY_TOPIC="" is an explicit silence-for-testing override
NTFY_TOPIC="${NTFY_TOPIC-tomas-ph-1ea8ac8e}"
API="${CCC_API-http://localhost:3000/api/leaderboards}"
OUT="out/$(date +%F).md"
TMP="$(mktemp)"; trap 'rm -f "$TMP"' EXIT

curl -sf --max-time 120 "$API" -o "$TMP"
[ -s "$TMP" ] || { echo "empty API response" >&2; exit 1; }

digest="$(python3 - "$TMP" "$OUT" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
out = sys.argv[2]
def money(v): return f"${v:,.0f}"
def line(i, r):
    cm = f"{r['cmRoas']:.2f}" if r.get('cmRoas') is not None else "-"
    return f"| {i} | {r.get('cre') or r.get('sh') or r['title']} | {money(r['spend'])} | {cm} | {money(r['contribution'])} |"
def table(rows):
    head = "| # | creative | spend | cmROAS | contrib |\n|---|---|---|---|---|"
    return "\n".join([head] + [line(i + 1, r) for i, r in enumerate(rows)]) if rows else "_none above floor_"
rg = d['ranges']
md = [f"# CCC Leaderboards — {rg['last7']['to']}", ""]
md += [f"## Top 5 images · last 7 days ({rg['last7']['from']} → {rg['last7']['to']})", table(d['last7']['images']), ""]
md += ["## Top 5 videos · last 7 days", table(d['last7']['videos']), ""]
md += [f"## Top 10 images · last 30 days ({rg['last30']['from']} → {rg['last30']['to']})", table(d['last30']['images']), ""]
md += ["## Top 10 videos · last 30 days", table(d['last30']['videos']), ""]
md += [f"## Quarter leaderboard ({rg['quarter']['from']} → {rg['quarter']['to']})", table(d['quarter']), ""]
open(out, "w").write("\n".join(md))
q = d['quarter'][:3]
print(" / ".join(f"{i+1}. {(r.get('cre') or r.get('sh') or r['title'])} {money(r['contribution'])}" for i, r in enumerate(q)) or "no qualifiers")
PY
)"
echo "wrote $OUT"
if [ -n "$NTFY_TOPIC" ]; then
  curl -s -H "Title: CCC Leaderboards (weekly)" \
    -H "Click: https://tomas-agent-box.tailb74909.ts.net:8443/leaderboards" \
    -d "Quarter top 3: $digest" "https://ntfy.sh/$NTFY_TOPIC" >/dev/null 2>&1 || true
fi
