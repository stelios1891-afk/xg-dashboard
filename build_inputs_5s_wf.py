"""
build_inputs_5s_wf.py — ΑΝΤΙΓΡΑΦΟ του build_inputs_5s.py με ΜΟΝΗ αλλαγη τον rescale factor sf:
  παλιο: sf = Σnp_raw/Σnp_comp ανα λιγκα-σεζον απο ΟΛΟΚΛΗΡΗ τη σεζον (look-ahead)
  νεο:   sf WALK-FORWARD ανα ματς, οπως το live add_current_season.py (KF=4):
           live_d = Σnp_raw/Σnp_comp των ματς της ιδιας λιγκας-σεζον με ημερομηνια < d (αυστηρα)
           md_d   = 2·(πληθος αυτων των ματς)/(ομαδες λιγκας)  [= γραμμες-ομαδα/ομαδες, ΟΠΩΣ το live: md = len(g)/nunique(team) = αγωνιστικες]
           prior  = full-season ratio της ΠΡΟΗΓΟΥΜΕΝΗΣ σεζον της ιδιας λιγκας (ιδια δεδομενα)
           sf_d   = prior·(live_d/prior)^(md_d/(md_d+KF))
           md_d=0 -> sf_d = prior
           χωρις περσινη (2122): sf_d = live_d· και για md_d=0 -> 1.0  (ΣΗΜΕΙΩΣΗ: η 2122
             χρησιμοποιειται ΜΟΝΟ ως prior στο backtest, δεν παιζονται στοιχηματα)
  Σεζον ΚΛΕΙΔΩΜΕΝΕΣ στις 5 του teamgame_inputs_5s.csv (2122-2526) — ΟΧΙ auto-detect (υπαρχει
  πλεον data_*_2627.json), ωστε η συγκριση με το παλιο csv να ειναι ιδια βαση.
  Εξοδος: teamgame_inputs_5s_wf.csv = ιδιες στηλες + sf_wf, md_wf (η στηλη sf = full-season, για ελεγχο).
ΔΕΝ πειραζει το build_inputs_5s.py ουτε το teamgame_inputs_5s.csv.
"""
import json, pandas as pd, numpy as np, os, sys
from datetime import datetime
try: sys.stdout.reconfigure(encoding='utf-8')
except Exception: pass

def isodate(s):
    try:
        return datetime.strptime(s.replace(' UTC',''),'%a, %b %d, %Y, %H:%M').strftime('%Y-%m-%d')
    except Exception:
        return s[:10]

LEAGUES=['EPL','LaLiga','SerieA','Bundesliga','Ligue1','PrimeiraLiga','Eredivisie']   # CORE 7
SEASONS=['2122','2223','2324','2425','2526']     # κλειδωμενες (ιδιες με teamgame_inputs_5s.csv)
KF=4.0

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
            for is_home,tid,opp,gf,dis_self,dis_opp in [
                (1,hid,aid,m['hs'],dis_home,dis_away),
                (0,aid,hid,m['as'],dis_away,dis_home)]:
                a=agg[tid]
                red_xg=0.0083*dis_opp - 0.5*0.0083*dis_self
                rows.append(dict(league=lg,season=sea,mid=mid,date=isodate(m['date']),
                    team=tid,opp=opp,is_home=is_home,gf=gf,
                    np_raw=a['np_raw'],np_comp=a['np_comp'],pen=a['pen'],ns=a['ns'],red_xg=red_xg))

df=pd.DataFrame(rows)
df=df.sort_values(['league','season','date','mid','is_home']).reset_index(drop=True)

# ---- full-season sf (οπως το παλιο· κρατιεται στη στηλη sf ΜΟΝΟ για ελεγχο) ----
SF_FULL={}
for (lg,sea),g in df.groupby(['league','season']):
    SF_FULL[(lg,sea)]=g.np_raw.sum()/g.np_comp.sum()
df['sf']=[SF_FULL[(lg,sea)] for lg,sea in zip(df.league,df.season)]

# ---- WALK-FORWARD sf ανα ματς ----
df['sf_wf']=np.nan; df['md_wf']=np.nan
note_2122=0
for (lg,sea),g in df.groupby(['league','season']):
    i=SEASONS.index(sea)
    prior=SF_FULL.get((lg,SEASONS[i-1])) if i>0 else None
    nteams=g.team.nunique()
    # αθροισματα ανα ημερομηνια (ματς = 2 γραμμες-ομαδα· μετραμε ματς = γραμμες/2)
    D=g.groupby('date').agg(raw=('np_raw','sum'),comp=('np_comp','sum'),n=('mid','nunique')).sort_index()
    craw=D.raw.cumsum().shift(1,fill_value=0.0)
    ccomp=D.comp.cumsum().shift(1,fill_value=0.0)
    cn=D.n.cumsum().shift(1,fill_value=0)
    sf_by_date={}; md_by_date={}
    for dt in D.index:
        n_before=int(cn[dt]); md=2.0*n_before/nteams     # live: len(γραμμες-ομαδα)/ομαδες = αγωνιστικες
        if n_before==0:
            live=None
        else:
            live=craw[dt]/ccomp[dt] if ccomp[dt]>0 else None
        if prior is None:                      # 2122: χωρις περσινη
            if live is None:
                sf=1.0; note_2122+=1
            else:
                sf=live
        else:
            if live is None or md==0:
                sf=prior
            else:
                sf=prior*(live/prior)**(md/(md+KF))
        sf_by_date[dt]=sf; md_by_date[dt]=md
    m=(df.league==lg)&(df.season==sea)
    df.loc[m,'sf_wf']=df.loc[m,'date'].map(sf_by_date).values
    df.loc[m,'md_wf']=df.loc[m,'date'].map(md_by_date).values

