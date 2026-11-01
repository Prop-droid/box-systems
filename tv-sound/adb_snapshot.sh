#!/bin/bash
# One-shot inside-the-TV state dump: firmware, HDMI-CEC/ARC/eARC state, audio routing, CEC settings.
TV="${BRAVIA_IP:-192.168.1.16}:5555"; adb connect "$TV" >/dev/null 2>&1 || true
A() { adb -s "$TV" shell "$@" 2>&1; }
echo "## build:  $(A getprop ro.build.display.id)  | model $(A getprop ro.product.model) | android $(A getprop ro.build.version.release)"
echo "## CEC settings (global):"; for k in hdmi_control_enabled hdmi_system_audio_control_enabled hdmi_control_auto_device_off_enabled hdmi_control_auto_wakeup_enabled; do echo "  $k = $(A settings get global $k)"; done
echo "## dumpsys hdmi_control (ARC/eARC/System Audio Mode):"; A dumpsys hdmi_control | grep -i -E 'arc|system audio|mSystemAudio|eARC|earc|logical|mDevice|Speaker|power|active|address|vendor' | head -80
echo "## audio routing:"; A dumpsys audio | grep -i -E 'hdmi|arc|speaker|device|routing|force' | head -40
echo "## active output devices:"; A dumpsys media.audio_policy | grep -i -E 'output|device|hdmi|speaker|arc' | head -40
