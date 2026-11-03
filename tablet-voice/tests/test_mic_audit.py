#!/usr/bin/env python3
"""tests/test_mic_audit.py: off-line proof of mic_audit.sh (spec 14 V7), with no device and no network.

adb is tests/fake_adb.sh (it runs the audit's own device command string against realistic fake dumps), the
alert poster is a stub that records its arguments, and every state file lives in a temporary folder (HOME
points there too). The socket check reads a real tablet-voice /health on the test port (127.0.0.1:18766 unless
TV_TEST_HOST says otherwise), started under timeout and stopped by closing its stdin.

  timeout 600 .venv/bin/python tests/test_mic_audit.py [--out DIR]   (exit 0 = all pass)
"""
import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness as H  # noqa: E402
from websockets.asyncio.client import connect  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
AUDIT = ROOT / "mic_audit.sh"
FAKE_ADB = ROOT / "tests/fake_adb.sh"
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append({"name": name, "ok": bool(ok), "detail": str(detail)[:400]})
    print(f"{'PASS' if ok else 'FAIL'} {name}{': ' + str(detail)[:300] if detail else ''}", flush=True)


class Box:
    """One temporary world: state folder, flags file, notify stub, adb log."""

    def __init__(self, root: Path, name: str, notify_ok=True):
        self.dir = root / name
        self.state = self.dir / "state"
        self.dir.mkdir(parents=True)
        self.flags = self.dir / "flags.json"
        self.notify_log = self.dir / "notify.log"
        self.adb_log = self.dir / "adb.log"
        self.notify = self.dir / "notify.sh"
        self.notify.write_text("#!/bin/bash\nprintf '%s\\t%s\\n' \"$1\" \"$2\" >> " + str(self.notify_log)
                               + ("\nexit 0\n" if notify_ok else "\nexit 1\n"))
        self.notify.chmod(0o755)
        self.set_flags(enabled=False, ws=False)

    def set_flags(self, **kw):
        self.flags.write_text(json.dumps(kw))

    def run(self, hour=14, extra=None, timeout=60):
        env = {"PATH": "/usr/bin:/bin", "HOME": str(self.dir), "LANG": "C.UTF-8", "ADB_BIN": str(FAKE_ADB),
               "NOTIFY": str(self.notify), "STATE_DIR": str(self.state), "FLAGS_FILE": str(self.flags),
               "HEALTH_URL": f"http://{H.HOST}:{H.VOICE_PORT}/health", "NOW_HOUR": str(hour), "CONFIRM_S": "0.2",
               "FAKEADB_LOG": str(self.adb_log), "TABLET_ADB": "fake-serial:5555"}
        env.update(extra or {})
        r = subprocess.run(["bash", str(AUDIT)], env=env, capture_output=True, text=True, timeout=timeout)
        lines = [ln for ln in r.stdout.splitlines() if ln.startswith("{")]
        j = json.loads(lines[-1]) if lines else {}
        return r, j

    def posts(self):
        return self.notify_log.read_text().splitlines() if self.notify_log.exists() else []

    def files(self):
        return sorted(p.name for p in self.state.glob("*")) if self.state.exists() else []


async def tablet_socket(hold_s):
    """A tablet peer (127.0.0.3, admitted through the tablet-ip file) that holds a socket for hold_s."""
    async with connect(H.VOICE_URL, origin="http://localhost:8765", local_addr=("127.0.0.3", 0), open_timeout=10) as ws:
        await ws.send(json.dumps({"type": "hello", "v": 1, "client": "dash", "build": "t", "rate": 16000, "frame": 1280,
                                  "lit": True, "fully": True, "tts": "off"}))
        await ws.recv()
        await asyncio.sleep(hold_s)


