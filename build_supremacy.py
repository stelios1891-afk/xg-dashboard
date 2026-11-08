import json, pandas as pd, numpy as np

DECAY=0.96
MIN_PRIOR=6          # ελαχιστα προηγουμενα ματς ανα ομαδα για να βγαλουμε προβλεψη

df=pd.read_csv('teamgame_inputs.csv')

# teamId -> name (απο τα data files) για μετεπειτα matching με odds
id2name={}
for lg in ['EPL','LaLiga','SerieA','Bundesliga','Ligue1']:
    for sea in ['2425','2526']:
        d=json.load(open(f'data_{lg}_{sea}.json'))
        for m in d.values():
            id2name[int(m['home']['id'])]=m['home']['name']
            id2name[int(m['away']['id'])]=m['away']['name']

# Ανασυνθεση ανα ματς: ενωνω τις 2 γραμμες-ομαδα
df=df.sort_values(['league','season','date','mid','is_home'])
matches=[]
for (lg,sea,mid),g in df.groupby(['league','season','mid'],sort=False):
    if len(g)!=2: continue
    h=g[g.is_home==1].iloc[0]; a=g[g.is_home==0].iloc[0]
    matches.append(dict(league=lg,season=sea,mid=mid,date=h['date'],
        home=int(h['team']),away=int(a['team']),
        hg=int(h['gf']),ag=int(a['gf']),
        h_xg=h['xg_model'],a_xg=a['xg_model'],
        h_ns=h['ns_eff'],a_ns=a['ns_eff'],
        h_xgps=h['xgps'],a_xgps=a['xgps']))
M=pd.DataFrame(matches).sort_values(['league','season','date','mid']).reset_index(drop=True)

def wmean(vals):
    n=len(vals)
    if n==0: return None
    wts=np.array([DECAY**(n-1-i) for i in range(n)])
    return float(np.sum(wts*np.array(vals))/wts.sum())

out=[]
for (lg,sea),G in M.groupby(['league','season'],sort=False):
    G=G.sort_values(['date','mid']).reset_index(drop=True)
    # ιστορικο ανα ομαδα: shots_for, xg_for, shots_against, xg_against
    hist={}
    # league averages (σταθερα ανα λιγκα-σεζον ως context normalizer)
    lg_shots=pd.concat([G.h_ns,G.a_ns]).mean()
    lg_xgps=(pd.concat([G.h_xg,G.a_xg]).sum())/(pd.concat([G.h_ns,G.a_ns]).sum())
    # per-league HFA: λογος μεσου home xg / away xg (σε goal units)
    hfa_ratio=G.h_xg.mean()/G.a_xg.mean()
    hf=np.sqrt(hfa_ratio); af=1/np.sqrt(hfa_ratio)
    for _,r in G.iterrows():
        H,A=r['home'],r['away']
        hh=hist.get(H); ha=hist.get(A)
        ok = hh is not None and ha is not None and len(hh['sf'])>=MIN_PRIOR and len(ha['sf'])>=MIN_PRIOR
        if ok:
            # rolling decay-weighted ratings (ΠΡΙΝ το ματς)
            H_attsh=wmean(hh['sf']); H_defsh=wmean(hh['sa'])
            A_attsh=wmean(ha['sf']); A_defsh=wmean(ha['sa'])
            H_attx=wmean(hh['xf'])/max(wmean(hh['sf']),1e-9)   # xG/shot attack
            H_defx=wmean(hh['xa'])/max(wmean(hh['sa']),1e-9)   # xG/shot conceded
            A_attx=wmean(ha['xf'])/max(wmean(ha['sf']),1e-9)
            A_defx=wmean(ha['xa'])/max(wmean(ha['sa']),1e-9)
            # expected shots (attack x defense interaction)
            esh_h=(H_attsh/lg_shots)*(A_defsh/lg_shots)*lg_shots
            esh_a=(A_attsh/lg_shots)*(H_defsh/lg_shots)*lg_shots
            # xG/shot (interaction)
            xps_h=H_attx*(A_defx/lg_xgps)
            xps_a=A_attx*(H_defx/lg_xgps)
            xg_h=esh_h*xps_h*hf
            xg_a=esh_a*xps_a*af
            out.append(dict(league=lg,season=sea,mid=r['mid'],date=r['date'],
                home=H,away=A,home_name=id2name.get(H),away_name=id2name.get(A),
                hg=r['hg'],ag=r['ag'],gd=r['hg']-r['ag'],
                model_sup=xg_h-xg_a,xg_h=xg_h,xg_a=xg_a))
        # update ιστορικο ΜΕΤΑ την προβλεψη (το τρεχον ματς μπαινει για τα επομενα)
        for tid,sf,xf,sa,xa in [(H,r['h_ns'],r['h_xg'],r['a_ns'],r['a_xg']),
                                (A,r['a_ns'],r['a_xg'],r['h_ns'],r['h_xg'])]:
            hist.setdefault(tid,dict(sf=[],xf=[],sa=[],xa=[]))
            hist[tid]['sf'].append(sf); hist[tid]['xf'].append(xf)
            hist[tid]['sa'].append(sa); hist[tid]['xa'].append(xa)

P=pd.DataFrame(out)
P.to_csv('model_predictions.csv',index=False)
print(f"Προβλεψεις (pre-match, ≥{MIN_PRIOR} προηγ. ματς): {len(P)} / {len(M)} ματς")
print(f"\nΑναλογια ανα λιγκα-σεζον:")
print(P.groupby(['league','season']).size().unstack(fill_value=0))
print(f"\nΣυνολικο correlation model_sup vs actual GD: {P.model_sup.corr(P.gd):.4f}")
print(f"Μεσο model_sup: {P.model_sup.mean():.3f} | μεσο actual GD: {P.gd.mean():.3f}")
