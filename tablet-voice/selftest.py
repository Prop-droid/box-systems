#!/usr/bin/env python3
"""selftest.py: end-to-end check of a running tablet-voice in dry run (spec 14 V4).

Makes the 9 clips of the V4 table with ffmpeg's flite voices (slt, rms) in a temporary folder that is deleted
at exit, streams each at real time like the page (wake: a 2.8 s pre-roll ending just after the wake phrase;
push-to-talk: a 0.4 s pre-roll), and checks the box's answer against the table, reading oww_reject,
allow_complete and read_needs_wake_text from the box hello. Where the table depends on a score ("hey travis,
what is next", the early reject), the check follows the box's own rule on the openWakeWord score the box
reports. Every endpoint must arrive within 1.0 s of the end of speech and every result within 2.0 s,
measured as 14d did (from the end of the synthetic clip, which these bounds were calibrated on); the line also
shows the stricter figure from the last loud sample (flite clips end with 0.08 to 0.20 s of silence). A clip
whose answer is right but late is streamed once more and both timings are printed (STT spikes from other load
on the 4-core box are common; a slow box fails both attempts).
Prints one line per clip and PASS n/9; exit 0 only for 9/9, 1 on a failed clip, 2 on a setup error.
It never writes: it asks for dry run and aborts unless the box confirms dry for this connection (the box
honours a dry hello from 127.0.0.1 only).

  .venv/bin/python selftest.py [--url ws://127.0.0.1:8766/] [--noise-bed AMP] [--only N,...] [--json]

--noise-bed AMP adds a continuous pink noise floor (ffmpeg anoisesrc amplitude, e.g. 0.006) under every clip,
an extra robustness check that is not part of the V4 table.
"""
import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wsprobe import DEFAULT_URL, RATE, first, load_wav, speech_end_s, stream_session  # noqa: E402

CARD = 'Didn\'t catch "Jarvis". Tap the mic to add tasks.'
DETECT_S = 0.12          # page detection delay after the end of the phrase: median of 14c 5e (0.06 to 0.28 s)
EP_MAX_S, RES_MAX_S = 1.0, 2.0

CASES = [  # n, name, text, voice, by, wake phrase (sets the wake instant) or a fixed wake_at
    (1, "hj_add_slt", "hey jarvis, add buy milk to my personal list", "slt", "wake", "hey jarvis", None),
    (2, "hj_dark_slt", "hey jarvis, turn on dark mode", "slt", "wake", "hey jarvis", None),
    (3, "hj_done_rms", "hey jarvis, mark buy milk as done", "rms", "wake", "hey jarvis", None),
    (4, "ptt_add_rms", "add buy milk to my personal list", "rms", "ptt", None, None),
    (5, "ht_salt_slt", "hey travis, can you pass the salt", "slt", "wake", "hey travis", None),
    (6, "ht_add_slt", "hey travis, add buy milk to my personal list", "slt", "wake", "hey travis", None),
    (7, "ht_next_slt", "hey travis, what is next", "slt", "wake", "hey travis", None),
    (8, "false_add_slt", "add buy milk to my personal list", "slt", "wake", None, 0.9),
    (9, "pink_noise_3s", None, None, "wake", None, 1.0),
]


def ff(args):
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", *args], check=True, timeout=60)


def flite(text, voice, path):
    ff(["-f", "lavfi", "-i", f"flite=text='{text}':voice={voice}", "-ar", str(RATE), "-ac", "1", "-y", path])


def pink(seconds, amp, seed, path):
    ff(["-f", "lavfi", "-i", f"anoisesrc=color=pink:amplitude={amp}:duration={seconds}:sample_rate={RATE}:seed={seed}",
        "-ac", "1", "-ar", str(RATE), "-y", path])


def oww_of(r):
    for _, m in r["msgs"]:
        c = m.get("check")
        if isinstance(c, dict) and c.get("oww") is not None:
            return c["oww"]
    return None


def wake_text_of(r):
    _, res = first(r["msgs"], "result")
    return (res or {}).get("check", {}).get("wake_text")


def no_speech(r) -> bool:
    return not any(m.get("type") == "tts_start" or (m.get("type") == "result" and m.get("say")) for _, m in r["msgs"])


def describe(r) -> str:
    _, res = first(r["msgs"], "result")
    if res:
        it = res.get("intent") or {}
        slots = ",".join(f"{k}={v}" for k, v in it.items() if k != "name" and v is not None)
        return (f'heard "{res.get("heard")}" -> {it.get("name")}{" (" + slots + ")" if slots else ""} ok={res.get("ok")} '
                f'dry={res.get("dry")} refused={res.get("refused")} say={json.dumps(res.get("say"))} card={json.dumps(res.get("card"))}')
    _, rej = first(r["msgs"], "reject")
    if rej:
        return f'reject {rej.get("why")} at stage {rej.get("stage")}' + (f' (would run {rej["would"]})' if rej.get("would") else "")
    return "no answer"


