#!/usr/bin/env python3
"""Apply the reviewed THT plan (tht_plan.json) to ClickUp.

Normalization (Tomas 2026-06-15):
  - LP deterministic by angle: cravings/swap/candy -> Swap, glp -> GLP-1, else Fiber
  - FB Page forced to "Better For You Food (102895552862171)" on all
  - Headline/Text kept exactly as drafted (only where a real script loaded)

Safety: re-GETs each task and writes a field ONLY if it is still empty (never
overwrites). DRY by default; THT_WRITE=1 to actually write, with verification.
"""
import json
import os

import autofill as af

WRITE = os.environ.get("THT_WRITE") == "1"
PAGE = "Better For You Food (102895552862171)"
HERE = os.path.dirname(os.path.abspath(__file__))


def lp_for(name):
    n = name.lower()
    if any(t in n for t in ("craving", "swap", "candy")):
        return af.LP_MAP["swap"]
    if "glp" in n:
        return af.LP_MAP["glp1"]
    return af.LP_MAP["fiber"]


def main():
    plan = json.load(open(os.path.join(HERE, "tht_plan.json")))
    total_writes = total_verified = touched = 0
    for r in plan:
        if r.get("skipped") or r.get("error"):
            continue
        tid, name, cid = r["tid"], r["name"], r["cid"]
        t = af.api("GET", f"/task/{tid}")
        if not t:
            print(f"{cid}: re-fetch failed, skip")
            continue

        def empty(key):
            return af.field_value(t, af.F[key]) is None

        writes = {}
        if empty("lp"):
            lp = lp_for(name)
            writes[af.F["lp"]] = lp
            if empty("lp_mirror"):
                writes[af.F["lp_mirror"]] = lp
        if empty("fb_page"):
            writes[af.F["fb_page"]] = PAGE
        if r.get("has_script"):
            if empty("headline") and r.get("headline"):
                writes[af.F["headline"]] = r["headline"]
            if empty("text") and r.get("text"):
                writes[af.F["text"]] = r["text"]

        if not writes:
            print(f"{cid}: nothing empty to write")
            continue
        touched += 1
        total_writes += len(writes)
        print(f"{cid} [{t.get('status',{}).get('status')}]: {len(writes)} fields -> "
              f"LP={lp_for(name).split('/')[-1][:18]} page=BFYF "
              f"{'+head+text' if r.get('has_script') else '(no copy)'}")
        if WRITE:
            ok = 0
            for fid, val in writes.items():
                resp = af.api("POST", f"/task/{tid}/field/{fid}", body={"value": val})
                ok += 1 if resp is not None else 0
            chk = af.api("GET", f"/task/{tid}")
            ver = sum(1 for fid in writes
                      if chk and any(f["id"] == fid and f.get("value") not in (None, "", [])
                                     for f in chk.get("custom_fields", [])))
            total_verified += ver
            print(f"    wrote {ok}/{len(writes)}, verified {ver}")

    mode = "WROTE" if WRITE else "DRY (no writes)"
    print(f"\n[{mode}] {touched} tasks, {total_writes} fields planned"
          + (f", {total_verified} verified persisted" if WRITE else ""))


if __name__ == "__main__":
    main()
