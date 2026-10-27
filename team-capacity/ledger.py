"""Append-only JSONL ledger per ISO week + pipeline snapshot. Optional Sheet mirror via gws-work."""
import json, os, subprocess
import config as C
def write(label, rows, snapshot, force=False):
    os.makedirs(C.LEDGER_DIR, exist_ok=True)
    p = os.path.join(C.LEDGER_DIR, f"{label}.jsonl")
    if os.path.exists(p) and not force: return False
    with open(p, "w") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    json.dump(snapshot, open(os.path.join(C.LEDGER_DIR, f"{label}.snapshot.json"), "w"), indent=1)
    return True
def mirror_sheet(sheet_id, label, rows):
    if not sheet_id or not rows: return
    cols = list(rows[0].keys())
    vals = [cols] + [[str(r.get(c, "")) for c in cols] for r in rows]
    subprocess.run([C.GWS, "sheets", "+append", "--spreadsheet", sheet_id, "--range", f"{label}!A1", "--values", json.dumps(vals)],
                   capture_output=True, text=True, timeout=120)
