"""Κατεβαζει shot-level xG απο FotMob για τα 402 ευρωπαικα ματς 25/26 (CL/EL/Conference),
matched στα Excel ματς με fuzzy (date+ονοματα). Αποθηκευει euro_shots.json."""
import urllib.request, json, gzip, time, sys, pandas as pd, unicodedata, re, os
sys.stdout.reconfigure(encoding='utf-8')
HDR={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36','Accept':'*/*','Referer':'https://www.fotmob.com/'}
OUT=r'C:\Users\User\AppData\Local\Temp\claude\C--Users-User-Desktop-Betting-Model\b46da584-c209-452b-8ff3-da29760f9223\scratchpad\euro_shots.json'
def get(url,tries=3):
    for i in range(tries):
        try:
            raw=urllib.request.urlopen(urllib.request.Request(url,headers=HDR),timeout=30).read()
            if raw[:2]==b'\x1f\x8b': raw=gzip.decompress(raw)
            return json.loads(raw)
        except Exception:
            if i==tries-1: raise
            time.sleep(2)
STOP={'fc','cf','ac','afc','sc','sk','if','bk','fk','sv','us','ss','as','rc','cd','ud','nk','kf','ca','1','the','sad','sl'}
def toks(s):
    s=unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().lower()
    return set(w for w in re.sub(r'[^a-z0-9 ]',' ',s).split() if w not in STOP)
FOT={'Champions League':42,'Europa League':73,'Conference League':10216}
F=r'C:\Users\User\Downloads\Multi-League xG Model.xlsx'
res={}; miss=[]; done=0
for comp,lid in FOT.items():
    d=get(f'https://www.fotmob.com/api/data/leagues?id={lid}&season=2025%2F2026')
    allm=(d.get('matches',{}).get('allMatches') or d.get('fixtures',{}).get('allMatches') or [])
    fev=[(m.get('id'),(m.get('status',{}).get('utcTime') or '')[:10],m.get('home',{}).get('name'),m.get('away',{}).get('name')) for m in allm if m.get('status',{}).get('finished')]
    print(f"[{comp}] FotMob finished={len(fev)}",flush=True)
    ex=pd.read_excel(F,sheet_name=comp)
    for _,r in ex.iterrows():
        if pd.isna(r['Home']) or pd.isna(r['Away']): continue
        h,a=str(r['Home']).strip(),str(r['Away']).strip()
        try: dt=pd.to_datetime(r['Date']).strftime('%Y-%m-%d')
        except: dt=''
        hn,an=toks(h),toks(a); best=None;bs=-1
        for mid,fd,fh,fa in fev:
            sc=len(hn&toks(fh))+len(an&toks(fa))+(2 if fd==dt else 0)
            if sc>bs: bs=sc;best=(mid,fd,fh,fa)
        if not best or bs<2: miss.append((comp,dt,h,a)); continue
        mid=best[0]
        try:
            md=get(f'https://www.fotmob.com/api/data/matchDetails?matchId={mid}')
            gen=md['general']; hid=gen['homeTeam']['id']; aid=gen['awayTeam']['id']
            shots=[]
            for s in md.get('content',{}).get('shotmap',{}).get('shots',[]) or []:
                if s.get('isOwnGoal'): continue
                shots.append(dict(tid=s.get('teamId'),xg=s.get('expectedGoals'),sit=s.get('situation'),min=s.get('min'),goal=s.get('eventType')=='Goal'))
            reds=[]
            for e in md.get('content',{}).get('matchFacts',{}).get('events',{}).get('events',[]) or []:
                if e.get('type')=='Card' and e.get('card') in ('Red','RedYellow'):
                    reds.append(dict(home=bool(e.get('isHome')),min=e.get('time')))
            key=f"{comp}|{dt}|{h}|{a}"
            res[key]=dict(mid=mid,hid=hid,aid=aid,hs=gen['homeTeam'].get('id') and (md.get('header',{}).get('teams',[{}])[0].get('score')),
                          shots=shots,reds=reds)
            done+=1
        except Exception as e:
            miss.append((comp,dt,h,a)); continue
        if done%50==0:
            json.dump(res,open(OUT,'w')); print(f"  ...{done} downloaded",flush=True)
        time.sleep(0.2)
json.dump(res,open(OUT,'w'))
nsh=sum(len(v['shots']) for v in res.values())
print(f"DONE: {done} ματς, {nsh} σουτ | unmatched {len(miss)}",flush=True)
if miss: print("UNMATCHED:",miss[:15],flush=True)
