#!/usr/bin/env python3
"""Runs ON THE MAC (via ssh stdin). Read-only export of Wispr Flow Notetaker calls.
Prints one JSON object per call to stdout. Text only: no audio, no screenshots."""
import sqlite3, os, json, sys

D = os.path.expanduser("~/Library/Application Support/Wispr Flow")
EXPECT = {"id", "title", "createdAt", "recordedMs", "summary", "notes", "speakerMap",
          "participantNames", "isDeleted", "transcriptReady", "summaryReady", "modifiedAt"}

con = sqlite3.connect("file:" + D + "/flow.sqlite?mode=ro", uri=True)
con.row_factory = sqlite3.Row
cols = {r[1] for r in con.execute("pragma table_info(Meetings)")}
missing = EXPECT - cols
if missing:
    sys.stderr.write("SCHEMA_CHANGED missing=%s\n" % sorted(missing))
    sys.exit(3)

q = ("select id,title,createdAt,modifiedAt,recordedMs,summary,notes,speakerMap,"
     "participantNames,transcriptReady,summaryReady from Meetings "
     "where isDeleted=0 order by createdAt")
for r in con.execute(q):
    m = dict(r)
    try:
        m["speakerMap"] = json.loads(m["speakerMap"]) if m["speakerMap"] else None
    except Exception:
        pass
    turns, src = [], None
    for name in ("refined.ndjson", "live.ndjson"):
        f = os.path.join(D, "meetings", m["id"], name)
        if os.path.exists(f):
            src = name
            for line in open(f, errors="ignore"):
                try:
                    j = json.loads(line)
                except Exception:
                    continue
                sp = j.get("speaker") or {}
                turns.append({"t": j.get("timestamp"),
                              "s": sp.get("id") if isinstance(sp, dict) else sp,
                              "n": sp.get("name") if isinstance(sp, dict) else None,
                              "x": (j.get("text") or "").strip()})
            break
    m["transcript_source"] = src
    m["turns"] = turns
    print(json.dumps(m, ensure_ascii=False))
