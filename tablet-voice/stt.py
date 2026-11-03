"""stt.py: faster-whisper base.en int8, resident in the service (14d section 6).

load() builds the model from the local Hugging Face cache only (local_files_only, plus HF_HUB_OFFLINE=1 in the
unit) and decodes 1 s of silence as a warm-up. transcribe() uses 14d 6a's settings: greedy (beam 1),
temperature 0, no prompt, no timestamps, no VAD filter (the service already endpointed). is_junk() is 14d 6c's
gate on top of faster-whisper's own no-speech rule.
"""
import logging
import time

import numpy as np
from faster_whisper import WhisperModel

from intents import norm

NAME = "faster-whisper base.en int8"
JUNK_TEXT = {"", "you", "thank you", "thanks for watching", "bye", "okay", "uh", "um", "hmm"}
_MODEL = None


def load(threads: int = 4) -> dict:
    """Load base.en (int8, CPU) and warm it up; returns load and warm-up times in ms."""
    global _MODEL
    logging.getLogger("faster_whisper").setLevel(logging.WARNING)
    t0 = time.perf_counter()
    _MODEL = WhisperModel("base.en", device="cpu", compute_type="int8", cpu_threads=threads,
                          num_workers=1, local_files_only=True)
    t1 = time.perf_counter()
    transcribe(np.zeros(16000, np.int16))
    t2 = time.perf_counter()
    return {"load_ms": round((t1 - t0) * 1000), "warmup_ms": round((t2 - t1) * 1000)}


def transcribe(pcm16: np.ndarray):
    """Returns (text, max no_speech_prob, min avg_logprob) over the segments; no segments = (\"\", 1.0, -9.0)."""
    segs, _info = _MODEL.transcribe(
        pcm16.astype(np.float32) / 32768.0, language="en", beam_size=1, temperature=0.0,
        condition_on_previous_text=False, without_timestamps=True, vad_filter=False,
        no_speech_threshold=0.6, log_prob_threshold=-1.0, compression_ratio_threshold=2.4,
        initial_prompt=None, hotwords=None)
    segs = list(segs)                       # the decode happens while the generator is consumed
    text = " ".join(s.text.strip() for s in segs).strip()
    no_speech = max((s.no_speech_prob for s in segs), default=1.0)
    avg_logprob = min((s.avg_logprob for s in segs), default=-9.0)
    return text, float(no_speech), float(avg_logprob)


def is_junk(text: str, no_speech: float, avg_logprob: float) -> bool:
    """14d 6c: junk if min avg_logprob < -1.0, or max no_speech > 0.5 with avg_logprob < -0.6, or a known filler."""
    return avg_logprob < -1.0 or (no_speech > 0.5 and avg_logprob < -0.6) or norm(text) in JUNK_TEXT
