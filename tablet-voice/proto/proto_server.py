"""Prototype of the box voice service (scratch only). Dry run: no task writes, no Fully REST call.
Protocol v1: JSON text frames + binary Int16LE mono 16 kHz frames (1280 samples = 80 ms)."""
import asyncio, json, sys, time, wave, logging, urllib.request
from concurrent.futures import ThreadPoolExecutor
import numpy as np, onnxruntime as ort
from websockets.asyncio.server import serve
from faster_whisper import WhisperModel
from faster_whisper.vad import get_vad_model
sys.path.insert(0, sys.argv[1]); from intents import strip_wake, match
OWW_DIR, PORT = sys.argv[2], int(sys.argv[3])
CFG = dict(vad_on=0.5, vad_off=0.35, onset_s=0.096, end_sil_s=0.8, no_speech_s=4.0, max_cmd_s=8.0,
           max_session_s=15.0, max_preroll_s=3.2, oww_extra_s=0.64, oww_reject=0.10, oww_ok=0.5, enforce_reject=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("voice")
STT = ThreadPoolExecutor(max_workers=1)        # one STT at a time; keeps the event loop free
WHISPER = WhisperModel("base.en", device="cpu", compute_type="int8", cpu_threads=4, local_files_only=True)
VAD_SESS = get_vad_model().session
_o = ort.SessionOptions(); _o.intra_op_num_threads = 1; _o.inter_op_num_threads = 1
MEL, EMB, WW = (ort.InferenceSession(f"{OWW_DIR}/{f}", _o, providers=["CPUExecutionProvider"])
                for f in ("melspectrogram.onnx", "embedding_model.onnx", "hey_jarvis_v0.1.onnx"))

def oww_score(pcm16):
    spec = np.squeeze(MEL.run(None, {"input": pcm16.astype(np.float32)[None, :]})[0]) / 10 + 2
    wins = [spec[i:i + 76] for i in range(0, spec.shape[0] - 75, 8)]
    if len(wins) < 16: return 0.0
    e = EMB.run(None, {"input_1": np.asarray(wins, np.float32)[..., None]})[0].reshape(len(wins), 96)
    return max(float(WW.run(None, {"x.1": e[j - 16:j][None]})[0][0, 0]) for j in range(16, len(e) + 1))

class StreamVAD:
    def __init__(self):
        self.h = np.zeros((1, 1, 128), np.float32); self.c = np.zeros((1, 1, 128), np.float32)
        self.ctx = np.zeros(64, np.float32); self.buf = np.zeros(0, np.float32)
    def feed(self, f32):
        self.buf = np.concatenate([self.buf, f32]); out = []
        while len(self.buf) >= 512:
            ch, self.buf = self.buf[:512], self.buf[512:]
            p, self.h, self.c = VAD_SESS.run(None, {"input": np.concatenate([self.ctx, ch])[None, :], "h": self.h, "c": self.c})
            self.ctx = ch[-64:]; out.append(float(p[0]))
        return out

class Session:
    def __init__(self, m):
        self.sid, self.by = m.get("sid"), m.get("by", "wake")
        self.pre = min(int(m.get("preroll_samples", 0)), int(CFG["max_preroll_s"] * 16000))
        self.chunks, self.n, self.vad, self.t_vad = [], 0, StreamVAD(), 0.0
        self.onset = None; self.run = 0.0; self.sil = 0.0; self.done = None
        self.oww = None; self.oww_task = None; self.t0 = time.perf_counter(); self.t_end = None
    def feed(self, pcm16):
        self.chunks.append(pcm16); self.n += len(pcm16)
        for p in self.vad.feed(pcm16.astype(np.float32) / 32768):
            self.t_vad += 0.032
            live = self.t_vad - self.pre / 16000           # seconds after the wake instant (negative = pre-roll)
            if live < 0 and self.by == "wake":
                continue                                   # pre-roll only warms the VAD state
            if self.onset is None:
                self.run = self.run + 0.032 if p >= CFG["vad_on"] else 0.0
                if self.run >= CFG["onset_s"]: self.onset = self.t_vad - self.run
                elif live >= CFG["no_speech_s"]: return "no_speech"
            else:
                self.sil = self.sil + 0.032 if p < CFG["vad_off"] else 0.0
                if self.sil >= CFG["end_sil_s"]: return "silence"
                if self.t_vad - self.onset >= CFG["max_cmd_s"]: return "maxlen"
            if live >= CFG["max_session_s"]: return "maxlen"
        return None
    def audio(self): return np.concatenate(self.chunks) if self.chunks else np.zeros(0, np.int16)

def transcribe(pcm16):
    t = time.perf_counter()
    segs = list(WHISPER.transcribe(pcm16.astype(np.float32) / 32768, language="en", beam_size=1, vad_filter=False,
                                   condition_on_previous_text=False, without_timestamps=True, temperature=0.0,
                                   no_speech_threshold=0.6, log_prob_threshold=-1.0)[0])
    text = " ".join(s.text.strip() for s in segs)
    nsp = max((s.no_speech_prob for s in segs), default=1.0); lp = min((s.avg_logprob for s in segs), default=-9.0)
    return text, nsp, lp, time.perf_counter() - t

HALLU = {"", "you", "thank you", "thanks for watching", "bye", "okay", "uh", "um", "hmm"}
async def finish(ws, s, why):
    loop = asyncio.get_running_loop(); t_ep = time.perf_counter()
    await ws.send(json.dumps({"type": "endpoint", "sid": s.sid, "why": why}))
    if s.oww_task: await s.oww_task
    text, nsp, lp, stt_s = await loop.run_in_executor(STT, transcribe, s.audio())
    junk = (lp < -1.0) or (nsp > 0.5 and lp < -0.6) or text.lower().strip(" .!?") in HALLU
    oww_hi = s.by == "ptt" or (s.oww or 0) >= CFG["oww_ok"]
    rest, wake_txt = strip_wake(text, wake_audio=oww_hi)
    it = {"intent": None} if junk else match(rest)
    accept = s.by == "ptt" or (it["intent"] and (oww_hi or wake_txt))
    say = None
    if accept and it["intent"] == "task.add":
        say = f"Added {it['title']} to {it['list']}" + (f" for {it['due']}" if it.get("due") else "") + "."
    elif accept and it["intent"] == "theme": say = f"{it['value'].capitalize()} mode."
    elif accept and it["intent"]: say = f"(dry run: {it['intent']})"
    elif s.by == "ptt" or (oww_hi and wake_txt): say = "Sorry, I didn't catch that."
    t_res = time.perf_counter()
    await ws.send(json.dumps({"type": "result", "sid": s.sid, "heard": text, "intent": it, "accepted": bool(accept),
                              "say": say, "timing_ms": {"stt": round(stt_s * 1000), "endpoint_to_result": round((t_res - t_ep) * 1000)}}))
    if say: await ws.send(json.dumps({"type": "tts_start", "sid": s.sid, "id": f"r{s.sid}", "est_ms": 900 + 70 * len(say), "via": "rest"}))
    log.info(json.dumps({"ev": "session", "sid": s.sid, "by": s.by, "why": why, "oww": s.oww, "audio_s": round(s.n / 16000, 2),
                         "onset_s": s.onset and round(s.onset, 2), "nsp": round(nsp, 3), "lp": round(lp, 2), "text": text,
                         "wake_text": wake_txt, "intent": it, "accepted": bool(accept), "stt_ms": round(stt_s * 1000)}))

async def handler(ws):
    s = None; loop = asyncio.get_running_loop()
    async for msg in ws:
        if isinstance(msg, bytes):
            if s is None or s.done: continue
            ev = s.feed(np.frombuffer(msg, dtype="<i2"))
            if s.by == "wake" and s.oww_task is None and s.n >= s.pre + CFG["oww_extra_s"] * 16000:
                s.oww_task = loop.run_in_executor(None, oww_score, s.audio()[-int((s.pre / 16000 + CFG["oww_extra_s"]) * 16000):])
                s.oww = await s.oww_task
                if CFG["enforce_reject"] and s.oww < CFG["oww_reject"]:
                    s.done = "reject"; await ws.send(json.dumps({"type": "reject", "sid": s.sid, "why": "wake_check", "oww": round(s.oww, 3)}))
                    log.info(json.dumps({"ev": "reject", "sid": s.sid, "oww": s.oww})); continue
            if ev == "no_speech":
                s.done = ev; await ws.send(json.dumps({"type": "reject", "sid": s.sid, "why": "no_command"}))
            elif ev:
                s.done = ev; await finish(ws, s, ev)
            continue
        m = json.loads(msg); t = m.get("type")
        if t == "hello":
            await ws.send(json.dumps({"type": "hello", "v": 1, "server": "tablet-voice-proto", "rate": 16000, "frame": 1280}))
        elif t == "wake":
            if s and not s.done: await ws.send(json.dumps({"type": "reject", "sid": m.get("sid"), "why": "busy"})); continue
            s = Session(m)
        elif t == "end" and s and not s.done:
            s.done = m.get("why", "user")
            if s.done == "user" and s.onset is not None: await finish(ws, s, "user")
        elif t == "tts_done":
            log.info(json.dumps({"ev": "tts_done", **m}))

async def main():
    WHISPER.transcribe(np.zeros(16000, np.float32), language="en", beam_size=1)  # (lazy) warm-up
    async with serve(handler, "127.0.0.1", PORT, origins=["http://localhost:8765", None], max_size=2**20, ping_interval=20):
        log.info(f"listening on 127.0.0.1:{PORT}"); await asyncio.Future()
asyncio.run(main())
