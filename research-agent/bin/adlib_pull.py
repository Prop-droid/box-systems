#!/home/tomas/.local/share/uv/tools/scrapling/bin/python
"""Meta Ad Library pull — Atria-compatible competitor swipe fallback.

Why: Atria's REST API answers 403 code 40302 ("This plan does not include the API
surface") since 2026-11-01, which killed the nightly competitor feed. The Meta Ad
Library web UI is public and renders fully under Camoufox (scrapling
StealthyFetcher, verified 2026-11-01), so this pulls the same active ads straight
from Meta for the curated brand set and writes the SAME files atria_swipe_pull.py
writes: atria-swipe-<date>-<slug>-plusN.jsonl (+ .md summary). monitor.sh steps
2-3, the lanes engine and the CCC Competitors tab (CURATED_RE) stay unchanged.

Interpreter: the scrapling uv tool env (scrapling 0.4.9 + camoufox):
    ~/.local/share/uv/tools/scrapling/bin/python
Usage:  adlib_pull.py m107585658730958 m112448499199569 ...   (id = "m" + FB page id)
Env:    ATRIA_OUT_DIR     output dir (default = the Atria swipe dir in ~/brain)
        ATRIA_RUN_DATE    YYYY-MM-DD (default today)
        ADLIB_SCROLLS     extra scroll loads per brand, ~30 ads each (default 3)
        ADLIB_TIMEOUT_MS  per-page Playwright timeout (default 90000)
        ADLIB_DEBUG_DIR   dump raw card text per brand here (debugging the parser)
        ATRIA_SCRIPT      path of atria_swipe_pull.py (angle taxonomy import)

Differences vs the Atria feed: media URLs are fbcdn (signed, expire after days);
`format` is video|image (no carousel detection); `variant_count` sums Meta's own
"N ads use this creative and text" per copy cluster; `start_date` is a date, not
a datetime. Records carry "source": "meta-ad-library".
"""
import json
import os
import re
import statistics
import sys
import time
import urllib.parse
from collections import Counter
from datetime import date, datetime
from pathlib import Path

OUT_DIR = Path(os.path.expanduser(os.environ.get(
    "ATRIA_OUT_DIR", "~/brain/projects/2026-06/competitor-ads-scrape/atria")))
SCROLLS = int(os.environ.get("ADLIB_SCROLLS", "3"))
TIMEOUT_MS = int(os.environ.get("ADLIB_TIMEOUT_MS", "90000"))
DEBUG_DIR = os.environ.get("ADLIB_DEBUG_DIR")

# Angle taxonomy + cluster helpers come from the Atria script (one source of truth).
ATRIA_SCRIPT = Path(os.path.expanduser(os.environ.get(
    "ATRIA_SCRIPT", "~/brain/.claude/skills/atria/scripts/atria_swipe_pull.py")))
if not Path(os.path.expanduser(os.environ.get("ATRIA_KEY_FILE", "~/.config/atria/key"))).exists():
    os.environ["ATRIA_KEY_FILE"] = "/dev/null"  # module reads the key at import; the API is never called here
sys.path.insert(0, str(ATRIA_SCRIPT.parent))
import atria_swipe_pull as asp  # noqa: E402

from scrapling.fetchers import StealthyFetcher  # noqa: E402

# Curated set (research-agent/monitor.conf). The page itself names the brand; this
# is the fallback when a brand renders zero cards.
KNOWN_NAMES = {
    "107585658730958": "Grüns", "112448499199569": "Oats Overnight", "178024832922517": "Seed",
    "109587824828077": "We Are Heylo", "185169218322380": "Pop Daddy Snacks",
    "1680529988890160": "SmartSweets", "100781548295457": "BelliWelli",
    "355249355465384": "Rotten Gummy Worms", "614717959176595": "Licorice.com",
    "162352551085006": "Olipop", "101077004856501": "Poppi",
    "310668346413198": "Goli", "107940537227344": "RYZE Superfoods",
}

URL = ("https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL"
       "&view_all_page_id={pid}&media_type=all&search_type=page"
       "&sort_data[direction]=desc&sort_data[mode]=relevancy_monthly_grouped")

