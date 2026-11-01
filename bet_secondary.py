import pandas as pd, numpy as np, unicodedata, re
from math import exp, factorial

EDGE=0.10; STAKE=1000.0; OMIN,OMAX=1.70,2.10; MIN_LINE=0.5; DRAW_BOOST=1.13
F=[factorial(i) for i in range(13)]

# predictions
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

def build_resolver(O):
    fdn={}
    for _,r in O.iterrows():
        if pd.notna(r.get('HomeTeam')): fdn[r['HomeTeam']]=norm(r['HomeTeam'])
        if pd.notna(r.get('AwayTeam')): fdn[r['AwayTeam']]=norm(r['AwayTeam'])
    def resolve(n):
        tn=norm(ALIAS.get(n,n)); best=None;bs=0;bj=0
        for raw,tg in fdn.items():
            ov=len(tn&tg)
            if ov>bs or (ov==bs and ov/max(len(tn|tg),1)>bj): bs=ov;bj=ov/max(len(tn|tg),1);best=raw
        return best if bs>0 else None
    return resolve

def ah_pre(o):  # pre-match AH: Betfair -> Pinnacle -> Avg
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
    return Pm,gd
def probs_1x2(Pm):
    pH=np.tril(Pm,-1).sum(); pD=np.trace(Pm); pA=np.triu(Pm,1).sum(); s=pH+pD+pA
    return pH/s,pD/s,pA/s
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

def evaluate(P, O, label, leagues):
    resolve=build_resolver(O); Om={}
    for _,r in O.iterrows(): Om[(r['HomeTeam'],r['AwayTeam'])]=r
    RESC={}
    bets=[]; rps_l=[]; ll_l=[]
    for _,r in P.iterrows():
        tot=r['xg_h']+r['xg_a']; sup=r['model_sup']
        lh=max((tot+sup)/2,0.05); la=max((tot-sup)/2,0.05)
        Pm,gd=gd_dist(lh,la); pH,pD,pA=probs_1x2(Pm)
        # RPS + logloss (χρειαζονται μονο model + αποτελεσμα)
        act=0 if r['gd']>0 else (1 if r['gd']==0 else 2)
        cum_p=np.cumsum([pH,pD,pA]); cum_a=np.cumsum([1 if i==act else 0 for i in range(3)])
        rps_l.append(np.sum((cum_p-cum_a)**2)/2)
        ll_l.append(-np.log(max([pH,pD,pA][act],1e-9)))
        # betting (pre-match AH)
        fh=RESC.setdefault(r['home_name'],resolve(r['home_name'])); fa=RESC.setdefault(r['away_name'],resolve(r['away_name']))
        o=Om.get((fh,fa)) if fh and fa else None
        if o is None: continue
        line=o.get('AHh'); oh,oa=ah_pre(o)
        if pd.isna(line) or oh is None: continue
        line=float(line)
        for side,ud,odds in [(1,line,oh),(-1,-line,oa)]:
            if ud<MIN_LINE or not(OMIN<=odds<=OMAX): continue
            pw,pp=p_cover(gd,side,ud)
            if pw*(odds-1)-(1-pw-pp)>=EDGE:
                bets.append(dict(league=r['league'],pnl=settle(r['gd'],side,ud,odds)))
    B=pd.DataFrame(bets)
    print(f"\n=== {label} === (RPS/logloss σε {len(P)} ματς)")
    print(f"{'λιγκα':14s} {'RPS':>7s} {'logloss':>8s} | {'bets':>5s} {'ROI':>8s} {'±SE':>6s}")
    idx=0; per={}
    for _,r in P.iterrows():
        per.setdefault(r['league'],dict(rps=[],ll=[])); per[r['league']]['rps'].append(rps_l[idx]); per[r['league']]['ll'].append(ll_l[idx]); idx+=1
    for lg in leagues:
        b=B[B.league==lg] if len(B) else pd.DataFrame()
        rps=np.mean(per[lg]['rps']) if lg in per else float('nan'); ll=np.mean(per[lg]['ll']) if lg in per else float('nan')
        if len(b):
            roi=b.pnl.mean(); se=b.pnl.std()/np.sqrt(len(b))
            print(f"{lg:14s} {rps:>7.4f} {ll:>8.4f} | {len(b):>5d} {roi:>+7.1%} {se:>6.1%}")
        else:
            print(f"{lg:14s} {rps:>7.4f} {ll:>8.4f} | {'—':>5s} {'—':>8s}")
    if len(B):
        print(f"{'ΣΥΝΟΛΟ':14s} {np.mean(rps_l):>7.4f} {np.mean(ll_l):>8.4f} | {len(B):>5d} {B.pnl.mean():>+7.1%} {B.pnl.std()/np.sqrt(len(B)):>6.1%}")

# TOP-5 (2025/26) στα ιδια pre-match AH odds
Otop=load_odds([f'odds/{lg}_2526.csv' for lg in ['EPL','LaLiga','SerieA','Bundesliga','Ligue1']])
evaluate(top,Otop,'TOP-5 (2025/26, pre-match AH)',['EPL','LaLiga','SerieA','Bundesliga','Ligue1'])
# ΔΕΥΤΕΡΕΥΟΝΤΑ
Osec=load_odds([f'odds2/{lg}_2526.csv' for lg in ['Bundesliga2','Eredivisie','PrimeiraLiga','GreeceSL']])
evaluate(sec,Osec,'ΔΕΥΤΕΡΕΥΟΝΤΑ (2025/26, pre-match AH)',['Bundesliga2','Eredivisie','PrimeiraLiga','GreeceSL'])
