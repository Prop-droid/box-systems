# Creative Feedback Loop — Design Spec

**Date:** 2026-06-13
**Status:** Approved, pre-implementation
**Owner:** Tomas

## Purpose

Capture Tomas's accept/edit/kill verdicts on creative drafts (scripts, briefs, ad copy), detect recurring patterns across those verdicts, and — with explicit human approval — promote stable patterns into the `feedback_*` memory canon that the creative skills already read. The result: future drafts drift toward what Tomas actually ships, closing the loop the MindStudio "agentic OS" article identifies as the missing connective layer.

This is the highest-leverage gap in Tomas's existing agentic stack (persistent context, tool registry, vector memory, and orchestration already exist). It reuses existing infrastructure rather than adding an island.

## Scope

**In scope (v1):** creative outputs only — the artifacts produced by `shameless-script`, `dr-script`, `creative-brief-builder`, `email-copy`, `landing-page-copy`, `micro-scripts`, and hook batches. Signal = shipped-as-is / edited / killed, plus the edit diff.

**Out of scope (v1, YAGNI):**
- Auto-inference of verdicts from ClickUp status or the approved-scripts SHA Doc (phase 2).
- ROAS / winners.jsonl performance coupling (winners archive already covers performance; join later).
- Any UI.
- Logging of drafts that never receive a verdict.
- Feedback on agent/cron outputs or generic non-creative skill outputs.

## Architecture — four units

Each unit has one job, a defined interface, and is independently testable.

### Unit 1 — `/feedback` (capture)
A slash command. Invoked by Tomas after a creative draft, carrying a verdict. No instrumentation of the generating skills (capture-on-verdict).

- **Input:** the verdict (`shipped` | `edited` | `killed`), plus optional payload (the final shipped version if `edited`; a reason if `killed`).
- **Behavior:**
  1. Locate the most recent creative artifact in the current session. If none is found, prompt Tomas to paste it or abort (do not log an empty record).
  2. Classify `brand`, `artifact_type`, and source `skill` from context.
  3. If `edited`: compute a `diff_summary` (1–2 lines: what changed and the direction) and extract a one-line `lesson`, using the draft and final both present in context.
  4. If `shipped`: `lesson` may be empty or a short "what worked" note; no diff.
  5. If `killed`: record the reason as `lesson`.
  6. Append exactly one record (one line) to the ledger.
- **Output:** one appended JSONL record; a one-line confirmation to Tomas.

### Unit 2 — the ledger (storage)
`~/systems/creative-feedback/ledger.jsonl` — append-only, local (per the local-cron rule; never on Drive).

Record schema (one JSON object per line):
```json
{
  "ts": "2026-06-13T12:40:00+03:00",
  "id": "fb_<8char>",
  "brand": "shameless",
  "artifact_type": "script | brief | ad_copy | email | lp | hook",
  "skill": "shameless-script",
  "verdict": "shipped | edited | killed",
  "draft": "<the generated text>",
  "final": "<shipped version, present only if edited>",
  "diff_summary": "<1-2 lines, present only if edited>",
  "lesson": "<one-line extracted lesson>",
  "tags": ["hook", "cta"],
  "promoted": false
}
```
- `id` is a content-independent short id (assigned at write; no `Math.random`/timestamp constraints apply here since this runs in normal shell/Claude context, not a Workflow script).
- `promoted` flips to `true` when a pattern that includes this record has been promoted into canon, for dedup.

### Unit 3 — `/feedback-synth` (synthesis)
On-demand slash command **and** a Monday cron (joins the existing Monday lineup: winners-refresh, sha-weekly-report). Runs via `claude` headless (stdin prompt) like the other `~/systems` agents.

