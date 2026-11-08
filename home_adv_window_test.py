"""
home_adv_window_test.py — 9/10/2026: ΕΠΑΝΑΛΗΨΗ σε ΑΝΕΞΑΡΤΗΤΑ δεδομενα του ευρηματος core7_early_weakness:
«στις αγωνιστικες 7-14 η εδρα ειναι μεγαλυτερη (+0.38 vs +0.26/+0.29) και ΚΑΙ το μοντελο ΚΑΙ η αγορα την υποτιμουν».
Δεδομενα: (1) CORE7 λιγκες 2010-11…2020-21 (football-data, μονο γκολ + γραμμη χαντικαπ οπου υπαρχει) — ΠΡΙΝ απο το δειγμα μας,
(2) Αγγλια/Σκωτια κατω κατηγοριες 2019-20…2025-26 (raw_fd_uk). Χωρις κοσμο (15/3/2020-31/5/2021) εξω.
Αγωνιστικη = min(ματς που εχουν παιξει οι 2 ομαδες) + 1 (οπως το md μας).
Μετρο: διαφορα γκολ γηπεδουχου ανα παραθυρο, και (οπου υπαρχει γραμμη) πραγματικο − γραμμη (αγορα).
ΠΡΟ-ΔΗΛΩΣΗ: επαναληψη αν 7-14 > (1-5 και 15+) σε ≥2/3 των σεζον ΚΑΙ η διαφορα 7-14 − υπολοιπα ≥2 SE στο συνολο.
"""
import sys, glob, os
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
def load(files, tag):
    out = []
    for f in sorted(files):
        try: d = pd.read_csv(f, encoding='latin-1')
        except Exception: continue
        if not {'Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG'} <= set(d.columns): continue
        d = d.dropna(subset=['HomeTeam', 'FTHG']).copy()
        d['dt'] = pd.to_datetime(d.Date, dayfirst=True, errors='coerce'); d = d.dropna(subset=['dt']).sort_values('dt')
        lg, sea = os.path.basename(f)[:-4].split('_')
        line = None
        for c in ('AHCh', 'AHh', 'BbAHh'):
            if c in d.columns and d[c].notna().mean() > 0.8: line = c; break
        n = {}
        for r in d.itertuples(index=False):
            h, a = r.HomeTeam, r.AwayTeam; md = min(n.get(h, 0), n.get(a, 0))
            L = getattr(r, line) if line else np.nan
            out.append(dict(src=tag, lg=lg, sea=sea, dt=r.dt, md=md, gd=r.FTHG - r.FTAG, L=L))
            n[h] = n.get(h, 0) + 1; n[a] = n.get(a, 0) + 1
    X = pd.DataFrame(out)
    X = X[~((X.dt >= '2020-03-15') & (X.dt < '2021-06-01'))]
    X['w'] = pd.cut(X.md, [-1, 4, 5, 13, 99], labels=['1-5', '6', '7-14', '15+'])
    X['res'] = X.gd + X.L          # πραγματικο − γραμμη (γραμμη γηπεδουχου: αρνητικη οταν φαβορι)
    return X
def report(X, title):
    print(f'\n=== {title}: {len(X)} ματς, {X.groupby(["lg", "sea"]).ngroups} λιγκες-σεζον ===')
    for w, x in X.groupby('w', observed=True):
        r = x.res.dropna()
        print(f'   αγων {w:5s} n{len(x):6d} · εδρα (διαφορα γκολ) {x.gd.mean():+.3f} ±{x.gd.std() / np.sqrt(len(x)):.3f}'
              + (f' · πραγματικο − γραμμη {r.mean():+.3f} ±{r.std() / np.sqrt(len(r)):.3f} (n{len(r)})' if len(r) > 100 else ''))
    # ανα σεζον: 7-14 − υπολοιπα (1-5 & 15+)
    rows = []
    for (lg, sea), x in X.groupby(['lg', 'sea']):
        a = x[x.w == '7-14'].gd; b = x[x.w.isin(['1-5', '15+'])].gd
        if len(a) > 20 and len(b) > 50: rows.append(dict(sea=sea, d=a.mean() - b.mean(), na=len(a)))
    R = pd.DataFrame(rows)
    by = R.groupby('sea').apply(lambda v: np.average(v.d, weights=v.na))
    m7 = X[X.w == '7-14'].gd; mo = X[X.w.isin(['1-5', '15+'])].gd
    diff = m7.mean() - mo.mean(); se = np.sqrt(m7.var() / len(m7) + mo.var() / len(mo))
    print(f'   7-14 − (1-5 & 15+): {diff:+.3f} ±{se:.3f} (t {diff / se:+.1f}) · σεζον θετικες {int((by > 0).sum())}/{len(by)} · λιγκες-σεζον θετικες {int((R.d > 0).sum())}/{len(R)}')
    print('   ανα σεζον: ' + ' '.join(f'{k}:{v:+.2f}' for k, v in by.items()))
    pas = (by > 0).mean() >= 2 / 3 and diff / se >= 2
    print(f'   ΚΡΙΣΗ: {"ΕΠΑΝΑΛΑΜΒΑΝΕΤΑΙ" if pas else "ΔΕΝ επαναλαμβανεται"}')
    # λεπτομερεια ανα αγωνιστικη
    g = X.groupby(X.md.clip(upper=25)).gd.mean()
    print('   ανα αγωνιστικη: ' + ' '.join(f'{int(k) + 1}:{v:+.2f}' for k, v in g.items()))
report(load(glob.glob('raw_fd_old/*.csv'), 'old'), 'CORE7 λιγκες 2010-2021 (πριν απο το δειγμα μας)')
report(load(glob.glob('raw_fd_uk/*.csv'), 'uk'), 'Αγγλια/Σκωτια κατω κατηγοριες 2019-2026')
report(load(glob.glob('raw_fd/*.csv'), 'core'), 'CORE7+ (raw_fd 2122-2526, ελεγχος ιδιου δειγματος)')
