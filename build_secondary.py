import json, pandas as pd, numpy as np
from datetime import datetime

NEW=['Bundesliga2','Eredivisie','PrimeiraLiga','GreeceSL']
SEA='2526'; BLEND=0.80; MIN_PRIOR=6; DECAY=0.96

def isodate(s):
    try: return datetime.strptime(s.replace(' UTC',''),'%a, %b %d, %Y, %H:%M').strftime('%Y-%m-%d')
    except: return s[:10]
def w(xg):
    if xg<=0.2: return 1.00
    if xg<=0.4: return 0.45
    if xg<=0.5: return 0.25
    if xg<=0.7: return 0.15
    return 0.05

# ---- INPUTS (compression + penalty + red adj) ----
rows=[]; id2name={}
for lg in NEW:
    d=json.load(open(f'data_{lg}_{SEA}.json'))
    for mid,m in d.items():
        if m['hs'] is None: continue
        hid=int(m['home']['id']); aid=int(m['away']['id'])
        id2name[hid]=m['home']['name']; id2name[aid]=m['away']['name']
        agg={hid:dict(np_raw=0.,np_comp=0.,pen=0,ns=0),aid:dict(np_raw=0.,np_comp=0.,pen=0,ns=0)}
        for s in m['shots']:
            xg=s.get('xg')
            if xg is None or s['tid'] not in agg: continue
            if s.get('sit')=='Penalty': agg[s['tid']]['pen']+=1
            else:
                agg[s['tid']]['np_raw']+=xg; agg[s['tid']]['np_comp']+=xg*w(xg); agg[s['tid']]['ns']+=1
        reds=m.get('reds',[]); ft=95
        dh=sum(max(0,ft-(r.get('min') or 0)) for r in reds if r['home'])
        da=sum(max(0,ft-(r.get('min') or 0)) for r in reds if not r['home'])
        for is_h,tid,opp,gf,dis_self,dis_opp in [(1,hid,aid,m['hs'],dh,da),(0,aid,hid,m['as'],da,dh)]:
            a=agg[tid]; red_xg=0.0083*dis_opp-0.5*0.0083*dis_self
            rows.append(dict(league=lg,season=SEA,mid=mid,date=isodate(m['date']),team=tid,
                gf=gf,np_raw=a['np_raw'],np_comp=a['np_comp'],pen=a['pen'],ns=a['ns'],red_xg=red_xg,is_home=is_h))
df=pd.DataFrame(rows)
df['comp_np_scaled']=df['np_comp']
for lg,g in df.groupby('league'):
    sf=g.np_raw.sum()/g.np_comp.sum(); df.loc[df.league==lg,'comp_np_scaled']=df.loc[df.league==lg,'np_comp']*sf
df['xg_model']=df['comp_np_scaled']+0.25*df['pen']+df['red_xg']
df['ns_eff']=df['ns']+df['pen']+(df['red_xg'].abs()/0.10)

# ---- SUPREMACY (rolling, 80/20 blend) ----
MM=[]
for (lg,mid),g in df.groupby(['league','mid']):
    if len(g)!=2: continue
    h=g[g.is_home==1].iloc[0]; a=g[g.is_home==0].iloc[0]
    MM.append(dict(league=lg,mid=mid,date=h['date'],home=int(h['team']),away=int(a['team']),
        hg=int(h['gf']),ag=int(a['gf']),h_xg=h['xg_model'],a_xg=a['xg_model'],h_ns=h['ns_eff'],a_ns=a['ns_eff']))
M=pd.DataFrame(MM).sort_values(['league','date','mid']).reset_index(drop=True)
def wmean(v):
    n=len(v)
    if n==0: return None
    ww=np.array([DECAY**(n-1-i) for i in range(n)]); return float((ww*np.array(v)).sum()/ww.sum())
out=[]
for lg,G in M.groupby('league'):
    G=G.sort_values(['date','mid']).reset_index(drop=True); hist={}
    lg_shots=pd.concat([G.h_ns,G.a_ns]).mean(); lg_xgps=pd.concat([G.h_xg,G.a_xg]).sum()/pd.concat([G.h_ns,G.a_ns]).sum()
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
            out.append(dict(league=lg,season=SEA,mid=r['mid'],home_name=id2name.get(H),away_name=id2name.get(A),
                hg=r['hg'],ag=r['ag'],gd=r['hg']-r['ag'],xg_h=xg_h,xg_a=xg_a,model_sup=xg_h-xg_a))
        for tid,sf,xf,sa,xa,gf,ga in [(H,r['h_ns'],r['h_xg'],r['a_ns'],r['a_xg'],r['hg'],r['ag']),
                                      (A,r['a_ns'],r['a_xg'],r['h_ns'],r['h_xg'],r['ag'],r['hg'])]:
            hist.setdefault(tid,dict(sf=[],xf=[],sa=[],xa=[],gf=[],ga=[]))
            for k,v in [('sf',sf),('xf',xf),('sa',sa),('xa',xa),('gf',gf),('ga',ga)]: hist[tid][k].append(v)
P=pd.DataFrame(out)
P.to_csv('pred_secondary.csv',index=False)
print(f"Predictions δευτερευοντων: {len(P)} ματς")
print(P.groupby('league').size())
print(f"\nCorrelation supremacy->GD ανα λιγκα:")
for lg in NEW:
    d=P[P.league==lg]
    if len(d): print(f"  {lg:14s}: {d.model_sup.corr(d.gd):.3f}  (n{len(d)})")
