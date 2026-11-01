import json, pandas as pd, numpy as np
from datetime import datetime
from math import exp, factorial

# fatigue adjustment (απο τα 36 ματς — IN-SAMPLE, βλ. προειδοποιηση)
ATT_MULT=0.89   # κουρασμενη επιθεση
DEF_MULT=1.18   # κουρασμενη αμυνα (=αντιπαλος επιθεση)
EDGE=0.10; OMIN,OMAX=1.70,2.10; MIN_LINE=0.5; DRAW_BOOST=1.13
F=[factorial(i) for i in range(13)]
def isodate(s):
    try: return datetime.strptime(s.replace(' UTC',''),'%a, %b %d, %Y, %H:%M').strftime('%Y-%m-%d')
    except: return s[:10]
def d2(s): return datetime.strptime(s,'%Y-%m-%d')
TOP5=['EPL','LaLiga','SerieA','Bundesliga','Ligue1']

# timelines
events=[]
for lg in TOP5:
    for sea in ['2425','2526']:
        d=json.load(open(f'data_{lg}_{sea}.json'))
        for m in d.values():
            if m['hs'] is None: continue
            dt=isodate(m['date']); h=int(m['home']['id']); a=int(m['away']['id'])
            events.append((dt,h,'H','LEAGUE')); events.append((dt,a,'A','LEAGUE'))
for e in json.load(open('euro_fixtures.json')):
    events.append((e['date'],e['home'],'H',e['comp'])); events.append((e['date'],e['away'],'A',e['comp']))
tl={}
for dt,t,v,c in events: tl.setdefault(t,[]).append((dt,v,c))
for t in tl: tl[t]=sorted(set(tl[t]),key=lambda x:x[0])
def tired(team,date,ven):
    pm=[x for x in tl.get(team,[]) if x[0]<date][-3:]
    venues=[v for _,v,_ in pm[-2:]]+[ven]
    return len(venues)==3 and all(v=='A' for v in venues) and len(pm)>=1 and pm[-1][2] in ('CL','EL','ECL') and pm[-1][1]=='A'

# odds
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
def ah_close(o):
    for hh,ha in [('BFECAHH','BFECAHA'),('PCAHH','PCAHA'),('AvgCAHH','AvgCAHA')]:
        if pd.notna(o.get(hh)) and pd.notna(o.get(ha)): return float(o[hh]),float(o[ha])
    return None,None
def gd_dist(lh,la):
    ph=[exp(-lh)*lh**i/F[i] for i in range(13)]; pa=[exp(-la)*la**j/F[j] for j in range(13)]
    Pm=np.outer(ph,pa)
    for i in range(13): Pm[i,i]*=DRAW_BOOST
    Pm/=Pm.sum(); gd={}
    for i in range(13):
        for j in range(13): gd[i-j]=gd.get(i-j,0)+Pm[i,j]
    return gd
def settle(g,side,line,odds):
    parts=[line] if (line*4)%2==0 else [line-0.25,line+0.25]; pnl=0.
    for L in parts:
        s=1/len(parts); m=(g if side==1 else -g)+L
        if m>0.01: pnl+=s*(odds-1)
        elif abs(m)<0.01: pnl+=0.
        else: pnl-=s
    return pnl

P=pd.read_csv('model_predictions.csv'); P=P[P.league.isin(TOP5)].copy()
RC={}
def bet_row(xg_h,xg_a,gd,r):
    o=Om.get((str(r['season']),RC.setdefault(r['home_name'],resolve(r['home_name'])),RC.setdefault(r['away_name'],resolve(r['away_name']))))
    if o is None: return None
    line=o.get('AHCh'); oh,oa=ah_close(o)
    if pd.isna(line) or oh is None: return None
    line=float(line); sup=xg_h-xg_a; tot=xg_h+xg_a; lh=max((tot+sup)/2,.05); la=max((tot-sup)/2,.05); dist=gd_dist(lh,la)
    out=[]
    for side,ud,odds in [(1,line,oh),(-1,-line,oa)]:
        if ud<MIN_LINE or not(OMIN<=odds<=OMAX): continue
        pw=pp=0.
        for k,p in dist.items():
            m=(k if side==1 else -k)+ud
            if m>0.01: pw+=p
            elif abs(m)<0.01: pp+=p
        if pw*(odds-1)-(1-pw-pp)>=EDGE: out.append(settle(gd,side,ud,odds))
    return out

