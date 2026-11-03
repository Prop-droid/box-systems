#!/usr/bin/env python3
"""tablet-voice: box side of the wall tablet's voice control, WebSocket protocol v1 (default port 8766).

Spec: ~/personal/tablet-upgrade/research_notes/Lenovo P11 Pro kiosk upgrade/14_voice_build_spec.md (V3, V4,
section 5) and 14d_box_voice_service.md. The dashboard page runs the microWakeWord stage; after a wake or a
push-to-talk tap it streams Int16LE mono 16 kHz audio here. This process endpoints it (Silero VAD), re-checks
the wake (openWakeWord score plus a jarvis-like token in the transcript), transcribes it (faster-whisper
base.en int8), matches Tier 0 intents, runs them against the dashboard (dry run: GET /api/data only) and
answers with a result and, when the page asked for speech, a tts_start. Audio lives in RAM for one session
and is never written anywhere. Transcripts, task titles and reply text go only to the 30-day
logs/sessions-YYYY-MM-DD.jsonl (and only for turns addressed to the box); stdout, which systemd keeps in the
persistent journal, gets a redacted copy of every line. Config: environment variables, see README.md.
"""
from __future__ import annotations

import asyncio
import collections
import datetime as dt
import functools
import http
import json
import logging
import math
import os
import re
import signal
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed
from websockets.protocol import State

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import actions  # noqa: E402
import fully  # noqa: E402
from intents import READ_INTENTS, WRITE_INTENTS, match, strip_wake  # noqa: E402

BUILD = "2026-11-02.2"
RATE = 16000
ALLOWED_ORIGIN = "http://localhost:8765"
LOOPBACK = "127.0.0.1"
FIXED_TABLET_IP = "192.168.1.89"
CARD_WAKE_TEXT = 'Didn\'t catch "Jarvis". Tap the mic to add tasks.'

np = None      # numpy, audio and stt are imported only in the pipeline stage (the skeleton stays small)
audio = None
stt = None


# ---------------------------------------------------------------- config

def _env(name, default=None):
    v = os.environ.get(name)
    return default if v is None or not v.strip() else v.strip()


def _flag(name, default: bool) -> bool:
    v = _env(name)
    if v is None:
        return default
    if v.lower() in ("1", "true", "yes", "on"):
        return True
    if v.lower() in ("0", "false", "no", "off"):
        return False
    raise SystemExit(f"tablet-voice: bad {name}={v!r} (use 0 or 1)")


def _number(name, default, lo, hi):
    v = _env(name)
    if v is None:
        return default
    try:
        x = float(v)
    except ValueError:
        raise SystemExit(f"tablet-voice: bad {name}={v!r} (not a number)") from None
    if not lo <= x <= hi:
        raise SystemExit(f"tablet-voice: {name}={x} outside {lo}..{hi}")
    return x


class Cfg:
    def __init__(self):
        self.host = _env("VOICE_HOST", "0.0.0.0")
        self.port = int(_number("VOICE_PORT", 8766, 1, 65535))
        self.stage = (_env("VOICE_STAGE", "skeleton") or "").lower()          # skeleton | pipeline
        if self.stage not in ("skeleton", "pipeline"):
            raise SystemExit(f"tablet-voice: bad VOICE_STAGE={self.stage!r} (skeleton or pipeline)")
        self.dry_run = _flag("VOICE_DRY_RUN", True)                          # writes need an explicit 0
        self.tts_via = (_env("VOICE_TTS_VIA", "auto") or "").lower()         # auto | page | rest | off
        if self.tts_via not in ("auto", "page", "rest", "off"):
            raise SystemExit(f"tablet-voice: bad VOICE_TTS_VIA={self.tts_via!r} (auto, page, rest or off)")
        self.oww_reject = _number("VOICE_OWW_REJECT", 0.0, 0.0, 1.0)        # 0 = shadow: log the score only
        self.require_fully_for_wake = _flag("VOICE_REQUIRE_FULLY_FOR_WAKE", True)
        self.allow_complete = _flag("VOICE_ALLOW_COMPLETE", False)          # D6: 0 when unset
        self.read_needs_wake_text = _flag("VOICE_READ_NEEDS_WAKE_TEXT", False)  # D11: 0 when unset
        self.dash = (_env("VOICE_DASH", "http://127.0.0.1:8765") or "").rstrip("/")
        self.stt_threads = int(_number("VOICE_STT_THREADS", 4, 1, 16))
        # test overrides (unset in the unit): log folder, model folder, tablet-ip file, stop on stdin EOF
        self.log_dir = Path(_env("VOICE_LOG_DIR", str(HERE / "logs")))
        self.models_dir = Path(_env("VOICE_MODELS", str(HERE / "models")))
        self.tablet_ip_file = Path(_env("VOICE_TABLET_IP_FILE", str(Path.home() / "systems/.state/tablet-ip")))
        self.exit_on_stdin_eof = _flag("VOICE_EXIT_ON_STDIN_EOF", False)

    def public(self) -> dict:
        return {"host": self.host, "port": self.port, "stage": self.stage, "dry_run": self.dry_run,
                "tts_via": self.tts_via, "oww_reject": self.oww_reject,
                "require_fully_for_wake": self.require_fully_for_wake, "allow_complete": self.allow_complete,
                "read_needs_wake_text": self.read_needs_wake_text, "dash": self.dash, "stt_threads": self.stt_threads,
                "fully_rest": fully.available()}


CFG = Cfg()

# Session tuning, 14d section 4 start values.
TUNE = {
    "vad_on": 0.50, "vad_off": 0.35, "onset_ms": 96, "end_sil_ms": 800, "min_speech_ms": 250,
    "wait_wake_ms": 4000, "wait_ptt_ms": 5000, "max_cmd_ms": 8000, "max_session_ms": 15000,
    "max_preroll_ms": 3200, "oww_extra_ms": 640, "oww_ok": 0.5, "tts_extra_ms": 3000,
    "hello_timeout_s": 10, "stall_grace_ms": 3000, "max_conns": 3,
    # hardening (15a Fix round): read budget from the wake, overall turn budget, real-time pacing, wake rate
    # caps per peer (box-local tools get more room: the selftest streams up to 18 sessions a minute), close
    # timeout for replaced or dead sockets, a stuck-STT bound for /health
    "read_budget_ms": 5000, "process_budget_ms": 20000, "pace_ahead_ms": 1500,
    "max_wakes_per_min": 12, "max_wakes_per_min_local": 40, "close_timeout_s": 2, "stt_stuck_s": 60,
}


_tune_env = _env("VOICE_TUNE")       # tests only, never in the unit: a JSON object of numeric TUNE values
if _tune_env:
    try:
        _over = json.loads(_tune_env)
    except ValueError:
        _over = None
    if not isinstance(_over, dict) or not all(
            k in TUNE and isinstance(v, (int, float)) and not isinstance(v, bool) for k, v in _over.items()):
        raise SystemExit("tablet-voice: bad VOICE_TUNE (a JSON object of known numeric TUNE keys)")
    TUNE.update(_over)


def _n(ms) -> int:
    return int(round(ms * RATE / 1000))


ONSET_N, END_SIL_N, MIN_SPEECH_N = _n(TUNE["onset_ms"]), _n(TUNE["end_sil_ms"]), _n(TUNE["min_speech_ms"])
WAIT_WAKE_N, WAIT_PTT_N = _n(TUNE["wait_wake_ms"]), _n(TUNE["wait_ptt_ms"])
MAX_CMD_N, MAX_SESSION_N = _n(TUNE["max_cmd_ms"]), _n(TUNE["max_session_ms"])
MAX_PRE_N, OWW_EXTRA_N = _n(TUNE["max_preroll_ms"]), _n(TUNE["oww_extra_ms"])
VAD_CHUNK = 512


