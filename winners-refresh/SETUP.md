# winners.jsonl auto-refresh

Keeps the local winner archive current so analytical questions hit fresh data
instead of a 1–2 week stale snapshot. Runs **Mondays 08:00 local** via launchd.

## What it does

`run_winners_refresh.sh` runs three steps from the ClickUp Connection folder:

1. **`discover_winners.py`** — queries the Creative Strategist list for every parent
   currently in `mb - winner` and appends any not already in `winners.jsonl` as a
   stub. (This is the step `enrich_v3.py` lacks — without it, newly-graduated
   winners never enter the archive.)
2. **`enrich_v3.py`** — fetches full data + comments + performance snapshots for
   every winner (~138s) and atomically rewrites `winners.jsonl`.
3. **`reparse_v3.py`** — fixes name-slug parsing.

Output: `~/Library/Logs/winners-refresh/<timestamp>.log` (one per run) plus
launchd's `launchd.out.log` / `launchd.err.log`.

## One-time setup (per Mac — not synced via Drive)

**1. Store the ClickUp personal API token durably** (the scripts read it from here):

```sh
mkdir -p "$HOME/.config/clickup"
printf '%s' 'pk_YOURTOKEN' > "$HOME/.config/clickup/pk"
chmod 600 "$HOME/.config/clickup/pk"
```

Get the token from ClickUp → Settings → Apps → API Token (`pk_...`). This replaces
the old throwaway `/tmp/clickup_pk`, which didn't survive reboots.

**2. Install the launchd job:**

```sh
cp "$HOME/Library/CloudStorage/GoogleDrive-propeidzas@gmail.com/My Drive/Code Things/systems/winners-refresh/com.tomas.winners-refresh.plist" "$HOME/Library/LaunchAgents/"
launchctl unload "$HOME/Library/LaunchAgents/com.tomas.winners-refresh.plist" 2>/dev/null
launchctl load "$HOME/Library/LaunchAgents/com.tomas.winners-refresh.plist"
```

## Run manually / test

```sh
bash "$HOME/Library/CloudStorage/GoogleDrive-propeidzas@gmail.com/My Drive/Code Things/systems/winners-refresh/run_winners_refresh.sh"
# or trigger the launchd job immediately:
launchctl start com.tomas.winners-refresh
tail -n 40 "$HOME/Library/Logs/winners-refresh/"*.log
```

## Notes

- **Per-Mac:** the plist, the token file, and `~/Library/Logs/` are local to each
  machine. The scripts and this doc ride Drive.
- **Schedule:** Monday 08:00, ahead of the 09:07 SHA weekly report. Bump the
  cadence in the plist (`StartCalendarInterval`) if winners need fresher tracking.
- **Token rotation:** if the ClickUp token is regenerated, rewrite
  `~/.config/clickup/pk`. A missing/expired token makes the run exit early with a
  clear error in the log.
- **Self-healing:** discovery re-adds any still-active winner each run, so a
  transient enrich failure that drops a record is recovered on the next pass.
