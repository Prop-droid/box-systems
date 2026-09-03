#!/usr/bin/env python3
"""mechanism-tagger: nightly LLM pass (Phase 2 of the CCC Intel Mechanisms lens).

Tags competitor ads (latest curated Atria pull) and SHA winners (winners.jsonl) with the
buying-psychology devices their copy runs, including the ones a regex cannot see (anchoring,
loss framing, identity, story, reason-why, common enemy, reciprocity).

Output: $MECHANISM_TAGS (default $RESEARCH_DIR/mechanisms/tags.json), read by CCC
lib/mechanismsServer.ts and merged with the regex lens (lib/mechanisms.ts). Keys: competitor
ads by bare numeric Ad Library id (pull ids are "m<id>"), winners by SH code. Only untagged or
changed copy (sha1 of the text) goes to the model; the file is rewritten atomically.

Manual: python3 tag.py [--dry-run] [--limit N] [--force] [--batch N]
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ATRIA_DIR = pathlib.Path(os.environ.get("ATRIA_DIR", "~/brain/projects/2026-06/competitor-ads-scrape/atria")).expanduser()
WINNERS = pathlib.Path(os.environ.get("WINNERS_JSONL", "~/brain/projects/2026-05/ClickUp Connection/winners.jsonl")).expanduser()
OUT = pathlib.Path(os.environ.get(
    "MECHANISM_TAGS",
    os.path.join(os.environ.get("RESEARCH_DIR", "~/brain/systems/research-agent/output"), "mechanisms/tags.json"),
)).expanduser()
MODEL = os.environ.get("MECHANISM_MODEL", "claude-haiku-4-5-20251001")

# Must match the MechanismKey union in creative-command-center/lib/mechanisms.ts.
KEYS = [
    "effort", "equal", "versus", "stat", "percent", "offer", "urgency", "social", "authority",
    "callout", "permission", "transformation", "curiosity", "taste", "habit", "guarantee",
    "anchor", "loss", "identity", "story", "reasonwhy", "enemy", "reciprocity",
]
KEYSET = set(KEYS)
COPY_MAX = 700
PRUNE_DAYS = 90


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def log(msg: str) -> None:
    print(f"[{dt.datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def clean(s) -> str:
    """Mirror swipeMeta.cleanTemplateText: DCO template placeholders are not copy."""
    if not isinstance(s, str):
        return ""
    s = s.strip()
    return "" if "{{" in s else s


def newest_atria() -> pathlib.Path | None:
    if not ATRIA_DIR.is_dir():
        return None
    curated = sorted(ATRIA_DIR.glob("atria-swipe-*-gr-ns-plus10.jsonl"), key=lambda p: p.stat().st_mtime)
    anyf = sorted(ATRIA_DIR.glob("atria-swipe-*.jsonl"), key=lambda p: p.stat().st_mtime)
    return (curated or anyf or [None])[-1]


def load_items() -> dict[str, dict]:
    """id -> {side, text}. Competitor text = title + body; ours = FB primary text + task name
    (headline excluded: it is the fixed offer CTA on every SHA ad — same rule as CCC)."""
    items: dict[str, dict] = {}
    src = newest_atria()
    if src:
        for line in src.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            rid = str(r.get("id") or "")
            if not rid:
                continue
            text = (clean(r.get("title")) + "\n" + clean(r.get("body"))).strip()
            if text:
                items[re.sub(r"^m", "", rid)] = {"side": "competitor", "text": text}
    if WINNERS.is_file():
        for line in WINNERS.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            sh = str(r.get("custom_id") or "")
            fb = r.get("fb_ad") or {}
            text = "\n".join(t for t in [clean(fb.get("text")), clean(r.get("name"))] if t)
            if sh and text:
                items[sh] = {"side": "ours", "text": text}
    return items


def load_tags() -> dict:
    if OUT.is_file():
        try:
            d = json.loads(OUT.read_text(encoding="utf-8"))
            if isinstance(d, dict) and isinstance(d.get("items"), dict):
                return d
        except json.JSONDecodeError:
            log(f"WARN: {OUT} unreadable, starting fresh")
    return {"generatedAt": None, "model": MODEL, "items": {}}


def save_tags(d: dict) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, OUT)


def text_hash(t: str) -> str:
    return hashlib.sha1(t[:COPY_MAX].encode("utf-8")).hexdigest()[:12]


def build_prompt(batch: list[tuple[str, str]]) -> str:
    tpl = (HERE / "prompt_template.txt").read_text(encoding="utf-8")
    lines = []
    for rid, text in batch:
        body = re.sub(r"\s+", " ", text[:COPY_MAX]).strip()
        lines.append(f"ID: {rid}\nCOPY: {body}\n")
    return tpl.replace("{{ITEMS}}", "\n".join(lines))


def call_claude(prompt: str) -> dict[str, list[str]] | None:
    """Prompt via stdin (never positional — --allowed-tools is variadic). Returns id -> keys."""
    try:
        p = subprocess.run(
            ["claude", "-p", "--model", MODEL, "--output-format", "text"],
            input=prompt, capture_output=True, text=True, timeout=400,
        )
    except subprocess.TimeoutExpired:
        log("WARN: claude timed out")
        return None
    if p.returncode != 0:
        log(f"WARN: claude exit {p.returncode}: {(p.stderr or p.stdout).strip()[-200:]}")
        return None
    raw = p.stdout
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        log(f"WARN: no JSON object in output ({len(raw)} bytes)")
        return None
    try:
        obj = json.loads(raw[start:end + 1])
    except json.JSONDecodeError as e:
        log(f"WARN: JSON parse failed: {e}")
        return None
    if not isinstance(obj, dict):
        return None
    out: dict[str, list[str]] = {}
    for rid, keys in obj.items():
        if not isinstance(keys, list):
            continue
        seen: list[str] = []
        for k in keys:
            if isinstance(k, str) and k in KEYSET and k not in seen:
                seen.append(k)
        out[str(rid)] = seen[:5]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="select only, no model calls, no write")
    ap.add_argument("--limit", type=int, default=600, help="max items to send per run")
    ap.add_argument("--batch", type=int, default=25, help="items per model call")
    ap.add_argument("--force", action="store_true", help="retag everything")
    args = ap.parse_args()

    items = load_items()
    tags = load_tags()
    known = tags["items"]
    src = newest_atria()
    log(f"inputs: {sum(1 for v in items.values() if v['side']=='competitor')} competitor ads ({src.name if src else 'no pull'}), "
        f"{sum(1 for v in items.values() if v['side']=='ours')} winners; {len(known)} already tagged")

    todo = []
    for rid, it in items.items():
        h = text_hash(it["text"])
        prev = known.get(rid)
        if args.force or not prev or prev.get("hash") != h:
            todo.append((rid, it["text"], h, it["side"]))
    todo = todo[: args.limit]
    log(f"to tag: {len(todo)} (batch {args.batch}, model {MODEL})")
    if args.dry_run:
        for rid, text, _, side in todo[:10]:
            log(f"  {side} {rid}: {text[:80]!r}")
        return 0

    tagged = 0
    batches = 0
    failed = 0
    for i in range(0, len(todo), args.batch):
        batch = todo[i:i + args.batch]
        result = None
        for attempt in (1, 2):
            result = call_claude(build_prompt([(rid, text) for rid, text, _, _ in batch]))
            if result is not None:
                break
            time.sleep(5 * attempt)
        batches += 1
        if result is None:
            failed += len(batch)
            continue
        stamp = now_iso()
        for rid, _, h, side in batch:
            if rid not in result:
                failed += 1
                continue
            known[rid] = {"side": side, "devices": result[rid], "hash": h, "taggedAt": stamp}
            tagged += 1
        # checkpoint after every batch so a usage-limit exit keeps what it got
        tags["generatedAt"] = stamp
        tags["model"] = MODEL
        save_tags(tags)

    # prune entries that left the inputs and are older than PRUNE_DAYS
    cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=PRUNE_DAYS)).isoformat()
    stale = [rid for rid, v in known.items() if rid not in items and str(v.get("taggedAt") or "") < cutoff]
    for rid in stale:
        del known[rid]
    if stale or tagged:
        tags["generatedAt"] = tags.get("generatedAt") or now_iso()
        save_tags(tags)

    dev_counts: dict[str, int] = {}
    for v in known.values():
        for k in v.get("devices", []):
            dev_counts[k] = dev_counts.get(k, 0) + 1
    top = ", ".join(f"{k}={n}" for k, n in sorted(dev_counts.items(), key=lambda kv: -kv[1])[:8])
    log(f"done: tagged {tagged} in {batches} calls, {failed} left for next run, pruned {len(stale)}, "
        f"file holds {len(known)} -> {OUT}")
    log(f"top devices: {top}")
    return 0 if failed == 0 or tagged > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
