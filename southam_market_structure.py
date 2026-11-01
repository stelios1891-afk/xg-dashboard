"""
southam_market_structure.py — 5/10/2026 (Στελιος: Βραζιλια & MLS, «ολοι οι μηχανισμοι»). ΦΑΣΗ 0: ΔΟΜΗ ΤΗΣ ΑΓΟΡΑΣ (μονο τιμες+σκορ).
Πηγη: football-data.co.uk new/BRA.csv & USA.csv (Pinnacle closing 1Χ2 2012-2025, Avg/Max closing) vs CORE7 (raw_fd, 2122-2526).
Μετρα ανα λιγκα:
  vig Pinnacle · ΚΛΙΣΗ βαθμονομησης (logit αποτελεσματος ~ a + b·logit(p_αγορας), b=1 τελεια, b>1 = η αγορα ΣΥΜΠΙΕΖΕΙ τα φαβορι)
  · μεροληψια ανα ζωνη πιθανοτητας (πραγματικο − αναμενομενο) · τυφλο ROI Pinnacle closing: γηπεδουχος/ισοπαλια/φιλοξενουμενος
  & φαβορι/αουτσαιντερ ανα ζωνη τιμης · ΙΔΙΑ στο Max (ψαξιμο τιμης) · ανα σεζον x/N · πορεια εδρας (αναμενομενη vs πραγματικη).
Τιποτα live.
"""
import sys, glob, os
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
def load_sa(f, lab):
    d = pd.read_csv(f, encoding='utf-8-sig')
    d = d.rename(columns={'HG': 'FTHG', 'AG': 'FTAG'}); d['lg'] = lab; d['sea'] = d.Season.astype(str)
    return d[d.Season <= 2025]
def load_core():
    out = []
    for f in glob.glob('raw_fd/*_*.csv'):
        lg, sea = os.path.basename(f)[:-4].split('_')
        if lg in ('Belgium', 'ScottishPrem'): continue
        d = pd.read_csv(f, encoding='latin-1'); d['lg'] = 'CORE7'; d['sea'] = sea; out.append(d)
    return pd.concat(out)
D = pd.concat([load_sa('southam/fd_BRA.csv', 'Βραζιλια'), load_sa('southam/fd_USA.csv', 'MLS'), load_core()], ignore_index=True)
D = D.dropna(subset=['PSCH', 'PSCD', 'PSCA', 'FTHG', 'FTAG'])
D['res'] = np.sign(D.FTHG - D.FTAG)
inv = 1 / D[['PSCH', 'PSCD', 'PSCA']].values; D['vig'] = inv.sum(1) - 1
P = inv / inv.sum(1, keepdims=True)          # αφαιρεση γκανιοτας αναλογικα
D['pH'], D['pD'], D['pA'] = P[:, 0], P[:, 1], P[:, 2]
def logit(p): p = np.clip(p, 1e-4, 1 - 1e-4); return np.log(p / (1 - p))
def slope(p, y):
    # λογιστικη παλινδρομηση y ~ a + b·logit(p) (Newton)
    X = np.c_[np.ones(len(p)), logit(p)]; w = np.array([0., 1.])
    for _ in range(30):
        mu = 1 / (1 + np.exp(-X @ w)); W = mu * (1 - mu); H = X.T @ (X * W[:, None]); g = X.T @ (y - mu)
        w += np.linalg.solve(H, g)
    se = np.sqrt(np.diag(np.linalg.inv(H)))
    return w[1], se[1], w[0]
def roi(d, col_o, cond):
    x = d[cond]; 
    if not len(x): return np.nan, 0, ''
    pnl = np.where(x['_win'], x[col_o] - 1, -1.0)
    ps = pd.Series(pnl, index=x.index).groupby(x.sea).mean()
    return pnl.mean(), len(x), f'{int((ps > 0).sum())}/{len(ps)}'
