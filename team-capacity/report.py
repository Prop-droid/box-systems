"""Plain-text report in Tomas's TOTAL TEAM PERFORMANCE shape, split VIDEO / IMAGE / TEAM. Insights via headless Claude with a deterministic fallback."""
import subprocess, os
import config as C, weeks as W
def _q(d, k): return d["kinds"][k]
def _queue(q):
    order = [C.S_QUEUE, C.S_LIVE, "cs review", C.S_FIX]
    return " • ".join(f"{s} {q[s]}" for s in order if q.get(s))
def _proj(k):
    p = k["proj_parts"]
    parts = [f"{p.get('mid', 0)} in progress not yet handed off", f"{p.get('todo_due', 0)} to-do due next week"]
    return f"~{int(k['proj'])} finished ({' + '.join(parts)})"
def render(sprint, ws, we, m, days, cap, gate_reverts, insights, label):
    V, I = _q(m, "vid"), _q(m, "img"); cap_total = sum(cap.values())
    off = [f"{C.NAMES[c]} out {len(d)} day(s) ({'; '.join(sorted({r for _, _, r in d}))})" for c, d in days.items() if d]
    per = sorted(C.POOL, key=lambda c: -(m["per"].get(c, {}).get("tracked", 0)))
    per_line = " • ".join(f"{c} {int(m['per'].get(c, {}).get('fin_vid', 0))} / {int(m['per'].get(c, {}).get('fin_img', 0))} / {m['per'].get(c, {}).get('tracked', 0):.1f}h of {cap[c]:.0f}h" for c in per)
    ratio = (m["tracked_finished"] / m["est_finished"]) if m["est_finished"] else 0
    L = [f"WEEK SPRINT {sprint} ({W.fmt_range(ws, we)})", "", "TOMAS – TOTAL TEAM PERFORMANCE", "", "Days-off", *(off or ["none logged"]), ""]
    for title, K in (("VIDEO", V), ("IMAGE", I)):
        unit = "videos" if title == "VIDEO" else "images"
        L += [title, f"Tasks with activity: {K.get('active', 0)}",
              f"Finished: {K.get('finished', 0)} • started: {K.get('started', 0)} • hit needs fixing: {K.get('nf_tasks', 0)}",
              f"Tracked: {K['tracked_h']}h • estimated on finished: {K['est_h']}h",
              f"Average revision rounds per finished task: ~{K['rev_rounds']}",
              f"Output: {K.get('output', 0)} {unit}",
              f"Queue now: {_queue(K['queue']) or 'empty'}",
              f"Projection next week: {_proj(K)}", ""]
    L += ["TEAM", f"Tracked vs capacity: {m['tracked_total']}h / {cap_total:.0f}h → {100 * m['tracked_total'] / cap_total:.0f}% used" if cap_total else "Tracked vs capacity: n/a",
          f"Finished tasks: {m['tracked_finished']}h tracked vs {m['est_finished']}h estimated → {ratio:.2f} actual/estimate",
          f"Hours on tasks not yet finished: {m['tracked_unfinished']}h (carries forward)",
          f"Finished total: {V.get('finished', 0) + I.get('finished', 0)}",
          f"Estimate reverts this week: {gate_reverts}", "",
          "Per person (video finished / image finished / tracked h of capacity)", per_line, ""]
    if m["air_notes"]: L += ["Output counted from Air (no OUTPUT line): " + "; ".join(m["air_notes"]), ""]
    L += ["INSIGHTS", insights.strip()]
    return "\n".join(L)
def fallback_insights(m, cap):
    V, I = _q(m, "vid"), _q(m, "img"); tot = sum(cap.values()) or 1
    over = [c for c, d in m["per"].items() if d.get("tracked", 0) > cap.get(c, C.CAP_H)]
    low = sorted(m["per"].items(), key=lambda x: x[1].get("tracked", 0))[:1]
    rev = "Video revisions high" if V["rev_rounds"] >= 0.7 else "Video revisions normal"
    return (f"Team at {100 * m['tracked_total'] / tot:.0f}% of capacity; over 36h: {', '.join(over) or 'nobody'}. "
            f"{rev} ({V['rev_rounds']} rounds) vs image {I['rev_rounds']}. "
            f"Lowest tracked: {low[0][0] if low else 'n/a'}.")
def claude_insights(report_body):
    prompt = ("You are writing the INSIGHTS block of a weekly creative-team report for Tomas (creative strategist). "
              "Below are the numbers. Write 3-4 plain sentences, no markdown, no bullets, no headers: what moved, where revisions cluster, "
              "where unfinished work clusters by person, who has free capacity. Use the 3-letter codes. Do not restate every number.\n\n" + report_body)
    try:
        p = subprocess.run([C.CLAUDE_BIN, "-p", "--model", "claude-fable-5"], input=prompt, capture_output=True, text=True, timeout=240)
        txt = p.stdout.strip()
        if p.returncode == 0 and 80 < len(txt) < 1500 and "#" not in txt[:3]: return txt
    except Exception: pass
    return None
def deliver(text, label, post_team, doc_id):
    os.makedirs(C.REPORT_DIR, exist_ok=True)
    path = os.path.join(C.REPORT_DIR, f"{label}.txt"); open(path, "w").write(text + "\n")
    notes = [f"saved {path}"]
    if post_team:
        p = subprocess.run([os.path.expanduser("~/systems/lib/discord-post.sh"), C.DISCORD_CHANNEL, C.DISCORD_TOKEN_VAR], input=text, capture_output=True, text=True, timeout=120)
        notes.append("discord #creative " + ("ok" if p.returncode == 0 else f"FAIL {p.stderr[-120:]}"))
    else:
        p = subprocess.run([os.path.expanduser("~/systems/lib/tg-notify.sh"), f"Team capacity {label} (Tomas-only preview)", text, "default"], capture_output=True, text=True, timeout=120)
        notes.append("ops-log preview " + ("ok" if p.returncode == 0 else f"FAIL {p.stderr[-120:]}"))
    if doc_id:
        p = subprocess.run([C.GWS, "docs", "+write", "--document", doc_id, "--text", "\n\n" + text + "\n"], capture_output=True, text=True, timeout=120)
        notes.append("doc append " + ("ok" if p.returncode == 0 else f"FAIL {p.stderr[-120:]}"))
    return notes
