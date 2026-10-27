"""Rollover + Mon-Fri spread. Pure: plan(...) returns intended writes; apply lives in run_weekly."""
import config as C
def plan(open_tasks, remaining_h, cap_h, weekday_due_ms, nws, nwe):
    """open_tasks: [{id, custom_id, status, people:[codes], est_h, tracked_h, priority, due_ms}]
    remaining_h: {task_id: hours}; cap_h: {code: hours}; weekday_due_ms: 5 ms stamps Mon..Fri 17:00.
    -> [{id, custom_id, person, due_ms, carried, overflow, remaining_h}]"""
    out = []
    for code in C.POOL:
        mine = [t for t in open_tasks if code in t["people"] and (t["status"] == C.S_LIVE or (t["status"] == C.S_QUEUE and nws <= (t.get("due_ms") or 0) <= nwe))]
        carried = sorted([t for t in mine if t["status"] == C.S_LIVE], key=lambda t: -remaining_h.get(t["id"], t["est_h"]))
        todo = sorted([t for t in mine if t["status"] == C.S_QUEUE], key=lambda t: (t.get("priority") or 9, -t["est_h"]))
        left = cap_h.get(code, C.CAP_H); day = 0; used = 0.0
        for t in carried + todo:
            h = remaining_h.get(t["id"], t["est_h"]) if t["status"] == C.S_LIVE else t["est_h"]
            share = h / max(1, len(t["people"]))
            overflow = False
            while day < 4 and used + share > left / 5 * (day + 1) + 1e-9: day += 1
            if used + share > left + 1e-9: overflow = True; day = 4
            used += share
            out.append({"id": t["id"], "custom_id": t.get("custom_id"), "person": code, "due_ms": weekday_due_ms[day],
                        "carried": t["status"] == C.S_LIVE, "overflow": overflow, "remaining_h": round(h, 1)})
    return out
