#!/usr/bin/env python3
"""tests/test_server.py: offline integration tests for tablet-voice, test ports only.

Starts tests/fake_dash.py on TEST_HOST:18765 (synthetic data, records every write) and server.py on
TEST_HOST:18766 in several configurations (phases), each under timeout(1) and stopped by closing its stdin.
TEST_HOST is 127.0.0.2 unless TV_TEST_HOST says otherwise (see tests/harness.py for why).
Never touches ports 8765 or 8766, the tablet, Fully or any systemd unit; FULLY_PW is never passed through.

  timeout 3600 .venv/bin/python tests/test_server.py --out DIR [--phases A,B,C,D,E,G,H,F]

A skeleton: health, hello, access control (Origin, peer via 127.0.0.2, path, 426, max conns), bad hello
  (1003), hello timeout (1008), replaced socket (4000), not_ready, ledger from state messages, telemetry,
  tablet-peer bookkeeping through the tablet-ip file
B pipeline, dry, shadow (VOICE_OWW_REJECT=0): selftest 9/9, the lit rule, busy, TTS window, end rules,
  stall cap, pre-roll trim, reads (next, tomorrow), refusals (shopping, completion), /stats, memory, CPU
C pipeline, dry, VOICE_OWW_REJECT=0.10: selftest 9/9 (early rejects)
D pipeline, LIVE writes against the fake dashboard: dry from 127.0.0.1 only, POST bodies, undeliverable,
  refusals, REST speech fallback with a dummy password (redacted, never logged)
E pipeline, dry, VOICE_ALLOW_COMPLETE=1 and VOICE_READ_NEEDS_WAKE_TEXT=1: a completion pick, strict reads
  (the ambiguous pick is covered deterministically in tests/test_actions.py)
F failure modes: dashboard down, missing model (exit 1), bad env (exit), port in use (exit 1)
G pipeline, dry, continuous pink noise bed under the 9 selftest clips (extra evidence, not in the V4 table)
H the 15a Fix round (review findings): journal redaction and the transcript policy, the log line budget and the
  streaming replay, the write outcomes (unknown, http error), the read budget and the shared prefetch, the turn
  budget, the replaced socket, the lit rule mid-stream, pacing and the wake rate cap, strict JSON lines, the end
  line and action_ms
F also: a live write with the dashboard down (not sent)
"""
import argparse
import asyncio
import base64
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import numpy as np
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidStatus

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness as H  # noqa: E402
from wsprobe import load_wav, stream_session, first, speech_end_s  # noqa: E402

PAGE = "http://localhost:8765"
RESULTS = []
CLIPS = {}
OUT = None


def check(name, ok, detail=""):
    RESULTS.append({"name": name, "ok": bool(ok), "detail": detail})
    print(f"{'PASS' if ok else 'FAIL'} {name}{': ' + detail if detail else ''}", flush=True)


def ws(**kw):
    origin = kw.pop("origin", PAGE)
    source = kw.pop("source", None)
    args = {"open_timeout": 10, "close_timeout": 5}
    if origin:
        args["origin"] = origin
    if source:
        args["local_addr"] = (source, 0)
    return connect(H.VOICE_URL, **args)


def hello_msg(client="t", **kw):
    m = {"type": "hello", "v": 1, "client": client, "build": "test", "rate": 16000, "frame": 1280,
         "lit": True, "fully": True, "tts": "off", "dry": True, "wake": {"engine": "test"}}
    m.update(kw)
    return json.dumps(m)


async def recv_json(c, timeout=10):
    while True:
        raw = await asyncio.wait_for(c.recv(), timeout)
        if isinstance(raw, str):
            return json.loads(raw)


async def expect_nothing(c, seconds):
    try:
        raw = await asyncio.wait_for(c.recv(), seconds)
        return raw
    except asyncio.TimeoutError:
        return None


def silence(sec):
    return np.zeros(int(sec * 16000), np.int16)


def log_events(proc, ev=None):
    time.sleep(0.4)
    rows = H.read_log(proc.log_dir)
    return [r for r in rows if ev is None or r.get("ev") == ev]


async def http_status(path, source=None, origin=None):
    """GET path on the voice port; returns the HTTP status (bound to `source` when given)."""
    import http.client
    c = http.client.HTTPConnection(H.HOST, H.VOICE_PORT, timeout=5, source_address=(source, 0) if source else None)
    hdr = {"Origin": origin} if origin else {}
    c.request("GET", path, headers=hdr)
    r = c.getresponse()
    body = r.read()
    c.close()
    return r.status, body


# ------------------------------------------------------------------ phase A: skeleton and access

async def phase_a(out):
    p = H.start_voice(out, "A-skeleton", {"VOICE_STAGE": "skeleton",
                                         "VOICE_TABLET_IP_FILE": str(Path(out) / "tablet-ip-test")}, limit_s=300)
    (Path(out) / "tablet-ip-test").write_text("127.0.0.3\n")
    try:
        h = p.health0
        check("A1 /health skeleton", h.get("ok") is True and h.get("v") == 1 and h.get("stage") == "skeleton"
              and h.get("dry_run") is True and h.get("tablet_connected") is False and h.get("last_hello") is None
              and h.get("loaded") is False, json.dumps({k: h[k] for k in ("ok", "v", "stage", "dry_run", "tablet_connected", "last_hello", "loaded")}))
        r = subprocess.run([H.PY, "wsprobe.py", "hello", "--url", H.VOICE_URL], capture_output=True, text=True, timeout=30, cwd=H.ROOT)
        hj = json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 else {}
        check("A2 wsprobe hello", hj.get("type") == "hello" and hj.get("v") == 1 and hj.get("stage") == "skeleton", r.stdout.strip()[:160])
        r = subprocess.run([H.PY, "wsprobe.py", "hello", "--url", H.VOICE_URL, "--origin", "http://evil.example"],
                           capture_output=True, text=True, timeout=30, cwd=H.ROOT)
        check("A3 Origin refused (wsprobe --origin http://evil.example)", r.returncode == 2 and r.stdout.strip() == "HTTP 403", r.stdout.strip())
        r = subprocess.run([H.PY, "wsprobe.py", "hello", "--url", H.VOICE_URL, "--origin", "none"],
                           capture_output=True, text=True, timeout=30, cwd=H.ROOT)
        check("A4 no Origin accepted (box tools)", r.returncode == 0, r.stdout.strip()[:80])
        r = subprocess.run([H.PY, "wsprobe.py", "hello", "--url", H.VOICE_URL, "--source", "127.0.0.2"],
                           capture_output=True, text=True, timeout=30, cwd=H.ROOT)
        check("A5 peer refused (source 127.0.0.2, WebSocket)", r.returncode == 2 and r.stdout.strip() == "HTTP 403", r.stdout.strip())
        st, _ = await http_status("/health", source="127.0.0.2")
        check("A6 peer refused (source 127.0.0.2, /health)", st == 403, f"status {st}")
        st, _ = await http_status("/health", origin="null")
        check("A7 Origin 'null' refused on /health", st == 403, f"status {st}")
        st, _ = await http_status("/nope")
        check("A8 unknown path 404", st == 404, f"status {st}")
        st, _ = await http_status("/")
        check("A9 plain GET / without upgrade 426", st == 426, f"status {st}")
        st, body = await http_status("/stats")
        sj = json.loads(body)
        check("A10 /stats shape", st == 200 and {"day", "mic_open_s", "lit_periods", "wakes", "ptt_turns", "runs", "rejects", "stt_p50_ms"} <= set(sj), body.decode()[:200])
        # bad hellos
        for label, first_msg in (("v 2", hello_msg(v=2)), ("rate 48000", hello_msg(rate=48000)), ("not hello", json.dumps({"type": "state"})),
                                 ("binary", b"\x00\x01"), ("v true", hello_msg(v=True))):
            async with ws() as c:
                await c.send(first_msg)
                try:
                    await asyncio.wait_for(c.recv(), 5)
                except ConnectionClosed:
                    pass
                check(f"A11 bad hello ({label}) closed 1003", c.close_code == 1003, f"code {c.close_code} reason {c.close_reason!r}")
        # hello timeout
        t0 = time.time()
        async with ws() as c:
            try:
                await asyncio.wait_for(c.recv(), 15)
            except ConnectionClosed:
                pass
            check("A12 hello timeout closed 1008", c.close_code == 1008 and 9 <= time.time() - t0 <= 12, f"code {c.close_code} after {time.time() - t0:.1f} s")
        # replaced
        async with ws() as a:
            await a.send(hello_msg(client="dup"))
            await recv_json(a)
            async with ws() as b:
                await b.send(hello_msg(client="dup"))
                await recv_json(b)
                try:
                    await asyncio.wait_for(a.recv(), 5)
                except ConnectionClosed:
                    pass
                check("A13 newer hello, same peer and client: older closed 4000 replaced", a.close_code == 4000 and a.close_reason == "replaced",
                      f"code {a.close_code} reason {a.close_reason!r}; newer open {b.state.name}")
        await asyncio.sleep(0.3)
        # max connections
        async with ws() as c1, ws() as c2, ws() as c3:
            for i, c in enumerate((c1, c2, c3)):
                await c.send(hello_msg(client=f"m{i}"))
                await recv_json(c)
            try:
                async with ws() as c4:
                    await c4.send(hello_msg(client="m4"))
                    code = "opened"
            except InvalidStatus as e:
                code = e.response.status_code
            check("A14 fourth connection refused 503", code == 503, f"{code}")
        await asyncio.sleep(0.3)
        # not_ready, ledger (a tablet peer: 127.0.0.3 through the tablet-ip file), telemetry, unknown, dropped binary
        st, body = await http_status("/stats")
        lit0 = json.loads(body)["lit_periods"]
        async with ws(source="127.0.0.3") as c:
            await c.send(hello_msg(client="led", lit=False))
            await recv_json(c)
            await c.send(json.dumps({"type": "wake", "sid": "s-nr", "by": "ptt", "preroll_samples": 0}))
            m = await recv_json(c)
            check("A15 skeleton wake -> reject not_ready", m.get("type") == "reject" and m.get("why") == "not_ready", json.dumps(m))
            await c.send(json.dumps({"type": "state", "lit": True, "mic": True, "reason": "test"}))
            await asyncio.sleep(1.5)
            await c.send(json.dumps({"type": "state", "lit": True, "mic": False, "reason": "test"}))
            await c.send(json.dumps({"type": "stats", "samplesPerSec": 16001, "engineMsP50": 4.2, "dropped": 0, "evil": "<script>"}))
            await c.send(json.dumps({"type": "near", "score": 0.61, "at": 12345}))
            await c.send(json.dumps({"type": "bogus"}))
            for _ in range(3):
                await c.send(b"\x00\x00" * 1280)
            await asyncio.sleep(0.3)
        st, body = await http_status("/stats")
        sj = json.loads(body)
        check("A16 ledger (tablet peer): mic-open seconds and one lit period from state messages; box-local sockets not counted",
              1.3 <= sj["mic_open_s"] <= 2.5 and sj["lit_periods"] == lit0 + 1 and lit0 == 0,
              f"mic_open_s {sj['mic_open_s']} lit_periods {lit0} -> {sj['lit_periods']}")
        rows = log_events(p)
        stats_rows = [r for r in rows if r.get("ev") == "stats"]
        check("A17 stats telemetry logged with type stats, unknown fields dropped",
              stats_rows and stats_rows[-1]["page"].get("type") == "stats" and "evil" not in json.dumps(stats_rows[-1]),
              json.dumps(stats_rows[-1]) if stats_rows else "none")
        check("A18 near telemetry logged", any(r.get("ev") == "near" and r["page"].get("score") == 0.61 for r in rows))
        closes = [r for r in rows if r.get("ev") == "close" and r.get("client") == "led"]
        local = [r for r in rows if r.get("ev") == "state" and r.get("peer") == "127.0.0.1"]
        check("A19 binary without a session dropped and counted", closes and closes[-1].get("dropped_msgs") == 3, json.dumps(closes[-1]) if closes else "none")
        rej = [r for r in rows if r.get("ev") == "rejected"]
        whys = sorted({r["why"] for r in rej})
        check("A20 every refusal logged once with peer, origin and path", {"origin", "peer", "path", "not_upgrade", "max_conns"} <= set(whys)
              and all("peer" in r and "origin" in r and "path" in r for r in rej), f"{len(rej)} lines, whys {whys}")
        # a tablet peer (127.0.0.3 through the tablet-ip file override)
        async with ws(source="127.0.0.3") as c:
            await c.send(hello_msg(client="dash", dry=True))
            hm = await recv_json(c)
            st, body = await http_status("/health")
            hj = json.loads(body)
            check("A21 tablet-ip file peer allowed; /health tablet_connected and last_hello",
                  hj["tablet_connected"] is True and (hj["last_hello"] or {}).get("peer") == "127.0.0.3",
                  json.dumps({"tablet_connected": hj["tablet_connected"], "last_hello": hj["last_hello"]}))
            check("A22 skeleton dry stays dry for a tablet peer", hm.get("dry") is True, json.dumps({"dry": hm.get("dry")}))
        await asyncio.sleep(0.5)
        st, body = await http_status("/health")
        check("A23 tablet_connected false after the tablet socket closes", json.loads(body)["tablet_connected"] is False)
        pid = p.child_pid()
        maps = Path(f"/proc/{pid}/maps").read_text() if pid else ""
        check("A24 skeleton loads no audio stack (no numpy, onnxruntime or ctranslate2 in the process maps)",
              pid and "onnxruntime" not in maps and "ctranslate2" not in maps and "numpy" not in maps, f"pid {pid}")
        mem = H.proc_mem(pid) if pid else {}
        RESULTS.append({"name": "A-mem", "ok": True, "detail": json.dumps(mem)})
        print(f"INFO skeleton memory {mem}")
    finally:
        rc = p.stop()
        check("A25 skeleton stops cleanly on stdin EOF", rc == 0, f"rc {rc}")


