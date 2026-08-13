# self-improve

The last mile of the box's self-learning loop. The proposal GENERATORS already
existed (weekly agents: retro/skill-garden/memory-hygiene; task-lessons synth;
creative-feedback synth; monthly consolidation/token-audit) but their reports
died unread in report directories - run_agents.sh ended in a Mac-era osascript
notification that is a no-op on this headless box. This job closes the loop.

## Flow

1. Tue 06:30 (`self-improve-digest.timer`, after Tue 05:00/05:30 synths; agents
   ran Sun 05:30): `run_digest.sh` gathers the newest report from every source,
   distills them via claude-max into ONE ranked `pending.md` (max 10 proposals,
   each with evidence + an exact apply action), posts count + top 3 to Discord
   #ops-log.
2. Tomas replies in #dev: `self-improve: apply P2, P4` (or `skip P3`).
3. The dispatched Claude session reads `pending.md`, applies exactly the named
   items - baseline commit first when touching ~/systems or skills; memory edits
   get a MEMORY.md index line - then moves them into `applied.md` with the date
   and replies with proof.

## Guardrails

- Digest NEVER applies anything; promotion is human-gated in Discord.
- Proposals that change how a generative creative skill writes copy are routed
  OUT to the creative-feedback promote path (keep_best_gate) - that loop has an
  eval gate, this one does not.
- LLM failure degrades to a Discord pointer at the raw reports, never silence.
- Old pending lists are archived to `archive/` before overwrite; unapplied items
  resurface next week only if their source agent still reports them (prevents
  zombie proposals nobody wants).

## Files

- `run_digest.sh`   - entry point (manual run is safe; burns window tokens, posts to Discord)
- `digest_prompt.md`- synthesis instructions + output contract
- `pending.md`      - current week's ranked proposals (the thing Tomas gates)
- `applied.md`      - append-only log of applied items
- `archive/`        - prior pending lists
