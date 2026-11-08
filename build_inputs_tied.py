"""
build_inputs_tied.py  -  ΑΝΤΙΓΡΑΦΟ του build_inputs.py, ΜΟΝΟ tied-state xG/σουτ.

Διαφορα απο το κανονικο: κραταμε ΜΟΝΟ τα σουτ (& penalties) που εγιναν οταν το σκορ
ητανε ισοπαλο (0-0, 1-1, ...), ανακατασκευαζοντας το σκορ τη στιγμη καθε σουτ απο τα
λεπτα των γκολ (FotMob goal-shots). Το red-advantage μετραει μονο λεπτα ισοπαλιας.
ΟΛΑ τα υπολοιπα ιδια (compression, rescale, penalty 0.25, red formula).

ΣΗΜΕΙΩΣΗ: τα ΓΚΟΛ (gf) μενουν ΤΕΛΙΚΑ (full-match) — χρησιμοποιουνται στο 20% goals-blend
και στο settlement του στοιχηματος. Tied-state εφαρμοζεται στα xG/σουτ (το 80% component).
Περιορισμος: τα own goals δεν υπαρχουν στα shot data (φιλτραρονται στο dl), αρα η
ανακατασκευη σκορ τα αγνοει (σπανιο).

Γραφει: teamgame_inputs_tied.csv   (ΔΕΝ πειραζει το κανονικο teamgame_inputs.csv)
"""
import json, pandas as pd, numpy as np, glob, os, sys
from datetime import datetime
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

def isodate(s):
    try:
        return datetime.strptime(s.replace(' UTC',''),'%a, %b %d, %Y, %H:%M').strftime('%Y-%m-%d')
    except Exception:
        return s[:10]

LEAGUES=['EPL','LaLiga','SerieA','Bundesliga','Ligue1']
SEASONS=sorted({os.path.basename(p)[:-5].split('_')[-1]
                for lg in LEAGUES for p in glob.glob(f'data_{lg}_*.json')})

def w(xg):
    if xg<=0.2: return 1.00
    if xg<=0.4: return 0.45
    if xg<=0.5: return 0.25
    if xg<=0.7: return 0.15
    return 0.05

rows=[]
# counters για report δειγματος
tot_np=kept_np=tot_pen=kept_pen=nomin=0
tot_matches=ownfoul=0

for lg in LEAGUES:
    for sea in SEASONS:
        path=f'data_{lg}_{sea}.json'
        if not os.path.exists(path): continue
        d=json.load(open(path,encoding='utf-8'))
        for mid,m in d.items():
            hid=int(m['home']['id']); aid=int(m['away']['id'])
            if m['hs'] is None or m['as'] is None: continue
            tot_matches+=1
            # --- goal timeline (goal-shots με λεπτο) ---
            goals=[(s.get('min'), s.get('tid')) for s in m['shots']
                   if s.get('goal') and s.get('min') is not None]
            # sanity: goal-shots vs τελικο σκορ (mismatch ~ own goals)
            gh=sum(1 for gm,gt in goals if gt==hid); ga_=sum(1 for gm,gt in goals if gt==aid)
            if gh!=m['hs'] or ga_!=m['as']: ownfoul+=1
            def score_before(mn):
                h=sum(1 for gm,gt in goals if gm is not None and gm<mn and gt==hid)
                a=sum(1 for gm,gt in goals if gm is not None and gm<mn and gt==aid)
                return h,a
            agg={hid:dict(np_raw=0.0,np_comp=0.0,pen=0,ns=0),
                 aid:dict(np_raw=0.0,np_comp=0.0,pen=0,ns=0)}
            for s in m['shots']:
                xg=s.get('xg')
                if xg is None: continue
                tid=s.get('tid')
                if tid not in agg: continue
                is_pen = s.get('sit')=='Penalty'
                if is_pen: tot_pen+=1
                else: tot_np+=1
                mn=s.get('min')
                if mn is None:
                    nomin+=1; continue          # δεν μπορω να ξερω το σκορ -> εκτος
                h,a=score_before(mn)
                if h!=a:                          # ΟΧΙ ισοπαλια -> πεταμε το σουτ
                    continue
                if is_pen:
                    agg[tid]['pen']+=1; kept_pen+=1
                else:
                    agg[tid]['np_raw']+=xg; agg[tid]['np_comp']+=xg*w(xg); agg[tid]['ns']+=1; kept_np+=1
            # --- red-card disadvantage minutes ΜΟΝΟ σε λεπτα ισοπαλιας ---
            ft=95
            dis_home=0.0; dis_away=0.0
            has_red = len(m['reds'])>0
            if has_red:
                for t in range(ft):
                    h=sum(1 for gm,gt in goals if gm is not None and gm<=t and gt==hid)
                    a=sum(1 for gm,gt in goals if gm is not None and gm<=t and gt==aid)
                    if h!=a: continue
                    home_down=any(r['home'] and (r.get('min') or 0)<=t for r in m['reds'])
                    away_down=any((not r['home']) and (r.get('min') or 0)<=t for r in m['reds'])
                    if home_down: dis_home+=1
                    if away_down: dis_away+=1
            for is_home,tid,opp,gf,dis_self,dis_opp in [
                (1,hid,aid,m['hs'],dis_home,dis_away),
                (0,aid,hid,m['as'],dis_away,dis_home)]:
                a=agg[tid]
                adv_min=dis_opp; own_dis=dis_self
                red_xg=0.0083*adv_min - 0.5*0.0083*own_dis
                rows.append(dict(league=lg,season=sea,mid=mid,date=isodate(m['date']),
                    team=tid,opp=opp,is_home=is_home,gf=gf,
                    np_raw=a['np_raw'],np_comp=a['np_comp'],pen=a['pen'],ns=a['ns'],
                    red_xg=red_xg))

df=pd.DataFrame(rows)
df['comp_np_scaled']=df['np_comp']
for (lg,sea),g in df.groupby(['league','season']):
    sf=g.np_raw.sum()/g.np_comp.sum() if g.np_comp.sum()>0 else 1.0
    mask=(df.league==lg)&(df.season==sea)
    df.loc[mask,'comp_np_scaled']=df.loc[mask,'np_comp']*sf
    df.loc[mask,'sf']=sf
df['xg_model']=df['comp_np_scaled']+0.25*df['pen']+df['red_xg']
df['ns_eff']=df['ns']+df['pen']+(df['red_xg'].abs()/0.10)
df['xgps']=df['xg_model']/df['ns_eff'].clip(lower=1)
df=df.sort_values(['league','season','date','mid','is_home'])
df.to_csv('teamgame_inputs_tied.csv',index=False)

print("=== ΔΕΙΓΜΑ ΠΟΥ ΚΡΑΤΗΘΗΚΕ (tied-state) ===")
print(f"non-penalty σουτ:  κρατηθηκαν {kept_np:6d} / {tot_np:6d}  ({100*kept_np/tot_np:.1f}%)  -> πεταχτηκαν {tot_np-kept_np}")
print(f"penalties:         κρατηθηκαν {kept_pen:6d} / {tot_pen:6d}  ({100*kept_pen/max(tot_pen,1):.1f}%)")
print(f"σουτ χωρις λεπτο (εκτος): {nomin}")
print(f"ματς: {tot_matches}  |  με mismatch goal-shots vs σκορ (πιθανα own goals): {ownfoul}")
print(f"\nteamgame_inputs_tied.csv: {len(df)} γραμμες-ομαδα")
print("Μεσο xg_model/ομαδα ανα λιγκα-σεζον (tied):")
print(df.groupby(['league','season']).xg_model.mean().round(3).unstack())
