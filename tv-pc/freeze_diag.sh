#!/bin/bash
# Freeze diagnostic for tv-pc, run as root over Tailscale SSH. Read-only.
echo "== now: $(date) | kernel $(uname -r)"
echo "== boots"; journalctl --list-boots --no-pager | tail -4
echo "== deployment"; rpm-ostree status 2>/dev/null | sed -n 1,10p
echo "== last 60 lines of frozen boot (-1)"; journalctl -b -1 -n 60 --no-pager -o short-iso-precise | cut -c1-280
echo "== kernel warnings+ (frozen boot)"; journalctl -b -1 -k -p warning --no-pager -o short-iso | cut -c1-280 | tail -60
echo "== kernel grep gpu/hang/mce/thermal/link (frozen boot)"; journalctl -b -1 -k --no-pager -o short-iso | grep -iE "amdgpu|drm|ring |timeout|gpu reset|hang|mce|machine check|hardware error|thermal|throttl|ctf|lockup|watchdog|rcu|BUG|Oops|panic|aer|pcie bus error|nvme|hdmi|frl|dmub|link train" | cut -c1-280 | tail -80
echo "== user-session warnings (frozen boot)"; journalctl -b -1 _UID=1000 -p warning --no-pager -o short-iso | cut -c1-280 | tail -40
echo "== gamescope (frozen boot)"; journalctl -b -1 --no-pager -o short-iso | grep -i gamescope | cut -c1-280 | tail -30
echo "== pstore"; ls -la /sys/fs/pstore /var/lib/systemd/pstore 2>&1 | head -20
echo "== coredumps today"; coredumpctl list --since today --no-pager 2>&1 | tail -15
echo "== steam gameprocess tail"; tail -n 15 /var/home/tomas/.local/share/Steam/logs/gameprocess_log.txt 2>/dev/null | cut -c1-220
echo "== last -x"; last -x -n 8 2>/dev/null
echo "== RAM"; dmidecode -t memory 2>/dev/null | grep -E "Configured Memory Speed|^\s+Size" | sort | uniq -c
echo "== temps now"; sensors 2>/dev/null | grep -E "Package|edge|junction|mem|PPT|fan[0-9]" | head -20
echo "== nvme"; (command -v nvme >/dev/null && nvme smart-log /dev/nvme0 | grep -E "critical_warning|temperature|media_errors|num_err_log|unsafe_shutdowns") 2>&1 | head
echo "== cmdline"; cat /proc/cmdline
