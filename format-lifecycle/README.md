# format-lifecycle

On-demand report classifying each video creative format as FRESH / SCALING /
PEAKING / FATIGUING / DEAD from our own weekly spend + ROAS curves, using the
`ai.asset_tagging_video` `format_style` tags. The point: catch a format on the
way up and stop briefing it on the way down, from spend truth instead of
eyeballing the Ad Library. (Idea lifted from the ORIRI "trending formats"
playbook, 2026-08-03, upgraded with our own data.)

- `format_lifecycle.py` — one BQ query (creative_dashboard × asset_tagging_video
  joined on the `video_id=` in `asset_link`), per-format weekly series, phase
  rules at the top of `classify()`. Reports land in `reports/`.

## Run

```bash
python3 ~/systems/format-lifecycle/format_lifecycle.py                 # SHA, 8 weeks
python3 ~/systems/format-lifecycle/format_lifecycle.py --weeks 12 --min-spend 5000
```

Needs BQ SA at `~/.config/gcloud/ejam-dwh-sa.json` and `bq` on PATH.

## Status: on-demand, no timer

Deliberately not cron'd — format calls are a judgment activity, run it before a
briefing wave or monthly. If a weekly feed is ever wanted, mirror the
fatigue-sentinel unit pattern.

## Known limits

- **Videos only.** `ai.asset_tagging_static` keys on an md5 file hash
  (`gs://ejam-asset-storage/.../images/<md5>.jpg`) with no counterpart column in
  `creative_dashboard` (images carry opaque `facebook.com/ads/image/?d=`
  links). Needs a join key from the data team before statics can be covered.
- `format_style` is free-text from the tagger, so big formats are sometimes one
  asset ("POV handheld restock…" = the $154k whale). Read single-asset rows as
  ad lifecycle, multi-asset rows as format lifecycle.
- Related but different: `~/systems/fatigue-sentinel/` watches per-ad decay on
  winning ads daily; this watches format-level lifecycle on demand.
