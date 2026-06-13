# test_render_proposals_md.py
import os, subprocess, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "render_proposals_md.py")

def main():
    props = [
        {"id": "prop_a", "kind": "decision", "pattern": "engine SCALE but human KILL when fatigued",
         "support_ids": ["2026-06-01T10:00:00.000Z"], "target": {"type": "rules_overrides", "key": "CM_SCALE"},
         "diff": "CM_SCALE 1.15 -> 1.30", "status": "pending"},
    ]
    inp = "\n".join(json.dumps(p) for p in props)
    out = subprocess.run([sys.executable, SCRIPT], input=inp, capture_output=True, text=True, check=True).stdout
    assert "Proposal" in out and "prop_a" in out and "CM_SCALE" in out, out
    # empty input -> the canonical "no patterns" line
    out2 = subprocess.run([sys.executable, SCRIPT], input="", capture_output=True, text=True, check=True).stdout
    assert "No stable patterns" in out2, out2
    print("OK")

main()
