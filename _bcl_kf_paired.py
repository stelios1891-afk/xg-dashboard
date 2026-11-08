import pickle, numpy as np, json
D = pickle.load(open('bcl_engine_preds2.pkl','rb')); ids, ys, act = D['id'], D['y'], D['act']
pos = {i:k for k,i in enumerate(ids)}
C = pickle.load(open('bcl_m2_cache2.pkl','rb'))
def arr(pr):
    v = np.full(len(ids), np.nan)
    for m,(p,y) in pr.items():
        if m in pos: v[pos[m]] = p
    return v
EV=[2021,2022,2023,2024,2025]
def rm(v,Y): m=(ys==Y)&np.isfinite(v); return np.sqrt(np.mean((act-v)[m]**2))
bases = sorted({c[:4] for c in C if len(c)==5})
for kf in (.25,.5,1.0):
    rows=[]
    for b in bases:
        if b+(0.0,) in C and b+(kf,) in C:
            v0, v1 = arr(C[b+(0.0,)]), arr(C[b+(kf,)])
            rows.append([rm(v1,Y)-rm(v0,Y) for Y in EV])
    R=np.array(rows)
    print(f'kf {kf}: {len(R)} βασικες ρυθμισεις · μεση διαφορα ανα σεζον ' + ' '.join(f'{x:+.3f}' for x in R.mean(0)) + f' · σεζον καλυτερες (μεσος) {(R.mean(0)<0).sum()}/5 · ρυθμισεις με ≥4/5: {((R<0).sum(1)>=4).sum()}/{len(R)}')
# αρχη σεζον
gno=np.zeros(len(ids),int); import collections; cnt=collections.Counter()
for i in np.argsort(D['t']): cnt[(ys[i],D['hid'][i])]+=1; gno[i]=cnt[(ys[i],D['hid'][i])]
b=(1.15,2.5,9999.0,25.0)
for kf in (0.0,.5):
    v=arr(C[b+(kf,)]); m=np.isfinite(v)
    print(f'{b} kf {kf}: 1-3 ματς {np.sqrt(np.mean((act-v)[m&(gno<=3)]**2)):.3f} · 4+ {np.sqrt(np.mean((act-v)[m&(gno>3)]**2)):.3f}')
