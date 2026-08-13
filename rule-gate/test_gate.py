#!/usr/bin/env python3
"""Unit tests for rule-gate's deterministic core (no tokens, no LLM)."""
import sys

from gate import tokens, rank, exit_code, build_prompt

FILES = [
    ("feedback_no_em_dashes.md", "Never use em dashes or en dashes in any copy."),
    ("feedback_always_link_clickup_task.md",
     "Always link the ClickUp task at the end of every reply. Give the tappable URL."),
    ("reference_ejam_bigquery.md", "The creative_dashboard table holds SHA spend revenue orders."),
]


def test_tokens_drop_stopwords():
    t = tokens("Always link the ClickUp task")
    assert "link" in t and "clickup" in t and "task" in t
    assert "the" not in t and "always" not in t


def test_rank_prefers_topical_overlap():
    r = rank("link the clickup task url in the reply", FILES, k=2)
    assert r, "expected at least one ranked file"
    assert r[0][0] == "feedback_always_link_clickup_task.md", r


def test_rank_empty_on_no_overlap():
    assert rank("quantum chromodynamics lattice", FILES) == []


def test_rank_respects_k():
    r = rank("clickup task dashboard copy dashes reply", FILES, k=1)
    assert len(r) == 1, r


def test_exit_code_strict_blocks_contradiction():
    v = [{"verdict": "safe"}, {"verdict": "contradiction"}]
    assert exit_code(v, strict=True) == 2
    assert exit_code(v, strict=False) == 0


def test_exit_code_clear_when_no_contradiction():
    v = [{"verdict": "safe"}, {"verdict": "redundant"}, {"verdict": "too_vague"}]
    assert exit_code(v, strict=True) == 0


def test_prompt_contains_rule_and_context():
    p = build_prompt("Always link the task", rank("clickup task", FILES))
    assert "Always link the task" in p
    assert "feedback_always_link_clickup_task.md" in p
    assert "—" not in p and "–" not in p  # no em/en dashes in our own scaffold


if __name__ == "__main__":
    fns = [g for n, g in sorted(globals().items()) if n.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"ok   {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
