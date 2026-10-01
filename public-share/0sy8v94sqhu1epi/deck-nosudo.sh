#!/usr/bin/env bash
# deck-nosudo.sh — finish Claude Code remote setup on Steam Deck WITHOUT sudo (tmux + cl/cln helpers).
set -u
mkdir -p ~/.local/bin
if ! command -v tmux >/dev/null 2>&1 && [ ! -x ~/.local/bin/tmux ]; then
  curl -fsSL -o ~/.local/bin/tmux.appimage https://github.com/nelsonenzo/tmux-appimage/releases/latest/download/tmux.appimage
  chmod +x ~/.local/bin/tmux.appimage
  if ~/.local/bin/tmux.appimage -V >/dev/null 2>&1; then
    ln -sf tmux.appimage ~/.local/bin/tmux
  else
    (cd ~/.local && ./bin/tmux.appimage --appimage-extract >/dev/null && rm -rf tmux-app && mv squashfs-root tmux-app)
    ln -sf ../tmux-app/AppRun ~/.local/bin/tmux
  fi
fi
if ! grep -q 'deck-setup' ~/.bashrc 2>/dev/null; then
cat >> ~/.bashrc <<'BRC'
# --- claude remote (deck-setup) ---
export PATH="$HOME/.local/bin:$PATH"
alias cl='tmux new -A -s claude'
# cln [name] [dir] → fresh Claude session in tmux with Remote Control (shows in the Claude app)
cln() { local name="${1:-c$(date +%H%M)}"; local dir="${2:-$HOME}"; tmux new -A -s "$name" -c "$dir" "claude --dangerously-skip-permissions --remote-control $name"; }
BRC
fi
export PATH="$HOME/.local/bin:$PATH"
echo "claude: $(claude --version 2>/dev/null || echo missing)"
echo "tmux:   $(tmux -V 2>/dev/null || echo missing)"
echo "helpers: $(grep -c deck-setup ~/.bashrc) (cl / cln in ~/.bashrc)"
echo "DONE. Open a new Konsole (or: source ~/.bashrc), then: cln"
