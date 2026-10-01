import json, os, re, urllib.request, urllib.parse
K=open(os.path.expanduser('~/.config/air/api_key')).read().strip()
W=open(os.path.expanduser('~/.config/air/workspace_id')).read().strip()
CU=open(os.path.expanduser('~/.config/clickup/pk')).read().strip()
def get(url, h):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=h)))
AH={'x-api-key':K,'x-air-workspace-id':W}
def children(pid, kind='boards'):
    out, cur = [], None
    while True:
        q={'parentBoardId':pid,'limit':100}
        if cur: q['cursor']=cur
        d=get(f'https://api.air.inc/v1/{kind}?'+urllib.parse.urlencode(q), AH)
        out+=d.get('data',[]); p=d.get('pagination') or {}
        if not p.get('hasMore'): return out
        cur=p['cursor']
PARENTS={'Static':'49651c6f-f1a0-4a8c-802c-33502dce29cc','Video':'21c7d681-8d09-45f2-bee3-4278ae69e074'}
allb=[]
for k,v in PARENTS.items():
    for b in children(v): b['_kind']=k; allb.append(b)
allb.sort(key=lambda b:b['createdAt'], reverse=True)
res=[]
for b in allb[:int(os.environ.get('N',20))]:
    r={'kind':b['_kind'],'created':b['createdAt'][:10],'title':b['title'],'id':b['id'],'files':[],'subs':[]}
    r['files']=[a['coverVersion']['fileName']+'.'+a['coverVersion']['ext'] for a in children(b['id'],'assets')]
    for s in children(b['id']):
        r['subs'].append({'title':s['title'],'files':[a['coverVersion']['fileName']+'.'+a['coverVersion']['ext'] for a in children(s['id'],'assets')]})
    m=re.match(r'(SH-\d+)',b['title'])
    if m:
        try:
            t=get(f'https://api.clickup.com/api/v2/task/{m.group(1)}?custom_task_ids=true&team_id=9011638245',{'Authorization':CU})
            r['task']=t['name']; fl=[f.get('value') for f in t['custom_fields'] if f['name']=='✨ File Link']
            r['filelink']=fl[0] if fl else None
            if r['filelink'] and '/a/' in r['filelink']:
                sh=r['filelink'].rstrip('/').split('/a/')[1].split('/')[0]
                d=get(f'https://api.air.inc/shorturl/{sh}',{}).get('data',{})
                r['filelink_board']=d.get('title')
        except Exception as e: r['task']=f'ERR {e}'
    res.append(r)
json.dump(res,open(os.path.expanduser('~/systems/air-upload/air_audit_recent.json'),'w'),indent=1)
for r in res:
    print(f"\n[{r['kind']} {r['created']}] {r['title']}")
    print(f"  task: {r.get('task')} | FileLink→ {r.get('filelink_board')} ({r.get('filelink')})")
    if r['files']: print(f"  files({len(r['files'])}): "+' | '.join(sorted(r['files'])[:3]))
    for s in r['subs']: print(f"  [{s['title']}]({len(s['files'])}): "+' | '.join(sorted(s['files'])[:2]))
