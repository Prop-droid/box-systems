# rule-gate

Pre-promotion check for **general operating rules** headed into Tomas's Claude
memory canon (`~/.claude/projects/-home-tomas/memory/`).

The creative `keep_best_gate` blocks a promotion that raises the compliance
violation_rate. General rules have no such numeric metric, so this gate catches
the three ways a promoted rule rots the canon instead:

| verdict | meaning |
|---|---|
| `contradiction` | conflicts with an existing canon rule (names the file) |
| `redundant` | already stated in canon; no new signal (canon bloat) |
| `too_vague` | not specific/checkable enough to act on consistently |
| `safe` | genuinely new, actionable rule that fits |
| `unknown` | judge failed; advisory only, never blocks |

**How:** deterministic keyword-overlap retrieval over the memory corpus picks the
top-6 related files, then one `claude-max` judgment classifies the candidate
against them. Retrieval + the verdict->exit-code mapping are pure and unit-tested
(`test_gate.py`, no tokens).

## Use

```bash
# single rule
python3 gate.py --rule "Always link the ClickUp task at the end of a reply."

# annotate a proposals.jsonl (gates only kind==memory proposals)
python3 gate.py --proposals ../task-lessons/proposals.jsonl

# block auto-promotion on a contradiction
python3 gate.py --proposals proposals.jsonl --strict   # exit 2 on contradiction
```

Advisory by default (exit 0 always) so a synth run never silently drops
proposals. `--strict` makes a `contradiction` exit 2 for a caller that wants to
hard-gate auto-promotion.

## Wired into

`task-lessons/run_lessons_synth.sh` appends a "Rule-gate verdicts" section to
`proposals.md` for any memory-target proposal, so Tomas sees contradiction/
redundancy flags at approve time. Best-effort: a gate failure never fails synth.

Tests: `python3 test_gate.py`. Not scheduled on its own; it rides the Tue 05:30
task-lessons synth.