# ------------------------------------------------------------------ phase B: pipeline, dry, shadow

async def ptt(text_key, **kw):
    return await stream_session(H.VOICE_URL, CLIPS[text_key], by="ptt", client=kw.pop("client", "b"), **kw)


async def phase_b(out):
    (Path(out) / "tablet-ip-test").write_text("127.0.0.3\n")
    p = H.start_voice(out, "B-pipeline-dry", {"VOICE_TABLET_IP_FILE": str(Path(out) / "tablet-ip-test")}, limit_s=1200)
    pid = p.child_pid()
    try:
        h = p.health0
        check("B1 /health pipeline", h.get("stage") == "pipeline" and h.get("stt") == "faster-whisper base.en int8" and h.get("loaded") is True,
              json.dumps({k: h[k] for k in ("stage", "stt", "loaded", "dry_run")}))
        mem_ready = H.proc_mem(pid)
        cpu0 = H.proc_cpu_s(pid)
        ready = [r for r in log_events(p, "ready")]
        print(f"INFO ready {json.dumps(ready[-1]) if ready else None} mem {mem_ready}")
        # V4 selftest
        r = subprocess.run([H.PY, "selftest.py", "--url", H.VOICE_URL, "--json", str(Path(out) / "selftest-B.json")],
                           capture_output=True, text=True, timeout=400, cwd=H.ROOT)
        (Path(out) / "selftest-B.txt").write_text(r.stdout + r.stderr)
        print(r.stdout)
        check("B2 selftest PASS 9/9 (shadow mode)", r.returncode == 0 and "PASS 9/9" in r.stdout, r.stdout.strip().splitlines()[-1] if r.stdout else r.stderr[-200:])
        cpu1 = H.proc_cpu_s(pid)
        mem_after = H.proc_mem(pid)
        RESULTS.append({"name": "B-cpu-mem", "ok": True, "detail": json.dumps({"cpu_s_selftest": round(cpu1 - cpu0, 2), "mem_ready": mem_ready, "mem_after_selftest": mem_after})})
        print(f"INFO cpu over the 9 selftest sessions {cpu1 - cpu0:.2f} s; mem after {mem_after}")
        rows = log_events(p, "session")
        check("B3 every session line carries \"dry_run\": true", rows and all(x.get("dry_run") is True for x in rows), f"{len(rows)} session lines")
        raw = "\n".join(Path(f).read_text() for f in Path(p.log_dir).glob("*.jsonl"))
        check("B4 log: refused wake_text present, no POST, no PCM", '"refused": "wake_text"' in raw and '"post"' not in raw and "/api/task" not in raw,
              f"dry_run lines {raw.count(chr(34) + 'dry_run' + chr(34) + ': true')}")
        # reads and refusals by push-to-talk
        r1 = await ptt("next")
        _, res = first(r1["msgs"], "result")
        check("B5 PTT 'what is next' -> next.event from /api/data", res and res["intent"]["name"] == "next.event" and res["ok"]
              and (res["say"].startswith("Next at") or res["say"].startswith("Nothing else today")), json.dumps(res and {"heard": res["heard"], "say": res["say"]}))
        r2 = await ptt("tomorrow")
        _, res = first(r2["msgs"], "result")
        check("B6 PTT 'what is on my schedule tomorrow' -> schedule.tomorrow", res and res["intent"]["name"] == "schedule.tomorrow"
              and res["say"].startswith("Tomorrow: all day, Mum's birthday. 09:00, Standup. 14:30, Dentist.") and "Two tasks due." in res["say"],
              json.dumps(res and {"heard": res["heard"], "say": res["say"]}))
        r3 = await ptt("shopping")
        _, res = first(r3["msgs"], "result")
        check("B7 PTT shopping add refused, nothing written", res and res["intent"]["name"] == "task.add" and res["intent"]["list"] == "shopping"
              and res["say"] == "I can only add to personal or work for now." and res["ok"] is False, json.dumps(res and {"heard": res["heard"], "say": res["say"]}))
        r4 = await ptt("done")
        _, res = first(r4["msgs"], "result")
        check("B8 PTT completion refused complete_off (D6)", res and res["intent"]["name"] == "task.complete" and res.get("refused") == "complete_off"
              and res["say"] == "I can't complete tasks by voice yet.", json.dumps(res and {"heard": res["heard"], "say": res["say"], "refused": res.get("refused")}))
        r5 = await ptt("light")
        _, res = first(r5["msgs"], "result")
        check("B9 PTT 'switch to light mode' -> do theme light", res and {"what": "theme", "value": "light"} in res["do"] and res["say"] == "Light mode on.",
              json.dumps(res and {"heard": res["heard"], "do": res["do"]}))
        r6 = await ptt("cancel")
        _, res = first(r6["msgs"], "result")
        check("B10 PTT 'never mind' -> cancel, nothing spoken", res and res["intent"]["name"] == "cancel" and res["say"] is None,
              json.dumps(res and {"heard": res["heard"], "say": res["say"]}))
        calls = H.get_json(H.DASH + "/calls")
        check("B11 dry run called nothing but GET /api/data", calls and all(c["method"] == "GET" and c["path"] == "/api/data" for c in calls), f"{len(calls)} calls")
        # lit rule
        async with ws() as c:
            await c.send(hello_msg(client="nofully", fully=False))
            await recv_json(c)
            await c.send(json.dumps({"type": "wake", "sid": "nf1", "by": "wake", "score": 0.99, "preroll_samples": 0}))
            m = await recv_json(c)
            check("B12 wake from a page without fully -> reject no_lit_signal", m.get("why") == "no_lit_signal", json.dumps(m))
            await c.send(json.dumps({"type": "wake", "sid": "nf2", "by": "ptt", "preroll_samples": 0}))
            m = await expect_nothing(c, 1.0)
            check("B13 push-to-talk from that page is accepted", m is None, f"{m}")
            await c.send(json.dumps({"type": "end", "sid": "nf2", "why": "cancel"}))
            await c.send(json.dumps({"type": "state", "lit": False, "mic": False, "reason": "screensaver"}))
            await c.send(json.dumps({"type": "wake", "sid": "nl1", "by": "ptt", "preroll_samples": 0}))
            m = await recv_json(c)
            check("B14 wake after state lit false -> reject not_lit", m.get("why") == "not_lit", json.dumps(m))
            await c.send(json.dumps({"type": "state", "lit": True, "mic": False, "reason": "armed-no-mic"}))
            await c.send(json.dumps({"type": "wake", "sid": "nl2", "by": "ptt", "preroll_samples": 0}))
            m = await recv_json(c)
            check("B15 wake after state mic false -> reject not_lit", m.get("why") == "not_lit", json.dumps(m))
        # busy and the stall cap
        async with ws() as a, ws() as b:
            await a.send(hello_msg(client="busyA"))
            await recv_json(a)
            await b.send(hello_msg(client="busyB"))
            await recv_json(b)
            await a.send(json.dumps({"type": "wake", "sid": "busy1", "by": "wake", "score": 0.99, "preroll_samples": 44800}))
            await a.send(silence(2.8).tobytes())
            await b.send(json.dumps({"type": "wake", "sid": "busy2", "by": "wake", "score": 0.99, "preroll_samples": 0}))
            m = await recv_json(b)
            check("B16 second wake while a session is open -> reject busy", m.get("why") == "busy", json.dumps(m))
            t0 = time.time()
            m = await recv_json(a, timeout=25)          # no frames after the pre-roll: the stall cap ends it
            check("B17 stalled stream dropped at the cap (reject too_long, about 18 s)", m.get("why") == "too_long" and 16 <= time.time() - t0 <= 21,
                  f"{json.dumps(m)} after {time.time() - t0:.1f} s")
        # TTS window
        async with ws() as c:
            await c.send(hello_msg(client="tts", tts="page"))
            await recv_json(c)
            await c.send(json.dumps({"type": "state", "lit": True, "mic": True, "reason": "armed"}))
        r7 = await stream_session(H.VOICE_URL, CLIPS["dark"], by="ptt", client="tts2", tts="page")
        ts = [m for _, m in r7["msgs"] if m.get("type") == "tts_start"]
        _, res = first(r7["msgs"], "result")
        check("B18 hello tts page: result then tts_start via page with est_ms and say",
              res and ts and ts[0]["via"] == "page" and ts[0]["est_ms"] == 900 + 70 * len(res["say"]) and ts[0]["say"] == res["say"],
              json.dumps(ts[0]) if ts else "no tts_start")
        async with ws() as c:
            await c.send(hello_msg(client="tts3", tts="page"))
            await recv_json(c)
            await c.send(json.dumps({"type": "wake", "sid": "w-in-window", "by": "wake", "score": 0.99, "preroll_samples": 0}))
            m = await recv_json(c)
            check("B19 wake inside the TTS window -> reject tts", m.get("why") == "tts", json.dumps(m))
            await c.send(json.dumps({"type": "wake", "sid": "p-in-window", "by": "ptt", "preroll_samples": 0}))
            m = await expect_nothing(c, 0.8)
            check("B20 push-to-talk inside the TTS window is accepted (barge-in)", m is None, f"{m}")
            await c.send(json.dumps({"type": "end", "sid": "p-in-window", "why": "cancel"}))
            await c.send(json.dumps({"type": "tts_done", "sid": ts[0]["sid"] if ts else None, "id": ts[0]["id"] if ts else None,
                                     "how": "event", "onset_ms": 420, "dur_ms": 1300}))
            await asyncio.sleep(0.2)
            await c.send(json.dumps({"type": "wake", "sid": "w-after", "by": "wake", "score": 0.99, "preroll_samples": 0}))
            m = await expect_nothing(c, 0.8)
            check("B21 after tts_done the wake is accepted again", m is None, f"{m}")
            await c.send(json.dumps({"type": "end", "sid": "w-after", "why": "cancel"}))
        rows = log_events(p, "tts_done")
        check("B22 tts_done logged with how, onset and duration; window closed", rows and rows[-1].get("window_closed") is True and rows[-1].get("onset_ms") == 420,
              json.dumps(rows[-1]) if rows else "none")
        # end rules
        r8 = await ptt("add_rms", end_at=1.0, end_why="dark")
        check("B23 end{dark} before the endpoint: dropped, nothing answered", not any(m.get("type") in ("result", "reject", "endpoint") for _, m in r8["msgs"]),
              json.dumps([m.get("type") for _, m in r8["msgs"]]))
        se = speech_end_s(CLIPS["next"])
        r9 = await ptt("next", end_at=se + 0.25, end_why="user")
        t_ep, ep = first(r9["msgs"], "endpoint")
        _, res = first(r9["msgs"], "result")
        check("B24 end{user} after speech: endpoint user, then the result", ep and ep.get("why") == "user" and res and res["intent"]["name"] == "next.event",
              json.dumps({"endpoint": ep, "heard": res and res["heard"]}))
        r10 = await stream_session(H.VOICE_URL, silence(0.5), by="ptt", client="b", end_at=1.0, end_why="user")
        _, rej = first(r10["msgs"], "reject")
        check("B25 end{user} with no speech -> reject no_command", rej and rej.get("why") == "no_command" and rej.get("stage") == "end", json.dumps(rej))
        r11 = await stream_session(H.VOICE_URL, silence(0.5), by="ptt", client="b")
        t_rej, rej = first(r11["msgs"], "reject")
        check("B26 push-to-talk and silence -> reject no_command after 5 s", rej and rej.get("why") == "no_command" and 4.9 <= t_rej <= 5.6,
              f"{json.dumps(rej)} at {t_rej}")
        # declared pre-roll longer than 3.2 s keeps its newest 3.2 s
        async with ws() as c:
            await c.send(hello_msg(client="pre"))
            await recv_json(c)
            await c.send(json.dumps({"type": "wake", "sid": "pre4", "by": "ptt", "preroll_samples": 64000}))
            await c.send(silence(4.0).tobytes())
            await c.send(json.dumps({"type": "end", "sid": "pre4", "why": "cancel"}))
            await asyncio.sleep(0.3)
        rows = [r for r in log_events(p, "session") if r.get("sid") == "pre4"]
        check("B27 pre-roll over 3.2 s trimmed to 3.2 s", rows and rows[-1].get("preroll_s") == 3.2 and rows[-1].get("audio_s") == 3.2, json.dumps(rows[-1]) if rows else "none")
        # socket closed mid-stream
        async with ws() as c:
            await c.send(hello_msg(client="gone"))
            await recv_json(c)
            await c.send(json.dumps({"type": "wake", "sid": "gone1", "by": "ptt", "preroll_samples": 0}))
            await c.send(CLIPS["add_rms"][:16000].tobytes())
        await asyncio.sleep(0.5)
        rows = [r for r in log_events(p, "session") if r.get("sid") == "gone1"]
        check("B28 socket closed mid-stream: session dropped socket_closed", rows and rows[-1].get("outcome") == "dropped" and rows[-1].get("why") == "socket_closed",
              json.dumps(rows[-1]) if rows else "none")
        st, body = await http_status("/stats")
        s0 = json.loads(body)
        rt = await stream_session(H.VOICE_URL, CLIPS["next"], by="ptt", client="dash", source="127.0.0.3")
        async with ws(source="127.0.0.3") as c:          # a tablet wake refused while TTS is off: none; use busy-free not_lit
            await c.send(hello_msg(client="dash2"))
            await recv_json(c)
            await c.send(json.dumps({"type": "state", "lit": False, "mic": False, "reason": "screensaver"}))
            await c.send(json.dumps({"type": "wake", "sid": "tab-nl", "by": "wake", "score": 0.99, "preroll_samples": 0}))
            await recv_json(c)
        st, body = await http_status("/stats")
        sj = json.loads(body)
        check("B29 /stats: box-local sessions apart; a tablet session and a tablet reject counted by reason; STT p50",
              s0["sessions"] == 0 and s0["local_sessions"] >= 20 and sj["sessions"] == 2 and sj["ptt_turns"] == 1 and sj["runs"] == 1
              and sj["rejects"] == {"not_lit": 1} and sj["stt_p50_ms"],
              json.dumps({k: sj[k] for k in ("sessions", "wakes", "ptt_turns", "runs", "rejects", "refused", "stt_p50_ms", "stt_n", "local_sessions")}))
        RESULTS.append({"name": "B-stats", "ok": True, "detail": json.dumps(sj)})
        mem_end = H.proc_mem(pid)
        RESULTS.append({"name": "B-mem-end", "ok": True, "detail": json.dumps(mem_end)})
        print(f"INFO mem at end of B {mem_end}")
    finally:
        rc = p.stop()
        stop = [r for r in H.read_log(p.log_dir) if r.get("ev") == "stop"]
        check("B30 pipeline stops cleanly on stdin EOF", rc == 0 and stop, f"rc {rc} stop {json.dumps(stop[-1]) if stop else None}")


