"""Pure metrics over normalised ClickUp data. No I/O. Everything split img/vid; backlog never counts."""
import collections
import config as C
import outputs as O

def people(t):
    s = set()
    for a in t.get("assignees", []):
        if a.get("id") in C.U2C: s.add(C.U2C[a["id"]])
    for f in t.get("custom_fields", []):
        if f.get("id") in (C.F_VIDEO_EDITOR, C.F_DESIGNER) and f.get("value"):
            for u in f["value"]:
                if u.get("id") in C.U2C: s.add(C.U2C[u["id"]])
    return s
def cf(t, fid):
    for f in t.get("custom_fields", []):
        if f.get("id") == fid: return f
def dtype(t):
    f = cf(t, C.F_DELIVERABLE_TYPE)
    if not f or f.get("value") is None: return "?"
    opts = {o["orderindex"]: o["name"] for o in (f.get("type_config") or {}).get("options", [])}
    return opts.get(f["value"], "?")
def kind(t):
    d = dtype(t).lower(); n = t.get("name", "").lower()
    return "img" if any(k in d for k in ("image", "static")) or any(k in n for k in ("_img", "image", "static")) else "vid"
def status(t): return (t.get("status") or {}).get("status", "").lower()
def entries(hist_entry):
    """time_in_status payload -> sorted [(since_ms, status)] incl. current status."""
    h = hist_entry or {}; out = []
    for s in h.get("status_history", []):
        out.append((int((s.get("total_time") or {}).get("since") or 0), s["status"].lower()))
    cs = h.get("current_status")
    if cs: out.append((int((cs.get("total_time") or {}).get("since") or 0), cs["status"].lower()))
    return sorted(out)
def finished_at(ev):
    """ms of FIRST entry into any handoff status, or None. Bounce-backs never re-count."""
    f = [ts for ts, s in ev if s in C.HANDOFF]
    return min(f) if f else None
def tracked_in(intervals, ws, we):
    """intervals: [(uid, start, end, source)] -> {code: hours}, booked to the week of the START."""
    per = collections.Counter()
    for uid, s, e, _ in intervals:
        if uid in C.U2C and ws <= s <= we: per[C.U2C[uid]] += (e - s) / 3.6e6
    return per
def est_h(t): return (t.get("time_estimate") or 0) / 3.6e6

def compute(tasks, hist, intervals, ws, we, nws, nwe, air_counter=None):
    """tasks: list; hist: {id: time_in_status}; intervals: {id: [(uid,s,e,src)]}; windows in ms."""
    K = {"vid": collections.Counter(), "img": collections.Counter()}
    est = collections.Counter(); tracked_k = collections.Counter(); nf_rounds = collections.Counter()
    per = collections.defaultdict(lambda: collections.Counter()); queue = {"vid": collections.Counter(), "img": collections.Counter()}
    openp = collections.defaultdict(collections.Counter); proj = {"vid": collections.Counter(), "img": collections.Counter()}
    finished, air_notes = [], []; tr_fin = 0.0; tr_unfin = 0.0
    for t in tasks:
        ppl = people(t)
        if not ppl: continue
        k = kind(t); st = status(t); ev = entries(hist.get(t["id"])); ivs = intervals.get(t["id"], [])
        wk = [(ts, s) for ts, s in ev if ws <= ts <= we]
        tr = tracked_in(ivs, ws, we); trh = sum(tr.values())
        for code, h in tr.items(): per[code]["tracked"] += h
        tracked_k[k] += trh
        if (wk or trh) and st != C.S_BACKLOG: K[k]["active"] += 1
        fa = finished_at(ev); isfin = fa is not None and ws <= fa <= we
        if isfin:
            K[k]["finished"] += 1; e = est_h(t); est[k] += e; tr_fin += trh
            out = O.output_line(t); note = None
            if out is None:
                link = (cf(t, C.F_FILE_LINK) or {}).get("value")
                out, err = (air_counter(link, k) if air_counter and link else (0, "no link"))
                note = f"{t.get('custom_id')}: no OUTPUT line, Air={out}" + (f" ({err})" if err else "")
                air_notes.append(note)
            K[k]["output"] += out or 0
            for p in ppl: per[p]["fin_" + k] += 1; per[p]["est"] += e / len(ppl)
            finished.append({"id": t.get("custom_id") or t["id"], "kind": k, "est": e, "tracked": trh, "people": sorted(ppl),
                             "output": out, "handoff_ms": fa, "status": st, "type": dtype(t), "name": t.get("name")})
        else:
            tr_unfin += trh
        if any(s == C.S_LIVE for _, s in wk): K[k]["started"] += 1
        r = sum(1 for _, s in wk if s == C.S_FIX)
        if r: K[k]["nf_tasks"] += 1; nf_rounds[k] += r
        if st in (C.S_QUEUE, C.S_LIVE, "cs review", C.S_FIX):
            queue[k][st] += 1
            for p in ppl: openp[p][f"{k}:{st}"] += 1
        # projection for next week (planned at run time: nothing is done yet)
        if fa is None:  # never handed off = still the editor's work
            due = int(t.get("due_date") or 0)
            if st in (C.S_LIVE, C.S_FIX): proj[k]["mid"] += 1
            elif st == C.S_QUEUE and nws <= due <= nwe: proj[k]["todo_due"] += 1
    for k in K:
        K[k]["est_h"] = round(est[k], 1); K[k]["tracked_h"] = round(tracked_k[k], 1)
        K[k]["rev_rounds"] = round(nf_rounds[k] / K[k]["finished"], 1) if K[k]["finished"] else 0.0
        K[k]["proj"] = round(sum(proj[k][s] * C.PROJ_W[s] for s in C.PROJ_W), 0)
        K[k]["proj_parts"] = dict(proj[k]); K[k]["queue"] = dict(queue[k])
    return {"kinds": {k: dict(v) for k, v in K.items()}, "per": {p: dict(c) for p, c in per.items()},
            "open": {p: dict(c) for p, c in openp.items()}, "finished": finished, "air_notes": air_notes,
            "tracked_total": round(sum(tracked_k.values()), 1), "tracked_finished": round(tr_fin, 1),
            "tracked_unfinished": round(tr_unfin, 1), "est_finished": round(sum(est.values()), 1)}
