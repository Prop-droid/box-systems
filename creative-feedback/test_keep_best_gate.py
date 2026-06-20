#!/usr/bin/env python3
"""Unit tests for the keep-best gate decision logic (no generation, no tokens)."""
import sys

from keep_best_gate import decide


def _r(id_, passed, hard=None):
    return {"id": id_, "passed": passed, "hard": hard or []}


def test_promote_when_no_regression():
    ref = [_r("p01", True), _r("p02", True), _r("p03", False, ["fat_burn"])]
    cand = [_r("p01", True), _r("p02", True), _r("p03", False, ["fat_burn"])]
    v = decide(ref, cand)
    assert v["decision"] == "promote", v
    assert v["regressions"] == [], v
    assert v["compared"] == 3, v


def test_block_when_rule_introduces_violation():
    ref = [_r("p01", True), _r("p02", True)]
    cand = [_r("p01", True), _r("p02", False, ["false_clean_label"])]
    v = decide(ref, cand)
    assert v["decision"] == "block", v
    assert v["regressions"] == [{"id": "p02", "now_violates": ["false_clean_label"]}], v


def test_promote_records_a_fix_but_does_not_require_one():
    ref = [_r("p01", False, ["detox_cleanse"]), _r("p02", True)]
    cand = [_r("p01", True), _r("p02", True)]
    v = decide(ref, cand)
    assert v["decision"] == "promote", v
    assert v["fixes"] == ["p01"], v
    assert v["candidate_violation_rate"] == 0.0, v
    assert v["reference_violation_rate"] == 0.5, v


def test_unmatched_ids_are_skipped():
    ref = [_r("p01", True)]
    cand = [_r("p99", False, ["x"])]   # id not in reference -> not counted
    v = decide(ref, cand)
    assert v["compared"] == 0, v
    assert v["decision"] == "promote", v


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ok   {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
