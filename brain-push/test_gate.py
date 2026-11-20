#!/usr/bin/env python3
"""Gate regression cases. Run: python3 test_gate.py (exit 1 on any mismatch)."""
import sys
import gate

OK = "Shameless Snacks/brand/product-and-website"
SRC = OK + "/x.md"
# (label, folder, text, expected: "block" | "hold" | "pass")
CASES = [
    ("personal email", OK, "ask someone@gmail.com", "block"),
    ("company email", OK, "owner jules@ejam.com", "pass"),
    ("mac path", OK, 'open "/Users/tomas/Library/x"', "block"),
    ("home-relative path", OK, "see `~/systems/foo/README.md`", "block"),
    ("linux home path", OK, "at /home/tomas/brain", "block"),
    ("url with /home/ segment", OK, "https://www.businesswire.com/news/home/20201027005938/en", "pass"),
    ("clickup token", OK, "pk_81523916_ABCDEFGHIJKLMNOPQRSTUVWX", "block"),
    ("task-naming slug is not a key", OK, "[[creative-task-naming-and-brief-conventions]]", "pass"),  # pragma: allowlist secret
    ("clickup user id", OK, "assignee 81523916", "block"),
    ("dollar figure is not a user id", OK, "spend $81,523,916 and 86% less", "pass"),
    ("person exit", OK, "Alejandra is no longer working with us", "block"),
    ("box hostname", OK, "ssh tomas-agent-box", "block"),
    ("tailnet address", OK, "http://100.107.26.69:3000/x", "block"),
    ("public funnel share link", OK, "report: https://tomas-agent-box.tailb74909.ts.net:8443/diff/abc/", "pass"),
    ("personal marker", OK, "lake house shortlist", "block"),
    ("raw source is warn only", OK, "**Sources**: `raw/brand-context/guide.md`", "pass"),
    ("banned term is warn only", OK, "Never say Ozempic.", "pass"),
    ("unknown folder", "Shameless Snacks/new-folder", "clean text", "block"),
    ("unknown root", "Personal", "clean text", "block"),
    ("held folder", "Shameless Snacks/open-loops/hypotheses", "clean text", "hold"),
]
bad = 0
for label, folder, text, want in CASES:
    f = gate.check(folder, folder + "/x.md", text)
    got = "block" if gate.is_alert(f) else "hold" if gate.is_blocked(f) else "pass"
    if got != want:
        bad += 1
        print(f"FAIL {label}: got {got}, want {want} ({gate.summarize(f) if f else 'no findings'})")
print(f"{len(CASES) - bad}/{len(CASES)} pass")
sys.exit(1 if bad else 0)
