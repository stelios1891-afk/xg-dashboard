import pandas as pd, numpy as np, json, unicodedata, re
from math import exp, factorial
from scipy.stats import norm as Nrm

BLEND=0.80; MIN_PRIOR=6; DECAY=0.96
EDGE=0.10; OMIN,OMAX=1.70,2.10; MIN_LINE=0.5; DRAW_BOOST=1.13
F=[factorial(i) for i in range(13)]
# ιστορικο σταθερο HFA (11 σεζον, within-pairing) απο συζητηση 22/6
HFA_FIX={'EPL':1.10,'LaLiga':1.15,'SerieA':1.08,'Bundesliga':1.12,'Ligue1':1.105}

TG=pd.read_csv('teamgame_inputs.csv')
id2name={}
for lg in ['EPL','LaLiga','SerieA','Bundesliga','Ligue1']:
    for sea in ['2425','2526']:
        d=json.load(open(f'data_{lg}_{sea}.json'))
        for m in d.values():
            id2name[int(m['home']['id'])]=m['home']['name']; id2name[int(m['away']['id'])]=m['away']['name']
TG=TG.sort_values(['league','season','date','mid','is_home'])
MM=[]
for (lg,sea,mid),g in TG.groupby(['league','season','mid'],sort=False):
    if len(g)!=2: continue
    h=g[g.is_home==1].iloc[0]; a=g[g.is_home==0].iloc[0]
    MM.append(dict(league=lg,season=str(sea),mid=mid,date=h['date'],home=int(h['team']),away=int(a['team']),
        hg=int(h['gf']),ag=int(a['gf']),h_xg=h['xg_model'],a_xg=a['xg_model'],h_ns=h['ns_eff'],a_ns=a['ns_eff']))
M=pd.DataFrame(MM).sort_values(['league','season','date','mid']).reset_index(drop=True)

def build(hfa_mode):
    def wmean(v):
        n=len(v)
        if n==0: return None
        w=np.array([DECAY**(n-1-i) for i in range(n)]); return float((w*np.array(v)).sum()/w.sum())
    out=[]
    for (lg,sea),G in M.groupby(['league','season'],sort=False):
        G=G.sort_values(['date','mid']).reset_index(drop=True); hist={}
        lg_shots=pd.concat([G.h_ns,G.a_ns]).mean(); lg_xgps=pd.concat([G.h_xg,G.a_xg]).sum()/pd.concat([G.h_ns,G.a_ns]).sum()
        if hfa_mode=='season': hf=np.sqrt(G.h_xg.mean()/G.a_xg.mean())
        else: hf=HFA_FIX[lg]
        af=1/hf
        for _,r in G.iterrows():
            H,A=r['home'],r['away']; hh=hist.get(H); ha=hist.get(A)
            if hh and ha and len(hh['sf'])>=MIN_PRIOR and len(ha['sf'])>=MIN_PRIOR:
                def blx(t,fx,fg): return BLEND*wmean(t[fx])+(1-BLEND)*wmean(t[fg])
                Hax=blx(hh,'xf','gf')/max(wmean(hh['sf']),1e-9); Hdx=blx(hh,'xa','ga')/max(wmean(hh['sa']),1e-9)
                Aax=blx(ha,'xf','gf')/max(wmean(ha['sf']),1e-9); Adx=blx(ha,'xa','ga')/max(wmean(ha['sa']),1e-9)
                esh_h=(wmean(hh['sf'])/lg_shots)*(wmean(ha['sa'])/lg_shots)*lg_shots
                esh_a=(wmean(ha['sf'])/lg_shots)*(wmean(hh['sa'])/lg_shots)*lg_shots
                xg_h=esh_h*(Hax*(Adx/lg_xgps))*hf; xg_a=esh_a*(Aax*(Hdx/lg_xgps))*af
                out.append(dict(league=lg,season=sea,home_name=id2name.get(H),away_name=id2name.get(A),
                    gd=r['hg']-r['ag'],xg_h=xg_h,xg_a=xg_a,model_sup=xg_h-xg_a))
            for tid,sf,xf,sa,xa,gf,ga in [(H,r['h_ns'],r['h_xg'],r['a_ns'],r['a_xg'],r['hg'],r['ag']),
                                          (A,r['a_ns'],r['a_xg'],r['h_ns'],r['h_xg'],r['ag'],r['hg'])]:
                hist.setdefault(tid,dict(sf=[],xf=[],sa=[],xa=[],gf=[],ga=[]))
                for k,v in [('sf',sf),('xf',xf),('sa',sa),('xa',xa),('gf',gf),('ga',ga)]: hist[tid][k].append(v)
    return pd.DataFrame(out)

def norm(s):
    s=unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().lower()
    return frozenset(set(re.sub(r'[^a-z ]',' ',s).split())-{'fc','cf','ac','calcio','club','de','afc','ss','us','as','rc','ud','sd','sc','rcd','real','1','vfl','vfb','tsg','sv','bsc','og'})
ALIAS={'Athletic Club':'Ath Bilbao','Borussia Mönchengladbach':"M'gladbach",'Espanyol':'Espanol','Hamburger SV':'Hamburg','Wolverhampton Wanderers':'Wolves'}
O=[]
for lg in ['EPL','LaLiga','SerieA','Bundesliga','Ligue1']:
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
RES={}
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
def bet(P):
    rows=[]
    for _,r in P.iterrows():
        tot=r['xg_h']+r['xg_a']; sup=r['model_sup']; lh=max((tot+sup)/2,.05); la=max((tot-sup)/2,.05)
        o=Om.get((str(r['season']),RES.setdefault(r['home_name'],resolve(r['home_name'])),RES.setdefault(r['away_name'],resolve(r['away_name']))))
        if o is None: continue
        line=o.get('AHCh'); oh=oa=None
        for hh,ha in [('BFECAHH','BFECAHA'),('PCAHH','PCAHA'),('AvgCAHH','AvgCAHA')]:
            if pd.notna(o.get(hh)) and pd.notna(o.get(ha)): oh,oa=float(o[hh]),float(o[ha]); break
        if pd.isna(line) or oh is None: continue
        line=float(line); dist=gd_dist(lh,la)
        for side,ud,odds in [(1,line,oh),(-1,-line,oa)]:
            if ud<MIN_LINE or not(OMIN<=odds<=OMAX): continue
            pw=pp=0.
            for k,p in dist.items():
                m=(k if side==1 else -k)+ud
                if m>0.01: pw+=p
                elif abs(m)<0.01: pp+=p
            if pw*(odds-1)-(1-pw-pp)>=EDGE: rows.append(dict(league=r['league'],season=r['season'],pnl=settle(r['gd'],side,ud,odds)))
    return pd.DataFrame(rows)

for mode,lab in [('season','ΤΩΡΙΝΟ (per-season xG HFA, look-ahead)'),('fixed','ΣΤΑΘΕΡΟ ιστορικο HFA (out-of-sample)')]:
    B=bet(build(mode)); r=B.pnl.values
    print(f"\n{lab}")
    print(f"  Portfolio: {r.mean():+.1%} ±{r.std()/np.sqrt(len(r)):.1%}  ({len(B)} bets)")
    for sea in ['2425','2526']:
        rs=B[B.season==sea].pnl.values; print(f"    {sea}: {rs.mean():+.1%} ({len(rs)} bets)")
