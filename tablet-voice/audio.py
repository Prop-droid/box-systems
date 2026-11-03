"""audio.py: streaming Silero VAD and the openWakeWord "hey jarvis" re-check (14d sections 4 and 5a).

Both are the validated prototype code: the VAD is the Silero v6 model bundled with faster-whisper 1.2.1
(input [n, 576] = 64 samples of context plus a 512-sample chunk, h and c state [1, 1, 128] carried between
calls); the wake check runs openWakeWord's three ONNX files with numpy and onnxruntime only (no openwakeword
package), one intra-op thread each. Audio is only ever held in RAM by the caller.
"""
import hashlib
from pathlib import Path

import numpy as np
import onnxruntime as ort

# openWakeWord release v0.5.1 files and their sha256 (14d section 1). The server refuses to start on a mismatch.
OWW_FILES = {
    "melspectrogram.onnx": "ba2b0e0f8b7b875369a2c89cb13360ff53bac436f2895cced9f479fa65eb176f",
    "embedding_model.onnx": "70d164290c1d095d1d4ee149bc5e00543250a7316b59f31d056cff7bd3075c1f",
    "hey_jarvis_v0.1.onnx": "94a13cfe60075b132f6a472e7e462e8123ee70861bc3fb58434a73712ee0d2cb",
}
CHUNK = 512          # VAD chunk: 32 ms at 16 kHz
CONTEXT = 64         # VAD context samples carried from the previous chunk

_VAD = None          # onnxruntime session of faster_whisper/assets/silero_vad_v6.onnx
_MEL = _EMB = _WW = None


def verify_models(models_dir) -> None:
    """Raise RuntimeError unless every openWakeWord file exists with the expected sha256."""
    for name, want in OWW_FILES.items():
        p = Path(models_dir) / name
        if not p.is_file():
            raise RuntimeError(f"missing model file {p} (run setup_models.sh)")
        got = hashlib.sha256(p.read_bytes()).hexdigest()
        if got != want:
            raise RuntimeError(f"sha256 mismatch for {p}: {got} (run setup_models.sh)")


def load(models_dir) -> None:
    """Load the VAD and the three openWakeWord sessions (about 30 ms; call once at start)."""
    global _VAD, _MEL, _EMB, _WW
    from faster_whisper.vad import get_vad_model   # sets 1 intra-op and 1 inter-op thread itself
    verify_models(models_dir)
    _VAD = get_vad_model().session
    o = ort.SessionOptions()
    o.intra_op_num_threads = 1
    o.inter_op_num_threads = 1
    o.log_severity_level = 3
    _MEL, _EMB, _WW = (ort.InferenceSession(str(Path(models_dir) / f), o, providers=["CPUExecutionProvider"])
                       for f in ("melspectrogram.onnx", "embedding_model.onnx", "hey_jarvis_v0.1.onnx"))


class StreamVAD:
    """One instance per session (state must not leak between sessions). feed() takes float32 in [-1, 1]
    of any length and returns one speech probability per completed 512-sample (32 ms) chunk."""

    def __init__(self):
        self.h = np.zeros((1, 1, 128), np.float32)
        self.c = np.zeros((1, 1, 128), np.float32)
        self.ctx = np.zeros(CONTEXT, np.float32)
        self.buf = np.zeros(0, np.float32)

    def feed(self, f32: np.ndarray) -> list:
        self.buf = np.concatenate([self.buf, f32.astype(np.float32, copy=False)])
        out = []
        while len(self.buf) >= CHUNK:
            ch, self.buf = self.buf[:CHUNK], self.buf[CHUNK:]
            p, self.h, self.c = _VAD.run(None, {"input": np.concatenate([self.ctx, ch])[None, :],
                                                "h": self.h, "c": self.c})
            self.ctx = ch[-CONTEXT:]
            out.append(float(p[0]))
        return out


def oww_score(pcm16: np.ndarray) -> float:
    """Max hey_jarvis probability over int16 PCM at 16 kHz; needs about 2.0 s or more (else 0.0)."""
    if len(pcm16) < 400:
        return 0.0
    spec = np.squeeze(_MEL.run(None, {"input": pcm16.astype(np.float32)[None, :]})[0]) / 10 + 2  # int16 scale
    if spec.ndim != 2:
        return 0.0
    wins = [spec[i:i + 76] for i in range(0, spec.shape[0] - 75, 8)]                       # one window per 80 ms
    if len(wins) < 16:
        return 0.0
    emb = _EMB.run(None, {"input_1": np.asarray(wins, np.float32)[..., None]})[0].reshape(len(wins), 96)
    return max(float(_WW.run(None, {"x.1": emb[j - 16:j][None]})[0][0, 0]) for j in range(16, len(emb) + 1))
