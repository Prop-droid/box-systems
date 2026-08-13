#!/usr/bin/env python3
"""Unit tests for telemetry's error-attribution and delta core (no transcripts)."""
import json
import os
import sys
import tempfile
from collections import Counter

import telemetry


def _write(path, entries):
    with open(path, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


def test_scan_attributes_errors_by_tool_name():
    entries = [
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "t1", "name": "Bash", "input": {}},
            {"type": "tool_use", "id": "t2", "name": "Skill", "input": {"skill": "atria"}},
        ]}},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t1", "is_error": True},
        ]}},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t2"},
        ]}},
    ]
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "s.jsonl")
        _write(p, entries)
        tools, tool_err, skills = Counter(), Counter(), Counter()
        telemetry.scan_file(p, tools, tool_err, skills)
    assert tools["Bash"] == 1 and tools["Skill"] == 1, tools
    assert tool_err["Bash"] == 1, tool_err
    assert tool_err.get("Skill", 0) == 0, tool_err
    assert skills["atria"] == 1, skills


def test_unknown_tool_result_id_falls_back():
    entries = [
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "ghost", "is_error": True},
        ]}},
    ]
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "s.jsonl")
        _write(p, entries)
        tools, tool_err, skills = Counter(), Counter(), Counter()
        telemetry.scan_file(p, tools, tool_err, skills)
    assert tool_err["?"] == 1, tool_err


def test_delta_computes_per_skill_change():
    cur = {"skills": Counter({"a": 5, "b": 2})}
    prev = {"skills": {"a": 3}}
    d = telemetry.delta(cur, prev, "skills")
    assert d["a"] == 2 and d["b"] == 2, d


def test_render_lists_never_used(monkeypatch=None):
    data = {"tools": Counter({"Bash": 3}), "tool_err": Counter(),
            "skills": Counter({"atria": 1}), "files": 1}
    orig = telemetry.catalog
    telemetry.catalog = lambda: {"atria", "ffmpeg-analyse-video", "council"}
    try:
        out = telemetry.render(data, 30, {})
    finally:
        telemetry.catalog = orig
    assert "council" in out and "ffmpeg-analyse-video" in out
    assert "Never-used local skills (2 of 3)" in out, out


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
    print(f"\n{len(fns)-failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
