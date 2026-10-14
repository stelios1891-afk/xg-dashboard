"""uel_steam_rules.py — 15/10/2026. Συνεχεια uel_steam_patterns: ΚΑΝΟΝΕΣ που ξερεις ΣΤΟ ΑΝΟΙΓΜΑ (χωρις να ξερεις που θα παει η αγορα).
Europa 2223-2526, ενα βιβλιο ανα ματς (Crown αλλιως SBOBET), τιμη ΑΝΟΙΓΜΑΤΟΣ και, για συγκριση, ΚΛΕΙΣΙΜΑΤΟΣ. Περιγραφικο — εκ των υστερων μοτιβα.
"""
import sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
import os
X = pd.read_pickle(os.environ.get('STEAM_FILE', 'uel_steam_rows.pkl'))
print('ΑΡΧΕΙΟ:', os.environ.get('STEAM_FILE', 'uel_steam_rows.pkl (Europa)'))
TOP5 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}
def run(lab, m_, side):
    y = X[m_].copy()
    if len(y) < 10: print(f'   {lab:60s} n{len(y)} (λιγα)'); return
    s = side(y) if callable(side) else np.full(len(y), side)
    po = [picks.settle(r.gd, sd, r.L0 if sd == 1 else -r.L0, r.oh0 if sd == 1 else r.oa0) for r, sd in zip(y.itertuples(), s)]
    pc = [picks.settle(r.gd, sd, r.L1 if sd == 1 else -r.L1, r.oh1 if sd == 1 else r.oa1) for r, sd in zip(y.itertuples(), s)]
    mv = (s * y.mv.values).mean()
    y['po'] = po; ps = y.groupby('sea').po.mean()
    print(f'   {lab:60s} n{len(y):4d} · ROI ανοιγμα {100 * np.mean(po):+6.1f}% · κλεισιμο {100 * np.mean(pc):+6.1f}% · κινηση προς εμας {mv:+.2f} · ('
          + ' '.join(f'{q[2:]} {100 * v:+.0f}' for q, v in ps.items()) + ')')
domA = ~X.lga.isin(TOP5) & (X.ta >= .9); domH = ~X.lgh.isin(TOP5) & (X.th >= .9)
print('Α) ΚΟΝΤΡΑ ΣΤΗΝ ΠΟΛΥ ΚΥΡΙΑΡΧΗ ΟΜΑΔΑ ΕΚΤΟΣ TOP-5 (η αγορα απομακρυνεται απο τους φιλοξενουμενους τετοιους, r −0.17)')
run('ΓΗΠΕΔΟΥΧΟΣ οταν ο φιλοξενουμενος ειναι πολυ κυριαρχη εκτος top-5', domA, 1)
run('   ... και ο γηπεδουχος ειναι top-5', domA & X.lgh.isin(TOP5), 1)
run('   ... και ο γηπεδουχος ειναι εκτος top-5', domA & ~X.lgh.isin(TOP5), 1)
run('ΦΙΛΟΞΕΝΟΥΜΕΝΟΣ οταν ο γηπεδουχος ειναι πολυ κυριαρχη εκτος top-5', domH, -1)
print('\nΒ) ΠΛΕΥΡΑ ΤΟΥ ΜΟΝΤΕΛΟΥ ΣΤΟ ΑΝΟΙΓΜΑ (η αγορα ερχεται προς το μοντελο, r +0.23)')
sgn = lambda y: np.where(y.md > 0, 1, -1)
for th in (0.2, 0.3, 0.5):
    run(f'μοντελο διαφωνει ≥{th} με το ανοιγμα', X.md.abs() >= th, sgn)
    run(f'   ... και ανοιξε >168ω πριν (πρωιμες γραμμες)', (X.md.abs() >= th) & (X.h_open > 168), sgn)
    run(f'   ... κατηγορια Α', (X.md.abs() >= th) & (X.cat == 'A'), sgn)
print('\nΓ) ΠΡΩΙΜΕΣ ΓΡΑΜΜΕΣ (>168ω) — φαβορι / αουτσαιντερ του ανοιγματος')
fav = lambda y: np.where(y.m0 > 0, 1, -1)
run('φαβορι ανοιγματος, γραμμη >168ω', X.h_open > 168, fav)
run('φαβορι ανοιγματος, γραμμη ≤168ω', X.h_open <= 168, fav)
