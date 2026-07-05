#!/usr/bin/env bash
# Option A apply — loads the LAN default-drop ruleset LIVE (not persisted across reboot).
# Single command: bash optionA-apply.sh
set -euo pipefail
NFT="$(dirname "$(readlink -f "$0")")/optionA.nft"

echo "Loading $NFT ..."
sudo nft -f "$NFT"

echo
echo "Active fw table:"
sudo nft list table inet fw

echo
echo "Quick reachability check (LAN bind should now be filtered for app ports):"
echo "  from another LAN host:  curl -m3 http://192.168.0.107:8092/   # should hang/refuse"
echo "  from this box:          curl -m3 http://127.0.0.1:8092/        # should still 200"
echo
echo "NOT persisted across reboot. To persist, add an nftables include or a systemd"
echo "unit that runs 'nft -f $NFT' at boot (left for you to opt into; no unit staged)."
echo "Rollback: bash optionA-rollback.sh"
