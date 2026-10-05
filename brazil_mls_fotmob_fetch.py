"""brazil_mls_fotmob_fetch.py — FotMob shot-data (Brazil Serie A id=268, MLS id=130).
Usage: python brazil_mls_fotmob_fetch.py Brazil 2020 2021 2022 | python brazil_mls_fotmob_fetch.py MLS 2021 ...
Output: data_<League>_<year>.json (same format as data_Brazil_2023.json + 'round','stage').
Resumable: skips mids already in file; saves every 50 matches. Never overwrites other files' mids.
"""
import urllib.request, json, gzip, time, sys, os
from collections import Counter
HERE=os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
try: sys.stdout.reconfigure(encoding='utf-8'); sys.stderr.reconfigure(encoding='utf-8')
except Exception: pass
HDR={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36',
     'Accept':'*/*','Referer':'https://www.fotmob.com/'}
IDS={'Brazil':268,'MLS':130}
SLEEP=0.5
def get(url,tries=6):
    for i in range(tries):
        try:
            raw=urllib.request.urlopen(urllib.request.Request(url,headers=HDR),timeout=30).read()
            if raw[:2]==b'\x1f\x8b': raw=gzip.decompress(raw)
            return json.loads(raw)
        except Exception:
            if i==tries-1: raise
            time.sleep(2*(2**i))

def parse(mid,rnd,stage):
    d=get(f'https://www.fotmob.com/api/data/matchDetails?matchId={mid}')
    c=d['content']; gen=d['general']; head=d.get('header',{}); teams=head.get('teams',[])
    hs=teams[0].get('score') if len(teams)>0 else None
    as_=teams[1].get('score') if len(teams)>1 else None
    hid=gen['homeTeam']['id']; aid=gen['awayTeam']['id']
    shots=[]
    for s in (c.get('shotmap') or {}).get('shots',[]) or []:
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
            'hs':hs,'as':as_,'shots':shots,'reds':reds,'round':rnd,'stage':stage}

def fixtures(lid,season):
    d=get(f'https://www.fotmob.com/api/data/leagues?id={lid}&season={season}')
    arr=(d.get('fixtures',{}).get('allMatches') or d.get('matches',{}).get('allMatches') or [])
    out=[]
    for m in arr:
        st=m.get('status',{})
        if not st.get('finished') or st.get('cancelled') or st.get('awarded'): continue
        r=m.get('round'); rn=m.get('roundName')
        isnum=str(r).isdigit() if r is not None else True
        out.append((str(m['id']), rn if rn is not None else (str(r) if r is not None else None), 'regular' if isnum else 'playoff'))
    return out

league=sys.argv[1]; seasons=sys.argv[2:]; lid=IDS[league]
summary=[]
for yr in seasons:
    path=f'data_{league}_{yr}.json'
    done={}
    if os.path.exists(path):
        try: done=json.load(open(path,encoding='utf-8'))
        except Exception: done={}
    fx=fixtures(lid,yr)
    print(f"[{league} {yr}] finished={len(fx)} stages={Counter(s for _,_,s in fx)} εχω={len(done)}",flush=True)
    todo=[f for f in fx if f[0] not in done]
    for i,(mid,rnd,stage) in enumerate(todo):
        try: done[mid]=parse(mid,rnd,stage)
        except Exception as e: print(f"   ! {mid}: {str(e)[:60]}",flush=True); continue
        if (i+1)%50==0:
            json.dump(done,open(path,'w',encoding='utf-8')); print(f"   {yr}: {i+1}/{len(todo)}",flush=True)
        time.sleep(SLEEP)
    json.dump(done,open(path,'w',encoding='utf-8'))
    print(f"[{league} {yr}] DONE {len(done)} (expected {len(fx)})",flush=True)
print("ALL DONE",flush=True)
