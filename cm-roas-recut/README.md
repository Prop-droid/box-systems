# cm-roas-recut

Re-ranks the Shameless creative pattern canon by **contribution-margin ROAS**
instead of spend / ClickUp `mb - winner` graduation / variant keep rate.

    CM-ROAS = (revenue + upsale_revenue - cogs - transaction_fee - agency_fees) / spend

Breakeven = 1.0. Reproduces the ~0.57 cmROAS figure already used in canon.

## Run

    python3 ~/systems/cm-roas-recut/cm_recut.py \
      [--pivot 2026-07-21] [--since 2026-02-01] [--outdir ~/brain/projects/2026-08/cm-roas-recut]

Needs: BQ SA `~/.config/gcloud/ejam-dwh-sa.json`, ClickUp token `~/.config/clickup/pk`.
Task names come from the local ClickUp archive first, REST for the rest (~3 min
on a cold cache; delete `names_all.json` in the outdir to force a refresh).

Outputs `bq_by_task.csv`, `names_all.json`, `pattern_cm.json` and prints four
cuts: pre/post pivot x all-tasks/winners-only.

## Canon it feeds

- `~/brain/memory/feedback_cm_roas_pattern_recut.md` (the canon brief skills read)
- `~/brain/projects/2026-08/cm-roas-recut/REPORT.md` (full tables + caveats)

Re-run after each sprint, or whenever the positioning pivots (move `--pivot`).
