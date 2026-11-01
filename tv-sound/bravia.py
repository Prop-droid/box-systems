#!/usr/bin/env python3
"""Sony Bravia XR-65A80L ("Livingroom TV", 192.168.1.16) REST helper for the TV-sound-echo debug.

  bravia.py state          -> power, Speakers (outputTerminal), volume/mute; +system info if a PSK exists
  bravia.py watch          -> poll every 5 s, append transitions to logs/output-YYYY-MM-DD.csv (systemd unit tv-sound-watch)
  bravia.py fix            -> Sony's documented hotfix for "sound from TV speakers AND audio system":
                              Speakers -> TV speaker -> back to Audio system (needs the PSK)
  bravia.py set speaker|audioSystem

PSK (optional, unlocks fix/set/system info): TV Settings > Network & Internet > Home network setup > IP control >
Authentication = "Normal and Pre-Shared Key", set a key, then save it to ~/.config/bravia/psk (chmod 600).
"""
import csv, datetime as dt, json, os, pathlib, sys, time, urllib.request

TV = os.environ.get("BRAVIA_IP", "192.168.1.16")
PSK_FILE = pathlib.Path.home() / ".config/bravia/psk"
LOG_DIR = pathlib.Path(__file__).resolve().parent / "logs"


def psk():
    try:
        return PSK_FILE.read_text().strip() or None
    except FileNotFoundError:
        return None


def call(service, method, params=None, version="1.0", timeout=4):
    body = json.dumps({"method": method, "id": 1, "params": params or [], "version": version}).encode()
    headers = {"Content-Type": "application/json"}
    if psk():
        headers["X-Auth-PSK"] = psk()
    req = urllib.request.Request(f"http://{TV}/sony/{service}", data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        out = json.loads(r.read().decode())
    if "error" in out:
        raise RuntimeError(f"{method}: {out['error']}")
    return out["result"]


def snapshot():
    """Returns dict; power 'unreachable' if the TV does not answer (deep standby)."""
    try:
        power = call("system", "getPowerStatus")[0]["status"]
    except Exception:
        return {"power": "unreachable", "speakers": "", "volume": "", "mute": ""}
    snap = {"power": power, "speakers": "", "volume": "", "mute": ""}
    try:
        snap["speakers"] = call("audio", "getSoundSettings", [{"target": "outputTerminal"}], "1.1")[0][0]["currentValue"]
    except Exception as e:
        snap["speakers"] = f"err:{e}"[:40]
    try:
        vol = call("audio", "getVolumeInformation")[0][0]
        snap["volume"], snap["mute"] = vol.get("volume"), vol.get("mute")
    except Exception:
        pass
    return snap


def cmd_state():
    s = snapshot()
    print(json.dumps(s))
    if psk():
        try:
            info = call("system", "getSystemInformation")[0]
            print(json.dumps({k: info.get(k) for k in ("model", "generation", "serial", "name", "region")}))
        except Exception as e:
            print("system info:", e)
    else:
        print("no PSK -> firmware/system info not readable (see docstring)")


def set_speakers(value):
    return call("audio", "setSoundSettings", [{"settings": [{"target": "outputTerminal", "value": value}]}], "1.1")


def cmd_fix():
    if not psk():
        sys.exit("fix needs the PSK (~/.config/bravia/psk); see docstring")
    before = snapshot()["speakers"]
    set_speakers("speaker"); time.sleep(3)
    set_speakers("audioSystem"); time.sleep(2)
    print(json.dumps({"before": before, "after": snapshot()["speakers"]}))


def cmd_watch(interval=5, heartbeat=600):
    LOG_DIR.mkdir(exist_ok=True)
    last, last_hb = None, 0.0
    while True:
        snap = snapshot()
        key = (snap["power"], snap["speakers"], snap["mute"])
        now = time.time()
        if key != last or now - last_hb >= heartbeat:
            path = LOG_DIR / f"output-{dt.date.today().isoformat()}.csv"
            new = not path.exists()
            with path.open("a", newline="") as f:
                w = csv.writer(f)
                if new:
                    w.writerow(["ts", "event", "power", "speakers", "volume", "mute"])
                w.writerow([dt.datetime.now().isoformat(timespec="seconds"),
                            "change" if key != last else "heartbeat",
                            snap["power"], snap["speakers"], snap["volume"], snap["mute"]])
            last, last_hb = key, now
        time.sleep(interval)


if __name__ == "__main__":
    a = sys.argv[1:] or ["state"]
    if a[0] == "state":
        cmd_state()
    elif a[0] == "watch":
        cmd_watch()
    elif a[0] == "fix":
        cmd_fix()
    elif a[0] == "set" and len(a) == 2 and a[1] in ("speaker", "audioSystem"):
        print(set_speakers(a[1]))
    else:
        sys.exit(__doc__)
