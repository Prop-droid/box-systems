"""fully.py: optional Fully Kiosk REST speech fallback (14d section 8; spec 14 section 0 item 5 and V11).

Inert unless FULLY_PW is in the environment (only from the optional ~/.config/tablet-voice/env, mode 600,
which spec 14 says to create only if D1 is "no"). With D1 = yes the page speaks itself
(fully.textToSpeech in the dashboard) and the box needs no copy of the password. The password goes into
the request URL and nowhere else: it is never logged, and errors are reduced to a class name or an HTTP
status. The server never calls this in dry run.
"""
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PORT = 2323
DEFAULT_TABLET = "192.168.1.89"


def available() -> bool:
    return bool(os.environ.get("FULLY_PW"))


def _host(peer) -> str:
    """The socket peer (socat connects from the tablet), else ~/systems/.state/tablet-ip, else the fixed address."""
    if peer and re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", peer) and not peer.startswith("127."):
        return peer
    try:
        ip = (Path.home() / "systems/.state/tablet-ip").read_text().strip()
        if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", ip):
            return ip
    except OSError:
        pass
    return DEFAULT_TABLET


def call(cmd: str, peer=None, params=None, timeout=2.0) -> dict:
    pw = os.environ.get("FULLY_PW")
    if not pw:
        return {"ok": False, "err": "no_password"}
    base = os.environ.get("VOICE_FULLY_URL") or f"http://{_host(peer)}:{PORT}"   # VOICE_FULLY_URL: tests only
    q = dict({"cmd": cmd, "type": "json"}, **(params or {}))
    q["password"] = pw
    url = base.rstrip("/") + "/?" + urllib.parse.urlencode(q)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            code, raw = r.status, r.read(4096)
        try:
            status = json.loads(raw).get("status")
        except (ValueError, AttributeError):
            status = None
        return {"ok": code == 200 and status in (None, "OK", "Success"), "status": status if isinstance(status, str) else None}
    except urllib.error.HTTPError as e:
        return {"ok": False, "err": f"http_{e.code}"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "err": type(e).__name__}


def speak(text: str, peer=None) -> dict:
    # no `engine` argument (a changing engine argument rebuilds Fully's TTS engine), en_US with an underscore,
    # queue=1 so a reply never cuts other speech queued on the tablet (14b 4a to 4d, 14d 8)
    return call("textToSpeech", peer, {"text": text, "locale": "en_US", "queue": "1"})


def stop(peer=None) -> dict:
    return call("stopTextToSpeech", peer)