def hello_cfg() -> dict:
    return {"end_sil_ms": TUNE["end_sil_ms"], "no_speech_ms": TUNE["wait_wake_ms"], "no_speech_ptt_ms": TUNE["wait_ptt_ms"],
            "min_speech_ms": TUNE["min_speech_ms"], "max_cmd_ms": TUNE["max_cmd_ms"],
            "max_session_ms": TUNE["max_session_ms"], "max_preroll_ms": TUNE["max_preroll_ms"],
            "oww_window_ms": TUNE["oww_extra_ms"], "oww_reject": CFG.oww_reject, "oww_ok": TUNE["oww_ok"],
            "allow_complete": CFG.allow_complete, "read_needs_wake_text": CFG.read_needs_wake_text,
            "require_fully_for_wake": CFG.require_fully_for_wake, "tts_via": CFG.tts_via,
            "tts_extra_ms": TUNE["tts_extra_ms"]}


def _short(v, n=120):
    if v is None:
        return None
    s = str(v)
    return s if len(s) <= n else s[:n] + "..."


def _num(v):
    """A finite number from the page, else None (NaN, Infinity and 1e999 never reach the log or the ledger)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return v if math.isfinite(v) else None


def _bad_constant(name):
    raise ValueError(f"non-finite JSON constant {name}")


def _loads(raw):
    """Parse one page message; None for anything that is not strict JSON (NaN and Infinity tokens included)
    or nests too deeply. A bad message is counted, never fatal for the connection."""
    try:
        return json.loads(raw, parse_constant=_bad_constant)
    except (ValueError, RecursionError, TypeError):
        return None


def _finite(o):
    """Non-finite floats to None, recursively (the fallback of _dumps)."""
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if isinstance(o, dict):
        return {k: _finite(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_finite(v) for v in o]
    return o


def _dumps(obj) -> str:
    """One strict-JSON line, ASCII only: no NaN or Infinity (jq and other strict readers reject them) and no raw
    U+2028, U+2029 or U+0085 (str.splitlines() cuts a line there; the file is read back by line)."""
    try:
        return json.dumps(obj, ensure_ascii=True, allow_nan=False, default=str)
    except ValueError:
        return json.dumps(_finite(obj), ensure_ascii=True, allow_nan=False, default=str)


def _rss_mb() -> dict:
    out = {}
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith(("VmRSS:", "VmHWM:")):
                out[line.split(":")[0].lower()] = round(int(line.split()[1]) / 1024, 1)
    except OSError:
        pass
    return out


# ---------------------------------------------------------------- logging and the ledger

JOURNAL_DROP = ("heard", "text", "say")


def journal_view(ev: dict) -> dict:
    """The copy of a log line that goes to stdout, which systemd keeps in the persistent user journal (no
    MaxRetentionSec on this box: months of history). No transcript, no task title or other intent slot, no
    reply text and no room loudness profile; the session line keeps heard_len, wake_text, the intent name,
    the outcome, the scores and the timings. The full line goes only to logs/ (30 days)."""
    kind = ev.get("ev")
    if kind == "session":
        out = {k: v for k, v in ev.items() if k not in JOURNAL_DROP}
        if isinstance(ev.get("heard"), str):
            out["heard_len"] = len(ev["heard"])
        if isinstance(ev.get("intent"), dict):
            out["intent"] = ev["intent"].get("name")
        return out
    if kind == "stats" and isinstance(ev.get("page"), dict):
        return {**ev, "page": {k: v for k, v in ev["page"].items() if not str(k).startswith("rms")}}
    return ev


class EventLog:
    """One JSON line per event to logs/sessions-YYYY-MM-DD.jsonl (30-day prune at start and at each rollover)
    and a redacted copy (journal_view) to stdout. Strict JSON, ASCII only. Never PCM, never a password."""
    KEEP_DAYS = 30

    def __init__(self, folder: Path):
        self.dir = folder
        self.dir.mkdir(parents=True, exist_ok=True)
        self.pruned = self.prune()

    def path_for(self, day: dt.date) -> Path:
        return self.dir / f"sessions-{day.isoformat()}.jsonl"

    def prune(self) -> int:
        cutoff = dt.date.today() - dt.timedelta(days=self.KEEP_DAYS)
        n = 0
        for p in self.dir.glob("sessions-*.jsonl"):
            m = re.fullmatch(r"sessions-(\d{4}-\d{2}-\d{2})\.jsonl", p.name)
            try:
                if m and dt.date.fromisoformat(m.group(1)) < cutoff:
                    p.unlink()
                    n += 1
            except (OSError, ValueError):
                pass
        return n

    def write(self, ev: dict) -> None:
        now = dt.datetime.now().astimezone()
        rec = {"ts": now.isoformat(timespec="milliseconds"), **ev}
        try:
            with open(self.path_for(now.date()), "a", encoding="utf-8") as f:
                f.write(_dumps(rec) + "\n")
        except OSError:
            pass
        try:
            sys.stdout.write(_dumps(journal_view(rec)) + "\n")
            sys.stdout.flush()
        except (OSError, ValueError):
            pass


class LogGate:
    """Line budget for the log lines that anyone who reaches the port can cause (refusals, the websockets
    library's own handshake errors) and that a looping client can cause (bad hellos, over-cap wakes, stray
    ends, handler errors): per (kind, peer) the first `burst` lines of each window pass, at most `total` pass
    per window over all keys, and the rest are only counted and summed up in one "suppressed" line when the
    window ends. That bounds the log volume and this object's memory."""

    def __init__(self, burst=5, total=60, window_s=60.0, max_keys=256):
        self.burst, self.total, self.window_s, self.max_keys = burst, total, window_s, max_keys
        self.t0 = None
        self.passed = collections.Counter()
        self.dropped = collections.Counter()
        self.n_passed = 0

    def roll(self, now=None):
        """Close the window once it is over, with one "suppressed" line if anything was held back."""
        now = time.monotonic() if now is None else now
        if self.t0 is None or now - self.t0 < self.window_s:
            return
        if self.dropped:
            top = [{"kind": k, "peer": p, "n": n} for (k, p), n in self.dropped.most_common(5)]
            LOG.write({"ev": "suppressed", "window_s": int(self.window_s), "n": sum(self.dropped.values()),
                       "keys": len(self.dropped), "top": top})
        self.t0, self.n_passed = None, 0
        self.passed.clear()
        self.dropped.clear()

    def allow(self, kind, peer) -> bool:
        now = time.monotonic()
        self.roll(now)
        if self.t0 is None:
            self.t0 = now
        key = (kind, str(peer))
        if self.passed[key] >= self.burst or self.n_passed >= self.total:
            if key not in self.dropped and len(self.dropped) >= self.max_keys:
                key = (kind, "other")
            self.dropped[key] += 1
            return False
        self.passed[key] += 1
        self.n_passed += 1
        return True


