#!/usr/bin/env python3
"""
Validate the email-copy SCORER against the labeled gold set (verify the verifier).

Identical logic to ~/systems/compliance-eval/test_scorer.py: precision/recall of
HARD-violation detection at the (fixture, rule_id) level must both be 1.0, and every
required/forbidden WARN must behave. On a small curated gold set any miss or false-flag
is a real bug to fix, not noise to tolerate.

Run:  python3 test_scorer.py
Exit: 0 = scorer trustworthy, 1 = scorer has a gap (do NOT trust it to gate generation).
"""
import json
import sys
from pathlib import Path

from scorer import Scorer

HERE = Path(__file__).parent
GOLD_DIR = HERE / "gold"
LABELS = json.loads((HERE / "gold_labels.json").read_text())


def main():
    s = Scorer()
    tp = fp = fn = 0
    warn_misses = []
    rows = []

    for fname, label in LABELS.items():
        if fname.startswith("_"):
            continue
        text = (GOLD_DIR / fname).read_text()
        res = s.score(text)
        pred = {f.rule_id for f in res.hard}
        exp = set(label["hard"])
        tp += len(pred & exp)
        fp += len(pred - exp)
        fn += len(exp - pred)

        pred_warn = {f.rule_id for f in res.warn}
        for w in label.get("warn_includes", []):
            if w not in pred_warn:
                warn_misses.append((fname, w, "missing"))
        for w in label.get("warn_excludes", []):
            if w in pred_warn:
                warn_misses.append((fname, w, "false-warn"))

        status = "ok" if pred == exp else "MISMATCH"
        if pred != exp:
            status += f"  +{sorted(pred - exp)} -{sorted(exp - pred)}"
        rows.append((fname, status))

    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0

    print(f"Scorer policy version: {s.policy_version}")
    print(f"Fixtures: {len([k for k in LABELS if not k.startswith('_')])}")
    print("-" * 60)
    for fname, status in rows:
        print(f"  {fname:32s} {status}")
    print("-" * 60)
    print(f"HARD detection  precision={precision:.3f}  recall={recall:.3f}  (TP={tp} FP={fp} FN={fn})")
    if warn_misses:
        print(f"WARN misses: {warn_misses}")

    ok = (precision == 1.0 and recall == 1.0 and not warn_misses)
    print("RESULT:", "PASS — scorer is trustworthy" if ok else "FAIL — fix the scorer/policy before trusting it")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
