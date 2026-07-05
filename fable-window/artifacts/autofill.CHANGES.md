# autofill.py — CHANGES

Extends `~/systems/launch-autofill/autofill.py` with a full **report-only**
convention lint for the SHA Creative Strategist list (`901110066469`).
Additive: the autofill write path is byte-for-byte unchanged; the lint is a new
mode that only reads.

## What changed

1. **New lint mode (`AUTOFILL_LINT=1` or `--lint`).** New `LINT_ONLY` flag +
   `run_lint()` entry point. When set, `__main__` runs `run_lint()` instead of
   `main()`. The lint reuses the existing `fetch_tasks()`, `field_value()`,
   `classify()`, `lp_on_hold()` and the `F{}` UUID map exactly — same list
   scoping, same parents-only / no-ClickBot / status filter, same lookback.
   **It issues zero POSTs** (no field writes, no comments), so it is safe to run
   against the live list.

2. **Five per-task checks** (see the module docstring + the dry-run report):
   - `name` — SHA naming canon. Structural: `SHA_`, 4-digit year, `S##` sprint,
     `_Tom_` owner. Angle: a canon angle token must be **present** in the name.
   - `req-fields` — required custom fields non-empty for the task's type+status.
   - `defaults` — launch tasks: assignee Alejandra + priority high + type-correct
     time estimate.
   - `list` — description contains a markdown ordered list (collapse-bug flag).
   - `em-dash` — em/en dash in a copy-facing field (extends the existing
     `_lint_dashes` sanitizer into a report-only check over live copy).

3. **Canon angle vocabulary** (`CANON_ANGLES`) sourced from
   `feedback_sha_task_angle_canon_naming.md` and the wiki angle canon it points
   to (`brain/wiki/shameless/creative-strategy/creative-angles.md`, the 15
   canonical positioning angles), plus documented short-token aliases and the
   recurring live tokens that map onto those angles.

4. **Output** — compact fixed-width violations table to stdout, sorted
   fail-first then by check then task, with a summary header (counts by class,
   by severity, by check). No auto-fix, ever.

## Design decisions (and why)

- **Angle check verifies PRESENCE, not slot position.** Live task names on this
  list do not follow one rigid token order — WL, Duo-, BRPK-, pack-launch and
  THT/talent names all shuffle where the angle sits (verified against 212 live
  SHA names). A positional exact-match produced ~60 false positives (script-name
  and talent-name tokens flagged as "invalid angle"). The lint instead confirms
  a canon angle token appears somewhere in the name, matching whole tokens and
  their hyphen / camelCase components (so `Fiber-Spec-Board2` and
  `Do-The-Fiber-Math1` pass on `Fiber`/`Spec`). **Limitation, documented in
  code:** this does not catch a canon angle in the wrong slot, nor an invented
  compound that reuses a canon word (`DailyFiber` passes on `Fiber`). Tightening
  to exact-slot enforcement (which would catch the `DailyFiber`→`Fiber` case
  from the memory) requires standardizing the name format first — out of scope
  for a report-only lint. Report severity is `warn` (review), not `fail`.

- **WL (whitelisting / creator-usage) tasks are exempt from the angle rule.**
  Their convention is `SHA_yr_S##_WL_<Talent>_<Month>_Tom` — no angle token by
  design. Structural checks still apply.

- **Time estimate is type-aware (8h video / 3h image), not a flat 8h.** The
  brief said "8h estimate"; the cited `feedback_launch_task_defaults.md` refines
  that to **480 min video/CTV, 180 min image-test** (Tomas corrected image down
  from 8h to 3h on 2026-06-26). The lint follows the memory (the authority the
  brief cites) and checks the type-correct value.

- **Required-field policy is status-gated.** Taxonomy (Brand, Product,
  Deliverable Type, Responsible) is required on every launch task; launch copy
  (FB Page, Headline, Text, LP) is only required once the task reaches
  `cs review` / `approved` / `sent to mb` — the ready-to-launch tiers where a
  media buyer asks for launch details (`project_sha_launch_details_fill.md`). LP
  is dropped from the requirement when the task is on `LP_HOLD`. `script_link` is
  **not** required — video scripts legitimately live in the description or inline
  (`project_launch_autofill_agent.md`), so requiring the field false-flagged.

- **em-dash is scoped to copy-facing fields (Headline, Text, name), not the
  description.** Descriptions hold the internal 🟥/🟦/🟧 brief scaffolding whose
  dashes are formatting, not ad copy; scanning them drowned the real headline/
  text hits (44 description hits vs 13 real copy hits).

- **Brief/research/admin tasks are classified out** of the naming + default
  checks (`Copy Research + N Task Ideas`, `Image Task Creation`, `Retro task`,
  etc.) — they are a different workflow, not launch creatives. They are still
  counted and still checked for ordered-list / em-dash. Names that are neither
  SHA-format nor a recognized brief family are flagged `freeform` for review.

## Dry-run result (2026-07-03, live read)

266 tasks in scope (launch 212, brief 52, freeform 2). **309 violations
(59 fail, 250 warn) across 214 tasks** — `defaults`=210, `req-fields`=57,
`name`=24, `em-dash`=13, `list`=5. Full table: `naming-lint.dryrun.md`.
Notable real signal: only 2 of 212 launch tasks fully pass the launch-defaults
(Alejandra + high + estimate) — consistent with Tomas's own note that these are
routinely forgotten. The `req-fields` fails are dominated by the known
variety-pack `Product` dropdown gap.

## Verify

```
AUTOFILL_LINT=1 python3 autofill.py     # report-only, zero writes
```
Confirmed: 0 POST calls issued in lint mode; write path (`main()`) unchanged.
