#!/usr/bin/env python3
"""One-off: fill the 4 FB launch fields on the explicit THT talent tasks that the
daily cron skips (they're subtasks; the cron is parents-only).

Fills ONLY: FB Ad3 - LP (+ Landing Page Link mirror), FB Ad4 - FB Page,
            FB Ad6 - Headline, FB Ad7 - Text.
Never overwrites a non-empty field. LP auto-picked by angle via autofill's LP_MAP
+ prompt. Script source = the task's 📽️ Script Link custom field (Google Doc),
falling back to the description.

Reuses all of autofill.py's machinery (api, field_value, run_claude, LP_MAP,
PROMPT_TMPL, dash-lint). Dry by default; set THT_WRITE=1 to actually write.
Writes a JSON plan to tht_plan.json for review.
"""
import json
import os
import re
import subprocess
import tempfile

import autofill as af

# autofill.fetch_gdoc_text assumes gws prints the doc to stdout, but gws actually
# SAVES to a file and prints JSON metadata. Corrected: export with -o to a temp
# file and read it back.
_GDOC_RE = re.compile(r"https://docs\.google\.com/document/d/([\w-]+)")


def fetch_doc(url_or_text):
    m = _GDOC_RE.search(url_or_text or "")
    if not m:
        return None
    fid = m.group(1)
    # gws -o sandboxes the output path to cwd, so run it inside a temp dir with a
    # relative filename and read it back.
    try:
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(["gws", "drive", "files", "export", "--params",
                            json.dumps({"fileId": fid, "mimeType": "text/plain"}),
                            "-o", "doc.txt"],
                           cwd=d, capture_output=True, text=True, timeout=60)
            out = os.path.join(d, "doc.txt")
            if os.path.exists(out):
                txt = open(out, encoding="utf-8", errors="replace").read().strip()
                return txt or None
    except Exception:
        return None
    return None

WRITE = os.environ.get("THT_WRITE") == "1"
PLAN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tht_plan.json")

# 📽️ Script Link (primary) then the plain "Script Link" url field
SCRIPT_LINK_FIELDS = [
    "d921663d-4b21-4c11-8670-bf37ad4c409d",  # 📽️ Script Link
    "28204a89-e03c-44ac-8fdb-96678ad492ab",  # Script Link
]
LAUNCH_KEYS = ["lp", "fb_page", "headline", "text"]

# THT talent tasks (custom_id, task_id) — tht-tagged, THT in name, statuses
# to do / approved / cs review. SH-16191 excluded (MRKL edit, no THT in name).
THT = [
    ("SH-16193", "868jzy9dc"), ("SH-16189", "868jzk3dk"),
    ("SH-16187", "868jzj5jh"), ("SH-16182", "868jz1wy5"),
    ("SH-16181", "868jz1wby"), ("SH-16171", "868jy7kam"),
    ("SH-16168", "868jy7jdm"), ("SH-16127", "868jwz6w3"),
    ("SH-15955", "868jtjqfy"), ("SH-15954", "868jtjq8c"),
    ("SH-15953", "868jtjn8n"), ("SH-15702", "868jnurtc"),
    ("SH-15477", "868jexk18"), ("SH-15475", "868jexjxg"),
    ("SH-15476", "868jexjxe"), ("SH-15471", "868jex9tv"),
    ("SH-14387", "868j19ft4"), ("SH-11303", "868he8qyx"),
]


def script_text(task):
    for fid in SCRIPT_LINK_FIELDS:
        v = af.field_value(task, fid)
        if v:
            txt = fetch_doc(v if isinstance(v, str) else str(v))
            if txt:
                return txt, "script-link"
    desc = (task.get("description") or task.get("text_content") or "").strip()
    if desc:
        doc = fetch_doc(desc)
        if doc:
            return doc, "desc-doc"
        return desc, "desc-text"
    return "", "none"