CTA_WORDS = {
    "shop now", "learn more", "sign up", "get offer", "order now", "subscribe", "download",
    "buy now", "book now", "apply now", "contact us", "get quote", "watch more", "send message",
    "send whatsapp message", "install now", "use app", "listen now", "see menu", "donate now",
    "play game", "open link", "get showtimes", "request time", "get directions", "like page",
    "get tickets", "try it", "see more", "visit profile", "view profile", "watch video",
}
VIDEO_ERR = "sorry, we're having trouble playing this video."
NOISE = {"low impression count", "platforms", "open dropdown", "see ad details",
         "see summary details", "this ad has multiple versions", "active", "inactive",
         "sponsored"}
DOMAIN_RE = re.compile(r"^[A-Z0-9][A-Z0-9.-]*\.[A-Z]{2,}(/\S*)?$")

# Each ad card = the smallest ancestor of its "Library ID: n" node whose text also
# holds "Sponsored" (header + creative live in one card). Over-climbing into a
# container with several cards is caught by the Library-ID count.
JS_CARDS = r"""
() => {
  const idRe = /^Library ID:\s*\d+$/;
  const nodes = [...document.querySelectorAll('span,div')]
    .filter(e => e.children.length === 0 && idRe.test((e.textContent || '').trim()));
  const out = [];
  for (const n of nodes) {
    let card = n, prev = n;
    for (let i = 0; i < 16 && card.parentElement; i++) {
      prev = card; card = card.parentElement;
      const t = card.innerText || '';
      if ((t.match(/Library ID:/g) || []).length > 1) { card = prev; break; }
      if (t.includes('Sponsored')) break;
    }
    const links = [...card.querySelectorAll('a[href]')].map(a => a.href);
    const videos = [...card.querySelectorAll('video')].map(v => ({src: v.currentSrc || v.src || '', poster: v.poster || ''}));
    const imgs = [...card.querySelectorAll('img')]
      .map(i => ({src: i.currentSrc || i.src || '', w: i.naturalWidth || 0, h: i.naturalHeight || 0}))
      .filter(i => i.src && !i.src.startsWith('data:'));
    out.push({text: card.innerText || '', links, videos, imgs});
  }
  return out;
}
"""
JS_META = r"""
() => {
  const t = document.body ? document.body.innerText : '';
  const m = t.match(/~?\s*([\d,.]+)\s+results?\b/);
  return {total_text: m ? m[1] : null, title: document.title, has_login: /log in to facebook/i.test(t)};
}
"""


def log(msg):
    print(msg, flush=True)


def fetch_brand(pid):
    """Render the brand's Ad Library page under Camoufox, scroll, return (cards, meta)."""
    got = {}

    def count(page):
        # body can still be null right after navigation: never dereference it blindly
        try:
            return page.evaluate("((((document.body || {}).innerText) || '').match(/Library ID:/g) || []).length")
        except Exception:
            return 0

    def answered(page):
        try:
            return page.evaluate("/[0-9][0-9,.]*\\s+results?\\b/.test(((document.body || {}).innerText) || '')")
        except Exception:
            return False

    def act(page):
        for label in ("Allow all cookies", "Decline optional cookies"):
            try:
                btn = page.get_by_role("button", name=label)
                if btn.count():
                    btn.first.click(timeout=2000)
                    page.wait_for_timeout(800)
                    break
            except Exception:
                pass
        # No wait_for_function here: facebook.com's CSP forbids string eval under
        # Firefox/Juggler (EvalError). page.evaluate works, so poll instead. Ads
        # render ~8s after the shell loads.
        deadline = time.time() + 40
        seen = 0
        while time.time() < deadline:
            seen = count(page)
            if seen:
                break
            if answered(page):
                break  # "0 results": the page answered, there is nothing to read
            page.wait_for_timeout(1000)
        page.wait_for_timeout(1500)  # let the first batch finish painting
        seen = count(page)
        for _ in range(SCROLLS):
            if seen == 0:
                break
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.mouse.wheel(0, 20000)
            page.wait_for_timeout(2500)
            n = count(page)
            if n <= seen:
                page.wait_for_timeout(2500)
                n = count(page)
                if n <= seen:
                    break
            seen = n
        got["cards"] = page.evaluate(JS_CARDS)
        got["meta"] = page.evaluate(JS_META)
        return page

    r = StealthyFetcher.fetch(URL.format(pid=pid), headless=True,
                              page_action=act, timeout=TIMEOUT_MS, google_search=False)
    return r.status, got.get("cards") or [], got.get("meta") or {}


