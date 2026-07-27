#!/bin/bash
# Keep the Pixel reachable over Tailscale + heal the Claude assistant role after app updates.
PH=100.64.31.118:5555
ADB=/usr/bin/adb
$ADB connect "$PH" >/dev/null 2>&1
# only proceed if the device is actually reachable/authorized
$ADB -s "$PH" get-state 2>/dev/null | grep -q device || exit 0
# assistant auto-heal: if Gemini reclaimed the role (Claude app update), reassert Claude
H=$($ADB -s "$PH" shell cmd role get-role-holders android.app.role.ASSISTANT 2>/dev/null | tr -d "\r")
if ! echo "$H" | grep -q anthropic; then
  $ADB -s "$PH" shell cmd role add-role-holder android.app.role.ASSISTANT com.anthropic.claude >/dev/null 2>&1
  logger -t pixel-watchdog "re-asserted Claude assistant role (was: $H)"
fi
