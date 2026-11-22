import json, pandas as pd, numpy as np
from datetime import datetime
from math import exp, factorial
def isodate(s):
    try: return datetime.strptime(s.replace(' UTC',''),'%a, %b %d, %Y, %H:%M').strftime('%Y-%m-%d')
    except: return s[:10]
def d2(s): return datetime.strptime(s,'%Y-%m-%d')
TOP5=['EPL','LaLiga','SerieA','Bundesliga','Ligue1']
EDGE=0.10; OMIN,OMAX=1.70,2.10; DRAW_BOOST=1.13; F=[factorial(i) for i in range(13)]
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
def prev(team,date): 
    s=[x for x in tl.get(team,[]) if x[0]<date]; return s[-1] if s else None
def tired2(team,date,ven):
    # τρεχον εκτος + αμεσως προηγουμενο = ευρωπαικο εκτος μεσοβδομαδα (1-5 μερες)
    if ven!='A': return False
    p=prev(team,date)
    if p is None: return False
    rest=(d2(date)-d2(p[0])).days
    return p[2] in ('CL','EL','ECL') and p[1]=='A' and 1<=rest<=5

P=pd.read_csv('model_predictions.csv'); P=P[P.league.isin(TOP5)].copy(); P['season']=P['season'].astype(str)
# --- φαινομενο: residual + επιθετικο/αμυντικο ---
base_sc=[]; base_co=[]; sc=[]; co=[]; gd_res=[]; wins=[]; proj=[]; nmatch=0; per_sea={'2425':[],'2526':[]}
for _,r in P.iterrows():
    for team,ven,psc,pco,asc,aco,gd in [
        (int(r['home']),'H',r['xg_h'],r['xg_a'],r['hg'],r['ag'],r['gd']),
        (int(r['away']),'A',r['xg_a'],r['xg_h'],r['ag'],r['hg'],-r['gd'])]:
        base_sc.append(asc-psc); base_co.append(aco-pco)
        if tired2(team,r['date'],ven):
            nmatch+=1; sc.append(asc-psc); co.append(aco-pco); gd_res.append(gd-(psc-pco))
            proj.append(psc); wins.append(1 if gd>0 else (0.5 if gd==0 else 0)); per_sea[r['season']].append(gd-(psc-pco))
bsc=np.mean(base_sc); bco=np.mean(base_co)
sc=np.array(sc); co=np.array(co); gd_res=np.array(gd_res)
print(f"ΣΕΝΑΡΙΟ: ευρωπαικο εκτος μεσοβδομαδα -> πρωταθλημα εκτος (2 σερι εκτος)")
print(f"Κουρασμενες ομαδες-ματς: {nmatch}\n")
print(f"Επιθετικο (scored−proj, vs baseline): {sc.mean()-bsc:+.3f} (±{sc.std()/np.sqrt(len(sc)):.3f})")
print(f"Αμυντικο (conceded−proj, vs baseline): {co.mean()-bco:+.3f} (±{co.std()/np.sqrt(len(co)):.3f})")
print(f"Συνολικο GD residual: {gd_res.mean():+.3f} (±{gd_res.std()/np.sqrt(len(gd_res)):.3f})")
print(f"Win rate: {np.mean(wins):.1%} (baseline 50%)")
mp=np.mean(proj)
print(f"  -> επιθετικο ≈ {(sc.mean()-bsc)/mp*100:+.0f}% xG | αμυντικο ≈ {(co.mean()-bco)/mp*100:+.0f}% xG αντιπαλου")
print(f"\nGD residual ανα σεζον:")
for s in ['2425','2526']:
    a=np.array(per_sea[s]); print(f"  {s}: {a.mean():+.3f} (±{a.std()/np.sqrt(max(len(a),1)):.3f}), n={len(a)}")

# --- FADE betting ---
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
RC={}
fade={'2425':[],'2526':[]}; fade_z={'2425':[],'2526':[]}
for _,r in P.iterrows():
    # η κουρασμενη ειναι ΠΑΝΤΑ ο φιλοξενουμενος εδω (τρεχον εκτος)
    th=tired2(int(r['away']),r['date'],'A')
    if not th: continue
    o=Om.get((r['season'],RC.setdefault(r['home_name'],resolve(r['home_name'])),RC.setdefault(r['away_name'],resolve(r['away_name']))))
    if o is None: continue
    line=o.get('AHCh'); oh,oa=ah(o)
    if pd.isna(line) or oh is None: continue
    line=float(line)
    pnl=settle(r['gd'],1,line,oh)  # ποντα τον γηπεδουχο (αντιπαλο της κουρασμενης)
    fade[r['season']].append(pnl)
    if OMIN<=oh<=OMAX: fade_z[r['season']].append(pnl)
def rep(a):
    a=np.array(a); return f"{a.mean():+.1%} ±{a.std()/np.sqrt(len(a)):.1%} (n{len(a)})" if len(a) else "n0"
print(f"\nFADE (ποντα τον γηπεδουχο αντιπαλο):")
for s in ['2425','2526']: print(f"  {s}: ολα {rep(fade[s])} | ζωνη 1.70-2.10 {rep(fade_z[s])}")
print(f"  ΣΥΝΟΛΟ: ολα {rep(fade['2425']+fade['2526'])} | ζωνη {rep(fade_z['2425']+fade_z['2526'])}")
