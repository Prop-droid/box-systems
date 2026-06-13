# test_decisions_unpromoted.py
import json, os, subprocess, tempfile, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "decisions_unpromoted.py")

def run(overrides, promoted):
    d = tempfile.mkdtemp()
    olog = os.path.join(d, "overrides.jsonl")
    with open(olog, "w") as f:
        for o in overrides:
            f.write(json.dumps(o) + "\n")
    with open(os.path.join(d, "decisions_promoted.json"), "w") as f:
        json.dump(promoted, f)
    env = {**os.environ, "OVERRIDE_LOG": olog, "FEEDBACK_DIR": d}
    out = subprocess.run([sys.executable, SCRIPT], capture_output=True, text=True, env=env)
    return [json.loads(l) for l in out.stdout.splitlines() if l.strip()]

def main():
    rows = [
        {"ts": "2026-06-01T10:00:00.000Z", "engineVerdict": "SCALE", "humanAction": "KILL", "agree": False, "mode": "executed", "adId": "A", "fatigued": True, "cmRoas": 0.9},
        {"ts": "2026-06-02T10:00:00.000Z", "engineVerdict": "KILL", "humanAction": "KILL", "agree": True, "mode": "executed", "adId": "B"},
        {"ts": "2026-06-03T10:00:00.000Z", "engineVerdict": "SCALE", "humanAction": "KILL", "agree": False, "mode": "dry_run", "adId": "C"},
        {"ts": "2026-06-04T10:00:00.000Z", "engineVerdict": "SCALE", "humanAction": "KILL", "agree": False, "mode": "executed", "adId": "D"},
    ]
    got = run(rows, [])
    keys = {r["key"] for r in got}
    assert keys == {"2026-06-01T10:00:00.000Z", "2026-06-04T10:00:00.000Z"}, keys  # only executed disagreements
    got2 = run(rows, ["2026-06-01T10:00:00.000Z"])
    assert {r["key"] for r in got2} == {"2026-06-04T10:00:00.000Z"}, "promoted key excluded"
    print("OK")

main()
