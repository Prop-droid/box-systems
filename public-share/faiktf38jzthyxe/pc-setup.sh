#!/usr/bin/env bash
# pc-setup.sh: Tailscale + SSH + Claude Code (Remote Control) on the Bazzite TV PC.
# Run as your normal user (NOT sudo), either way:
#   USB stick: open the stick in Dolphin → right-click empty space → Open Terminal Here → bash pc-setup.sh
#   Online:    bash <(curl -fsSL https://tomas-agent-box.tailb74909.ts.net:8443/pc/faiktf38jzthyxe/pc-setup.sh)
# Idempotent: safe to rerun. Bazzite-safe: no rpm-ostree/dnf layering, no reboot needed;
# user files live in /var/home, system bits are /etc drop-ins (both survive image updates).
set -u
# Launched without a terminal (double-click) → reopen in Konsole so the prompts are visible
if [ ! -t 0 ] && [ -z "${PCSETUP_IN_TERM:-}" ] && command -v konsole >/dev/null 2>&1; then
  exec env PCSETUP_IN_TERM=1 konsole --hold -e bash "$(readlink -f "$0")"
fi
# Log everything next to the script (on the stick) so a failed run can be diagnosed
if [ -f "$0" ] && [ -w "$(dirname "$(readlink -f "$0")")" ]; then LOG_DIR=$(dirname "$(readlink -f "$0")"); else LOG_DIR=$HOME; fi
exec 3>&1 4>&2
exec > >(tee -a "$LOG_DIR/pc-setup.log") 2>&1
trap 'echo "!! FAILED (line $LINENO): $BASH_COMMAND"' ERR
echo "=== pc-setup $(date '+%F %T') · $(. /etc/os-release; echo "$PRETTY_NAME") · user=$USER"
HOSTNAME_TS=tv-pc
BOX_KEY='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIJsQVwHZFjUYMyyr2Lc7xurFC6nDgUow3rdeTTZLQf+ box->tv-pc'
MAC_KEY='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINGSrc6idWjfg/GRO/fTU2DxWdWqaFdBx5pR6yGh7qcd mac-to-tablet'
PHONE_KEY='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIC5YEhGwNcwm90loVlpO/pLjOlpD0BT0DrUxLAANuYOg pixel-box-termius'
step(){ printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
[ "$(id -u)" -ne 0 ] || { echo "Run as your normal user, not root/sudo."; exit 1; }
mkdir -p ~/.local/bin ~/.ssh && chmod 700 ~/.ssh
export PATH="$HOME/.local/bin:$PATH"

step "1/8 sudo (enter your PC password once)"
sudo -v || { echo "sudo failed"; exit 1; }

step "2/8 Tailscale → joins your tailnet as '$HOSTNAME_TS'"
command -v tailscale >/dev/null || { echo "Tailscale missing: run 'ujust enable-tailscale', then rerun this."; exit 1; }
sudo systemctl enable --now tailscaled
for _ in $(seq 20); do sudo tailscale status --json >/dev/null 2>&1 && break; sleep 1; done
if tailscale status >/dev/null 2>&1; then
  sudo tailscale set --operator="$USER" --hostname="$HOSTNAME_TS"
else
  echo "A login URL will appear: open it, sign in with the SAME account as the box (Prop-droid)."
  sudo tailscale up --operator="$USER" --hostname="$HOSTNAME_TS"
fi

step "3/8 SSH server (key-only) + fleet keys (box, Mac, phone)"
for k in "$BOX_KEY" "$MAC_KEY" "$PHONE_KEY"; do
  grep -qF "$k" ~/.ssh/authorized_keys 2>/dev/null || echo "$k" >> ~/.ssh/authorized_keys
done
chmod 600 ~/.ssh/authorized_keys
command -v restorecon >/dev/null && sudo restorecon -R "$HOME/.ssh"   # SELinux labels (Fedora/Bazzite)
sudo tee /etc/ssh/sshd_config.d/10-fleet.conf >/dev/null <<'SSHD'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
SSHD
sudo systemctl enable --now sshd && sudo systemctl reload sshd
if command -v firewall-cmd >/dev/null 2>&1; then
  sudo firewall-cmd -q --permanent --add-service=ssh && sudo firewall-cmd -q --reload
fi

step "4/8 PC → box SSH key + 'box' shortcut"
[ -f ~/.ssh/id_ed25519_box ] || ssh-keygen -t ed25519 -N '' -C "$HOSTNAME_TS->box" -f ~/.ssh/id_ed25519_box -q
if ! grep -q '^Host box' ~/.ssh/config 2>/dev/null; then
cat >> ~/.ssh/config <<'CFG'
Host box tomas-agent-box
    HostName 100.107.26.69
    User tomas
    IdentityFile ~/.ssh/id_ed25519_box
    ServerAliveInterval 30
CFG
chmod 600 ~/.ssh/config
fi

step "5/8 tmux"
TMUX_BIN=$(command -v tmux || true)
if [ -z "$TMUX_BIN" ] && [ -x /home/linuxbrew/.linuxbrew/bin/brew ]; then
  /home/linuxbrew/.linuxbrew/bin/brew install tmux && TMUX_BIN=/home/linuxbrew/.linuxbrew/bin/tmux
fi
if [ -z "$TMUX_BIN" ] || [ ! -x "$TMUX_BIN" ]; then
  curl -fsSL -o ~/.local/bin/tmux.appimage https://github.com/nelsonenzo/tmux-appimage/releases/latest/download/tmux.appimage
  chmod +x ~/.local/bin/tmux.appimage
  if ~/.local/bin/tmux.appimage -V >/dev/null 2>&1; then
    ln -sf tmux.appimage ~/.local/bin/tmux
  else  # no FUSE → extract once
    (cd ~/.local && ./bin/tmux.appimage --appimage-extract >/dev/null && rm -rf tmux-app && mv squashfs-root tmux-app)
    ln -sf ../tmux-app/AppRun ~/.local/bin/tmux
  fi
  TMUX_BIN=$HOME/.local/bin/tmux
fi
echo "tmux: $TMUX_BIN"

step "6/8 Claude Code (native → ~/.local/bin/claude)"
[ -x ~/.local/bin/claude ] || curl -fsSL https://claude.ai/install.sh | bash
if ! grep -q 'pc-setup' ~/.bashrc 2>/dev/null; then
cat >> ~/.bashrc <<'BRC'
# --- claude remote (pc-setup) ---
export PATH="$HOME/.local/bin:/home/linuxbrew/.linuxbrew/bin:$PATH"
alias cl='tmux new -A -s claude'
alias box='ssh -t box "tmux new -A -s claude"'
# cln [name] [dir] → fresh Claude session with Remote Control (shows in the Claude app)
cln() { local name="${1:-c$(date +%H%M)}"; local dir="${2:-$HOME}"; tmux new -A -s "$name" -c "$dir" "claude --dangerously-skip-permissions --remote-control $name"; }
BRC
fi

step "7/8 Claude login (subscription, NOT API key)"
if [ ! -s ~/.claude/.credentials.json ]; then
  echo "Claude opens now. Log in with your Claude subscription (propeidzas@gmail.com),"
  echo "say YES to 'trust this folder' + the bypass-permissions warning, then /exit."
  read -rp "Press Enter to start Claude... " _
  (cd ~ && ~/.local/bin/claude --dangerously-skip-permissions) >&3 2>&4 </dev/tty
fi

step "8/8 Autostart: Claude Remote Control session 'tv-pc' on every boot"
if [ -s ~/.claude/.credentials.json ]; then
  mkdir -p ~/.config/systemd/user
  cat > ~/.config/systemd/user/claude-remote.service <<UNIT
[Unit]
Description=Claude Code Remote Control session (tmux: claude)

[Service]
Type=oneshot
RemainAfterExit=yes
Environment=PATH=%h/.local/bin:/home/linuxbrew/.linuxbrew/bin:/usr/local/bin:/usr/bin:/bin
TimeoutStartSec=600
ExecStartPre=/bin/sh -c 'until curl -fsI https://claude.ai >/dev/null 2>&1; do sleep 3; done'
ExecStart=$TMUX_BIN new -d -s claude -c %h "%h/.local/bin/claude --dangerously-skip-permissions --remote-control $HOSTNAME_TS; exec bash -l"
ExecStop=-$TMUX_BIN kill-session -t claude

[Install]
WantedBy=default.target
UNIT
  sudo loginctl enable-linger "$USER"
  systemctl --user daemon-reload
  systemctl --user enable claude-remote.service >/dev/null 2>&1
  "$TMUX_BIN" has-session -t claude 2>/dev/null || systemctl --user restart claude-remote.service
else
  echo "Not logged in yet: skipped. Rerun this script after logging in."
fi

TS_IP=$(tailscale ip -4 2>/dev/null | head -1)
cat <<MSG | tee "$LOG_DIR/pc-setup-report.txt"

================ DONE: just say "done" in Discord #dev ===================
pc-setup OK  user=$USER  ts=${TS_IP:-?}  host=$HOSTNAME_TS
sshd=$(systemctl is-active sshd)  claude=$(~/.local/bin/claude --version 2>/dev/null | head -1 || echo missing)  autostart=$(systemctl --user is-enabled claude-remote.service 2>/dev/null || echo no)
pc->box key: $(cat ~/.ssh/id_ed25519_box.pub)
==========================================================================
Use it (open a NEW Konsole window first: this one doesn't know cl/cln yet):
  Phone/web  → Claude app → Code → session 'tv-pc'
  From box   → I can now run: ssh tv-pc (report also saved to pc-setup-report.txt)
  On the PC  → cl (attach) · cln (new session) · box (jump to the box)
MSG
