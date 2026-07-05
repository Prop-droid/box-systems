# fatigue-sentinel

Daily creative fatigue watch. Flags **winning** ads (baseline ROAS above
breakeven) whose hook rate or ROAS is decaying vs their trailing 7-day baseline,
and pushes one ntfy alert (Priority high) listing the top 5 decayers by spend.
Every Monday it also sends a Priority min heartbeat.

- `fatigue_sentinel.py` — one BQ query (ad_id x day, folded into now/baseline
  windows in-query), decay logic, ntfy push. Tunables at the top of the file.
- `run_sentinel.sh` — env + credential guard wrapper. `--dry-run` prints the
  would-be pushes and sends one real `[TEST]` Priority min push (delivery proof).
- `fatigue-sentinel.service` / `.timer` — daily 08:30 unit pair.

## Status: STAGING — not installed

The timer is **not** enabled. To enable after review:

```bash
cp ~/systems/fatigue-sentinel/fatigue-sentinel.service \
   ~/systems/fatigue-sentinel/fatigue-sentinel.timer \
   ~/systems/systemd/
bash ~/systems/systemd/install.sh
```

(Optionally add `fatigue-sentinel` to the `TIMERS` list in
`~/systems/watchdog/box-watchdog.sh` so the watchdog tracks it.)

## Manual run

```bash
~/systems/fatigue-sentinel/run_sentinel.sh --dry-run   # preview, sends [TEST] push
~/systems/fatigue-sentinel/run_sentinel.sh             # live
```

Needs BQ SA at `~/.config/gcloud/ejam-dwh-sa.json` and `bq` on PATH.
