#!/usr/bin/env bash
# Installs/updates the LAN firewall. Run after editing box-fw.nft.
set -euo pipefail
d="$(dirname "$(readlink -f "$0")")"
sudo mkdir -p /etc/nftables.d
sudo install -m 644 "$d/box-fw.nft" /etc/nftables.d/box-fw.nft
sudo install -m 644 "$d/box-firewall.service" /etc/systemd/system/box-firewall.service
sudo systemctl daemon-reload
sudo systemctl enable --now box-firewall.service
sudo systemctl reload box-firewall.service
sudo /usr/sbin/nft list table inet fw
