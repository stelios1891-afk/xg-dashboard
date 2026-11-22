import json, pandas as pd, numpy as np
from datetime import datetime
def isodate(s):
    try: return datetime.strptime(s.replace(' UTC',''),'%a, %b %d, %Y, %H:%M').strftime('%Y-%m-%d')
    except: return s[:10]
def d2(s): return datetime.strptime(s,'%Y-%m-%d')
BLEND=0.80; MIN_PRIOR=6; DECAY=0.96; OMIN,OMAX=1.70,2.10
HFA_FIX={'Bundesliga2':1.102,'Eredivisie':1.130,'PrimeiraLiga':1.116,'GreeceSL':1.133}
JOBS=[('Bundesliga2',['2425','2526']),('Eredivisie',['2425','2526']),('PrimeiraLiga',['2425','2526']),('GreeceSL',['2526'])]
def w(x):
    if x<=0.2: return 1.00
    if x<=0.4: return 0.45
    if x<=0.5: return 0.25
    if x<=0.7: return 0.15
    return 0.05
def build(lg,sea,hf):
    d=json.load(open(f'data_{lg}_{sea}.json')); rows=[]; id2name={}
    for mid,m in d.items():
        if m['hs'] is None: continue
        hid=int(m['home']['id']); aid=int(m['away']['id']); id2name[hid]=m['home']['name']; id2name[aid]=m['away']['name']
        agg={hid:dict(nr=0.,nc=0.,pen=0,ns=0),aid:dict(nr=0.,nc=0.,pen=0,ns=0)}
        for s in m['shots']:
            xg=s.get('xg')
            if xg is None or s['tid'] not in agg: continue
            if s.get('sit')=='Penalty': agg[s['tid']]['pen']+=1
            else: agg[s['tid']]['nr']+=xg; agg[s['tid']]['nc']+=xg*w(xg); agg[s['tid']]['ns']+=1
        reds=m.get('reds',[]); ft=95
        dh=sum(max(0,ft-(r.get('min') or 0)) for r in reds if r['home']); da=sum(max(0,ft-(r.get('min') or 0)) for r in reds if not r['home'])
        for ih,tid,gf,ds,do in [(1,hid,m['hs'],dh,da),(0,aid,m['as'],da,dh)]:
            a=agg[tid]; rx=0.0083*do-0.5*0.0083*ds
            rows.append(dict(mid=mid,date=isodate(m['date']),team=tid,gf=gf,nr=a['nr'],nc=a['nc'],pen=a['pen'],ns=a['ns'],rx=rx,is_home=ih))
    df=pd.DataFrame(rows); sf=df.nr.sum()/df.nc.sum()
    df['xg_model']=df['nc']*sf+0.25*df['pen']+df['rx']; df['ns_eff']=df['ns']+df['pen']+df['rx'].abs()/0.10
    MM=[]
    for mid,g in df.groupby('mid'):
        if len(g)!=2: continue
        h=g[g.is_home==1].iloc[0]; a=g[g.is_home==0].iloc[0]
        MM.append(dict(mid=mid,date=h['date'],home=int(h['team']),away=int(a['team']),hg=int(h['gf']),ag=int(a['gf']),
            h_xg=h['xg_model'],a_xg=a['xg_model'],h_ns=h['ns_eff'],a_ns=a['ns_eff']))
    M=pd.DataFrame(MM).sort_values(['date','mid']).reset_index(drop=True)
    def wm(v):
        n=len(v)
        if n==0: return None
        ww=np.array([DECAY**(n-1-i) for i in range(n)]); return float((ww*np.array(v)).sum()/ww.sum())
    lg_sh=pd.concat([M.h_ns,M.a_ns]).mean(); lg_xp=pd.concat([M.h_xg,M.a_xg]).sum()/pd.concat([M.h_ns,M.a_ns]).sum()
    af=1/hf; hist={}; out=[]
    for _,r in M.iterrows():
        H,A=r['home'],r['away']; hh=hist.get(H); ha=hist.get(A)
        if hh and ha and len(hh['sf'])>=MIN_PRIOR and len(ha['sf'])>=MIN_PRIOR:
            def bx(t,fx,fg): return BLEND*wm(t[fx])+(1-BLEND)*wm(t[fg])
            Hax=bx(hh,'xf','gf')/max(wm(hh['sf']),1e-9); Hdx=bx(hh,'xa','ga')/max(wm(hh['sa']),1e-9)
            Aax=bx(ha,'xf','gf')/max(wm(ha['sf']),1e-9); Adx=bx(ha,'xa','ga')/max(wm(ha['sa']),1e-9)
            eh=(wm(hh['sf'])/lg_sh)*(wm(ha['sa'])/lg_sh)*lg_sh; ea=(wm(ha['sf'])/lg_sh)*(wm(hh['sa'])/lg_sh)*lg_sh
            xh=eh*(Hax*(Adx/lg_xp))*hf; xa=ea*(Aax*(Hdx/lg_xp))*af
            out.append(dict(league=lg,season=sea,date=r['date'],home=H,away=A,home_name=id2name.get(H),away_name=id2name.get(A),
                gd=r['hg']-r['ag'],xg_h=xh,xg_a=xa,model_sup=xh-xa))
        for tid,sf_,xf,sa,xa,gf,ga in [(H,r['h_ns'],r['h_xg'],r['a_ns'],r['a_xg'],r['hg'],r['ag']),(A,r['a_ns'],r['a_xg'],r['h_ns'],r['h_xg'],r['ag'],r['hg'])]:
            hist.setdefault(tid,dict(sf=[],xf=[],sa=[],xa=[],gf=[],ga=[]))
            for k,v in [('sf',sf_),('xf',xf),('sa',sa),('xa',xa),('gf',gf),('ga',ga)]: hist[tid][k].append(v)
    return pd.DataFrame(out)

# predictions ολων
P=pd.concat([build(lg,sea,HFA_FIX[lg]) for lg,seas in JOBS for sea in seas],ignore_index=True)
# timelines: league (δευτερευοντα) + euro
events=[]
for lg,seas in JOBS:
    for sea in seas:
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
def tired3(team,date,ven):
    pm=prevs(team,date,3); venues=[v for _,v,_ in pm[-2:]]+[ven]
    return len(venues)==3 and all(v=='A' for v in venues) and len(pm)>=1 and pm[-1][2] in ('CL','EL','ECL') and pm[-1][1]=='A'
def tired2(team,date,ven):
    if ven!='A': return False
    pm=prevs(team,date,1)
    if not pm: return False
    rest=(d2(date)-d2(pm[-1][0])).days
    return pm[-1][2] in ('CL','EL','ECL') and pm[-1][1]=='A' and 1<=rest<=5

# residuals
for scen,fn in [('3-εκτος',tired3),('2-εκτος',tired2)]:
    res=[]; per={}
    for _,r in P.iterrows():
        for team,ven,proj in [(r['home'],'H',r['model_sup']),(r['away'],'A',-r['model_sup'])]:
            if fn(team,r['date'],ven):
                act=r['gd'] if ven=='H' else -r['gd']
                res.append(act-proj); per.setdefault(r['league'],[]).append(act-proj)
    res=np.array(res)
    print(f"\nΣΕΝΑΡΙΟ {scen} — δευτερευοντα (residual κουρασμενης):")
    if len(res): print(f"  ΟΛΑ: {res.mean():+.3f} (±{res.std()/np.sqrt(len(res)):.3f}), n={len(res)}")
    else: print("  n=0"); continue
    for lg in per: print(f"    {lg}: {np.mean(per[lg]):+.3f}, n={len(per[lg])}")
