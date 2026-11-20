#!/usr/bin/env python3
"""Weekly job (Saturday 06:00 Vilnius): pull -> metrics -> ledger -> spread plan (log only) -> report -> deliver.
The rollover (due dates -> this week, estimate minus tracked) is rollover.py, Monday 07:10 after the DM (no weekend ClickUp pings).
Flags: --dry-run (no ClickUp writes, no delivery, print report) --window START END (YYYY-MM-DD, inclusive; replay) --force (rewrite ledger).
settings.json: post_team (Discord #creative vs Tomas-only ops-log), doc_id, sheet_id. (writes = estimate gate only; rollover_writes = rollover.py)"""
import argparse, json, os, sys, subprocess, time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as C, clickup as CU, weeks as W, metrics as M, capacity as CAP, calendar_pull as CALP, spread as SP, ledger as LG, report as R, outputs as O, rollover as RO
TZ = ZoneInfo(C.TZ)
def alert(title, body):
    subprocess.run([os.path.expanduser("~/systems/lib/tg-notify.sh"), title, body, "high"], capture_output=True, timeout=60)
def iso(ms): return W.from_ms(ms).isoformat()
def gate_reverts_in(ws, we):
    if not os.path.exists(C.GATE_LOG): return 0
    n = 0
    for line in open(C.GATE_LOG):
        try: r = json.loads(line)
        except Exception: continue
        if ws <= r.get("ms", 0) <= we and r.get("action") == "reverted": n += 1
    return n
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--window", nargs=2); ap.add_argument("--force", action="store_true")
    a = ap.parse_args(); S = C.settings(); now = datetime.now(TZ)
    state = json.load(open(C.STATE)) if os.path.exists(C.STATE) else {}
    if a.window:
        ws = W.ms(datetime.fromisoformat(a.window[0]).replace(tzinfo=TZ)); we = W.ms(datetime.fromisoformat(a.window[1]).replace(tzinfo=TZ) + timedelta(days=1)) - 1
        nws, nwe = we + 1, we + 7 * 86400000
    else:
        ws, we = W.window(now, state.get("last_end_ms")); nws, nwe = W.next_week(now)
    label, wk, hdr_ws = W.label_for(we); sprint = f"S{wk}"   # label by window END week; header range starts at that week's Monday
    print(f"[{now:%F %T}] window {iso(ws)} -> {iso(we)} label {label} dry_run={a.dry_run} writes={S['writes']}", flush=True)
    try:
        tasks = CU.list_tasks(ws - 14 * 86400000)
        tasks = [t for t in tasks if M.people(t)]
        orig = RO.orig_estimates()   # report keeps the pre-rollover estimate
        for t in tasks:
            if t["id"] in orig: t["_orig_estimate"] = orig[t["id"]]
        hist = CU.bulk_time_in_status([t["id"] for t in tasks])
        cand = [t for t in tasks if (t.get("time_spent") or 0) > 0 and int(t.get("date_updated") or 0) >= ws]
        ivs = CU.intervals_for(cand)
        try:
            ooo, hol = CALP.pull(iso(ws), iso(we)); nooo, nhol = CALP.pull(iso(nws), iso(nwe)); cal_ok = True
        except Exception as e:
            print("calendar failed:", e); ooo = hol = nooo = nhol = []; cal_ok = False
    except Exception as e:
        alert("team-capacity: pull failed, nothing written", str(e)[:800]); print("ABORT", e); sys.exit(2)
    print(f"tasks {len(tasks)} hist {len(hist)} interval-tasks {len(ivs)} ooo {len(ooo)} hol {len(hol)}", flush=True)
    days = CAP.days_off(ooo, hol); cap = CAP.capacity(days)
    ndays = CAP.days_off(nooo, nhol); ncap = CAP.capacity(ndays)
    air = None if a.dry_run and os.environ.get("NO_AIR") else O.air_count
    m = M.compute(tasks, hist, ivs, ws, we, nws, nwe, air_counter=air)
    # ledger rows: person x task x week for finished + live/queue tasks with activity
    rows = []
    for f in m["finished"]:
        for p in f["people"]:
            rows.append({"week": label, "person": p, "task": f["id"], "name": f["name"], "type": f["type"], "kind": f["kind"], "status": f["status"],
                         "estimate_h": round(f["est"], 2), "tracked_h": round(f["tracked"] / len(f["people"]), 2), "finished": True, "output": f["output"],
                         "handoff": iso(f["handoff_ms"]), "days_off_h": round(sum(h for _, h, _ in days.get(p, [])), 1)})
    snapshot = {"week": label, "run": now.isoformat(), "kinds": m["kinds"], "per": m["per"], "open": m["open"], "capacity": cap, "days_off": days}
    if not a.dry_run:
        wrote = LG.write(label, rows, snapshot, force=a.force)
        if not wrote and not a.force: print(f"ledger {label} exists; skipping (use --force)"); 
        elif S.get("sheet_id"): LG.mirror_sheet(S["sheet_id"], label, rows)
    # Mon-Fri spread plan for next week: journal only. The old tag/"Remaining h" apply path is gone (no tags on CS tasks);
    # the real rollover is rollover.py on Monday.
    open_tasks = []
    for t in tasks:
        st = M.status(t)
        if st in (C.S_LIVE, C.S_QUEUE):
            tr_life = (t.get("time_spent") or 0) / 3.6e6
            open_tasks.append({"id": t["id"], "custom_id": t.get("custom_id"), "status": st, "people": sorted(M.people(t)), "est_h": M.est_h(t) or C.DEFAULT_EST_H[M.kind(t)],
                               "tracked_h": tr_life, "priority": int(((t.get("priority") or {}).get("orderindex") or 9)) if t.get("priority") else 9, "due_ms": int(t.get("due_date") or 0)})
    remaining = {o["id"]: max(0.0, o["est_h"] - o["tracked_h"]) for o in open_tasks if o["status"] == C.S_LIVE}
    plan = SP.plan(open_tasks, remaining, ncap, W.weekdays_1700(nws), nws, nwe)
    print(f"spread plan (log only): {len(plan)} tasks, carried {sum(p['carried'] for p in plan)}, overflow {sum(p['overflow'] for p in plan)}")
    for p in plan: print("  ", p["person"], p["custom_id"], W.from_ms(p["due_ms"]).strftime("%a %d"), "carried" if p["carried"] else "todo", f"{p['remaining_h']}h", "OVERFLOW" if p["overflow"] else "")
    # report
    reverts = gate_reverts_in(ws, we)
    draft = R.render(sprint, hdr_ws, we, m, days, cap, reverts, "(pending)", label)
    ins = (R.claude_insights(draft, m["open"]) if not a.dry_run else None) or R.fallback_insights(m, cap)
    text = R.render(sprint, hdr_ws, we, m, days, cap, reverts, ins, label)
    if not cal_ok: text += "\nNote: calendar feed failed, days-off not applied."
    print("\n" + text + "\n")
    if a.dry_run: return
    notes = R.deliver(text, label, S["post_team"], S.get("doc_id"))
    print("; ".join(notes))
    state.update({"last_end_ms": we, "last_label": label, "last_run": now.isoformat()}); json.dump(state, open(C.STATE, "w"), indent=1)
if __name__ == "__main__": main()