async def phase_c(out):
    p = H.start_voice(out, "C-oww-reject", {"VOICE_OWW_REJECT": "0.10"}, limit_s=600)
    try:
        r = subprocess.run([H.PY, "selftest.py", "--url", H.VOICE_URL, "--json", str(Path(out) / "selftest-C.json")],
                           capture_output=True, text=True, timeout=400, cwd=H.ROOT)
        (Path(out) / "selftest-C.txt").write_text(r.stdout + r.stderr)
        print(r.stdout)
        check("C1 selftest PASS 9/9 with VOICE_OWW_REJECT=0.10", r.returncode == 0 and "PASS 9/9" in r.stdout, r.stdout.strip().splitlines()[-1] if r.stdout else "")
    finally:
        p.stop()


async def phase_d(out):
    (Path(out) / "tablet-ip-test").write_text("127.0.0.3\n")
    p = H.start_voice(out, "D-live", {"VOICE_DRY_RUN": "0", "VOICE_TABLET_IP_FILE": str(Path(out) / "tablet-ip-test"),
                                      "FULLY_PW": "dummy-test-value-not-a-password", "VOICE_FULLY_URL": H.DASH}, limit_s=600)
    try:
        n0 = len(H.get_json(H.DASH + "/calls"))
        r = await stream_session(H.VOICE_URL, CLIPS["add_rms"], by="ptt", client="dry127", dry=True)
        _, res = first(r["msgs"], "result")
        posts = [c for c in H.get_json(H.DASH + "/calls")[n0:] if c["method"] == "POST"]
        check("D1 live box, hello dry from 127.0.0.1 honoured: 'Would add', no POST", res and res["dry"] is True and res["say"].startswith("Would add") and not posts,
              json.dumps(res and {"say": res["say"], "dry": res["dry"]}))
        n0 = len(H.get_json(H.DASH + "/calls"))
        r = await stream_session(H.VOICE_URL, CLIPS["add_rms"], by="ptt", client="live127", dry=False)
        _, res = first(r["msgs"], "result")
        posts = [c for c in H.get_json(H.DASH + "/calls")[n0:] if c["method"] == "POST"]
        check("D2 live write: POST /api/task/add with title, due, list; reply 'Added ...'; do refresh",
              res and res["ok"] and res["say"].startswith("Added") and {"what": "refresh"} in res["do"] and len(posts) == 1
              and posts[0]["path"] == "/api/task/add" and posts[0]["body"]["list"] == "personal" and posts[0]["body"]["due"] is None,
              json.dumps({"say": res and res["say"], "posts": posts}))
        n0 = len(H.get_json(H.DASH + "/calls"))
        r = await stream_session(H.VOICE_URL, CLIPS["add_rms"], by="ptt", client="gone", dry=False, close_on_endpoint=True)
        await asyncio.sleep(2.5)
        posts = [c for c in H.get_json(H.DASH + "/calls")[n0:] if c["method"] == "POST"]
        rows = [x for x in log_events(p, "session") if x.get("sid") == r["sid"]]
        check("D3 socket gone after the endpoint: nothing written, refused undeliverable", not posts and rows and rows[-1].get("refused") == "undeliverable",
              json.dumps(rows[-1] if rows else None))
        n0 = len(H.get_json(H.DASH + "/calls"))
        for key in ("shopping", "done"):
            await stream_session(H.VOICE_URL, CLIPS[key], by="ptt", client="live127", dry=False)
        posts = [c for c in H.get_json(H.DASH + "/calls")[n0:] if c["method"] == "POST"]
        check("D4 live: shopping and completion refused, no POST", not posts, json.dumps(posts))
        n0 = len(H.get_json(H.DASH + "/calls"))
        r = await stream_session(H.VOICE_URL, CLIPS["add_rms"], by="ptt", client="dash", dry=True, source="127.0.0.3")
        _, res = first(r["msgs"], "result")
        posts = [c for c in H.get_json(H.DASH + "/calls")[n0:] if c["method"] == "POST"]
        check("D5 hello dry from a non-loopback peer is ignored on a live box (writes)", res and res["dry"] is False and len(posts) == 1,
              json.dumps({"dry": res and res["dry"], "posts": len(posts)}))
        # REST speech fallback: page asks for speech but has no fully object -> REST (fake), password redacted
        n0 = len(H.get_json(H.DASH + "/calls"))
        r = await stream_session(H.VOICE_URL, CLIPS["dark"], by="ptt", client="restpage", dry=False, tts="page", fully=False)
        ts = [m for _, m in r["msgs"] if m.get("type") == "tts_start"]
        rest = [c for c in H.get_json(H.DASH + "/calls")[n0:] if c["path"] == "/?cmd"]
        check("D6 REST fallback: tts_start via rest, Fully cmd textToSpeech en_US queue 1, no engine",
              ts and ts[0]["via"] == "rest" and rest and rest[0]["body"]["cmd"] == "textToSpeech" and rest[0]["body"]["locale"] == "en_US"
              and rest[0]["body"]["queue"] == "1" and "engine" not in rest[0]["body"], json.dumps({"tts_start": ts[:1], "rest": rest[:1]}))
        await asyncio.sleep(0.3)
        raw = "\n".join(Path(f).read_text() for f in Path(p.log_dir).glob("*.jsonl")) + (Path(out) / "server-D-live.out").read_text()
        check("D7 the dummy password never appears in the log or stdout", "dummy-test-value" not in raw, f"{len(raw)} bytes scanned")
        h = H.get_json(H.HTTP + "/health")
        check("D8 /health reports dry_run false and fully_rest true (a boolean, no secret)", h["dry_run"] is False and h["cfg"]["fully_rest"] is True)
    finally:
        p.stop()