- **Input:** the ledger; a watermark file `~/systems/creative-feedback/.watermark` (timestamp of last synthesis).
- **Behavior:**
  1. Read ledger records newer than the watermark (plus any older un-promoted records for context).
  2. Cluster by `artifact_type + tag + edit-direction`.
  3. Flag a pattern as **stable** when it appears **≥3 times with a consistent direction** (threshold configurable in a small `config.json`).
  4. For each stable pattern, draft a proposed promotion rendered as a concrete diff against a target: either a new/updated `feedback_*` memory file, or a rule line in a script-skill file.
  5. Write all proposals to `~/systems/creative-feedback/proposals.md` (human-readable, each with: pattern summary, supporting record ids, the proposed diff, target file).
  6. Update the watermark.
- **Output:** `proposals.md` populated. **Never writes to canon.**
- **Idempotency:** watermark advances; already-promoted patterns are skipped via the `promoted` flag and a promoted-patterns log.

### Unit 4 — promotion (gated apply)
Triggered when Tomas approves entries in `proposals.md` (e.g., `/feedback-promote` or by telling Claude which proposals to apply).

- **Input:** approved proposal(s) from `proposals.md`.
- **Behavior:**
  1. Apply the diff: write/update the target `feedback_*` memory file and add/refresh its one-line entry in `MEMORY.md`; or edit the target script-skill file.
  2. Mark the supporting ledger records `promoted: true` and append the pattern to `~/systems/creative-feedback/promoted.log`.
  3. Confirm what changed.
- **Output:** updated canon (memory and/or skill file); ledger + promoted log updated.
- **Safety:** nothing here runs without Tomas's explicit approval of the specific proposal.

## Data flow

```
existing creative skills generate draft
        │
        ▼
Tomas: /feedback <verdict> [+final|+reason]
        │
        ▼
ledger.jsonl  ──(weekly cron or on-demand)──▶  /feedback-synth
                                                     │
                                                     ▼
                                              proposals.md
                                                     │
                                          Tomas approves
                                                     ▼
                                        promotion → feedback_* memory / skill file
                                                     │
                                                     ▼
                                   next generation reads updated canon  (loop closed)
```

## Integration with existing systems

- **Location:** `~/systems/creative-feedback/` — matches the existing cron-agent layout; local, never Drive.
- **Cron:** synthesis added to the Monday lineup via launchd (same pattern as winners-refresh / sha-weekly-report); prompt piped to `claude` headless over stdin.
- **Promotion target:** the existing `feedback_*` memories the creative skills already auto-read (`script_defaults` instructs "read before writing any ad copy"). No new read-path is introduced.
- **Brand routing:** Shameless lessons route to Shameless `feedback_*` memories; other-brand lessons route to `dr-script`-general feedback memory.

## Error handling

- `/feedback` with no creative artifact in the session → prompt Tomas to paste it, or abort; never log an empty/placeholder record.
- Ledger writes are single atomic appended lines (no partial-record corruption).
- Synthesis is idempotent: re-running without new records produces no new proposals; watermark + `promoted` flag prevent re-proposing.
- Missing ledger or empty ledger → synthesis exits cleanly with a "nothing to synthesize" note.
- A malformed ledger line is skipped with a logged warning, not a hard failure.

## Testing

- **Unit 1:** feed a known draft + each verdict type; assert exactly one well-formed record appended; assert abort on no-artifact.
- **Unit 2:** schema validation on appended records; atomic-append under repeated writes.
- **Unit 3:** seed a ledger with a planted ≥3× pattern and noise; assert the pattern is flagged and noise is not; assert idempotency on re-run.
- **Unit 4:** approve a proposal; assert the target memory/skill file and MEMORY.md are updated and supporting records flip to `promoted`.

## Configuration

`~/systems/creative-feedback/config.json`:
```json
{ "stable_threshold": 3, "brands": ["shameless"], "default_brand": "shameless" }
```

## Open phase-2 ideas (not built now)

- Auto-infer verdicts by reconciling generated drafts against the approved-scripts SHA Doc and ClickUp task status.
- Join promoted lessons to winners.jsonl performance so "edited toward X" can be weighted by whether X actually performed.
