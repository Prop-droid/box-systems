# Agentic OS DESIGN.md — Senior-Architect Review

Reviewer pass, 2026-07-06. Source under review: `~/agentic-os/DESIGN.md` (v0.1, 2026-06-14).
Pressure-tested against the 2026-07-02 to 07-05 fable-window (40+ overnight headless tasks, 17/17 exit=0 across nights 2-4), the usage-guard build, the fable-resume watchdog, and the compliance-eval gate. Evidence cited inline as [source].

## Verdict (one paragraph)

The org SHAPE is right and largely already running: supervisor-not-swarm, build-on-what-we-own, ephemeral subagents, human-gate-outbound, one-department-first. What the doc gets wrong is the same thing the window spent four nights learning the hard way: it puts the reliability machinery (orchestration loop, retry, assembly, QA gate, memory recall) INSIDE LLM agents, when every reliability win of the window came from deterministic scripts doing the waiting and agents doing only judgment [fable-window-lessons L6]. The doc is a v0.1 org chart. The window already built the missing v1 substrate (driver.sh, usage-guard, fable-resume, compliance-eval, the verify pass). The correct move is not to build a bespoke "Creative Lead orchestrator" from this doc; it is to generalize the fable-window harness into the org's execution layer and hang the existing skills off it. Three decisions in the doc are now contradicted by measured evidence and must change before Phase 1 (below).

---

## 1. What holds (validated by the window, keep as-is)