class Ledger:
    """Today's numbers for /stats and the daily line: mic-open seconds and lit periods (from the page's state
    messages and socket lifetimes, 14d 9.5), wakes, PTT turns, runs, rejects by reason, STT p50. Only the
    tablet counts (any allowed peer but 127.0.0.1): box-local tools (selftest, wsprobe) are counted apart in
    local_sessions, so a regression run never inflates the audit numbers. STT p50 covers every session."""

    def __init__(self):
        self.day = dt.date.today()
        self.reset()

    def reset(self):
        self.mic_s = 0.0
        self.lit_periods = 0
        self.sessions = self.wakes = self.ptt = self.runs = 0
        self.rejects = collections.Counter()
        self.refused = collections.Counter()
        self.outcomes = collections.Counter()
        self.stt_ms = []
        self.local_sessions = 0

    def add_session(self, rec: dict):
        if _num(rec.get("stt_ms")) is not None:
            self.stt_ms.append(rec["stt_ms"])
        if rec.get("peer") == LOOPBACK:
            self.local_sessions += 1
            return
        self.sessions += 1
        if rec.get("by") == "ptt":
            self.ptt += 1
        else:
            self.wakes += 1
        out = rec.get("outcome")
        self.outcomes[str(out)] += 1
        if out == "run":
            self.runs += 1
        elif out == "reject":
            self.rejects[str(rec.get("why"))] += 1
        if rec.get("refused"):
            self.refused[str(rec["refused"])] += 1

    REPLAY_KEYS = ('"ev": "session"', '"mic_closed_s"', '"lit_rise"')

    def replay(self, path: Path) -> int:
        """Rebuild today's numbers from today's log after a restart. Streams the file (a large file never sits
        in memory), splits on newline only, and parses only the lines that can carry ledger data."""
        try:
            f = open(path, encoding="utf-8", errors="replace", newline="\n")
        except OSError:
            return 0
        n = 0
        with f:
            for ln in f:
                if not any(k in ln for k in self.REPLAY_KEYS):
                    continue
                r = _loads(ln)
                if not isinstance(r, dict):
                    continue
                if r.get("ev") == "session":
                    self.add_session(r)
                    n += 1
                if _num(r.get("mic_closed_s")) is not None:
                    self.mic_s += r["mic_closed_s"]
                if r.get("lit_rise") is True or (_num(r.get("lit_rise")) is not None and r["lit_rise"] > 0):
                    self.lit_periods += int(r["lit_rise"])
        return n

    def snapshot(self, open_mic_s=0.0) -> dict:
        st = sorted(self.stt_ms)
        return {"day": self.day.isoformat(), "mic_open_s": round(self.mic_s + open_mic_s, 1),
                "lit_periods": self.lit_periods, "sessions": self.sessions, "wakes": self.wakes, "ptt_turns": self.ptt,
                "runs": self.runs, "rejects": dict(self.rejects), "refused": dict(self.refused),
                "outcomes": dict(self.outcomes), "stt_p50_ms": st[len(st) // 2] if st else None, "stt_n": len(st),
                "local_sessions": self.local_sessions}


LOG: EventLog = None      # set in main()
LEDGER = Ledger()
GATE = LogGate()


# ---------------------------------------------------------------- connections, sessions, hub

class Conn:
    _ids = 0

    def __init__(self, ws):
        Conn._ids += 1
        self.id = Conn._ids
        self.ws = ws
        self.peer = _peer(ws.remote_address)
        self.origin = ws.request.headers.get("Origin") if ws.request else None
        self.t0 = time.monotonic()
        self.said_hello = False
        self.client = ""
        self.lit = None          # None = unknown; set by hello.lit and state.lit
        self.mic = None
        self.fully = False
        self.tts = "off"         # "page" only when the hello says so
        self.dry = CFG.dry_run
        self.session = None
        self.mic_since = None    # wall time when the page reported mic on
        self.dropped_msgs = self.dropped_bytes = self.bad = 0
        self.closing = False     # replaced by a newer socket: everything it still sends is ignored

    def is_open(self) -> bool:
        return self.ws.state is State.OPEN

    async def send(self, obj) -> bool:
        try:
            await self.ws.send(json.dumps(obj))
            return True
        except ConnectionClosed:
            return False

    def mic_update(self, mic, now):
        """Track the mic-open interval; returns the seconds just closed (for the log line), else None."""
        if mic is True and self.mic_since is None:
            self.mic_since = now
            return None
        if mic is not True and self.mic_since is not None:
            closed = max(0.0, now - self.mic_since)
            self.mic_since = None
            if self.peer != LOOPBACK:
                LEDGER.mic_s += closed
            return round(closed, 2)
        return None


class Session:
    """One wake or push-to-talk turn. States: streaming -> processing -> done (or streaming -> done)."""

    def __init__(self, conn: Conn, m: dict, sid: str, by: str):
        self.conn, self.sid, self.by = conn, sid, by
        self.page_score = _num(m.get("score"))
        self.page_t_ms = _num(m.get("t_ms"))
        declared = m.get("preroll_samples")
        declared = declared if isinstance(declared, int) and not isinstance(declared, bool) and declared > 0 else 0
        self.declared_pre = declared
        self.skip = max(0, declared - MAX_PRE_N)     # a longer pre-roll keeps its newest 3.2 s
        self.pre = min(declared, MAX_PRE_N)
        self.wait_n = WAIT_PTT_N if by == "ptt" else WAIT_WAKE_N
        self.buf, self.n = [], 0
        self.vad = audio.StreamVAD()
        self.vad_n = 0
        self.onset = None
        self.run = self.sil = 0
        self.ep_live_n = None
        self.state = "streaming"
        self.dry = conn.dry
        self.oww = self.oww_ms = None
        self.oww_task = self.prefetch = self.watchdog = None
        self.endpoint_why = None
        self.t_open = time.monotonic()
        self.read_deadline = self.t_open + TUNE["read_budget_ms"] / 1000   # one read budget from the wake
        self.write_started = False
        self.logged = False

    def audio(self):
        return np.concatenate(self.buf) if self.buf else np.zeros(0, np.int16)

    def feed(self, pcm):
        """Feed Int16 samples; returns None, "silence", "maxlen" or "no_command" (VAD endpointing, 14d 4)."""
        if self.skip:
            k = min(self.skip, len(pcm))
            pcm, self.skip = pcm[k:], self.skip - k
            if not len(pcm):
                return None
        self.buf.append(pcm)
        self.n += len(pcm)
        for p in self.vad.feed(pcm.astype(np.float32) / 32768.0):
            self.vad_n += VAD_CHUNK
            live = self.vad_n - self.pre               # samples after the wake instant (end of the pre-roll)
            if self.by == "wake" and live <= 0:
                continue                               # the pre-roll only warms the VAD state
            if self.onset is None:
                if p >= TUNE["vad_on"]:
                    self.run += VAD_CHUNK
                    if self.run >= ONSET_N:
                        self.onset, self.sil = self.vad_n - self.run, 0
                else:
                    self.run = 0
                if self.onset is None and live >= self.wait_n:
                    return "no_command"
            else:
                self.sil = self.sil + VAD_CHUNK if p < TUNE["vad_off"] else 0
                if self.sil >= END_SIL_N:
                    if (self.vad_n - self.sil) - self.onset < MIN_SPEECH_N:   # a blip, not a command
                        if live < self.wait_n:
                            self.onset, self.run, self.sil = None, 0, 0
                            continue
                        return "no_command"
                    self.ep_live_n = live
                    return "silence"
                if self.vad_n - self.onset >= MAX_CMD_N:
                    self.ep_live_n = live
                    return "maxlen"
            if live >= MAX_SESSION_N:
                self.ep_live_n = live
                return "maxlen" if self.onset is not None else "no_command"
        return None

    def log_base(self) -> dict:
        return {"ev": "session", "sid": self.sid, "conn": self.conn.id, "peer": self.conn.peer, "by": self.by,
                "page_score": self.page_score, "oww": round(self.oww, 4) if self.oww is not None else None,
                "oww_ms": self.oww_ms, "preroll_s": round(self.pre / RATE, 2), "audio_s": round(self.n / RATE, 2),
                "onset_s": round((self.onset - self.pre) / RATE, 2) if self.onset is not None else None,
                "endpoint": self.endpoint_why,
                "endpoint_s": round(self.ep_live_n / RATE, 2) if self.ep_live_n is not None else None,
                "dry_run": self.dry}


class Hub:
    def __init__(self):
        self.conns: dict[int, Conn] = {}
        self.by_key: dict[tuple, Conn] = {}
        self.active: Session | None = None      # one session at a time: one tablet, one microphone
        self.tts: dict[str, dict] = {}          # peer -> {"until", "sid", "id"}: the box TTS window (14d 5c)
        self.last_hello = None                  # the last hello from the tablet (not from 127.0.0.1)
        self.ready = False
        self.stt_name = None
        self.load_info = {}
        self.t0 = time.monotonic()
        self.tts_seq = 0
        self.wakes_by_peer: dict[str, collections.deque] = {}   # allowed peers only, so at most a few keys
        self.prefetch = None                    # the GET /api/data in flight, shared while it runs
        self.stt_since = None                   # monotonic start of the STT call in progress

    def wake_rate_ok(self, peer, now) -> bool:
        """At most max_wakes_per_min wake messages per peer in any 60 s (box-local tools: the _local cap)."""
        cap = TUNE["max_wakes_per_min_local"] if peer == LOOPBACK else TUNE["max_wakes_per_min"]
        q = self.wakes_by_peer.setdefault(peer, collections.deque())
        while q and now - q[0] >= 60:
            q.popleft()
        if len(q) >= cap:
            return False
        q.append(now)
        return True

    def get_prefetch(self, loop):
        """One GET /api/data at a time: a wake while one is in flight shares it (a hung dashboard cannot pile
        up blocked worker threads), and it is bounded by the read budget."""
        f = self.prefetch
        if f is None or f.done():
            f = self.prefetch = loop.run_in_executor(IO_POOL, actions.fetch_data, CFG.dash,
                                                     TUNE["read_budget_ms"] / 1000)
        return f

    def tablet_connected(self) -> bool:
        return any(c.said_hello and c.peer != LOOPBACK and c.is_open() for c in self.conns.values())

    def tts_open(self, peer) -> bool:
        w = self.tts.get(peer)
        if w and w["until"] > time.monotonic():
            return True
        self.tts.pop(peer, None)
        return False

    def open_mic_s(self, now) -> float:
        return sum(now - c.mic_since for c in self.conns.values() if c.mic_since is not None and c.peer != LOOPBACK)


HUB = Hub()
_BG = set()                                                                # strong refs to fire-and-forget tasks


def _bg(coro):
    task = asyncio.get_running_loop().create_task(coro)
    _BG.add(task)
    task.add_done_callback(_BG.discard)
    return task


class _WsLogHandler(logging.Handler):
    """websockets' own warnings and errors (malformed requests, scanners) as one compact JSON line, no traceback,
    through the line budget per peer (any host that reaches the port can cause them)."""

    def emit(self, record):
        try:
            peer = "?"
            ws = getattr(record, "websocket", None)          # websockets' LoggerAdapter extra
            if ws is not None:
                try:
                    peer = _peer(ws.remote_address)
                except Exception:  # noqa: BLE001
                    pass
            if not GATE.allow("ws_log", peer):
                return
            exc = type(record.exc_info[1]).__name__ if record.exc_info and record.exc_info[1] else None
            LOG.write({"ev": "ws_log", "level": record.levelname.lower(), "msg": _short(record.getMessage(), 120),
                       "exc": exc, "peer": peer})
        except Exception:  # noqa: BLE001
            pass


STT_POOL = ThreadPoolExecutor(max_workers=1, thread_name_prefix="stt")     # one STT at a time
OWW_POOL = ThreadPoolExecutor(max_workers=1, thread_name_prefix="oww")     # openWakeWord check, never behind HTTP
IO_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="io")       # dashboard and Fully HTTP


