import json, pandas as pd, numpy as np, unicodedata, re
from datetime import datetime
from math import exp, factorial

BLEND=0.80; MIN_PRIOR=6; DECAY=0.96
EDGE=0.10; OMIN,OMAX=1.70,2.10; MIN_LINE=0.5; DRAW_BOOST=1.13
F=[factorial(i) for i in range(13)]
# Bundesliga2/Eredivisie/PrimeiraLiga: 2 σεζον. GreeceSL: μονο 2526
JOBS=[('Bundesliga2',['2425','2526']),('Eredivisie',['2425','2526']),
      ('PrimeiraLiga',['2425','2526']),('GreeceSL',['2526'])]

def isodate(s):
    try: return datetime.strptime(s.replace(' UTC',''),'%a, %b %d, %Y, %H:%M').strftime('%Y-%m-%d')
    except: return s[:10]
def w(x):
    if x<=0.2: return 1.00
    if x<=0.4: return 0.45
    if x<=0.5: return 0.25
    if x<=0.7: return 0.15
    return 0.05

def build(lg,sea):
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
    hf=np.sqrt(M.h_xg.mean()/M.a_xg.mean()); af=1/hf; hist={}; out=[]
    for _,r in M.iterrows():
        H,A=r['home'],r['away']; hh=hist.get(H); ha=hist.get(A)
        if hh and ha and len(hh['sf'])>=MIN_PRIOR and len(ha['sf'])>=MIN_PRIOR:
            def bx(t,fx,fg): return BLEND*wm(t[fx])+(1-BLEND)*wm(t[fg])
            Hax=bx(hh,'xf','gf')/max(wm(hh['sf']),1e-9); Hdx=bx(hh,'xa','ga')/max(wm(hh['sa']),1e-9)
            Aax=bx(ha,'xf','gf')/max(wm(ha['sf']),1e-9); Adx=bx(ha,'xa','ga')/max(wm(ha['sa']),1e-9)
            eh=(wm(hh['sf'])/lg_sh)*(wm(ha['sa'])/lg_sh)*lg_sh; ea=(wm(ha['sf'])/lg_sh)*(wm(hh['sa'])/lg_sh)*lg_sh
            xh=eh*(Hax*(Adx/lg_xp))*hf; xa=ea*(Aax*(Hdx/lg_xp))*af
            out.append(dict(home_name=id2name.get(H),away_name=id2name.get(A),gd=r['hg']-r['ag'],xg_h=xh,xg_a=xa,model_sup=xh-xa))
        for tid,sf_,xf,sa,xa,gf,ga in [(H,r['h_ns'],r['h_xg'],r['a_ns'],r['a_xg'],r['hg'],r['ag']),(A,r['a_ns'],r['a_xg'],r['h_ns'],r['h_xg'],r['ag'],r['hg'])]:
            hist.setdefault(tid,dict(sf=[],xf=[],sa=[],xa=[],gf=[],ga=[]))
            for k,v in [('sf',sf_),('xf',xf),('sa',sa),('xa',xa),('gf',gf),('ga',ga)]: hist[tid][k].append(v)
    return pd.DataFrame(out)

def norm(s):
    s=unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().lower()
    return frozenset(set(re.sub(r'[^a-z ]',' ',s).split())-{'fc','cf','ac','calcio','club','de','afc','ss','us','as','rc','ud','sd','sc','rcd','real','1','vfl','vfb','tsg','sv','bsc','og'})
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
def bet_season(P,lg,sea):
    O=pd.read_csv(f'odds2/{lg}_{sea}.csv',encoding='latin-1')
    fdn={}
    for _,r in O.iterrows():
        if pd.notna(r.get('HomeTeam')): fdn[r['HomeTeam']]=norm(r['HomeTeam'])
        if pd.notna(r.get('AwayTeam')): fdn[r['AwayTeam']]=norm(r['AwayTeam'])
    def res(n):
        tn=norm(n); best=None;bs=0;bj=0
        for raw,tg in fdn.items():
            ov=len(tn&tg)
            if ov>bs or (ov==bs and ov/max(len(tn|tg),1)>bj): bs=ov;bj=ov/max(len(tn|tg),1);best=raw
        return best if bs>0 else None
    Om={}
    for _,r in O.iterrows(): Om[(r['HomeTeam'],r['AwayTeam'])]=r
    RC={}; pnls=[]
    for _,r in P.iterrows():
        tot=r['xg_h']+r['xg_a']; sup=r['model_sup']; lh=max((tot+sup)/2,0.05); la=max((tot-sup)/2,0.05); gd=gd_dist(lh,la)
        fh=RC.setdefault(r['home_name'],res(r['home_name'])); fa=RC.setdefault(r['away_name'],res(r['away_name']))
        o=Om.get((fh,fa)) if fh and fa else None
        if o is None: continue
        line=o.get('AHh')
        oh=oa=None
        for hh,ha in [('BFEAHH','BFEAHA'),('PAHH','PAHA'),('AvgAHH','AvgAHA')]:
            if pd.notna(o.get(hh)) and pd.notna(o.get(ha)): oh,oa=float(o[hh]),float(o[ha]); break
        if pd.isna(line) or oh is None: continue
        line=float(line)
        for side,ud,odds in [(1,line,oh),(-1,-line,oa)]:
            if ud<MIN_LINE or not(OMIN<=odds<=OMAX): continue
            pw=pp=0.
            for k,p in gd.items():
                m=(k if side==1 else -k)+ud
                if m>0.01: pw+=p
                elif abs(m)<0.01: pp+=p
            if pw*(odds-1)-(1-pw-pp)>=EDGE: pnls.append(settle(r['gd'],side,ud,odds))
    return np.array(pnls)

print(f"{'πρωταθλημα':14s} {'24/25':>16s} {'25/26':>16s} {'ΣΥΝΟΛΟ (2 σεζον)':>18s}")
print("─"*68)
allp={}
for lg,seas in JOBS:
    cells={}; combined=[]
    for sea in ['2425','2526']:
        if sea not in seas: cells[sea]='—'; continue
        P=build(lg,sea); pn=bet_season(P,lg,sea); combined.append(pn)
        cells[sea]=f"{pn.mean():+.1%}±{pn.std()/np.sqrt(len(pn)):.0%} (n{len(pn)})" if len(pn) else "n0"
    C=np.concatenate(combined) if combined else np.array([])
    comb=f"{C.mean():+.1%} ±{C.std()/np.sqrt(len(C)):.1%} (n{len(C)})" if len(C) else "—"
    print(f"{lg:14s} {cells['2425']:>16s} {cells['2526']:>16s} {comb:>18s}")
