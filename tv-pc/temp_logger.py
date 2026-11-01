#!/usr/bin/env python3
"""Log tv-pc temps, loads, power and fans every 10 s to logs/temps-YYYY-MM-DD.csv.

Companion to netconsole_listener.py for the hard-freeze hunt: the PC's own
disk loses its last minutes on a freeze, this box keeps them. Source is
CoolerControl's Prometheus /metrics (admin login, same as fan_sync.py).
Units: temps C, load %, power W, fans rpm, clock MHz. Every 5 min the hz
column is refreshed over SSH from the active CRTC (ties a freeze to the
display mode in use). A '#' line marks the PC going up or unreachable.
"""
import base64
import csv
import glob
import http.cookiejar
import os
import re
import subprocess
import time
import urllib.error
import urllib.request

B = "https://tv-pc.tailb74909.ts.net"
PC = "root@100.74.97.97"
DIR = os.path.expanduser("~/systems/tv-pc/logs")
KEEP_DAYS = 30
CPU = "Intel(R) Core(TM) i5-14400F"
# column -> (metric, device, sensor/channel); nct6798 temp8 = PECI, the fan-curve source
COLS = {
    "cpu_pkg": ("temperature_celsius", CPU, "temp1"),
    "cpu_peci": ("temperature_celsius", "nct6798", "temp8"),
    "cpu_load": ("duty_percent", CPU, "CPU Load"),
    "cpu_w": ("power_watts", CPU, "power0"),
    "gpu_edge": ("temperature_celsius", "amdgpu", "temp1"),
    "gpu_hot": ("temperature_celsius", "amdgpu", "temp2"),
    "gpu_mem": ("temperature_celsius", "amdgpu", "temp3"),
    "gpu_load": ("duty_percent", "amdgpu", "GPU Load"),
    "gpu_w": ("power_watts", "amdgpu", "power1_average"),
    "gpu_mhz": ("frequency_hertz", "amdgpu", "freq1"),
    "gpu_fan": ("fan_rpm", "amdgpu", "fan1"),
    "nvme": ("temperature_celsius", "nvme", "temp1"),
    "fan1": ("fan_rpm", "nct6798", "fan1"),
    "fan2": ("fan_rpm", "nct6798", "fan2"),
    "fan4": ("fan_rpm", "nct6798", "fan4"),
}
PW = open(os.path.expanduser("~/.config/coolercontrol/tv-pc.pass")).read().strip()
opener = None


def metrics():
    global opener
    for retry in (False, True):
        try:
            if opener is None:
                opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
                r = urllib.request.Request(B + "/login", method="POST")
                r.add_header("Authorization", "Basic " + base64.b64encode(f"CCAdmin:{PW}".encode()).decode())
                opener.open(r, timeout=5)
            return opener.open(B + "/metrics", timeout=5).read().decode()
        except urllib.error.HTTPError as e:
            opener = None  # session expired or daemon restarted: log in again once
            if e.code != 401 or retry:
                raise


def parse(text):
    vals = {}
    for m in re.finditer(r'^coolercontrol_(\w+)\{(.*)\} (\S+)$', text, re.M):
        lab = dict(re.findall(r'(\w+)="([^"]*)"', m[2]))
        vals[(m[1], lab.get("device"), lab.get("sensor") or lab.get("channel"))] = float(m[3])
    row = []
    for metric, dev, name in COLS.values():
        v = vals.get((metric, dev, name))
        if v is None:
            row.append("")
        elif metric == "frequency_hertz":
            row.append(round(v / 1e6))
        elif metric == "fan_rpm":
            row.append(round(v))
        else:
            row.append(f"{round(v, 1):g}")
    return row


def display_mode():
    try:
        out = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", PC,
                              "grep -h 'mode: ' /sys/kernel/debug/dri/*/state"],
                             capture_output=True, text=True, timeout=20).stdout
    except subprocess.TimeoutExpired:
        return ""
    m = re.search(r'mode: "(\d+x\d+)": (\d+) ', out)  # first active CRTC; idle ones read "": 0
    return f"{m[1]}@{m[2]}" if m else ""


def prune():
    cutoff = time.time() - KEEP_DAYS * 86400
    for p in glob.glob(os.path.join(DIR, "temps-*.csv")):
        if os.path.getmtime(p) < cutoff:
            os.remove(p)


os.makedirs(DIR, exist_ok=True)
up, hz, next_hz = None, "", 0
while True:
    t = time.time()
    try:
        row, err = parse(metrics()), None
    except Exception as e:
        row, err = None, e
    ok = row is not None
    if ok and t >= next_hz:
        hz, next_hz = display_mode(), t + 300
    if ok or ok != up:
        path = os.path.join(DIR, time.strftime("temps-%Y-%m-%d.csv"))
        new = not os.path.exists(path)
        with open(path, "a", newline="") as f:
            if new:
                csv.writer(f).writerow(["time", *COLS, "hz"])
                prune()
            if ok != up:
                f.write(f"# {time.strftime('%H:%M:%S')} {'up' if ok else 'unreachable: ' + str(err)[:100]}\n")
            if ok:
                csv.writer(f).writerow([time.strftime("%H:%M:%S"), *row, hz])
    if not ok:
        next_hz = 0  # re-read the mode as soon as the PC is back
    up = ok
    time.sleep(max(1, 10 - (time.time() - t)))