def parse_card(c, fallback_brand):
    text = c.get("text") or ""
    m = re.search(r"Library ID:\s*(\d+)", text)
    if not m:
        return None
    lib = m.group(1)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    start = None
    m = re.search(r"Started running on ([A-Z][a-z]{2} \d{1,2}, \d{4})", text)
    if m:
        try:
            start = datetime.strptime(m.group(1), "%b %d, %Y").date().isoformat()
        except ValueError:
            pass
    m = re.search(r"(\d+) ads use this creative and text", text)
    variants = int(m.group(1)) if m else 1

    sp = next((i for i, l in enumerate(lines) if l == "Sponsored"), None)
    creator = brand = None
    if sp is not None:
        if sp >= 3 and lines[sp - 2].lower() == "with":
            creator, brand = lines[sp - 3], lines[sp - 1]
        elif sp >= 1:
            brand = lines[sp - 1]
    after = lines[sp + 1:] if sp is not None else []

    cta_i = next((i for i in range(len(after) - 1, -1, -1) if after[i].lower() in CTA_WORDS), None)
    if cta_i is not None and cta_i > 0 and after[cta_i - 1].lower() == VIDEO_ERR:
        cta_i = None  # that "Learn more" belongs to the player error, the card has no button
    cta = after[cta_i] if cta_i is not None else None
    block = after[:cta_i] if cta_i is not None else after[:]

    clean, skip_next = [], False
    for l in block:
        low = l.lower()
        if skip_next and low == "learn more":
            skip_next = False
            continue
        skip_next = False
        if low == VIDEO_ERR:
            clean.append("\x00VIDEO")
            skip_next = True
            continue
        if low in NOISE or low.startswith("impressions:") or re.fullmatch(r"<?\d[\d,]*\+?", l):
            continue
        clean.append(l)
    dom_i = next((i for i, l in enumerate(clean) if l != "\x00VIDEO" and DOMAIN_RE.match(l)), None)
    vid_i = next((i for i, l in enumerate(clean) if l == "\x00VIDEO"), None)
    cut = dom_i if dom_i is not None else vid_i
    headline, desc = None, []
    if cut is not None:
        body = [l for l in clean[:cut] if l != "\x00VIDEO"]
        tail = [l for l in clean[cut + 1:] if l != "\x00VIDEO"]
        if tail:
            headline, desc = tail[0], tail[1:]
    else:
        body = clean[:]
        if cta and len(body) >= 2 and len(body[-1]) <= 90:
            headline = body.pop()

    links = c.get("links") or []
    link_url = None
    for h in links:
        if "l.facebook.com/l.php" in h:
            u = urllib.parse.parse_qs(urllib.parse.urlparse(h).query).get("u")
            if u:
                link_url = u[0]
                break
    if not link_url:
        link_url = next((h for h in links if "facebook.com" not in h and "instagram.com" not in h), None)

    media = [v.get("src") for v in (c.get("videos") or []) if (v.get("src") or "").startswith("http")]
    media += [v.get("poster") for v in (c.get("videos") or []) if v.get("poster")]
    media += [i["src"] for i in (c.get("imgs") or [])
              if i.get("src") and (i.get("w", 0) >= 200 or (i.get("w", 0) == 0 and "s60x60" not in i["src"]))]
    has_video = vid_i is not None or bool(c.get("videos"))
    return {
        "brand_name": brand or fallback_brand, "creator": creator, "platform_native_id": lib,
        "start_date": start, "variants": variants, "cta": cta, "title": headline or "",
        "body": "\n".join(body).strip(), "description": "\n".join(desc).strip() or None,
        "link_url": link_url, "media_urls": media[:4], "format": "video" if has_video else "image",
    }


