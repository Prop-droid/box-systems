"""Fake page: sends hello, wake + pre-roll, then live 80 ms frames in real time. Prints message arrival times."""
import asyncio, json, sys, time, wave, numpy as np
from websockets.asyncio.client import connect
def load(p):
    with wave.open(p) as w: return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
async def run(port, path, lead_s, wake_after_s, by, label):
    x = load(path); x = np.concatenate([np.zeros(int(lead_s * 16000), np.int16), x, np.zeros(int(2.5 * 16000), np.int16)])
    speech_end = lead_s + len(load(path)) / 16000                 # end of the synthetic speech in stream time
    wake_i = int((lead_s + wake_after_s) * 16000)                  # page detection instant
    pre = x[max(0, wake_i - int(2.8 * 16000)):wake_i] if by == "wake" else x[:0]
    async with connect(f"ws://127.0.0.1:{port}/", origin="http://localhost:8765") as ws:
        await ws.send(json.dumps({"type": "hello", "v": 1, "client": "proto"})); await ws.recv()
        t0 = time.perf_counter(); stream_t0 = wake_i / 16000 if by == "wake" else 0.0
        await ws.send(json.dumps({"type": "wake", "sid": label, "by": by, "score": 0.98, "preroll_samples": len(pre)}))
        if len(pre): await ws.send(pre.tobytes())
        got = []
        async def reader():
            async for msg in ws:
                m = json.loads(msg); m["_t_stream"] = round(stream_t0 + time.perf_counter() - t0, 2); got.append(m)
                if m["type"] in ("reject",) or m["type"] == "tts_start" or (m["type"] == "result" and not m.get("say")): return
        rd = asyncio.create_task(reader())
        i = wake_i if by == "wake" else 0
        while i < len(x) and not rd.done():
            await ws.send(x[i:i + 1280].tobytes()); i += 1280
            await asyncio.sleep(max(0, (i - (wake_i if by == "wake" else 0)) / 16000 - (time.perf_counter() - t0)))
        await asyncio.wait_for(rd, 10)
        res = next((m for m in got if m["type"] == "result"), None)
        ep = next((m for m in got if m["type"] in ("endpoint", "reject")), None)
        print(json.dumps({"case": label, "speech_end_s": round(speech_end, 2), "endpoint_at_s": ep and ep["_t_stream"],
                          "endpoint": ep and {k: ep[k] for k in ep if k in ("type", "why", "oww")},
                          "result_at_s": res and res["_t_stream"],
                          "speech_end_to_result_s": res and round(res["_t_stream"] - speech_end, 2),
                          "heard": res and res["heard"], "intent": res and res["intent"], "say": res and res["say"],
                          "timing_ms": res and res["timing_ms"]}))
async def main():
    port, A = int(sys.argv[1]), sys.argv[2]
    await run(port, f"{A}/hj_add_slt.wav", 1.6, 1.0, "wake", "hj_add_slt")        # wake fires 1.0 s into the clip
    await run(port, f"{A}/dark_slt.wav", 1.6, 0.9, "wake", "dark_slt")
    await run(port, f"{A}/done_rms.wav", 1.6, 1.0, "wake", "done_rms")
    await run(port, f"{A}/add_milk_rms.wav", 0.3, 0.0, "ptt", "ptt_add_milk_rms")
    await run(port, f"{A}/not_wake_slt.wav", 1.6, 1.0, "wake", "not_wake_slt")    # 'hey travis ...'
    await run(port, f"{A}/add_milk_slt.wav", 1.6, 0.9, "wake", "no_wake_phrase")  # false trigger on a non-wake command
    await run(port, f"{A}/noise_only_3s.wav", 1.0, 1.0, "wake", "noise_only")
asyncio.run(main())
