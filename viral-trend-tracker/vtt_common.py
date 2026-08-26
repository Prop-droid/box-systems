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


def write_receipts(source, platform, receipts):
    """Receipts = the actual example posts behind a term's heat scalar
    ({date, source, platform, term, title, url, score}), read by the CCC Viral
    tab. Merge-by-term like write_merged so partial re-runs never wipe the day.
    """
    today = date.today().isoformat()
    VTT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = VTT_DIR / f"{source}-{platform}-receipts-{today}.jsonl"
    scraped = {r["term"] for r in receipts}
    if out_path.exists():
        for line in out_path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("term") not in scraped:
                receipts.append(r)
    receipts.sort(key=lambda r: (r["term"], -r.get("score", 0)))
    tmp = out_path.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(r) + "\n" for r in receipts))
    tmp.rename(out_path)
    print(f"{out_path}: {len(receipts)} receipts", file=sys.stderr)


def top_receipts(source, platform, term, posts, cap=3):
    """posts = [(title, url, score)] -> receipt rows for the term, best first."""
    today = date.today().isoformat()
    rows = []
    seen = set()
    for title, url, score in sorted(posts, key=lambda p: -p[2]):
        if not url or url in seen or not title:
            continue
        seen.add(url)
        rows.append({"date": today, "source": source, "platform": platform,
                     "term": term, "title": str(title)[:160], "url": url, "score": int(score)})
        if len(rows) == cap:
            break
    return rows


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