async def phase_e(out):
    p = H.start_voice(out, "E-complete-strict", {"VOICE_ALLOW_COMPLETE": "1", "VOICE_READ_NEEDS_WAKE_TEXT": "1"}, limit_s=600)
    try:
        r = await stream_session(H.VOICE_URL, CLIPS["done"], by="ptt", client="e")
        _, res = first(r["msgs"], "result")
        check("E1 VOICE_ALLOW_COMPLETE=1, dry: 'Would complete Buy milk.'", res and res["say"] == "Would complete Buy milk.", json.dumps(res and {"heard": res["heard"], "say": res["say"]}))
        out_t = subprocess.run([H.PY, "selftest.py", "--url", H.VOICE_URL], capture_output=True, text=True, timeout=400, cwd=H.ROOT)
        (Path(out) / "selftest-E.txt").write_text(out_t.stdout + out_t.stderr)
        print(out_t.stdout)
        check("E3 selftest PASS 9/9 with completion on and strict reads", out_t.returncode == 0 and "PASS 9/9" in out_t.stdout, out_t.stdout.strip().splitlines()[-1] if out_t.stdout else "")
    finally:
        p.stop()


async def phase_f(out, dash_proc):
    # dashboard down: stop the fake dash first
    rc_dash = dash_proc.stop()
    p = H.start_voice(out, "F-dash-down", {}, limit_s=300)
    try:
        r = await stream_session(H.VOICE_URL, CLIPS["next"], by="ptt", client="f")
        _, res = first(r["msgs"], "result")
        check("F1 dashboard down -> \"The dashboard isn't answering.\"", res and res["say"] == "The dashboard isn't answering." and res["ok"] is False,
              json.dumps(res and {"say": res["say"], "timing": res["timing_ms"]}))
        # a live write with the dashboard down: never sent, so "couldn't" is the truth
        p_live = None
        p.stop()
        p_live = H.start_voice(out, "F-dash-down-live", {"VOICE_DRY_RUN": "0"}, limit_s=300)
        r = await stream_session(H.VOICE_URL, CLIPS["add_rms"], by="ptt", client="flive", dry=False)
        _, res = first(r["msgs"], "result")
        rows = [x for x in log_events(p_live, "session") if x.get("sid") == r["sid"]]
        check("F1b live write, dashboard down: \"I couldn't add that. The dashboard isn't answering.\", logged post not_sent",
              res and res["say"] == "I couldn't add that. The dashboard isn't answering." and rows
              and (rows[-1].get("action") or {}).get("post") == "not_sent", json.dumps(res and {"say": res["say"]}))
        p_live.stop()
        p = H.start_voice(out, "F-dash-down-2", {}, limit_s=300)
        # port in use: a second server on the same port exits 1
        d2 = Path(out) / "logs-F-second"
        env = {k: v for k, v in os.environ.items() if k != "FULLY_PW"}
        env.update({"VOICE_HOST": H.HOST, "VOICE_PORT": str(H.VOICE_PORT), "VOICE_STAGE": "skeleton", "VOICE_LOG_DIR": str(d2)})
        r2 = subprocess.run(["timeout", "60", H.PY, "server.py"], capture_output=True, text=True, env=env, cwd=H.ROOT, timeout=90, stdin=subprocess.DEVNULL)
        check("F2 port in use -> fatal bind, exit 1", r2.returncode == 1 and '"where": "bind"' in r2.stdout, r2.stdout.strip().splitlines()[-1][:200] if r2.stdout else "")
    finally:
        p.stop()
    empty = Path(out) / "empty-models"
    empty.mkdir(exist_ok=True)
    env = {k: v for k, v in os.environ.items() if k != "FULLY_PW"}
    env.update({"VOICE_HOST": H.HOST, "VOICE_PORT": str(H.VOICE_PORT), "VOICE_STAGE": "pipeline", "VOICE_MODELS": str(empty),
                "VOICE_LOG_DIR": str(Path(out) / "logs-F-nomodel"), "HF_HUB_OFFLINE": "1"})
    r3 = subprocess.run(["timeout", "60", H.PY, "server.py"], capture_output=True, text=True, env=env, cwd=H.ROOT, timeout=90, stdin=subprocess.DEVNULL)
    check("F3 missing openWakeWord model -> fatal load, exit 1 (unit fails loudly)", r3.returncode == 1 and "missing model file" in r3.stdout,
          r3.stdout.strip().splitlines()[-1][:220] if r3.stdout else "")
    env.update({"VOICE_MODELS": str(H.ROOT / "models"), "VOICE_STAGE": "bogus"})
    r4 = subprocess.run(["timeout", "60", H.PY, "server.py"], capture_output=True, text=True, env=env, cwd=H.ROOT, timeout=90, stdin=subprocess.DEVNULL)
    check("F4 bad VOICE_STAGE -> exit with a message", r4.returncode != 0 and "VOICE_STAGE" in (r4.stdout + r4.stderr), (r4.stdout + r4.stderr).strip()[:160])
    return rc_dash


