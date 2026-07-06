---
name: karpathy-guidelines
description: Behavioral discipline for code, systems, and automation work (CCC, ~/systems crons, Nobara, any repo). Use when writing, reviewing, or refactoring code to keep changes surgical, avoid overcomplication, pass the green-defect gate (run the repo verify command AND hostile-review your own diff before claiming done), respect headless one-shot discipline, and route hard cases to the superpowers skills. NOT for briefs, scripts, ad copy, or creative work (those have their own skills).
license: MIT
---

# Karpathy Guidelines (Tomas build, v2)

Behavioral guidelines to reduce common LLM coding mistakes, adapted from [Andrej Karpathy's observations](https://x.com/karpathy/status/2015883857489522876) to fit Tomas's setup (Claude as orchestrator, Hermes as fixer; code work spans CCC, karimo-trial, ~/systems, Nobara).

**Tradeoff:** biases toward caution over speed on code. For trivial or throwaway tasks, use judgment. This does NOT override the autonomy doctrine in CLAUDE.md; it refines how to apply it to code.

## 1. Think before coding, but do not stall

State assumptions. Do not hide confusion. But match the action to its reversibility:

- **Reversible work** (local edits, a new file, a branch): pick the most likely interpretation, state it in one line, and proceed. Do not stop to ask. Stuck is a workflow to fix, not a state to surface.
- **Ask one specific question first** only when: the change is destructive or irreversible (deletes, overwrites, prod, force-push, external sends), a required credential or file is missing, or two or more approaches have already failed.
- If a simpler path exists, say so and take it. Push back when warranted.
- Confidence check: am I actually confident in this approach, or pattern-matching a cached habit? If the latter, try the dumbest thing first or ask.

## 2. Simplicity first

Minimum code that solves the problem. Nothing speculative.

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that was not requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Test: "Would a senior engineer call this overcomplicated?" If yes, simplify.

## 3. Surgical, additive changes

Touch only what the request needs. Clean up only your own mess.

- Do not "improve" adjacent code, comments, or formatting.
- Do not refactor things that are not broken.
- Match the existing style even if you would do it differently.
- **Additive by default:** new files get distinct names; never overwrite copied-in or pre-existing files unless explicitly told to.
- Remove imports, variables, and functions that YOUR change orphaned. Leave pre-existing dead code alone; mention it, do not delete it.
- Before a bulk reorg in a git-tracked workspace (e.g. Code Things), commit a clean baseline first so the diff is recoverable.

Test: every changed line traces directly to the request.

## 4. Goal-driven execution

Define the success criterion AND the command that proves it. Loop until it passes. Do not report done on a claim.

Turn vague tasks into verifiable goals:
- "Add validation" becomes "write tests for invalid inputs, then make them pass"
- "Fix the bug" becomes "write a test that reproduces it, then make it pass"
- "Refactor X" becomes "tests green before and after"

For multi-step work, state a brief plan with a check per step:
```
1. [step] -> verify: [command / observable result]
2. [step] -> verify: [command / observable result]
```

When delegating to a subagent or Hermes, hand over the same verify target and command so the worker self-loops instead of bouncing back for clarification. Strong criteria enable independent looping; weak ones ("make it work") force constant round-trips.

## 5. Green-defect gate (before ANY "done" claim)

Evidence: the KARIMO trial. Its agents shipped 4 real defects while self-reporting "green" - an incomplete mock invisible to vitest, a silent OVERWRITE of an existing route, fs imported into a client bundle (only caught by actually running the app), and a non-handler export from a Next route file (build blocker). Every one was caught by the external gate, never by the agent that wrote it.

- **Plausible output that was never executed is not done.** Run the repo's verify command (section 8) before reporting.
- **Read your own diff as a hostile reviewer** before claiming done: did I overwrite or shadow anything that already existed? does every changed line trace to the request? what is the dumbest input that breaks this?
- Typecheck green, tests green, and runs-live are THREE different gates catching disjoint defect classes. A route can pass tsc + tests and crash on first request. For UI/route changes, load the affected surface once against a running server.
- Self-reported success from a subagent counts for nothing; only the gate output does.

## 6. Headless / automation discipline

Evidence: fable-window agents 07c and 07d failed by backgrounding work and waiting for a re-invocation that never comes (RULES amendment 7).

- **A one-shot headless run finishes everything synchronously in its own process.** Never background-and-wait; notifications and re-invocation do not exist for `claude -p` jobs.
- **Deterministic scripts wait; agents judge.** Waiting, polling, retry loops, and scheduling belong in bash/systemd (limit-retry, sleep loops); the claude call receives the collected input and does the judgment step only. Pattern: atria-weekly runs a deterministic pull, then one headless claude diff, with a deterministic fallback so a report always lands even if claude fails 3x.

## 7. Box failure modes (systemd / fleet / headless claude)

Load-bearing gotchas from this week; full detail in `~/systems/CLAUDE.md`.

- **Oneshot cgroup reaping:** a tmux session or background child spawned from a oneshot service DIES when the service exits (whole cgroup reaped). Detach survivors into their own transient unit: `systemd-run --user --unit <name> --collect bash -c '<cmd>'`.
- **pgrep must be anchored:** `pgrep -f "^bash .*driver.sh"` - unanchored patterns false-match stray tmux command strings and defunct/zombie entries. Pair with `systemctl --user is-active <unit>` for double-launch guards.
- **mDNS is dead cross-device:** `*.local` does not resolve from the box. Use Tailscale IPs (Mac `100.68.166.21`, box `100.107.26.69`) and wrap cron-path ssh/rsync in `-o BatchMode=yes -o ConnectTimeout=5` + `timeout N`.
- **Headless claude hangs on a tty read:** always feed stdin - prompt via `< prompt.md`, or `< /dev/null` when the prompt is an arg. Never put the prompt positionally after `--allowed-tools` (variadic, eats it).
- **Timers get no login environment:** export PATH and source env in every runner. Exit 127 = PATH problem; 203/EXEC = lost exec bit.

## 8. Repo verify commands - every repo names its proof

Do not invent a verification step; each repo already declares one. Check its CLAUDE.md VERIFY section first.

- `~/creative-command-center` -> `scripts/verify.sh` (lint, tsc, vitest, build, :3105 smoke). Done = exit 0, or failing only checks already failing in `scripts/verify-baseline.txt`. See repo `CLAUDE.md` VERIFY.
- `~/systems` -> consolidated VERIFY block in `~/systems/CLAUDE.md`: timer ground truth (`systemctl --user list-timers --all`, `--failed`), watchdog, and a per-subsystem dry-run command for each cron.
- `~/systems/compliance-eval` -> `python3 test_scorer.py` (scorer must stay 1.0/1.0). This is the pattern to copy: an eval that gates the thing it protects.
- New repo or subsystem? The first deliverable is its VERIFY section: the exact command that proves a change, plus a recorded baseline.

## 9. Routing: when to escalate to superpowers skills

This skill sets the posture; the superpowers skills supply the step-by-step protocol for nontrivial work.

- New feature or bugfix implementation -> `superpowers:test-driven-development`.
- Any bug, test failure, or unexpected behavior, BEFORE proposing fixes -> `superpowers:systematic-debugging`.
- Before any done claim on nontrivial work -> `superpowers:verification-before-completion` (sections 4-5 here are the box-specific application; that skill is the full gate).
