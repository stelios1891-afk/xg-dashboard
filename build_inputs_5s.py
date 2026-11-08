"""
build_inputs_5s.py — ΙΔΙΑ ΚΛΕΙΔΩΜΕΝΗ λογικη με build_inputs.py (compression + penalty 0.25
+ red adj + per-league-season rescale), αλλα:
  - ΜΟΝΟ CORE 7 λιγκες
  - ΟΛΕΣ οι διαθεσιμες σεζον (auto-detect· 5: 2122/2223/2324/2425/2526)
  - output → teamgame_inputs_5s.csv (ΔΕΝ πειραζει το production teamgame_inputs.csv)
"""
import json, pandas as pd, numpy as np, glob, os, sys
import red_modes
from datetime import datetime
try: sys.stdout.reconfigure(encoding='utf-8')
except Exception: pass

def isodate(s):
    try:
        return datetime.strptime(s.replace(' UTC',''),'%a, %b %d, %Y, %H:%M').strftime('%Y-%m-%d')
    except Exception:
        return s[:10]

LEAGUES=['EPL','LaLiga','SerieA','Bundesliga','Ligue1','PrimeiraLiga','Eredivisie']   # CORE 7
SEASONS=sorted({os.path.basename(p)[:-5].split('_')[-1]
                for lg in LEAGUES for p in glob.glob(f'data_{lg}_*.json')})

NOCOMP = 'nocomp' in sys.argv   # test-mode: χωρις compression (w=1 παντου)
def w(xg):
    if NOCOMP: return 1.00
    if xg<=0.2: return 1.00
    if xg<=0.4: return 0.45
    if xg<=0.5: return 0.25
    if xg<=0.7: return 0.15
    return 0.05

rows=[]
for lg in LEAGUES:
    for sea in SEASONS:
        path=f'data_{lg}_{sea}.json'
        if not os.path.exists(path): continue
        d=json.load(open(path,encoding='utf-8'))
        for mid,m in d.items():
            hid=int(m['home']['id']); aid=int(m['away']['id'])
            if m['hs'] is None or m['as'] is None: continue
            agg={hid:dict(np_raw=0.0,np_comp=0.0,pen=0,ns=0),
                 aid:dict(np_raw=0.0,np_comp=0.0,pen=0,ns=0)}
            for s in m['shots']:
                xg=s.get('xg')
                if xg is None: continue
                tid=s.get('tid')
                if tid not in agg: continue
                if s.get('sit')=='Penalty':
                    agg[tid]['pen']+=1
                else:
                    agg[tid]['np_raw']+=xg
                    agg[tid]['np_comp']+=xg*w(xg)
                    agg[tid]['ns']+=1
            ft=95; dis_home=0.0; dis_away=0.0
            for r in m['reds']:
                mn=r.get('min') or 0
                dur=max(0,ft-mn)
                if r['home']: dis_home+=dur
                else: dis_away+=dur
            _RADJ=red_modes.live_adj(m)
            for is_home,tid,opp,gf,dis_self,dis_opp in [
                (1,hid,aid,m['hs'],dis_home,dis_away),
                (0,aid,hid,m['as'],dis_away,dis_home)]:
                a=agg[tid]
                # 5/10/2026: κοκκινες = red_modes.LIVE_MODE (εμπειρικη ανα σκορ, σωστη κατευθυνση) — αντι +0.0083 στον πλεονεκτουντα
                _ra=_RADJ[tid]; a=dict(a); a['np_raw']*=_ra['fr']; a['np_comp']*=_ra['fc']; a['ns']*=_ra['fn']
                red_xg=_ra['term']
                rows.append(dict(league=lg,season=sea,mid=mid,date=isodate(m['date']),
                    team=tid,opp=opp,is_home=is_home,gf=gf,
                    np_raw=a['np_raw'],np_comp=a['np_comp'],pen=a['pen'],ns=a['ns'],red_xg=red_xg))

df=pd.DataFrame(rows)
df['comp_np_scaled']=df['np_comp']
for (lg,sea),g in df.groupby(['league','season']):
    sf=g.np_raw.sum()/g.np_comp.sum()
    m=(df.league==lg)&(df.season==sea)
    df.loc[m,'comp_np_scaled']=df.loc[m,'np_comp']*sf
    df.loc[m,'sf']=sf
df['xg_model']=df['comp_np_scaled']+0.25*df['pen']+df['red_xg']
df['ns_eff']=np.maximum(df['ns']+df['pen']+df['red_xg']/0.10, 0.5*(df['ns']+df['pen']))   # 5/10: ψευδο-σουτ με προσημο (red_modes)
df['xgps']=df['xg_model']/df['ns_eff'].clip(lower=1)
df=df.sort_values(['league','season','date','mid','is_home'])
OUT = 'teamgame_inputs_5s_nocomp.csv' if NOCOMP else 'teamgame_inputs_5s.csv'
df.to_csv(OUT,index=False)
print(f"{OUT}: {len(df)} γραμμες-ομαδα ({len(df)//2} ματς)")
print(f"σεζον: {SEASONS}")
print("\nΜατς ανα λιγκα-σεζον:")
print(df.groupby(['league','season']).size().div(2).astype(int).unstack())
