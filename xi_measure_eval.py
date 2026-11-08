# -*- coding: utf-8 -*-
"""xi_measure_eval.py — 21/10/2026: αξιολογηση του αγωνα μετρων (xi_measure_race.py → xi_measure_rows.csv).
Στοχοι: λαθος του live μοντελου (core7_mech_preds_bl_0.6, 2223-2526) σε ΔΙΑΦΟΡΑ xG και ΔΙΑΦΟΡΑ ΓΚΟΛ, και ανα πλευρα (xG που βαζει ο γηπεδουχος
↔ επιθεση γηπ. + αμυνα φιλοξ.). Χαρακτηριστικο = Δ γηπ − Δ φιλ (Δ = ενδεκαδα σημερα − συνηθισμενη).
LOSO: συντελεστης απο 3 σεζον → 4η· βελτιωση = MSE(μονο σταθερα) − MSE(σταθερα + b·x), εκτος δειγματος.
ΚΡΙΤΗΡΙΟ (γραφτηκε ΠΡΙΝ): καλυτερο μετρο = μεγαλυτερη βελτιωση στη ΔΙΑΦΟΡΑ xG, θετικη σε ≥3/4 σεζον και ≥5/7 λιγκες· επιβεβαιωση στα γκολ."""
import sys, json, glob, re
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
NL = chr(10)
R = pd.read_csv('xi_measure_rows.csv', dtype={'mid': str, 'sea': str})
P = pd.read_csv('core7_mech_preds_bl_0.6.csv', dtype={'mid': str, 'season': str})
X = {}
for f in glob.glob('data_*_*.json'):
    if not re.search(r'data_(EPL|LaLiga|SerieA|Bundesliga|Ligue1|Eredivisie|PrimeiraLiga)_\d{4}\.json$', f): continue
    for k, v in json.load(open(f, encoding='utf-8')).items():
        hid = v['home']['id']; xh = xa = 0.0; has = False
        for s in v.get('shots') or []:
            if s.get('xg') is None: continue
            has = True
            if s.get('tid') == hid: xh += s['xg']
            else: xa += s['xg']
        if has: X[str(k)] = (xh, xa)
D = P.merge(R, on='mid', how='inner')
D['axh'] = D.mid.map(lambda k: X.get(k, (np.nan, np.nan))[0]); D['axa'] = D.mid.map(lambda k: X.get(k, (np.nan, np.nan))[1])
D['r_xgd'] = (D.axh - D.axa) - (D.xg_h - D.xg_a); D['r_gd'] = D.gd - (D.xg_h - D.xg_a)
D['r_xh'] = D.axh - D.xg_h; D['r_xa'] = D.axa - D.xg_a
SE = sorted(D.season.unique()); LGS = sorted(D.league.unique())
MEAS = [('M1 βαθμολογια FotMob', 'M1'), ('M2 βαθμολογια ανα θεση', 'M2'), ('M3 αξια', 'M3'), ('M4 εμπιστοσυνη προπονητη', 'M4'),
        ('M5 επιδραση xG (λ30)', 'M5_30'), ('M5 επιδραση xG (λ100)', 'M5_100'), ('M5 επιδραση xG (λ300)', 'M5_300')]
for _, c in MEAS:
    D[f'x_{c}'] = D[f'{c}_h'] - D[f'{c}_a']
    for g in ('O', 'D'): D[f'x_{c}{g}'] = D[f'{c}{g}_h'] - D[f'{c}{g}_a']
def loso(cols, ycol, data):
    """επιστρεφει: βελτιωση ανα σεζον (×1000 MSE), προβλεψεις εκτος δειγματος, συντελεστες ανα fold."""
    pred = pd.Series(np.nan, index=data.index); base = pd.Series(np.nan, index=data.index); coefs = []
    ok = data[cols + [ycol]].notna().all(axis=1)
    for s in SE:
        tr = data[(data.season != s) & ok]; te = data[(data.season == s) & ok]
        Xtr = np.column_stack([np.ones(len(tr))] + [tr[c].values for c in cols]); b = np.linalg.lstsq(Xtr, tr[ycol].values, rcond=None)[0]
        Xte = np.column_stack([np.ones(len(te))] + [te[c].values for c in cols])
        pred[te.index] = Xte @ b; base[te.index] = tr[ycol].mean(); coefs.append(b[1:])
    y = data[ycol]; gain = (y - base) ** 2 - (y - pred) ** 2
    return gain, ok, coefs
