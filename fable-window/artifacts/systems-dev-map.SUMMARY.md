# systems-dev-map (task 41) — SUMMARY

**Delivered:** `~/systems/CLAUDE.md` (new file, 265 lines) — the instantly-effective-developer map for the box automation estate. CLAUDE.md was absent, so per rule 10 it was written live (new file only, no existing source touched). Commits: `0b843ab` baseline before, `aacb134` after.

## What the map covers

1. **Subsystem map** — all 22 dirs + tablet-screen.sh, grouped (data pipelines / research-agent / reports+synthesis / feedback+lessons loops / infra+guards). Each entry: what it does, live schedule, entry point, and its dry-run/test command (`PERF_DRY_RUN=1`, `AUTOFILL_LINT=1`, `--dry-run`, `DRY_RUN=1`, `--limit N`, unit tests) or an explicit "no dry-run + what a manual run costs".
2. **systemd patterns** — oneshot+timer with `Persistent=true`, `%h` units, install.sh deploy flow, the **cgroup kill gotcha** (children of a oneshot die with the service cgroup; detach via `systemd-run --user --unit X --collect`, anchored-pgrep double-launch guard), no-login-env (127 = PATH, 203/EXEC = lost exec bit), night-slot staggering, and the **repo-vs-live drift rule** (list-timers is ground truth; ~14 live units are owned outside this repo).
3. **Headless claude conventions** — `/usr/local/bin/claude-max` wrapper semantics (PAUSE_CLAUDE_BG early-exit, OAuth not API key, PATH prepend), prompt via stdin (--allowed-tools is variadic), `</dev/null`, `--dangerously-skip-permissions` + tool bounding, timeout/validate/retry/atomic-land, deterministic + hermes fallbacks, Sonnet-for-crons model discipline, limit-hit = transient, zero-output silent failure, no background-and-wait in one-shot runs.
4. **Fleet networking** — Tailscale IPs not mDNS (Mac 100.68.166.21 + id_ed25519_mac, box 100.107.26.69), per-host ssh aliases, tablet adb 192.168.0.160, ntfy topics, creds-outside-repo inventory.
5. **Git** — `git@github-personal:Prop-droid/box-systems.git` (alias required), `type(scope):` commit style, baseline-before-risky-change convention.
6. **VERIFY** — one paste-ready block: scheduling ground truth, watchdog, every per-subsystem dry-run/test, a cheap end-to-end claude-max probe, and manual-run cost cautions.

## Non-obvious findings surfaced while mapping (recorded in the map)

- `research-deepdive.service` (live) was **repurposed to the lanes engine** (`bin/run-lanes.sh`); `deepdive.sh` is manual-only now, and `systemd/README.md`'s schedule table is stale on that row (also missing atria-weekly, fatigue-sentinel, iteration-suggestions, task-lessons-synth, tablet-screen, box-watchdog time drift 06:30 vs "08:30" in comments).
- atria-weekly + fatigue-sentinel timers are now LIVE (first fire 2026-07-06 07:30/08:30) — their READMEs still say "STAGED, not enabled".
- usage-guard / fable-resume / iteration-suggestions unit files exist only in `~/.config/systemd/user/`, not in `systemd/` in the repo — deploy drift if the box is ever rebuilt from the repo.
- `launch-autofill` has no live timer (plist is `.disabled`, no systemd unit) — it currently only runs manually.
- The baseline commit also swept in pending approved night-4 work (autofill.py v2 replacement + the 4 staged unit files) that was sitting uncommitted.

## Open questions

- Should the live-only units (usage-guard, fable-resume, iteration-suggestions) be copied into `systemd/` so install.sh owns them? (Recommended; one-line cp each.)
- `systemd/README.md` schedule table could be regenerated from `list-timers` — left untouched (existing file, out of task scope).