df['comp_np_scaled']=df['np_comp']*df['sf_wf']
df['xg_model']=df['comp_np_scaled']+0.25*df['pen']+df['red_xg']
df['ns_eff']=df['ns']+df['pen']+(df['red_xg'].abs()/0.10)
df['xgps']=df['xg_model']/df['ns_eff'].clip(lower=1)
COLS=['league','season','mid','date','team','opp','is_home','gf','np_raw','np_comp','pen','ns','red_xg',
      'comp_np_scaled','sf','xg_model','ns_eff','xgps','sf_wf','md_wf']
df=df[COLS].sort_values(['league','season','date','mid','is_home'])
OUT='teamgame_inputs_5s_wf.csv'
df.to_csv(OUT,index=False)
print(f"{OUT}: {len(df)} γραμμες-ομαδα ({len(df)//2} ματς)")
print(f"σεζον: {SEASONS}   KF={KF}")
print(f"ΣΗΜΕΙΩΣΗ 2122 (χωρις περσινη): sf_wf=live_d· ημερομηνιες με md_d=0 -> sf_wf=1.0: {note_2122} (1 ανα λιγκα = η 1η αγωνιστικη ημερα)")
print("\nΜατς ανα λιγκα-σεζον:")
print(df.groupby(['league','season']).size().div(2).astype(int).unstack())

# ---- ΕΛΕΓΧΟΣ / ΠΙΝΑΚΑΣ Δ ----
def zone(md):
    return 'md1-6' if md<6 else ('md7-14' if md<14 else 'md15+')
df['zone']=df.md_wf.apply(zone)
print("\nΠΙΝΑΚΑΣ Δ — sf ανα λιγκα-σεζον: full | sf_wf @md1 (1η ημερα) | @md5 (4<=md<5) | @md15 (14<=md<15) | @τελευταια ημερα | Δ%τελ")
print(f"{'λιγκα':>13s} {'σεζ':>5s} | {'full':>7s} | {'@md1':>7s} {'@md5':>7s} {'@md15':>7s} {'@τελ':>7s} | {'Δ%τελ':>7s} | μεση |sf_wf−sf_full|: {'md1-6':>7s} {'md7-14':>7s} {'md15+':>7s}")
bad=0
for (lg,sea),g in df.groupby(['league','season']):
    full=SF_FULL[(lg,sea)]
    first=g.sort_values('date').iloc[0].sf_wf
    last=g.sort_values('date').iloc[-1].sf_wf
    def at(lo,hi):
        s=g[(g.md_wf>=lo)&(g.md_wf<hi)]
        return s.sf_wf.mean() if len(s) else float('nan')
    dl=(last-full)/full
    if abs(dl)>=0.01: bad+=1
    ad=(g.sf_wf-g.sf).abs()
    z=ad.groupby(g.zone).mean()
    print(f"{lg:>13s} {sea:>5s} | {full:7.4f} | {first:7.4f} {at(4,5):7.4f} {at(14,15):7.4f} {last:7.4f} | {dl:>+7.2%} | "
          f"{'':>27s}{z.get('md1-6',float('nan')):7.4f} {z.get('md7-14',float('nan')):7.4f} {z.get('md15+',float('nan')):7.4f}")
print(f"\nΕΛΕΓΧΟΣ τελευταιας αγωνιστικης: |sf_wf−sf_full|/sf_full >= 1% σε {bad} απο {df.groupby(['league','season']).ngroups} λιγκες-σεζον")
ad=(df.sf_wf-df.sf).abs()
print("Μεση απολυτη διαφορα |sf_wf − sf_full| ανα ζωνη md (ολες οι λιγκες-σεζον, γραμμες-ομαδα):")
print(ad.groupby(df.zone).agg(['mean','max','count']).round(4).to_string())
print("  -- μονο σεζον με περσινη (2223-2526):")
m=df.season!='2122'
print(ad[m].groupby(df.zone[m]).agg(['mean','max','count']).round(4).to_string())
print("[τελος]")
