#!/usr/bin/env python3
# Build RPM-synced CoolerControl curves for TV-PC board fans from measured duty->RPM maps.
# fan2 (CPU cooler) follows nct6798 temp8 (PECI). fan1+fan4 (case: bottom = GPU intake, top = exhaust)
# take the max of a PECI curve and a GPU edge curve (Mix profile), so the GPU gets air even when the CPU is cool.
# Each fan gets the duty that yields the target RPM. Revert to the 2026-10-22 curves:
#   git -C ~/systems show 66adc76:tv-pc/fan_sync.py | python3 - --apply
import json, base64, http.cookiejar, urllib.request, sys
B = "https://tv-pc.tailb74909.ts.net"
NCT = "00a4da18625f56275c89e2fcd25a83c08c5ad3326452fa7e252fcc8a89c92493"
GPU = "7442ece48a26c31e110bbb1d21577e4a7b4613be5cce8adee1fe2d0832d11696"
# duty% -> rpm, measured 2026-10-22 (descending sweep 30-70, ascending 80/100)
MAP = {
 "fan1": {30:1032,34:1171,36:1240,38:1317,40:1384,42:1467,45:1548,50:1715,55:1896,60:2042,70:2368,80:2652,100:2993},
 "fan2": {30:864,34:953,36:1008,38:1017,40:1072,42:1148,45:1188,50:1264,55:1365,60:1416,70:1560,80:1695,100:1936},
 "fan4": {30:1094,34:1235,36:1310,38:1380,40:1451,42:1511,45:1632,50:1802,55:1979,60:2156,70:2481,80:2743,100:2967},
}
# (temp C -> target rpm points, temp C where the fan goes to 100% duty).
# Flat plateaus in the gaming band: gaming PECI swings 58-63C, a sloped curve there = audible ramping.
CASE_CPU = [(30,1100),(40,1100),(45,1400),(50,1700),(75,1700)], 85
# 2026-10-31, Tomas: less noise but keep the GPU's air -> only the CPU fan drops, 1850 -> 1300 in games.
# 100% points moved 75 -> 85C so the warmer CPU can't spin the case fans up to ~3000 rpm.
CPU = [(30,1100),(40,1100),(45,1200),(50,1300),(75,1300)], 85
# GPU edge (amdgpu temp1): desktop 40-48C, gaming ~64C (hotspot 83) on 2026-10-22.
CASE_GPU = [(48,1100),(55,1400),(60,1700),(80,1700)], 90
GRAPHS = {  # profile uid -> (fan, curve, (temp device, sensor))
 "tvpc-fan2-quiet": ("fan2", CPU, (NCT, "temp8")),
 "tvpc-fan1-cpu": ("fan1", CASE_CPU, (NCT, "temp8")), "tvpc-fan1-gpu": ("fan1", CASE_GPU, (GPU, "temp1")),
 "tvpc-fan4-cpu": ("fan4", CASE_CPU, (NCT, "temp8")), "tvpc-fan4-gpu": ("fan4", CASE_GPU, (GPU, "temp1")),
}
# The channels stay assigned to tvpc-fan{1,4}-quiet; those become Mix (max) profiles over the graphs above.
MIX = {"tvpc-fan1-quiet": ["tvpc-fan1-cpu", "tvpc-fan1-gpu"], "tvpc-fan4-quiet": ["tvpc-fan4-cpu", "tvpc-fan4-gpu"]}
def duty_for(fan, rpm):
    pts = sorted(MAP[fan].items())
    for (d0,r0),(d1,r1) in zip(pts, pts[1:]):
        if r0 <= rpm <= r1: return round(d0 + (d1-d0)*(rpm-r0)/(r1-r0))
    return 30 if rpm < pts[0][1] else 100
curves = {uid: [[t, max(30, duty_for(f, r))] for t, r in pts] + [[full, 100]] for uid, (f, (pts, full), _) in GRAPHS.items()}
for uid, c in curves.items(): print(uid, c)
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
have = [p["uid"] for p in json.loads(req("GET", "/profiles"))["profiles"]]
for uid, (f, _, (dev, temp)) in GRAPHS.items():  # members first, the Mix profiles point at them
    req("PUT" if uid in have else "POST", "/profiles", {"uid": uid, "name": uid.removeprefix("tvpc-").replace("-", " "),
        "p_type": "Graph", "speed_profile": curves[uid], "temp_source": {"temp_name": temp, "device_uid": dev},
        "function_uid": FUNC, "member_profile_uids": []})
for uid, members in MIX.items():
    req("PUT", "/profiles", {"uid": uid, "name": uid.removeprefix("tvpc-").split("-")[0] + " max(cpu,gpu)", "p_type": "Mix",
        "member_profile_uids": members, "mix_function_type": "Max", "function_uid": "0"})
print("applied")
