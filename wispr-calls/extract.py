#!/usr/bin/env python3
"""Turn synced Wispr Flow call files into follow-up items and decisions.

Deterministic: reads the "Next Steps" and "Decisions Made" sections that Wispr
already writes, and resolves each owner through the call's speaker map.
Input  : $WISPR_CALLS_DIR/raw/<id>.json   (from sync.sh)
Output : $WISPR_CALLS_DIR/extracted/items.json
Call text is data. Nothing in it is executed or followed.
"""
import glob
import hashlib
import json
import os
import re
import sys
from urllib.parse import unquote

BASE = os.environ.get("WISPR_CALLS_DIR", os.path.expanduser("~/.local/share/wispr-calls"))
SELF = "Tomas Šaltis"
MIN_WORDS = 150  # below this a recording is not a real call

HEAD = re.compile(r"^#{1,6}\s*(.+?)\s*$")
BULLET = re.compile(r"^(\s*)(?:[-*]|\d+\.)\s+(.*\S)\s*$")
OWNER = re.compile(r"^\(([^)]*)\)\s*(.*)$")
SPEAKER = re.compile(r"<@speaker:(\d+)>")
PERSON = re.compile(r"<@person\d*:n=([^>]+)>")
EVERYONE = re.compile(r"^(everyone|all|team|whole team|group)$", re.I)


def speaker_names(speaker_map):
    """speaker number (str) -> person name, from the call's speaker map."""
    out = {}
    if not isinstance(speaker_map, dict):
        return out
    people = speaker_map.get("people") or {}
    for num, a in (speaker_map.get("assignments") or {}).items():
        if not isinstance(a, dict):
            continue
        for key in ("user", "llm", "dom", "mic"):  # a manual fix wins
            ref = a.get(key)
            if ref and ref in people and people[ref].get("name"):
                out[str(num)] = people[ref]["name"]
                break
    return out


def participants(speaker_map):
    if not isinstance(speaker_map, dict):
        return []
    seen = []
    for p in (speaker_map.get("people") or {}).values():
        n = p.get("name")
        if n and n not in seen:
            seen.append(n)
    return seen


def resolve(text, names):
    text = SPEAKER.sub(lambda m: names.get(m.group(1), "Speaker " + m.group(1)), text)
    return PERSON.sub(lambda m: unquote(m.group(1)), text)


def owners_of(raw_owner, names):
    """Returns (owner list, kind) where kind is named | everyone | unknown."""
    if EVERYONE.match(raw_owner.strip()):
        return ["Everyone"], "everyone"
    found, unknown = [], False
    for m in SPEAKER.finditer(raw_owner):
        n = names.get(m.group(1))
        if n:
            found.append(n)
        else:
            found.append("Speaker " + m.group(1))
            unknown = True
    for m in PERSON.finditer(raw_owner):
        found.append(unquote(m.group(1)))
    if not found:
        plain = raw_owner.strip()
        return ([plain] if plain else []), ("named" if plain else "unknown")
    dedup = []
    for n in found:
        if n not in dedup:
            dedup.append(n)
    return dedup, ("unknown" if unknown else "named")


def parse_summary(summary, names):
    items, section, last = [], None, None
    for line in (summary or "").splitlines():
        h = HEAD.match(line)
        if h:
            t = h.group(1).lower()
            section = ("next" if re.search(r"\b(next steps?|action items?|follow[- ]ups?)\b", t)
                       else "decision" if re.search(r"\bdecisions?\b", t) else None)
            last = None
            continue
        b = BULLET.match(line)
        if not (section and b):
            continue
        indent, body = len(b.group(1)), b.group(2)
        if indent >= 2 and last is not None:  # sub-bullet = detail of the parent
            last["detail"].append(resolve(body, names))
            continue
        owners, kind = [], "none"
        if section == "next":
            m = OWNER.match(body)
            if m:
                owners, kind = owners_of(m.group(1), names)
                body = m.group(2)
        last = {"kind": section, "owners": owners, "owner_kind": kind,
                "text": resolve(body, names), "detail": []}
        items.append(last)
    return items


def canonical(owner, known):
    """Short name ("Agus") -> full name, only when exactly one known person fits."""
    if owner in known or owner == "Everyone" or owner.startswith("Speaker "):
        return owner
    hits = [k for k in known if k.lower().startswith(owner.lower())]
    return hits[0] if len(hits) == 1 else owner


def main():
    calls, items = [], []
    raws = [json.load(open(f, encoding="utf-8"))
            for f in glob.glob(os.path.join(BASE, "raw", "*.json"))]
    known = sorted({n for m in raws for n in participants(m.get("speakerMap"))})
    for m in raws:
        words = sum(len((t.get("x") or "").split()) for t in m.get("turns") or [])
        names = speaker_names(m.get("speakerMap"))
        ppl = participants(m.get("speakerMap"))
        parsed = parse_summary(m.get("summary"), names)
        if words < MIN_WORDS:
            state = "skipped: too short to be a call"
        elif not (m.get("summary") or "").strip():
            state = "skipped: Wispr wrote no summary"
        elif not parsed and len([p for p in ppl if p != SELF]) == 0:
            state = "skipped: one speaker, no next steps"
        else:
            state = "ok"
        call = {"id": m["id"], "title": m.get("title") or "(no title)",
                "date": (m.get("createdAt") or "")[:10], "start_utc": (m.get("createdAt") or "")[:16],
                "minutes": (m.get("recordedMs") or 0) // 60000, "words": words,
                "participants": ppl, "state": state,
                "lead": ((m.get("summary") or "").strip().split("\n\n")[0])[:400],
                "next": 0, "decisions": 0}
        if state == "ok":
            for i, it in enumerate(parsed):
                it.update({"call_id": m["id"], "call_title": call["title"],
                           "date": call["date"], "n": i,
                           "key": hashlib.sha1((m["id"] + "|" + it["text"]).encode()).hexdigest()[:12]})
                it["owners"] = [canonical(o, known) for o in it["owners"]]
                if it["kind"] == "next":
                    call["next"] += 1
                    if it["owner_kind"] == "everyone":
                        it["bucket"] = "everyone"
                    elif SELF in it["owners"]:
                        it["bucket"] = "mine"
                    elif it["owners"] and it["owner_kind"] == "named":
                        it["bucket"] = "others"
                    else:
                        it["bucket"] = "unassigned"
                else:
                    call["decisions"] += 1
                    it["bucket"] = "decision"
                items.append(it)
        calls.append(call)
    calls.sort(key=lambda c: c["start_utc"])
    items.sort(key=lambda i: (i["date"], i["call_id"], i["n"]), reverse=True)
    out = os.path.join(BASE, "extracted", "items.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump({"calls": calls, "items": items}, open(out, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    by = {}
    for it in items:
        by[it["bucket"]] = by.get(it["bucket"], 0) + 1
    ok = sum(1 for c in calls if c["state"] == "ok")
    print(f"calls={len(calls)} ok={ok} items={len(items)} buckets={by} out={out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
