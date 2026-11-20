"""Usage from every request in the session transcripts (read-only), last N days.

Prices each deduplicated API request from its own token counts, so sessions that never wrote
a cost record and all subagent runs are included. Groups a session's subagent files with it.
"""
import collections
import glob
import json
import os
import re
import sys
import time

ROOT = os.path.expanduser("~/.claude/projects")
DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 14
CUT = time.time() - DAYS * 86400
CUT_ISO = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(CUT))
# $ per million tokens: (input, output, cache read). Cache write = 2.0x input (1h) or 1.25x input (5m).
PRICE = {"fable-5-1": (10, 50, 0.25), "fable-5-2": (8, 40, 0.20), "fable-5": (10, 50, 0.25), "opus-5-5": (4, 20, 0.20),
         "opus": (4, 20, 0.20), "sonnet": (3, 15, 0.30), "haiku": (1, 5, 0.10)}


def price_for(model):
    m = (model or "").replace("claude-", "")
    for k in ("fable-5-1", "fable-5-2", "fable-5", "opus-5-5", "opus", "sonnet", "haiku"):
        if m.startswith(k):
            return PRICE[k]
    return None


def first_text(msg):
    c = msg.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        for b in c:
            if isinstance(b, dict) and b.get("type") == "text":
                return b.get("text", "")
    return ""


def session_key(path):
    rel = os.path.relpath(path, ROOT).split(os.sep)
    if len(rel) >= 3:          # project/session/subagents/x.jsonl
        return rel[0] + "/" + rel[1], True
    return rel[0] + "/" + rel[1][:-6], False


S = collections.defaultdict(lambda: dict(cost=0.0, main=0.0, sub=0.0, reqs=0, sub_reqs=0, prompt="", entry=None, model=collections.Counter(),
                                         effort=collections.Counter(), ctx_sum=0, first_ts=None, cost_state=None, sub_files=0))
