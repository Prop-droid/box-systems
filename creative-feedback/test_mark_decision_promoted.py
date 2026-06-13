# test_mark_decision_promoted.py
import json, os, subprocess, tempfile, sys
HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "mark_decision_promoted.py")

def main():
    d = tempfile.mkdtemp()
    env = {**os.environ, "FEEDBACK_DIR": d}
    subprocess.run([sys.executable, SCRIPT, "k1", "k2"], env=env, check=True)
    subprocess.run([sys.executable, SCRIPT, "k2", "k3"], env=env, check=True)  # k2 dedup
    got = json.load(open(os.path.join(d, "decisions_promoted.json")))
    assert sorted(got) == ["k1", "k2", "k3"], got
    print("OK")

main()
