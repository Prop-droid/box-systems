#!/usr/bin/env python3
"""Combination-suggestion report (Tomas, 2026-08-19).

Three sections:
  1. Best hooks last 7 days / last 30 days (donor pool).
  2. Videos with good spend but weak hooks (transplant targets, 30d).
  3. Combination suggestions: which donor hook to test on which target body,
     same-angle donors preferred.

Deterministic: bq only, no LLM. Usage: report.py [YYYY-MM-DD end-date]
Writes reports/combination-<date>.md and prints it.
"""
import json, os, subprocess, sys, datetime, statistics, pathlib

HERE = pathlib.Path(__file__).resolve().parent
SQL = (HERE / "per_ad.sql").read_text()

WK_MIN_SPEND = float(os.environ.get("WK_MIN_SPEND", 150))   # weekly donor floor
MO_MIN_SPEND = float(os.environ.get("MO_MIN_SPEND", 500))   # monthly donor floor
TGT_MIN_SPEND = float(os.environ.get("TGT_MIN_SPEND", 1000))  # target floor (30d)
N_WK, N_MO, N_TGT, N_SUGG = 10, 10, 12, 3


def bq(frm, to):
    q = SQL.replace("@from", frm).replace("@to", to)
    env = dict(os.environ, GOOGLE_APPLICATION_CREDENTIALS=os.path.expanduser(
        "~/.config/gcloud/ejam-dwh-sa.json"))
    out = subprocess.run(
        ["bq", "query", "--use_legacy_sql=false", "--format=json", "--quiet",
         "--max_rows=1000"],
        input=q, capture_output=True, text=True, env=env, timeout=300)
    if out.returncode != 0:
        sys.exit(f"bq failed ({frm}..{to}): {out.stderr[-500:]}")
    rows = json.loads(out.stdout or "[]")
    for r in rows:
        for k in ("spend", "hook_pct", "tpi_pct", "cm_roas", "vlen"):
            r[k] = float(r[k]) if r.get(k) not in (None, "") else None
        r["impr"] = int(float(r["impr"]))
    return [r for r in rows if r["hook_pct"] is not None]


def concept(sh):
    return "-".join(sh.split("-")[:2])   # SH-16180-1 -> SH-16180


def ctype(r):
    d = (r.get("descriptor") or "").upper()
    if "_WL" in d or d.startswith("WL") or "UGC" in d or "TIKTOK" in d:
        return "WL/UGC"
    return "produced"


def desc_txt(r, width=55):
    t = (r.get("descriptor") or "").strip().replace("\n", " ")
    if t.lower().startswith("http"):   # some ad_names carry the LP URL there
        t = ""
    return (t[: width - 1] + "…") if len(t) > width else (t or "—")


def row(r):
    return (f"| {r['sh']} | {desc_txt(r)} | {r['hook_pct']:.1f}% | "
            f"{r['tpi_pct']:.1f}% | ${r['spend']:,.0f} | {r['cm_roas']:.2f} |")


HDR = ("| SH | Creative | Hook | TPI | Spend | CM-ROAS |\n"
       "|---|---|---|---|---|---|")


def main():
    end = datetime.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else \
        datetime.date.today() - datetime.timedelta(days=1)
    wk = bq(str(end - datetime.timedelta(days=6)), str(end))
    mo = bq(str(end - datetime.timedelta(days=29)), str(end))

    wk_don = sorted([r for r in wk if r["spend"] >= WK_MIN_SPEND],
                    key=lambda r: -r["hook_pct"])[:N_WK]
    mo_pool = [r for r in mo if r["spend"] >= MO_MIN_SPEND]
    mo_don = sorted(mo_pool, key=lambda r: -r["hook_pct"])[:N_MO]

    med = statistics.median([r["hook_pct"] for r in mo_pool]) if mo_pool else 0
    targets = sorted([r for r in mo if r["spend"] >= TGT_MIN_SPEND
                      and r["hook_pct"] < med], key=lambda r: -r["spend"])[:N_TGT]

    # donor pool = union of both leaderboards, best hook first, minus targets
    donors, seen = [], {t["sh"] for t in targets}
    for r in sorted(mo_don + wk_don, key=lambda r: -r["hook_pct"]):
        if r["sh"] not in seen:
            donors.append(r); seen.add(r["sh"])

    L = [f"# SHA Combination Suggestion Report — {end} (windows: 7d & 30d)", ""]
    L += [f"## Best hooks — last 7 days (spend ≥ ${WK_MIN_SPEND:.0f})", "", HDR]
    L += [row(r) for r in wk_don] or ["(none met the floor)"]
    L += ["", f"## Best hooks — last 30 days (spend ≥ ${MO_MIN_SPEND:.0f})", "", HDR]
    L += [row(r) for r in mo_don] or ["(none met the floor)"]
    L += ["", f"## Good spend, weak hook — 30d spend ≥ ${TGT_MIN_SPEND:.0f}, "
              f"hook below cohort median ({med:.1f}%)", "", HDR]
    L += [row(r) for r in targets] or ["(none — every big spender hooks fine)"]

    L += ["", "## Combination suggestions (test donor hook on target body)", ""]
    if not targets:
        L.append("Nothing to combine this window.")
    for t in targets:
        # sibling variations of the same concept aren't transplant donors —
        # the buyer would just shift budget to the sibling instead
        pool = [d for d in donors if concept(d["sh"]) != concept(t["sh"])]
        same = [d for d in pool if ctype(d) == ctype(t)]
        picks = (same + [d for d in pool if d not in same])[:N_SUGG]
        L.append(f"**{t['sh']}** (${t['spend']:,.0f} · {t['cm_roas']:.2f} CM-ROAS · "
                 f"hook {t['hook_pct']:.1f}% · {ctype(t)} · {desc_txt(t)}):")
        for d in picks:
            tag = "same type" if ctype(d) == ctype(t) else "cross-type"
            L.append(f"- ← **{d['sh']}** hook ({d['hook_pct']:.1f}% hook, {tag}): "
                     f"{desc_txt(d)}")
        L.append("")

    L += ["---", "Hook = 3s views ÷ impressions; TPI = ~15s quartile proxy ÷ impressions. "
          "Hook does NOT predict CM-ROAS in this account (r ≈ −0.1..−0.16) — these are "
          "attention transplants onto money-proven bodies, not ROAS predictions. "
          "Recut mandate: one hook swap = one cut."]

    md = "\n".join(L) + "\n"
    out = HERE / "reports" / f"combination-{end}.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(md)
    print(md)
    print(f"[saved] {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
