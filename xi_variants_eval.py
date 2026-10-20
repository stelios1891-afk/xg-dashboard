# -*- coding: utf-8 -*-
"""xi_variants_eval.py — 21/10/2026: αξιολογηση παραλλαγων (xi_variants_build → xi_variants_rows.csv) με LOSO 4 σεζον (2223-2526).
Στοχοι: λαθος live μοντελου σε διαφορα xG (κυριο) και διαφορα γκολ (απο xi_measure_eval_rows.csv).
ΑΝΑΦΟΡΑ = «αξια (μεσος ln) + εμπιστοσυνη 10 ματς λεπτα» (ο νικητης του 1ου γυρου).
ΚΑΝΟΝΑΣ (γραφτηκε ΠΡΙΝ): μια παραλλαγη αντικαθιστα την αναφορα ΜΟΝΟ αν η ΕΠΙΛΟΓΗ της μεσα στο LOSO (διαλεγεται στις 3 σεζον, κρινεται στην 4η)
δινει περισσοτερη βελτιωση απο την αναφορα σε ≥3/4 σεζον ΚΑΙ στο xG ΚΑΙ στα γκολ· αλλιως μενει η αναφορα (απλη)."""
import sys, itertools
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
NL = chr(10)
V = pd.read_csv('xi_variants_rows.csv', dtype={'mid': str, 'sea': str})
E = pd.read_csv('xi_measure_eval_rows.csv', dtype={'mid': str, 'season': str}, usecols=['mid', 'season', 'league', 'r_xgd', 'r_gd'])
D = E.merge(V, on='mid', how='inner')
SE = sorted(D.season.unique()); LGS = sorted(D.league.unique())
TR = [f'T{a}{n}' for a in ('m', 's') for n in (5, 10, 20)]; VA = ['Vlog', 'Vrel', 'Vsum']
NAMES = {'Tm5': 'εμπιστ. 5 ματς λεπτα', 'Tm10': 'εμπιστ. 10 ματς λεπτα', 'Tm20': 'εμπιστ. 20 ματς λεπτα', 'Ts5': 'εμπιστ. 5 ματς εκκινησεις',
         'Ts10': 'εμπιστ. 10 ματς εκκινησεις', 'Ts20': 'εμπιστ. 20 ματς εκκινησεις', 'Vlog': 'αξια (μεσος ln)', 'Vrel': 'αξια σχετικα με ομαδα', 'Vsum': 'αξια (ln αθροισματος)'}
for c in TR + VA:
    D[f'x_{c}'] = D[f'{c}_h'] - D[f'{c}_a']
    if c != 'Vsum':
        for g in ('gk', 'df', 'md', 'at'): D[f'x_{c}{g}'] = D[f'{c}{g}_h'] - D[f'{c}{g}_a']
def fitpred(tr, te, cols, ycol, by=None):
    if by is None:
        X = np.column_stack([np.ones(len(tr))] + [tr[c].fillna(0).values for c in cols]); b = np.linalg.lstsq(X, tr[ycol].values, rcond=None)[0]
        return np.column_stack([np.ones(len(te))] + [te[c].fillna(0).values for c in cols]) @ b
    out = np.zeros(len(te))
    for g in te[by].unique():
        t1, t2 = tr[tr[by] == g], te[by] == g
        X = np.column_stack([np.ones(len(t1))] + [t1[c].fillna(0).values for c in cols]); b = np.linalg.lstsq(X, t1[ycol].values, rcond=None)[0]
        out[t2.values] = np.column_stack([np.ones(t2.sum())] + [te[t2][c].fillna(0).values for c in cols]) @ b
    return out
def loso_gain(cols, ycol, by=None, data=None):
    data = D if data is None else data
    ok = data[ycol].notna() & data[cols].notna().any(axis=1); d = data[ok]; per = {}; tot = []
    for s in SE:
        tr, te = d[d.season != s], d[d.season == s]
        p = fitpred(tr, te, cols, ycol, by); base = tr[ycol].mean(); y = te[ycol].values
        g = (y - base) ** 2 - (y - p) ** 2; per[s] = 1000 * g.mean(); tot.append(g)
    return 1000 * np.concatenate(tot).mean(), per
def line(nm, cols, by=None):
    gx, px = loso_gain(cols, 'r_xgd', by); gg, pg = loso_gain(cols, 'r_gd', by)
    print(f'   {nm:44s} │ xG {gx:+6.2f} (' + ' '.join(f'{v:+.1f}' for v in px.values()) + f') {sum(v > 0 for v in px.values())}/4'
          f' │ γκολ {gg:+6.2f} (' + ' '.join(f'{v:+.1f}' for v in pg.values()) + f') {sum(v > 0 for v in pg.values())}/4')
    return gx, gg, px, pg
