#!/usr/bin/env python3
"""
Daily ClickUp launch-details autofill for the Creative Strategist list.

Scans tasks in statuses: to do / in progress / cs review / approved / sent to mb.
For each task, fills ONLY EMPTY custom fields among:

  Launch:   FB Ad3 - LP (+ Landing Page Link mirror), FB Ad4 - FB Page,
            FB Ad6 - Headline, FB Ad7 - Text
  Taxonomy: Brand, Product, Deliverable Type, Channel, Responsible

Context sources:
  - image tasks: task name tokens + description (copy block)
  - video tasks: script from description; fallback = Google Doc link in
    description (fetched via `gws drive files export`); if neither exists,
    post a ClickUp comment assigned to Tomas asking for the script.

Value generation is delegated to `claude -p` (headless) with brand canon +
voice rules embedded in the prompt. Never overwrites a non-empty field.

Env:
    TOKEN_FILE          ClickUp pk token file (default ~/.config/clickup/pk)
    AUTOFILL_DRY_RUN=1  compute + print planned writes/pings, write nothing
    AUTOFILL_MODEL      claude model alias for headless calls (default sonnet)
    AUTOFILL_LOOKBACK_DAYS  only fetch tasks updated in the last N days (default 30)
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://api.clickup.com/api/v2"
LIST_ID = "901110066469"   # Shameless Snacks > Creative Marketing > Tomas | Creative Strategist
TEAM_ID = "9011638245"
TOKEN_FILE = os.path.expanduser(os.environ.get("TOKEN_FILE", "~/.config/clickup/pk"))
TOKEN = open(TOKEN_FILE).read().strip()
DRY_RUN = os.environ.get("AUTOFILL_DRY_RUN") == "1"
MODEL = os.environ.get("AUTOFILL_MODEL", "sonnet")
MAX_LLM_CALLS = int(os.environ.get("AUTOFILL_MAX_LLM", "30"))  # per-run cap
LOOKBACK_DAYS = int(os.environ.get("AUTOFILL_LOOKBACK_DAYS", "30"))
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")
REQUEST_TIMEOUT = 60
TOMAS_ID = 81523916
PING_COOLDOWN_DAYS = 7

STATUSES = ["to do", "in progress", "cs review", "approved", "sent to mb"]

# ---- target custom fields ------------------------------------------------
F = {
    "lp":          "7eca3451-c4df-4897-a543-c92a3d04ede6",  # FB Ad3 - LP (short_text)
    "lp_mirror":   "ee82257f-f430-4137-9d3a-54e40bc31ab4",  # Landing Page Link (short_text)
    "fb_page":     "77e384fd-202e-47cf-9ef6-5b9b2d7aa36f",  # FB Ad4 - FB Page (short_text)
    "headline":    "5a13da3d-3644-44d5-bf25-2af39ee2b661",  # FB Ad6 - Headline (short_text)
    "text":        "580b7f41-99f5-4c9f-a721-d59f6d2c4e48",  # FB Ad7 - Text (text)
    "script_link": "d921663d-4b21-4c11-8670-bf37ad4c409d",  # 📽️ Script Link (url) — video script Doc
    "brand":       "ddffbadd-796b-46d7-8b9c-17fe534746cc",  # ✨ Brand (drop_down)
    "product":     "84571f5b-7801-40d7-b453-0b37bdfa01e8",  # ✨ Product (drop_down)
    "deliv_type":  "dba1ec3e-ef43-449c-bfea-3990a75d0c6f",  # 💎 Deliverable Type (drop_down)
    "channel":     "280a416b-ce78-4732-8a76-79732cd93afa",  # 🚨 Channel (labels)
    "responsible": "a81df287-335f-493b-adb8-b7ac2bcbc581",  # 👤 Responsible (users/group)
}
CHANNEL_FACEBOOK_UUID = "b5d2e5be-5720-4429-9040-db8396aa250c"
RESPONSIBLE_GUID = {  # group user fields take the workspace-member UUID string
    "image": "cf65787a-6fe1-4473-8e2a-889720cda89b",  # Designer team
    "video": "1a5392c6-9f0d-4ccd-8c4d-5dde128c1d62",  # Video Editor team
}

# LP HOLD — these launches are waiting for a NEW landing page URL (Tomas,
# 2026-06-11). Matched against the task name with non-alphanumerics stripped;
# lp + mirror are skipped on match, all other fields still fill. Remove the
# token (or swap in the new URL via LP_MAP) once the page ships.
LP_HOLD = ["founder", "giancarlo", "allstar", "berryblast"]


def lp_on_hold(name):
    flat = re.sub(r"[^a-z0-9]", "", name.lower())
    return any(p in flat for p in LP_HOLD)


LP_MAP = {
    "fiber":  "https://snacks.eatshameless.com/gummies/meta/fiber-packed/trw-gifts/",
    "glp1":   "https://snacks.eatshameless.com/gummies/meta/fiber-packed/glp-1/",
    "swap":   "https://snacks.eatshameless.com/gummies/meta/fiber-packed/swap/?headline=10+Reasons+Why+These+Fiber-Packed+Gummies+Are+The+Best+Candy+Swap+For+2026&lpv=SHA-Gummies-Facebook-Swap-02-27-26",
}
FB_PAGES = [
    "Shameless Snacks (114450944603601)",
    "Better For You Food (102895552862171)",
    "Fiber Secrets (993925060460014)",
    "Low Sugar Secrets (785221974676410)",
    "The Snack Burglar (252876461239289)",
]

# ---- HTTP helpers ----------------------------------------------------------

def api(method, path, body=None, params=None):
    url = f"{BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": TOKEN, "Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as r:
                return json.loads(r.read() or "{}")
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(15 * (attempt + 1)); continue
            print(f"  HTTP {e.code} {method} {path}: {e.read().decode()[:200]}")
            return None
        except Exception as e:
            if attempt == 2:
                print(f"  ERROR {method} {path}: {e}")
                return None
            time.sleep(5)
    return None


def fetch_tasks():
    # NOTE: on the LIST endpoint, subtasks=true returns EVERY subtask on the
    # list (statuses[] only filters parents) — that pulled ~5k tasks per run
    # and contributed to the 2026-06-11 memory crash. The TEAM endpoint applies
    # statuses[] to subtasks too; list_ids[] keeps it scoped to the Creative
    # Strategist list only. date_updated_gt trims the ~4.6k historical
    # "sent to mb" archive down to the recently-touched working set.
    #
    # PARENT TASKS ONLY (Tomas, 2026-06-12): subtasks — especially the
    # ClickBot "MB - Winner" ones — are other teams' jurisdiction; the
    # 2026-06-12 run autofilled 256 subtasks before this was caught.
    since_ms = int((time.time() - LOOKBACK_DAYS * 86400) * 1000)
    tasks, page = [], 0
    while True:
        r = api("GET", f"/team/{TEAM_ID}/task", params={
            "list_ids[]": LIST_ID, "statuses[]": STATUSES,
            "subtasks": "false", "include_closed": "false",
            "date_updated_gt": since_ms, "page": page})
        if not r or not r.get("tasks"):
            break
        tasks += r["tasks"]
        if r.get("last_page", len(r["tasks"]) < 100):
            break
        page += 1
    # belt-and-suspenders: client-side status filter + hard subtask exclusion
    # + skip anything ClickBot created (automation-spawned channel/winner
    # subtasks like "Applovin - CPP", "TikTok", "Facebook - LC Scaling" —
    # Tomas 2026-06-12: 100% excluded, other teams' jurisdiction)
    return [t for t in tasks
            if t.get("status", {}).get("status", "").lower() in STATUSES
            and not t.get("parent")
            and (t.get("creator") or {}).get("username") != "ClickBot"]


# ---- context extraction ----------------------------------------------------

def field_value(task, fid):
    for f in task.get("custom_fields", []):
        if f["id"] == fid:
            v = f.get("value")
            if v in (None, "", [], {}):
                return None
            return v
    return None


def deliv_type_options():
    """name -> orderindex for the Deliverable Type + Product dropdowns."""
    r = api("GET", f"/list/{LIST_ID}/field")
    opts = {}
    for f in (r or {}).get("fields", []):
        if f["id"] in (F["deliv_type"], F["product"], F["brand"]):
            opts[f["id"]] = {o["name"]: o["orderindex"]
                             for o in f.get("type_config", {}).get("options", [])}
    return opts


GDOC_RE = re.compile(r"https://docs\.google\.com/document/d/([\w-]+)")


def fetch_gdoc_text(text):
    """Export a Google Doc linked in `text` to plain text. gws writes the export to a
    FILE (stdout is only JSON metadata) and sandboxes -o to the cwd, so run it inside a
    temp dir with a relative output name and read it back. (Pre-2026-06-15 this read
    stdout and silently fed the model metadata instead of the script.)"""
    m = GDOC_RE.search(text or "")
    if not m:
        return None
    try:
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(
                ["gws", "drive", "files", "export", "--params",
                 json.dumps({"fileId": m.group(1), "mimeType": "text/plain"}),
                 "-o", "doc.txt"],
                cwd=d, capture_output=True, text=True, timeout=60)
            out = os.path.join(d, "doc.txt")
            if os.path.exists(out):
                return open(out, encoding="utf-8", errors="replace").read().strip() or None
    except Exception:
        return None
    return None


def classify(task):
    """image | video, from Deliverable Type option name, else name tokens."""
    for f in task.get("custom_fields", []):
        if f["id"] == F["deliv_type"] and f.get("value") not in (None, ""):
            opts = f.get("type_config", {}).get("options", [])
            try:
                idx = int(f["value"])
                name = next((o["name"] for o in opts if o["orderindex"] == idx), "")
            except (ValueError, TypeError):
                name = next((o["name"] for o in opts if o["id"] == f["value"]), "")
            if "image" in name.lower():
                return "image"
            if name:
                return "video"
    n = task["name"].lower()
    if any(t in n for t in ("_wl_", "video", "_tht", "talent", "ugc", "[", "vsl")):
        return "video"
    return "image"


# ---- claude headless -------------------------------------------------------

PROMPT_TMPL = """You fill Facebook ad launch fields for Shameless Snacks (low-sugar high-fiber gummy candy) ClickUp tasks. Return ONLY a JSON object, no prose, no code fences.

