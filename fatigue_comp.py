import json, pandas as pd, numpy as np
from datetime import datetime
def isodate(s):
    try: return datetime.strptime(s.replace(' UTC',''),'%a, %b %d, %Y, %H:%M').strftime('%Y-%m-%d')
    except: return s[:10]
def d2(s): return datetime.strptime(s,'%Y-%m-%d')
TOP5=['EPL','LaLiga','SerieA','Bundesliga','Ligue1']; OMIN,OMAX=1.70,2.10
events=[]
for lg in TOP5:
    for sea in ['2425','2526']:
        d=json.load(open(f'data_{lg}_{sea}.json'))
        for m in d.values():
            if m['hs'] is None: continue
            dt=isodate(m['date']); events.append((dt,int(m['home']['id']),'H','LEAGUE')); events.append((dt,int(m['away']['id']),'A','LEAGUE'))
for e in json.load(open('euro_fixtures.json')):
    events.append((e['date'],e['home'],'H',e['comp'])); events.append((e['date'],e['away'],'A',e['comp']))
tl={}
for dt,t,v,c in events: tl.setdefault(t,[]).append((dt,v,c))
for t in tl: tl[t]=sorted(set(tl[t]),key=lambda x:x[0])
def prevs(team,date,k): return [x for x in tl.get(team,[]) if x[0]<date][-k:]

import unicodedata,re
def norm(s):
    s=unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().lower()
    return frozenset(set(re.sub(r'[^a-z ]',' ',s).split())-{'fc','cf','ac','calcio','club','de','afc','ss','us','as','rc','ud','sd','sc','rcd','real','1','vfl','vfb','tsg','sv','bsc','og'})
ALIAS={'Athletic Club':'Ath Bilbao','Borussia Mönchengladbach':"M'gladbach",'Espanyol':'Espanol','Hamburger SV':'Hamburg','Wolverhampton Wanderers':'Wolves'}
O=[]
for lg in TOP5:
    for sea in ['2425','2526']:
        o=pd.read_csv(f'odds/{lg}_{sea}.csv',encoding='latin-1'); o['season']=sea; O.append(o)
O=pd.concat(O,ignore_index=True)
fdn={}
for _,r in O.iterrows(): fdn[r['HomeTeam']]=norm(r['HomeTeam']); fdn[r['AwayTeam']]=norm(r['AwayTeam'])
def resolve(n):
    tn=norm(ALIAS.get(n,n)); best=None;bs=0;bj=0
    for raw,tg in fdn.items():
        ov=len(tn&tg)
        if ov>bs or (ov==bs and ov/max(len(tn|tg),1)>bj): bs=ov;bj=ov/max(len(tn|tg),1);best=raw
    return best if bs>0 else None
Om={}
for _,r in O.iterrows(): Om[(str(r['season']),r['HomeTeam'],r['AwayTeam'])]=r
def ah(o):
    for hh,ha in [('BFECAHH','BFECAHA'),('PCAHH','PCAHA'),('AvgCAHH','AvgCAHA')]:
        if pd.notna(o.get(hh)) and pd.notna(o.get(ha)): return float(o[hh]),float(o[ha])
    return None,None
def settle(g,side,line,odds):
    parts=[line] if (line*4)%2==0 else [line-0.25,line+0.25]; pnl=0.
    for L in parts:
        s=1/len(parts); m=(g if side==1 else -g)+L
        if m>0.01: pnl+=s*(odds-1)
        elif abs(m)<0.01: pnl+=0.
        else: pnl-=s
    return pnl
P=pd.read_csv('model_predictions.csv'); P=P[P.league.isin(TOP5)].copy(); P['season']=P['season'].astype(str)
RC={}
def euro_comp_2away(team,date):  # 2-εκτος: επιστρεφει comp του προηγ ευρωπαικου εκτος, αλλιως None
    pm=prevs(team,date,1)
    if pm and pm[-1][2] in ('CL','EL','ECL') and pm[-1][1]=='A':
        rest=(d2(date)-d2(pm[-1][0])).days
        if 1<=rest<=5: return pm[-1][2]
    return None
def euro_comp_3away(team,date,ven):  # 3-εκτος με ευρωπη μεση
    pm=prevs(team,date,3); venues=[v for _,v,_ in pm[-2:]]+[ven]
    if len(venues)==3 and all(v=='A' for v in venues) and len(pm)>=1 and pm[-1][2] in ('CL','EL','ECL') and pm[-1][1]=='A':
        return pm[-1][2]
    return None

def run(which):
    res={c:dict(gd=[],fade=[],fz=[]) for c in ['CL','EL','ECL']}
    for _,r in P.iterrows():
        comp=None
        if which=='2away': comp=euro_comp_2away(int(r['away']),r['date'])  # κουρασμενη=away
        else: comp=euro_comp_3away(int(r['away']),r['date'],'A')
        if comp is None: continue
        res[comp]['gd'].append(-r['gd']-(r['xg_a']-r['xg_h']))  # residual κουρασμενης (away)
        o=Om.get((r['season'],RC.setdefault(r['home_name'],resolve(r['home_name'])),RC.setdefault(r['away_name'],resolve(r['away_name']))))
        if o is None: continue
        line=o.get('AHCh'); oh,oa=ah(o)
        if pd.isna(line) or oh is None: continue
        pnl=settle(r['gd'],1,float(line),oh)
        res[comp]['fade'].append(pnl)
        if OMIN<=oh<=OMAX: res[comp]['fz'].append(pnl)
    return res
for which,lab in [('3away','ΣΕΝΑΡΙΟ 3-ΕΚΤΟΣ (n~36)'),('2away','ΣΕΝΑΡΙΟ 2-ΕΚΤΟΣ (n~180)')]:
    print(f"\n{lab} — ανα διοργανωση:")
    print(f"  {'comp':4s} {'n':>4s} | {'GD residual':>16s} | {'FADE ζωνη ROI':>18s}")
    R=run(which)
    for c in ['CL','EL','ECL']:
        gd=np.array(R[c]['gd']); fz=np.array(R[c]['fz'])
        gds=f"{gd.mean():+.3f} (±{gd.std()/np.sqrt(max(len(gd),1)):.3f})" if len(gd) else "—"
        fzs=f"{fz.mean():+.1%} (n{len(fz)})" if len(fz) else "n0"
        print(f"  {c:4s} {len(gd):>4d} | {gds:>16s} | {fzs:>18s}")
