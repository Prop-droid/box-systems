"""Shared helpers for VTT ingest lanes (spec 2026-08-13-trend-tracker-research).

Each lane writes daily per-term JSONL rows {date, source, platform, term, value,
...} to $VTT_DIR/<source>-<platform>-<date>.jsonl, merge-by-term so a partial
re-run never wipes the day's file (ad-rank clobber lesson). `value` is that
lane's raw daily "heat" scalar; the CCC scorer (lib/vtt.ts) turns the per-term
time series into velocity/acceleration/momentum.
"""
import json
import os
import sys
from datetime import date
from pathlib import Path

VTT_DIR = Path(os.environ.get("VTT_DIR", "/home/tomas/brain/projects/2026-08/viral-trend-tracker"))
WATCHLIST = Path(__file__).with_name("watchlist.txt")

# Subreddit / channel context that's topically on-brand even without a keyword hit.
RELEVANT_SUBS = {
    "snacks", "eatcheapandhealthy", "nutrition", "fitness", "loseit", "functionalfood",
    "guthealth", "healthyfood", "xxfitness", "volumeeating", "candy", "keto", "1200isplenty",
    "supplements", "advancedfitness", "flexibledieting", "gainit",
}


def load_watchlist():
    terms = []
    for line in WATCHLIST.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            terms.append(line)
    return terms


def relevant(term, title, context=""):
    """Keep a post/video if its context is on-brand or its title carries a term word."""
    if context and context.lower() in RELEVANT_SUBS:
        return True
    tl = (title or "").lower()
    return any(w for w in term.lower().split() if len(w) >= 4 and w in tl)


def write_merged(source, platform, rows, term_count):
    """Merge-by-term write; return count of terms with data (for the exit gate)."""
    today = date.today().isoformat()
    VTT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = VTT_DIR / f"{source}-{platform}-{today}.jsonl"
    scraped = {r["term"] for r in rows}
    if out_path.exists():
        for line in out_path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("term") not in scraped:
                rows.append(r)
    rows.sort(key=lambda r: r["term"])
    tmp = out_path.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(r) + "\n" for r in rows))
    tmp.rename(out_path)
    print(f"{out_path}: {len(rows)} rows, {term_count}/{len(scraped)} terms with data", file=sys.stderr)
    return out_path
