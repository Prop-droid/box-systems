# Watchdog shared helpers. Sourced by every check script.
# Runner exports RESULTS_FILE before invoking checks.

ok()   { printf 'OK|%s|%s\n'   "$1" "$2" >>"$RESULTS_FILE"; }
warn() { printf 'WARN|%s|%s\n' "$1" "$2" >>"$RESULTS_FILE"; }
fail() { printf 'FAIL|%s|%s\n' "$1" "$2" >>"$RESULTS_FILE"; }

# newest_mtime_epoch <glob...> -> prints epoch of newest matching file, or 0
newest_mtime_epoch() {
  local newest=0 f m
  for f in "$@"; do
    [ -e "$f" ] || continue
    m=$(stat -c %Y "$f" 2>/dev/null || stat -f %m "$f" 2>/dev/null) || continue
    [ "$m" -gt "$newest" ] && newest=$m
  done
  echo "$newest"
}

# age_hours <epoch> -> hours since epoch (rounded down); 999999 if epoch=0
age_hours() {
  local e=$1
  [ "$e" -eq 0 ] && { echo 999999; return; }
  echo $(( ( $(date +%s) - e ) / 3600 ))
}