BRAND CANON (hard rules):
- Stats: 26g prebiotic fiber, only 3g sugar, 70 calories, 3g net carbs per bag. Never other numbers.
- Voice: contractions, mixed sentence length, 6th-8th grade. NO em dashes. No "Here's the thing". No corporate verbs.
- CTA pushes the daily-fiber habit, never discounts/urgency.
- NEVER name competitor/supplement brands (Metamucil etc.) in paid copy; genericize ("fiber powder", "gut health capsule").
- No disease/treatment/weight-loss claims. Allowed: prebiotic fiber, food noise, pooping every day.
- Use marketing flavor names (OMG Peach, Wassup Watermelon, Super Sour Blue Raspberry, Green Apple Blast, Red Raspberry Sour Scouts).

TASK NAME: {name}
TASK KIND: {kind}
NAME TOKEN GUIDE: SHA_YYYY_S##_<PRODUCT>_<ANGLE>_<VARIANT>_<TESTTYPE>_Tom_<EDITOR>. PRODUCT: OG=original bag, AS/AllStars=All Stars, CC=Candy Carnival, SVP=Super Variety.

CONTEXT (description / script):
---
{context}
---

LANDING PAGE MAP (pick by angle token in the name; null if no clear match):
- fiber / guthealth / general -> {lp_fiber}
- glp1 / glp-1 -> {lp_glp1}
- swap / craving / candy-swap -> {lp_swap}

