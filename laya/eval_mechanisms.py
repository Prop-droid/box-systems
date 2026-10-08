#!/usr/bin/env python3
"""Zero-shot Laya vs the Haiku labels mechanism-tagger already wrote.

Gold = tags.json devices for items whose current copy hash still matches. One noul
question per device, all 23 in one forward pass per item. Prints per-device P/R/F1,
micro-F1, latency. Usage: eval_mechanisms.py [N] [threshold]
"""
import json, pathlib, re, sys, time, random
sys.path.insert(0, str(pathlib.Path.home() / "systems/mechanism-tagger"))
import tag  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 150
TH = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5

desc = {}
for line in (tag.HERE / "prompt_template.txt").read_text().splitlines():
    m = re.match(r"- (\w+): (.+)", line)
    if m and m.group(1) in tag.KEYSET:
        desc[m.group(1)] = m.group(2)
questions = {k: {"type": "noul", "instructions": f"Does this ad copy use this device? {k}: {desc[k]}"} for k in tag.KEYS}

items = tag.load_items()
gold = tag.load_tags()["items"]
pairs = [(rid, it["text"], set(gold[rid]["devices"])) for rid, it in items.items()
         if rid in gold and gold[rid].get("hash") == tag.text_hash(it["text"])]
random.Random(7).shuffle(pairs)
pairs = pairs[:N]
print(f"gold items matched: {len(pairs)}", flush=True)

from laya import Router  # noqa: E402
router = Router()
t0 = time.time(); router.predict("warmup", {"x": questions["stat"]}); print(f"load+warmup {time.time()-t0:.1f}s", flush=True)

tp = {k: 0 for k in tag.KEYS}; fp = dict(tp); fn = dict(tp); lat = []; rows = []
for rid, text, g in pairs:
    body = re.sub(r"\s+", " ", text[:tag.COPY_MAX]).strip()
    t = time.time(); r = router.predict(body, questions); lat.append(time.time() - t)
    probs = {k: r["answers"][k]["noul"] for k in tag.KEYS}
    pred = {k for k, p in probs.items() if p >= TH}
    print(f"{len(rows)+1}/{len(pairs)} {lat[-1]:.1f}s gold={sorted(g)} pred={sorted(pred)}", flush=True)
    rows.append({"id": rid, "gold": sorted(g), "pred": sorted(pred), "probs": probs, "model": r.get("routing", {}).get("model")})
    for k in tag.KEYS:
        tp[k] += k in pred and k in g; fp[k] += k in pred and k not in g; fn[k] += k not in pred and k in g
pathlib.Path(pathlib.Path(__file__).parent / "eval_mechanisms.jsonl").write_text("\n".join(json.dumps(x) for x in rows))

f = lambda a, b, c: (a / (a + b) if a + b else 0, a / (a + c) if a + c else 0)
print(f"\n{'device':15} {'P':>5} {'R':>5} {'F1':>5} gold")
for k in tag.KEYS:
    p, rc = f(tp[k], fp[k], fn[k]); f1 = 2*p*rc/(p+rc) if p+rc else 0
    print(f"{k:15} {p:5.2f} {rc:5.2f} {f1:5.2f} {tp[k]+fn[k]}")
T, F, M = sum(tp.values()), sum(fp.values()), sum(fn.values()); p, rc = f(T, F, M)
lat.sort()
print(f"\nmicro P={p:.2f} R={rc:.2f} F1={2*p*rc/(p+rc) if p+rc else 0:.2f} | items={len(pairs)} th={TH} | latency p50={lat[len(lat)//2]*1000:.0f}ms p95={lat[int(len(lat)*.95)]*1000:.0f}ms")
