"""Πληρες shot-level ολων των 25/26 ευρωπαικων (CL/EL/Conference, league phase + knockouts).
Keyed by comp|date|FotMob_home|FotMob_away. Αποθηκευει hs+as, team ids, shots, reds. Resume-aware."""
import urllib.request, json, gzip, time, sys, os
sys.stdout.reconfigure(encoding='utf-8')
HDR={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36','Accept':'*/*','Referer':'https://www.fotmob.com/'}
OUT=r'C:\Users\User\AppData\Local\Temp\claude\C--Users-User-Desktop-Betting-Model\b46da584-c209-452b-8ff3-da29760f9223\scratchpad\euro_shots_full.json'
def get(url,tries=3):
    for i in range(tries):
        try:
            raw=urllib.request.urlopen(urllib.request.Request(url,headers=HDR),timeout=30).read()
            if raw[:2]==b'\x1f\x8b': raw=gzip.decompress(raw)
            return json.loads(raw)
        except Exception:
            if i==tries-1: raise
            time.sleep(2)
FOT={'Champions League':42,'Europa League':73,'Conference League':10216}
res={}
if os.path.exists(OUT):
    try: res=json.load(open(OUT,encoding='utf-8'))
    except: res={}
done=0
for comp,lid in FOT.items():
    d=get(f'https://www.fotmob.com/api/data/leagues?id={lid}&season=2025%2F2026')
    allm=(d.get('matches',{}).get('allMatches') or d.get('fixtures',{}).get('allMatches') or [])
    fin=[m for m in allm if m.get('status',{}).get('finished')]
    # φιλτρο: league phase onward (>=2025-09-01, εξαιρει summer qualifiers)
    fin=[m for m in fin if (m.get('status',{}).get('utcTime') or '')[:10]>='2025-09-01']
    print(f"[{comp}] finished (Σεπ+): {len(fin)}",flush=True)
    for m in fin:
        dt=(m.get('status',{}).get('utcTime') or '')[:10]; fh=m.get('home',{}).get('name'); fa=m.get('away',{}).get('name')
        key=f"{comp}|{dt}|{fh}|{fa}"
        if key in res: continue
        try:
            md=get(f'https://www.fotmob.com/api/data/matchDetails?matchId={m.get("id")}')
            gen=md['general']; head=md.get('header',{}); teams=head.get('teams',[])
            hs=teams[0].get('score') if len(teams)>0 else None; as_=teams[1].get('score') if len(teams)>1 else None
            hid=gen['homeTeam']['id']; aid=gen['awayTeam']['id']; shots=[]
            for s in md.get('content',{}).get('shotmap',{}).get('shots',[]) or []:
                if s.get('isOwnGoal'): continue
                shots.append(dict(tid=s.get('teamId'),xg=s.get('expectedGoals'),sit=s.get('situation'),min=s.get('min'),goal=s.get('eventType')=='Goal'))
            reds=[]
            for e in md.get('content',{}).get('matchFacts',{}).get('events',{}).get('events',[]) or []:
                if e.get('type')=='Card' and e.get('card') in ('Red','RedYellow'): reds.append(dict(home=bool(e.get('isHome')),min=e.get('time')))
            res[key]=dict(mid=m.get('id'),hid=hid,aid=aid,hs=hs,as_=as_,fh=fh,fa=fa,shots=shots,reds=reds)
            done+=1
        except Exception as ex: print(f'  ! {key}: {str(ex)[:40]}',flush=True); continue
        if done%50==0: json.dump(res,open(OUT,'w')); print(f'  ...{done} νεα downloaded (συνολο {len(res)})',flush=True)
        time.sleep(0.18)
json.dump(res,open(OUT,'w'))
byc={}
for k in res: byc[k.split('|')[0]]=byc.get(k.split('|')[0],0)+1
print(f"DONE: συνολο {len(res)} ματς ({done} νεα) | ανα διοργανωση {byc}",flush=True)