def expect(n, cfg, r):
    """(ok, why) for clip n against the V4 table."""
    _, res = first(r["msgs"], "result")
    _, rej = first(r["msgs"], "reject")
    t_ep, _ = first(r["msgs"], "endpoint")
    it = (res or {}).get("intent") or {}
    oww = oww_of(r)
    say = (res or {}).get("say") or ""
    if n == 1:
        ok = (res and it.get("name") == "task.add" and it.get("list") == "personal" and res.get("dry") is True
              and not res.get("refused") and say.startswith("Would add"))
        return ok, "task.add personal, dry, needs wake_text"
    if n == 2:
        if cfg.get("read_needs_wake_text") and not wake_text_of(r) and not res:
            ok = rej and rej.get("why") == "wake_check" and rej.get("would") == "theme" and no_speech(r)
            return ok, "strict reads (D11) and no jarvis-like token: silent reject, would have run theme"
        ok = res and it.get("name") == "theme" and it.get("value") == "dark" and {"what": "theme", "value": "dark"} in (res.get("do") or [])
        return ok, "theme dark with do theme"
    if n == 3:
        if cfg.get("allow_complete"):
            ok = res and it.get("name") == "task.complete" and (res.get("refused") == "wake_text" or say.startswith(("Would complete", "I couldn't find", "Which one")))
        else:
            ok = res and it.get("name") == "task.complete" and res.get("refused") in ("complete_off", "wake_text")
        return ok and not say.startswith("Done"), "task.complete matched, refused (complete_off or wake_text), no Done"
    if n == 4:
        ok = res and it.get("name") == "task.add" and it.get("list") == "personal" and res.get("dry") is True and say.startswith("Would add")
        return ok, "push-to-talk task.add personal, dry"
    if n == 5:
        ok = no_speech(r) and ((res and it.get("name") is None) or (rej and rej.get("why") in ("wake_check", "no_command")))
        return ok, "no intent, silent"
    if n == 6:
        if oww is not None and oww < 0.5:   # no phrase in the audio either: the false-trigger rule (silent)
            ok = rej and rej.get("why") == "wake_check" and no_speech(r)
            return ok, f"oww {oww} < 0.5: silent reject"
        ok = res and it.get("name") == "task.add" and res.get("refused") == "wake_text" and res.get("say") is None and res.get("card") == CARD and no_speech(r)
        return ok, "task.add matched, refused wake_text, card only, no speech"
    if n == 7:
        answer = oww is not None and oww >= 0.5 and not cfg.get("read_needs_wake_text")
        if answer or wake_text_of(r):
            ok = res and it.get("name") == "next.event" and res.get("ok") is True and bool(say)
            return ok, f"next.event answered (oww {oww})"
        ok = rej and rej.get("why") == "wake_check" and no_speech(r)
        return ok, f"silent reject (oww {oww}, read_needs_wake_text {cfg.get('read_needs_wake_text')})"
    if n == 8:
        if cfg.get("oww_reject", 0) > 0 and oww is not None and oww < cfg["oww_reject"]:
            ok = rej and rej.get("why") == "wake_check" and rej.get("stage") == "early" and t_ep is None
            return ok, f"early reject wake_check (oww {oww} < {cfg['oww_reject']})"
        ok = t_ep is not None and rej and rej.get("why") == "wake_check" and rej.get("would") == "task.add" and no_speech(r)
        return ok, f"silent reject, would have run task.add (oww {oww})"
    if n == 9:
        if cfg.get("oww_reject", 0) > 0 and oww is not None and oww < cfg["oww_reject"]:
            ok = rej and rej.get("why") == "wake_check" and rej.get("stage") == "early"
            return ok, f"early reject wake_check (oww {oww} < {cfg['oww_reject']})"
        ok = rej and rej.get("why") == "no_command" and t_ep is None
        return ok, f"reject no_command (oww {oww})"
    return False, "unknown case"


def latency(r, clip_end):
    """(ok, text, numbers): endpoint within 1.0 s and the answer within 2.0 s of the end of the clip (14d's
    reference); the strict figures from the last loud sample are reported alongside."""
    t_ep, _ = first(r["msgs"], "endpoint")
    if t_ep is None:
        t_rej, _ = first(r["msgs"], "reject")
        return True, (f"answered {t_rej:.2f} s after the wake instant" if t_rej is not None else "no answer"), {"answer_after_wake_s": t_rej}
    t_ans = next((t for t, m in r["msgs"] if m.get("type") in ("result", "reject") and t >= t_ep), None)
    ep, ep_strict = t_ep - clip_end, t_ep - r["speech_end"]
    if t_ans is None:
        return False, f"endpoint +{ep:.2f} s, no answer", {"endpoint_s": round(ep, 3)}
    ans, ans_strict = t_ans - clip_end, t_ans - r["speech_end"]
    ok = bool(ep <= EP_MAX_S and ans <= RES_MAX_S)
    nums = {"endpoint_s": round(ep, 3), "answer_s": round(ans, 3), "endpoint_strict_s": round(ep_strict, 3), "answer_strict_s": round(ans_strict, 3)}
    return ok, (f"endpoint +{ep:.2f} s, answer +{ans:.2f} s after the clip end "
                f"(+{ep_strict:.2f} s, +{ans_strict:.2f} s after the last loud sample)"), nums


