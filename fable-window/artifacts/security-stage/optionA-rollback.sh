#!/usr/bin/env bash
# Option A rollback — removes the fw table, restoring the prior no-LAN-firewall state.
# Tailscale's own tables are untouched. Single command: bash optionA-rollback.sh
set -euo pipefail
if sudo nft list table inet fw >/dev/null 2>&1; then
  sudo nft delete table inet fw
  echo "Deleted table inet fw. LAN firewall removed."
else
  echo "No table inet fw present. Nothing to roll back."
fi
