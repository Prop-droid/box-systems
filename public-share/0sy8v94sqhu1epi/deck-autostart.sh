#!/usr/bin/env bash
# deck-autostart.sh — user-level systemd unit that starts a Claude Remote Control session
# in tmux (session "claude") on every Deck boot. No sudo. Lives in /home → survives updates.
set -u
export PATH="$HOME/.local/bin:$PATH"
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/claude-remote.service <<'UNIT'
[Unit]
Description=Claude Code Remote Control session (tmux: claude)

[Service]
Type=oneshot
RemainAfterExit=yes
Environment=PATH=%h/.local/bin:/usr/local/bin:/usr/bin:/bin
TimeoutStartSec=600
# wait for network before launching, so remote-control registers cleanly
ExecStartPre=/bin/sh -c 'until curl -fsI https://claude.ai >/dev/null 2>&1; do sleep 3; done'
ExecStart=%h/.local/bin/tmux new -d -s claude -c %h "%h/.local/bin/claude --dangerously-skip-permissions --remote-control deck; exec bash -l"
ExecStop=-%h/.local/bin/tmux kill-session -t claude

[Install]
WantedBy=default.target
UNIT
systemctl --user daemon-reload
systemctl --user enable claude-remote.service
systemctl --user restart claude-remote.service
sleep 8
echo "unit:  $(systemctl --user is-enabled claude-remote.service) / $(systemctl --user is-active claude-remote.service)"
echo "tmux:  $(tmux ls 2>/dev/null || echo 'no sessions')"
echo "DONE. Session 'claude' now auto-starts at boot; attach locally with: cl"
