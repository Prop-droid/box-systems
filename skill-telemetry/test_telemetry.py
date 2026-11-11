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


def test_scan_counts_direct_skill_md_reads():
    entries = [
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "r1", "name": "Read",
             "input": {"file_path": "/home/x/.claude/skills/fleet-control/SKILL.md"}},
            {"type": "tool_use", "id": "b1", "name": "Bash",
             "input": {"command": "cat ~/.hermes/skills/creative/comfyui/SKILL.md | head -40"}},
            {"type": "tool_use", "id": "r2", "name": "Read",
             "input": {"file_path": "/home/x/systems/README.md"}},
            {"type": "tool_use", "id": "b2", "name": "Bash",
             "input": {"command": "ls -la ~/.claude/skills/spotify/SKILL.md"}},
            {"type": "tool_use", "id": "s1", "name": "Skill", "input": {"skill": "atria"}},
        ]}},
    ]
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "s.jsonl")
        _write(p, entries)
        tools, tool_err, skills, reads = Counter(), Counter(), Counter(), Counter()
        telemetry.scan_file(p, tools, tool_err, skills, reads)
    assert dict(reads) == {"fleet-control": 1, "comfyui": 1}, reads
    assert dict(skills) == {"atria": 1}, skills


def test_hermes_ledger_and_window():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, ".usage.json")
        with open(p, "w") as f:
            json.dump({"comfyui": {"use_count": 13, "last_used_at": "2026-10-14T10:47:33+00:00"},
                       "old-one": {"use_count": 2, "last_used_at": "2026-06-17T08:03:03+00:00"},
                       "never": {"use_count": 0, "last_used_at": None}}, f)
        ledger = telemetry.hermes_ledger(p)
        assert telemetry.hermes_ledger(os.path.join(d, "missing.json")) == {}
    assert ledger["comfyui"] == {"uses": 13, "last": "2026-10-14"}, ledger
    now = 1794000000  # 2026-11-06 UTC
    assert telemetry.hermes_recent(ledger, 30, now=now) == {"comfyui"}
    assert telemetry.hermes_recent(ledger, 365, now=now) == {"comfyui", "old-one"}


def test_never_used_needs_all_three_signals_silent():
    today = __import__("time").strftime("%Y-%m-%d", __import__("time").gmtime())
    data = {"tools": Counter({"Bash": 3}), "tool_err": Counter(), "files": 1,
            "skills": Counter({"atria": 1}),
            "reads": Counter({"council": 2}),
            "hermes": {"comfyui": {"uses": 13, "last": today}}}
    orig = telemetry.catalog
    telemetry.catalog = lambda: {"atria", "council", "comfyui", "dead-one"}
    try:
        out = telemetry.render(data, 30, {})
    finally:
        telemetry.catalog = orig
    assert "Never-used local skills (1 of 4)" in out, out
    assert out.rstrip().endswith("dead-one"), out[-200:]
    assert "| council | 0 | - | 2 |" in out, out
    assert "| comfyui | 13 |" in out, out


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
