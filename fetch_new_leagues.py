"""fetch_new_leagues.py — κατεβαζει FotMob shot-data για τα νεα υποψηφια πρωταθληματα,
στην ΙΔΙΑ μορφη με το dl.py (data_<name>_<season>.json). Resume: skip οσα υπαρχουν."""
import urllib.request, json, gzip, time, sys, os
os.chdir(r'C:\Users\User\Desktop\Betting Model')
try: sys.stdout.reconfigure(encoding='utf-8'); sys.stderr.reconfigure(encoding='utf-8')
except Exception: pass
HDR={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36',
     'Accept':'*/*','Referer':'https://www.fotmob.com/'}
def get(url,tries=4):
    for i in range(tries):
        try:
            raw=urllib.request.urlopen(urllib.request.Request(url,headers=HDR),timeout=30).read()
            if raw[:2]==b'\x1f\x8b': raw=gzip.decompress(raw)
            return json.loads(raw)
        except Exception:
            if i==tries-1: raise
            time.sleep(1.2*(i+1))

def parse(mid):
    d=get(f'https://www.fotmob.com/api/data/matchDetails?matchId={mid}')
    c=d['content']; gen=d['general']; head=d.get('header',{}); teams=head.get('teams',[])
    hs=teams[0].get('score') if len(teams)>0 else None
    as_=teams[1].get('score') if len(teams)>1 else None
    hid=gen['homeTeam']['id']; aid=gen['awayTeam']['id']
    shots=[]
    for s in c.get('shotmap',{}).get('shots',[]) or []:
        if s.get('isOwnGoal'): continue
        shots.append({'tid':s.get('teamId'),'xg':s.get('expectedGoals'),
                      'min':s.get('min'),'sit':s.get('situation'),'goal':s.get('eventType')=='Goal'})
    reds=[]
    for e in c.get('matchFacts',{}).get('events',{}).get('events',[]) or []:
        if e.get('type')=='Card' and e.get('card') in ('Red','RedYellow'):
            reds.append({'home':bool(e.get('isHome')),'min':e.get('time')})
    return {'mid':mid,'date':gen.get('matchTimeUTC') or gen.get('matchTimeUTCDate'),
            'home':{'name':gen['homeTeam']['name'],'id':hid},
            'away':{'name':gen['awayTeam']['name'],'id':aid},
            'hs':hs,'as':as_,'shots':shots,'reds':reds}

# (name, FotMob id, [(season_str, code)])
JOBS=[
 ('Championship',48,[('2024%2F2025','2425'),('2025%2F2026','2526')]),
 ('ScottishPrem',64,[('2024%2F2025','2425'),('2025%2F2026','2526')]),
 ('Belgium',40,[('2024%2F2025','2425'),('2025%2F2026','2526')]),
 ('SerieB',86,[('2025%2F2026','2526')]),
 ('LaLiga2',140,[('2025%2F2026','2526')]),
 ('Ligue2',110,[('2025%2F2026','2526')]),
]
def finished_ids(lid,season):
    d=get(f'https://www.fotmob.com/api/data/leagues?id={lid}&season={season}')
    arr=(d.get('matches',{}).get('allMatches') or d.get('fixtures',{}).get('allMatches') or [])
    return [m.get('id') for m in arr if m.get('status',{}).get('finished')]

for name,lid,seasons in JOBS:
    for season,code in seasons:
        path=f'data_{name}_{code}.json'
        done={}
        if os.path.exists(path):
            try: done=json.load(open(path,encoding='utf-8'))
            except Exception: done={}
        ids=finished_ids(lid,season)
        todo=[m for m in ids if str(m) not in done]
        print(f"[{name} {code}] finished={len(ids)}  εχω={len(done)}  προς={len(todo)}",flush=True)
        for i,mid in enumerate(todo):
            try:
                done[str(mid)]=parse(mid)
            except Exception as e:
                print(f"   ! {mid}: {str(e)[:40]}",flush=True); continue
            if (i+1)%25==0:
                json.dump(done,open(path,'w',encoding='utf-8'))
                print(f"   {name} {code}: {i+1}/{len(todo)}",flush=True)
            time.sleep(0.15)
        json.dump(done,open(path,'w',encoding='utf-8'))
        nsh=sum(len(v['shots']) for v in done.values())
        print(f"[{name} {code}] DONE {len(done)} ματς, {nsh} σουτ",flush=True)
print("ALL DONE",flush=True)
