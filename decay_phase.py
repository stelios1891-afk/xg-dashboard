import pandas as pd, numpy as np, json

BLEND=0.80; MIN_PRIOR=6
DECAYS=[0.99,0.96,0.92,0.88,0.85]

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
                md=(len(hh['sf'])+len(ha['sf']))/2+1     # προσεγγιση αγωνιστικης
                # form deviation (transition): |φορμα5 - baseline| σε xG_for, μεσος 2 ομαδων
                def dev(t):
                    xf=t['xf']
                    if len(xf)<5: return 0.0
                    return abs(np.mean(xf[-5:])-np.mean(xf))
                fdev=(dev(hh)+dev(ha))/2
                out.append(dict(mid=r['mid'],gd=r['hg']-r['ag'],model_sup=xg_h-xg_a,md=md,fdev=fdev))
            for tid,sf,xf,sa,xa,gf,ga in [(H,r['h_ns'],r['h_xg'],r['a_ns'],r['a_xg'],r['hg'],r['ag']),
                                          (A,r['a_ns'],r['a_xg'],r['h_ns'],r['h_xg'],r['ag'],r['hg'])]:
                hist.setdefault(tid,dict(sf=[],xf=[],sa=[],xa=[],gf=[],ga=[]))
                for k,v in [('sf',sf),('xf',xf),('sa',sa),('xa',xa),('gf',gf),('ga',ga)]: hist[tid][k].append(v)
    return pd.DataFrame(out)

# transition threshold: top 30% form-deviation (σταθερο, απο το τρεχον decay)
ref=build(0.96); thr=ref.fdev.quantile(0.70)

print("CORRELATION (model_sup vs actual GD) ανα ΦΑΣΗ ΣΕΖΟΝ και decay:\n")
print(f"{'decay':>6s} | {'αρχη (md 7-18)':>15s} {'ΜΕΣΟ (md 19-32)':>16s} {'τελος (md 33+)':>15s}")
res={}
for D in DECAYS:
    P=build(D); res[D]=P
    early=P[(P.md>=7)&(P.md<=18)]; mid=P[(P.md>=19)&(P.md<=32)]; late=P[P.md>=33]
    print(f"{D:>6.2f} | {early.model_sup.corr(early.gd):>15.3f} {mid.model_sup.corr(mid.gd):>16.3f} {late.model_sup.corr(late.gd):>15.3f}   (n {len(early)}/{len(mid)}/{len(late)})")

print("\nCORRELATION ανα decay: ΣΤΑΘΕΡΕΣ ομαδες vs ομαδες ΣΕ ΜΕΤΑΒΑΣΗ (top 30% form swing):\n")
print(f"{'decay':>6s} | {'σταθερες':>10s} {'σε μεταβαση':>12s}")
for D in DECAYS:
    P=res[D]
    stab=P[P.fdev<thr]; trans=P[P.fdev>=thr]
    print(f"{D:>6.2f} | {stab.model_sup.corr(stab.gd):>10.3f} {trans.model_sup.corr(trans.gd):>12.3f}   (n {len(stab)}/{len(trans)})")

# ΜΕΣΟ-ΣΕΖΟΝ ειδικα στις ομαδες σε μεταβαση (η ακριβης υποθεση)
print("\nΕΣΤΙΑΣΗ: ομαδες ΣΕ ΜΕΤΑΒΑΣΗ, ΜΟΝΟ στο μεσο-σεζον (md 19-32):")
print(f"{'decay':>6s} | {'corr':>8s}")
for D in DECAYS:
    P=res[D]; sub=P[(P.fdev>=thr)&(P.md>=19)&(P.md<=32)]
    print(f"{D:>6.2f} | {sub.model_sup.corr(sub.gd):>8.3f}   (n {len(sub)})")