def report(title, ycol):
    print(f'{NL}{"=" * 126}{NL}{title}')
    print(f'   {"μετρο":28s} │ {"συσχ.":>6s} │ {"LOSO βελτ. ×1000":>16s} │ ' + ' '.join(f'{s:>6s}' for s in SE) + ' │ λιγκες θετικες │ κλιση (σταθερη;)')
    res = {}
    for nm, c in MEAS:
        col = f'x_{c}'; g, ok, cf = loso([col], ycol, D)
        r = D.loc[ok, [col, ycol]].corr().iloc[0, 1]
        per = [1000 * g[ok & (D.season == s)].mean() for s in SE]; lg = [g[ok & (D.league == l)].mean() for l in LGS]
        res[c] = 1000 * g[ok].mean()
        print(f'   {nm:28s} │ {r:+6.3f} │ {1000 * g[ok].mean():+16.2f} │ ' + ' '.join(f'{v:+6.2f}' for v in per)
              + f' ({sum(v > 0 for v in per)}/4) │ {sum(v > 0 for v in lg)}/7 │ ' + ' '.join(f'{x[0]:+.2f}' for x in cf))
    return res
print(f'ματς: {len(D)} (2223-2526) · με xG: {D.r_xgd.notna().sum()}')
r1 = report('Α. ΛΑΘΟΣ ΜΟΝΤΕΛΟΥ ΣΤΗ ΔΙΑΦΟΡΑ xG (κυριο κριτηριο)', 'r_xgd')
r2 = report('Β. ΛΑΘΟΣ ΜΟΝΤΕΛΟΥ ΣΤΗ ΔΙΑΦΟΡΑ ΓΚΟΛ (επιβεβαιωση)', 'r_gd')
# ---------- συνδυασμοι ----------
print(f'{NL}{"=" * 126}{NL}Γ. ΣΥΝΔΥΑΣΜΟΙ (πολλαπλη, LOSO) — διαφορα xG / διαφορα γκολ')
best5 = max(['M5_30', 'M5_100', 'M5_300'], key=lambda c: r1[c])
COMBOS = [('M1+M3', ['M1', 'M3']), ('M1+M4', ['M1', 'M4']), ('M3+M4', ['M3', 'M4']), (f'M1+M3+M4', ['M1', 'M3', 'M4']),
          (f'M1+M3+{best5}', ['M1', 'M3', best5]), (f'ΟΛΑ (M1+M2+M3+M4+{best5})', ['M1', 'M2', 'M3', 'M4', best5])]
for nm, cs in COMBOS:
    cols = [f'x_{c}' for c in cs]; out = []
    for ycol in ('r_xgd', 'r_gd'):
        g, ok, cf = loso(cols, ycol, D)
        per = [1000 * g[ok & (D.season == s)].mean() for s in SE]
        out.append(f'{1000 * g[ok].mean():+6.2f} ({sum(v > 0 for v in per)}/4)')
    cfm = np.mean(cf, axis=0)
    print(f'   {nm:34s} │ xG {out[0]} │ γκολ {out[1]} │ βαρη ' + ' '.join(f'{c}:{v:+.2f}' for c, v in zip(cs, cfm)))
# ---------- ανα θεση: τα xG που βαζει ο γηπεδουχος = επιθεση γηπ. + αμυνα φιλοξ. ----------
print(f'{NL}{"=" * 126}{NL}Δ. ΑΝΑ ΘΕΣΗ — xG που ΒΑΖΕΙ ο γηπεδουχος (λαθος μοντελου) ~ επιθεση/μεσοι γηπ. (O_h) + αμυνα/τερμ. φιλοξ. (D_a)')
for nm, c in MEAS:
    D['tmp_o'] = D[f'{c}O_h']; D['tmp_d'] = D[f'{c}D_a']
    g, ok, cf = loso(['tmp_o', 'tmp_d'], 'r_xh', D)
    per = [1000 * g[ok & (D.season == s)].mean() for s in SE]; cfm = np.mean(cf, axis=0)
    print(f'   {nm:28s} │ βελτ. {1000 * g[ok].mean():+6.2f} ({sum(v > 0 for v in per)}/4) │ επιθεση γηπ. {cfm[0]:+.2f} · αμυνα φιλοξ. {cfm[1]:+.2f} (αναμενεται +, −)')
# ---------- μεγεθος: τι σημαινει στην πραξη ----------
print(f'{NL}{"=" * 126}{NL}Ε. ΜΕΓΕΘΟΣ — ακραια ματς (5% / 95% του χαρακτηριστικου): μεσο λαθος μοντελου στη διαφορα xG και γκολ')
for nm, c in MEAS:
    col = f'x_{c}'; q5, q95 = D[col].quantile(.05), D[col].quantile(.95)
    lo, hi = D[D[col] <= q5], D[D[col] >= q95]
    print(f'   {nm:28s} │ χαμηλο 5%: xG {lo.r_xgd.mean():+.2f} γκολ {lo.r_gd.mean():+.2f} │ ψηλο 5%: xG {hi.r_xgd.mean():+.2f} γκολ {hi.r_gd.mean():+.2f} │ διαφορα xG {hi.r_xgd.mean() - lo.r_xgd.mean():+.2f}')
D.to_csv('xi_measure_eval_rows.csv', index=False)
