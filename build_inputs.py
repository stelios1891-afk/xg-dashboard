import json, pandas as pd, numpy as np, glob, os, sys
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

def isodate(s):
    # "Fri, Aug 16, 2024, 19:00 UTC" -> "2024-08-16"
    try:
        return datetime.strptime(s.replace(' UTC',''),'%a, %b %d, %Y, %H:%M').strftime('%Y-%m-%d')
    except Exception:
        return s[:10]

LEAGUES=['EPL','LaLiga','SerieA','Bundesliga','Ligue1','Belgium','ScottishPrem','PrimeiraLiga']
# αυτο-ανιχνευση σεζον απο τα data files των top-5 (ωστε να πιανει αυτοματα και τη νεα σεζον)
SEASONS=sorted({os.path.basename(p)[:-5].split('_')[-1]
                for lg in LEAGUES for p in glob.glob(f'data_{lg}_*.json')})

def w(xg):
    if xg<=0.2: return 1.00
    if xg<=0.4: return 0.45
    if xg<=0.5: return 0.25
    if xg<=0.7: return 0.15
    return 0.05

rows=[]
for lg in LEAGUES:
    for sea in SEASONS:
        path=f'data_{lg}_{sea}.json'
        if not os.path.exists(path):
            continue
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
                    agg[tid]['pen']+=1            # penalty: fixed 0.25, εκτος compression
                else:
                    agg[tid]['np_raw']+=xg
                    agg[tid]['np_comp']+=xg*w(xg)
                    agg[tid]['ns']+=1
            # red-card disadvantage minutes (full time ~ max shot min, cap 95)
            ft=95
            dis_home=0.0; dis_away=0.0   # λεπτα που η ομαδα παιζει με 10
            for r in m['reds']:
                mn=r.get('min') or 0
                dur=max(0,ft-mn)
                if r['home']: dis_home+=dur
                else: dis_away+=dur
            for is_home,tid,opp,gf,dis_self,dis_opp in [
                (1,hid,aid,m['hs'],dis_home,dis_away),
                (0,aid,hid,m['as'],dis_away,dis_home)]:
                a=agg[tid]
                # red adj ως xG (pseudo-shots): +0.0083×(λεπτα με αριθμ.πλεονεκτημα) − μισο για μειονεκτημα
                adv_min=dis_opp; own_dis=dis_self
                red_xg=0.0083*adv_min - 0.5*0.0083*own_dis
                rows.append(dict(league=lg,season=sea,mid=mid,date=isodate(m['date']),
                    team=tid,opp=opp,is_home=is_home,gf=gf,
                    np_raw=a['np_raw'],np_comp=a['np_comp'],pen=a['pen'],ns=a['ns'],
                    red_xg=red_xg))

df=pd.DataFrame(rows)
# Per-league-season rescale του compressed NON-penalty, ωστε Σcomp_np==Σraw_np
df['comp_np_scaled']=df['np_comp']
for (lg,sea),g in df.groupby(['league','season']):
    sf=g.np_raw.sum()/g.np_comp.sum()
    m=(df.league==lg)&(df.season==sea)
    df.loc[m,'comp_np_scaled']=df.loc[m,'np_comp']*sf
    df.loc[m,'sf']=sf
# Τελικο xG: compressed non-penalty (rescaled) + penalty×0.25 (fixed) + red adj
df['xg_model']=df['comp_np_scaled']+0.25*df['pen']+df['red_xg']
# Pseudo-shots για το red adj (Q=0.10) ωστε να μη χαλαει το xG/shot
df['ns_eff']=df['ns']+df['pen']+(df['red_xg'].abs()/0.10)
df['xgps']=df['xg_model']/df['ns_eff'].clip(lower=1)   # xG per (effective) shot
df=df.sort_values(['league','season','date','mid','is_home'])
df.to_csv('teamgame_inputs.csv',index=False)
print(f"teamgame_inputs: {len(df)} γραμμες-ομαδα ({len(df)//2} ματς)")
print("\nΜεσο xG_model/ομαδα ανα λιγκα-σεζον:")
print(df.groupby(['league','season']).xg_model.mean().round(3).unstack())
print("\nΔειγμα:")
print(df[['league','season','date','team','opp','is_home','gf','ns','xg_model','xgps']].head(4).to_string(index=False))
