#!/usr/bin/env bash
# zd3_flash_xmos.sh - flash the Fosi Audio ZD3 (XMOS XU316) with the XMOS-native DFU flow via xmosdfu
# (vendor request RESETINTODFU 0xf2 -> device reboots into DFU mode -> DFU_DNLOAD 64 B blocks -> RESETFROMDFU 0xf3).
# Why not dfu-util: its standard DFU_DETACH + host USB reset loses XMOS lib_xua devices (dfu-util ticket #65);
# reproduced twice on 2026-10-31 - the ZD3 vanished from USB and needed a mains power-cycle each time.
# Usage:  zd3_flash_xmos.sh           -> dry run (device present, version, what xmosdfu sees)
#         zd3_flash_xmos.sh --flash   -> unbind snd-usb-audio from the ZD3, xmosdfu --download 1.0.8, re-read version
# Fosi prerequisites: ZD3 powered ON, input = USB, USB-B cable to the PC. After success: unplug USB, power ZD3 off/on.
set -u
VID=152a; PID=889b
BIN="${ZD3_BIN:-/var/home/tomas/Downloads/fosi-zd3/update_zd3_1.0.8_spdif_noise_fix.bin}"
SHA_EXPECTED="b8498ca4d47f20dd"
XMOSDFU="${XMOSDFU:-/var/home/tomas/Downloads/fosi-zd3/tools/xmos_dfu/xmos_dfu/xmosdfu}"
echo "== ZD3 on USB?"
lsusb -d $VID:$PID || { echo "NOT FOUND: ZD3 must be ON, input USB, USB-B cable in. If a DFU attempt just failed: mains power-cycle the ZD3."; exit 1; }
echo "== version (bcdDevice):"; lsusb -v -d $VID:$PID 2>/dev/null | grep -E "bcdDevice" | sed 's/^ *//'
echo "== xmosdfu sees:"; "$XMOSDFU" --listdevices 2>&1 | grep -E "VID|Firmware|Interface" | head -4
[ "${1:-}" = "--flash" ] || { echo "== dry run only (add --flash to write 1.0.8)"; exit 0; }
[ -s "$BIN" ] || { echo "image missing: $BIN"; exit 2; }
S=$(sha256sum "$BIN" | cut -c1-16); [ "$S" = "$SHA_EXPECTED" ] || { echo "sha256 mismatch ($S != $SHA_EXPECTED) - refusing"; exit 2; }
echo "== detaching snd-usb-audio from the ZD3 (keeps PipeWire off it during DFU):"
DEVDIR=$(dirname "$(grep -l "^$PID" /sys/bus/usb/devices/*/idProduct 2>/dev/null | head -1)")
DEVN=$(basename "$DEVDIR")
for i in "$DEVDIR"/"$DEVN":*; do
  drv=$(basename "$(readlink -f "$i/driver" 2>/dev/null)" 2>/dev/null)
  if [ "$drv" = "snd-usb-audio" ]; then echo "$(basename "$i")" > /sys/bus/usb/drivers/snd-usb-audio/unbind && echo "   unbound $(basename "$i")"; fi
done
echo "== $(date +%H:%M:%S) xmosdfu --download (RESETINTODFU -> poll for DFU-mode device -> download -> RESETFROMDFU):"
"$XMOSDFU" --download "$BIN" 2>&1 | tr '\r' '\n' | grep -vE "^\s*$" | tail -n 25
echo "== $(date +%H:%M:%S) waiting for the ZD3 to come back in application mode..."
for i in $(seq 1 20); do sleep 2; lsusb -d $VID:$PID >/dev/null 2>&1 && break; done
echo "== ZD3 after:"
lsusb -d $VID: || echo "(no $VID device on the bus)"
lsusb -v -d $VID:$PID 2>/dev/null | grep -E "bcdDevice" | sed 's/^ *//' || echo "not back yet - if still absent after 1 min: mains power-cycle the ZD3"
"$XMOSDFU" --listdevices 2>&1 | grep -E "Firmware" | head -2
echo "== Fosi step 11: unplug the USB cable from the ZD3, then power it off and on."
