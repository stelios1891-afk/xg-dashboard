import pandas as pd, numpy as np, unicodedata, re
from scipy.stats import norm as N

SIGMA=1.6   # τυπικη αποκλιση goal difference (κανονικη προσεγγιση)

P=pd.read_csv('model_predictions.csv')

def norm(s):
    s=unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().lower()
    toks=set(re.sub(r'[^a-z ]',' ',s).split())
    return frozenset(toks-{'fc','cf','ac','calcio','club','de','afc','cp','ss','us','as',
        'rc','ud','sd','sc','rcd','real','1','vfl','vfb','tsg','sv','bsc','og'})

ALIAS={'Athletic Club':'Ath Bilbao','Borussia Mönchengladbach':"M'gladbach",
       'Espanyol':'Espanol','Hamburger SV':'Hamburg','Wolverhampton Wanderers':'Wolves'}

# Φορτωσε ολα τα odds
od=[]
for lg in ['EPL','LaLiga','SerieA','Bundesliga','Ligue1']:
    for sea in ['2425','2526']:
        o=pd.read_csv(f'odds/{lg}_{sea}.csv',encoding='latin-1')
        o['league']=lg; o['season']=sea
        od.append(o)
O=pd.concat(od,ignore_index=True)

def best_odds(row):
    # προτεραιοτητα: Betfair Exchange closing -> Pinnacle closing -> Avg closing
    for hh,ha in [('BFECAHH','BFECAHA'),('PCAHH','PCAHA'),('AvgCAHH','AvgCAHA')]:
        if hh in row and ha in row and pd.notna(row[hh]) and pd.notna(row[ha]):
            return row[hh],row[ha]
    return np.nan,np.nan

def fm_norm(name):
    return norm(ALIAS.get(name,name))

# index odds by (season, home_raw, away_raw) + resolver fm_name -> fd_name (best overlap)
O['hn']=O.HomeTeam.apply(norm); O['an']=O.AwayTeam.apply(norm)
Omap={}
for _,r in O.iterrows():
    Omap[(str(r['season']),r['HomeTeam'],r['AwayTeam'])]=r

fd_names={}
for _,r in O.iterrows():
    fd_names[r['HomeTeam']]=r['hn']; fd_names[r['AwayTeam']]=r['an']

def resolve(fm_name):
    tn=fm_norm(fm_name)
    best=None; bs=0; bj=0
    for raw,tg in fd_names.items():
        ov=len(tn&tg)
        if ov==0: continue
        j=ov/max(len(tn|tg),1)
        if ov>bs or (ov==bs and j>bj): bs=ov; bj=j; best=raw
    return best
RES={n:resolve(n) for n in set(P.home_name)|set(P.away_name)}

rows=[]
miss=0
for _,p in P.iterrows():
    fh=RES.get(p['home_name']); fa=RES.get(p['away_name'])
    o=Omap.get((str(p['season']),fh,fa)) if fh and fa else None
    if o is None:
        miss+=1; continue
    line=o.get('AHCh')
    oh,oa=best_odds(o)
    if pd.isna(line) or pd.isna(oh) or pd.isna(oa): continue
    ph=(1/oh)/((1/oh)+(1/oa))                      # no-vig P(home covers)
    market_sup=-float(line)+SIGMA*N.ppf(min(max(ph,1e-4),1-1e-4))
    rows.append(dict(league=p['league'],season=str(p['season']),mid=p['mid'],
        gd=p['gd'],model_sup=p['model_sup'],market_sup=market_sup,line=float(line)))

D=pd.DataFrame(rows)
print(f"Ματς με odds match: {len(D)} / {len(P)} (χαθηκαν {miss} σε matching)")
D.to_csv('compare_corr.csv',index=False)

def block(d,label):
    cm=d.model_sup.corr(d.gd); ck=d.market_sup.corr(d.gd)
    cmk=d.model_sup.corr(d.market_sup)
    print(f"{label:24s} n={len(d):4d} | model↔GD {cm:.3f} | market↔GD {ck:.3f} | model↔market {cmk:.3f}")
    return cm,ck

print("\n=== CORRELATION με actual goal difference ===")
print(f"{'':24s} {'':9s} {'ΜΟΝΤΕΛΟ':>10s} {'ΑΓΟΡΑ':>13s}")
block(D,'ΣΥΝΟΛΟ (ολα)')
print()
for sea in ['2425','2526']:
    block(D[D.season==sea],f'Σεζον {sea}')
print()
for lg in ['EPL','LaLiga','SerieA','Bundesliga','Ligue1']:
    block(D[D.league==lg],lg)
