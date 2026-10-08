#!/usr/bin/env python3
"""Crisp-question variant: 8 concrete devices, one short yes/no each. Usage: eval_crisp.py [N] [th]"""
import pathlib, re, sys, time, random
sys.path.insert(0, str(pathlib.Path.home() / "systems/mechanism-tagger"))
import tag  # noqa: E402
N = int(sys.argv[1]) if len(sys.argv) > 1 else 30
TH = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
Q = {
    "offer": "Does the ad offer a discount, coupon, free gift, free shipping or bundle price?",
    "urgency": "Does the ad use a deadline, scarcity or limited-time pressure?",
    "social": "Does the ad cite reviews, ratings, customer counts or popularity as proof?",
    "authority": "Does the ad cite a doctor, dietitian, expert, study or clinical research?",
    "stat": "Does the ad state a specific nutrient or product number such as grams, calories or fiber?",
    "percent": "Does the ad make a percentage comparison claim like 60% less sugar (not a discount)?",
    "taste": "Does the ad describe taste, flavor, texture or cravings?",
    "callout": "Does the ad name its reader by group or situation, like moms or people on GLP-1?",
}
qs = {k: {"type": "noul", "instructions": v} for k, v in Q.items()}
items = tag.load_items(); gold = tag.load_tags()["items"]
pairs = [(rid, it["text"], set(gold[rid]["devices"]) & set(Q)) for rid, it in items.items()
         if rid in gold and gold[rid].get("hash") == tag.text_hash(it["text"])]
random.Random(7).shuffle(pairs); pairs = pairs[:N]
from laya import Router  # noqa: E402
r = Router(); r.predict("warmup", {"x": qs["offer"]})
c = {k: [0, 0, 0] for k in Q}; lat = []
for i, (rid, text, g) in enumerate(pairs, 1):
    body = re.sub(r"\s+", " ", text[:tag.COPY_MAX]).strip()
    t = time.time(); out = r.predict(body, qs); lat.append(time.time() - t)
    pred = {k for k in Q if out["answers"][k]["noul"] >= TH}
    for k in Q:
        c[k][0] += k in pred and k in g; c[k][1] += k in pred and k not in g; c[k][2] += k in g and k not in pred
    print(f"{i}/{len(pairs)} {lat[-1]:.1f}s", flush=True)
print(f"\n{'device':10} {'P':>5} {'R':>5} {'F1':>5} gold")
for k, (a, b, d) in c.items():
    p = a/(a+b) if a+b else 0; rc = a/(a+d) if a+d else 0
    print(f"{k:10} {p:5.2f} {rc:5.2f} {2*p*rc/(p+rc) if p+rc else 0:5.2f} {a+d}")
A, B, D = (sum(v[i] for v in c.values()) for i in range(3)); p, rc = A/(A+B), A/(A+D)
lat.sort(); print(f"micro P={p:.2f} R={rc:.2f} F1={2*p*rc/(p+rc):.2f} | n={len(pairs)} th={TH} | p50 {lat[len(lat)//2]:.1f}s/item (8 questions)")
