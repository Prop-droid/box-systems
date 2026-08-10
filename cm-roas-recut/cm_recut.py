#!/usr/bin/env python3
"""Re-rank Shameless creative patterns by CONTRIBUTION-MARGIN ROAS, not spend.

Why: the winner archive ranks patterns by spend + graduated ClickUp status.
Spend is a proxy the media buyer sets; CM is the money. This recomputes the
pattern canon on CM-ROAS = (revenue + upsale - cogs - txfee - agency) / spend.

Inputs : BigQuery ejam-dwh.production.creative_dashboard (SA at ~/.config/gcloud/ejam-dwh-sa.json)
         ClickUp task names via local archive + REST fallback (~/.config/clickup/pk)
Outputs: <outdir>/bq_by_task.csv, pattern_cm.json, REPORT.md
Usage  : python3 cm_recut.py [--pivot 2026-07-21] [--since 2026-02-01] [--outdir DIR]
"""
import argparse, collections, csv, json, os, re, subprocess, sys, time
import urllib.request, concurrent.futures as cf

CU_DIR   = os.path.expanduser('~/brain/projects/2026-05/ClickUp Connection')
SA       = os.path.expanduser('~/.config/gcloud/ejam-dwh-sa.json')
CU_TOKEN = os.path.expanduser('~/.config/clickup/pk')
TEAM     = '9011638245'

# CM-ROAS numerator. Keep in sync with finance's definition if it ever changes.
CM_EXPR = ("SUM(revenue) + SUM(upsale_revenue) - SUM(cogs) "
           "- SUM(transaction_fee) - SUM(agency_fees)")

PATTERNS = [
 ("P1_retro_iteration",   r"retro|proven|mashup|hooktest|hook_test|iteration|_v\d"),
 ("P2_static_headline",   r"imagetest|headlinetest|layouttest|copytest|\bimg\b|static"),
 ("P3_offer_urgency",     r"offer|sale|discount|deal|clearance|freegift|free_gift|urgency|lastcall|bfcm|blackfriday|pricecut"),
 ("P4_reasonwhy_letter",  r"wearesorry|we_are_sorry|sorry|letter|warehouse|pallet|tariff|goodbye|finalclearance"),
 ("P5_fiber_comparison",  r"fiber|broccoli|26g|29g|fibre"),
 ("P6_body_disruption",   r"poop|bloat|constip|gut|regular|bathroom|brick|digest"),
 ("P7_toxic_breakup",     r"toxic|breakup|break_up|sweettooth|sweet_tooth"),
 ("P8_qvc_liveshopping",  r"qvc|liveshop|live_shop|homeshopping"),
 ("P9_founder_vsl",       r"founder|genetics|dadbod|dad_bod|confession|\bvsl\b"),
 ("P11_glp1_weightloss",  r"glp|glp1|weightloss|weight_loss|\bwl\b|semaglutide|ozempic"),
 ("P12_ugc_whitelisting", r"ugc|whitelist|\bwl_|tiktok|creator|spark|influencer"),
 ("P13_social_proof",     r"review|amazon|target|sellout|sold_out|testimonial|socialproof|proof"),
 ("P14_seasonal",         r"nynm|newyear|new_year|christmas|xmas|halloween|valentine|carnival|easter|mothersday|fathersday|4thofjuly|memorial|laborday|summer|fall|backtoschool"),
 ("X_lowcal_taste",       r"lowcal|low_cal|lowcalorie|taste|candy|guiltfree|guilt_free|sweet|flavor|dessert|treat|snack"),
]
COMP = [(k, re.compile(p, re.I)) for k, p in PATTERNS]


def bq_by_task(since, pivot, out_csv):
    sql = f"""
SELECT clickup_project,
       IF(dt >= '{pivot}', 'post', 'pre') AS win,
       ROUND(SUM(spend),2) AS spend,
       ROUND(SUM(revenue),2) AS revenue,
       ROUND({CM_EXPR},2) AS cm,
       ROUND(SUM(orders),1) AS orders,
       ROUND(SUM(IF(asset_type='VIDEO', spend, 0)),2) AS video_spend
FROM `ejam-dwh.production.creative_dashboard`
WHERE brand='SHA' AND dt >= '{since}' AND spend > 0
GROUP BY 1,2 HAVING spend >= 200 ORDER BY spend DESC"""
    env = dict(os.environ, GOOGLE_APPLICATION_CREDENTIALS=SA)
    with open(out_csv, 'w') as fh:
        subprocess.run(['bq', '--project_id=ejam-dwh', 'query', '--use_legacy_sql=false',
                        '--format=csv', '--max_rows=20000', sql],
                       check=True, stdout=fh, env=env)
    return list(csv.DictReader(open(out_csv)))


