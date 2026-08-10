#!/bin/bash
# Re-open the Google Assistant Voice Match enrollment on the P11 Pro.
# Run when Tomas is standing at the tablet; he then follows the on-screen
# prompts (say "Hey/Ok Google" 4x). Restore dashboard after: tablet-dash-restore below.
TAB="${TAB:-192.168.0.160:5555}"
adb connect "${TAB%:*}:5555" >/dev/null
adb -s "$TAB" shell "input keyevent KEYCODE_WAKEUP; sleep 1; wm dismiss-keyguard; sleep 1; am start -a com.google.android.googlequicksearchbox.action.ASSISTANT_SETTINGS"
sleep 6
adb -s "$TAB" shell "input tap 252 440"   # "Voice Match" (first item in Popular settings)
echo "Voice Match screen open on tablet. After enrollment finishes, restore the dashboard with:"
echo "  adb -s $TAB shell 'am force-stop de.ozerov.fully; monkey -p de.ozerov.fully -c android.intent.category.LAUNCHER 1'"
