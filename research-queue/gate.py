#!/usr/bin/env python3
"""research-queue eval-gate: deterministic hard kills over a synthesized report.

Usage: gate.py <report.md> <verdicts.jsonl> <meta.json> <min_source_domains>
Exit 0 = ship; exit 1 = fail, one reason per line on stdout.

Fable-window lesson 2: named, binary, checkable kills; no fail-N-of-M soft
scoring. Lesson 9 scope note: research reports are NOT copy-facing text, so
the brand no-em-dash rule is deliberately NOT checked here.
"""
import sys, json, re, os
from urllib.parse import urlparse

report_p, verdicts_p, meta_p, min_domains = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
text = open(report_p, errors="replace").read()
verdicts = [json.loads(l) for l in open(verdicts_p) if l.strip()]
meta = json.load(open(meta_p)) if os.path.exists(meta_p) else {}
fails = []

# K1: starts with an H1 (a previously-applied FAILED-GATE banner line is tolerated)
body = "\n".join(l for l in text.splitlines() if not l.startswith("> GATE:"))
if not body.lstrip().startswith("# "):
    fails.append("K1: report does not start with an H1 '# ' line")

# K2: required sections
for sec in ("## TL;DR", "## Findings", "## Divergences", "## Open questions", "## Sources"):
    if not re.search("^" + re.escape(sec), body, re.M | re.I):
        fails.append(f"K2: missing required section '{sec}'")

def section(name):
    m = re.search(rf"^## {name}\s*$(.*?)(?=^## |\Z)", body, re.M | re.S | re.I)
    return m.group(1) if m else ""

# K3 + K4: every TOP-LEVEL Findings bullet is confidence-tagged and carries a
# URL. Indented sub-bullets belong to their parent finding and are exempt
# (first smoke run showed the strict version kills legitimate nested structure).
TAGS = ("[CONFIRMED]", "[SINGLE-SOURCE]", "[CONTESTED]")
bullets = [l for l in section("Findings").splitlines() if re.match(r"[-*] ", l)]
if not bullets:
    fails.append("K3: Findings section has no bullets")
for l in bullets:
    if not any(t in l for t in TAGS):
        fails.append(f"K3: untagged finding bullet: {l.strip()[:80]}")
    if "http" not in l:
        fails.append(f"K4: finding bullet with no source URL: {l.strip()[:80]}")

# K5: minimum distinct source domains
domains = {urlparse(u).netloc.removeprefix("www.") for u in re.findall(r"https?://\S+", section("Sources"))}
domains.discard("")
if len(domains) < min_domains:
    fails.append(f"K5: only {len(domains)} distinct source domains in Sources (need >= {min_domains})")

# K6: refuted claims must be surfaced as killed, never as findings
refuted = [v for v in verdicts if v.get("verdict") == "REFUTED"]
if refuted:
    if not re.search(r"^## Killed claims", body, re.M | re.I):
        fails.append("K6: verdicts contain REFUTED claims but report has no '## Killed claims' section")
    ftext = section("Findings").lower()
    for v in refuted:
        key = " ".join(re.findall(r"[a-z0-9]+", v.get("claim", "").lower())[:8])
        if key and key in re.sub(r"[^a-z0-9 ]", " ", ftext):
            fails.append(f"K6: refuted claim appears in Findings: {v.get('claim','')[:80]}")

# K7: degraded runs must say so in the report
if meta.get("degraded") and "DEGRADED" not in body:
    fails.append("K7: run was degraded (" + meta["degraded"][:60] + ") but report lacks a DEGRADED note")

if fails:
    print("\n".join(fails))
    sys.exit(1)
print(f"gate PASS: {len(bullets)} tagged findings, {len(domains)} source domains, "
      f"{len(refuted)} refuted claims surfaced, degraded={bool(meta.get('degraded'))}")
