#!/usr/bin/env bash
# tv_speaker_unmutes.sh - symptom-level detector: every episode where the Sony A80L audio HAL
# unmuted its own speakers (`audio_hal: speaker mute = 0`) while logging, with the nearest cause:
#   zd3-drop        <Set System Audio Mode> OFF from the ZD3 (addr 5) within 3 s before  (the 00:49 echo)
#   voice-search    Google TV mic session (katniss ARCProvider) within 5 s before          (seen 10:35, no CEC involved)
#   speaker-setting TV "Speaker setting changed to TV Speaker" within 3 s before
#   tv-standby      TV <Standby> within 15 s before
#   UNKNOWN         none of the above -> new mechanism, read the raw log around it
# Duration is a floor: start to the last unmute line of the episode (episodes collapse within 30 s).
set -euo pipefail
cd "$(dirname "$0")/logs"
for f in logcat-*.log; do
  year=$(echo "$f" | sed -E 's/logcat-([0-9]{4})-.*/\1/')
  awk -v Y="$year" -v F="$f" '
    function secs(t,   b) { split(t, b, ":"); return b[1]*3600 + b[2]*60 + b[3] }
    function flush() { if (start != "") printf "%-15s %s-%s %s  >=%.1fs  %s\n", kind, Y, d0, substr(start,1,8), lastU-startS, F; start = "" }
    /\[R\]:<Set System Audio Mode> 5F:72:00/        { sam = secs($2) }
    /katniss_search_ARCProvider: #audio# activating/ { mic = secs($2) }
    /Speaker setting changed to TV Speaker/          { spk = secs($2) }
    /\[S\]:<Standby>/                                 { stb = secs($2) }
    /speaker mute = 0/ {
      t = secs($2)
      if (start == "" || t - lastU > 30) {
        flush(); start = $2; startS = t; d0 = $1
        kind = (sam && t-sam <= 3) ? "zd3-drop" : (mic && t-mic <= 5) ? "voice-search" : (spk && t-spk <= 3) ? "speaker-setting" : (stb && t-stb <= 15) ? "tv-standby" : "UNKNOWN"
      }
      lastU = t
    }
    END { flush() }' "$f"
done | sort -k2
