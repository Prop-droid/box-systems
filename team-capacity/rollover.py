#!/usr/bin/env python3
"""Weekly rollover, runs right after the report (Tomas 2026-11-09: "after the report is done, change the due dates of
unfinished tasks to this week; change time estimate minus the time tracked last week").

Unfinished = pool task in to do / in progress / needs fixing with a due date before the target Monday.
- due date -> same weekday + Vilnius wall time in the target week (Sat/Sun -> Friday); date-only stays date-only.
- native time estimate -> estimate minus the time tracked since this task's last cut. First cut = everything tracked
  to date (no earlier week was ever subtracted). Floored at MIN_EST_H so an estimate never blanks (blank trips the
  estimate gate); never raised; untouched when nothing was tracked or no estimate is set.
- blocked / backlog / handed-off tasks are untouched. No tags, no extra fields.
Each cut is appended to ledger/rollover.jsonl. The first cut's est_before_ms is the ORIGINAL estimate, which the weekly
report keeps using (orig_estimates) so "estimated on finished" does not shrink when a task carries over.

Timer: rollover.py --auto (Mon 07:10 Vilnius, after the DM; writes only if settings.json rollover_writes; Sat/Sun = skip).
Manual: python3 rollover.py --target 2026-11-09 [--cutoff 2026-11-09] [--apply]   (plan only without --apply)"""
import argparse, json, os, subprocess, sys, time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as C, clickup as CU, metrics as M, weeks as W

ROLL = (C.S_QUEUE, C.S_LIVE, C.S_FIX)
MIN_EST_H = 1.0
H = 3.6e6
LEDGER = os.path.join(C.LEDGER_DIR, "rollover.jsonl")
# ClickUp stores a date-only due date as 04:00 in the setter's timezone (team: LT, TR, AR, CO, PH)
SETTER_TZS = [ZoneInfo(z) for z in ("Europe/Vilnius", "Europe/Istanbul", "America/Argentina/Buenos_Aires", "America/Bogota", "Asia/Manila")]

def cuts(path=LEDGER):
    """{task_id: [cut, ...]} in file order."""
    out = {}
    if os.path.exists(path):
        for line in open(path):
            try: r = json.loads(line)
            except Exception: continue
            out.setdefault(r["id"], []).append(r)
    return out

def orig_estimates(path=LEDGER):
    """{task_id: estimate ms before its first cut}."""
    return {tid: cs[0]["est_before_ms"] for tid, cs in cuts(path).items() if cs[0].get("est_before_ms")}

def date_only(due_ms):
    return any(datetime.fromtimestamp(due_ms / 1000, z).strftime("%H:%M:%S") == "04:00:00" for z in SETTER_TZS)

def shift_due(due_ms, target_mon_ms):
    """Same weekday + Vilnius wall time in the target week; Sat/Sun -> Friday."""
    d = W.from_ms(due_ms); mon = W.from_ms(target_mon_ms)
    return W.ms(datetime.combine((mon + timedelta(days=min(d.weekday(), 4))).date(), d.time(), W.TZ))

def tracked_ms(intervals, cutoff_ms):
    """All users' timer time on the task up to cutoff. intervals: [(uid, start, end, src)]."""
    return sum(min(e, cutoff_ms) - s for _, s, e, _ in intervals if s < cutoff_ms)

def new_estimate(est_ms, delta_ms):
    if not est_ms or not delta_ms: return est_ms
    return int(min(est_ms, max(MIN_EST_H * H, est_ms - delta_ms)))

def plan(tasks, intervals, ledger_cuts, cutoff_ms, target_mon_ms):
    out = []
    for t in tasks:
        due = int(t.get("due_date") or 0)
        if not due or due >= target_mon_ms or M.status(t) not in ROLL or not M.people(t): continue
        prev = (ledger_cuts.get(t["id"]) or [None])[-1]
        tot = tracked_ms(intervals.get(t["id"], []), cutoff_ms)
        delta = max(0, tot - (prev["tracked_total_ms"] if prev else 0))
        est = int(t.get("time_estimate") or 0)
        out.append({"id": t["id"], "custom_id": t.get("custom_id"), "status": M.status(t), "people": sorted(M.people(t)),
                    "kind": M.kind(t), "due_old": due, "due_new": shift_due(due, target_mon_ms), "date_only": date_only(due),
                    "est_before_ms": est, "est_after_ms": new_estimate(est, delta), "tracked_total_ms": tot, "delta_ms": delta,
                    "first_cut": prev is None})
    return out