for lg in ('Βραζιλια', 'MLS', 'CORE7'):
    d = D[D.lg == lg].copy()
    print(f'\n================ {lg} — n {len(d)} · σεζον {d.sea.min()}-{d.sea.max()} · vig Pinnacle {100*d.vig.median():.2f}% ================')
    print(f'  γηπεδουχος: αναμενομενη {100*d.pH.mean():.1f}% πραγματικη {100*(d.res == 1).mean():.1f}% · ισοπαλια {100*d.pD.mean():.1f}%/{100*(d.res == 0).mean():.1f}% · φιλοξ {100*d.pA.mean():.1f}%/{100*(d.res == -1).mean():.1f}%')
    # κλιση: στοιβαζουμε τα 3 αποτελεσματα
    p = np.r_[d.pH, d.pD, d.pA]; y = np.r_[(d.res == 1), (d.res == 0), (d.res == -1)].astype(float)
    b, se, a = slope(p, y); print(f'  ΚΛΙΣΗ ολα (1/Χ/2): b={b:.3f} ±{se:.3f} (1 = τελεια· >1 = η αγορα συμπιεζει)')
    for nm, pp, yy in (('νικη γηπεδ.', d.pH, d.res == 1), ('ισοπαλια', d.pD, d.res == 0), ('νικη φιλοξ.', d.pA, d.res == -1)):
        b, se, a = slope(pp.values, yy.values.astype(float)); print(f'     {nm:12s} b={b:.3f} ±{se:.3f} a={a:+.3f}')
    # μεροληψια ανα ζωνη (ολα τα αποτελεσματα στοιβαγμενα)
    bins = [0, .15, .25, .35, .45, .55, .65, .75, 1]
    z = pd.DataFrame(dict(p=p, y=y)); z['b'] = pd.cut(z.p, bins)
    g = z.groupby('b', observed=True).agg(n=('y', 'size'), exp=('p', 'mean'), act=('y', 'mean'))
    print('  ζωνη πιθανοτητας → αναμενομενο/πραγματικο (pp):  ' + ' · '.join(f'{iv.left:.2f}-{iv.right:.2f}: {100*(r.act-r.exp):+.1f} (n{r.n})' for iv, r in g.iterrows()))
    # τυφλα ROI
    rows = []
    for side, oc, mc, cond_w in (('Γηπεδουχος', 'PSCH', 'MaxCH', d.res == 1), ('Ισοπαλια', 'PSCD', 'MaxCD', d.res == 0), ('Φιλοξενουμενος', 'PSCA', 'MaxCA', d.res == -1)):
        e = d.copy(); e['_win'] = cond_w.values
        for lo, hi in ((1, 1.5), (1.5, 2), (2, 2.6), (2.6, 3.5), (3.5, 6), (6, 99), (1, 99)):
            r1, n1, s1 = roi(e, oc, (e[oc] >= lo) & (e[oc] < hi))
            r2, n2, s2 = roi(e, mc, (e[oc] >= lo) & (e[oc] < hi)) if mc in e and e[mc].notna().any() else (np.nan, 0, '')
            rows.append((side, f'{lo}-{hi if hi < 99 else "∞"}', n1, r1, s1, r2))
    print('  ΤΥΦΛΟ ROI closing:  πλευρα / ζωνη τιμης Pinnacle → n · ROI Pinnacle · σεζον θετικες · ROI στο Max αγορας')
    for side, zb, n1, r1, s1, r2 in rows:
        if n1 >= 30: print(f'     {side:15s} @{zb:9s} n{n1:5d}  {100*r1:+6.1f}%  {s1:6s}  Max {100*r2:+6.1f}%')
    # εδρα ανα σεζον
    s = d.groupby('sea').apply(lambda x: pd.Series(dict(exp=x.pH.mean() - x.pA.mean(), act=(x.res == 1).mean() - (x.res == -1).mean())), include_groups=False)
    print('  ΕΔΡΑ ανα σεζον (P(1)−P(2)): ' + ' · '.join(f'{k}: αγορα {100*r.exp:+.0f} / πραγμ {100*r.act:+.0f}' for k, r in s.iterrows()))
