#!/usr/bin/env python3
"""
Eval harness runner for the email-copy skill.

Adapted from ~/systems/compliance-eval/run_eval.py per artifacts/eval-factory.TEMPLATE.md;
only the docstring and the skill under test differ. Pipeline:

  bait prompts --(generate or load)--> emails --> scorer --> report --> baseline diff

Modes:
  --mode fixtures           Score the gold/ fixtures (free, proves the pipeline end-to-end)
  --mode score-dir DIR      Score every *.txt in DIR
  --mode generate           Run the generator on each prompt in prompts.jsonl, then score
                            (costs tokens — uses GEN_CMD, default: claude -p)

Options:
  --save LABEL              Write the run to baselines/LABEL.json
  --compare LABEL           Diff this run against baselines/LABEL.json (regressions/fixes)
  --limit N                 Only process the first N items (smoke test)
  --save-scripts            In generate mode, also save generated emails under runs/LABEL/
  --gen-cmd "..."           Override generator command; {prompt} is substituted

Exit code: 0 if no regressions vs --compare baseline (or no baseline given) AND no items
errored; 1 if there are regressions or generation errors. (A nonzero violation rate alone
does not fail the run — it's the metric you track over time.)
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from scorer import Scorer

HERE = Path(__file__).parent
DEFAULT_GEN_CMD = 'claude -p {prompt}'


def load_prompts():
    items = []
    for line in (HERE / "prompts.jsonl").read_text().splitlines():
        line = line.strip()
        if line:
            items.append(json.loads(line))
    return items


def generate(prompt_text, gen_cmd):
    """Run the generator command, returning (email_text, error_or_None)."""
    cmd = gen_cmd.replace("{prompt}", subprocess.list2cmdline([prompt_text]))
    try:
        out = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return "", "timeout"
    if out.returncode != 0:
        return out.stdout, f"gen_exit_{out.returncode}: {out.stderr.strip()[:200]}"
    return out.stdout, None


def build_report(items, mode, scorer):
    results = []
    total_hard = total_warn = passed = errors = 0
    for it in items:
        res = scorer.score(it["text"]) if it.get("text") is not None else None
        rec = {"id": it["id"], "label": it.get("label", it["id"])}
        if it.get("error"):
            rec["error"] = it["error"]
            errors += 1
        if res is not None:
            rec["passed"] = res.passed
            rec["hard"] = sorted({f.rule_id for f in res.hard})
            rec["warn"] = sorted({f.rule_id for f in res.warn})
            rec["hard_spans"] = [f.match for f in res.hard]
            total_hard += res.hard_count
            total_warn += res.warn_count
            passed += int(res.passed)
        results.append(rec)
    n = len(items)
    scored = [r for r in results if "passed" in r]
    report = {
        "mode": mode,
        "policy_version": scorer.policy_version,
        "summary": {
            "items": n,
            "scored": len(scored),
            "errors": errors,
            "passed": passed,
            "pass_rate": round(passed / len(scored), 3) if scored else None,
            "violation_rate": round(1 - passed / len(scored), 3) if scored else None,
            "total_hard": total_hard,
            "total_warn": total_warn,
        },
        "results": results,
    }
    return report


def gather_items(args, scorer):
    """Return list of {id, label, text, error?}."""
    if args.mode == "fixtures":
        items = []
        for p in sorted((HERE / "gold").glob("*.txt")):
            items.append({"id": p.stem, "label": p.name, "text": p.read_text()})
        return items[: args.limit] if args.limit else items

    if args.mode == "score-dir":
        d = Path(args.dir)
        items = []
        for p in sorted(d.glob("*.txt")):
            items.append({"id": p.stem, "label": p.name, "text": p.read_text()})
        return items[: args.limit] if args.limit else items

    if args.mode == "generate":
        prompts = load_prompts()
        if args.limit:
            prompts = prompts[: args.limit]
        gen_cmd = args.gen_cmd or DEFAULT_GEN_CMD
        rule = args.rule  # candidate feedback rule injected into every prompt (keep-best gate)
        save_dir = None
        if args.save_scripts:
            label = args.save or "adhoc"
            save_dir = HERE / "runs" / label
            save_dir.mkdir(parents=True, exist_ok=True)
        items = []
        for pr in prompts:
            print(f"  generating {pr['id']} ({pr.get('angle','')})...", file=sys.stderr)
            prompt_text = pr["prompt"]
            if rule:
                prompt_text += f"\n\nAlso apply this guidance: {rule}"
            text, err = generate(prompt_text, gen_cmd)
            if save_dir and text:
                (save_dir / f"{pr['id']}.txt").write_text(text)
            items.append({"id": pr["id"], "label": f"{pr['id']} {pr.get('angle','')}",
                          "text": text if not err else None, "error": err})
        return items

    raise SystemExit(f"unknown mode: {args.mode}")


def diff_against_baseline(report, label):
    path = HERE / "baselines" / f"{label}.json"
    if not path.exists():
        print(f"  (no baseline '{label}' to compare against)")
        return []
    base = json.loads(path.read_text())
    base_pass = {r["id"]: r.get("passed") for r in base["results"] if "passed" in r}
    regressions, fixes = [], []
    for r in report["results"]:
        if "passed" not in r:
            continue
        was = base_pass.get(r["id"])
        if was is True and r["passed"] is False:
            regressions.append((r["id"], r["hard"]))
        elif was is False and r["passed"] is True:
            fixes.append(r["id"])
    print(f"\n  vs baseline '{label}':  regressions={len(regressions)}  fixes={len(fixes)}")
    for rid, hard in regressions:
        print(f"    REGRESSION {rid}: now violates {hard}")
    for rid in fixes:
        print(f"    fixed {rid}")
    return regressions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="fixtures", choices=["fixtures", "score-dir", "generate"])
    ap.add_argument("--dir")
    ap.add_argument("--save")
    ap.add_argument("--compare")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--save-scripts", action="store_true")
    ap.add_argument("--gen-cmd")
    ap.add_argument("--rule", help="candidate feedback rule injected into every prompt (keep-best gate)")
    args = ap.parse_args()

    scorer = Scorer()
    items = gather_items(args, scorer)
    report = build_report(items, args.mode, scorer)

    s = report["summary"]
    print(f"\nMode: {args.mode}   policy {report['policy_version']}")
    print(f"Items {s['items']} | scored {s['scored']} | errors {s['errors']} | "
          f"pass {s['passed']}/{s['scored']} | violation_rate {s['violation_rate']} | "
          f"HARD {s['total_hard']} WARN {s['total_warn']}")
    print("-" * 64)
    for r in report["results"]:
        if "error" in r and "passed" not in r:
            print(f"  {r['label']:34s} ERROR: {r['error']}")
            continue
        mark = "PASS" if r["passed"] else "FAIL"
        extra = ""
        if not r["passed"]:
            extra = f"  hard={r['hard']} {r['hard_spans']}"
        elif r["warn"]:
            extra = f"  warn={r['warn']}"
        print(f"  {r['label']:34s} {mark}{extra}")

    if args.save:
        out = HERE / "baselines" / f"{args.save}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2))
        print(f"\n  saved baseline -> {out.relative_to(HERE)}")

    regressions = diff_against_baseline(report, args.compare) if args.compare else []

    failed = bool(regressions) or s["errors"] > 0
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
