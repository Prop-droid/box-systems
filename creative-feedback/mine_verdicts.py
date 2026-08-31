#!/usr/bin/env python3
"""Mine creative verdicts from Discord + Telegram conversations into ledger.jsonl.

Phase-2 auto-inference (design.md): Tomas decided 2026-08-31 that the feedback
loop should read his conversations and capture the decisions he makes there,
instead of requiring explicit /feedback commands.

Reads recent messages via dev-bot/discord_read.py, asks headless claude to
extract shipped/edited/killed verdicts on creative artifacts, validates each
record through append.py, dedupes via .mine_state.json.

Usage:  python3 mine_verdicts.py            # mine + append
        DRY_RUN=1 python3 mine_verdicts.py  # print records, write nothing
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

DIR = os.path.dirname(os.path.abspath(__file__))
DISCORD_READ = os.path.expanduser("~/systems/dev-bot/discord_read.py")
CLAUDE = "/usr/local/bin/claude-max"
STATE_PATH = os.path.join(DIR, ".mine_state.json")
PROMPT_PATH = os.path.join(DIR, "mine_prompt.md")
DRY = os.environ.get("DRY_RUN") == "1"

CHANNELS = ["creative", "general", "war-room", "assistant", "dev"]
THREAD_MAX_AGE_DAYS = 14   # threads older than this (by creation) are skipped
MSGS_PER_SOURCE = 40
DISCORD_EPOCH_MS = 1420070400000
MSG_RE = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\] ")
TG_ARCHIVE = os.path.expanduser("~/systems/dev-bot/tg_archive")


def telegram_chunks(since, newest):
    """Fresh Telegram messages (fleet group + DMs) as discord-format chunks.

    Reads the tg_archive jsonl directly (epoch ts beats telegram_read's
    yearless display format), dedupes by (mid, from) like telegram_read,
    groups per topic, keeps a 10-line context tail before the first fresh line.
    """
    chunks = []
    if not os.path.isdir(TG_ARCHIVE):
        return chunks, newest
    for fname in sorted(os.listdir(TG_ARCHIVE)):
        if not fname.endswith(".jsonl"):
            continue
        by_thread, topics, seen = {}, {}, set()
        for ln in open(os.path.join(TG_ARCHIVE, fname), encoding="utf-8"):
            try:
                r = json.loads(ln)
            except ValueError:
                continue
            if r.get("topic"):
                topics[r.get("thread")] = r["topic"]
            key = (r.get("mid"), r.get("from"))
            if r.get("mid") and key in seen:
                continue
            seen.add(key)
            by_thread.setdefault(r.get("thread"), []).append(r)
        for tid, msgs in by_thread.items():
            lines, fresh_idx = [], None
            for i, r in enumerate(msgs):
                stamp = datetime.fromtimestamp(r.get("ts", 0)).strftime("%Y-%m-%d %H:%M")
                lines.append(f"[{stamp}] {r.get('from', '?')}: {r.get('text', '')}")
                if stamp > since and fresh_idx is None:
                    fresh_idx = i
                if stamp > newest:
                    newest = stamp
            if fresh_idx is None:
                continue
            label = topics.get(tid) or fname[:-6]
            start = max(0, fresh_idx - 10)
            chunks.append(f"=== telegram:{label} ===\n" + "\n".join(lines[start:]))
    return chunks, newest


def read_source(name_or_id, limit=MSGS_PER_SOURCE):
    try:
        out = subprocess.run(
            ["python3", DISCORD_READ, str(name_or_id), str(limit)],
            capture_output=True, text=True, timeout=60)
        return out.stdout if out.returncode == 0 else ""
    except subprocess.TimeoutExpired:
        return ""


def snowflake_dt(sid):
    return datetime.fromtimestamp(((int(sid) >> 22) + DISCORD_EPOCH_MS) / 1000,
                                  tz=timezone.utc)


def load_state():
    try:
        return json.load(open(STATE_PATH))
    except Exception:
        return {"since": None, "hashes": []}


def rec_hash(rec):
    key = f"{rec.get('brand')}|{rec.get('artifact_type')}|{rec.get('verdict')}|{(rec.get('draft') or '')[:200]}"
    return hashlib.sha1(key.encode()).hexdigest()[:16]


def main():
    state = load_state()
    since = state.get("since") or (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d %H:%M")

    listing = subprocess.run(["python3", DISCORD_READ, "list"],
                             capture_output=True, text=True, timeout=60).stdout
    sources = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=THREAD_MAX_AGE_DAYS)
    for line in listing.splitlines():
        parts = line.split(None, 2)
        if len(parts) != 3:
            continue
        kind, sid, name = parts
        if kind == "channel" and name in CHANNELS:
            sources.append((sid, name))
        elif kind == "thread" and snowflake_dt(sid) >= cutoff:
            sources.append((sid, name))

    # Keep only messages newer than the checkpoint; keep a short context tail of
    # older lines so a fresh verdict can still see the draft it refers to.
    chunks, newest = [], since
    for sid, name in sources:
        raw = read_source(sid)
        fresh_idx = None
        lines = raw.splitlines()
        for i, ln in enumerate(lines):
            m = MSG_RE.match(ln)
            if m and m.group(1) > since:
                fresh_idx = i if fresh_idx is None else fresh_idx
                newest = max(newest, m.group(1))
        if fresh_idx is None:
            continue
        start = max(0, fresh_idx - 10)
        chunks.append(f"=== {name} ===\n" + "\n".join(lines[start:]))

    tg, newest = telegram_chunks(since, newest)
    chunks.extend(tg)

    if not chunks:
        print(f"nothing new since {since}")
        return 0

    prompt = open(PROMPT_PATH).read() + "\n\n# INPUT\n\n" + "\n\n".join(chunks)
    print(f">> {len(chunks)} source(s) with fresh messages since {since}; asking claude ...")
    try:
        out = subprocess.run(
            [CLAUDE, "--print", "--model", "claude-sonnet-4-6",
             "--dangerously-skip-permissions"],
            input=prompt, capture_output=True, text=True, timeout=900)
    except subprocess.TimeoutExpired:
        print("ERROR: claude timed out", file=sys.stderr)
        return 1
    if out.returncode != 0:
        # usage-limit / pause exits are transient by estate convention
        print(f"ERROR: claude rc={out.returncode}: {out.stderr[-300:]}", file=sys.stderr)
        return 1

    # Malformed output (no NONE, no JSON) must not advance the checkpoint —
    # that would silently consume messages a healthy retry could still mine.
    has_json = any(l.strip().startswith("{") for l in out.stdout.splitlines())
    if not has_json and "NONE" not in out.stdout:
        print(f"ERROR: unusable claude output: {out.stdout[:200]!r}", file=sys.stderr)
        return 1

    seen = set(state.get("hashes", []))
    appended = skipped = 0
    for line in out.stdout.splitlines():
        line = line.strip()
        if not line or line == "NONE" or not line.startswith("{"):
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        h = rec_hash(rec)
        if h in seen:
            skipped += 1
            continue
        if DRY:
            print("DRY:", json.dumps(rec, ensure_ascii=False)[:300])
            appended += 1
            continue
        ap = subprocess.run(["python3", os.path.join(DIR, "append.py")],
                            input=json.dumps(rec), capture_output=True, text=True)
        if ap.returncode == 0:
            print(ap.stdout.strip())
            seen.add(h)
            appended += 1
        else:
            print(f"append rejected: {ap.stderr.strip()[:200]}", file=sys.stderr)
            skipped += 1

    if not DRY:
        state["since"] = newest
        state["hashes"] = list(seen)[-500:]
        tmp = STATE_PATH + ".tmp"
        json.dump(state, open(tmp, "w"))
        os.replace(tmp, STATE_PATH)
    print(f"done: {appended} verdict(s) {'(dry)' if DRY else 'appended'}, {skipped} skipped, checkpoint -> {newest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