- **Supervisor pattern over swarm (Principle 1).** The window ran a strict sequential driver over isolated one-shot subagents and never once wanted a self-organizing swarm. The instinct is correct and now has local proof, not just the cited industry stat.
- **Build on what we own, no LangGraph (Principle 2).** The entire window ran on Hermes + `claude -p` + the Workflow-tool fan-out + ~50 role-shaped skills, with zero framework adoption. The "formalize the org, do not migrate" thesis is vindicated. Do not reopen this.
- **The Workflow tool is the correct fan-out primitive** (used in the orchestration-flow example). It is correct precisely BECAUSE it runs subagents synchronously in-process, which is the only fan-out shape that survives a headless one-shot run (see breakage #1). Worth stating explicitly in the doc as the reason, not just the mechanism.
- **Ephemeral subagents by default, persistent only when always-on (Principle 5).** Matches exactly what the driver did: spin a worker per task in an isolated context, let it die. Keep.
- **Human gates on outbound + ship/edit/kill as the spirit of QA (Principle 3).** Right in spirit. The window sharpened the mechanic (see breakage #3 and change #2), but the gate-outbound stance held across 40+ tasks with zero unrecoverable writes [L8].
- **One department live before the next (Principle 4, roadmap).** The anti-over-build discipline is the doc's best instinct and the window's too. Do not fan out to five departments on paper.

## 2. What breaks at contact with reality

### B1. The "Creative Lead" as an LLM orchestrator is the exact failure mode the window killed
The flow ("Lead plans, fans out subagents, assembles, returns") describes an agent that dispatches work and then waits for it. In headless operation, which is the whole point of an always-on org on the box, that is precisely how tasks 07c and 07d died: they backgrounded work and awaited notifications/re-invocation that do not exist in `claude -p` [RULES rule 7; fable-window memory; L5]. It became the single most-repeated lesson of the window. The doc does not mention this constraint anywhere. An agent-owned orchestration loop is survivable ONLY if the entire fan-out completes synchronously inside one process inside the timeout via the Workflow tool. The doc should not describe the Lead as the loop owner at all.

### B2. Reliability machinery lives in agents; the window proved it must be deterministic
Routing, retry, assembly, resume, and the QA gate are all drawn as agent responsibilities (Hermes router + Creative Lead + QA subagent). Every reliability-shaped thing that actually held in the window was a script with constants at the top: driver.sh handled 16 retries over 8h and marked LIMIT-GAVE-UP cleanly; gen_driver made generation resumable and budget-safe; atria-weekly ships a deterministic python fallback so a report lands even when headless claude fails 3x [L6]. The doc has no driver, no resume semantics, no fallback-to-degraded-output, no budget ceiling that is enforced by code rather than agent goodwill. This is the highest-leverage gap.

### B3. Locked decision #2 is now false: the binding constraint is the usage window, not outbound actions
The doc says "cost is not the binding constraint; Max 5x; gate on OUTBOUND, not spend" and leaves "budget ceiling per autonomous run (TBD)." The window disproved this on night 1: a 23:00 start collided with an exhausted usage window and lost work until a morning rerun [fable-window memory]. It forced the usage-guard build the same week: a systemd timer that pauses background burn at 90% during 08:00-23:00 specifically to protect Tomas's daytime interactive budget [usage-guard memory]. An always-on org that fans out subagents liberally shares one 5h window (and the weekly cap) with Tomas's own interactive sessions and will starve them. "Gate on outbound, not spend" is exactly backwards for background autonomy. The TBD is the load-bearing hole.

### B4. The QA/Reviewer is vibe critique; the window proved eval-gates beat it
QA is drawn as "a subagent that checks each output against brand canon + compliance." The cleanest result of the window was that named kill-criteria and layered eval-gates beat exactly this move. Rewritten skills replaced "critique internally" with binary hard kills and won the A/B one-to-one (rerouted blood-sugar bait, corrected 58% to the 46% canon ceiling, dropped the absolute-calorie claim); the regex scorer alone could not separate good from bad, the signal came from gold-semantic + scorer-blind grep + human read layered on top; and the harness stayed trustworthy only because the scorer was pinned at precision=recall=1.0 [L2, L3, L4]. A single LLM reviewer "checking" is the weakest version of the gate the window already outgrew. compliance-scrub and compliance-eval already exist to do this deterministically.

### B5. "persist" agents cannot be persistent Claude processes
The type taxonomy lists Chief of Staff, EA, and Coach as "persist = always-on agent." There is no persistent Claude Code process on this box; a headless one-shot cannot stay resident and cannot self-resume [L5; fable-window memory]. Every "persistent" agent is really a systemd timer firing a deterministic wake-up that shells a one-shot `claude -p`, plus an external watchdog to relaunch a dead driver. The window had to build fable-resume for exactly this, and learned two non-obvious gotchas doing it (a tmux/child spawned from a oneshot service dies with the service cgroup, so you must detach via `systemd-run`; anchor the pgrep guard or stray command strings false-match) [fable-window memory]. The doc's "persist" type hides a scheduler + watchdog it does not budget for.

### B6. L1 canon "read on startup" is the weaker leg of the memory model
The memory table has every worker "read Shameless canon at runtime" from MEMORY.md/wiki. The one clean A/B of the window showed baked-in canon beats runtime memory recall: gold 20/20 vs 19/20, warn leakage 2 vs 7, number-baits taken 0 vs 3, and when memory reads were blocked the recall-dependent skill degraded to guesses in 8/14 outputs [L1]. The workers (shameless-script, clickup-task-creator) already bake canon in. The doc should treat memory as where agents DISCOVER canon, not load-bearing runtime recall at generation time.

### B7. No independent verify step, and QA is conflated with verify
The doc has one "QA/Reviewer" doing everything. The window ran a SEPARATE mechanical verify task every night and it caught real defects the authoring passes could not see: 4 of 7 fresh SKILL.md files had invalid YAML frontmatter; a later verify re-ran the scorer, re-diffed 133/133 memory-link parity, nft-parsed both rulesets, and git-apply-checked both patches [L7]. Content-QA (brand/compliance/taste) and mechanical-verify (does it parse, does the suite still pass, does the claimed fact hold) are different jobs. The doc needs both, as separate nodes, and neither should be the authoring session self-certifying.

### B8. Under-specified guardrails will be re-litigated every run
"Humans gate anything outbound" and "fan out only when needed" are the same class of rule as the window's "no em dashes in copy-facing text," which was left undefined and got re-argued in three ledger entries, flagged by both verify passes (~276 + 85 dashes), and escalated as an open question in two reports without ever resolving, because the rule was ambiguous, not the work [L9]. Any rule an autonomous agent must interpret gets interpreted differently every run. "Outbound" and "when needed" need explicit include/exclude lists before this org runs unattended.

## 3. The three highest-leverage changes

**Change 1 (structural): the orchestrator is a deterministic harness, not an LLM "Lead." Port the fable-window harness; do not build a new one.**
Replace the Creative-Lead-owns-the-loop model with a driver.sh-shaped substrate: sequential queue over per-task one-shot agents, `.done`-marker resume, limit-retry with LIMIT-GAVE-UP, degrade-to-worse-output fallback, a ledger per run, and a hard token-budget ceiling enforced in code. The "Lead reasoning" becomes ONE agent call inside that loop (the plan/decompose step), and fan-out happens via the Workflow tool synchronously in-process. This kills the 07c/07d failure mode structurally [L5, L6], and buys resume, observability, and budget-safety for free because the parts already exist and are proven. This is assembly, not R&D.

**Change 2 (quality): the QA node is an eval-gate plus a separate mechanical-verify node, not a reviewer agent.**
Wire the gate as: compliance-scrub + a named binary kill-criteria checklist + the compliance-eval scorer held at 1.0/1.0, with an LLM call reserved only for the semantic-read layer that regex cannot cover [L2, L3, L4]. Add a distinct verify node that parses/tests/diffs the mechanics and never rewrites content [L7]. Split "QA/Reviewer 🟡" into QA-content and Verify-mechanics. This is the difference between a gate that catches defects and one that vibe-approves them.

**Change 3 (economics): reopen locked-decision #2. The usage window is the binding constraint; wire the org to usage-guard, off-peak scheduling, and a real per-run budget.**
Delete "budget: TBD." Set a hard per-run token ceiling. Make every background/fan-out job respect the usage-guard PAUSE flags and schedule heavy fan-out off-peak so it does not eat Tomas's 08:00-23:00 interactive cap [usage-guard memory; night-1 collision]. Add fable-resume-style liveness so a limit-paused or crashed queue relaunches at reset instead of dying. Keep the outbound human-gate, but recognize spend/cap is the real constraint for always-on autonomy, not outbound actions.

(Honorable mentions, cheaper: bake canon into worker skills rather than runtime memory reads [L1, B6]; redefine "persist" agents as timer + one-shot + watchdog, not resident processes [B5]; give "outbound" and "fan out when needed" include/exclude lists [L9, B8]. Fold these into the changes above.)

## 4. Build-order recommendation

The doc's Phase 1 (Creative department first) is still the right first department. But insert a Phase 0 and reshape Phase 1 around the harness, because the substrate is what the window proved and it is 80% built already.

- **Phase 0 (new, days not weeks, mostly packaging): generalize the fable-window harness into the org execution substrate.** driver + `.done` resume + limit-retry + ledger + degrade-fallback + usage-guard integration + fable-resume liveness + a mechanical-verify step. All of these exist as proven parts from this week; the work is extracting them from `~/fable-window` into a reusable `~/agentic-os` runner. Ship nothing agentic until the substrate can run, resume, budget-cap, and verify a trivial queue end to end. Verify target: a throwaway 3-task queue survives a forced kill mid-run and a simulated limit-pause, and lands a ledger + verify pass.
- **Phase 1 (Creative department, reshaped): creative jobs as a queue through that substrate, QA = the eval-gate from Change 2.** Copywriter/Scriptwriter/Researcher/Analyst are agent calls with canon baked into their skills; the Lead is the plan step, not the loop. Prove it on real briefs with ship/edit/kill and the compliance-eval gate before adding a second department. This is the money work and most pieces exist.
- **Phase 2 (EA): scope it as draft-to-staging with baseline discipline**, not "messages/calendar autonomy." Every EA write goes to a staging artifact with a git/hash baseline immediately before and after, handed off as a risk-ordered apply checklist with embedded backup commands [L8]. Keep locked-decision #4 (draft-and-approve only); add the baseline mechanic it is missing.
- **Defer Developer/QA-loop (Phase 3) and Coach (Phase 4) exactly as the doc says.** No change; the anti-over-build call is correct.

**Do first:** Phase 0 substrate extraction. **Do not do:** build a bespoke Creative-Lead orchestrator from the v0.1 doc. **Blocking risk if skipped:** an agent-owned loop that backgrounds-and-waits, which is the one failure mode the window most conclusively ruled out.

---
Reviewer note: this is a review of a design doc, not a working system; it changes no live state. All claims trace to files on disk in `~/fable-window` and the memory dir, cited inline.
