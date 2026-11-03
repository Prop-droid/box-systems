"""tests/harness.py: run the fake dashboard and tablet-voice on the test ports only (dash :18765, voice :18766).

The test host defaults to 127.0.0.2 (TV_TEST_HOST overrides it): the page track's staged dashboard and mock box
hold 127.0.0.1:18765 and 127.0.0.1:18766 while it runs, and its port check binds 127.0.0.1 only, so the same
ports on a second loopback address never collide with it. Box clients that connect to 127.0.0.2 without
binding a source still arrive from 127.0.0.1 (the kernel's source for 127.0.0.0/8), so the peer allowlist
behaves as in production. Every process runs under timeout(1) and is stopped by closing its stdin; this code
sends no signals. FULLY_PW is never passed through from the caller's environment."""
import json
import os
import socket
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = str(ROOT / ".venv/bin/python")
HOST = os.environ.get("TV_TEST_HOST", "127.0.0.2")
VOICE_PORT, DASH_PORT = 18766, 18765
VOICE_URL = f"ws://{HOST}:{VOICE_PORT}/"
HTTP = f"http://{HOST}:{VOICE_PORT}"
DASH = f"http://{HOST}:{DASH_PORT}"


def port_busy(port) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex((HOST, port)) == 0


class Proc:
    def __init__(self, args, env, log_path, limit_s):
        self.log_path = Path(log_path)
        self.log = open(log_path, "a")
        self.p = subprocess.Popen(["timeout", str(int(limit_s)), *args], stdin=subprocess.PIPE, stdout=self.log,
                                  stderr=subprocess.STDOUT, env=env, cwd=str(ROOT))

    def alive(self) -> bool:
        return self.p.poll() is None

    def stop(self, wait=30):
        try:
            self.p.stdin.close()
        except OSError:
            pass
        try:
            self.p.wait(wait)
        except subprocess.TimeoutExpired:
            pass   # timeout(1) ends it at its limit
        self.log.close()
        return self.p.returncode

    def child_pid(self):
        """pid of the python process under timeout(1)."""
        try:
            kids = Path(f"/proc/{self.p.pid}/task/{self.p.pid}/children").read_text().split()
            return int(kids[0]) if kids else None
        except (OSError, ValueError):
            return None


def proc_mem(pid) -> dict:
    out = {}
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith(("VmRSS:", "VmHWM:", "Threads:")):
                k, v = line.split(":", 1)
                out[k] = int(v.split()[0]) / 1024 if k != "Threads" else int(v)
    except OSError:
        pass
    return out


def proc_cpu_s(pid) -> float:
    try:
        f = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return (int(f[11]) + int(f[12])) / os.sysconf("SC_CLK_TCK")
    except (OSError, IndexError, ValueError):
        return float("nan")


def get_json(url, timeout=3):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def wait_health(limit_s=60):
    t0 = time.time()
    while time.time() - t0 < limit_s:
        try:
            return get_json(HTTP + "/health")
        except OSError:
            time.sleep(0.25)
    return None


def start_dash(out_dir, limit_s=1800):
    assert not port_busy(DASH_PORT), "port 18765 busy"
    env = {k: v for k, v in os.environ.items() if k != "FULLY_PW"}
    p = Proc([PY, "tests/fake_dash.py", "--host", HOST, "--port", str(DASH_PORT)], env, Path(out_dir) / "fake_dash.out", limit_s)
    for _ in range(40):
        if port_busy(DASH_PORT):
            return p
        time.sleep(0.25)
    raise RuntimeError("fake dash did not start")


def start_voice(out_dir, name, env_over=None, limit_s=900, wait=True):
    assert not port_busy(VOICE_PORT), "port 18766 busy"
    log_dir = Path(out_dir) / f"logs-{name}"
    log_dir.mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if k != "FULLY_PW"}
    env.update({"VOICE_HOST": HOST, "VOICE_PORT": str(VOICE_PORT), "VOICE_DASH": DASH,
                "VOICE_LOG_DIR": str(log_dir), "VOICE_EXIT_ON_STDIN_EOF": "1", "HF_HUB_OFFLINE": "1",
                "PYTHONUNBUFFERED": "1", "VOICE_STAGE": "pipeline", "VOICE_DRY_RUN": "1",
                "VOICE_TTS_VIA": "auto", "VOICE_OWW_REJECT": "0", "VOICE_REQUIRE_FULLY_FOR_WAKE": "1",
                "VOICE_ALLOW_COMPLETE": "0", "VOICE_READ_NEEDS_WAKE_TEXT": "0"})
    env.update(env_over or {})
    p = Proc([PY, "server.py"], env, Path(out_dir) / f"server-{name}.out", limit_s)
    p.log_dir = log_dir
    if wait:
        h = wait_health()
        if h is None:
            p.stop()
            raise RuntimeError(f"server {name} did not answer /health")
        p.health0 = h
    return p


def read_log(log_dir) -> list:
    out = []
    for f in sorted(Path(log_dir).glob("sessions-*.jsonl")):
        for ln in f.read_text().splitlines():
            try:
                out.append(json.loads(ln))
            except ValueError:
                pass
    return out


def flite(text, voice, path):
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-f", "lavfi", "-i", f"flite=text='{text}':voice={voice}",
                    "-ar", "16000", "-ac", "1", "-y", str(path)], check=True, timeout=60)
