#!/usr/bin/env python3
# Sweep TV-PC board fans (fan1/2/4) through fixed duties via CoolerControl, record RPM, restore profiles.
import json, subprocess, time, http.cookiejar, urllib.request, base64, ssl
B = "https://tv-pc.tailb74909.ts.net"
NCT = "00a4da18625f56275c89e2fcd25a83c08c5ad3326452fa7e252fcc8a89c92493"
FANS = ["fan1", "fan2", "fan4"]
pw = open("/home/tomas/.config/coolercontrol/tv-pc.pass").read().strip()
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
def req(method, path, body=None, auth=None):
    r = urllib.request.Request(B + path, method=method, data=json.dumps(body).encode() if body is not None else None)
    r.add_header("Content-Type", "application/json")
    if auth: r.add_header("Authorization", "Basic " + base64.b64encode(auth.encode()).decode())
    return op.open(r, timeout=10).read()
req("POST", "/login", auth="CCAdmin:" + pw)
def rpms():
    out = subprocess.run(["ssh", "root@100.74.97.97",
        "d=$(dirname $(grep -l nct6798 /sys/class/hwmon/hwmon*/name)); cat $d/fan1_input $d/fan2_input $d/fan4_input"],
        capture_output=True, text=True).stdout.split()
    return dict(zip(FANS, map(int, out)))
res = {}
try:
    for duty in [25, 35, 45, 55, 65, 80, 100]:
        for f in FANS: req("PUT", f"/devices/{NCT}/settings/{f}/manual", {"speed_fixed": duty})
        time.sleep(6)
        res[duty] = rpms(); print(duty, res[duty], flush=True)
finally:
    for f in FANS: req("PUT", f"/devices/{NCT}/settings/{f}/profile", {"profile_uid": f"tvpc-{f}-quiet"})
    print("restored profiles")
json.dump(res, open("/home/tomas/systems/tv-pc/fan_sweep.json", "w"))