seen = set()
by_day = collections.Counter(); by_model = collections.Counter(); by_eff = collections.Counter(); by_bucket = collections.Counter()
parts = collections.Counter(); unpriced = collections.Counter()
files = [f for f in glob.glob(os.path.join(ROOT, "**", "*.jsonl"), recursive=True) if os.path.getmtime(f) >= CUT]
files.sort(key=lambda f: (session_key(f)[1], f))      # main files first
for f in files:
    key, is_sub = session_key(f)
    s = S[key]
    if is_sub:
        s["sub_files"] += 1
    with open(f, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"type":"assistant"' in line:
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("type") != "assistant":
                    continue
                ts = d.get("timestamp") or ""
                msg = d.get("message") or {}
                mid = msg.get("id")
                if not mid or mid in seen:
                    continue
                seen.add(mid)
                if not is_sub and s["entry"] is None:
                    s["entry"] = d.get("entrypoint")
                if ts < CUT_ISO:
                    continue
                u = msg.get("usage") or {}
                p = price_for(msg.get("model"))
                if not p:
                    if msg.get("model") != "<synthetic>":
                        unpriced[msg.get("model")] += 1
                    continue
                pin, pout, pread = p
                cc = u.get("cache_creation") or {}
                w1h = cc.get("ephemeral_1h_input_tokens")
                w5m = cc.get("ephemeral_5m_input_tokens")
                cw = u.get("cache_creation_input_tokens") or 0
                if w1h is None and w5m is None:
                    w1h, w5m = cw, 0
                out = u.get("output_tokens") or 0
                think = (u.get("output_tokens_details") or {}).get("thinking_tokens") or 0
                rd = u.get("cache_read_input_tokens") or 0
                inp = u.get("input_tokens") or 0
                c_out = out * pout / 1e6
                c_read = rd * pread / 1e6
                c_write = ((w1h or 0) * 2.0 * pin + (w5m or 0) * 1.25 * pin) / 1e6
                c_in = inp * pin / 1e6
                c = c_out + c_read + c_write + c_in
                side = is_sub or bool(d.get("isSidechain"))
                s["cost"] += c
                s["sub" if side else "main"] += c
                s["sub_reqs" if side else "reqs"] += 1
                s["model"][msg.get("model")] += c
                s["effort"][str(d.get("effort"))] += c
                ctx = inp + rd + cw
                s["ctx_sum"] += ctx
                if s["first_ts"] is None or ts < s["first_ts"]:
                    s["first_ts"] = ts
                by_day[ts[:10]] += c
                by_model[(msg.get("model"), "subagent" if side else "main")] += c
                by_eff[str(d.get("effort"))] += c
                b = "<100k" if ctx < 100_000 else "100-200k" if ctx < 200_000 else "200-400k" if ctx < 400_000 else ">400k"
                by_bucket[b] += c
                parts["thinking output"] += min(think, out) * pout / 1e6
                parts["visible output"] += max(out - think, 0) * pout / 1e6
                parts["cache reads"] += c_read
                parts["cache writes"] += c_write
                parts["uncached input"] += c_in
            elif not is_sub and not s["prompt"] and '"type":"user"' in line:
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("type") == "user" and not d.get("isSidechain"):
                    s["prompt"] = first_text(d.get("message") or {})
                    s["entry"] = s["entry"] or d.get("entrypoint")
            elif not is_sub and '"type":"cost-state"' in line:
                try:
                    s["cost_state"] = float(json.loads(line).get("totalCostUSD") or 0)
                except Exception:
                    pass


def classify(s, key):
    p = s["prompt"][:8000]
    m = re.search(r"\[#([\w-]+) recent messages\]", p)
    if m or "[Latest request addressed to you]" in p:
        return "discord:" + (m.group(1) if m else "?")
    cont = p.lstrip().startswith("This session is being continued")
    if s["entry"] == "cli":
        return "terminal" + (" (continued)" if cont else "")
    if cont:
        return "bot or headless (continued after compaction)"
    if s["entry"] == "sdk-cli":
        return "cron/headless"
    return s["entry"] or "unknown"


tot = sum(s["cost"] for s in S.values())
sub = sum(s["sub"] for s in S.values())
print(f"last {DAYS} days | sessions with spend: {sum(1 for s in S.values() if s['cost'] > 0)} | requests: {sum(s['reqs'] + s['sub_reqs'] for s in S.values()):,}")
print(f"API-equivalent spend ${tot:,.0f} | main threads ${tot - sub:,.0f} | subagents ${sub:,.0f} ({100 * sub / tot:.0f}%) | unpriced models {dict(unpriced)}")
missing = [s for s in S.values() if s["cost"] > 1 and s["cost_state"] is None]
print(f"sessions with spend but no cost record: {len(missing)} worth ${sum(s['cost'] for s in missing):,.0f}")

print("\n== by surface ==")
agg = collections.defaultdict(lambda: [0, 0.0, 0.0])
for k, s in S.items():
    if s["cost"] <= 0:
        continue
    a = agg[classify(s, k)]
    a[0] += 1; a[1] += s["cost"]; a[2] += s["sub"]
for k, (n, c, sb) in sorted(agg.items(), key=lambda kv: -kv[1][1]):
    print(f"{k:46} sessions={n:4d} ${c:7.0f} {100 * c / tot:5.1f}%  of which subagents ${sb:6.0f}")

print("\n== by model and role ==")
for (m, role), c in by_model.most_common(12):
    print(f"{str(m):30} {role:9} ${c:7.0f} {100 * c / tot:5.1f}%")
print("\n== by effort ==")
for k, c in by_eff.most_common():
    print(f"effort={k:8} ${c:7.0f} {100 * c / tot:5.1f}%")
print("\n== by context size of the request ==")
for k in ("<100k", "100-200k", "200-400k", ">400k"):
    print(f"{k:9} ${by_bucket[k]:7.0f} {100 * by_bucket[k] / tot:5.1f}%")
print("\n== what the spend is made of ==")
for k, c in parts.most_common():
    print(f"{k:16} ${c:7.0f} {100 * c / tot:5.1f}%")
print("\n== by day (UTC) ==")
print("  ".join(f"{k[5:]} ${by_day[k]:.0f}" for k in sorted(by_day)))

print("\n== top 14 sessions (parent + its subagents) ==")
for k, s in sorted(S.items(), key=lambda kv: -kv[1]["cost"])[:14]:
    pr = re.sub(r"\s+", " ", s["prompt"])
    m = re.search(r"\[Latest request addressed to you\]\s*(.{0,60})", pr)
    label = (m.group(1) if m else pr[:60])
    n = s["reqs"] + s["sub_reqs"]
    mdl = s["model"].most_common(1)[0][0].replace("claude-", "") if s["model"] else "?"
    eff = s["effort"].most_common(1)[0][0] if s["effort"] else "?"
    print(f"${s['cost']:7.0f} sub=${s['sub']:6.0f} reqs={n:5d} avg_ctx={s['ctx_sum'] // max(n, 1):8,d} {mdl[:12]:12} {eff:6} {classify(s, k)[:24]:24} {(s['first_ts'] or '')[:10]} | {label}")
