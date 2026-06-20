#!/usr/bin/env python3
"""
Keep-best gate for feedback promotion (research priority #2).

Problem it solves: feedback-synth promotes a pattern into canon when it recurs >=3x.
Frequency is not evidence of *improvement*. The self-improving-agents research found
~49% of un-gated "optimizations" score BELOW baseline — so a promoted rule can quietly
make generation worse. This gate blocks promotion of any skill-rule that REGRESSES the
one hard metric we have today: the compliance violation_rate from ~/systems/compliance-eval.

What it does NOT do: judge creative quality (no hard metric for that yet — that's the
quality-eval, research priority #4). This is a no-harm guardrail, not a quality oracle.
A rule that is compliance-neutral passes the gate; it does not certify the rule is good.

How: re-generate scripts with the candidate rule injected (compliance-eval --rule) on a
prompt subset, and compare violation outcomes against the stored reference baseline on the
SAME prompts. Any item that newly violates => REGRESSION => BLOCK.

Usage:
    python3 keep_best_gate.py --rule "Open on the founder confession within 3 seconds." \
        --reference baseline_20260620 --limit 5
Exit: 0 = promote (no regression), 2 = block (regression), 1 = error.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

CEVAL = Path.home() / "systems" / "compliance-eval"


def decide(reference_results, candidate_results):
    """Pure decision function. Inputs are lists of {id, passed, hard} dicts.

    Returns a verdict dict. BLOCK if any item passed in reference but fails with the
    candidate rule (a newly-introduced violation). Items absent from one side are skipped.
    """
    ref = {r["id"]: r for r in reference_results if "passed" in r}
    regressions, fixes, compared = [], [], 0
    for c in candidate_results:
        if "passed" not in c:
            continue
        r = ref.get(c["id"])
        if r is None:
            continue
        compared += 1
        if r["passed"] and not c["passed"]:
            regressions.append({"id": c["id"], "now_violates": c.get("hard", [])})
        elif not r["passed"] and c["passed"]:
            fixes.append(c["id"])
    ref_vr = _violation_rate([ref[c["id"]] for c in candidate_results
                              if "passed" in c and c["id"] in ref])
    cand_vr = _violation_rate([c for c in candidate_results if "passed" in c and c["id"] in ref])
    decision = "block" if regressions else "promote"
    return {
        "decision": decision,
        "compared": compared,
        "reference_violation_rate": ref_vr,
        "candidate_violation_rate": cand_vr,
        "regressions": regressions,
        "fixes": fixes,
    }


def _violation_rate(results):
    scored = [r for r in results if "passed" in r]
    if not scored:
        return None
    return round(1 - sum(1 for r in scored if r["passed"]) / len(scored), 3)


def _run_candidate(rule, limit, gen_cmd):
    """Run the compliance harness with the candidate rule; return its results list."""
    label = "_gate_candidate"
    cmd = [sys.executable, str(CEVAL / "run_eval.py"), "--mode", "generate",
           "--rule", rule, "--save", label]
    if limit:
        cmd += ["--limit", str(limit)]
    if gen_cmd:
        cmd += ["--gen-cmd", gen_cmd]
    proc = subprocess.run(cmd, cwd=str(CEVAL), capture_output=True, text=True)
    sys.stderr.write(proc.stdout)
    if proc.returncode not in (0, 1):  # 1 = harness saw a violation/regression; still valid data
        raise RuntimeError(f"harness failed ({proc.returncode}): {proc.stderr[:300]}")
    report = json.loads((CEVAL / "baselines" / f"{label}.json").read_text())
    (CEVAL / "baselines" / f"{label}.json").unlink(missing_ok=True)
    return report["results"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rule", required=True, help="candidate feedback rule to gate")
    ap.add_argument("--reference", default="baseline_20260620",
                    help="reference baseline label in compliance-eval/baselines/")
    ap.add_argument("--limit", type=int, default=5, help="prompt subset size (speed/cost)")
    ap.add_argument("--gen-cmd")
    args = ap.parse_args()

    ref_path = CEVAL / "baselines" / f"{args.reference}.json"
    if not ref_path.exists():
        print(f"ERROR: reference baseline not found: {ref_path}", file=sys.stderr)
        return 1
    reference_results = json.loads(ref_path.read_text())["results"]

    candidate_results = _run_candidate(args.rule, args.limit, args.gen_cmd)
    verdict = decide(reference_results, candidate_results)

    print("\n" + "=" * 60)
    print(f"KEEP-BEST GATE  rule: {args.rule!r}")
    print(f"  compared {verdict['compared']} items   "
          f"ref_vr={verdict['reference_violation_rate']}  "
          f"cand_vr={verdict['candidate_violation_rate']}")
    for reg in verdict["regressions"]:
        print(f"  REGRESSION {reg['id']}: now violates {reg['now_violates']}")
    for fid in verdict["fixes"]:
        print(f"  fix {fid}")
    print(f"  DECISION: {verdict['decision'].upper()}"
          + ("  — safe to promote" if verdict["decision"] == "promote"
             else "  — DO NOT promote, rule introduces a compliance regression"))
    print("=" * 60)
    return 0 if verdict["decision"] == "promote" else 2


if __name__ == "__main__":
    sys.exit(main())
