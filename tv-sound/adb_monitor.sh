#!/bin/bash
# Inside-the-TV monitor for the A80L echo debug (systemd unit tv-sound-adb).
# Streams the TV's logcat (HDMI/CEC/eARC/audio routing lines only) to logs/logcat-YYYY-MM-DD.log and,
# whenever a CEC/ARC/audio-system event shows up, appends a `dumpsys hdmi_control` snapshot to logs/hdmi-snap.log.
# Prereq (one-time, on the TV): Settings > System > About > tap "Android TV OS build" 7x -> Developer options ->
# USB debugging ON; then from the box: adb connect 192.168.1.16:5555 and accept "Allow USB debugging" (Always).
TV="${BRAVIA_IP:-192.168.1.16}:5555"
DIR="$(cd "$(dirname "$0")" && pwd)/logs"; mkdir -p "$DIR"
NOISE='ExInputItemManager|ExternalInputRepository|SyncMessenger|TVCallback: callback|metrics_recorder|createTrack_l|notificationFrames|registerEffect|FadeOutManager|\[MEXI\]|HotPlugDetectionAction: Poll|cast_shell.*metrics_stat|V2TraitNotifyService|onCreateTrait|Give Device Power Status|Report Power Status'
FILTER='Hdmi|CEC|Cec|eARC|EARC|eArc|Earc|ARC|SystemAudio|AudioService|AudioPolicy|audio_hw|AudioFlinger|outputTerminal|speaker|Speaker|audio system|BraviaSync|bravia.*sync|tvsettings|com.sony.dtv.*(audio|hdmi)'
while true; do
  adb connect "$TV" >/dev/null 2>&1
  if ! adb -s "$TV" get-state >/dev/null 2>&1; then
    echo "$(date -Is) adb: TV not reachable/authorised" >> "$DIR/adb-monitor.log"; sleep 30; continue
  fi
  echo "$(date -Is) adb: connected $(adb -s "$TV" shell getprop ro.build.display.id 2>/dev/null)" >> "$DIR/adb-monitor.log"
  adb -s "$TV" shell dumpsys hdmi_control > "$DIR/hdmi_control-$(date +%F_%H%M%S).txt" 2>/dev/null
  # -T 1: start from now; one line per event; grep is line-buffered so events land immediately
  # NOISE: our own REST polling shows up as System.out [MEXI] lines; HotPlugDetectionAction polls every 5 s; cast metrics
  adb -s "$TV" logcat -v threadtime -T 1 2>/dev/null | grep --line-buffered -E "$FILTER" | grep --line-buffered -v -E "$NOISE" | while IFS= read -r line; do
    printf '%s\n' "$line" >> "$DIR/logcat-$(date +%F).log"
    if printf '%s' "$line" | grep -q -E 'System Audio Mode|SystemAudio|eARC|EARC|eArc|Initiate ARC|Terminate ARC|Request ARC|Report ARC|communication|setSoundSettings|TV speaker|Set Osd|Active Source|Routing Change|Standby'; then
      now=$(date +%s); if (( now - ${last_snap:-0} > 20 )); then
        { echo "===== $(date -Is) trigger: ${line:0:160}"; adb -s "$TV" shell dumpsys hdmi_control 2>/dev/null | grep -i -E 'arc|system audio|mSystemAudio|eARC|device|logical|power|active' | head -60; } >> "$DIR/hdmi-snap.log"
        last_snap=$now
      fi
    fi
  done
  echo "$(date -Is) adb: logcat stream ended, reconnecting" >> "$DIR/adb-monitor.log"; sleep 10
done
