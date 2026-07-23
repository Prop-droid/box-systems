# needle-test — brand-canon grounding regression suite (snapshot)

**Canonical live dir: `~/brain/systems/needle-test/`** — run it there (run.py
resolves the wiki path relative to its own location). This copy exists so the
harness is version-controlled in box-systems, same pattern as fable-window/.
Re-sync after editing the live dir: `cp ~/brain/systems/needle-test/{run.py,run_brain.py,needles.yaml} ~/systems/needle-test/`

- `run.py` — needles vs the WIKI (headless claude, Read/Grep/Glob only).
- `run_brain.py` — needles vs the eJam Company Brain MCP (added 2026-07-23):
  headless runs allowed only mcp__brain__* tools, cwd outside ~/brain, so it
  measures what a teammate's AI grounding on the brain actually retrieves.
  First full run 2026-07-23: 26/26 PASS, zero forbidden fragments.
- `needles.yaml` — shared needle set. Scoring: all `expected` fragments must
  appear (`a|b` = alternatives); any `forbidden` = auto-FAIL. Add a needle per
  canon change.

## guard.py (added 2026-07-23, post-meltdown)
Shared box-safety layer for both runners: pins each headless run's MCP config
to exactly the servers it needs (`--strict-mcp-config` ALONE is a no-op — an
explicit `--mcp-config` is required or all ~/.claude.json servers boot per
needle), blocks spawning above loadavg 3.0, and checkpoints every answered
needle to a daily rows-*.jsonl so killed runs resume. Workers capped at 2.
