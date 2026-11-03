# tablet-voice

Box side of the wall tablet's voice control. The dashboard page (Fully Kiosk on the Lenovo P11 Pro) runs the
"Hey Jarvis" microWakeWord stage and a push-to-talk pill; only after a detection or a tap does audio leave
the tablet, over `ws://localhost:8766/` (Termux socat forward) to this service on the box (:8766). Here it is
endpointed (Silero VAD, the model bundled with faster-whisper), the wake is re-checked (openWakeWord
`hey_jarvis` with numpy and onnxruntime, plus a jarvis-like token in the transcript), transcribed
(faster-whisper base.en int8, resident), matched against Tier 0 intents and answered. Audio stays in RAM for
one session and is never written. Listening happens only while the tablet screen is lit; the page enforces
that and this service refuses wakes from a page that says it is dark.

Design and rollout: `~/personal/tablet-upgrade/research_notes/Lenovo P11 Pro kiosk upgrade/14_voice_build_spec.md`
(steps V3 and V4 are this folder; protocol in its section 5) and `14d_box_voice_service.md`. Build report:
`15a_box_impl_report.md` in the same folder.

## Files

- `server.py`: config, access control, `/health`, `/stats`, protocol v1, sessions, decision table, logging
- `audio.py` (StreamVAD, openWakeWord check), `stt.py` (Whisper, junk gate), `intents.py` (Tier 0 matcher),
  `actions.py` (dashboard calls and reply text), `fully.py` (optional Fully REST speech, inert without FULLY_PW)
- `wsprobe.py` (hello probe, play a WAV as a session), `selftest.py` (the 9 V4 clips), `setup_models.sh`
- `mic_audit.sh`: the lit-rule audit that does not trust the page (spec 14 section 0 item 12, V7), run every
  10 minutes by `~/systems/systemd/tablet-voice-micaudit.{service,timer}`; adb only, no Fully password
- `tests/`: `test_intents.py`, `test_actions.py` (no network), `test_server.py` + `harness.py` +
  `fake_dash.py` (integration on test ports only), `test_mic_audit.py` + `fake_adb.sh` (the audit, no device),
  `proto/`: the 14d prototype, kept for reference
- `models/` (gitignored): the three openWakeWord v0.5.1 ONNX files; `logs/` (gitignored): `sessions-YYYY-MM-DD.jsonl`, 30 days

## What is logged where

- `logs/sessions-YYYY-MM-DD.jsonl` (30 days, pruned at start and at midnight): every event as one strict-JSON,
  ASCII-only line. Session lines carry the transcript (`heard`, `text`), the intent with its slots and the
  reply (`say`) only for turns addressed to the box: a tap, a transcript with the name, or a turn that ran,
  refused or spoke. A wake with no name and nothing run (silent reject, junk, silent result) keeps only
  `heard_len`, `transcript: "not_kept"`, the scores and the intent name. Replies built from calendar or task
  data are logged by length only.
- stdout, which systemd keeps in the persistent user journal (months on this box): a redacted copy of every
  line. Session lines lose `heard`, `text`, `say` and the slots (`intent` is the name only, `heard_len` is
  added); stats lines lose the room loudness percentiles (`rms*`). Never PCM, never a password.
- Lines anyone who reaches the port can cause (refusals, the websockets library's handshake errors, bad hellos,
  over-cap wakes, stray `end`s, handler errors) pass at most 5 a minute per peer and 60 a minute in all; the rest
  are counted in one `suppressed` line per minute.
- Transcripts, so: `grep '"sid": "<sid>"' logs/sessions-$(date +%F).jsonl`, not `journalctl`.

## Environment (the unit sets these; unset values fall back to the safe side)

| Variable | Unit | Code default | Meaning |
|---|---|---|---|
| VOICE_HOST / VOICE_PORT | 0.0.0.0 / 8766 | same | bind address; peers allowed: 127.0.0.1, `~/systems/.state/tablet-ip`, 192.168.1.89 |
| VOICE_STAGE | skeleton (V3), pipeline (V4) | skeleton | skeleton answers hello/state/health only; wakes get `reject{not_ready}` |
| VOICE_DRY_RUN | 1 | 1 | 1 = no task writes and no Fully REST; reads (GET /api/data) stay live |
| VOICE_TTS_VIA | auto | auto | auto = page speech when the hello says `fully` and `tts:"page"`, else REST if FULLY_PW, else card only |
| VOICE_OWW_REJECT | 0 | 0 | early reject below this openWakeWord score; 0 = shadow mode (score logged only) |
| VOICE_REQUIRE_FULLY_FOR_WAKE | 1 | 1 | wake sessions need a page with a reliable lit signal (`reject{no_lit_signal}`) |
| VOICE_ALLOW_COMPLETE | 0 | 0 | D6: task completion by voice |
| VOICE_READ_NEEDS_WAKE_TEXT | 0 | 0 | D11: reads after a wake need "jarvis" in the transcript |
| VOICE_DASH | http://127.0.0.1:8765 | same | tablet-dash base URL |
| VOICE_STT_THREADS | 4 | 4 | CTranslate2 threads |

