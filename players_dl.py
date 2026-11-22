"""
players_dl.py  -  PILOT re-download player data (EPL 24/25 μονο).
Κραταει ανα παικτη: id, name, positionId, usualPosition, teamName, isGoalkeeper,
λεπτα, + τα per-player stats που χρειαζεται το player-rating pilot.
Γραφει players_EPL_2425.json (ΔΕΝ πειραζει τιποτα του κανονικου μοντελου). Resume.
"""
import urllib.request, json, gzip, time, os, sys
try: sys.stdout.reconfigure(encoding='utf-8')
except Exception: pass
hdr={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64)','Accept':'*/*','Referer':'https://www.fotmob.com/'}

NEED=['Minutes played','FotMob rating','Goals prevented','Saves','xGOT faced','High claim',
      'Tackles','Interceptions','Clearances','Blocks','Aerial duels won','Dribbled past',
      'Accurate crosses','Expected assists (xA)','Passes into final third',
      'Recoveries','Expected goals (xG)',
      'Total shots','Chances created','Big chances created',
      'Successful dribbles','Touches in opposition box',
      'xG Non-penalty','Expected goals on target (xGOT)','Big chances missed']

def get(url,tries=3):
    for i in range(tries):
        try:
            raw=urllib.request.urlopen(urllib.request.Request(url,headers=hdr),timeout=25).read()
            if raw[:2]==b'\x1f\x8b': raw=gzip.decompress(raw)
            return raw
        except Exception:
            if i==tries-1: raise
            time.sleep(1.5*(i+1))

def sval(o):
    if not isinstance(o,dict): return o
    s=o.get('stat',o)
    return s.get('value') if isinstance(s,dict) else s

def parse(mid):
    d=json.loads(get(f'https://www.fotmob.com/api/data/matchDetails?matchId={mid}'))
    ps=d.get('content',{}).get('playerStats',{})
    out=[]
    for k,v in ps.items():
        flat={}
        for grp in (v.get('stats') or []):
            for name,obj in (grp.get('stats') or {}).items():
                flat[name]=sval(obj)
        stats={n:flat.get(n) for n in NEED}
        out.append({'id':v.get('id'),'name':v.get('name'),'teamName':v.get('teamName'),
                    'positionId':v.get('positionId'),'usualPosition':v.get('usualPosition'),
                    'isGoalkeeper':v.get('isGoalkeeper'),'stats':stats})
    return out

key='EPL_2425'
mids=json.load(open('match_index.json'))[key]
out_path='players_EPL_2425.json'
done=json.load(open(out_path,encoding='utf-8')) if os.path.exists(out_path) else {}
todo=[m for m in mids if str(m) not in done]
print(f"{key}: {len(done)} ηδη, {len(todo)} απομενουν")
err=0
for n,mid in enumerate(todo,1):
    try:
        done[str(mid)]=parse(mid)
        if n==1:
            vd=[p for p in done[str(mid)] if p['name']=='Virgil van Dijk']
            print("  δειγμα (Van Dijk):", json.dumps(vd[0],ensure_ascii=False)[:300] if vd else done[str(mid)][0]['name'])
    except Exception as e:
        err+=1
        if err<=5: print(f"  err {mid}: {type(e).__name__} {str(e)[:50]}")
    if n%50==0:
        json.dump(done,open(out_path,'w')); print(f"  ...{n}/{len(todo)} (err {err})")
    time.sleep(0.1)
json.dump(done,open(out_path,'w'))
nplayers=sum(len(v) for v in done.values())
print(f"DONE: {len(done)} ματς, {nplayers} player-records, errors {err}")
