# Applied self-improve proposals

(append-only; each entry = date, proposal id + one-liner, proof)

## 2026-08-13 — P1 (variant): SessionStart hook no longer drops daily log + budget note
Source: token-audit 2026-08-01. P1 proposed raising the 6,000-char cap to 12,000;
applied a better fix instead — section budgeting — so always-on context stays flat
at 6,000 rather than growing (which the same audit flagged as the problem). The
index preview now gets only the char budget left after the fixed sections, so the
daily log and Context Budget note are always kept.
Proof: `hooks/session-start.py` build_context() reserves fixed sections first;
verified all 4 sections present at exactly 6,000 chars, no tail truncation.
File: ~/.tools/claude-memory-compiler/hooks/session-start.py (no VCS in that dir;
rollback snapshot: hooks/session-start.py.applied-2026-08-13).
