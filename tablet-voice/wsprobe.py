#!/usr/bin/env python3
"""wsprobe.py: command-line client for tablet-voice, protocol v1 (spec 14 V3 and V4).

  wsprobe.py hello [--url ws://127.0.0.1:8766/] [--origin URL|none] [--source IP]
      Prints the server's hello as one JSON line, or the HTTP refusal ("HTTP 403", exit 2).
  wsprobe.py play WAV [--ptt] [--live] [--url URL] [--origin URL|none] [--wake-at S] [--lead S]
                      [--tts off|page] [--source IP]
      Streams a WAV at real time as one session, the way the page does: a wake session sends a 2.8 s
      pre-roll that ends at the wake instant (--wake-at seconds into the clip, default 1.0), push-to-talk
      (--ptt) a 0.4 s pre-roll that ends where the clip starts; then 80 ms frames until the box answers.
      Prints every box message as {"t": seconds after the wake instant, "msg": ...}, then a summary line.
      Dry unless --live: the box honours a dry hello from 127.0.0.1 only, and a box started with
      VOICE_DRY_RUN=1 stays dry whatever the client asks.

The default Origin is the page's (http://localhost:8765); "--origin none" sends no Origin header.
--source binds the client socket to a local address (127.0.0.2 proves the peer allowlist on one box).
"""
import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
import wave

import numpy as np
from websockets.asyncio.client import connect
from websockets.exceptions import InvalidStatus

RATE = 16000
FRAME = 1280                   # 80 ms, 2,560 bytes
DEFAULT_URL = "ws://127.0.0.1:8766/"
PAGE_ORIGIN = "http://localhost:8765"


def load_wav(path) -> np.ndarray:
    """16 kHz mono Int16 samples; any other format is converted with ffmpeg."""
    try:
        with wave.open(path) as w:
            if w.getframerate() == RATE and w.getnchannels() == 1 and w.getsampwidth() == 2:
                return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").copy()
    except (wave.Error, EOFError):
        pass
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "c.wav")
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", path, "-ar", str(RATE), "-ac", "1",
                        "-sample_fmt", "s16", "-y", out], check=True, timeout=60)
        with wave.open(out) as w:
            return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").copy()


def speech_end_s(clip: np.ndarray, thresh=327) -> float:
    """Seconds to the last sample above about -40 dBFS (the real end of speech in a padded clip)."""
    idx = np.nonzero(np.abs(clip.astype(np.int32)) > thresh)[0]
    return (idx[-1] + 1) / RATE if len(idx) else 0.0


def _kw(origin, source):
    kw = {"open_timeout": 10, "max_size": 2 ** 20, "close_timeout": 5}
    if origin:
        kw["origin"] = origin
    if source:
        kw["local_addr"] = (source, 0)
    return kw


async def hello(url, origin=PAGE_ORIGIN, source=None, client="wsprobe", extra=None):
    """Returns the server's hello dict; raises InvalidStatus on an HTTP refusal."""
    async with connect(url, **_kw(origin, source)) as ws:
        msg = {"type": "hello", "v": 1, "client": client, "build": "wsprobe", "rate": RATE, "frame": FRAME,
               "lit": True, "fully": True, "tts": "off", "dry": True, "wake": {"engine": "wsprobe"}}
        msg.update(extra or {})
        await ws.send(json.dumps(msg))
        return json.loads(await asyncio.wait_for(ws.recv(), 10))


