#!/usr/bin/env python3
"""Scan Claude Code transcripts (box + staged Mac) for Tomas-corrections.

Deterministic pre-filter: finds short user messages that look like corrections
or durable-preference statements, pairs each with the preceding assistant
snippet, and appends unseen candidates to candidates.jsonl. A separate judge
pass (run_correction_capture.sh) decides which candidates are real lessons.

State: state.json holds {"files": {path: "mtime:size"}, "seen": [ids]}.
- files: skip unchanged transcript files (cheap incremental scans)
- seen: ids already judged (consumed); scan never re-emits them
candidates.jsonl is the pending queue; scan appends, judge drains.
"""
import json
import hashlib
import os
import re
import sys
from glob import glob

DIR = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(DIR, "state.json")
CANDIDATES = os.path.join(DIR, "candidates.jsonl")
SOURCES = [
    ("box", os.path.expanduser("~/.claude/projects")),
    ("mac", os.path.join(DIR, "staging/mac")),
]
MAX_USER_LEN = 600      # corrections are short; also guards against re-ingesting
                        # this pipeline's own judge prompts (huge single messages)
SNIPPET_LEN = 400

# Correction / durable-preference markers, matched case-insensitive at word level.
MARKERS = re.compile(
    r"(?i)\b("
    r"no[,.] |not what i|wrong|don'?t |do not |never |stop |instead|"
    r"i said|i asked|i told you|you should( have|'ve)|that'?s not|"
    r"why did you|why would you|revert|undo th|again[,.!]|"
    r"from now on|always (do|use|ask|check|put|write|send)|remember (to|that)|"
    r"i (don'?t|didn'?t) (want|like|mean)|not like th|too (long|short|much|many)"
    r")"
)
# Noise: messages that match markers but are commands/system artifacts.
SKIP_PREFIXES = ("<command-", "<local-command", "<system-reminder", "Caveat:",
                 "[Request interrupted", "CLARIFICATION_REQUIRED")


def load_state():
    if os.path.exists(STATE):
        with open(STATE) as f:
            s = json.load(f)
        s.setdefault("files", {})
        s["seen"] = set(s.get("seen", []))
        return s
    return {"files": {}, "seen": set()}


def save_state(s):
    out = {"files": s["files"], "seen": sorted(s["seen"])}
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(out, f)
    os.replace(tmp, STATE)


def entry_text(msg):
    """Extract plain text from a transcript message content field."""
    content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [b.get("text", "") for b in content
                 if isinstance(b, dict) and b.get("type") == "text"]
        return "\n".join(p for p in parts if p)
    return ""


def scan_file(path, source, seen, pending_ids):
    out = []
    prev_assistant = ""
    session = os.path.basename(path)
    try:
        fh = open(path, errors="replace")
    except OSError:
        return out
    with fh:
        for line in fh:
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("isMeta") or e.get("isSidechain"):
                continue
            etype = e.get("type")
            msg = e.get("message") or {}
            if etype == "assistant":
                t = entry_text(msg)
                if t:
                    prev_assistant = t[-SNIPPET_LEN:]
                continue
            if etype != "user":
                continue
            t = entry_text(msg).strip()
            if not t or len(t) > MAX_USER_LEN:
                continue
            if t.startswith(SKIP_PREFIXES):
                continue
            if not MARKERS.search(t):
                continue
            if not prev_assistant:
                # Corrections happen mid-conversation; a first-message match is
                # a scripted headless prompt, not Tomas correcting the agent.
                continue
            cid = hashlib.sha1((session + ":" + str(e.get("uuid", t))).encode()).hexdigest()[:16]
            if cid in seen or cid in pending_ids:
                continue
            out.append({
                "id": cid,
                "ts": e.get("timestamp", ""),
                "source": source,
                "project": os.path.basename(os.path.dirname(path)),
                "user_text": t,
                "prev_assistant": prev_assistant.strip()[:SNIPPET_LEN],
            })
    return out


def main():
    state = load_state()
    pending_ids = set()
    if os.path.exists(CANDIDATES):
        with open(CANDIDATES) as f:
            for line in f:
                try:
                    pending_ids.add(json.loads(line)["id"])
                except Exception:
                    pass

    new = []
    for source, root in SOURCES:
        for path in glob(os.path.join(root, "**", "*.jsonl"), recursive=True):
            if "/memory/" in path:
                continue
            try:
                st = os.stat(path)
            except OSError:
                continue
            sig = f"{int(st.st_mtime)}:{st.st_size}"
            if state["files"].get(path) == sig:
                continue
            new.extend(scan_file(path, source, state["seen"], pending_ids))
            state["files"][path] = sig

    # Drop scripted prompts: identical text recurring across >= 3 candidates
    # (eval harnesses and cron prompts repeat verbatim; humans do not).
    counts = {}
    for c in new:
        k = hashlib.sha1(" ".join(c["user_text"].lower().split()).encode()).hexdigest()
        c["_k"] = k
        counts[k] = counts.get(k, 0) + 1
    new = [c for c in new if counts[c.pop("_k")] < 3]

    if new:
        new.sort(key=lambda c: c["ts"])
        with open(CANDIDATES, "a") as f:
            for c in new:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
    save_state(state)
    print(f"scan: {len(new)} new candidate(s), {len(pending_ids) + len(new)} pending total")


if __name__ == "__main__":
    sys.exit(main())
