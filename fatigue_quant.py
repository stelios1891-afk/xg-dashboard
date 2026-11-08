import json, pandas as pd, numpy as np
from datetime import datetime

def isodate(s):
    try: return datetime.strptime(s.replace(' UTC',''),'%a, %b %d, %Y, %H:%M').strftime('%Y-%m-%d')
    except: return s[:10]
def d2(s): return datetime.strptime(s,'%Y-%m-%d')
TOP5=['EPL','LaLiga','SerieA','Bundesliga','Ligue1']
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
def prev(team,date,k=3): 
    s=[x for x in tl.get(team,[]) if x[0]<date]; return s[-k:] if s else []

P=pd.read_csv('model_predictions.csv'); P=P[P.league.isin(TOP5)].copy()
# baseline (ολες οι ομαδες-ματς): scored/conceded residual
def collect(filter_tired):
    scored_res=[]; conc_res=[]; gd_res=[]; wins=[]; proj_sc=[]
    for _,r in P.iterrows():
        dt=r['date']
        for team,ven,psc,pco,asc,aco,gd in [
            (int(r['home']),'H',r['xg_h'],r['xg_a'],r['hg'],r['ag'],r['gd']),
            (int(r['away']),'A',r['xg_a'],r['xg_h'],r['ag'],r['hg'],-r['gd'])]:
            pm=prev(team,dt,3); venues=[v for _,v,_ in pm[-2:]]+[ven]
            B=(len(venues)==3 and all(v=='A' for v in venues))
            euro_mid=B and len(pm)>=1 and pm[-1][2] in ('CL','EL','ECL') and pm[-1][1]=='A'
            tired = euro_mid if filter_tired=='euromid' else (True if filter_tired=='all' else B)
            if tired:
                scored_res.append(asc-psc); conc_res.append(aco-pco); gd_res.append(gd-(psc-pco))
                proj_sc.append(psc); wins.append(1 if gd>0 else (0.5 if gd==0 else 0))
    return dict(sc=np.array(scored_res),co=np.array(conc_res),gd=np.array(gd_res),ps=np.array(proj_sc),w=np.array(wins))

base=collect('all'); tired=collect('euromid')
def line(x): return f"{x.mean():+.3f} (±{x.std()/np.sqrt(len(x)):.3f})"
print(f"BASELINE (ολες οι ομαδες, n={len(base['sc'])}):")
print(f"  scored − proj: {line(base['sc'])} | conceded − proj: {line(base['co'])} | win rate: {base['w'].mean():.1%}\n")
print(f"ΚΟΥΡΑΣΜΕΝΕΣ (εκτος/ευρωπη-εκτος/εκτος, n={len(tired['sc'])}):")
print(f"  scored − proj:   {line(tired['sc'])}  <- επιθετικο")
print(f"  conceded − proj: {line(tired['co'])}  <- αμυντικο")
print(f"  win rate: {tired['w'].mean():.1%}  (baseline {base['w'].mean():.1%})\n")

# ποσοστιαια χειροτερευση του xG της κουρασμενης
mean_proj=tired['ps'].mean()
att_drop=tired['sc'].mean()            # απολυτη πτωση scored (vs baseline ~0)
att_pct=att_drop/mean_proj*100
def_add=tired['co'].mean()
print(f"ΠΟΣΟΤΙΚΟΠΟΙΗΣΗ ADJUSTMENT:")
print(f"  Μεσο projected xG κουρασμενης: {mean_proj:.2f}")
print(f"  Επιθετικη πτωση: {att_drop:+.3f} γκολ  =  {att_pct:+.0f}% του xG της")
print(f"  Αμυντικη επιβαρυνση: {def_add:+.3f} γκολ (δεχεται περισσοτερα)")
print(f"  -> Προτεινομενο: xG κουρασμενης ×{1+att_drop/mean_proj:.2f}, xG αντιπαλου ×{1+def_add/(mean_proj):.2f} (περιπου)")
print(f"\n  Συνολικο GD effect: {line(tired['gd'])}")
# ανα σεζον για σταθεροτητα του επιθετικου
print("\n  Επιθετικη πτωση ανα σεζον:")
for sea in ['2425','2526']:
    idx=[]; 
    # rebuild per season quickly
Psea={}
for sea in ['2425','2526']:
    Ps=P[P.season.astype(str)==sea]; sc=[]
    for _,r in Ps.iterrows():
        for team,ven,psc,asc in [(int(r['home']),'H',r['xg_h'],r['hg']),(int(r['away']),'A',r['xg_a'],r['ag'])]:
            pm=prev(team,r['date'],3); venues=[v for _,v,_ in pm[-2:]]+[ven]
            if len(venues)==3 and all(v=='A' for v in venues) and len(pm)>=1 and pm[-1][2] in ('CL','EL','ECL') and pm[-1][1]=='A':
                sc.append(asc-psc)
    sc=np.array(sc); print(f"    {sea}: {sc.mean():+.3f} (±{sc.std()/np.sqrt(max(len(sc),1)):.3f}), n={len(sc)}")