def _peer(addr) -> str:
    try:
        ip = addr[0]
    except (TypeError, IndexError):
        return "?"
    ip = str(ip)
    return ip[7:] if ip.startswith("::ffff:") else ip


_ip_cache = {"mtime": None, "ip": None}


def _state_ip():
    try:
        mtime = CFG.tablet_ip_file.stat().st_mtime
    except OSError:
        return None
    if mtime != _ip_cache["mtime"]:
        try:
            txt = CFG.tablet_ip_file.read_text().strip()
        except OSError:
            txt = ""
        _ip_cache.update(mtime=mtime, ip=txt if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", txt) else None)
    return _ip_cache["ip"]


def allowed_peer(ip) -> bool:
    """127.0.0.1, the address in ~/systems/.state/tablet-ip and 192.168.1.89; nothing else (tailnet, LAN)."""
    return ip == LOOPBACK or ip == FIXED_TABLET_IP or (ip is not None and ip == _state_ip())


# ---------------------------------------------------------------- HTTP side: access, /health, /stats

def health() -> dict:
    now = time.monotonic()
    act, since = HUB.active, HUB.stt_since
    stt_busy = round(now - since, 1) if since is not None else None
    return {"ok": not (stt_busy is not None and stt_busy > TUNE["stt_stuck_s"]), "v": 1, "stage": CFG.stage,
            "dry_run": CFG.dry_run, "tablet_connected": HUB.tablet_connected(),
            "last_hello": HUB.last_hello, "stt": HUB.stt_name, "loaded": HUB.ready, "build": BUILD,
            "uptime_s": round(now - HUB.t0), "conns": len(HUB.conns),
            "session_active": act is not None,
            "session_age_s": round(now - act.t_open, 1) if act is not None else None,
            "session_state": act.state if act is not None else None, "stt_busy_s": stt_busy,
            "cfg": {"oww_reject": CFG.oww_reject, "allow_complete": CFG.allow_complete,
                    "read_needs_wake_text": CFG.read_needs_wake_text,
                    "require_fully_for_wake": CFG.require_fully_for_wake, "tts_via": CFG.tts_via,
                    "fully_rest": fully.available()}}


def stats() -> dict:
    now = time.time()
    return {**LEDGER.snapshot(HUB.open_mic_s(now)),
            "mic_open_now": any(c.mic_since is not None and c.peer != LOOPBACK for c in HUB.conns.values()),
            "conns": len(HUB.conns), "tablet_connected": HUB.tablet_connected()}


def _json_resp(connection, status, obj):
    resp = connection.respond(status, json.dumps(obj) + "\n")
    del resp.headers["Content-Type"]
    resp.headers["Content-Type"] = "application/json"
    resp.headers["Cache-Control"] = "no-store"
    return resp


def _refuse(connection, status, why, peer, origin, path):
    if GATE.allow("rejected", peer):
        LOG.write({"ev": "rejected", "why": why, "status": status, "peer": peer, "origin": _short(origin),
                   "path": _short(path, 80)})
    return connection.respond(status, http.HTTPStatus(status).phrase + "\n")


def _header(headers, name):
    """(first value or None, True when the header came more than once). headers.get() raises on duplicates."""
    vals = headers.get_all(name)
    return (vals[0] if vals else None), len(vals) > 1


def process_request(connection, request):
    """Every HTTP request comes through here first: peer allowlist, Origin check, /health, /stats.
    Each refusal is logged once (ev "rejected") with peer, origin and path, within the line budget per peer
    (the first 5 a minute, then one "suppressed" count)."""
    peer = _peer(connection.remote_address)
    origin, dup_origin = _header(request.headers, "Origin")
    path = request.path.split("?", 1)[0]
    if not allowed_peer(peer):
        return _refuse(connection, 403, "peer", peer, origin, request.path)
    if dup_origin or (origin is not None and origin != ALLOWED_ORIGIN):
        return _refuse(connection, 403, "origin", peer, origin, request.path)
    if path == "/health":
        return _json_resp(connection, 200, health())
    if path == "/stats":
        return _json_resp(connection, 200, stats())
    if path != "/":
        return _refuse(connection, 404, "path", peer, origin, request.path)
    if "websocket" not in (_header(request.headers, "Upgrade")[0] or "").lower():
        return _refuse(connection, 426, "not_upgrade", peer, origin, request.path)
    if len(HUB.conns) >= TUNE["max_conns"]:
        return _refuse(connection, 503, "max_conns", peer, origin, request.path)
    return None


# ---------------------------------------------------------------- WebSocket side

async def handler(ws):
    conn = Conn(ws)
    HUB.conns[conn.id] = conn
    LOG.write({"ev": "connect", "conn": conn.id, "peer": conn.peer, "origin": _short(conn.origin),
               "path": _short(ws.request.path, 80)})
    try:
        try:
            first = await asyncio.wait_for(ws.recv(), TUNE["hello_timeout_s"])
        except asyncio.TimeoutError:
            await ws.close(1008, "hello timeout")
            return
        if not await on_hello(conn, first):
            return
        async for msg in ws:
            if isinstance(msg, (bytes, bytearray, memoryview)):
                await on_binary(conn, bytes(msg))
            else:
                await on_text(conn, msg)
    except ConnectionClosed:
        pass
    except Exception as e:  # noqa: BLE001  (one bad connection must never take the service down)
        if GATE.allow("error", conn.peer):
            LOG.write({"ev": "error", "where": "handler", "conn": conn.id, "err": f"{type(e).__name__}: {_short(e, 200)}"})
    finally:
        await cleanup(conn)


async def cleanup(conn: Conn):
    s = conn.session
    if s is not None and s.state == "streaming":
        drop_session(s, "socket_closed")
    closed = conn.mic_update(False, time.time())
    HUB.conns.pop(conn.id, None)
    key = (conn.peer, conn.client)
    if HUB.by_key.get(key) is conn:
        del HUB.by_key[key]
    rec = {"ev": "close", "conn": conn.id, "peer": conn.peer, "client": conn.client,
           "code": conn.ws.close_code, "reason": _short(conn.ws.close_reason, 60),
           "secs": round(time.monotonic() - conn.t0, 1), "dropped_msgs": conn.dropped_msgs,
           "dropped_bytes": conn.dropped_bytes}
    if closed is not None and conn.peer != LOOPBACK:
        rec["mic_closed_s"] = closed
    LOG.write(rec)


async def on_hello(conn: Conn, raw) -> bool:
    m = _loads(raw) if isinstance(raw, str) else None
    ok = (isinstance(m, dict) and m.get("type") == "hello" and type(m.get("v")) is int and m.get("v") == 1
          and type(m.get("rate")) is int and m.get("rate") == RATE)
    if not ok:
        kind = "binary" if not isinstance(raw, str) else (m.get("type") if isinstance(m, dict) else "not_json")
        if GATE.allow("bad_hello", conn.peer):
            LOG.write({"ev": "bad_hello", "conn": conn.id, "peer": conn.peer, "kind": _short(kind, 20),
                       "v": _short(m.get("v"), 10) if isinstance(m, dict) else None,
                       "rate": _short(m.get("rate"), 10) if isinstance(m, dict) else None})
        await conn.ws.close(1003, "expected hello v1 rate 16000")
        return False
    conn.said_hello = True
    conn.client = _short(m.get("client") or "", 32)
    conn.lit = m.get("lit") if isinstance(m.get("lit"), bool) else None
    conn.fully = m.get("fully") is True
    conn.tts = "page" if m.get("tts") == "page" else "off"
    conn.dry = CFG.dry_run or (conn.peer == LOOPBACK and m.get("dry") is True)   # dry from 127.0.0.1 only
    key = (conn.peer, conn.client)
    old = HUB.by_key.get(key)
    HUB.by_key[key] = conn
    if old is not None and old is not conn and old.is_open():
        # a page that reconnects (Wi-Fi drop, reload) must not wait for the old socket's close handshake: its
        # streaming turn ends now and its mic-open interval closes now, not when websockets gives up on it
        old.closing = True
        if old.session is not None and old.session.state == "streaming":
            drop_session(old.session, "replaced")
        rrec = {"ev": "replaced", "old": old.id, "new": conn.id, "peer": conn.peer, "client": conn.client}
        closed = old.mic_update(False, time.time())
        if closed is not None and old.peer != LOOPBACK:
            rrec["mic_closed_s"] = closed
        LOG.write(rrec)
        _bg(old.ws.close(4000, "replaced"))
    now_iso = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    if conn.peer != LOOPBACK:
        HUB.last_hello = {"ts": now_iso, "peer": conn.peer, "client": conn.client}
    rec = {"ev": "hello", "conn": conn.id, "peer": conn.peer, "client": conn.client,
           "build": _short(m.get("build"), 40), "lit": conn.lit, "fully": conn.fully, "tts": conn.tts,
           "dry_requested": m.get("dry") is True, "dry": conn.dry}
    if isinstance(m.get("wake"), dict):
        rec["wake"] = {k: _short(m["wake"].get(k), 24) for k in ("engine", "model", "cutoff") if k in m["wake"]}
    if conn.lit is True and conn.peer != LOOPBACK:
        LEDGER.lit_periods += 1
        rec["lit_rise"] = True
    LOG.write(rec)
    await conn.send({"type": "hello", "v": 1, "server": "tablet-voice", "build": BUILD, "stage": CFG.stage,
                     "stt": HUB.stt_name if HUB.ready else None, "dry": conn.dry, "tts": conn.tts, "cfg": hello_cfg()})
    return True


async def on_text(conn: Conn, raw: str):
    if conn.closing:
        return
    m = _loads(raw)
    if not isinstance(m, dict):
        conn.bad += 1
        return
    t = m.get("type")
    if t == "state":
        on_state(conn, m)
    elif t == "wake":
        await on_wake(conn, m)
    elif t == "end":
        await on_end(conn, m)
    elif t == "tts_done":
        on_tts_done(conn, m)
    elif t == "stop_tts":
        await on_stop_tts(conn, m)
    elif t in ("stats", "near"):
        on_telemetry(conn, t, m)
    else:
        conn.bad += 1
        if conn.bad <= 3:
            LOG.write({"ev": "unknown_msg", "conn": conn.id, "type": _short(t, 20)})


def on_state(conn: Conn, m: dict):
    now = time.time()
    rec = {"ev": "state", "conn": conn.id, "peer": conn.peer}
    if isinstance(m.get("lit"), bool):
        if m["lit"] and conn.lit is not True and conn.peer != LOOPBACK:
            LEDGER.lit_periods += 1
            rec["lit_rise"] = True
        conn.lit = m["lit"]
    if isinstance(m.get("mic"), bool):
        closed = conn.mic_update(m["mic"], now)
        conn.mic = m["mic"]
        if closed is not None and conn.peer != LOOPBACK:
            rec["mic_closed_s"] = closed
    rec.update(lit=conn.lit, mic=conn.mic, reason=_short(m.get("reason"), 40))
    LOG.write(rec)
    s = conn.session
    if s is not None and s.state == "streaming" and (conn.lit is False or conn.mic is False):
        # the page says dark (or mic off) while audio still streams: drop it like end{why:"dark"}, so a missing
        # or late end never gets dark audio transcribed (D2 strict stop); a turn past its endpoint finishes. The
        # page sends this state right before its end{dark}, so by_state marks which message got there first.
        drop_session(s, "dark" if conn.lit is False else "mic_off", {"by_state": True})


STATS_KEYS = ("secs", "state", "frames", "samplesPerSec", "engineMsP50", "engineMsP95", "engineMsMax",
              "engineMsMean", "rmsP10", "rmsP50", "rmsP90", "rmsMax", "maxScore", "dropped", "gateSleptFrames")
NEAR_KEYS = ("score", "at", "t_ms")


def on_telemetry(conn: Conn, t: str, m: dict):
    """Page Worker telemetry (spec 14 section 5): logged only, never answered."""
    page = {"type": t}
    for k in (STATS_KEYS if t == "stats" else NEAR_KEYS):
        v = m.get(k)
        if isinstance(v, bool) or v is None:
            continue
        if isinstance(v, (int, float)):
            if _num(v) is not None:
                page[k] = round(v, 4) if isinstance(v, float) else v
        elif isinstance(v, str):
            page[k] = v[:24]
    LOG.write({"ev": t, "conn": conn.id, "peer": conn.peer, "page": page})


def on_tts_done(conn: Conn, m: dict):
    w = HUB.tts.get(conn.peer)
    closed = False
    if w is not None and (m.get("id") is None or m.get("id") == w["id"]):
        HUB.tts.pop(conn.peer, None)
        closed = True
    LOG.write({"ev": "tts_done", "conn": conn.id, "sid": _short(m.get("sid"), 64), "id": _short(m.get("id"), 40),
               "how": _short(m.get("how"), 16), "onset_ms": _num(m.get("onset_ms")), "dur_ms": _num(m.get("dur_ms")),
               "window_closed": closed})


async def on_stop_tts(conn: Conn, m: dict):
    HUB.tts.pop(conn.peer, None)
    rest = None
    if fully.available() and not conn.dry:
        rest = await asyncio.get_running_loop().run_in_executor(IO_POOL, fully.stop, conn.peer)
    LOG.write({"ev": "stop_tts", "conn": conn.id, "sid": _short(m.get("sid"), 64), "rest": rest})


async def reject_wake(conn: Conn, sid, by, why, m):
    await conn.send({"type": "reject", "sid": sid, "why": why, "stage": "wake"})
    rec = {"ev": "session", "sid": sid, "conn": conn.id, "peer": conn.peer, "by": by, "outcome": "reject",
           "why": why, "stage": "wake", "page_score": _num(m.get("score")), "dry_run": conn.dry}
    LEDGER.add_session(rec)
    LOG.write(rec)


async def on_wake(conn: Conn, m: dict):
    sid = _short(m.get("sid") or uuid.uuid4().hex[:12], 64)
    by = "ptt" if m.get("by") == "ptt" else "wake"
    if not HUB.wake_rate_ok(conn.peer, time.monotonic()):
        # more wakes than a person makes (12 a minute from the tablet): busy, logged within the line budget
        await conn.send({"type": "reject", "sid": sid, "why": "busy", "stage": "wake", "limit": "rate"})
        rec = {"ev": "session", "sid": sid, "conn": conn.id, "peer": conn.peer, "by": by, "outcome": "reject",
               "why": "rate", "stage": "wake", "page_score": _num(m.get("score")), "dry_run": conn.dry}
        LEDGER.add_session(rec)
        if GATE.allow("rate", conn.peer):
            LOG.write(rec)
        return
    why = None
    if CFG.stage != "pipeline" or not HUB.ready:
        why = "not_ready"
    elif by == "wake" and CFG.require_fully_for_wake and not conn.fully:
        why = "no_lit_signal"        # no reliable screensaver signal on that page: push-to-talk only (14d 9.2)
    elif conn.lit is False or conn.mic is False:
        why = "not_lit"              # the page's last state said dark or mic off: a page bug, logged
    elif HUB.active is not None or conn.session is not None:
        why = "busy"
    elif by == "wake" and HUB.tts_open(conn.peer):
        why = "tts"                  # the tablet may still be speaking our reply
    if why:
        await reject_wake(conn, sid, by, why, m)
        return
    s = Session(conn, m, sid, by)
    HUB.active = conn.session = s
    s.prefetch = HUB.get_prefetch(asyncio.get_running_loop())   # reads hit a warm cache
    s.watchdog = _bg(stall_watchdog(s))


def release(s: Session):
    s.state = "done"
    if HUB.active is s:
        HUB.active = None
    if s.conn.session is s:
        s.conn.session = None
    if s.watchdog is not None and s.watchdog is not asyncio.current_task():
        s.watchdog.cancel()


def log_session(s: Session, rec: dict):
    s.logged = True
    LEDGER.add_session(rec)
    LOG.write(rec)


def drop_session(s: Session, why: str, extra=None):
    """The page ended the stream (dark, cancel, error) or went away before the endpoint: nothing is answered."""
    if s.state == "done":
        return
    release(s)
    rec = s.log_base()
    rec.update(outcome="dropped", why=why, **(extra or {}))
    log_session(s, rec)


async def reject_session(s: Session, why: str, stage: str, would=None, extra=None):
    if s.state == "done":
        return
    release(s)
    msg = {"type": "reject", "sid": s.sid, "why": why, "stage": stage}
    if s.oww is not None:
        msg["check"] = {"oww": round(s.oww, 3)}
    if would:
        msg["would"] = would
    await s.conn.send(msg)
    rec = s.log_base()
    rec.update(outcome="reject", why=why, stage=stage)
    if would:
        rec["would_run"] = would
    rec.update(extra or {})
    log_session(s, rec)


async def stall_watchdog(s: Session):
    """A page that stops streaming mid-session (frozen, proxy stall) cannot hold the session past the cap."""
    try:
        await asyncio.sleep((TUNE["max_session_ms"] + TUNE["stall_grace_ms"]) / 1000)
    except asyncio.CancelledError:
        return
    if s.state == "streaming":
        await reject_session(s, "too_long", "stall")


async def oww_check(s: Session):
    """openWakeWord over the pre-roll plus the first 640 ms of live audio (14d 5a); early reject only when
    VOICE_OWW_REJECT > 0 (0 = shadow mode: the score is logged and used by the decision table only)."""
    t0 = time.perf_counter()
    pcm = s.audio()[: s.pre + OWW_EXTRA_N]
    try:
        s.oww = await asyncio.get_running_loop().run_in_executor(OWW_POOL, audio.oww_score, pcm)
    except Exception as e:  # noqa: BLE001
        LOG.write({"ev": "error", "where": "oww", "sid": s.sid, "err": type(e).__name__})
        s.oww = 0.0
    s.oww_ms = round((time.perf_counter() - t0) * 1000, 1)
    if CFG.oww_reject > 0 and s.oww < CFG.oww_reject and s.state == "streaming":
        await reject_session(s, "wake_check", "early")


async def on_binary(conn: Conn, data: bytes):
    s = conn.session
    if (s is None or s.state != "streaming" or len(data) % 2 or conn.closing
            or conn.lit is False or conn.mic is False):
        conn.dropped_msgs += 1            # no open session (rejected wake, after the endpoint, page bug) or the
        conn.dropped_bytes += len(data)   # page's own last state says dark or mic off
        return
    n_new = len(data) // 2
    live_s = (s.n + max(0, n_new - s.skip) - s.pre) / RATE          # audio after the pre-roll, this frame included
    if live_s - (time.monotonic() - s.t_open) > TUNE["pace_ahead_ms"] / 1000:
        await reject_session(s, "too_fast", "pace")                  # the page streams in real time; this is not it
        return
    ev = s.feed(np.frombuffer(data, dtype="<i2"))
    if s.by == "wake" and s.oww_task is None and s.n >= s.pre + OWW_EXTRA_N:
        s.oww_task = _bg(oww_check(s))
    if ev == "no_command":
        await reject_session(s, "no_command", "vad")
    elif ev:
        s.state = "processing"
        if s.watchdog is not None:
            s.watchdog.cancel()
        _bg(process(s, ev))


async def on_end(conn: Conn, m: dict):
    s = conn.session
    why = _short(m.get("why"), 16) or "user"
    applies = s is not None and (m.get("sid") is None or m.get("sid") == s.sid)
    rec = {"ev": "end", "conn": conn.id, "sid": _short(m.get("sid"), 64), "why": why,
           "state": s.state if applies else "none"}
    if applies or GATE.allow("end", conn.peer):        # one line per end; stray ones within the line budget
        LOG.write(rec)
    if not applies:
        return
    if s.state != "streaming":
        return    # past the endpoint: the box finishes the turn even for "dark" (14d 9.3); "cancel" drops only before it
    if why in ("user", "maxlen"):
        if s.onset is not None:
            s.state = "processing"
            s.ep_live_n = s.vad_n - s.pre
            if s.watchdog is not None:
                s.watchdog.cancel()
            _bg(process(s, "user" if why == "user" else "maxlen"))
        else:
            await reject_session(s, "no_command", "end")
    else:
        drop_session(s, why)          # "dark", "cancel", "error": dropped before the endpoint


def decide(by: str, name, wake_text: bool, oww_hi: bool, junk: bool) -> str:
    """The V4 decision table with section 0 item 11's write rule.
    run | sorry | refuse_wake_text | silent_reject | silent_result | junk"""
    if by == "ptt":
        return "run" if name else "sorry"
    if junk:
        return "junk"
    if name in WRITE_INTENTS:
        if wake_text:
            return "run"
        # the name is missing from the transcript: card only when openWakeWord says the phrase is in the
        # audio; otherwise this was no wake at all (a false trigger) and stays silent, as the V4 selftest table
        # expects for "add buy milk ..." sent as a wake
        return "refuse_wake_text" if oww_hi else "silent_reject"
    if name in READ_INTENTS:
        gate = wake_text if CFG.read_needs_wake_text else (oww_hi or wake_text)
        return "run" if gate else "silent_reject"
    return "sorry" if (oww_hi and wake_text) else "silent_result"


def plan_tts(conn: Conn, say, dry):
    """Which path speaks the reply: "page", "rest" or None (card only). Nothing while the hello said tts off."""
    if not say or conn.tts == "off" or CFG.tts_via == "off":
        return None, None
    page_ok = conn.fully and conn.tts == "page"
    rest_ok = fully.available()
    if CFG.tts_via == "page":
        via = "page" if page_ok else None
    elif CFG.tts_via == "rest":
        via = "rest" if rest_ok else ("page" if page_ok else None)
    else:
        via = "page" if page_ok else ("rest" if rest_ok else None)
    if via == "rest" and dry:
        return None, "rest_skipped_dry"      # dry run never calls Fully REST
    return via, None


async def speak(s: Session, say: str) -> dict:
    conn = s.conn
    via, note = plan_tts(conn, say, s.dry)
    if via is None:
        return {"tts": note}
    HUB.tts_seq += 1
    tid = f"t{HUB.tts_seq}"
    est = min(15000, 900 + 70 * len(say))
    HUB.tts[conn.peer] = {"until": time.monotonic() + (est + TUNE["tts_extra_ms"]) / 1000, "sid": s.sid, "id": tid}
    sent = await conn.send({"type": "tts_start", "sid": s.sid, "id": tid, "est_ms": est, "via": via, "say": say})
    out = {"tts": via, "tts_id": tid, "est_ms": est, "tts_sent": sent}
    if via == "rest":
        r = await asyncio.get_running_loop().run_in_executor(IO_POOL, fully.speak, say, conn.peer)
        out["rest"] = r
        if not r.get("ok") and conn.fully and conn.tts == "page":
            await conn.send({"type": "tts_start", "sid": s.sid, "id": tid, "est_ms": est, "via": "page", "say": say})
            out["tts"] = "rest_failed_page"
    return out


def _transcribe(pcm):
    """stt.transcribe on the STT thread, with its start time visible to /health (stt_busy_s)."""
    HUB.stt_since = time.monotonic()
    try:
        return stt.transcribe(pcm)
    finally:
        HUB.stt_since = None


async def process(s: Session, why: str):
    """Endpoint reached: the turn runs inside one budget (TUNE process_budget_ms, 20 s). On an overrun (a hung
    STT, say) the session is released with an error result, or with the unsure line when a write had started,
    so nothing can hold HUB.active and turn every later wake into reject{busy}."""
    try:
        await asyncio.wait_for(_process(s, why), TUNE["process_budget_ms"] / 1000)
    except asyncio.TimeoutError:
        LOG.write({"ev": "error", "where": "process", "sid": s.sid, "err": "budget"})
        if s.state != "done":
            release(s)
            say = actions.UNSURE if s.write_started else actions.WENT_WRONG
            await s.conn.send({"type": "result", "sid": s.sid, "heard": None, "text": None, "intent": {"name": None},
                               "ok": False, "say": say, "card": say, "do": [{"what": "refresh"}] if s.write_started else [],
                               "dry": s.dry})
        if not s.logged:
            rec = s.log_base()
            rec.update(outcome="error", why="process_budget", write_started=s.write_started)
            log_session(s, rec)


async def _process(s: Session, why: str):
    """STT, junk gate, wake strip, intent, decision, action, result, speech."""
    conn = s.conn
    loop = asyncio.get_running_loop()
    s.endpoint_why = why
    t_ep = time.perf_counter()
    try:
        await conn.send({"type": "endpoint", "sid": s.sid, "why": why})
        LOG.write({"ev": "endpoint", "sid": s.sid, "why": why, "conn": conn.id})
        if s.by == "wake":
            if s.oww_task is not None:
                await s.oww_task
            if s.oww is None:
                pcm = s.audio()[: s.pre + OWW_EXTRA_N]
                s.oww = await loop.run_in_executor(OWW_POOL, audio.oww_score, pcm)
            if CFG.oww_reject > 0 and s.oww < CFG.oww_reject:
                await reject_session(s, "wake_check", "final")
                return
            if s.state == "done":
                return
        t0 = time.perf_counter()
        text, no_speech, avg_lp = await loop.run_in_executor(STT_POOL, _transcribe, s.audio())
        stt_ms = round((time.perf_counter() - t0) * 1000)
        junk = stt.is_junk(text, no_speech, avg_lp)
        oww_hi = s.oww is not None and s.oww >= TUNE["oww_ok"]
        rest, wake_text = strip_wake(text, wake_audio=(s.by == "ptt" or oww_hi))
        it = {"intent": None} if junk else match(rest)
        name = it.get("intent")
        slots = {k: v for k, v in it.items() if k != "intent"}
        kind = decide(s.by, name, wake_text, oww_hi, junk)
        heard = {"heard": text, "text": rest, "no_speech": round(no_speech, 3), "avg_logprob": round(avg_lp, 3),
                 "junk": junk, "wake_text": wake_text, "intent": {"name": name, **slots}, "stt_ms": stt_ms}
        if kind in ("silent_reject", "junk") or (kind == "silent_result" and not wake_text):
            # nothing ran, nothing was said, and the name was not heard: most likely speech overheard after a
            # false wake. Its words are not kept anywhere (length, scores and the intent name only).
            del heard["heard"], heard["text"]
            heard.update(intent={"name": name}, heard_len=len(text), transcript="not_kept")
        if kind in ("junk", "silent_reject"):
            await reject_session(s, "no_command" if kind == "junk" else "wake_check", "final",
                                 would=name if kind == "silent_reject" else None, extra=heard)
            return
        act = None
        if kind == "run":
            data_res = None
            if name in ("next.event", "schedule.tomorrow", "task.complete") and s.prefetch is not None:
                try:                                   # the read budget started at the wake (about 5 s)
                    data_res = await asyncio.wait_for(asyncio.shield(s.prefetch),
                                                      max(0.0, s.read_deadline - time.monotonic()))
                except asyncio.TimeoutError:
                    data_res = None
            res = await loop.run_in_executor(IO_POOL, functools.partial(
                actions.run, name, slots, dry=s.dry, dash=CFG.dash, data_res=data_res,
                deliverable=conn.is_open, allow_complete=CFG.allow_complete, read_deadline=s.read_deadline,
                on_write=functools.partial(setattr, s, "write_started", True)))
            act = res.get("action")
            if data_res is not None:
                act = dict(act or {}, prefetch_ms=data_res.get("ms"), prefetch_err=data_res.get("err"))
        elif kind == "refuse_wake_text":
            res = {"ok": False, "say": None, "card": CARD_WAKE_TEXT, "do": [], "refused": "wake_text", "say_log": None}
        elif kind == "sorry":
            res = {"ok": False, "say": actions.SORRY, "card": actions.SORRY, "do": [], "refused": None, "say_log": actions.SORRY}
        else:  # silent_result: no speech, the card shows what was heard
            res = {"ok": False, "say": None, "card": None, "do": [], "refused": None, "say_log": None}
        total_ms = round((time.perf_counter() - t_ep) * 1000)
        msg = {"type": "result", "sid": s.sid, "heard": text, "text": rest, "intent": {"name": name, **slots},
               "ok": bool(res["ok"]), "say": res["say"], "card": res["card"], "do": res["do"], "dry": s.dry,
               "check": {"oww": round(s.oww, 3) if s.oww is not None else None, "wake_text": wake_text},
               "timing_ms": {"stt": stt_ms, "action": (act or {}).get("ms"), "total": total_ms}}
        if res.get("refused"):
            msg["refused"] = res["refused"]
        delivered = False
        if res.get("refused") != "undeliverable":
            delivered = await conn.send(msg)
        release(s)
        spoken = await speak(s, res["say"]) if (delivered and res["say"]) else {}
        rec = s.log_base()
        rec.update(heard)
        rec.update(outcome="refused" if res.get("refused") else kind,
                   ok=bool(res["ok"]), refused=res.get("refused"), say=res.get("say_log"),
                   say_len=len(res["say"]) if res.get("say") else 0, do=[d.get("what") for d in res["do"]],
                   action=act, action_ms=(act or {}).get("ms"), delivered=delivered, total_ms=total_ms, **spoken)
        if res.get("unsure"):
            rec["unsure"] = True
        if kind == "refuse_wake_text":
            rec["would_run"] = name
        log_session(s, rec)
    except Exception as e:  # noqa: BLE001
        LOG.write({"ev": "error", "where": "process", "sid": s.sid, "err": f"{type(e).__name__}: {_short(e, 200)}"})
        if s.state != "done":
            release(s)
            await conn.send({"type": "result", "sid": s.sid, "heard": None, "text": None, "intent": {"name": None},
                             "ok": False, "say": actions.WENT_WRONG, "card": actions.WENT_WRONG, "do": [], "dry": s.dry})
            rec = s.log_base()
            rec.update(outcome="error", why=type(e).__name__)
            log_session(s, rec)


# ---------------------------------------------------------------- housekeeping and main

async def tick():
    """Every 15 s: day rollover (daily summary line, mic intervals split at midnight, log prune)."""
    while True:
        await asyncio.sleep(15)
        GATE.roll()
        today = dt.date.today()
        if today == LEDGER.day:
            continue
        midnight = dt.datetime.combine(today, dt.time.min).timestamp()
        for c in HUB.conns.values():
            if c.mic_since is not None and c.mic_since < midnight:
                if c.peer != LOOPBACK:
                    LEDGER.mic_s += midnight - c.mic_since
                c.mic_since = midnight
        LOG.write({"ev": "daily", **LEDGER.snapshot()})
        LEDGER.day = today
        LEDGER.reset()
        carry = sum(1 for c in HUB.conns.values() if c.lit and c.peer != LOOPBACK)
        LEDGER.lit_periods += carry
        LOG.write({"ev": "rollover", "lit_rise": carry, "pruned": LOG.prune()})


async def amain() -> int:
    global np, audio, stt
    loop = asyncio.get_running_loop()
    LOG.write({"ev": "start", "build": BUILD, "pid": os.getpid(), "python": sys.version.split()[0],
               "cfg": CFG.public(), "log_pruned": LOG.pruned})
    replayed = LEDGER.replay(LOG.path_for(LEDGER.day))
    if CFG.stage == "pipeline":
        try:
            t0 = time.perf_counter()
            import numpy as _np
            import audio as _audio
            import stt as _stt
            np, audio, stt = _np, _audio, _stt
            audio.load(CFG.models_dir)
            HUB.load_info = {"audio_ms": round((time.perf_counter() - t0) * 1000), **stt.load(CFG.stt_threads)}
            HUB.stt_name, HUB.ready = stt.NAME, True
        except Exception as e:  # noqa: BLE001  (missing model, hash mismatch, no HF cache: exit, unit fails loudly)
            LOG.write({"ev": "fatal", "where": "load", "err": f"{type(e).__name__}: {_short(e, 300)}"})
            return 1
        LOG.write({"ev": "ready", "stt": stt.NAME, **HUB.load_info, **_rss_mb(), "replayed_sessions": replayed})
    stop = loop.create_future()

    def _stop(*_a):
        if not stop.done():
            stop.set_result(True)
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _stop)
    if CFG.exit_on_stdin_eof:            # test harness: closing our stdin is the stop signal (no kill needed)
        def _on_stdin():
            if not os.read(0, 4096):
                loop.remove_reader(0)
                _stop()
        loop.add_reader(0, _on_stdin)
    try:
        async with serve(handler, CFG.host, CFG.port, origins=[ALLOWED_ORIGIN, None],
                         process_request=process_request, max_size=262144, ping_interval=20, ping_timeout=20,
                         close_timeout=TUNE["close_timeout_s"], server_header="tablet-voice"):
            LOG.write({"ev": "listening", "host": CFG.host, "port": CFG.port, "stage": CFG.stage, "dry_run": CFG.dry_run})
            ticker = asyncio.create_task(tick())
            await stop
            ticker.cancel()
    except OSError as e:
        LOG.write({"ev": "fatal", "where": "bind", "err": f"{type(e).__name__}: {_short(e, 200)}"})
        return 1
    cpu = os.times()
    LOG.write({"ev": "stop", "uptime_s": round(time.monotonic() - HUB.t0), "cpu_s": round(cpu.user + cpu.system, 2), **_rss_mb()})
    return 0


def main():
    global LOG
    LOG = EventLog(CFG.log_dir)
    wl = logging.getLogger("websockets")
    wl.setLevel(logging.WARNING)
    wl.addHandler(_WsLogHandler())
    wl.propagate = False
    try:
        rc = asyncio.run(amain())
    except KeyboardInterrupt:
        rc = 0
    STT_POOL.shutdown(wait=False, cancel_futures=True)
    OWW_POOL.shutdown(wait=False, cancel_futures=True)
    IO_POOL.shutdown(wait=False, cancel_futures=True)
    sys.exit(rc)


if __name__ == "__main__":
    main()
