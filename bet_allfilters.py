import pandas as pd, numpy as np, unicodedata, re
from math import exp, factorial
EDGE=0.10; DRAW_BOOST=1.13
F=[factorial(i) for i in range(13)]
top=pd.read_csv('model_predictions.csv'); top=top[top.season.astype(str)=='2526'].copy()
sec=pd.read_csv('pred_secondary.csv')
def norm(s):
    s=unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().lower()
    return frozenset(set(re.sub(r'[^a-z ]',' ',s).split())-{'fc','cf','ac','calcio','club','de','afc','ss','us','as','rc','ud','sd','sc','rcd','real','1','vfl','vfb','tsg','sv','bsc','og'})
ALIAS={'Athletic Club':'Ath Bilbao','Borussia Mönchengladbach':"M'gladbach",'Espanyol':'Espanol','Hamburger SV':'Hamburg','Wolverhampton Wanderers':'Wolves'}
def load_odds(paths):
    O=[]
    for p in paths:
        try: O.append(pd.read_csv(p,encoding='latin-1'))
        except: pass
    return pd.concat(O,ignore_index=True) if O else pd.DataFrame()
def resolver(O):
    fdn={}
    for _,r in O.iterrows():
        if pd.notna(r.get('HomeTeam')): fdn[r['HomeTeam']]=norm(r['HomeTeam'])
        if pd.notna(r.get('AwayTeam')): fdn[r['AwayTeam']]=norm(r['AwayTeam'])
    def res(n):
        tn=norm(ALIAS.get(n,n)); best=None;bs=0;bj=0
        for raw,tg in fdn.items():
            ov=len(tn&tg)
            if ov>bs or (ov==bs and ov/max(len(tn|tg),1)>bj): bs=ov;bj=ov/max(len(tn|tg),1);best=raw
        return best if bs>0 else None
    return res
def ah_pre(o):
    for hh,ha in [('BFEAHH','BFEAHA'),('PAHH','PAHA'),('AvgAHH','AvgAHA')]:
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
def p_cover(gd,side,line):
    pw=pp=0.
    for k,p in gd.items():
        m=(k if side==1 else -k)+line
        if m>0.01: pw+=p
        elif abs(m)<0.01: pp+=p
    return pw,pp
def settle(g,side,line,odds):
    parts=[line] if (line*4)%2==0 else [line-0.25,line+0.25]; pnl=0.
    for L in parts:
        s=1/len(parts); m=(g if side==1 else -g)+L
        if m>0.01: pnl+=s*(odds-1)
        elif abs(m)<0.01: pnl+=0.
        else: pnl-=s
    return pnl
def ev(P,O,label,leagues):
    res=resolver(O); Om={}
    for _,r in O.iterrows(): Om[(r['HomeTeam'],r['AwayTeam'])]=r
    RC={}; bets=[]
    for _,r in P.iterrows():
        tot=r['xg_h']+r['xg_a']; sup=r['model_sup']
        lh=max((tot+sup)/2,0.05); la=max((tot-sup)/2,0.05); gd=gd_dist(lh,la)
        fh=RC.setdefault(r['home_name'],res(r['home_name'])); fa=RC.setdefault(r['away_name'],res(r['away_name']))
        o=Om.get((fh,fa)) if fh and fa else None
        if o is None: continue
        line=o.get('AHh'); oh,oa=ah_pre(o)
        if pd.isna(line) or oh is None: continue
        line=float(line)
        # ΟΛΑ: φαβορι+underdog, καθε γραμμη, καθε odds
        for side,L,odds in [(1,line,oh),(-1,-line,oa)]:
            pw,pp=p_cover(gd,side,L)
            if pw*(odds-1)-(1-pw-pp)>=EDGE:
                bets.append(dict(league=r['league'],side='underdog' if L>0 else 'favorite',pnl=settle(r['gd'],side,L,odds)))
    B=pd.DataFrame(bets)
    print(f"\n=== {label} — ΟΛΑ τα bets (μονο edge≥10%) ===")
    print(f"{'λιγκα':14s} {'bets':>5s} {'ROI':>8s} {'±SE':>6s}")
    for lg in leagues:
        b=B[B.league==lg]
        if len(b): print(f"{lg:14s} {len(b):>5d} {b.pnl.mean():>+7.1%} {b.pnl.std()/np.sqrt(len(b)):>6.1%}")
    print(f"{'ΣΥΝΟΛΟ':14s} {len(B):>5d} {B.pnl.mean():>+7.1%} {B.pnl.std()/np.sqrt(len(B)):>6.1%}")
    for s in ['underdog','favorite']:
        bs=B[B.side==s]
        if len(bs): print(f"  └ {s:9s} {len(bs):>5d} {bs.pnl.mean():>+7.1%} {bs.pnl.std()/np.sqrt(len(bs)):>6.1%}")
Otop=load_odds([f'odds/{lg}_2526.csv' for lg in ['EPL','LaLiga','SerieA','Bundesliga','Ligue1']])
ev(top,Otop,'TOP-5 (2025/26)',['EPL','LaLiga','SerieA','Bundesliga','Ligue1'])
Osec=load_odds([f'odds2/{lg}_2526.csv' for lg in ['Bundesliga2','Eredivisie','PrimeiraLiga','GreeceSL']])
ev(sec,Osec,'ΔΕΥΤΕΡΕΥΟΝΤΑ (2025/26)',['Bundesliga2','Eredivisie','PrimeiraLiga','GreeceSL'])
