#!/usr/bin/env python3
"""
Deterministic compliance scorer for Shameless Snacks copy.

This is the EXTERNAL VERIFIER the self-improving-agents research called for: a hard,
un-gameable metric a generation loop can be gated against. It is data-driven (reads
policy.json) so the canon can evolve without touching code, and it is itself validated
against a labeled gold set by test_scorer.py before it is trusted.

Usage (library):
    from scorer import Scorer
    s = Scorer()
    result = s.score("...script text...")
    # result.hard -> list of Finding, result.warn -> list, result.passed -> bool

Usage (CLI):
    python3 scorer.py path/to/script.txt
    echo "some copy" | python3 scorer.py -
"""
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

POLICY_PATH = Path(__file__).parent / "policy.json"


@dataclass
class Finding:
    rule_id: str
    severity: str       # "hard" | "warn"
    why: str
    match: str          # the exact text span that matched
    span: tuple         # (start, end) char offsets


@dataclass
class ScoreResult:
    passed: bool                       # True if zero HARD violations
    hard: list = field(default_factory=list)
    warn: list = field(default_factory=list)

    @property
    def hard_count(self):
        return len(self.hard)

    @property
    def warn_count(self):
        return len(self.warn)

    def to_dict(self):
        return {
            "passed": self.passed,
            "hard_count": self.hard_count,
            "warn_count": self.warn_count,
            "hard": [asdict(f) for f in self.hard],
            "warn": [asdict(f) for f in self.warn],
        }


class Scorer:
    def __init__(self, policy_path: Path = POLICY_PATH):
        policy = json.loads(Path(policy_path).read_text())
        self.policy_version = policy.get("_meta", {}).get("policy_version", "?")
        self.hard_rules = self._compile(policy.get("hard", []))
        self.warn_rules = self._compile(policy.get("warn", []))
        self.allow_spans_re = [
            re.compile(self._ws(p), re.IGNORECASE) for p in policy.get("allow", {}).get("patterns", [])
        ]

    @staticmethod
    def _ws(pattern):
        # Treat a literal space as "any run of whitespace" so multi-word phrases
        # still match when ad copy wraps them across a line break.
        return pattern.replace(" ", r"\s+")

    @classmethod
    def _compile(cls, rules):
        compiled = []
        for r in rules:
            pats = [re.compile(cls._ws(p), re.IGNORECASE) for p in r["patterns"]]
            compiled.append((r["id"], r["why"], pats))
        return compiled

    def _allowlisted(self, text, start, end):
        """True if the matched span sits inside an explicitly-permitted phrase."""
        for ar in self.allow_spans_re:
            for m in ar.finditer(text):
                if m.start() <= start and m.end() >= end:
                    return True
        return False

    def _scan(self, text, rules, severity):
        out = []
        for rule_id, why, pats in rules:
            for pat in pats:
                for m in pat.finditer(text):
                    if self._allowlisted(text, m.start(), m.end()):
                        continue
                    out.append(Finding(rule_id, severity, why, m.group(0), (m.start(), m.end())))
        return out

    def score(self, text: str) -> ScoreResult:
        hard = self._scan(text, self.hard_rules, "hard")
        warn = self._scan(text, self.warn_rules, "warn")
        # de-dup identical (rule_id, span) findings
        hard = _dedup(hard)
        warn = _dedup(warn)
        return ScoreResult(passed=(len(hard) == 0), hard=hard, warn=warn)


def _dedup(findings):
    seen = set()
    out = []
    for f in findings:
        key = (f.rule_id, f.span)
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


def _cli():
    if len(sys.argv) < 2:
        print("usage: scorer.py <file|->", file=sys.stderr)
        sys.exit(2)
    arg = sys.argv[1]
    text = sys.stdin.read() if arg == "-" else Path(arg).read_text()
    res = Scorer().score(text)
    print(json.dumps(res.to_dict(), indent=2))
    sys.exit(0 if res.passed else 1)


if __name__ == "__main__":
    _cli()