def main():
    plan = []
    for cid, tid in THT:
        t = af.api("GET", f"/task/{tid}")
        if not t:
            print(f"{cid}: FETCH FAILED")
            plan.append({"cid": cid, "tid": tid, "error": "fetch failed"})
            continue
        name = t["name"]
        missing = [k for k in LAUNCH_KEYS if af.field_value(t, af.F[k]) is None]
        already = [k for k in LAUNCH_KEYS if k not in missing]
        if "lp" in missing and af.lp_on_hold(name):
            missing.remove("lp")
        if not missing:
            print(f"{cid}: all 4 launch fields already set, skip")
            plan.append({"cid": cid, "name": name, "status": t.get("status", {}).get("status"),
                         "missing": [], "already": already, "skipped": "already complete"})
            continue

        ctx, src = script_text(t)
        # only trust headline/text when a real script actually loaded; otherwise the
        # model would invent copy from the task name (the failure mode we are avoiding)
        has_script = src in ("script-link", "desc-doc") and len(ctx) >= 200
        ans = af.run_claude(af.PROMPT_TMPL.format(
            name=name, kind="video", context=(ctx[:6000] or "(empty)"),
            lp_fiber=af.LP_MAP["fiber"], lp_glp1=af.LP_MAP["glp1"], lp_swap=af.LP_MAP["swap"],
            pages="\n".join("- " + p for p in af.FB_PAGES),
            deliv_opts="[]", product_opts="[]",
            missing=json.dumps(missing))) or {}

        writes = {}
        if "lp" in missing and ans.get("lp"):
            writes[af.F["lp"]] = ans["lp"]
            if af.field_value(t, af.F["lp_mirror"]) is None:
                writes[af.F["lp_mirror"]] = ans["lp"]
        if "fb_page" in missing and ans.get("fb_page") in af.FB_PAGES:
            writes[af.F["fb_page"]] = ans["fb_page"]
        if has_script and "headline" in missing and ans.get("headline"):
            writes[af.F["headline"]] = ans["headline"]
        if has_script and "text" in missing and ans.get("text"):
            writes[af.F["text"]] = ans["text"]

        row = {"cid": cid, "tid": tid, "name": name,
               "status": t.get("status", {}).get("status"),
               "script_src": src, "has_script": has_script, "script_chars": len(ctx),
               "missing": missing, "already": already,
               "lp": ans.get("lp"), "fb_page": ans.get("fb_page"),
               "headline": ans.get("headline"), "text": ans.get("text"),
               "notes": ans.get("notes"), "n_writes": len(writes)}
        plan.append(row)
        print(f"\n{cid} [{t.get('status',{}).get('status')}] missing={missing} src={src} writes={len(writes)}")
        print(f"  LP:   {ans.get('lp')}")
        print(f"  PAGE: {ans.get('fb_page')}")
        print(f"  HEAD: {ans.get('headline')}")
        txt = (ans.get('text') or '')
        print(f"  TEXT: {txt[:200]}{'...' if len(txt) > 200 else ''}")
        if ans.get("notes"):
            print(f"  notes: {ans['notes']}")

        if WRITE and writes:
            ok = 0
            for fid, val in writes.items():
                r = af.api("POST", f"/task/{tid}/field/{fid}", body={"value": val})
                ok += 1 if r is not None else 0
            chk = af.api("GET", f"/task/{tid}")
            verified = sum(1 for fid in writes
                           if chk and any(f["id"] == fid and f.get("value") not in (None, "", [])
                                          for f in chk.get("custom_fields", [])))
            row["wrote"] = ok
            row["verified"] = verified
            print(f"  WROTE {ok}/{len(writes)}, verified {verified}")

    json.dump(plan, open(PLAN_FILE, "w"), indent=1, ensure_ascii=False)
    mode = "WRITE" if WRITE else "DRY"
    print(f"\n[{mode}] {len(plan)} tasks processed. Plan -> {PLAN_FILE}")


if __name__ == "__main__":
    main()