print(f'ματς {len(D)}')
print(f'{NL}{"=" * 130}{NL}1. ΕΜΠΙΣΤΟΣΥΝΗ ΠΡΟΠΟΝΗΤΗ — μονη της (βελτιωση ×1000, LOSO, ανα σεζον)')
for c in TR: line(NAMES[c], [f'x_{c}'])
print(f'{NL}2. ΑΞΙΑ — μονη της')
for c in VA: line(NAMES[c], [f'x_{c}'])
print(f'{NL}3. ΖΕΥΓΗ αξια + εμπιστοσυνη (9 × 2 = 18 συνδυασμοι)')
PAIRS = {}
for t in TR:
    for v in VA:
        PAIRS[(t, v)] = line(f'{NAMES[v]} + {NAMES[t]}', [f'x_{v}', f'x_{t}'])
REF = ('Tm10', 'Vlog')
print(f'{NL}4. ΤΙΜΙΑ ΕΠΙΛΟΓΗ μεσα στο LOSO (το ζευγος διαλεγεται στις 3 σεζον — με LOSO μεσα τους — και κρινεται στην 4η) vs ΑΝΑΦΟΡΑ {NAMES[REF[1]]} + {NAMES[REF[0]]}')
for ycol, lab in (('r_xgd', 'xG'), ('r_gd', 'γκολ')):
    win = 0; rows = []
    for s in SE:
        inner = [x for x in SE if x != s]; dtr = D[D.season != s]
        def inner_score(pair):
            sc = 0
            for s2 in inner:
                tr, te = dtr[dtr.season != s2], dtr[dtr.season == s2]; cols = [f'x_{pair[1]}', f'x_{pair[0]}']
                ok_tr = tr[ycol].notna(); ok_te = te[ycol].notna()
                p = fitpred(tr[ok_tr], te[ok_te], cols, ycol); y = te[ok_te][ycol].values
                sc += ((y - tr[ok_tr][ycol].mean()) ** 2 - (y - p) ** 2).mean()
            return sc
        best = max(PAIRS, key=inner_score)
        te = D[(D.season == s) & D[ycol].notna()]; tr = D[(D.season != s) & D[ycol].notna()]
        def g(pair):
            p = fitpred(tr, te, [f'x_{pair[1]}', f'x_{pair[0]}'], ycol); y = te[ycol].values
            return 1000 * ((y - tr[ycol].mean()) ** 2 - (y - p) ** 2).mean()
        gb, gr = g(best), g(REF); win += gb > gr
        rows.append(f'{s}: διαλεξε {best[1]}+{best[0]} {gb:+.2f} vs αναφορα {gr:+.2f}')
    print(f'   {lab}: ' + ' · '.join(rows) + f' → καλυτερη επιλογη σε {win}/4')
print(f'{NL}5. ΒΑΡΗ ΑΝΑ ΘΕΣΗ (τερμ./αμυνα/μεσοι/επιθεση χωριστα για αξια ΚΑΙ εμπιστοσυνη — 8 συντελεστες) vs αναφορα (2)')
line('αναφορα: αξια + εμπιστοσυνη (2)', [f'x_{REF[1]}', f'x_{REF[0]}'])
pos_cols = [f'x_{REF[1]}{g}' for g in ('gk', 'df', 'md', 'at')] + [f'x_{REF[0]}{g}' for g in ('gk', 'df', 'md', 'at')]
line('ανα θεση (8)', pos_cols)
ok = D[pos_cols + ['r_xgd']].notna().all(axis=1)
X = np.column_stack([np.ones(ok.sum())] + [D.loc[ok, c].values for c in pos_cols]); b = np.linalg.lstsq(X, D.loc[ok, 'r_xgd'].values, rcond=None)[0]
print('   βαρη (ολα τα δεδομενα, xG): ' + ' · '.join(f'{c.replace("x_", "")} {v:+.2f}' for c, v in zip(pos_cols, b[1:])))
print(f'{NL}6. ΣΥΝΤΕΛΕΣΤΕΣ ΑΝΑ ΛΙΓΚΑ vs ενας για ολες (αναφορα)')
line('ενας για ολες', [f'x_{REF[1]}', f'x_{REF[0]}'])
line('ανα λιγκα', [f'x_{REF[1]}', f'x_{REF[0]}'], by='league')
print(f'{NL}7. ΑΝΑ ΛΙΓΚΑ — βελτιωση αναφορας (LOSO, xG / γκολ)')
for lg in LGS:
    q = D[D.league == lg]
    gx, _ = loso_gain([f'x_{REF[1]}', f'x_{REF[0]}'], 'r_xgd', data=q); gg, _ = loso_gain([f'x_{REF[1]}', f'x_{REF[0]}'], 'r_gd', data=q)
    print(f'   {lg:13s} n {len(q):5d} │ xG {gx:+6.2f} │ γκολ {gg:+6.2f}')
