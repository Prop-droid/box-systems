# fatigue-sentinel — dry-run verification

Command: `~/systems/fatigue-sentinel/run_sentinel.sh --dry-run`
Date: 2026-07-04 (Saturday)

## Output

```
DRY RUN — fatigue sentinel: 387 active ads (spend_now >= $100)

[WOULD PUSH — Priority high] Creative fatigue: 27 winner(s) decaying
7adfa57ff7d2dbdbc965f9edc88a8b2e | $2570 | roas 1.21->0.71 | hook 0.0%->0.0%
SH-13107-6 | $1608 | roas 1.19->0.60 | hook 0.0%->0.0%
SH-16360-1 | $1001 | roas 1.17->0.37 | hook 36.3%->39.8%
SH-8654-7 | $860 | roas 1.84->0.26 | hook 44.6%->44.3%
120245025553470301 | $760 | roas 1.70->1.06 | hook 0.0%->0.0%
not Monday (Saturday) — no heartbeat

sent one real [TEST] Priority min push (delivery proof)
```

## What this proves

- One BQ query ran against `ejam-dwh.production.creative_dashboard` (SA
  `~/.config/gcloud/ejam-dwh-sa.json`), returned 387 ads clearing the active
  floor (`spend_now >= $100`, i.e. $50/day x 2-day now window).
- Decay logic fired: 27 winners (baseline ROAS > 1.0) with a hook OR roas drop
  past threshold and >= 10k impressions in the 48h window. Top 5 by now-spend
  are shown, exactly what the live Priority-high push would contain.
- Creative code resolution works both ways: `SH-####-#` extracted from
  `ad_name` where present, raw `ad_id` fallback otherwise
  (`7adfa57...`, `120245025553470301`).
- Heartbeat gating works: Saturday run correctly skipped the Monday heartbeat.
- Delivery proven: one real `[TEST]` Priority min push was sent to ntfy topic
  `tomas-tab-958e4431` (urllib raises on any non-2xx; it returned clean).

## Notes / observations

- Several top decayers show `hook 0.0%->0.0%`: those ads have >=10k impressions
  in the window but `view_3s_count` unpopulated (non-Meta channels track the 3s
  view differently). They alert on the ROAS-drop leg of the OR, which is
  correct — the ROAS collapse (e.g. SH-8654-7: 1.84 -> 0.26) is the real signal.
- 27 alerting winners on a Saturday is a lot; if the live push feels noisy after
  a week, tighten via the config block at the top of `fatigue_sentinel.py`
  (raise `MIN_IMPRESSIONS_48H`, `ROAS_DROP_REL`, or `BREAKEVEN_ROAS`). No code
  changes needed — all thresholds are constants there.

## Staging status

Not installed. Unit pair (`fatigue-sentinel.service` + `.timer`, daily 08:30)
lives in `~/systems/fatigue-sentinel/`. Enable per README:
`cp` the two units into `~/systems/systemd/` then `bash ~/systems/systemd/install.sh`.
