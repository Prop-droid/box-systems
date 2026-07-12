# research-queue — verified-research pipeline (v1, staged 2026-07-12)

One question in, one adversarially-verified, cited, gated report out. Applies
the fable-window lessons (deterministic fan-out, adversarial verify, eval-gate)
to research tasks. Design doc: `~/fable-window/artifacts/research-harness.DESIGN.md`.

NOT scheduled. No timer exists; runs are manual or queued through night-queue.

## Pipeline

```
question -> S1 scope (haiku: N search angles, strict JSON)
         -> S2 dual sweeps IN PARALLEL          <- use-perplexity-for-search rule
              web lane:  headless claude (WebSearch/WebFetch/curl, NO perplexity)
              pplx lane: hermes -z (owns the perplexity MCP; claude has none)
              degrade:   hermes down -> 2nd independent web sweep + DEGRADED note
         -> S3 deterministic claim merge (python: extract ===CLAIMS=== blocks,
              jaccard dedup, cross-backend first, cap at RQ_MAX_CLAIMS, no silent caps)
         -> S4 adversarial verify (sonnet: try to REFUTE each claim;
              CONFIRMED needs 2 independent domains; missing verdicts degrade
              to UNVERIFIED deterministically)
         -> S5 synthesize (sonnet: inputs inlined, confidence tags mandatory,
              REFUTED claims -> "Killed claims" section, never findings)
         -> S6 eval-gate (gate.py, 7 named binary kills; 1 feedback retry,
              then land with a FAILED-GATE banner: worse report > silence)
         -> S7 gbrain draft (out/<slug>/gbrain-draft.md; only writes to gbrain
              when RQ_GBRAIN_FILE=1, via `gbrain put research/<slug>`)
```

Every stage output lands in `out/<slug>/` and the runner skips stages whose
output already exists: a killed or usage-paused run resumes, never restarts.
`~/.claude/PAUSE_CLAUDE_BG` is honored at start and after every LLM call.

## Usage

```bash
bash run_research.sh --question "..." [--slug s] [--fast] [--dry-run]
bash run_research.sh --queue          # drain next pending from queue/questions.jsonl
RQ_GBRAIN_FILE=1 bash run_research.sh --queue     # also file the page to gbrain
```

`--fast` = smoke/cheap profile: 3 angles, 8 claims, 3 min domains, tighter
timeouts. Queue rows: `{"id": "q1", "question": "...", "status": "pending"}`.

## Night-queue integration

Render `templates/research.task.template` ({{QUESTION}}, {{SLUG}},
{{NQ_ARTIFACTS}}) into a `.task` file and `nq add` it:

```bash
sed -e 's|{{QUESTION}}|current best practices for X|g' \
    -e 's|{{SLUG}}|2026-07-15-x-practices|g' \
    -e 's|{{NQ_ARTIFACTS}}|/home/tomas/systems/night-queue/queue/artifacts|g' \
    templates/research.task.template > /tmp/40-research-x.task
cp /tmp/40-research-x.task ~/systems/night-queue/queue/tasks/
```

The wrapper task is haiku (it only shells out to the runner and reports); the
runner routes its own models per stage.

## Model routing + cost bounds (env-overridable, constants at top of runner)

| stage | model | timeout | bound |
|---|---|---|---|
| scope | claude-haiku-4-5 | 300s | RQ_ANGLES (5) |
| sweep x2 | claude-sonnet-4-6 / hermes chain | 900s each | parallel, wall = max |
| verify | claude-sonnet-4-6 | 700s | RQ_MAX_CLAIMS (12) |
| synth | claude-sonnet-4-6 (RQ_SYNTH_MODEL for opus) | 600s | RQ_INLINE_CAP 24k chars/sweep |

Worst case ~6 claude calls + 1 hermes call per question. The hermes lane spends
paid Codex/Gemini tokens; everything else rides the Max subscription window and
obeys usage-guard.

## Gate kills (gate.py)

K1 H1 first line; K2 required sections (TL;DR/Findings/Divergences/Open
questions/Sources); K3 every finding bullet confidence-tagged
([CONFIRMED]/[SINGLE-SOURCE]/[CONTESTED]); K4 every finding bullet has a URL;
K5 >= min distinct source domains; K6 REFUTED claims listed under Killed
claims and absent from Findings; K7 degraded runs must print DEGRADED.
Scope note: reports are not copy-facing text; the no-em-dash rule is
intentionally not a gate check.

## Verify

```bash
bash run_research.sh --dry-run --question "test"          # plumbing, no LLM
python3 gate.py out/<slug>/report.md out/<slug>/04-verdicts.jsonl \
        out/<slug>/meta.json 3                            # re-gate any run
ls out/<slug>/          # 01-angles 02-sweep-{web,pplx} 03-claims 04-verdicts report.md gate.result
```

Smoke run (executed 2026-07-12, --fast): `out/2026-07-12-llm-agent-eval-harnesses/`.

## Relationship to existing pieces

- `research-agent/` (SHA creative research, external-only, single claude pass)
  stays as-is; this is the generic, verification-hardened harness. If it earns
  it, deepdive.sh can later delegate its LLM pass to this runner.
- Interactive deep research keeps using the built-in `deep-research` skill;
  this is the headless/cron equivalent with the same shape (fan-out -> claims
  -> adversarial verify -> cited synthesis) plus a deterministic gate.