Test-only overrides (never in the unit): VOICE_LOG_DIR, VOICE_MODELS, VOICE_TABLET_IP_FILE,
VOICE_EXIT_ON_STDIN_EOF, VOICE_FULLY_URL, VOICE_TUNE (a JSON object of `TUNE` numbers). A browser `hello` may ask
for `dry:true`; only 127.0.0.1 is honoured.

Limits in code (`TUNE` in server.py): reads get one 5 s budget from the wake (a prefetch that failed fast is retried
once inside it, never after a timeout; one `GET /api/data` in flight at a time); writes time out after 7 s, and a
write that went out without an answer is reported as "I'm not sure that went through. Check the list." (logged
`post: "unknown"`), never as a failure; a turn has 20 s from its endpoint, then it is released with an error
result; live audio may run at most 1.5 s ahead of real time (`reject{too_fast}`); 12 wakes a minute per tablet
peer (40 for 127.0.0.1), beyond that `reject{busy, limit: "rate"}`; a `state` with `lit:false` or `mic:false`
drops a turn that is still streaming (`why` dark or mic_off, `by_state: true`); a replaced socket's streaming turn ends and its
mic interval closes at once, and a dead socket's close handshake waits 2 s. openWakeWord runs on its own thread.
`/health` also reports `session_age_s`, `session_state` and `stt_busy_s` (`ok` turns false when one STT call has
run for more than 60 s).

## Setup

```bash
cd ~/systems/tablet-voice
uv venv --python /usr/bin/python3.13 .venv && uv pip install --python .venv/bin/python -r requirements.txt
bash setup_models.sh          # verifies (or fetches) the ONNX files by sha256 and checks the base.en HF cache
```

## Verify

```bash
systemctl --user is-active tablet-voice.service
curl -s localhost:8766/health                       # "stage", "dry_run", "tablet_connected", "last_hello", "loaded"
curl -s localhost:8766/stats                        # today: mic_open_s, lit_periods, wakes, ptt_turns, runs, rejects
.venv/bin/python wsprobe.py hello                   # one JSON line, "type": "hello", "v": 1
.venv/bin/python wsprobe.py hello --origin http://evil.example     # HTTP 403
.venv/bin/python selftest.py                        # PASS 9/9 (pipeline stage; always dry)
.venv/bin/python tests/test_intents.py && .venv/bin/python tests/test_actions.py
```

Offline integration (test ports only, never 8765 or 8766, bounded):
`timeout 3600 .venv/bin/python tests/test_server.py --out <dir>` (host 127.0.0.2 unless TV_TEST_HOST is set).
The mic audit, with a stub adb and no device: `timeout 600 .venv/bin/python tests/test_mic_audit.py --out <dir>`;
its alert paths on the box, with the real adb read-only and nothing posted:
`DRY_RUN=1 FAKE_TOP=screensaver FAKE_REC=1 ~/systems/tablet-voice/mic_audit.sh` and
`DRY_RUN=1 FAKE_WV=0.0 ~/systems/tablet-voice/mic_audit.sh` (both print `DRY_RUN alert:`).

## Mic audit (V7)

`mic_audit.sh` prints one JSON line per run to the journal of `tablet-voice-micaudit.service`:
`{"ts", "top", "act", "awake", "fully_recording", "night", "wv", "fully_v", "sock", "nosock_run", "verdict", "transient"}`.
`verdict` is `ok`, `VIOLATION` (Fully recording while the resumed activity is not FullyActivity or the display is
not awake, confirmed by a second read 3 s later), `night_rec` (recording 22:00 to 08:00, allowed after a touch),
`read_error` or `adb_down`. Alerts (Discord #ops-log through `lib/tg-notify.sh`, once per key in
`~/systems/.state/tablet-voice-micaudit-last`): a violation (once a day), a WebView or Fully version change
(versions in `~/systems/.state/tablet-voice-versions`, read hourly; the cue to re-run the V14 regression), no
tablet socket on three lit daytime runs in a row while `flags.json` has `enabled` and `ws`, an unreadable
recorder section (once a day). adb down is logged, not alerted. Install only these two units, never through
`systemd/install.sh`: `install -m 644 ~/systems/systemd/tablet-voice-micaudit.{service,timer} ~/.config/systemd/user/`
then `systemctl --user daemon-reload && systemctl --user enable --now tablet-voice-micaudit.timer`.
