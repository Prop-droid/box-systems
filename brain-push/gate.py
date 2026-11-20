#!/usr/bin/env python3
"""Gate for the wiki -> eJam Company Brain push. Deterministic, no LLM.

prepare.py calls check() for every wiki page. A page with one HARD finding is
NOT exported (not in manifest.json, not in entries/), so push.py cannot send
it. WARN findings are reported and the page still goes.

Rules (Tomas, 2026-11-12). Config: gate_config.json next to this file.
  folder      HARD  the page's wiki folder is not on the allowlist
              HOLD  the folder is in hold_folders (kept on the box on purpose:
                    not exported, no alert)
  secret      HARD  key / token pattern
  email       HARD  an email address outside the company domains
  personal    HARD  personal-side marker (account-firewall rules.json)
  local_path  HARD  /Users/, /home/, ~/, cloud-storage mount path
  host        HARD  box hostname, tailnet address, localhost port
  user_id     HARD  ClickUp user ID
  person_exit HARD  statement that a named person left / was removed
  compliance  WARN  hard banned claim (compliance-eval policy.json); customer
                    voice, research and performance pages are exempt (same
                    exclusion list as the nightly compliance scrub).
                    WARN, not HARD: on 2026-11-12 a HARD setting blocked 50 of
                    149 pages, because canon pages name the banned terms as
                    rules and examples ("never say X"). A regex cannot tell a
                    ban from a claim.
  raw_source  WARN  cites a raw/ file that teammates cannot open

Public share links on the box funnel (https://<box>.ts.net:8443/...) are
allowed: they are made for teammates.

CLI: python3 gate.py            dry report for the current wiki, exit 0
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE / "gate_config.json").read_text())
FIREWALL_RULES = Path.home() / "systems/account-firewall/rules.json"
SCRUB = Path.home() / "systems/compliance-scrub/scan.py"

COMPANY_DOMAINS = tuple(CONFIG["company_email_domains"])
ALLOW_FOLDERS = set(CONFIG["allow_folders"])
HOLD_FOLDERS = set(CONFIG.get("hold_folders", []))

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
PATTERNS = {
    "secret": [
        r"(?<![A-Za-z0-9])pk_\d{4,}_[A-Z0-9]{16,}",
        r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{20,}",
        r"(?<![A-Za-z0-9])tk_live_[A-Za-z0-9]{8,}",
        r"AIza[0-9A-Za-z_-]{30,}",
        r"xox[abprs]-[A-Za-z0-9-]{10,}",
        r"gh[pousr]_[A-Za-z0-9]{30,}",
        r"apify_api_[A-Za-z0-9]{20,}",
        r"Bearer\s+[A-Za-z0-9._-]{24,}",
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        r"(?i)\b(password|passwd|api[_-]?key|secret|token)\b\s*[:=]\s*[\"']?[A-Za-z0-9/+_-]{16,}",
    ],
    "local_path": [
        r"/Users/[A-Za-z0-9._-]+",
        r"(?<![\w.-])/home/[a-z][a-z0-9_-]*",
        r"(?<![\w/.])~/[\w.]",
        r"Library/CloudStorage",
        r"GoogleDrive-",
    ],
    "host": [
        r"(?i)tomas-agent-box",
        r"(?i)\b[\w-]+\.ts\.net\b",
        r"\b100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b",
        r"(?i)\blocalhost:\d{2,5}\b",
        r"\b127\.0\.0\.1\b",
    ],
    "user_id": [
        r"(?<![\w$.,/#-])(?:8[1-9]\d{6}|114210317)(?![\w,-]|\.\d)",
    ],
    "person_exit": [
        r"(?i)\b(?:is|are|was|were)? ?no longer work(?:s|ing)? (?:with|for|at)\b",
        r"(?i)\bleft the (?:company|team|business)\b",
        r"(?i)\b(?:was|were|got|been) (?:fired|let go|terminated|laid off)\b",
    ],
    "raw_source": [
        r"(?<![\w/])raw/[\w.-]+/[\w./-]+",
    ],
}
SEVERITY = {"raw_source": "WARN"}
FUNNEL_URL = re.compile(r"https://[\w.-]+\.ts\.net:8443/\S*")
COMPILED = {k: [re.compile(p) for p in v] for k, v in PATTERNS.items()}


def _personal_markers():
    rules = json.loads(FIREWALL_RULES.read_text())
    return [re.compile(p) for p in rules["personal"]["markers"]]


def _scrub():
    spec = importlib.util.spec_from_file_location("compliance_scrub_scan", SCRUB)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PERSONAL = _personal_markers()
_SCAN = _scrub()
_HARD, _WARN, _ALLOW = _SCAN.load_policy()


def folder_allowed(folder):
    return folder in ALLOW_FOLDERS


def check(folder, source, text):
    """Return [(severity, rule, line_no, fragment)] for one wiki page.

    folder = wiki folder path ("Shameless Snacks/brand/..."), source = path
    relative to the wiki root, text = page content.
    """
    out = []
    if folder in HOLD_FOLDERS:
        out.append(("HOLD", "folder", 0, f"'{folder}' is held on the box"))
    elif not folder_allowed(folder):
        out.append(("HARD", "folder", 0, f"'{folder}' is not on the allowlist"))
    exempt = any(x in ("/" + source).lower() for x in _SCAN.EXCLUDE_SUBSTR)
    for ln, line in enumerate(text.splitlines(), 1):
        for m in EMAIL.finditer(line):
            if not m.group(0).lower().endswith(COMPANY_DOMAINS):
                out.append(("HARD", "email", ln, m.group(0)))
        for rx in PERSONAL:
            m = rx.search(line)
            if m:
                out.append(("HARD", "personal", ln, m.group(0)))
        scan_line = FUNNEL_URL.sub("", line)
        for rule, rxs in COMPILED.items():
            for rx in rxs:
                m = rx.search(scan_line)
                if m:
                    out.append((SEVERITY.get(rule, "HARD"), rule, ln, m.group(0)))
                    break
        if not exempt:
            spans = _SCAN.allowed_spans(line, _ALLOW)
            for rid, _why, rxs in _HARD:
                for rx in rxs:
                    for m in rx.finditer(line):
                        if any(a <= m.start() and m.end() <= b for a, b in spans):
                            continue
                        out.append(("WARN", f"compliance/{rid}", ln, m.group(0)))
    return out


def is_blocked(findings):
    """True = do not export. HARD = alert, HOLD = expected and silent."""
    return any(sev in ("HARD", "HOLD") for sev, *_ in findings)


def is_alert(findings):
    return any(sev == "HARD" for sev, *_ in findings)


def summarize(findings, limit=4):
    """Compact 'rule xN (first fragment)' text for one page."""
    agg = {}
    for sev, rule, ln, frag in findings:
        a = agg.setdefault((sev, rule), {"n": 0, "frag": frag, "ln": ln})
        a["n"] += 1
    parts = [f"{sev} {rule} x{v['n']} (line {v['ln']}: {v['frag'][:60]})"
             for (sev, rule), v in sorted(agg.items())]
    more = f" +{len(parts) - limit} more" if len(parts) > limit else ""
    return "; ".join(parts[:limit]) + more


def _dry():
    wiki = Path.home() / "brain/wiki"
    skip_names = {"index.md", "log.md", "overview.md"}
    blocked = warned = total = 0
    for p in sorted(wiki.rglob("*.md")):
        rel = p.relative_to(wiki)
        if len(rel.parts) < 2 or rel.parts[0] == "meta" or ".backup" in str(rel):
            continue
        if p.name in skip_names or p.name.endswith("-index.md"):
            continue
        total += 1
        f = check("/".join(rel.parts[:-1]), str(rel), p.read_text(errors="replace"))
        if not f:
            continue
        if is_blocked(f):
            blocked += 1
            print(f"BLOCK {rel}\n      {summarize([x for x in f if x[0] in ('HARD', 'HOLD')])}")
        else:
            warned += 1
    print(f"\n{total} pages: {blocked} blocked, {warned} warn-only, "
          f"{total - blocked - warned} clean")


if __name__ == "__main__":
    _dry()
    sys.exit(0)
