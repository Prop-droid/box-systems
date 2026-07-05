# atria-weekly (STAGED, not enabled)

Weekly Atria **followed-brands** competitor swipe pull + strategist NEW-ads diff.
Staged by fable-window task 15 on 2026-07-04. Nothing here is installed or
enabled until you run the steps below.

## What it does

1. `run_atria_weekly.sh` runs the atria skill's `atria_swipe_pull.py` with **no
   brand args** = the full followed roster (20 brands as of 2026-07-04), writing
   `atria-swipe-<date>.jsonl` + `.md` into
   `~/brain/projects/2026-06/competitor-ads-scrape/atria/`.
2. It finds the newest and previous **followed** snapshots (exact-date names;
   the daily gr-ns files are suffixed and excluded) and asks headless
   `claude-max` (Sonnet, stdin prompt, bounded tools) to write a NEW-ads diff to
   `atria-weekly-diff-<date>.md`.
3. If headless claude is capped/unavailable after 3 tries, a deterministic
   python fallback writes the same diff so the weekly report always lands.

## Relationship to the existing daily job

`research-monitor.service`/`.timer` (daily 01:45) already pulls a **brand-filtered
gut-health set** (`MONITOR_BRAND_IDS` -> the `-gr-ns-plus10` daily files) and
feeds the OpportunityBoard. This weekly job is **complementary**: the broad
followed roster, once a week, for a wider swipe surface. Both write into the same
dir but with distinct filenames, so they do not clobber each other.

## Enable (when you decide to)

```sh
# 1. symlink (or copy) the units into the user unit dir
ln -sf ~/systems/atria-weekly/atria-weekly.service ~/.config/systemd/user/atria-weekly.service
ln -sf ~/systems/atria-weekly/atria-weekly.timer   ~/.config/systemd/user/atria-weekly.timer

# 2. reload + enable the timer
systemctl --user daemon-reload
systemctl --user enable --now atria-weekly.timer

# 3. verify
systemctl --user list-timers | grep atria-weekly
```

Track the units in `~/systems/systemd/` per the box convention, and add a
watchdog line so a silent failure is visible (memory rule: a new cron is
invisible to the watchdog until it is registered):

```
# append to ~/systems/watchdog/jobs.conf
atria-weekly|192|/home/tomas/systems/atria-weekly/logs/atria-weekly-*.log|log
```

(192h ~= 8 days of slack on a weekly cadence.)

## Test before enabling

```sh
# one real run, foreground, watch the log
~/systems/atria-weekly/run_atria_weekly.sh
tail -n 40 ~/systems/atria-weekly/logs/atria-weekly-$(date +%F).log
ls -la ~/brain/projects/2026-06/competitor-ads-scrape/atria/atria-weekly-diff-$(date +%F).md
```

## Dependencies / gotchas

- Atria API key at `~/.config/atria/key` (chmod 600). If it 401s, refresh:
  `ssh mac 'cat ~/.config/atria/key'` -> box, `chmod 600`. The script exits 3
  with this hint if the key file is missing.
- Headless claude runs share the session usage cap; a limit-hit run is transient
  and the fallback covers it. 07:30 Mon is chosen to sit outside peak hours.
- First enabled run in `OUT_DIR` may have no prior followed snapshot there (the
  2026-07-04 seed run is the first). Until a second weekly snapshot exists, the
  diff reports "first snapshot, all counted new". This is expected.