async def phase_g(out):
    p = H.start_voice(out, "G-noise-bed", {}, limit_s=600)
    try:
        r = subprocess.run([H.PY, "selftest.py", "--url", H.VOICE_URL, "--noise-bed", "0.006", "--json", str(Path(out) / "selftest-G.json")],
                           capture_output=True, text=True, timeout=400, cwd=H.ROOT)
        (Path(out) / "selftest-G.txt").write_text(r.stdout + r.stderr)
        print(r.stdout)
        check("G1 selftest with a continuous pink bed (amplitude 0.006): informational", True, r.stdout.strip().splitlines()[-1] if r.stdout else "")
    finally:
        p.stop()


# ------------------------------------------------------------------ phase H: 15a Fix round (review findings)

def dash_control(**kw):
    req = urllib.request.Request(H.DASH + "/control", data=json.dumps(kw).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())


def raw_http(lines, src=None, timeout=5):
    s = socket.socket()
    s.settimeout(timeout)
    if src:
        s.bind((src, 0))
    s.connect((H.HOST, H.VOICE_PORT))
    s.sendall(("\r\n".join(lines) + "\r\n\r\n").encode("latin-1"))
    data = b""
    try:
        while b"\r\n" not in data:
            c = s.recv(4096)
            if not c:
                break
            data += c
    except socket.timeout:
        pass
    s.close()
    return data.split(b"\r\n", 1)[0].decode("latin-1", "replace")


def upgrade_lines(extra):
    return ["GET / HTTP/1.1", f"Host: {H.HOST}:{H.VOICE_PORT}", "Upgrade: websocket", "Connection: Upgrade",
            "Sec-WebSocket-Key: " + base64.b64encode(os.urandom(16)).decode(), "Sec-WebSocket-Version: 13", *extra]