async def run(args) -> int:
    from wsprobe import hello as probe_hello
    try:
        h = await probe_hello(args.url, client="selftest")
    except Exception as e:  # noqa: BLE001
        print(f"SETUP-FAIL: cannot reach {args.url}: {type(e).__name__}: {e}")
        return 2
    cfg = h.get("cfg") or {}
    print(f"box: build {h.get('build')}, stage {h.get('stage')}, dry {h.get('dry')}, stt {h.get('stt')}, "
          f"oww_reject {cfg.get('oww_reject')}, allow_complete {cfg.get('allow_complete')}, "
          f"read_needs_wake_text {cfg.get('read_needs_wake_text')}")
    if h.get("stage") != "pipeline" or not h.get("stt"):
        print("SETUP-FAIL: the box is not in the pipeline stage")
        return 2
    if h.get("dry") is not True:
        print("SETUP-FAIL: the box did not confirm dry run for this connection; refusing to run")
        return 2
    only = {int(x) for x in args.only.split(",")} if args.only else None
    results = []
    with tempfile.TemporaryDirectory(prefix="tvself-") as td:
        bed = None
        if args.noise_bed:
            pink(40, args.noise_bed, 11, os.path.join(td, "bed.wav"))
            bed = load_wav(os.path.join(td, "bed.wav"))
        for n, name, text, voice, by, phrase, wake_at in CASES:
            if only and n not in only:
                continue
            path = os.path.join(td, f"{name}.wav")
            if text is None:
                pink(3, 0.006, 1, path)            # 14d's documented level, fixed seed
            else:
                flite(text, voice, path)
            clip = load_wav(path)
            if phrase:
                pp = os.path.join(td, f"{name}.phrase.wav")
                flite(phrase, voice, pp)
                wake_at = round(speech_end_s(load_wav(pp)) + DETECT_S, 3)
            lead = 2.0
            clip_end = lead + len(clip) / RATE - (lead + (wake_at or 0.0 if by == "wake" else 0.0))
            r = await stream_session(args.url, clip, by=by, wake_at=wake_at or 0.0, lead=lead, dry=True, client="selftest", bed=bed)
            ok_out, rule = expect(n, cfg, r)
            ok_lat, lat, nums = latency(r, clip_end)
            retried = None
            if ok_out and not ok_lat:
                r2 = await stream_session(args.url, clip, by=by, wake_at=wake_at or 0.0, lead=lead, dry=True, client="selftest", bed=bed)
                ok_out2, _ = expect(n, cfg, r2)
                ok_lat2, lat2, nums2 = latency(r2, clip_end)
                retried = {"first": nums, "retry": nums2}
                lat = f"{lat}; retried: {lat2}"
                if ok_out2:
                    r, ok_lat, nums = r2, ok_lat2, nums2
            ok = bool(ok_out) and ok_lat
            oww = oww_of(r)
            wt = wake_text_of(r)
            line = (f"{'PASS' if ok else 'FAIL'} {n} {name} ({by}{', wake at %.2f s' % wake_at if by == 'wake' else ''}): "
                    f"{describe(r)} | oww {oww} wake_text {wt} | {lat}")
            if not ok_out:
                line += f" | expected: {rule}"
            if not ok_lat:
                line += f" | latency over {EP_MAX_S} s / {RES_MAX_S} s"
            print(line, flush=True)
            results.append({"n": n, "name": name, "ok": ok, "outcome_ok": bool(ok_out), "latency_ok": ok_lat, "rule": rule,
                            "oww": oww, "wake_text": wt, "speech_end": float(r["speech_end"]), "clip_end": float(clip_end),
                            "wake_at": float(wake_at) if wake_at is not None else None, "latency": nums, "retried": retried,
                            "msgs": [{"t": t, **m} for t, m in r["msgs"]]})
    passed = sum(1 for x in results if x["ok"])
    n_retry = sum(1 for x in results if x.get("retried"))
    print(f"PASS {passed}/{len(results)}" + (f" ({n_retry} clip{'s' if n_retry != 1 else ''} streamed twice for latency)" if n_retry else ""))
    if args.json:
        Path(args.json).write_text(json.dumps({"hello": h, "results": results}, indent=1))
    return 0 if passed == len(results) == (len(only) if only else len(CASES)) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="tablet-voice V4 selftest (dry run, 9 synthetic clips)")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--noise-bed", type=float, default=0.0, help="continuous pink noise amplitude, e.g. 0.006")
    ap.add_argument("--only", default="", help="comma-separated clip numbers")
    ap.add_argument("--json", default="", help="also write the full message log to this file")
    return asyncio.run(run(ap.parse_args()))


if __name__ == "__main__":
    sys.exit(main())
