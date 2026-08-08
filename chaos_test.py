import json, numpy as np, pandas as pd

TOP5={'EPL':'EPL','LaLiga':'LaLiga','SerieA':'SerieA','Bundesliga':'Bundesliga','Ligue1':'Ligue1'}
NEW={'2.Bundesliga':'Bundesliga2','Eredivisie':'Eredivisie','MLS':'MLS','Πορτογαλια':'PrimeiraLiga','Ελλαδα':'GreeceSL'}

def league_rows(filekey, seasons):
    rows=[]
    for sea in seasons:
        try: d=json.load(open(f'data_{filekey}_{sea}.json'))
        except FileNotFoundError: continue
        for m in d.values():
            if m['hs'] is None: continue
            hid=int(m['home']['id']); aid=int(m['away']['id'])
            hx=ax=hs_=as_=0.0
            for s in m['shots']:
                xg=s.get('xg') or 0
                if s['tid']==hid: hx+=xg; hs_+=1
                elif s['tid']==aid: ax+=xg; as_+=1
            rows.append(dict(hx=hx,ax=ax,hg=m['hs'],ag=m['as'],hsh=hs_,ash=as_))
    return pd.DataFrame(rows)

def metrics(df):
    if len(df)==0: return None
    gpg=(df.hg+df.ag).mean()
    shpg=(df.hsh+df.ash).mean()
    xgd=df.hx-df.ax; gd=df.hg-df.ag
    corr=np.corrcoef(xgd,gd)[0,1]                       # single-match xG->goals
    # upset: ομαδα με xG edge >=0.75 που ΔΕΝ κερδισε
    dom=df[abs(xgd)>=0.75]
    if len(dom):
        won=((dom.hx-dom.ax>0)&(dom.hg-dom.ag>0))|((dom.ax-dom.hx>0)&(dom.ag-dom.hg>0))
        upset=1-won.mean()
    else: upset=np.nan
    # conversion noise: std(goals - xG) ανα ομαδα-ματς
    conv=np.concatenate([(df.hg-df.hx).values,(df.ag-df.ax).values]).std()
    return dict(n=len(df),gpg=gpg,shpg=shpg,corr=corr,upset=upset,conv=conv)

print(f"{'ΛΙΓΚΑ':16s} {'ματς':>5s} {'γκολ/μ':>7s} {'σουτ/μ':>7s} | {'xG→GD corr':>11s} {'upset%':>7s} {'conv.θορ':>8s}")
print("─"*72)
print("TOP-5 (2024/25 + 2025/26):")
top_corr=[]; top_conv=[]; top_ups=[]
for name,fk in TOP5.items():
    m=metrics(league_rows(fk,['2425','2526']))
    top_corr.append(m['corr']); top_conv.append(m['conv']); top_ups.append(m['upset'])
    print(f"  {name:14s} {m['n']:>5d} {m['gpg']:>7.2f} {m['shpg']:>7.1f} | {m['corr']:>11.3f} {m['upset']:>6.1%} {m['conv']:>8.3f}")
print(f"  {'-- ΜΕΣΟΣ ΟΡΟΣ':14s} {'':>5s} {'':>7s} {'':>7s} | {np.mean(top_corr):>11.3f} {np.mean(top_ups):>6.1%} {np.mean(top_conv):>8.3f}")
print("\nΝΕΑ ΠΡΩΤΑΘΛΗΜΑΤΑ (2025/26):")
for name,fk in NEW.items():
    m=metrics(league_rows(fk,['2526']))
    if m is None: print(f"  {name}: no data"); continue
    flag=''
    if m['corr']<np.mean(top_corr)-0.05: flag+=' ⚠χαμηλο corr'
    if m['conv']>np.mean(top_conv)+0.05: flag+=' ⚠υψηλος θορυβος'
    print(f"  {name:14s} {m['n']:>5d} {m['gpg']:>7.2f} {m['shpg']:>7.1f} | {m['corr']:>11.3f} {m['upset']:>6.1%} {m['conv']:>8.3f}{flag}")
print("\n(corr = ποσο τα xG ενος ματς προβλεπουν το σκορ του | upset% = ομαδα με xG edge ≥0.75 που δεν κερδισε")
print(" conv.θορ = τυπικη αποκλιση (γκολ − xG) ανα ομαδα-ματς, δηλ. ποσο 'ξεφευγει' το σκορ απο τα xG)")
