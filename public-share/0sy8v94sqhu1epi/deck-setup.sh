#!/usr/bin/env bash
# deck-setup.sh — Claude Code + remote access on Steam Deck (SteamOS).
# Run ONCE in Desktop mode → Konsole, as user deck:  bash deck-setup.sh
# Everything lands in /home (survives SteamOS updates); tailscale uses the
# official deck-tailscale script (self-persists via atomic-update.conf.d).
set -u
BOX_PUBKEY='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKVlFMTJew73y1GCY6WqLx8od+WLiwTI+6cxQraeGOvq box->deck'
step(){ printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
[ "$(id -un)" = deck ] || { echo "run as user deck"; exit 1; }
mkdir -p ~/.local/bin

step "1/7 sudo password"
if ! sudo -n true 2>/dev/null; then
  if [ "$(passwd -S 2>/dev/null | awk '{print $2}')" = "NP" ]; then
    echo "No password set for 'deck' yet — choose one now (needed for sudo)."
    passwd
  fi
  sudo -v || { echo "sudo failed"; exit 1; }
fi

step "2/7 sshd + box key"
sudo systemctl enable --now sshd
mkdir -p ~/.ssh && chmod 700 ~/.ssh
grep -qF "$BOX_PUBKEY" ~/.ssh/authorized_keys 2>/dev/null || echo "$BOX_PUBKEY" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

step "3/7 Tailscale (official deck-tailscale installer)"
if [ ! -x /opt/tailscale/tailscale ]; then
  curl -fsSL https://raw.githubusercontent.com/tailscale-dev/deck-tailscale/main/tailscale.sh -o /tmp/deck-tailscale.sh
  sudo bash /tmp/deck-tailscale.sh
fi
sudo systemctl enable --now tailscaled
echo "If a login URL appears below, open it in the Deck browser and approve."
sudo /opt/tailscale/tailscale up --operator=deck --hostname=steamdeck

step "4/7 Claude Code (native install → ~/.local/bin/claude)"
if [ ! -x ~/.local/bin/claude ]; then
  curl -fsSL https://claude.ai/install.sh | bash
fi

step "5/7 tmux"
if ! command -v tmux >/dev/null 2>&1 && [ ! -x ~/.local/bin/tmux ]; then
  curl -fsSL -o ~/.local/bin/tmux.appimage https://github.com/nelsonenzo/tmux-appimage/releases/latest/download/tmux.appimage
  chmod +x ~/.local/bin/tmux.appimage
  if ~/.local/bin/tmux.appimage -V >/dev/null 2>&1; then
    ln -sf tmux.appimage ~/.local/bin/tmux
  else  # no FUSE → extract once
    (cd ~/.local && ./bin/tmux.appimage --appimage-extract >/dev/null && rm -rf tmux-app && mv squashfs-root tmux-app)
    ln -sf ../tmux-app/AppRun ~/.local/bin/tmux
  fi
fi

step "6/7 shell helpers (cl / cln)"
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

step "7/7 status"
echo "tailscale: $(sudo /opt/tailscale/tailscale ip -4 2>/dev/null || echo '?')"
echo "sshd:      $(systemctl is-active sshd)"
echo "claude:    $(~/.local/bin/claude --version 2>/dev/null || echo missing)"
echo "tmux:      $(tmux -V 2>/dev/null || echo missing)"
cat <<'MSG'

NEXT (on the Deck):
  1. Reopen Konsole (or: source ~/.bashrc)
  2. claude        → log in with your Claude subscription (browser opens); then exit
  3. cln           → new Remote-Control session; pick it up in the Claude app → Code tab
Power: Desktop mode → Settings → Power Management → never sleep on AC, else sessions die on suspend.
MSG
