#!/usr/bin/env bash
# zd3_resets.sh - count ZD3 self-drops (Set System Audio Mode OFF sent by CEC addr 5 with no TV
# <Standby>/<Request ARC Termination> in the preceding 10 s) across logs/logcat-*.log.
# Use: before/after comparison for the ZD3 fw 1.0.8 flash (baseline 2026-10-31: 1 in 25.5 h).
# Events inside MAINT windows are hands-on work (cable plugs, power-cycles) and are labelled
# "maintenance", not counted. Format: "YYYY-MM-DD HH:MM:SS HH:MM:SS" (local time of the TV log).
set -euo pipefail
MAINT=(
  "2026-10-31 09:00:00 09:45:00"  # fw 1.0.8 flash session: USB plug-in 09:01, mains power-cycles 09:26, step-11 power-cycle 09:39
)
cd "$(dirname "$0")/logs"
for f in logcat-*.log; do
  day=$(echo "$f" | sed -E 's/logcat-([0-9]{4}-[0-9]{2}-[0-9]{2})\.log/\1/')
  year=${day%%-*}
  win=""
  for m in "${MAINT[@]}"; do
    set -- $m
    [[ $1 == "$day" ]] && win+="$2-$3;"
  done
  awk -v Y="$year" -v F="$f" -v W="$win" '
    function secs(d, t,   a, b) { split(d, a, "-"); split(t, b, ":"); return a[2]*86400 + b[1]*3600 + b[2]*60 + b[3] }
    function in_maint(hms,   n, i, p) {
      n = split(W, w, ";")
      for (i = 1; i <= n; i++) if (w[i] != "") { split(w[i], p, "-"); if (hms >= p[1] && hms <= p[2]) return 1 }
      return 0
    }
    /\[S\]:<Standby>|\[S\]:<Request ARC Termination>/ { lastTV = secs($1, $2) }
    /\[R\]:<Set System Audio Mode> 5F:72:00/ {
      t = secs($1, $2); hms = substr($2, 1, 8)
      kind = (lastTV && t - lastTV <= 10) ? "tv-standby" : (in_maint(hms) ? "maintenance" : "SELF-DROP")
      printf "%s %s-%s %s %s\n", kind, Y, $1, hms, F
    }' "$f"
done | sort -k2 | tee /dev/stderr | awk '$1=="SELF-DROP"{n++; d[substr($2,1,10)]++} END{printf "\nZD3 self-drops total: %d\n", n+0; for (k in d) printf "  %s: %d\n", k, d[k]}' 2>/dev/null
