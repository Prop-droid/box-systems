#!/usr/bin/env bash
# tests/fake_adb.sh: a stand-in for adb for the off-line mic audit tests (never talks to a device).
# It runs the device command string that mic_audit.sh sends, locally, with `dumpsys` defined as a function that
# prints realistic Android 11 dumps built from FAKEADB_* variables, so the audit's own grep and sed pipeline
# and its parser are what get tested:
#   FAKEADB_TOP      fully | screensaver | other | none   (the resumed activity)
#   FAKEADB_AWAKE    Awake | Asleep | Dozing
#   FAKEADB_REC      number of Fully recording clients inside the RecordActivityMonitor section
#   FAKEADB_OTHER    1 adds an active recorder of another app (never counted)
#   FAKEADB_NOHEADER 1 = dumpsys audio without the RecordActivityMonitor section (a format change)
#   FAKEADB_DOWN     1 = the device does not answer
#   FAKEADB_WV, FAKEADB_FV   versionName of the WebView and of Fully
#   FAKEADB_SEQ      a file of "TOP AWAKE REC" lines; each snapshot call takes the next line (confirm reads)
#   FAKEADB_LOG      every call is appended here
set -uo pipefail
[ -n "${FAKEADB_LOG:-}" ] && printf '%s\n' "$*" >> "$FAKEADB_LOG"
if [ "${1:-}" = connect ]; then
  [ "${FAKEADB_DOWN:-0}" = 1 ] && { echo "failed to connect to ${2:-}"; exit 1; }
  echo "already connected to ${2:-}"; exit 0
fi
[ "${1:-}" = -s ] && shift 2
[ "${1:-}" = shell ] || { echo "fake_adb: unsupported: $*" >&2; exit 2; }
shift
[ "${FAKEADB_DOWN:-0}" = 1 ] && { echo "error: device offline" >&2; exit 1; }
cmd="$*"

top="${FAKEADB_TOP:-fully}" awake="${FAKEADB_AWAKE:-Awake}" rec="${FAKEADB_REC:-0}"
if [ -n "${FAKEADB_SEQ:-}" ] && [ -s "$FAKEADB_SEQ" ] && [[ "$cmd" == *"dumpsys audio"* ]]; then
  read -r top awake rec < "$FAKEADB_SEQ"
  tail -n +2 "$FAKEADB_SEQ" > "$FAKEADB_SEQ.next" && mv -f "$FAKEADB_SEQ.next" "$FAKEADB_SEQ"
fi
export top awake rec

dumpsys() {
  case "$1" in
    activity)
      echo "ACTIVITY MANAGER ACTIVITIES (dumpsys activity activities)"
      echo "Display #0 (activities from top to bottom):"
      case "$top" in
        screensaver)
          echo "  Stack #18: type=standard mode=fullscreen"
          echo "    mResumedActivity: ActivityRecord{d4e5f6 u0 de.ozerov.fully/.ScreensaverActivity t18}"
          echo "  Stack #17: type=standard mode=fullscreen"
          echo "    mLastPausedActivity: ActivityRecord{a1b2c3 u0 de.ozerov.fully/.FullyActivity t17}"
          echo " ResumedActivity:ActivityRecord{d4e5f6 u0 de.ozerov.fully/.ScreensaverActivity t18}" ;;
        other)
          echo "  Stack #20: type=standard mode=fullscreen"
          echo "    mResumedActivity: ActivityRecord{0a0b0c u0 com.google.android.calendar/com.android.calendar.AllInOneActivity t20}"
          echo "  Stack #17: type=standard mode=fullscreen"
          echo "    mLastPausedActivity: ActivityRecord{a1b2c3 u0 de.ozerov.fully/.FullyActivity t17}"
          echo " ResumedActivity:ActivityRecord{0a0b0c u0 com.google.android.calendar/com.android.calendar.AllInOneActivity t20}" ;;
        fully)
          echo "  Stack #17: type=standard mode=fullscreen"
          echo "    mResumedActivity: ActivityRecord{a1b2c3 u0 de.ozerov.fully/.FullyActivity t17}"
          echo " ResumedActivity:ActivityRecord{a1b2c3 u0 de.ozerov.fully/.FullyActivity t17}" ;;
        *)
          echo "  Stack #17: type=standard mode=fullscreen"
          echo "    mLastPausedActivity: ActivityRecord{a1b2c3 u0 de.ozerov.fully/.FullyActivity t17}" ;;
      esac ;;
    power)
      echo "POWER MANAGER (dumpsys power)"
      echo "Power Manager State:"
      echo "  mDirty=0x0"
      echo "  mWakefulness=$awake"
      echo "  mWakefulnessChanging=false" ;;
    audio)
      echo "Audio event log: phone state (logged after successful call to AudioService.setMode())"
      echo "11-02 09:00:01:000 setMode(MODE_NORMAL) from package=de.ozerov.fully pid=4992"
      echo
      if [ "${FAKEADB_NOHEADER:-0}" != 1 ]; then
        echo "RecordActivityMonitor dump time: 5:40:12 PM"
        local i
        for ((i = 0; i < rec; i++)); do
          echo "riid $((4 + i)); active true"
          echo "  session:$((6537 + i)) -- source client=MIC -- uid:10312 -- patch:142 -- pack:de.ozerov.fully -- format client=AudioFormat: 16000Hz"
        done
        if [ "${FAKEADB_OTHER:-0}" = 1 ]; then
          echo "riid 9; active true"
          echo "  session:6600 -- source client=VOICE_RECOGNITION -- uid:10123 -- patch:150 -- pack:com.google.android.googlequicksearchbox -- format client=AudioFormat: 16000Hz"
        fi
        echo
        echo
      fi
      echo "Audio event log: recording activity received by AudioService"
      echo "11-02 13:12:03:420 rec start riid:3 uid:10312 session:6521 src:MIC pack:de.ozerov.fully"
      echo "11-02 13:12:08:101 rec stop riid:3 uid:10312 session:6521 src:MIC pack:de.ozerov.fully"
      echo
      echo "PlaybackActivityMonitor dump time: 5:40:12 PM"
      echo "  ID:31 -- type:android.media.MediaPlayer -- u/pid:10312/4992 -- state:idle -- pack:de.ozerov.fully" ;;
    package)
      case "$2" in
        com.google.android.webview)
          echo "Packages:"
          echo "  Package [com.google.android.webview] (3c2a1b):"
          echo "    versionCode=807804733 minSdk=29 targetSdk=36"
          echo "    versionName=${FAKEADB_WV:-156.0.8078.47}"
          echo "  Hidden system packages:"
          echo "    versionName=90.0.4430.210" ;;
        de.ozerov.fully)
          echo "Packages:"
          echo "  Package [de.ozerov.fully] (5d6e7f):"
          echo "    versionName=${FAKEADB_FV:-1.60.1}" ;;
      esac ;;
  esac
}
export -f dumpsys
bash -c "$cmd"