async def stream_session(url, clip, *, by="wake", wake_at=1.0, lead=2.0, dry=True, tts="off", fully=True,
                         lit=True, mic=True, origin=PAGE_ORIGIN, source=None, client="wsprobe", printer=None,
                         end_at=None, end_why="user", close_on_endpoint=False, tail_s=17.0, score=0.99, bed=None):
    """Stream one session like the page and collect the box's messages.

    Times are seconds after the wake instant (the end of the pre-roll). Returns a dict with hello, msgs
    [(t, msg)], speech_end (the end of speech in the same time base) and sid."""
    x = np.concatenate([np.zeros(int(lead * RATE), np.int16), clip.astype(np.int16), np.zeros(int(tail_s * RATE), np.int16)])
    if bed is not None:                       # a continuous noise floor under the whole stream (tests only)
        b = np.resize(bed.astype(np.int32), len(x))
        x = np.clip(x.astype(np.int32) + b, -32768, 32767).astype(np.int16)
    wake_i = int(round((lead + (wake_at if by == "wake" else 0.0)) * RATE))
    pre_n = int(2.8 * RATE) if by == "wake" else int(0.4 * RATE)
    pre = x[max(0, wake_i - pre_n):wake_i]
    speech_end = lead + speech_end_s(clip) - wake_i / RATE
    sid = uuid.uuid4().hex[:12]
    msgs = []
    async with connect(url, **_kw(origin, source)) as ws:
        await ws.send(json.dumps({"type": "hello", "v": 1, "client": client, "build": "wsprobe", "rate": RATE,
                                  "frame": FRAME, "lit": lit, "fully": fully, "tts": tts, "dry": dry,
                                  "wake": {"engine": "wsprobe", "model": "none"}}))
        hel = json.loads(await asyncio.wait_for(ws.recv(), 10))
        await ws.send(json.dumps({"type": "state", "lit": lit, "mic": mic, "reason": "wsprobe"}))
        t0 = time.perf_counter()
        await ws.send(json.dumps({"type": "wake", "sid": sid, "by": by, "score": score if by == "wake" else None,
                                  "preroll_samples": int(len(pre)), "t_ms": int(time.time() * 1000)}))
        if len(pre):
            await ws.send(pre.tobytes())
        st = {"stop": False}
        done = asyncio.Event()

        async def reader():
            async for raw in ws:
                if not isinstance(raw, str):
                    continue
                m = json.loads(raw)
                t = round(time.perf_counter() - t0, 3)
                msgs.append((t, m))
                if printer:
                    printer(t, m)
                kind = m.get("type")
                if kind in ("endpoint", "reject"):
                    st["stop"] = True
                if kind == "endpoint" and close_on_endpoint:
                    await ws.close()
                    done.set()
                    return
                if kind == "reject":
                    done.set()
                elif kind == "result":
                    asyncio.get_running_loop().call_later(0.6, done.set)   # a tts_start follows at once, if any

        rd = asyncio.create_task(reader())
        i, k, ended = wake_i, 0, False
        while i < len(x) and not st["stop"] and not rd.done():
            k += 1
            delay = k * FRAME / RATE - (time.perf_counter() - t0)    # frame k is sent when its 80 ms are complete
            if delay > 0:
                await asyncio.sleep(delay)
            if st["stop"] or rd.done():
                break
            await ws.send(x[i:i + FRAME].tobytes())
            i += FRAME
            if end_at is not None and not ended and time.perf_counter() - t0 >= end_at:
                ended = True
                await ws.send(json.dumps({"type": "end", "sid": sid, "why": end_why}))
                if end_why not in ("user", "maxlen"):
                    break                                            # dark, cancel, error: the page stops at once
        try:
            await asyncio.wait_for(done.wait(), 12)
        except asyncio.TimeoutError:
            pass
        rd.cancel()
    return {"hello": hel, "msgs": msgs, "speech_end": round(speech_end, 3), "sid": sid}


def first(msgs, kind):
    return next(((t, m) for t, m in msgs if m.get("type") == kind), (None, None))


def summary(r) -> dict:
    t_ep, _ = first(r["msgs"], "endpoint")
    t_res, res = first(r["msgs"], "result")
    t_rej, rej = first(r["msgs"], "reject")
    out = {"speech_end_s": r["speech_end"]}
    if t_ep is not None:
        out["endpoint_after_speech_s"] = round(t_ep - r["speech_end"], 2)
    if res is not None:
        out.update(result_after_speech_s=round(t_res - r["speech_end"], 2), intent=res.get("intent"),
                   say=res.get("say"), refused=res.get("refused"), dry=res.get("dry"))
    if rej is not None:
        out.update(reject=rej.get("why"), reject_stage=rej.get("stage"), reject_at_s=t_rej)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="tablet-voice protocol v1 probe")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("hello", "play"):
        p = sub.add_parser(name)
        p.add_argument("--url", default=DEFAULT_URL)
        p.add_argument("--origin", default=PAGE_ORIGIN, help='Origin header, or "none"')
        p.add_argument("--source", default=None, help="local address to bind (e.g. 127.0.0.2)")
        if name == "play":
            p.add_argument("wav")
            p.add_argument("--ptt", action="store_true")
            p.add_argument("--live", action="store_true", help="ask for a live (non-dry) session")
            p.add_argument("--wake-at", type=float, default=1.0)
            p.add_argument("--lead", type=float, default=2.0)
            p.add_argument("--tts", choices=("off", "page"), default="off")
    a = ap.parse_args(argv)
    origin = None if a.origin.lower() == "none" else a.origin
    try:
        if a.cmd == "hello":
            print(json.dumps(asyncio.run(hello(a.url, origin, a.source))))
            return 0
        clip = load_wav(a.wav)
        r = asyncio.run(stream_session(a.url, clip, by="ptt" if a.ptt else "wake", wake_at=a.wake_at, lead=a.lead,
                                       dry=not a.live, tts=a.tts, origin=origin, source=a.source,
                                       printer=lambda t, m: print(json.dumps({"t": t, "msg": m}), flush=True)))
        print(json.dumps({"summary": summary(r)}))
        return 0 if any(m.get("type") in ("result", "reject") for _, m in r["msgs"]) else 1
    except InvalidStatus as e:
        print(f"HTTP {e.response.status_code}")
        return 2
    except (OSError, asyncio.TimeoutError) as e:
        print(f"connect failed: {type(e).__name__}: {e}")
        return 3


if __name__ == "__main__":
    sys.exit(main())
