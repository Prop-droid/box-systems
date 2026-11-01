#!/bin/bash
# Fosi Audio ZD3 (XMOS XU316, Thesycon VID) firmware check / DFU flash from Linux. Run as root on the machine the ZD3 is USB-connected to.
#   zd3_flash.sh            -> dry run: show device, current firmware (bcdDevice), DFU capability
#   zd3_flash.sh --flash    -> write the 1.0.8 upgrade image via dfu-util, then show the new version
# DEPRECATED 2026-10-31: dfu-util DETACH+reset loses the ZD3 (dfu-util ticket #65, reproduced twice; mains power-cycle needed). Use zd3_flash_xmos.sh (xmosdfu). Factory image stays untouched on the device.
set -u
VID=152a; PID=889b
BIN="${ZD3_BIN:-/var/home/tomas/Downloads/fosi-zd3/update_zd3_1.0.8_spdif_noise_fix.bin}"
SHA_EXPECTED="b8498ca4d47f20dd"
DFU="$(command -v dfu-util || ls /home/linuxbrew/.linuxbrew/bin/dfu-util 2>/dev/null || true)"
[ -n "$DFU" ] || { echo "dfu-util not installed"; exit 2; }
echo "== ZD3 on USB?"
if ! lsusb -d $VID:$PID; then echo "NOT FOUND: check ZD3 input = USB, USB-B cable to a rear port (no hub), ZD3 powered"; exit 1; fi
echo "== descriptors (bcdDevice = firmware revision):"
lsusb -v -d $VID:$PID 2>/dev/null | grep -E "bcdDevice|iManufacturer|iProduct|bInterfaceClass +254|bInterfaceSubClass +1 |Device Firmware Upgrade|bcdDFUVersion|wTransferSize|bitWillDetach|bitCanDnload|bmAttributes +0x0" | sed 's/^ *//' | head -n 20
echo "== dfu-util -l:"
"$DFU" -l 2>&1 | grep -i -E "found|$VID" || echo "(dfu-util sees no DFU interface on the ZD3 -> fall back to xmosdfu)"
if [ "${1:-}" != "--flash" ]; then echo "== dry run only (add --flash to write 1.0.8)"; exit 0; fi
echo "== NOTE: ZD3 must be powered ON (not standby) and on the USB input before flashing; attempts 1+2 (09:11 and 09:22 EET, standby and awake) rebooted it into DFU mode and it never re-attached - use zd3_flash_xmos.sh"
echo "== image: $BIN"
[ -s "$BIN" ] || { echo "image missing"; exit 2; }
S=$(sha256sum "$BIN" | cut -c1-16); [ "$S" = "$SHA_EXPECTED" ] || { echo "sha256 mismatch ($S != $SHA_EXPECTED) - refusing"; exit 2; }
echo "== flashing (detach -> DFU mode -> download -> reset):"
"$DFU" --detach-delay 10 -d "$VID:$PID,$VID:*" -D "$BIN" -R 2>&1 | grep -v -E "^$|Copyright|License|free software|ABSOLUTELY NO WARRANTY|dfu-util.sourceforge|Please report" | tail -n 25
echo "== waiting for the ZD3 to come back..."
for i in $(seq 1 15); do sleep 2; lsusb -d $VID:$PID >/dev/null 2>&1 && break; done
echo "== ZD3 after:"
lsusb -v -d $VID:$PID 2>/dev/null | grep -E "bcdDevice" | sed 's/^ *//' || echo "ZD3 not re-enumerated yet - power-cycle it and run the dry run again"
echo "== any DFU-mode/XMOS device visible (any VID):"
"$DFU" -l 2>&1 | grep -i found || echo "(none)"
lsusb | grep -iE "152a|20b1|xmos" || true
