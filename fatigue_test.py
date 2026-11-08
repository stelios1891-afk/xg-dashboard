import json, pandas as pd, numpy as np
from datetime import datetime

def isodate(s):
    try: return datetime.strptime(s.replace(' UTC',''),'%a, %b %d, %Y, %H:%M').strftime('%Y-%m-%d')
    except: return s[:10]
def d2(s): return datetime.strptime(s,'%Y-%m-%d')

TOP5=['EPL','LaLiga','SerieA','Bundesliga','Ligue1']
# 1) league fixtures (ολα τα ματς με ημερομηνια/εδρα) ανα ομαδα
events=[]  # (date, team, venue, comp)
for lg in TOP5:
    for sea in ['2425','2526']:
        d=json.load(open(f'data_{lg}_{sea}.json'))
        for m in d.values():
            if m['hs'] is None: continue
            dt=isodate(m['date']); h=int(m['home']['id']); a=int(m['away']['id'])
            events.append((dt,h,'H','LEAGUE')); events.append((dt,a,'A','LEAGUE'))
# 2) ευρωπαικα
euro=json.load(open('euro_fixtures.json'))
for e in euro:
    events.append((e['date'],e['home'],'H',e['comp'])); events.append((e['date'],e['away'],'A',e['comp']))
# 3) timeline ανα ομαδα
tl={}
for dt,t,v,c in events: tl.setdefault(t,[]).append((dt,v,c))
for t in tl: tl[t]=sorted(set(tl[t]),key=lambda x:x[0])

def prev_matches(team,date,k=3):
    seq=[x for x in tl.get(team,[]) if x[0]<date]
    return seq[-k:] if seq else []

# 4) flag σεναρια σε καθε league ματς
P=pd.read_csv('model_predictions.csv'); P=P[P.league.isin(TOP5)].copy()
def scen(team,date,cur_venue):
    pm=prev_matches(team,date,3)
    A=False; B=False
    if pm:
        pd_,pv,pc=pm[-1]
        rest=(d2(date)-d2(pd_)).days
        if pc in ('CL','EL','ECL') and pv=='A' and 1<=rest<=4: A=True   # ευρωπαικο εκτος μεσοβδομαδα
    # 3 σερι εκτος (τρεχον + 2 προηγουμενα venues == A)
    venues=[v for _,v,_ in pm[-2:]]+[cur_venue]
    if len(venues)==3 and all(v=='A' for v in venues): B=True
    return A,B

rows=[]
for _,r in P.iterrows():
    dt=r['date']
    for team,venue,proj,act in [(int(r['home']),'H',r['model_sup'],r['gd']),
                                (int(r['away']),'A',-r['model_sup'],-r['gd'])]:
        A,B=scen(team,dt,venue)
        # residual απο σκοπια της ομαδας: actual - projected (αρνητικο = υπο-αποδοση)
        rows.append(dict(scenA=A,scenB=B,resid=act-proj,proj=proj))
D=pd.DataFrame(rows)

base=D.resid.mean()
print(f"Baseline μεσο residual (ολες οι ομαδες-ματς): {base:+.3f}  (n={len(D)})")
print(f"  [residual = actual − projected· ~0 σημαινει το μοντελο ειναι καλιμπραρισμενο]\n")
for lab,mask in [("Σεναριο Α: ευρωπαικο ΕΚΤΟΣ μεσοβδομαδα -> μετα",D.scenA),
                 ("Σεναριο Β: 3 σερι εκτος εδρας",D.scenB),
                 ("Α ή Β (οποιαδηποτε κοπωση)",D.scenA|D.scenB)]:
    g=D[mask]
    if len(g):
        diff=g.resid.mean()-base; se=g.resid.std()/np.sqrt(len(g))
        print(f"{lab}")
        print(f"   n={len(g)} | μεσο residual {g.resid.mean():+.3f} (±{se:.3f}) | vs baseline: {diff:+.3f}")
        print(f"   -> κουρασμενη ομαδα {'ΥΠΟαποδιδει' if diff<0 else 'ΥΠΕΡαποδιδει'} κατα {abs(diff):.3f} γκολ vs projection\n")

# Βαθυτερη αναλυση σεναριου Β
print("="*60)
print("ΑΝΑΛΥΣΗ ΣΕΝΑΡΙΟΥ Β (3 σερι εκτος) — ειναι σταθερο;\n")
# ξαναφτιαχνω με season + euro-middle flag
P2=pd.read_csv('model_predictions.csv'); P2=P2[P2.league.isin(TOP5)].copy()
rows2=[]
for _,r in P2.iterrows():
    dt=r['date']
    for team,venue,proj,act in [(int(r['home']),'H',r['model_sup'],r['gd']),(int(r['away']),'A',-r['model_sup'],-r['gd'])]:
        pm=prev_matches(team,dt,3)
        venues=[v for _,v,_ in pm[-2:]]+[venue]
        B=(len(venues)==3 and all(v=='A' for v in venues))
        # ευρωπη στη μεση: το προηγουμενο (pm[-1]) ηταν ευρωπαικο εκτος
        euro_mid=False
        if B and len(pm)>=1:
            _,pv,pc=pm[-1]
            if pc in ('CL','EL','ECL') and pv=='A': euro_mid=True
        rows2.append(dict(season=str(r['season']),scenB=B,euro_mid=euro_mid,resid=act-proj))
D2=pd.DataFrame(rows2); base2=D2.resid.mean()
for sea in ['2425','2526']:
    g=D2[(D2.scenB)&(D2.season==sea)]
    print(f"  Β σεζον {sea}: n={len(g)} | residual {g.resid.mean():+.3f} (±{g.resid.std()/np.sqrt(max(len(g),1)):.3f})")
gm=D2[D2.euro_mid]
print(f"\n  Β + ευρωπη στη μεση (ακριβως: εκτος/ευρωπη-εκτος/εκτος):")
print(f"     n={len(gm)} | residual {gm.resid.mean():+.3f} (±{gm.resid.std()/np.sqrt(max(len(gm),1)):.3f})")
gb=D2[(D2.scenB)&(~D2.euro_mid)]
print(f"  Β χωρις ευρωπη (3 εκτος καθαρα πρωταθλημα/κυπελλο):")
print(f"     n={len(gb)} | residual {gb.resid.mean():+.3f} (±{gb.resid.std()/np.sqrt(max(len(gb),1)):.3f})")