def load_names(ids, cache):
    """Local archive first, ClickUp REST for the rest. Cached to <outdir>/names_all.json."""
    if os.path.exists(cache):
        return json.load(open(cache))
    names = {}
    for f in ('tasks_since_2025-09-30.jsonl', 'winners.jsonl'):
        p = os.path.join(CU_DIR, f)
        if not os.path.exists(p):
            continue
        for line in open(p):
            d = json.loads(line)
            names[d['custom_id']] = {'name': d.get('name', ''),
                                     'status': (d.get('status') or '').lower()}
    todo = [i for i in ids if i not in names]
    token = open(CU_TOKEN).read().strip()

    def get(cid):
        url = (f'https://api.clickup.com/api/v2/task/{cid}'
               f'?custom_task_ids=true&team_id={TEAM}&include_subtasks=false')
        req = urllib.request.Request(url, headers={'Authorization': token})
        for a in range(3):
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    d = json.load(r)
                    return cid, {'name': d.get('name', ''),
                                 'status': (d.get('status') or {}).get('status', '').lower()}
            except Exception:
                if a == 2:
                    return cid, None
                time.sleep(1.5 * (a + 1))

    if todo:
        print(f'  fetching {len(todo)} task names from ClickUp...', file=sys.stderr)
        with cf.ThreadPoolExecutor(5) as ex:
            for cid, rec in ex.map(get, todo):
                if rec:
                    names[cid] = rec
    json.dump(names, open(cache, 'w'), indent=0)
    return names


def rank(rows, names, win, winners_only):
    agg = collections.defaultdict(lambda: collections.defaultdict(float))
    tot = cmtot = 0.0
    seen = set()
    for r in rows:
        if r['win'] != win:
            continue
        cid = r['clickup_project']
        rec = names.get(cid)
        if not re.match(r'^SH-\d+$', cid) or not rec or not rec.get('name'):
            continue
        if winners_only and 'winner' not in (rec.get('status') or ''):
            continue
        sp, cm, rev = float(r['spend']), float(r['cm']), float(r['revenue'])
        tot += sp; cmtot += cm; seen.add(cid)
        name = rec['name'].replace(' ', '_')
        for k, rx in COMP:
            if rx.search(name):
                a = agg[k]; a['spend'] += sp; a['cm'] += cm; a['rev'] += rev; a['n'] += 1
    base = cmtot / tot if tot else 0
    out = [dict(pattern=k, tasks=int(a['n']), spend=round(a['spend']),
                roas=round(a['rev'] / a['spend'], 3), cm_roas=round(a['cm'] / a['spend'], 3),
                vs_base=round(a['cm'] / a['spend'] - base, 3))
           for k, a in agg.items() if a['spend'] > 0]
    out.sort(key=lambda x: -x['cm_roas'])
    return {'window': win, 'winners_only': winners_only, 'tasks': len(seen),
            'spend': round(tot), 'baseline_cm_roas': round(base, 3), 'patterns': out}


def status_split(rows, names):
    b = collections.defaultdict(lambda: collections.defaultdict(float))
    for r in rows:
        s = (names.get(r['clickup_project']) or {}).get('status') or ''
        lane = ('WINNER' if 'winner' in s else 'LOSER' if 'loser' in s
                else 'TESTING' if 'testing' in s else 'OTHER')
        a = b[(lane, r['win'])]
        a['spend'] += float(r['spend']); a['cm'] += float(r['cm'])
        a['rev'] += float(r['revenue']); a['n'] += 1
    return {f'{k[0]}|{k[1]}': dict(tasks=int(v['n']), spend=round(v['spend']),
                                   roas=round(v['rev'] / v['spend'], 3),
                                   cm_roas=round(v['cm'] / v['spend'], 3))
            for k, v in b.items() if v['spend'] > 0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pivot', default='2026-07-21', help='candy-first positioning pivot date')
    ap.add_argument('--since', default='2026-02-01')
    ap.add_argument('--outdir', default=os.path.expanduser('~/brain/projects/2026-08/cm-roas-recut'))
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)

    print('[1/3] BigQuery per-task CM pull', file=sys.stderr)
    rows = bq_by_task(a.since, a.pivot, os.path.join(a.outdir, 'bq_by_task.csv'))
    ids = sorted({r['clickup_project'] for r in rows if re.match(r'^SH-\d+$', r['clickup_project'])})

    print('[2/3] resolve task names', file=sys.stderr)
    names = load_names(ids, os.path.join(a.outdir, 'names_all.json'))

    print('[3/3] rank patterns by CM-ROAS', file=sys.stderr)
    res = {'generated_for': {'since': a.since, 'pivot': a.pivot},
           'cm_roas_formula': '(revenue + upsale_revenue - cogs - transaction_fee - agency_fees) / spend',
           'status_split': status_split(rows, names),
           'cuts': [rank(rows, names, w, wo) for w in ('pre', 'post') for wo in (False, True)]}
    json.dump(res, open(os.path.join(a.outdir, 'pattern_cm.json'), 'w'), indent=1)

    for c in res['cuts']:
        tag = 'winners-only' if c['winners_only'] else 'all-tasks'
        print(f"\n=== {c['window']} / {tag}: {c['tasks']} tasks, ${c['spend']:,}, "
              f"baseline CM-ROAS {c['baseline_cm_roas']}")
        for p in c['patterns']:
            print(f"  {p['pattern']:24}{p['tasks']:>5}{p['spend']:>11,}"
                  f"{p['roas']:>8.3f}{p['cm_roas']:>9.3f}{p['vs_base']:>+9.3f}")
    print(f"\nwrote {a.outdir}/pattern_cm.json")


if __name__ == '__main__':
    main()
