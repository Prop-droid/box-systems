# karpathy-guidelines v2 - CHANGES (2026-07-06)

Replacement for `~/.claude/skills/karpathy-guidelines/SKILL.md`. NOT installed (RULES #2); artifact only.

## What changed and why

1. **New section 5, green-defect gate.** KARIMO trial evidence (memory `project_karimo_trial`): agents shipped 4 real defects while self-reporting green (tsc-invisible mock, silent route overwrite, fs-in-client-bundle, non-handler route export), all caught by the external gate. Codifies: run the repo verify command + hostile self-review of the diff; typecheck/tests/runs-live are three disjoint gates; subagent self-reports count for nothing. The old "anti-green-defect" one-liner in section 2 was folded into this real gate.
2. **New section 6, headless/automation discipline.** From fable-window 07c/07d failures (RULES amendment 7) and the atria-weekly runner: one-shot agents finish synchronously, never background-and-wait; deterministic scripts wait/retry, agents only judge.
3. **New section 7, box failure modes.** This week's systemd/fleet gotchas distilled from `~/systems/CLAUDE.md` (task 41): oneshot cgroup reaping (systemd-run --collect escape), anchored pgrep vs zombie/tmux false-matches, mDNS dead cross-device (Tailscale IPs), stdin hang on headless claude, no-login-env timers (127/203 decode).
4. **New section 8, repo-verify table.** Points at the proof commands tasks 40/41 created (CCC `scripts/verify.sh` + baseline, `~/systems/CLAUDE.md` VERIFY block) plus `compliance-eval/test_scorer.py` as the pattern; rule that a new repo's first deliverable is its VERIFY section.
5. **New section 9, superpowers routing.** TDD for features, systematic-debugging for bugs, verification-before-completion before any done claim; positions this skill as posture, superpowers as protocol.
6. **Frontmatter description updated** to name the green-defect gate, headless discipline, and superpowers routing so the skill fires on those tasks. Name unchanged.
7. **Sections 1-4 kept intact** (one line trimmed from each of 2 and 4 for budget). Length: 64 -> 105 lines, under the 2x cap.
