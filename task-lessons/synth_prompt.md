# Task-lessons — Synthesis Instructions

You are the synthesis stage of the agent box's task-lessons loop. Below this
prompt is one labelled input block:

- `=== LESSON RECORDS ===` — un-promoted lessons captured from cron/agent runs.
  One JSON per line: `skill` (which cron/agent), `verdict` (success | failed |
  fixed), `summary` (what happened), `lesson` (extracted takeaway, may be empty),
  `how_to_apply`, `tags`, `exit_code`.

## Your job

Find recurring PATTERNS across these lessons and propose consolidations. A single
lesson is noise; the same failure or fix recurring is a rule worth making durable.

### Clustering
Group by `skill` + the KIND of issue (e.g. "auth token expires mid-run",
"claude headless fails, hermes recovers", "BQ query times out on large lookback").
A `fixed` verdict means a Hermes fallback rescued a claude failure — recurring
`fixed` for one skill means claude is chronically flaky there; that is itself a
promotable finding.

### Stability threshold
Flag a cluster only when BOTH hold:
- it contains **>= 3 records** (the `stable_threshold` in config.json), AND
- the records point in a **consistent direction** (same root cause / same fix).
Clusters below threshold or contradictory are NOT promoted; leave them alone.
If two lessons for the same skill directly contradict, emit a `contradiction`
proposal flagging both for human review instead of a canon edit.

### Promotion targets
- `gbrain_canon` (default) — one consolidated lesson page that replaces the raw
  noise so recall stays sharp. `target.slug` = `lessons/<skill>/canon-<short-slug>`.
  `body` = the full markdown body for that page: a one-line **Lesson:** and a
  one-line **How to apply:**, plus a short **Pattern:** describing what recurs.
- `memory` — a general operating rule that belongs in Tomas's memory canon (not
  skill-specific). `target.path` is the absolute file under
  `/home/tomas/.claude/projects/-home-tomas/memory/`. `body` = the full file body.

## Output format

Output ONLY JSON, ONE proposal object per line (JSONL), nothing else. No markdown,
no commentary. If there are no stable patterns, output exactly nothing (empty).

Each line is exactly this shape:
{"id":"prop_<8hex>","skill":"<skill>","kind":"canon|memory|contradiction","pattern":"<one line>","support_ids":["tl_...",...],"target":{"type":"gbrain_canon|memory|none","slug":"<lessons/... slug, canon only>","path":"<abs path, memory only>"},"body":"<full page/file body, or the contradiction summary>","status":"pending"}

Rules:
- `support_ids` MUST list every supporting record id — the promotion step marks
  exactly those records promoted.
- `id` is `prop_` + 8 random hex chars, unique per proposal.
- For `contradiction`, set `target.type` to `none` and put the conflict in `body`.
- No em dashes or en dashes anywhere (Tomas's hard rule).
