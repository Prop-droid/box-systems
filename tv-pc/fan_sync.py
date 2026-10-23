#!/usr/bin/env python3
# Build RPM-synced CoolerControl curves for TV-PC board fans from measured duty->RPM maps.
# All three follow nct6798 temp8 (PECI); each fan gets the duty that yields the same target RPM.
import json, base64, http.cookiejar, urllib.request, sys
B = "https://tv-pc.tailb74909.ts.net"
NCT = "00a4da18625f56275c89e2fcd25a83c08c5ad3326452fa7e252fcc8a89c92493"
# duty% -> rpm, measured 2026-10-22 (descending sweep 30-70, ascending 80/100)
MAP = {
 "fan1": {30:1032,34:1171,36:1240,38:1317,40:1384,42:1467,45:1548,50:1715,55:1896,60:2042,70:2368,80:2652,100:2993},
 "fan2": {30:864,34:953,36:1008,38:1017,40:1072,42:1148,45:1188,50:1264,55:1365,60:1416,70:1560,80:1695,100:1936},
 "fan4": {30:1094,34:1235,36:1310,38:1380,40:1451,42:1511,45:1632,50:1802,55:1979,60:2156,70:2481,80:2743,100:2967},
}
# PECI temp C -> target rpm (same for all fans); 75C+ = 100% duty on every fan.
# Flat 1700 plateau 50-70C: gaming PECI swings 58-63C, a sloped curve there = audible ramping.
TARGET = [(30,1100),(40,1100),(45,1400),(50,1700),(70,1700)]
# Per-fan extra rpm in the gaming band (>=50C). fan2 = CPU cooler; Tomas 2026-10-22: "processor fan can spin faster"
EXTRA = {"fan2": 150}
def duty_for(fan, rpm):
    pts = sorted(MAP[fan].items())
    for (d0,r0),(d1,r1) in zip(pts, pts[1:]):
        if r0 <= rpm <= r1: return round(d0 + (d1-d0)*(rpm-r0)/(r1-r0))
    return 30 if rpm < pts[0][1] else 100
curves = {f: [[t, max(30, duty_for(f, r + (EXTRA.get(f, 0) if t >= 50 else 0)))] for t, r in TARGET] + [[75, 100]] for f in MAP}
for f, c in curves.items(): print(f, c)
if "--apply" not in sys.argv: sys.exit()
pw = open("/home/tomas/.config/coolercontrol/tv-pc.pass").read().strip()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def req(m, p, body=None, auth=None):
    r = urllib.request.Request(B+p, method=m, data=json.dumps(body).encode() if body is not None else None)
    r.add_header("Content-Type", "application/json")
    if auth: r.add_header("Authorization", "Basic " + base64.b64encode(auth.encode()).decode())
    return op.open(r, timeout=10).read()
req("POST", "/login", auth="CCAdmin:" + pw)
# Hysteresis: speed rises immediately, drops only after temp falls 3C and holds 4s
FUNC = "tvpc-hysteresis"
fn = {"uid": FUNC, "name": "hysteresis 3C down", "f_type": "Standard", "duty_minimum": 1, "duty_maximum": 100,
      "step_size_min_decreasing": 0, "step_size_max_decreasing": 0, "response_delay": 4, "deviance": 3.0,
      "only_downward": True, "threshold_hopping": True, "bypass_min_at_extremes": False}
have = [f["uid"] for f in json.loads(req("GET", "/functions"))["functions"]]
req("PUT" if FUNC in have else "POST", "/functions", fn)
for f, c in curves.items():
    req("PUT", "/profiles", {"uid": f"tvpc-{f}-quiet", "name": f"{f} synced rpm", "p_type": "Graph",
        "speed_profile": c, "temp_source": {"temp_name": "temp8", "device_uid": NCT},
        "function_uid": FUNC, "member_profile_uids": []})
print("applied")
