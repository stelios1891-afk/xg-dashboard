import json, numpy as np, pandas as pd
LEAGUES=['Bundesliga2','Eredivisie','PrimeiraLiga','GreeceSL']
def rows(lg,sea):
    try: d=json.load(open(f'data_{lg}_{sea}.json'))
    except FileNotFoundError: return None
    r=[]
    for m in d.values():
        if m['hs'] is None: continue
        hid=int(m['home']['id']); aid=int(m['away']['id']); hx=ax=hs=as_=0.
        for s in m['shots']:
            xg=s.get('xg') or 0
            if s['tid']==hid: hx+=xg; hs+=1
            elif s['tid']==aid: ax+=xg; as_+=1
        r.append(dict(hx=hx,ax=ax,hg=m['hs'],ag=m['as'],hsh=hs,ash=as_))
    return pd.DataFrame(r)
def met(df):
    if df is None or len(df)==0: return None
    xgd=df.hx-df.ax; gd=df.hg-df.ag
    dom=df[abs(xgd)>=0.75]
    won=((dom.hx-dom.ax>0)&(dom.hg-dom.ag>0))|((dom.ax-dom.hx>0)&(dom.ag-dom.hg>0)) if len(dom) else None
    conv=np.concatenate([(df.hg-df.hx).values,(df.ag-df.ax).values]).std()
    return dict(gpg=(df.hg+df.ag).mean(),corr=np.corrcoef(xgd,gd)[0,1],
                upset=(1-won.mean()) if won is not None else np.nan,conv=conv)
print(f"{'πρωταθλημα':14s} | {'γκολ/μ':>13s} | {'xG→GD corr':>15s} | {'χαος(conv)':>15s} | {'upset%':>13s}")
print(f"{'':14s} | {'24/25':>6s} {'25/26':>6s} | {'24/25':>7s} {'25/26':>7s} | {'24/25':>7s} {'25/26':>7s} | {'24/25':>6s} {'25/26':>6s}")
print("─"*82)
for lg in LEAGUES:
    m1=met(rows(lg,'2425')); m2=met(rows(lg,'2526'))
    def c(m,k,f): return (f%m[k]) if m else '  —'
    print(f"{lg:14s} | {c(m1,'gpg','%5.2f')} {c(m2,'gpg','%5.2f')} | {c(m1,'corr','%6.3f')} {c(m2,'corr','%6.3f')} | {c(m1,'conv','%6.3f')} {c(m2,'conv','%6.3f')} | {c(m1,'upset','%5.1f%%') if m1 else '  —':>6s} {c(m2,'upset','%.1f%%')}")