def main(out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="micaudit-", dir=str(out)))
    lit = {"FAKEADB_TOP": "fully", "FAKEADB_AWAKE": "Awake", "FAKEADB_REC": "1"}
    dark = {"FAKEADB_TOP": "screensaver", "FAKEADB_AWAKE": "Awake", "FAKEADB_REC": "0"}

    # 1. lit with the mic open: ok, and the first run records the versions without an alert
    b = Box(root, "basic")
    r, j = b.run(extra=lit)
    check("1 lit, Fully recording: top fully, fully_recording 1, verdict ok (the V7 lit read)",
          r.returncode == 0 and j.get("top") == "fully" and j.get("fully_recording") == 1 and j.get("verdict") == "ok"
          and j.get("awake") == "Awake" and j.get("act") == "de.ozerov.fully/.FullyActivity", r.stdout.strip())
    check("1b the line carries the spec's literal forms '\"top\": \"fully\"' and '\"fully_recording\": 1'",
          '"top": "fully"' in r.stdout and '"fully_recording": 1' in r.stdout)
    vers = (b.state / "tablet-voice-versions").read_text() if (b.state / "tablet-voice-versions").exists() else ""
    check("1c first run records WebView and Fully versions (first versionName line), no alert",
          vers == "webview=156.0.8078.47\nfully=1.60.1\n" and not b.posts() and j.get("wv") == "156.0.8078.47"
          and j.get("fully_v") == "1.60.1", repr(vers))
    # 2. screensaver, released
    r, j = b.run(extra=dark)
    check("2 screensaver, no recorder: top screensaver, fully_recording 0, verdict ok (the V7 dark read)",
          j.get("top") == "screensaver" and j.get("fully_recording") == 0 and j.get("verdict") == "ok", r.stdout.strip())
    # 3. violation, confirmed, alerted once a day
    r, j = b.run(extra={**dark, "FAKEADB_REC": "1"})
    p1 = b.posts()
    check("3 screensaver with Fully recording, confirmed by the second read: VIOLATION, one alert",
          j.get("verdict") == "VIOLATION" and len(p1) == 1 and "microphone open while dark" in p1[0]
          and "screensaver" in p1[0], r.stdout.strip() + " | " + " / ".join(p1))
    r, j = b.run(extra={**dark, "FAKEADB_REC": "1"})
    check("3b the same day again: VIOLATION logged, no second alert", j.get("verdict") == "VIOLATION" and len(b.posts()) == 1,
          len(b.posts()))
    adb_calls = b.adb_log.read_text().splitlines()
    check("3c a hit is read twice (one confirm read), all through the stub",
          sum(1 for c in adb_calls if "dumpsys audio" in c) >= 2 and all(c.startswith(("connect", "-s fake-serial")) for c in adb_calls),
          f"{len(adb_calls)} stub calls")
    # 4. transient: the confirm read shows the release
    seq = b.dir / "seq.txt"
    seq.write_text("screensaver Awake 1\nscreensaver Awake 0\n")
    n0 = len(b.posts())
    r, j = b.run(extra={"FAKEADB_SEQ": str(seq)})
    check("4 a hit that the confirm read does not repeat: verdict ok, transient true, no alert",
          j.get("verdict") == "ok" and j.get("transient") is True and len(b.posts()) == n0 and "VIOLATION" not in r.stdout,
          r.stdout.strip())
    # 5, 6. another app on top; screen off
    c = Box(root, "other")
    r, j = c.run(extra={"FAKEADB_TOP": "other", "FAKEADB_REC": "1"})
    check("5 another app on top while Fully records: VIOLATION, alert",
          j.get("verdict") == "VIOLATION" and j.get("top") == "other" and len(c.posts()) == 1, r.stdout.strip())
    d = Box(root, "screenoff")
    r, j = d.run(extra={"FAKEADB_TOP": "fully", "FAKEADB_AWAKE": "Asleep", "FAKEADB_REC": "1"})
    check("6 screen off (mWakefulness=Asleep) while Fully records: VIOLATION, alert",
          j.get("verdict") == "VIOLATION" and j.get("awake") == "Asleep" and len(d.posts()) == 1, r.stdout.strip())
    r, j = d.run(extra={"FAKEADB_TOP": "none", "FAKEADB_AWAKE": "Asleep", "FAKEADB_REC": "0"})
    check("6b screen off, no resumed activity, no recorder: top none, verdict ok", j.get("top") == "none" and j.get("verdict") == "ok",
          r.stdout.strip())
    # 7. night: recording allowed after a touch, logged as night_rec
    e = Box(root, "night")
    r, j = e.run(hour=23, extra=lit)
    check("7 23:00, lit, Fully recording: verdict night_rec, night true, no alert",
          j.get("verdict") == "night_rec" and j.get("night") is True and not e.posts(), r.stdout.strip())
    r, j = e.run(hour=7, extra=dark)
    check("7b 07:00 dark: night true, verdict ok", j.get("night") is True and j.get("verdict") == "ok")
    # 8, 9. only the RecordActivityMonitor section counts
    f = Box(root, "range")
    r, j = f.run(extra={**lit, "FAKEADB_REC": "0"})
    check("8 Fully named only in the event logs around the section (past sessions, playback): fully_recording 0",
          j.get("fully_recording") == 0 and j.get("verdict") == "ok", r.stdout.strip())
    r, j = f.run(extra={**dark, "FAKEADB_OTHER": "1"})
    check("9 another app's active recorder under the screensaver: not counted, verdict ok",
          j.get("fully_recording") == 0 and j.get("verdict") == "ok", r.stdout.strip())
    r, j = f.run(extra={**lit, "FAKEADB_REC": "2"})
    check("9b two Fully clients counted as 2", j.get("fully_recording") == 2)
    # 10. version change: once, with the V14 cue; then recorded
    r, j = b.run(extra={**lit, "FAKEADB_WV": "157.0.8100.12"})
    check("10 versions are not re-read within the hour (no alert from a changed device value yet)",
          not any("version" in x for x in b.posts()) and j.get("wv") == "156.0.8078.47")
    os.utime(b.state / "tablet-voice-versions", (time.time() - 3700, time.time() - 3700))
    r, j = b.run(extra={**lit, "FAKEADB_WV": "157.0.8100.12"})
    vp = [x for x in b.posts() if "version" in x.lower()]
    check("10b an hour later the new WebView version alerts once, names both versions and the V14 regression",
          len(vp) == 1 and "156.0.8078.47 to 157.0.8100.12" in vp[0] and "V14 regression" in vp[0]
          and (b.state / "tablet-voice-versions").read_text().startswith("webview=157.0.8100.12"), vp)
    os.utime(b.state / "tablet-voice-versions", (time.time() - 3700, time.time() - 3700))
    r, j = b.run(extra={**lit, "FAKEADB_WV": "157.0.8100.12"})
    check("10c the next hourly read with the same versions: no second alert",
          len([x for x in b.posts() if "version" in x.lower()]) == 1)
    # 11, 12. the spec's DRY_RUN lines: alert text printed, nothing posted, no state written
    g = Box(root, "dry")
    r, j = g.run(extra=lit)
    snap0 = {p.name: p.read_bytes() for p in g.state.glob("*")}
    m0 = {p.name: p.stat().st_mtime_ns for p in g.state.glob("*")}
    r, j = g.run(extra={**lit, "DRY_RUN": "1", "FAKE_TOP": "screensaver", "FAKE_REC": "1"})
    check("11 DRY_RUN=1 FAKE_TOP=screensaver FAKE_REC=1: 'DRY_RUN alert:' with the violation, verdict VIOLATION, nothing posted",
          "DRY_RUN alert:" in r.stdout and "microphone open while dark" in r.stdout and j.get("verdict") == "VIOLATION"
          and not g.posts(), r.stdout.strip())
    r, j = g.run(extra={**lit, "DRY_RUN": "1", "FAKE_WV": "0.0"})
    check("12 DRY_RUN=1 FAKE_WV=0.0: 'DRY_RUN alert:' naming the version change and the V14 regression, nothing posted",
          "DRY_RUN alert:" in r.stdout and "version changed" in r.stdout and "0.0" in r.stdout and "V14" in r.stdout
          and not g.posts(), r.stdout.strip())
    check("12b DRY_RUN wrote no state (same files, same bytes, same mtimes)",
          {p.name: p.read_bytes() for p in g.state.glob("*")} == snap0 and {p.name: p.stat().st_mtime_ns for p in g.state.glob("*")} == m0,
          g.files())
    # 13. adb down: a line, no alert
    h = Box(root, "adbdown")
    r, j = h.run(extra={"FAKEADB_DOWN": "1"})
    check("13 adb down: verdict adb_down, exit 0, no alert", r.returncode == 0 and j.get("verdict") == "adb_down" and not h.posts(),
          r.stdout.strip())
    # 14. unreadable recorder section: retried, then read_error, alerted once a day
    k = Box(root, "readerr")
    r, j = k.run(extra={**lit, "FAKEADB_NOHEADER": "1"})
    r2, j2 = k.run(extra={**lit, "FAKEADB_NOHEADER": "1"})
    check("14 dumpsys audio without RecordActivityMonitor (twice): read_error, never 'no recorder', one alert a day",
          j.get("verdict") == "read_error" and j.get("fully_recording") is None and j2.get("verdict") == "read_error"
          and len(k.posts()) == 1 and "blind" in k.posts()[0], r.stdout.strip())
    # 15. a failed post is retried next run (the key is only recorded after a successful post)
    m = Box(root, "notifyfail", notify_ok=False)
    m.run(extra={**dark, "FAKEADB_REC": "1"})
    keys = (m.state / "tablet-voice-micaudit-last").read_text() if (m.state / "tablet-voice-micaudit-last").exists() else ""
    check("15 a failed alert post records no key, so the next run tries again", "violation:" not in keys, repr(keys))

    # 16 to 19. the socket check, by day while lit, flags enabled and ws
    s = Box(root, "sock")
    s.set_flags(enabled=True, ws=True)
    runs = [s.run(extra={**lit, "FAKE_SOCK": "false"})[1] for _ in range(3)]
    check("16 three lit daytime runs without a socket: nosock_run 1, 2, 3 and one alert at the third",
          [x.get("nosock_run") for x in runs] == [1, 2, 3] and len([p for p in s.posts() if "no socket" in p]) == 1
          and runs[2].get("sock") is False, [x.get("nosock_run") for x in runs])
    r, j = s.run(extra={**lit, "FAKE_SOCK": "false"})
    check("16b a fourth run the same day: no second alert", len([p for p in s.posts() if "no socket" in p]) == 1)
    r, j = s.run(extra={**lit, "FAKE_SOCK": "true"})
    check("16c the socket is back: nosock_run 0", j.get("nosock_run") == 0 and j.get("sock") is True)
    t = Box(root, "sock2")
    t.set_flags(enabled=True, ws=True)
    t.run(extra={**lit, "FAKE_SOCK": "false"})
    t.run(extra=dark)
    r, j = t.run(extra={**lit, "FAKE_SOCK": "false"})
    check("17 a dark run in between breaks the row (three in a row means consecutive runs)",
          j.get("nosock_run") == 1 and not t.posts(), j.get("nosock_run"))
    r, j = t.run(hour=23, extra={**lit, "FAKE_SOCK": "false"})
    check("17b no socket check at night (the night rule keeps the page off the socket)", j.get("sock") is None)
    u = Box(root, "flagsoff")
    r, j = u.run(extra={**lit, "FAKE_SOCK": "false"})
    check("18 flags without enabled and ws: no socket check", j.get("sock") is None and j.get("nosock_run") == 0)
    # 19. the real /health on the test port: down, false, true
    s.set_flags(enabled=True, ws=True)
    assert not H.port_busy(H.VOICE_PORT), "test port busy"
    r, j = s.run(extra=lit)
    check(f"19 /health unreachable ({H.HOST}:{H.VOICE_PORT}): sock \"down\"", j.get("sock") == "down", j.get("sock"))
    ipf = s.dir / "tablet-ip"
    ipf.write_text("127.0.0.3\n")
    p = H.start_voice(s.dir, "health", {"VOICE_STAGE": "skeleton", "VOICE_TABLET_IP_FILE": str(ipf)}, limit_s=120)
    try:
        r, j = s.run(extra=lit)
        check("19b real tablet-voice /health, no tablet socket: sock false", j.get("sock") is False, j.get("sock"))

        async def with_socket():
            task = asyncio.create_task(tablet_socket(4.0))
            await asyncio.sleep(1.0)
            rr, jj = await asyncio.get_running_loop().run_in_executor(None, lambda: s.run(extra=lit))
            await task
            return jj
        jj = asyncio.run(with_socket())
        check("19c real /health with a tablet socket open: sock true, the row resets", jj.get("sock") is True and jj.get("nosock_run") == 0,
              jj.get("sock"))
    finally:
        p.stop()

    # never the real thing
    src = AUDIT.read_text()
    code = [ln for ln in src.splitlines() if not ln.lstrip().startswith("#")]
    literal = [ln.strip() for ln in code
               if re.search(r"(timeout\s+\d+\s+|^\s*|\$\(\s*|[|;&]\s*)adb\s+(-s|shell|connect|exec-out|devices|forward)\b", ln)]
    via_var = [ln.strip() for ln in code if '"$ADB_BIN"' in ln]
    check("20 every adb call in mic_audit.sh goes through $ADB_BIN (the tests' stub), none to a literal adb, no password",
          not literal and len(via_var) == 4 and "password" not in src.lower().replace("fully password", ""),
          {"literal": literal, "via_ADB_BIN": len(via_var)})
    (out / "mic_audit_results.json").write_text(json.dumps(RESULTS, indent=1))
    n_ok = sum(1 for x in RESULTS if x["ok"])
    print(f"TOTAL {n_ok}/{len(RESULTS)} mic audit checks passed")
    return 0 if n_ok == len(RESULTS) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=tempfile.mkdtemp(prefix="micaudit-out-"))
    sys.exit(main(Path(ap.parse_args().out)))
