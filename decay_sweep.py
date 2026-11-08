import pandas as pd, numpy as np, json, unicodedata, re
from scipy.stats import norm as Nrm

BLEND=0.80; MIN_PRIOR=6; SIGMA=1.6
DECAYS=[0.99,0.97,0.96,0.94,0.92,0.90,0.85]

TG=pd.read_csv('teamgame_inputs.csv')
id2name={}
for lg in ['EPL','LaLiga','SerieA','Bundesliga','Ligue1']:
    for sea in ['2425','2526']:
        d=json.load(open(f'data_{lg}_{sea}.json'))
        for m in d.values():
            id2name[int(m['home']['id'])]=m['home']['name']; id2name[int(m['away']['id'])]=m['away']['name']

# reconstruct matches (μια φορα)
TG=TG.sort_values(['league','season','date','mid','is_home'])
MM=[]
for (lg,sea,mid),g in TG.groupby(['league','season','mid'],sort=False):
    if len(g)!=2: continue
    h=g[g.is_home==1].iloc[0]; a=g[g.is_home==0].iloc[0]
    MM.append(dict(league=lg,season=str(sea),mid=mid,date=h['date'],home=int(h['team']),away=int(a['team']),
        hg=int(h['gf']),ag=int(a['gf']),h_xg=h['xg_model'],a_xg=a['xg_model'],
        h_ns=h['ns_eff'],a_ns=a['ns_eff']))
M=pd.DataFrame(MM).sort_values(['league','season','date','mid']).reset_index(drop=True)

def build(DECAY):
    def wmean(v):
        n=len(v)
        if n==0: return None
        w=np.array([DECAY**(n-1-i) for i in range(n)]); return float((w*np.array(v)).sum()/w.sum())
    out=[]
    for (lg,sea),G in M.groupby(['league','season'],sort=False):
        G=G.sort_values(['date','mid']).reset_index(drop=True); hist={}
        lg_shots=pd.concat([G.h_ns,G.a_ns]).mean()
        lg_xgps=pd.concat([G.h_xg,G.a_xg]).sum()/pd.concat([G.h_ns,G.a_ns]).sum()
        hf=np.sqrt(G.h_xg.mean()/G.a_xg.mean()); af=1/hf
        for _,r in G.iterrows():
            H,A=r['home'],r['away']; hh=hist.get(H); ha=hist.get(A)
            if hh and ha and len(hh['sf'])>=MIN_PRIOR and len(ha['sf'])>=MIN_PRIOR:
                def blx(t,fx,fg): return BLEND*wmean(t[fx])+(1-BLEND)*wmean(t[fg])
                Hax=blx(hh,'xf','gf')/max(wmean(hh['sf']),1e-9); Hdx=blx(hh,'xa','ga')/max(wmean(hh['sa']),1e-9)
                Aax=blx(ha,'xf','gf')/max(wmean(ha['sf']),1e-9); Adx=blx(ha,'xa','ga')/max(wmean(ha['sa']),1e-9)
                esh_h=(wmean(hh['sf'])/lg_shots)*(wmean(ha['sa'])/lg_shots)*lg_shots
                esh_a=(wmean(ha['sf'])/lg_shots)*(wmean(hh['sa'])/lg_shots)*lg_shots
                xg_h=esh_h*(Hax*(Adx/lg_xgps))*hf; xg_a=esh_a*(Aax*(Hdx/lg_xgps))*af
                out.append(dict(league=lg,season=sea,mid=r['mid'],home=H,away=A,
                    home_name=id2name.get(H),away_name=id2name.get(A),
                    gd=r['hg']-r['ag'],model_sup=xg_h-xg_a))
            for tid,sf,xf,sa,xa,gf,ga in [(H,r['h_ns'],r['h_xg'],r['a_ns'],r['a_xg'],r['hg'],r['ag']),
                                          (A,r['a_ns'],r['a_xg'],r['h_ns'],r['h_xg'],r['ag'],r['hg'])]:
                hist.setdefault(tid,dict(sf=[],xf=[],sa=[],xa=[],gf=[],ga=[]))
                for k,v in [('sf',sf),('xf',xf),('sa',sa),('xa',xa),('gf',gf),('ga',ga)]: hist[tid][k].append(v)
    return pd.DataFrame(out)

# market_sup ανα ματς (μια φορα, ανεξαρτητο decay)
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
def market_sup(sea,hn,an):
    fh=resolve(hn); fa=resolve(an)
    o=Om.get((sea,fh,fa)) if fh and fa else None
    if o is None: return None
    line=o.get('AHCh')
    for hh,ha in [('BFECAHH','BFECAHA'),('PCAHH','PCAHA'),('AvgCAHH','AvgCAHA')]:
        if pd.notna(o.get(hh)) and pd.notna(o.get(ha)): oh,oa=float(o[hh]),float(o[ha]); break
    else: return None
    if pd.isna(line): return None
    ph=(1/oh)/((1/oh)+(1/oa))
    return -float(line)+SIGMA*Nrm.ppf(min(max(ph,1e-4),1-1e-4))

print(f"{'decay':>6s} {'half-life':>9s} | {'corr 24/25':>10s} {'corr 25/26':>10s} | {'MAE-gd':>7s} | {'disagree ολα':>12s} {'24/25':>7s} {'25/26':>7s}")
for D in DECAYS:
    P=build(D)
    P['msup']=[market_sup(s,h,a) for s,h,a in zip(P.season,P.home_name,P.away_name)]
    Q=P.dropna(subset=['msup']).copy()
    Q['disag']=Q.model_sup-Q.msup; Q['mres']=Q.gd-Q.msup
    hl=np.log(0.5)/np.log(D)
    c1=P[P.season=='2425'].model_sup.corr(P[P.season=='2425'].gd)
    c2=P[P.season=='2526'].model_sup.corr(P[P.season=='2526'].gd)
    mae=(P.model_sup-P.gd).abs().mean()
    dall=Q.disag.corr(Q.mres)
    d1=Q[Q.season=='2425'].disag.corr(Q[Q.season=='2425'].mres)
    d2=Q[Q.season=='2526'].disag.corr(Q[Q.season=='2526'].mres)
    star=' <-- τρεχον' if D==0.96 else ''
    print(f"{D:>6.2f} {hl:>8.1f}μ | {c1:>10.3f} {c2:>10.3f} | {mae:>7.3f} | {dall:>+12.4f} {d1:>+7.4f} {d2:>+7.4f}{star}")
