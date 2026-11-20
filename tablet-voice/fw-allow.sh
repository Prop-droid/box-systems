#!/bin/bash
# Re-adds the live box-firewall rule that lets the wall tablet reach tablet-voice (tcp 8766).
# Why: /etc/nftables.d/box-fw.nft is root-owned (editing it needs Tomas's password) and admits the
# tablet only on tcp 8765. sudoers gives tomas NOPASSWD /usr/sbin/nft, so the 8766 rule lives in the
# live ruleset (added 2026-11-04) and this re-adds it after a box reboot or a box-firewall reload.
# No-op once box-fw.nft itself carries 8766 (staged: ~/personal/tablet-upgrade/backups/voice/box-fw.nft.new).
# Called as ExecStartPre=- by tablet-voice.service and tablet-voice-micaudit.service.
set -u
NFT="sudo -n /usr/sbin/nft"
rules=$($NFT -a list chain inet fw input 2>&1) || { echo "fw-allow: no inet fw input chain, nothing to do ($rules)"; exit 0; }
printf '%s\n' "$rules" | grep -Eq 'ip saddr 192\.168\.1\.89 tcp dport (8766|\{[^}]*8766[^}]*\}) accept' && exit 0
h=$(printf '%s\n' "$rules" | sed -n 's/.*ip saddr 192\.168\.1\.89 tcp dport 8765 accept.*# handle \([0-9][0-9]*\)$/\1/p' | head -1)
if $NFT add rule inet fw input ${h:+position "$h"} ip saddr 192.168.1.89 tcp dport 8766 accept comment '"tablet-voice"'; then
  echo "fw-allow: re-added tablet 192.168.1.89 -> tcp 8766${h:+ after handle $h}"
else
  echo "fw-allow: FAILED to add the tcp 8766 rule"; exit 1
fi
