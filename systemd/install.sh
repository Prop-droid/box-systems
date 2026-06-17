#!/bin/bash
# Install/refresh this suite's systemd USER timers on the box.
#
# The box schedules everything via systemd user timers (NOT launchd, despite the
# Mac-era plist comments in some scripts). These unit files are the source of
# truth for the schedule; the live copies in ~/.config/systemd/user/ are deployed
# from here. Units use %h so they are host-portable, but their ExecStart paths
# assume the suite is deployed at ~/sha-systems.
#
# Workflow: edit a unit here -> run this script -> done. Idempotent.
#   bash systemd/install.sh
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.config/systemd/user"
mkdir -p "$DEST"

cp -v "$SRC"/*.service "$SRC"/*.timer "$DEST"/
systemctl --user daemon-reload

for t in "$SRC"/*.timer; do
  systemctl --user enable --now "$(basename "$t")"
done

echo "--- active timers for this suite ---"
systemctl --user list-timers --all