def main():
    ids = [a[1:] if a.startswith("m") else a for a in sys.argv[1:]]
    if not ids:
        sys.exit("usage: adlib_pull.py m<page id> [m<page id> ...]")
    run_date = date.fromisoformat(os.environ.get("ATRIA_RUN_DATE") or date.today().isoformat())
    log(f"Pulling active ads from the Meta Ad Library for {len(ids)} brand(s)...")

    deduped, per_brand, first_name, failures = [], {}, None, 0
    for pid in ids:
        bid = "m" + pid
        t0 = time.time()
        try:
            status, cards, meta = fetch_brand(pid)
        except Exception as e:  # browser/launch failure for this brand only
            log(f"  {KNOWN_NAMES.get(pid, bid)}: FETCH ERROR {e}")
            failures += 1
            continue
        if DEBUG_DIR:
            Path(DEBUG_DIR).mkdir(parents=True, exist_ok=True)
            (Path(DEBUG_DIR) / f"{bid}.json").write_text(json.dumps({"meta": meta, "cards": cards}, ensure_ascii=False, indent=1))
        ads = [a for a in (parse_card(c, KNOWN_NAMES.get(pid)) for c in cards) if a]
        names = Counter(a["brand_name"] for a in ads if a["brand_name"])
        bname = names.most_common(1)[0][0] if names else KNOWN_NAMES.get(pid, bid)
        first_name = first_name or bname
        total_txt = (meta or {}).get("total_text")
        total = int(re.sub(r"[^\d]", "", total_txt)) if total_txt and re.sub(r"[^\d]", "", total_txt) else None
        if not ads:
            why = "login wall" if (meta or {}).get("has_login") else f"http {status}, {len(cards)} cards"
            log(f"  {bname}: 0 ads parsed ({why}, page says {total_txt or '?'} results) {time.time()-t0:.0f}s")
            if total:  # the page has ads we failed to read = a broken pull for this brand
                failures += 1
            per_brand[bname] = {"active": total or 0, "unique": 0}
            continue

        clusters = {}
        for a in ads:
            clusters.setdefault(asp.norm_body(a["body"]), []).append(a)
        unique = []
        for cluster in clusters.values():
            rep = cluster[0]
            angles = asp.tag_angles(f"{rep['title']} {rep['body']}")
            codes = sorted({c for c in (asp.extract_code({"body": a["body"], "title": a["title"]}) for a in cluster) if c})
            days = [(run_date - date.fromisoformat(a["start_date"])).days for a in cluster if a["start_date"]]
            unique.append({
                "brand_id": bid, "brand_name": bname,
                "id": "m" + rep["platform_native_id"],
                "platform_native_id": rep["platform_native_id"],
                "ad_library_url": f"https://www.facebook.com/ads/library/?id={rep['platform_native_id']}",
                "media_urls": rep["media_urls"],
                "format": rep["format"],
                "cta": rep["cta"],
                "title": rep["title"],
                "body": rep["body"],
                "link_url": rep["link_url"],
                "angles": angles,
                "winning_lane": bool(set(angles) & asp.WINNING_LANES),
                "variant_count": sum(a["variants"] for a in cluster),
                "sample_codes": codes[:8],
                "start_date": rep["start_date"], "end_date": None,
                "days_running": max(max(days), 0) if days else None,
                "creator": rep["creator"],
                "source": "meta-ad-library",
            })
        unique.sort(key=lambda x: x["variant_count"], reverse=True)
        deduped += unique
        per_brand[bname] = {"active": total if total is not None else len(ads), "unique": len(unique)}
        log(f"  {bname}: {len(ads)} cards (page says {total_txt or '?'} active) -> {len(unique)} unique  {time.time()-t0:.0f}s")

    if not deduped:
        sys.exit("FAIL: 0 active ads across all brands - treating as a broken pull, not a quiet day.")
    if failures and failures * 2 >= len(ids):
        sys.exit(f"FAIL: {failures}/{len(ids)} brands returned nothing readable - not writing a half-empty snapshot.")

    all_days = [a["days_running"] for a in deduped if a["days_running"] is not None]
    median_days = statistics.median(all_days) if all_days else 0
    threshold = max(60, 2 * median_days)
    for a in deduped:
        a["long_runner"] = bool(a["days_running"] and a["days_running"] >= threshold)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    today = run_date.isoformat()
    slug = re.sub(r"[^a-z0-9]+", "-", (first_name or ids[0]).lower()).strip("-")
    suffix = f"-{slug}" + (f"-plus{len(ids)-1}" if len(ids) > 1 else "")
    jsonl_path = OUT_DIR / f"atria-swipe-{today}{suffix}.jsonl"
    md_path = OUT_DIR / f"atria-swipe-{today}{suffix}.md"
    tmp = jsonl_path.with_suffix(".jsonl.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for ad in deduped:
            f.write(json.dumps(ad, ensure_ascii=False) + "\n")
    os.replace(tmp, jsonl_path)

    angle_counts = Counter(a for ad in deduped for a in ad["angles"])
    total = len(deduped)
    lines = [f"# Competitor swipe — {today} (Meta Ad Library, Atria API fallback)", "",
             f"Pulled active ads from {len(ids)} curated brand(s) straight from the Meta Ad Library; "
             f"{total} unique copy clusters after dedup. 'Active' = Meta's own result count for the page; "
             f"'Unique' = clusters among the newest ~{30 * (SCROLLS + 1)} ads read per brand.",
             "Angle tags are heuristic (keyword) and grounded in the Shameless ROAS-truth lanes (offer / urgency / usp win).",
             "", "## Per-brand", "", "| Brand | Active | Unique |", "|---|---|---|"]
    for bname, c in sorted(per_brand.items(), key=lambda x: -x[1]["unique"]):
        lines.append(f"| {bname} | {c['active']} | {c['unique']} |")
    lines += ["", "## Angle distribution (unique ads)", ""]
    for angle, n in angle_counts.most_common():
        flag = " (winning lane)" if angle in asp.WINNING_LANES else ""
        lines.append(f"- {angle}: {n} ({round(100*n/total)}%){flag}")
    long_runners = sorted([a for a in deduped if a.get("long_runner")], key=lambda x: -(x["days_running"] or 0))[:15]
    if long_runners:
        lines += ["", f"## Longevity outliers (active ≥{round(threshold)}d; pull median {round(median_days)}d)",
                  "_An ad still running this long past the category norm is one the competitor keeps paying for. Proven-winner proxy — swipe the mechanics first._", ""]
        for a in long_runners:
            lines.append(f"**{a['brand_name']}** · {a['days_running']}d · {a['variant_count']}× · [{a['format']}|{a['cta']}] · {', '.join(a['angles']) or 'untagged'}")
            lines.append(f"> {a['title'] or a['body'][:160]}")
            lines.append("")
    lines += ["", "## Most-pushed copy in the winning lanes (offer / urgency / USP)",
              "_Sorted by variant_count = how many ads run the same copy. High count = a bet the competitor is scaling._", ""]
    for a in [a for a in deduped if a["winning_lane"]][:15]:
        lines.append(f"**{a['brand_name']}** · {a['variant_count']}× · [{a['format']}|{a['cta']}] · {', '.join(a['angles'])}")
        lines.append(f"> {a['title']}")
        if a["body"]:
            lines.append(f"> {a['body'][:220].strip()}")
        lines.append("")
    bf = [a for a in deduped if "body_function" in a["angles"]][:10]
    if bf:
        lines += ["## Owned-language watch (competitors on body-function / not-a-laxative territory)", ""]
        for a in bf:
            lines.append(f"- **{a['brand_name']}** ({a['variant_count']}×): {a['title'] or a['body'][:120]}")
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    log(f"wrote {jsonl_path} ({total} clusters) + {md_path.name}")


if __name__ == "__main__":
    main()