FB PAGES (pick one; default "Shameless Snacks (114450944603601)"; use "Better For You Food (102895552862171)" for gut-health/wellness-framed angles):
{pages}

DELIVERABLE TYPE OPTIONS (pick the exact name): {deliv_opts}
PRODUCT OPTIONS (pick the exact name): {product_opts}

Fill ONLY these missing fields: {missing}

Headline: <=60 chars, hook-style, may use 1 emoji. Text: FB primary copy, 3-6 short paragraphs in first person matching the script/description voice; if the context has a 🟥 COPY block, adapt that copy rather than inventing. If the context is too thin to write honest copy, set "headline" and "text" to null. NEVER use em dashes or en dashes anywhere in headline or text; use commas, periods, or plain hyphens instead. No competitor brand names in paid text.

Return JSON with keys (only the requested ones): lp (url string or null), fb_page (exact string from list), headline, text, deliv_type (exact option name), product (exact option name), notes (one line, why/what you based copy on).
"""


def _lint_dashes(v):
    # Hard guarantee: no em/en dashes reach ClickUp copy fields (brand rule).
    if isinstance(v, str):
        v = re.sub(r"\s*—\s*", ", ", v)
        v = re.sub(r"\s+–\s+", ", ", v).replace("–", "-")
    return v


def run_claude(prompt):
    try:
        out = subprocess.run(
            ["claude", "-p", "--model", MODEL, "--output-format", "text"],
            input=prompt, capture_output=True, text=True, timeout=300)
        raw = out.stdout.strip()
        raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.M).strip()
        m = re.search(r"\{.*\}", raw, re.S)
        ans = json.loads(m.group(0)) if m else None
        return {k: _lint_dashes(v) for k, v in ans.items()} if ans else None
    except Exception as e:
        print(f"  claude call failed: {e}")
        return None


# ---- state / ping ----------------------------------------------------------

def load_state():
    try:
        return json.load(open(STATE_FILE))
    except Exception:
        return {"pinged": {}}


def save_state(s):
    json.dump(s, open(STATE_FILE, "w"), indent=1)


def ping_for_script(task, state):
    last = state["pinged"].get(task["id"], 0)
    if time.time() - last < PING_COOLDOWN_DAYS * 86400:
        return
    msg = ("[launch-autofill] This video task has no script I can read "
           "(empty description, no copy block, no Google Doc link). "
           "To fill headline + ad text I need: 1) where does the script live? "
           "2) which LP should it route to? 3) which FB page? "
           "Drop the script in the description or link the Doc and I'll pick it up tomorrow.")
    if DRY_RUN:
        print(f"  DRY: would ping Tomas on {task.get('custom_id', task['id'])}")
    else:
        api("POST", f"/task/{task['id']}/comment",
            body={"comment_text": msg, "assignee": TOMAS_ID, "notify_all": False})
        state["pinged"][task["id"]] = time.time()
        save_state(state)
    print(f"  PING (no script): {task.get('custom_id', task['id'])}")


# ---- main ------------------------------------------------------------------

def main():
    state = load_state()
    opts = deliv_type_options()
    tasks = fetch_tasks()
    print(f"{len(tasks)} tasks in scope")
    filled, pinged, skipped, llm_calls = 0, 0, 0, 0

    for t in tasks:
        cid = t.get("custom_id") or t["id"]
        # "channel" deliberately absent — Tomas 2026-06-12: never touch the
        # 🚨 Channel custom field.
        missing = [k for k in ("lp", "fb_page", "headline", "text",
                               "brand", "product", "deliv_type",
                               "responsible")
                   if field_value(t, F[k]) is None]
        if not missing:
            skipped += 1
            continue

        lp_held = "lp" in missing and lp_on_hold(t["name"])
        if lp_held:
            missing.remove("lp")
            if not missing:
                print(f"{cid}: LP on hold (waiting new LP URL), nothing else missing")
                skipped += 1
                continue

        kind = classify(t)
        desc = (t.get("description") or t.get("text_content") or "").strip()
        context = desc
        copy_fields_needed = any(k in missing for k in ("headline", "text", "lp", "fb_page"))

        if kind == "video" and copy_fields_needed:
            # script source order: 📽️ Script Link custom field (talent/video tasks keep
            # the script there, not the description), then a Doc linked in the
            # description, then a substantial inline description.
            link = field_value(t, F["script_link"])
            doc = fetch_gdoc_text(link) if isinstance(link, str) else None
            if not doc:
                doc = fetch_gdoc_text(desc)
            if doc:
                context = doc[:6000]
            elif len(desc) >= 80:
                context = desc
            else:
                ping_for_script(t, state)
                pinged += 1
                # still fill deterministic taxonomy below, minus copy fields
                missing = [m for m in missing if m in
                           ("brand", "responsible", "product", "deliv_type")]
                if not missing:
                    continue

        hold_note = " (LP on hold: waiting new LP URL)" if lp_held else ""
        print(f"\n{cid} [{kind}] missing: {', '.join(missing)}{hold_note}")
        fields_payload = []

        # deterministic fields, no LLM needed
        if "responsible" in missing:
            fields_payload.append({"id": F["responsible"],
                                   "value": {"add": [RESPONSIBLE_GUID[kind]]}})
        if "brand" in missing:
            idx = opts.get(F["brand"], {}).get("Shameless")
            if idx is not None:
                fields_payload.append({"id": F["brand"], "value": idx})

        llm_keys = [m for m in missing if m in
                    ("lp", "fb_page", "headline", "text", "product", "deliv_type")]
        ans = None
        if llm_keys and llm_calls >= MAX_LLM_CALLS:
            print(f"  SKIP LLM (cap {MAX_LLM_CALLS} reached) — will catch it on a later run")
            llm_keys = []
        if llm_keys:
            llm_calls += 1
            ans = run_claude(PROMPT_TMPL.format(
                name=t["name"], kind=kind, context=context[:6000] or "(empty)",
                lp_fiber=LP_MAP["fiber"], lp_glp1=LP_MAP["glp1"], lp_swap=LP_MAP["swap"],
                pages="\n".join("- " + p for p in FB_PAGES),
                deliv_opts=json.dumps(list(opts.get(F["deliv_type"], {}))),
                product_opts=json.dumps(list(opts.get(F["product"], {}))),
                missing=json.dumps(llm_keys)))
        if ans:
            if "lp" in llm_keys and ans.get("lp"):
                fields_payload.append({"id": F["lp"], "value": ans["lp"]})
                if field_value(t, F["lp_mirror"]) is None:
                    fields_payload.append({"id": F["lp_mirror"], "value": ans["lp"]})
            if "fb_page" in llm_keys and ans.get("fb_page") in FB_PAGES:
                fields_payload.append({"id": F["fb_page"], "value": ans["fb_page"]})
            if "headline" in llm_keys and ans.get("headline"):
                fields_payload.append({"id": F["headline"], "value": ans["headline"]})
            if "text" in llm_keys and ans.get("text"):
                fields_payload.append({"id": F["text"], "value": ans["text"]})
            for key, fid in (("deliv_type", F["deliv_type"]), ("product", F["product"])):
                if key in llm_keys and ans.get(key) in opts.get(fid, {}):
                    fields_payload.append({"id": fid, "value": opts[fid][ans[key]]})
            if ans.get("notes"):
                print(f"  notes: {ans['notes']}")

        if not fields_payload:
            continue
        if DRY_RUN:
            print(f"  DRY: would set {[p['id'][:8] for p in fields_payload]}")
            for p in fields_payload:
                v = json.dumps(p["value"], ensure_ascii=False)
                print(f"    {p['id'][:8]} = {v[:160]}")
        else:
            ok = True
            for p in fields_payload:
                r = api("POST", f"/task/{t['id']}/field/{p['id']}", body={"value": p["value"]})
                ok = ok and r is not None
            # verify a sample field actually persisted
            chk = api("GET", f"/task/{t['id']}")
            persisted = sum(1 for p in fields_payload
                            if chk and any(f["id"] == p["id"] and f.get("value") not in (None, "", [])
                                           for f in chk.get("custom_fields", [])))
            print(f"  wrote {len(fields_payload)} fields, verified {persisted}")
        filled += 1

    print(f"\nDone: {filled} tasks filled, {pinged} pinged, {skipped} already complete, "
          f"{llm_calls}/{MAX_LLM_CALLS} LLM calls")


if __name__ == "__main__":
    main()
