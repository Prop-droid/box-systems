#!/usr/bin/env python3
"""Laya (local Jev) yes/no flags over every SHA ad comment, before the Claude digest pass.

Ryze/Jev pattern: a keyword shortlist first (subscription, price), then one yes/no question per
comment, then three bands: AUTO >= 0.80 is counted as fact, REVIEW 0.55-0.80 is handed to Claude
to confirm, anything below is dropped. AUTO precision 2026-10-06 on 398 real comments: 46/50
(Laya alone gave subscription 1.00 for "Sucralose is a hard pass", hence the shortlist). Prints a markdown block for the prompt's {{FLAGS}} and
writes every flagged comment to out/flags-DATE.jsonl. Fail-soft: if Laya is down it prints a
one-line notice and exits 0, so the digest runs exactly as before.

Usage: flag_comments.py <comments.json from 01_comments.sql> <out.jsonl>
"""
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.expanduser("~/systems/lib"))
from decide import ask_batch  # noqa: E402

AUTO, REVIEW = 0.80, 0.55
FLAGS = {
    "adverse": ("Adverse reaction", "Does the commenter say or warn that eating these causes diarrhea, gas, bloating, stomach pain or other bad physical effects?"),
    "order_problem": ("Order / site problem", "Does the commenter report a problem buying or receiving an order, such as a broken link, error page, missing items, late delivery or no reply from support?"),
    "subscription": ("Subscription complaint", "Does the commenter complain about being signed up for a subscription, recurring orders, or paying extra shipping without one?"),
    "price": ("Price objection", "Does the commenter say the product is too expensive or poor value?"),
}
# Rules-first shortlist: only comments matching these are asked; the rest score 0.
SHORTLIST = {
    "subscription": re.compile(r"subscri|recurring|monthly|auto.?(ship|pay|renew)|every month|cancel", re.I),
    "price": re.compile(r"\$|pric|expens|cost|cheap|afford|pay|money|value|worth|deal", re.I),
}


def main() -> int:
    src, out = sys.argv[1], sys.argv[2]
    rows = [r for r in json.load(open(src)) if (r.get("comment_text") or "").strip()]
    texts = [r["comment_text"][:500] for r in rows]
    probs = [{k: 0.0 for k in FLAGS} for _ in rows]
    # Unfiltered flags share one batch pass; each shortlisted flag asks only its matches.
    groups = [([k for k in FLAGS if k not in SHORTLIST], list(range(len(rows))))]
    groups += [([k], [i for i, t in enumerate(texts) if rx.search(t)]) for k, rx in SHORTLIST.items()]
    for keys, idx in groups:
        if not idx:
            continue
        ans = ask_batch([texts[i] for i in idx], {k: {"type": "noul", "instructions": FLAGS[k][1]} for k in keys})
        if ans is None:
            print("(Laya flagger unavailable this run; estimate from the sample as usual.)")
            return 0
        for i, a in zip(idx, ans):
            probs[i].update({k: float(a[k]["noul"]) for k in keys})

    hits = collections.defaultdict(lambda: {"auto": [], "review": []})
    with open(out, "w") as f:
        for r, pr in zip(rows, probs):
            p = {k: round(v, 3) for k, v in pr.items()}
            band = {k: "auto" if v >= AUTO else "review" for k, v in p.items() if v >= REVIEW}
            for k, b in band.items():
                hits[k][b].append((p[k], r))
            if band:
                f.write(json.dumps({"d": r.get("d"), "cre": r.get("cre"), "likes": r.get("likes"),
                                    "text": r["comment_text"], "p": p, "band": band}) + "\n")

    print(f"Machine flags over ALL {len(rows)} sampled comments (local Laya model, ~90% precise at AUTO; "
          f"REVIEW items are unconfirmed, judge them yourself):")
    for k, (label, _) in FLAGS.items():
        auto, review = hits[k]["auto"], hits[k]["review"]
        cres = collections.Counter(r.get("cre") for _, r in auto if r.get("cre")).most_common(3)
        print(f"\n### {label}: {len(auto)} AUTO, {len(review)} REVIEW"
              + (f" | top cre: {', '.join(f'{c} ({n})' for c, n in cres)}" if cres else ""))
        for b, items in (("AUTO", auto), ("REVIEW", review)):
            for prob, r in sorted(items, key=lambda x: -x[0])[:8]:
                text = " ".join(r["comment_text"].split())[:220]
                print(f"- [{b} {prob:.2f}] {r.get('cre') or '-'}: \"{text}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
