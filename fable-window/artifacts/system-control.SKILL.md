---
name: system-control
version: 1.0.0
description: Practical control of Tomas's machines from a Claude session — open new macOS Terminal/iTerm2 windows and tabs and run commands in them via osascript, activate/quit apps, place windows, read/write the clipboard, post notifications, hold the Mac awake with caffeinate; on the Linux box manage tmux sessions (new detached sessions, send-keys, capture-pane), systemd user units, and background jobs that survive disconnect. Prefers macos-mcp Snapshot→element for GUI acts when available. USE THIS whenever a task means "open a new terminal", "run this in another window/tab", "control my mac", "activate/quit an app", "keep this running after I disconnect", "start a detached job on the box", "leave this running in the background", or "spin up a tmux session". Trigger phrases below. For WHICH device / how to reach it (addresses, keys, ports) use fleet-control; this skill is HOW to drive a terminal, session, app, or background job once you are on the machine.
triggers:
  - "open a new terminal"
  - "open a new terminal window"
  - "open a new tab and run"
  - "run this in another window"
  - "control my mac"
  - "activate the app"
  - "quit the app"
  - "put a notification on my mac"
  - "keep this running after I disconnect"
  - "leave this running in the background"
  - "start a detached tmux session"
  - "run this in the background on the box"
  - "keep my mac awake"
---

# System Control

How to actually drive a terminal, an app, a persistent session, or a background job on Tomas's machines. Two surfaces: **macOS** (osascript / macos-mcp GUI control) and the **Linux agent box** (tmux + systemd user units). This is the mechanics layer. To decide WHICH device and HOW to reach it (hostnames, Tailscale IPs, SSH keys, adb paths), read `fleet-control` first — then come here to do the work.

**One rule above all: never kill a session, window, or process you did not create.** The box runs load-bearing persistent tmux sessions (`claude`, `main`) and always-on systemd user services; the Mac has whatever Tomas left open. Scope every stop/kill to something you started and named. Read the Safety Rails section before any kill/pkill/quit.

---

## 0. Pick the surface (read this first)

| You want to… | macOS | Linux box |
|---|---|---|
| Run a command in a fresh visible terminal | `osascript` → Terminal/iTerm2 `do script` | there is no GUI — use tmux (§4) |
| Keep something running after you disconnect | `caffeinate` + a detached process | tmux detached session or `systemd-run --user` (§4/§5) |
| Drive a GUI app (click, type, place windows) | **macos-mcp Snapshot→element** (preferred), osascript fallback | n/a (box is headless) |
| Manage an always-on service | launchd/`launchctl` (rare on Mac) | `systemctl --user` (§5) |
| Read/write clipboard | `pbcopy`/`pbpaste` | `xclip`/`wl-copy` only if a display is attached |
| Post a notification | `display notification` / `terminal-notifier` | `notify-send` (GUI session) or ntfy push (see fleet-control) |

The box is **headless** — "open a terminal" there means "start or reuse a tmux session", not spawn a window. On the Mac, prefer **macos-mcp** (`Snapshot` reads the UI element tree, then `Click`/`Type`/`Shortcut`/`App`) for anything GUI; fall back to `osascript` when macos-mcp is not granted or not installed.

---

## 1. macOS — open terminals and run commands (osascript)

All of these run on the Mac itself (or over `ssh mac` with the Mac awake — see fleet-control §1/§10). `do script` with **no target opens a NEW window**; targeting an existing window/tab reuses it.

**Terminal.app — new window, run a command:**
```bash
osascript -e 'tell application "Terminal" to do script "cd ~/brain && ls"'
osascript -e 'tell application "Terminal" to activate'
```

**Terminal.app — new TAB in the front window** (there is no clean `do script` verb for a tab, so open a tab via the menu keystroke, then write into the now-front tab):
```bash
osascript <<'EOF'
tell application "Terminal" to activate
tell application "System Events" to keystroke "t" using command down
delay 0.4
tell application "Terminal" to do script "echo running in the new tab" in front window
EOF
```

**Terminal.app — run in an EXISTING window** (window 1) instead of spawning one:
```bash
osascript -e 'tell application "Terminal" to do script "make -j8" in window 1'
```