# Βρες κουρασμενα ματς, τρεξε betting με/χωρις adjustment
base_b={'2425':[],'2526':[]}; adj_b={'2425':[],'2526':[]}; fade=[]
n_tired=0
for _,r in P.iterrows():
    th=tired(int(r['home']),r['date'],'H'); ta=tired(int(r['away']),r['date'],'A')
    if not (th or ta): continue
    n_tired+=1; sea=str(r['season'])
    xh,xa=r['xg_h'],r['xg_a']
    # adjustment
    if th: axh,axa=xh*ATT_MULT, xa*DEF_MULT
    else:  axh,axa=xh*DEF_MULT, xa*ATT_MULT
    b0=bet_row(xh,xa,r['gd'],r); b1=bet_row(axh,axa,r['gd'],r)
    if b0: base_b[sea]+=b0
    if b1: adj_b[sea]+=b1
    # fade: πονταρε τον αντιπαλο της κουρασμενης στη γραμμη αγορας
    o=Om.get((sea,RC.get(r['home_name']),RC.get(r['away_name'])))
    if o is not None:
        line=o.get('AHCh'); oh,oa=ah_close(o)
        if pd.notna(line) and oh is not None:
            line=float(line)
            if th: fade.append(settle(r['gd'],-1,-line,oa))   # πονταρε away
            else:  fade.append(settle(r['gd'], 1, line,oh))   # πονταρε home

print(f"Κουρασμενα ματς (εκτος/ευρωπη-εκτος/εκτος): {n_tired}\n")
def rep(d):
    a=np.array(d)
    return f"{a.mean():+.1%} ±{a.std()/np.sqrt(len(a)):.1%} (n{len(a)})" if len(a) else "n0"
print("FILTERED BETTING (edge≥10%,+hcap,odds range) στα κουρασμενα ματς:")
for sea in ['2425','2526']:
    print(f"  {sea}: χωρις adj {rep(base_b[sea])} | ΜΕ adj {rep(adj_b[sea])}")
allbase=base_b['2425']+base_b['2526']; alladj=adj_b['2425']+adj_b['2526']
print(f"  ΣΥΝΟΛΟ: χωρις adj {rep(allbase)} | ΜΕ adj {rep(alladj)}")
print(f"\nFADE (πονταρε παντα τον αντιπαλο της κουρασμενης, γραμμη αγορας, odds range):")
fade_r=[x for x in fade]  # ολα
print(f"  ΣΥΝΟΛΟ: {rep(fade_r)}")

# fade ανα σεζον + με/χωρις odds range
print("\n--- FADE αναλυτικα ---")
fade_all={'2425':[],'2526':[]}; fade_zone={'2425':[],'2526':[]}
for _,r in P.iterrows():
    th=tired(int(r['home']),r['date'],'H'); ta=tired(int(r['away']),r['date'],'A')
    if not (th or ta): continue
    sea=str(r['season'])
    o=Om.get((sea,RC.get(r['home_name']),RC.get(r['away_name'])))
    if o is None: continue
    line=o.get('AHCh'); oh,oa=ah_close(o)
    if pd.isna(line) or oh is None: continue
    line=float(line)
    if th: side,L,odds=-1,-line,oa
    else:  side,L,odds= 1, line,oh
    pnl=settle(r['gd'],side,L,odds)
    fade_all[sea].append(pnl)
    if OMIN<=odds<=OMAX: fade_zone[sea].append(pnl)
def rep(a):
    a=np.array(a); return f"{a.mean():+.1%} ±{a.std()/np.sqrt(len(a)):.1%} (n{len(a)})" if len(a) else "n0"
for sea in ['2425','2526']:
    print(f"  {sea}: ολα τα odds {rep(fade_all[sea])} | μονο ζωνη 1.70-2.10 {rep(fade_zone[sea])}")
za=fade_zone['2425']+fade_zone['2526']; aa=fade_all['2425']+fade_all['2526']
print(f"  ΣΥΝΟΛΟ: ολα {rep(aa)} | ζωνη {rep(za)}")
