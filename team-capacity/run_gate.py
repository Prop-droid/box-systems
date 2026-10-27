#!/usr/bin/env python3
"""Estimate gate, every 15 min: pool tasks in 'in progress' with a blank estimate -> back to 'to do' + comment tagging the assignee.
Gated by settings.json writes; otherwise logs what it would do. Log: gate.log (JSONL)."""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as C, clickup as CU, metrics as M
MSG = "Add a time estimate before starting, then move back to in progress."
def main():
    S = C.settings(); now = int(time.time() * 1000)
    tasks = [t for t in CU.list_tasks(now - 30 * 86400000, statuses=[C.S_LIVE]) if M.people(t) and M.status(t) == C.S_LIVE]
    blank = [t for t in tasks if not t.get("time_estimate")]
    with open(C.GATE_LOG, "a") as log:
        for t in blank:
            uid = next((a["id"] for a in t.get("assignees", []) if a["id"] in C.U2C), None)
            rec = {"ms": now, "task": t.get("custom_id"), "id": t["id"], "assignee": uid, "action": "would_revert"}
            if S["writes"]:
                try:
                    CU.update_task(t["id"], {"status": C.S_QUEUE}); CU.comment(t["id"], MSG, assignee=uid); rec["action"] = "reverted"
                except Exception as e: rec["action"] = "error"; rec["err"] = str(e)[:200]
            log.write(json.dumps(rec) + "\n"); print(rec)
    print(f"gate: {len(tasks)} in progress, {len(blank)} blank estimate, writes={S['writes']}")
if __name__ == "__main__": main()