def ws_frame(payload: bytes, opcode=1):
    mask, n = os.urandom(4), len(payload)
    hdr = bytes([0x80 | opcode])
    if n < 126:
        hdr += bytes([0x80 | n])
    elif n < 65536:
        hdr += bytes([0x80 | 126]) + n.to_bytes(2, "big")
    else:
        hdr += bytes([0x80 | 127]) + n.to_bytes(8, "big")
    m = (mask * (n // 4 + 1))[:n]
    return hdr + mask + bytes(a ^ b for a, b in zip(payload, m))


def raw_ws(src):
    s = socket.socket()
    s.bind((src, 0))
    s.settimeout(5)
    s.connect((H.HOST, H.VOICE_PORT))
    s.sendall(("\r\n".join(upgrade_lines([f"Origin: {PAGE}"])) + "\r\n\r\n").encode())
    data = b""
    while b"\r\n\r\n" not in data:
        data += s.recv(4096)
    assert b" 101 " in data.split(b"\r\n", 1)[0], data[:80]
    return s


def strict_ok(line):
    try:
        json.loads(line, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
        return True
    except ValueError:
        return False


def file_lines(proc):
    out = []
    for f in sorted(Path(proc.log_dir).glob("sessions-*.jsonl")):
        out += [ln for ln in f.read_text(encoding="utf-8").split("\n") if ln.strip()]
    return out


def stdout_lines(proc):
    return [ln for ln in proc.log_path.read_text(encoding="utf-8", errors="replace").split("\n") if ln.startswith("{")]


def rows_for(lines, **match):
    out = []
    for ln in lines:
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        if all(r.get(k) == v for k, v in match.items()):
            out.append(r)
    return out


async def paced(c, sid, clip, by="ptt", pre=None, state_at=None, state_msg=None, tail_s=1.5, end_at=None, end_msg=None):
    """Stream like the page: an optional pre-roll at once, then 80 ms frames in real time; optional mid-stream
    messages. Returns the box messages collected until a result or reject (or 8 s after the stream)."""
    await c.send(json.dumps({"type": "wake", "sid": sid, "by": by, "score": 0.99 if by == "wake" else None,
                             "preroll_samples": 0 if pre is None else len(pre)}))
    if pre is not None and len(pre):
        await c.send(pre.tobytes())
    x = np.concatenate([clip.astype(np.int16), np.zeros(int(tail_s * 16000), np.int16)])
    got, t0, k = [], time.perf_counter(), 0

    async def reader():
        while True:
            raw = await c.recv()
            if isinstance(raw, str):
                m = json.loads(raw)
                got.append((round(time.perf_counter() - t0, 3), m))
                if m.get("type") in ("result", "reject"):
                    return
    rd = asyncio.create_task(reader())
    for i in range(0, len(x), 1280):
        k += 1
        d = k * 0.08 - (time.perf_counter() - t0)
        if d > 0:
            await asyncio.sleep(d)
        if rd.done():
            break
        if state_msg is not None and state_at is not None and i >= state_at * 16000:
            await c.send(json.dumps(state_msg))
            state_msg = None
        if end_msg is not None and end_at is not None and i >= end_at * 16000:
            await c.send(json.dumps(end_msg))
            end_msg = None
        if any(m.get("type") == "endpoint" for _, m in got):
            break
        await c.send(x[i:i + 1280].tobytes())
    try:
        await asyncio.wait_for(rd, 8)
    except (asyncio.TimeoutError, ConnectionClosed):
        pass
    return got


async def tablet(client="dash", **kw):
    c = await connect(H.VOICE_URL, origin=PAGE, local_addr=("127.0.0.3", 0), open_timeout=10, close_timeout=5)
    await c.send(hello_msg(client=client, **kw))
    await recv_json(c)
    await c.send(json.dumps({"type": "state", "lit": True, "mic": True, "reason": "test"}))
    return c


def wake_at(phrase_key):
    return round(speech_end_s(CLIPS[phrase_key]) + 0.12, 3)


async def phase_h(out):
    ipf = Path(out) / "tablet-ip-test"
    ipf.write_text("127.0.0.3\n")
    p = H.start_voice(out, "H-fixround", {"VOICE_TABLET_IP_FILE": str(ipf)}, limit_s=1500)
    t_flood = None
    try:
        # ---- finding 4: refusals and websockets' own errors within a line budget
        n0 = len(file_lines(p))
        t_flood = time.time()
        t0 = time.perf_counter()
        codes = [raw_http(["GET /health HTTP/1.1", f"Host: {H.HOST}"], src="127.0.0.2") for _ in range(300)]
        flood_s = time.perf_counter() - t0
        for _ in range(30):
            s = socket.socket()
            s.settimeout(3)
            s.bind(("127.0.0.2", 0))
            s.connect((H.HOST, H.VOICE_PORT))
            s.sendall(b"\x16\x03\x01\x02\x00\x01\x00\x01\xfc\x03\x03" + os.urandom(64) + b"\r\n\r\n")
            try:
                s.recv(200)
            except OSError:
                pass
            s.close()
        dup = raw_http(upgrade_lines([f"Origin: {PAGE}", "Origin: http://evil.example"]))
        await asyncio.sleep(0.5)
        new = [json.loads(x) for x in file_lines(p)[n0:]]
        rej2 = [r for r in new if r.get("ev") == "rejected" and r.get("peer") == "127.0.0.2"]
        wsl2 = [r for r in new if r.get("ev") == "ws_log" and r.get("peer") == "127.0.0.2"]
        check("H1 300 refused requests from one non-allowed peer: all 403, at most 5 rejected lines a minute",
              all(c.startswith("HTTP/1.1 403") for c in codes) and len(rej2) == 5,
              f"{len(rej2)} lines for 300 requests in {flood_s:.2f} s (15a: 300 lines)")
        check("H2 30 garbage connections: websockets' handshake errors logged at most 5 a minute for that peer, with the peer",
              len(wsl2) <= 5 and all(r.get("peer") == "127.0.0.2" for r in wsl2), f"{len(wsl2)} ws_log lines")
        dupl = [r for r in new if r.get("ev") == "rejected" and r.get("why") == "origin" and r.get("peer") == "127.0.0.1"]
        check("H3 two Origin headers: 403 and a rejected line (was a 500 from the library)", dup.startswith("HTTP/1.1 403") and dupl, dup)

        # ---- findings 1 and 10: the journal never carries transcripts, task titles or replies
        r_add = await stream_session(H.VOICE_URL, CLIPS["add_rms"], by="ptt", client="hj")
        _, res_add = first(r_add["msgs"], "result")
        await asyncio.sleep(0.5)
        f_add = rows_for(file_lines(p), ev="session", sid=r_add["sid"])
        o_add = rows_for(stdout_lines(p), ev="session", sid=r_add["sid"])
        check("H4 session line in the file: transcript, text, intent slots, reply and action_ms",
              f_add and f_add[-1].get("heard") and f_add[-1].get("text") and isinstance(f_add[-1].get("intent"), dict)
              and f_add[-1]["intent"].get("title") and f_add[-1].get("say", "").startswith("Would add")
              and isinstance(f_add[-1].get("action_ms"), (int, float)),
              json.dumps({k: f_add[-1].get(k) for k in ("heard", "intent", "say", "action_ms")}) if f_add else "none")
        title = (f_add[-1]["intent"].get("title") if f_add else "") or "zz-none"
        o_raw = "\n".join(stdout_lines(p))
        check("H5 the same session on stdout (journal): no heard, text or say; intent is the name only; heard_len kept",
              o_add and not {"heard", "text", "say"} & set(o_add[-1]) and o_add[-1].get("intent") == "task.add"
              and o_add[-1].get("heard_len") == len(f_add[-1]["heard"]) and title not in o_raw
              and "Would add" not in o_raw, json.dumps(o_add[-1]) if o_add else "none")
        # the transcript policy: overheard speech after a false wake is not kept anywhere
        r_salt = await stream_session(H.VOICE_URL, CLIPS["salt"], by="wake", wake_at=wake_at("ph_travis"), client="hj")
        r_fadd = await stream_session(H.VOICE_URL, CLIPS["false_add"], by="wake", wake_at=0.9, client="hj")
        await asyncio.sleep(0.5)
        f_salt = rows_for(file_lines(p), ev="session", sid=r_salt["sid"])
        f_fadd = rows_for(file_lines(p), ev="session", sid=r_fadd["sid"])
        whole = "\n".join(file_lines(p)) + o_raw
        check("H6 'hey travis, can you pass the salt' (no intent, no name): words kept nowhere, heard_len and scores kept",
              f_salt and f_salt[-1].get("transcript") == "not_kept" and "heard" not in f_salt[-1] and f_salt[-1].get("heard_len", 0) > 0
              and "salt" not in whole.lower() and f_salt[-1].get("oww") is not None,
              json.dumps({k: f_salt[-1].get(k) for k in ("outcome", "transcript", "heard_len", "wake_text", "oww")}) if f_salt else "none")
        check("H7 a silent reject after a false wake ('add buy milk ...' as a wake): no words, would_run task.add kept",
              f_fadd and f_fadd[-1].get("transcript") == "not_kept" and "heard" not in f_fadd[-1] and f_fadd[-1].get("would_run") == "task.add",
              json.dumps({k: f_fadd[-1].get(k) for k in ("outcome", "why", "transcript", "would_run")}) if f_fadd else "none")
        # the end line (finding 12) and an end after the endpoint
        se = speech_end_s(CLIPS["next"])
        r_end = await stream_session(H.VOICE_URL, CLIPS["next"], by="ptt", client="hj", end_at=se + 0.25, end_why="user")
        r_can = await stream_session(H.VOICE_URL, CLIPS["add_rms"], by="ptt", client="hj", end_at=1.0, end_why="cancel")
        await asyncio.sleep(0.5)
        e_user = rows_for(stdout_lines(p), ev="end", sid=r_end["sid"])
        e_can = rows_for(stdout_lines(p), ev="end", sid=r_can["sid"])
        s_can = rows_for(stdout_lines(p), ev="session", sid=r_can["sid"])
        s_end = rows_for(stdout_lines(p), ev="session", sid=r_end["sid"])
        check("H8 journal: one end line per end message ('\"ev\": \"end\"', why user, state streaming; why cancel)",
              e_user and e_user[0].get("why") == "user" and e_user[0].get("state") == "streaming"
              and e_can and e_can[0].get("why") == "cancel" and s_can and s_can[-1].get("outcome") == "dropped",
              json.dumps({"user": e_user[:1], "cancel": e_can[:1]}))
        check("H9 journal: the V8 literal '\"intent\": \"next.event\"' and a top-level action_ms on the session line",
              s_end and s_end[-1].get("intent") == "next.event" and '"intent": "next.event"' in o_raw + "\n".join(stdout_lines(p))
              and isinstance(s_end[-1].get("action_ms"), (int, float)), json.dumps(s_end[-1]) if s_end else "none")
        # stats telemetry: room loudness in the file only
        c = await tablet(client="tele")
        await c.send(json.dumps({"type": "stats", "secs": 60, "samplesPerSec": 16000, "rmsP10": 0.001, "rmsP50": 0.004,
                                 "rmsP90": 0.02, "rmsMax": 0.3, "dropped": 0}))
        # finding 9: non-finite numbers and line separators from the page
        await c.send('{"type": "stats", "rmsP50": NaN, "engineMsP50": Infinity, "samplesPerSec": -Infinity}')
        await c.send('{"type": "tts_done", "id": "x", "how": "event", "onset_ms": 1e999, "dur_ms": 12}')
        await c.send(json.dumps({"type": "state", "lit": True, "mic": True, "reason": "x y z\u0085w"}))
        await c.send("[" * 100000)
        await asyncio.sleep(0.5)
        alive = c.state.name
        await c.close()
        await asyncio.sleep(0.4)
        fl, ol = file_lines(p), stdout_lines(p)
        st_f = [r for r in rows_for(fl, ev="stats") if r["page"].get("rmsP50") == 0.004]
        st_o = [r for r in rows_for(ol, ev="stats") if r["page"].get("samplesPerSec") == 16000 and r["page"].get("secs") == 60]
        check("H10 stats: room loudness percentiles in the 30-day file, not in the journal",
              st_f and st_o and not any(k.startswith("rms") for k in st_o[-1]["page"]), json.dumps(st_o[-1]) if st_o else "none")
        bad = [x[:120] for x in fl + ol if not strict_ok(x)]
        nonascii = [x[:80] for x in fl + ol if not x.isascii()]
        td = rows_for(fl, ev="tts_done", id="x")
        check("H11 NaN, Infinity and 1e999 from the page: every file and journal line is strict JSON, ASCII only; the "
              "NaN stats message is dropped, 1e999 logged as null", not bad and not nonascii and td and td[-1].get("onset_ms") is None,
              json.dumps({"not_strict": bad[:2], "not_ascii": nonascii[:2]}))
        sep = [r for r in rows_for(fl, ev="state") if " " in str(r.get("reason"))]
        check("H12 a reason with U+2028, U+2029, U+0085 is one escaped line; deep nesting does not end the connection",
              sep and alive == "OPEN" and not [r for r in rows_for(fl, ev="error") if r.get("where") == "handler"],
              f"{len(sep)} lines, connection {alive}")

        # ---- finding 7: the lit rule mid-stream
        c = await tablet(client="dark")
        got = await paced(c, "dark-mid", CLIPS["add_rms"], state_at=0.8,
                          state_msg={"type": "state", "lit": False, "mic": False, "reason": "screensaver"})
        await asyncio.sleep(0.4)
        await c.close()
        drop = rows_for(file_lines(p), ev="session", sid="dark-mid")
        cl = [r for r in rows_for(file_lines(p), ev="close") if r.get("client") == "dark"]
        check("H13 state lit false mid-stream (no end message): the turn is dropped (why dark, by_state), nothing answered, "
              "later frames dropped", not any(m.get("type") in ("result", "endpoint") for _, m in got) and drop
              and drop[-1].get("outcome") == "dropped" and drop[-1].get("why") == "dark" and drop[-1].get("by_state") is True
              and cl and cl[-1].get("dropped_msgs", 0) > 5,
              json.dumps({"msgs": [m.get("type") for _, m in got], "session": drop[-1] if drop else None,
                          "dropped_msgs": cl[-1].get("dropped_msgs") if cl else None}))
        c = await tablet(client="micoff")
        got = await paced(c, "mic-mid", CLIPS["add_rms"], state_at=0.8, state_msg={"type": "state", "mic": False, "reason": "toggle"})
        await asyncio.sleep(0.4)
        await c.close()
        drop = rows_for(file_lines(p), ev="session", sid="mic-mid")
        check("H14 state mic false mid-stream: dropped as mic_off", drop and drop[-1].get("why") == "mic_off" and
              not any(m.get("type") == "result" for _, m in got), json.dumps(drop[-1]) if drop else "none")
        c = await tablet(client="darkafter")
        await c.send(json.dumps({"type": "wake", "sid": "dark-after", "by": "ptt", "preroll_samples": 0}))
        x = np.concatenate([CLIPS["next"], np.zeros(16000 * 2, np.int16)])
        t0, k, got = time.perf_counter(), 0, []
        for i in range(0, len(x), 1280):
            k += 1
            d = k * 0.08 - (time.perf_counter() - t0)
            if d > 0:
                await asyncio.sleep(d)
            try:
                raw = await asyncio.wait_for(c.recv(), 0.001)
                if isinstance(raw, str):
                    got.append(json.loads(raw))
            except asyncio.TimeoutError:
                pass
            if any(m.get("type") == "endpoint" for m in got):
                await c.send(json.dumps({"type": "state", "lit": False, "mic": False, "reason": "screensaver"}))
                break
            await c.send(x[i:i + 1280].tobytes())
        while not any(m.get("type") in ("result", "reject") for m in got):
            raw = await asyncio.wait_for(c.recv(), 10)
            if isinstance(raw, str):
                got.append(json.loads(raw))
        await c.close()
        res = next((m for m in got if m.get("type") == "result"), None)
        check("H15 dark after the endpoint: the turn still finishes (14d 9.3)", res and res["intent"]["name"] == "next.event",
              json.dumps([m.get("type") for m in got]))

        # ---- finding 6: a replaced socket that went silent
        s_old = raw_ws("127.0.0.3")
        s_old.sendall(ws_frame(hello_msg(client="dash").encode()))
        s_old.sendall(ws_frame(json.dumps({"type": "state", "lit": True, "mic": True, "reason": "t"}).encode()))
        s_old.sendall(ws_frame(json.dumps({"type": "wake", "sid": "old1", "by": "ptt", "preroll_samples": 0}).encode()))
        for _ in range(5):
            s_old.sendall(ws_frame(bytes(2560), opcode=2))
        await asyncio.sleep(0.6)                          # the old page now never reads and never answers a close
        c = await connect(H.VOICE_URL, origin=PAGE, local_addr=("127.0.0.3", 0), open_timeout=10, close_timeout=5)
        t_rep = time.perf_counter()
        await c.send(hello_msg(client="dash"))
        await recv_json(c)
        await c.send(json.dumps({"type": "state", "lit": True, "mic": True, "reason": "t"}))
        await c.send(json.dumps({"type": "wake", "sid": "new1", "by": "ptt", "preroll_samples": 0}))
        m = await expect_nothing(c, 0.8)
        first_ok = None if m else round(time.perf_counter() - t_rep, 2)
        await c.send(json.dumps({"type": "end", "sid": "new1", "why": "cancel"}))
        await asyncio.sleep(3.0)
        rows = file_lines(p)
        old_s = rows_for(rows, ev="session", sid="old1")
        repl = rows_for(rows, ev="replaced")
        old_close = [r for r in rows_for(rows, ev="close") if r.get("conn") == (repl[-1].get("old") if repl else -1)]
        check("H16 a newer hello replaces a silent socket: the old turn is dropped at once and the first wake on the new socket is accepted",
              first_ok is not None and first_ok < 1.0 and old_s and old_s[-1].get("why") == "replaced",
              json.dumps({"first_wake_accepted_after_s": first_ok, "old_session": old_s[-1] if old_s else None, "m": m}))
        check("H17 the old socket's mic interval closes at the replacement (mic_closed_s on the replaced line) and the old socket "
              "is gone within the 2 s close timeout", repl and repl[-1].get("mic_closed_s") is not None and old_close
              and old_close[-1].get("secs", 99) < 4.0, json.dumps({"replaced": repl[-1] if repl else None,
                                                                  "old_close": old_close[-1] if old_close else None}))
        await c.close()
        s_old.close()

        # ---- finding 5: a hung dashboard, one read budget from the wake, oww on its own thread, a shared prefetch
        dash_control(get_mode="hang")
        try:
            n_get0 = len([x for x in H.get_json(H.DASH + "/calls") if x["path"] == "/api/data"])
            r_h = await stream_session(H.VOICE_URL, CLIPS["next"], by="ptt", client="hung", tail_s=20.0)
            t_ep, _ = first(r_h["msgs"], "endpoint")
            t_res, res = first(r_h["msgs"], "result")
            n_get1 = len([x for x in H.get_json(H.DASH + "/calls") if x["path"] == "/api/data"])
            check("H18 hung dashboard, push-to-talk 'what is next': 'The dashboard isn't answering.' within the 5 s read budget "
                  "from the wake (15a review: 8.09 s after the endpoint, two sequential timeouts)",
                  res and res["say"] == "The dashboard isn't answering." and t_res is not None and t_res <= 5.6 and n_get1 - n_get0 == 1,
                  json.dumps({"endpoint_s": t_ep, "result_s": t_res, "endpoint_to_result_s": round(t_res - t_ep, 2) if t_res and t_ep else None,
                              "gets": n_get1 - n_get0}))
            async with ws() as cc:
                await cc.send(hello_msg(client="stack"))
                await recv_json(cc)
                for kk in range(4):
                    await cc.send(json.dumps({"type": "wake", "sid": f"st{kk}", "by": "ptt", "preroll_samples": 0}))
                    await cc.send(json.dumps({"type": "end", "sid": f"st{kk}", "why": "cancel"}))
                await asyncio.sleep(0.3)
            r_d = await stream_session(H.VOICE_URL, CLIPS["hj_dark"], by="wake", wake_at=wake_at("ph_jarvis"), client="hung2", tail_s=8.0)
            t_ep2, _ = first(r_d["msgs"], "endpoint")
            t_res2, res2 = first(r_d["msgs"], "result")
            await asyncio.sleep(0.3)
            sess = rows_for(file_lines(p), ev="session", sid=r_d["sid"])
            n_get2 = len([x for x in H.get_json(H.DASH + "/calls") if x["path"] == "/api/data"])
            check("H19 after 4 stacked sessions on a hung dashboard, 'hey jarvis, turn on dark mode' needs no dashboard: "
                  "fast answer, openWakeWord not queued behind HTTP (15a review: 4.07 s, oww 4,252 ms)",
                  res2 and res2["intent"]["name"] == "theme" and t_res2 - t_ep2 < 1.6 and sess and sess[-1].get("oww_ms", 9e9) < 1000,
                  json.dumps({"endpoint_to_result_s": round(t_res2 - t_ep2, 2) if t_res2 and t_ep2 else None,
                              "oww_ms": sess[-1].get("oww_ms") if sess else None}))
            check("H20 one GET /api/data in flight at a time (the 5 stacked wakes shared prefetches instead of 5 blocked threads)",
                  n_get2 - n_get1 <= 2, f"{n_get2 - n_get1} GETs for 5 sessions")
        finally:
            dash_control(get_mode="ok")
        async with ws() as cc:
            await cc.send(hello_msg(client="age"))
            await recv_json(cc)
            await cc.send(json.dumps({"type": "wake", "sid": "age1", "by": "ptt", "preroll_samples": 0}))
            await asyncio.sleep(1.2)
            h1 = H.get_json(H.HTTP + "/health")
            await cc.send(json.dumps({"type": "end", "sid": "age1", "why": "cancel"}))
            await asyncio.sleep(0.3)
        h2 = H.get_json(H.HTTP + "/health")
        check("H21 /health: session_age_s and session_state while a turn is open, null after; stt_busy_s null when idle",
              h1.get("session_active") and 1.0 <= (h1.get("session_age_s") or 0) <= 3.0 and h1.get("session_state") == "streaming"
              and h2.get("session_age_s") is None and h2.get("stt_busy_s") is None and h2.get("ok") is True,
              json.dumps({k: h1.get(k) for k in ("session_age_s", "session_state", "stt_busy_s")}))

        # ---- finding 4: the suppressed count arrives with the window's end (the 15 s tick)
        wait = 60 + 17 - (time.time() - t_flood)
        if wait > 0:
            await asyncio.sleep(wait)
        sup = rows_for(file_lines(p), ev="suppressed")
        n_sup = sum(r.get("n", 0) for r in sup)
        check("H22 one 'suppressed' line per window with the count of the held-back lines",
              sup and n_sup >= 295 + 20 and any(x.get("peer") == "127.0.0.2" for x in sup[0].get("top", [])),
              json.dumps(sup[:1]))
    finally:
        p.stop()

    # ---- finding 8: pacing and the wake rate cap (own server: the cap counts per minute)
    p = H.start_voice(out, "H-rate", {"VOICE_TABLET_IP_FILE": str(ipf)}, limit_s=600)
    try:
        pid = p.child_pid()
        c = await tablet(client="burst")
        burst = np.concatenate([CLIPS["add_rms"], np.zeros(16000, np.int16)]).tobytes()
        await c.send(json.dumps({"type": "wake", "sid": "burst1", "by": "ptt", "preroll_samples": 0}))
        t0 = time.perf_counter()
        await c.send(burst)
        m = await recv_json(c, timeout=5)
        dt_rej = time.perf_counter() - t0
        check("H23 3.5 s of audio sent at once after a wake: reject too_fast at once, no transcription",
              m.get("type") == "reject" and m.get("why") == "too_fast" and dt_rej < 0.5, json.dumps(m) + f" after {dt_rej:.2f} s")
        cpu0, t0, n_wakes, kinds = H.proc_cpu_s(pid), time.time(), 0, {}
        while time.time() - t0 < 30:
            n_wakes += 1
            await c.send(json.dumps({"type": "wake", "sid": f"fl{n_wakes}", "by": "ptt", "preroll_samples": 0}))
            await c.send(burst)
            try:
                mm = await recv_json(c, timeout=5)
            except asyncio.TimeoutError:
                mm = {}
            key = f"{mm.get('why')}{'/' + mm['limit'] if mm.get('limit') else ''}"
            kinds[key] = kinds.get(key, 0) + 1
            await asyncio.sleep(0.05)
        cpu = H.proc_cpu_s(pid) - cpu0
        await c.close()
        await asyncio.sleep(0.5)
        sl = [r for r in rows_for(file_lines(p), ev="session") if str(r.get("sid", "")).startswith("fl")]
        check("H24 a 30 s flood of faster-than-real-time sessions from the tablet peer: no transcription, at most 12 wakes a minute "
              "accepted, the rest reject busy with limit rate, log lines within the budget (15a review: 36 STT runs, 87.1 CPU-s)",
              cpu < 10 and kinds.get("busy/rate", 0) >= n_wakes - 12 and kinds.get("too_fast", 0) <= 11 and len(sl) <= 12 + 5
              and not [r for r in sl if r.get("stt_ms")],
              json.dumps({"wakes": n_wakes, "answers": kinds, "server_cpu_s": round(cpu, 2), "session_lines": len(sl)}))
        async with ws() as cc:
            await cc.send(hello_msg(client="local13"))
            await recv_json(cc)
            lim = 0
            for kk in range(13):
                await cc.send(json.dumps({"type": "wake", "sid": f"lc{kk}", "by": "ptt", "preroll_samples": 0}))
                mm = await expect_nothing(cc, 0.15)
                if mm and '"limit"' in str(mm):
                    lim += 1
                await cc.send(json.dumps({"type": "end", "sid": f"lc{kk}", "why": "cancel"}))
        check("H25 box-local tools keep their own, larger cap (13 quick wakes from 127.0.0.1: none rate-limited)", lim == 0, lim)
    finally:
        p.stop()

    # ---- finding 3: writes that time out after the request went out (live box against the fake dashboard)
    p = H.start_voice(out, "H-live", {"VOICE_DRY_RUN": "0", "VOICE_TABLET_IP_FILE": str(ipf)}, limit_s=600)
    try:
        async def live_add(**mode):
            dash_control(**{"post_mode": "ok", "post_delay_s": 0, **mode})
            n0 = len(H.get_json(H.DASH + "/calls"))
            r = await stream_session(H.VOICE_URL, CLIPS["add_rms"], by="ptt", client="live", dry=False, tail_s=16.0)
            _, res = first(r["msgs"], "result")
            await asyncio.sleep(max(0.0, float(mode.get("post_delay_s", 0)) - 5.0) + 1.0)
            posts = [x for x in H.get_json(H.DASH + "/calls")[n0:] if x["method"] == "POST"]
            rows = rows_for(file_lines(p), ev="session", sid=r["sid"])
            return res, posts, rows
        try:
            res, posts, rows = await live_add(post_delay_s=6.5)
            check("H26 the 15a review case (the dashboard answers the add after 6.5 s): now inside the 7 s write timeout, 'Added ...'",
                  res and res["ok"] and res["say"].startswith("Added") and len(posts) == 1, json.dumps(res and {"say": res["say"], "ok": res["ok"]}))
            res, posts, rows = await live_add(post_delay_s=9.0)
            check("H27 no answer within 7 s (the add lands later): 'I'm not sure that went through. Check the list.', a refresh, "
                  "logged post unknown; never 'couldn't'",
                  res and res["say"] == "I'm not sure that went through. Check the list." and res["card"] == res["say"] and res["ok"] is False
                  and {"what": "refresh"} in res["do"] and len(posts) == 1 and rows and (rows[-1].get("action") or {}).get("post") == "unknown"
                  and rows[-1].get("unsure") is True,
                  json.dumps({"say": res and res["say"], "do": res and res["do"], "dash_recorded": len(posts),
                              "action": rows[-1].get("action") if rows else None}))
            res, posts, rows = await live_add(post_mode="reset")
            check("H28 the dashboard records the add and drops the connection without an answer: the unsure line",
                  res and res["say"] == "I'm not sure that went through. Check the list." and len(posts) == 1, json.dumps(res and {"say": res["say"]}))
            res, posts, rows = await live_add(post_mode="http500")
            check("H29 an HTTP 500 answer: 'I couldn't add that.' (the server answered, the write failed)",
                  res and res["say"] == "I couldn't add that." and rows and (rows[-1].get("action") or {}).get("status") == 500,
                  json.dumps(res and {"say": res["say"]}))
        finally:
            dash_control(post_mode="ok", post_delay_s=0)
    finally:
        p.stop()

    # ---- finding 5: the turn budget releases a stuck turn (shortened budget, a write that hangs)
    p = H.start_voice(out, "H-budget", {"VOICE_DRY_RUN": "0", "VOICE_TUNE": json.dumps({"process_budget_ms": 3000})}, limit_s=300)
    try:
        dash_control(post_delay_s=9.0)
        try:
            r = await stream_session(H.VOICE_URL, CLIPS["add_rms"], by="ptt", client="budget", dry=False, tail_s=16.0)
            t_ep, _ = first(r["msgs"], "endpoint")
            t_res, res = first(r["msgs"], "result")
            hb = H.get_json(H.HTTP + "/health")
            await asyncio.sleep(0.4)
            rows = rows_for(file_lines(p), ev="session", sid=r["sid"])
            errs = [x for x in rows_for(file_lines(p), ev="error") if x.get("sid") == r["sid"]]
            check("H30 a turn over its budget (3 s here, 20 s in production) is released: the unsure line (a write had started), "
                  "the session freed, logged outcome error why process_budget",
                  res and res["say"] == "I'm not sure that went through. Check the list." and 2.5 <= t_res - t_ep <= 4.0
                  and hb.get("session_active") is False and rows and rows[-1].get("why") == "process_budget"
                  and rows[-1].get("write_started") is True and errs,
                  json.dumps({"endpoint_to_result_s": round(t_res - t_ep, 2) if t_res and t_ep else None,
                              "session_active_after": hb.get("session_active"), "row": rows[-1] if rows else None}))
            await asyncio.sleep(7.0)                      # let the late POST land before the next phase
        finally:
            dash_control(post_delay_s=0)
    finally:
        p.stop()

    # ---- findings 4 and 9: the ledger survives a restart (U+2028 in a reason) and a 120 MB log is streamed
    led = Path(out) / "logs-H-ledger"
    led.mkdir(exist_ok=True)
    p = H.start_voice(out, "H-ledger-1", {"VOICE_STAGE": "skeleton", "VOICE_TABLET_IP_FILE": str(ipf), "VOICE_LOG_DIR": str(led)}, limit_s=120)
    try:
        c = await tablet(client="led")
        await asyncio.sleep(2.0)
        await c.send(json.dumps({"type": "state", "lit": True, "mic": False, "reason": "x y"}))
        await c.send(json.dumps({"type": "state", "lit": True, "mic": True, "reason": "b"}))
        await asyncio.sleep(1.0)
        await c.send(json.dumps({"type": "state", "lit": True, "mic": False, "reason": "ok"}))
        await asyncio.sleep(0.3)
        before = H.get_json(H.HTTP + "/stats")["mic_open_s"]
        await c.close()
    finally:
        p.stop()
    p = H.start_voice(out, "H-ledger-2", {"VOICE_STAGE": "skeleton", "VOICE_TABLET_IP_FILE": str(ipf), "VOICE_LOG_DIR": str(led)}, limit_s=120)
    try:
        after = H.get_json(H.HTTP + "/stats")["mic_open_s"]
    finally:
        p.stop()
    check("H31 mic-open seconds survive a restart when a state reason holds U+2028 (15a review: 3.0 before, 1.0 after)",
          abs(before - after) < 0.05 and 2.9 <= after <= 3.4, f"before {before}, after {after}")
    big = Path(out) / "logs-H-big"
    big.mkdir(exist_ok=True)
    day = time.strftime("%Y-%m-%d")
    junk = json.dumps({"ts": "x", "ev": "rejected", "why": "peer", "status": 403, "peer": "10.9.9.9", "origin": None, "path": "/health"}) + "\n"
    with open(big / f"sessions-{day}.jsonl", "w") as fh:
        fh.write(json.dumps({"ts": "x", "ev": "hello", "peer": "192.168.1.89", "lit": True, "lit_rise": True}) + "\n")
        block = junk * 10000
        for _ in range(int(120e6 / len(block))):
            fh.write(block)
        fh.write(json.dumps({"ts": "x", "ev": "state", "peer": "192.168.1.89", "mic_closed_s": 2.5}) + "\n")
        fh.write(json.dumps({"ts": "x", "ev": "session", "peer": "192.168.1.89", "by": "ptt", "outcome": "run", "stt_ms": 700}) + "\n")
    size_mb = (big / f"sessions-{day}.jsonl").stat().st_size / 1e6
    p = H.start_voice(out, "H-big", {"VOICE_STAGE": "skeleton", "VOICE_LOG_DIR": str(big)}, limit_s=180)
    try:
        sj = H.get_json(H.HTTP + "/stats")
        mem = H.proc_mem(p.child_pid())
    finally:
        p.stop()
        for f in big.glob("sessions-*.jsonl"):
            f.unlink()
    check(f"H32 a {size_mb:.0f} MB log of refusals is streamed at start: ledger rebuilt, peak memory stays small "
          "(15a: read whole into memory, an OOM risk under MemoryMax)",
          sj.get("mic_open_s") == 2.5 and sj.get("lit_periods") == 1 and sj.get("sessions") == 1 and mem.get("VmHWM", 999) < 120,
          json.dumps({"stats": {k: sj.get(k) for k in ("mic_open_s", "lit_periods", "sessions")}, "VmHWM_MB": round(mem.get("VmHWM", 0), 1)}))


def make_clips(td):
    spec = {"next": ("what is next", "slt"), "tomorrow": ("what is on my schedule tomorrow", "awb"),
            "shopping": ("add eggs to the shopping list", "slt"), "done": ("mark buy milk as done", "slt"),
            "done_milk": ("mark milk as done", "slt"), "light": ("switch to light mode", "slt"), "cancel": ("never mind", "slt"),
            "add_rms": ("add buy milk to my personal list", "rms"), "dark": ("turn on dark mode", "slt"),
            "salt": ("hey travis, can you pass the salt", "slt"), "false_add": ("add buy milk to my personal list", "slt"),
            "hj_dark": ("hey jarvis, turn on dark mode", "slt"), "ph_jarvis": ("hey jarvis", "slt"), "ph_travis": ("hey travis", "slt")}
    for k, (text, voice) in spec.items():
        path = Path(td) / f"{k}.wav"
        H.flite(text, voice, path)
        CLIPS[k] = load_wav(str(path))


async def main_async(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    phases = [x.strip().upper() for x in a.phases.split(",") if x.strip()]
    with tempfile.TemporaryDirectory(prefix="tvtest-") as td:
        make_clips(td)
        dash = H.start_dash(out)
        try:
            for ph in phases:
                print(f"=== phase {ph} ===", flush=True)
                t0 = time.time()
                if ph == "A":
                    await phase_a(out)
                elif ph == "B":
                    await phase_b(out)
                elif ph == "C":
                    await phase_c(out)
                elif ph == "D":
                    await phase_d(out)
                elif ph == "E":
                    await phase_e(out)
                elif ph == "G":
                    await phase_g(out)
                elif ph == "H":
                    await phase_h(out)
                elif ph == "F":
                    await phase_f(out, dash)
                print(f"=== phase {ph} done in {time.time() - t0:.0f} s ===", flush=True)
        finally:
            if dash.alive():
                dash.stop()
    failed = [r for r in RESULTS if not r["ok"]]
    (out / "results.json").write_text(json.dumps(RESULTS, indent=1))
    n = len([r for r in RESULTS if not r["name"].endswith(("-mem", "-cpu-mem", "-stats", "-mem-end"))])
    print(f"TOTAL {n - len(failed)}/{n} checks passed")
    return 0 if not failed else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--phases", default="A,B,C,D,E,G,H,F")
    return asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    sys.exit(main())