**iTerm2 — new window / tab, run a command** (iTerm2's model is cleaner: create the split/tab, then `write text`):
```bash
# New window:
osascript <<'EOF'
tell application "iTerm2"
  activate
  set w to (create window with default profile)
  tell current session of w to write text "cd ~/brain && npm run dev"
end tell
EOF

# New tab in the current window:
osascript <<'EOF'
tell application "iTerm2"
  tell current window
    create tab with default profile
    tell current session to write text "tail -f /var/log/system.log"
  end tell
end tell
EOF
```

**Which terminal is installed?** Don't assume. Check before scripting:
```bash
osascript -e 'id of app "iTerm2"' 2>/dev/null && echo "iTerm2 present" || echo "use Terminal.app"
```

**Gotchas:**
- First `do script` / `keystroke` after a cold start needs the app frontmost — `activate` first, add a small `delay` before the tab keystroke or the command lands in the old tab.
- `keystroke ... using command down` requires the **Automation** and **Accessibility** grants (System Settings → Privacy & Security). Over headless SSH these GUI grants may be missing — if a keystroke silently no-ops, that is why; fall back to a plain new-window `do script`.
- `do script` returns immediately; it does not wait for the command to finish. To know when it's done, have the command write a sentinel file and poll for it.

---

## 2. macOS — activate / quit apps, window placement

**Activate (bring to front) / launch / quit:**
```bash
osascript -e 'tell application "Safari" to activate'      # launch or focus
open -a "Visual Studio Code"                              # launch (no AppleScript needed)
osascript -e 'tell application "Safari" to quit'          # graceful quit (may prompt to save)
osascript -e 'tell application "Preview" to quit saving no'   # quit, discard unsaved
```
Prefer `quit` (graceful) over `kill`/`pkill` for GUI apps — see Safety Rails. Only escalate to `kill` for a truly hung app, and target a **specific PID** you resolved, never a broad `pkill -f`.

**Window placement** (position/size in screen points, origin = top-left):
```bash
osascript <<'EOF'
tell application "System Events" to tell process "Safari"
  set position of window 1 to {0, 25}
  set size of window 1 to {1280, 800}
end tell
EOF
```
Needs Accessibility grant. For multi-monitor or reliable element targeting, prefer **macos-mcp**: `Snapshot` to read window/element geometry, then act — deterministic, no coordinate guessing.

---

## 3. macOS — clipboard, notifications, caffeinate

**Clipboard:**
```bash
printf '%s' "text to copy" | pbcopy          # write
pbpaste                                        # read
osascript -e 'set the clipboard to "hi"'      # AppleScript alternative
```

**Notification** (banner in Notification Center):
```bash
osascript -e 'display notification "Build finished" with title "Claude" sound name "Glass"'
terminal-notifier -title "Claude" -message "done" 2>/dev/null   # if installed; richer (click actions)
```
To push to a device that is not the Mac in front of you, use the tablet/phone **ntfy** path in fleet-control, not `display notification`.

**caffeinate — keep the Mac awake so a long job / reverse-SSH survives:**
```bash
caffeinate -dimsu &                 # prevent display+idle+system sleep until killed; note the PID
caffeinate -t 3600                  # stay awake for 3600s then exit
caffeinate -w 12345                 # stay awake until PID 12345 exits (wrap a specific job)
caffeinate -dis make release        # stay awake only for the duration of this command
```
Best pattern: `caffeinate -dis <yourcommand>` so wakefulness is scoped exactly to the job and self-clears when it ends — no dangling caffeinate to remember to kill. This is the fix for "box→Mac SSH dies because the Mac slept" (fleet-control §1): keep the Mac plugged and wrap the reverse-reach job in caffeinate.

---

## 4. Linux box — tmux (the "terminal" of a headless machine)

On the box, a tmux session IS the persistent terminal. It survives SSH drops; you attach and detach freely. **The box already runs load-bearing sessions `claude` and `main` — do not touch them (see Safety Rails).** Create your OWN named session for new work.

**Create a NEW detached session and run a long job in it** (survives disconnect immediately, no attach needed):
```bash
tmux new-session -d -s build 'cd ~/systems && ./long-report.sh; exec bash'
# -d = detached; -s build = your own name; trailing `exec bash` keeps the pane open after the job
```

**Send a command into an existing session** (send-keys types it + presses Enter):
```bash
tmux send-keys -t build 'echo phase 2 && ./step2.sh' Enter
```

**Read what a session printed** (capture-pane; non-interactive, safe to poll):
```bash
tmux capture-pane -t build -p              # current visible pane, as text
tmux capture-pane -t build -p -S -200      # include last 200 lines of scrollback
```

**List / attach / detach:**
```bash
tmux ls                                    # list sessions — check names before creating/killing
tmux attach -t build                       # attach (Ctrl-b d to detach and leave it running)
tmux attach -d -t build                    # attach and reap a lingering zombie client
```

**Kill ONLY your own session when done:**
```bash
tmux kill-session -t build                 # never `kill-server` (nukes claude/main too)
```

**Poll-to-completion pattern** (headless, no attach): have the job write a sentinel, poll for it, then capture output.
```bash
tmux new-session -d -s job1 'set -e; ./work.sh > ~/tmp/job1.log 2>&1; touch ~/tmp/job1.done'
# ... later, poll: `test -f ~/tmp/job1.done` ; then `cat ~/tmp/job1.log`
```

**Alternatives to tmux for "survive disconnect"** (use when a full session is overkill):
```bash
setsid -f ./worker.sh > ~/tmp/worker.log 2>&1        # detached, new session, no controlling tty
nohup ./worker.sh > ~/tmp/worker.log 2>&1 &          # ignores SIGHUP; note $! for the PID
```
Prefer tmux on the box — it is the house style and gives you capture-pane visibility. Prefer `systemd-run --user` (§5) when the thing should be supervised/restartable rather than fire-and-forget.

---

## 5. Linux box — systemd user units & supervised background jobs

The box runs services via **`systemctl --user`** (NOT launchd, NOT system-wide). Units live in `~/.config/systemd/user/`; the `~/systems` suite tracks its units in `~/systems/systemd/` and (re)deploys via `systemd/install.sh`.

**Inspect / control an existing service** (read before you touch — these are load-bearing):
```bash
systemctl --user status creative-command-center
systemctl --user restart tablet-dash.service
journalctl --user -u hermes-gateway -n 80 --no-pager
systemctl --user list-units --type=service        # what's running
systemctl --user list-timers                       # scheduled crons (the timer suite)
```

**Run a one-off supervised background job** (systemd-run gives it a name, logs to journal, survives disconnect):
```bash
systemd-run --user --unit=myjob --description="one-off report" \
  bash -c 'cd ~/systems && ./report.sh'
journalctl --user -u myjob -f          # follow its output
systemctl --user stop myjob            # stop ONLY the unit you named
```

**Survive full logout** (not just SSH drop): user services stop when the last session ends unless lingering is on.
```bash
loginctl show-user tomas | grep Linger     # check
loginctl enable-linger tomas               # keep user units alive with no active login (box already set)
```

**Adding a new persistent service:** drop the unit in `~/systems/systemd/`, run that suite's `systemd/install.sh`, then `systemctl --user daemon-reload && systemctl --user enable --now <unit>`. Don't hand-place units directly in `~/.config/systemd/user/` for anything that belongs to `~/systems` — it will drift from the tracked copy.

---

## 6. Safety rails (the ones that actually bite)

- ☐ **Never kill a session/window/process you did not create.** Before any `kill-session`, `stop`, or `quit`, run `tmux ls` / `systemctl --user list-units` and confirm the target is one YOU started and named. The box's `claude` and `main` tmux sessions and its always-on services are load-bearing.
- ☐ **Never `tmux kill-server`.** It destroys every session including the persistent ones. Kill by `-t <yourname>` only.
- ☐ **Never inline `pkill -f <name>` — it self-matches.** The `pkill` process's own command line contains `<name>`, so it (and the compound shell running it) gets killed before the restart line runs. This is a documented box footgun (`tablet_server.py`, `reauth_personal.py`). Instead:
  - Put restart logic in a `restart.sh` FILE on the device and call the file, OR
  - Resolve a PID and exclude yourself: `pgrep -f worker.py | grep -v $$ | xargs -r kill`, OR
  - Prefer `systemctl --user restart <unit>` / `tmux kill-session -t <name>` — clean, no self-match.
- ☐ **adb / ssh→adb: one command at a time.** Never chain `&&`, `|`, `;`, `>`, or quotes across an `ssh → adb → sh` boundary — they get dropped or mangled. Put compound logic in a script file on the target and call it. Use `%s` for spaces in `adb shell input text`. (Full device-reach detail: fleet-control §4/§5.)
- ☐ **Graceful before forceful.** Quit GUI apps with `quit`, stop services with `systemctl --user stop`. Only escalate to `kill <PID>` on a confirmed-hung target with a specific PID — never a broad `pkill -f` / `killall`.
- ☐ **`do script` / `systemd-run` return immediately.** They don't wait for the work to finish. Gate "done" on a sentinel file or `journalctl`/`capture-pane` output, not on the launcher's exit.
- ☐ **GUI osascript needs grants.** Automation + Accessibility must be granted to the driving terminal app; over headless SSH they may be absent (silent no-op). Prefer macos-mcp (also grant-gated but element-deterministic) or a plain new-window `do script` that needs no keystroke.
- ☐ **caffeinate leaks.** A bare `caffeinate &` outlives your task. Prefer `caffeinate -dis <cmd>` (scoped to the command) or `caffeinate -w <PID>` (scoped to a job) so it self-clears.

---

## 7. Cross-references

- **`fleet-control`** — which device, what address/key/port, how one box reaches another, adb/Fully/ntfy specifics, the persistent-session aliases (`cl`, `claude-box`, `claudebox`). Read it to get ONTO the machine; use this skill to DRIVE it once there.
- **macos-mcp** (Mac, installed 2026-07-02) — Accessibility-API GUI control: `Snapshot`→element then `Click`/`Type`/`Shortcut`/`App`/`Shell`. Preferred over osascript coordinate/keystroke hacks for anything GUI.
- **mobile-mcp / android MCP** (box→tablet/phone) — accessibility-tree device control; same "one action, verify, next" discipline as adb.

*All commands here are for Tomas's own machines under his control. When a detail conflicts with a live check, trust the live check.*