def apply(rows, label, cutoff_ms, path=LEDGER):
    """Write each row, log the cut, read it back. -> (verified, failed)."""
    ok, bad = [], []
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        for r in rows:
            body = {"due_date": r["due_new"], "due_date_time": not r["date_only"]}
            if r["est_after_ms"] != r["est_before_ms"]: body["time_estimate"] = r["est_after_ms"]
            try: CU.update_task(r["id"], body)
            except Exception as e: bad.append(dict(r, err=str(e)[:200])); continue
            rec = dict(r, week=label, cut_ms=cutoff_ms, applied_ms=int(time.time() * 1000))
            f.write(json.dumps(rec) + "\n"); f.flush()
            try:
                back = CU.req("GET", f"/task/{r['id']}")
                good = int(back.get("due_date") or 0) == r["due_new"] and int(back.get("time_estimate") or 0) == int(r["est_after_ms"] or 0)
            except Exception as e: good = False; rec["err"] = str(e)[:200]
            (ok if good else bad).append(rec)
    return ok, bad

def run(target_mon_ms, cutoff_ms, writes):
    """Pull unfinished pool tasks due before target Monday -> plan -> (apply). -> (label, rows, verified, failed)."""
    label = W.iso_label(W.from_ms(target_mon_ms))[0]
    tasks = [t for t in CU.list_tasks(0, statuses=list(ROLL)) if M.people(t)]
    cand = [t for t in tasks if 0 < int(t.get("due_date") or 0) < target_mon_ms]
    ivs = CU.intervals_for([t for t in cand if (t.get("time_spent") or 0) > 0])
    rows = plan(cand, ivs, cuts(), cutoff_ms, target_mon_ms)
    if not writes or not rows: return label, rows, [], []
    ok, bad = apply(rows, label, cutoff_ms)
    return label, rows, ok, bad

def fmt_row(r):
    e0, e1 = r["est_before_ms"] / H, (r["est_after_ms"] or 0) / H
    est = f"{e0:g}h -> {e1:.2f}h (tracked {r['delta_ms'] / H:.2f}h)" if r["est_after_ms"] != r["est_before_ms"] else f"{e0:g}h unchanged"
    return (f"{r['custom_id']} {r['status']} {','.join(r['people'])} due {W.from_ms(r['due_old']):%a %d %b} -> "
            f"{W.from_ms(r['due_new']):%a %d %b} | est {est}")

def summary(label, rows, ok, bad, writes):
    cut = [r for r in rows if r["est_after_ms"] != r["est_before_ms"]]
    floored = [r for r in cut if r["est_before_ms"] - r["delta_ms"] < MIN_EST_H * H]
    head = f"Rollover {label}: {len(rows)} unfinished tasks -> this week, {len(cut)} estimates cut (-{sum(r['est_before_ms'] - r['est_after_ms'] for r in cut) / H:.1f}h)"
    if floored: head += f", {len(floored)} floored to {MIN_EST_H:g}h (under {MIN_EST_H:g}h left or already over)"
    return head + (f"; verified {len(ok)}, failed {len(bad)}" if writes else " (plan only)")

def notify(title, body, prio="default"):
    subprocess.run([os.path.expanduser("~/systems/lib/tg-notify.sh"), title, body, prio], capture_output=True, timeout=60)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--target", help="target Monday YYYY-MM-DD")
    ap.add_argument("--cutoff", help="count tracked time up to (YYYY-MM-DD[THH:MM], Vilnius); default = target Monday 00:00")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--auto", action="store_true", help="timer mode: this week's Monday, writes = settings.json rollover_writes")
    a = ap.parse_args()
    now = datetime.now(W.TZ)
    if a.auto:
        if now.weekday() >= 5: print("weekend: skipped, Monday's run catches up"); return
        mon, writes = W.ms(W.monday_of(now)), bool(C.settings().get("rollover_writes"))
    elif a.target: mon, writes = W.ms(datetime.fromisoformat(a.target).replace(tzinfo=W.TZ)), a.apply
    else: ap.error("--target or --auto")
    cutoff = W.ms(datetime.fromisoformat(a.cutoff).replace(tzinfo=W.TZ)) if a.cutoff else mon
    try: label, rows, ok, bad = run(mon, cutoff, writes)
    except Exception as e:
        if a.auto: notify("team-capacity rollover FAILED, nothing written", str(e)[:800], "high")
        raise
    lines = [fmt_row(r) for r in sorted(rows, key=lambda r: (r["status"], r["custom_id"] or ""))]
    lines += [f"FAILED {r.get('custom_id')} {r.get('err', 'read-back mismatch')}" for r in bad]
    head = summary(label, rows, ok, bad, writes)
    print("\n".join(lines + [head]))
    if a.auto and rows:
        notify(f"team-capacity {head}", "\n".join(lines)[:1800], "high" if bad else "default")
    if bad: sys.exit(1)
if __name__ == "__main__": main()
