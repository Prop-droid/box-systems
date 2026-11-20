"""Loop gate in stt.transcribe (F2 follow-up, 2026-11-04), checked through a fake model: no Whisper load, no audio.
A decode whose compression ratio is above 2.4 comes back as "" with its scores, so is_junk drops it.
Run: .venv/bin/python tests/test_stt_gate.py   (exit 0 = every case passes)"""
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import stt  # noqa: E402


class FakeModel:
    def __init__(self, segs):
        self.segs, self.kw = segs, None

    def transcribe(self, audio, **kw):
        self.kw = kw
        return iter(self.segs), None


def seg(text, ratio, no_speech=0.01, lp=-0.2):
    return SimpleNamespace(text=text, compression_ratio=ratio, no_speech_prob=no_speech, avg_logprob=lp)


LOOP = " Add a little bit of" + " a little bit of" * 55        # shaped like the P1 pink-noise loop (ratio 25.6)
cases = [
    # (name, segments, expected transcribe() result, expected is_junk)
    ("command, ratio 0.8", [seg(" Add by milk to my personal list.", 0.8, 0.0128, -0.2196)],
     ("Add by milk to my personal list.", 0.0128, -0.2196), False),
    ("pink-noise loop, ratio 25.6", [seg(LOOP, 25.6, 0.9262, -0.1279)], ("", 0.9262, -0.1279), True),
    ("ratio exactly 2.4 is kept", [seg(" Add eggs to the shopping list.", 2.4)], ("Add eggs to the shopping list.", 0.01, -0.2), False),
    ("one looping segment of two", [seg(" Add milk.", 0.7, 0.02, -0.3), seg(" la la la", 2.41, 0.05, -0.4)], ("", 0.05, -0.4), True),
    ("no segments", [], ("", 1.0, -9.0), True),
]


def main() -> int:
    ok, n = 0, 0
    for name, segs, want, junk in cases:
        stt._MODEL = FakeModel(segs)
        got = stt.transcribe(np.zeros(16000, np.int16))
        kw = stt._MODEL.kw
        good = (isinstance(got, tuple) and len(got) == 3 and got == want and all(isinstance(x, float) for x in got[1:])
                and stt.is_junk(*got) is junk and kw["temperature"] == 0.0
                and kw["compression_ratio_threshold"] == stt.LOOP_RATIO)
        ok += good
        n += 1
        print(f"{'PASS' if good else 'FAIL'} {name:30s} -> ({got[0][:40]!r}, {got[1]}, {got[2]}) junk={stt.is_junk(*got)}")
    for ratios, want in (([], False), ([2.4], False), ([2.41], True), ([0.8, 25.6], True), ([1.02], False)):
        good = stt.is_loop(ratios) is want
        ok += good
        n += 1
        print(f"{'PASS' if good else 'FAIL'} is_loop({ratios}) -> {stt.is_loop(ratios)}")
    good = stt.is_junk(LOOP.strip(), 0.9262, -0.1279) is False    # why the gate exists: the scores alone let it through
    ok += good
    n += 1
    print(f"{'PASS' if good else 'FAIL'} the loop text with its scores passes is_junk without the gate")
    print(f"{ok}/{n} pass")
    return 0 if ok == n else 1


if __name__ == "__main__":
    sys.exit(main())
