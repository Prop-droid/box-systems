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
