# -*- coding: utf-8 -*-
"""t25b_groups_behavior.py — ΦΑΣΗ 3β: ΣΥΜΠΕΡΙΦΟΡΑ (πενταδες, t25) ανα ΓΚΡΟΥΠ ΚΙΝΗΤΡΟΥ (t24), Μαρτιος/Απριλιος (21/10/2026).
Για καθε γκρουπ: μεσος ορος ΤΟΥ ΜΑΤΣ και Δ = ματς − μεσος ορος της ιδιας ομαδας στα προηγουμενα ματς (αλλαξε συμπεριφορα;).
Μεγεθη: λεπτα 5 βασικων · ποσοι βασικοι εκτος · μεριδιο λεπτων σε περιθωριακους (εκτος 8) · βασικοι στην 4η · βασικοι στην 4η σε κοντινο (≤8) ·
βασικοι στα τελευταια 5′ με διαφορα ≤6. Περιγραφικο. Εξοδος: t25b_groups_behavior_out.txt"""
import os, sys, pickle
import numpy as np, pandas as pd
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
sys.stdout.reconfigure(encoding='utf-8')
G = pickle.load(open(os.path.join(ROOT, 'nba_diag_data.pkl'), 'rb'))['G'].reset_index(drop=True)
X = pd.read_csv(os.path.join(SC, '_t24_groups.csv'))
X['date'] = G.date.dt.strftime('%Y-%m-%d').values[X.i]
F = pd.read_csv(os.path.join(SC, '_t25_feats.csv'))
M = X.merge(F.drop(columns=['sea', 'opp', 'home']), left_on=['date', 't'], right_on=['date', 'team'], how='left')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
P('NBA · ΦΑΣΗ 3: ΣΥΜΠΕΡΙΦΟΡΑ ΑΝΑ ΓΚΡΟΥΠ (ESPN πενταδες) · Δ = ματς − μεσος ορος ιδιας ομαδας πριν')
for mon in (1, 2, 3, 4):
    d = M[(M.mon == mon) & M.core_min.notna()]; n0 = len(M[M.mon == mon])
    P(f'  ταιριασμα μηνα {mon}: {len(d)}/{n0}')
KS = [('core_min', 'λεπτα 5 βασικων', 1), ('core_dnp', 'βασικοι εκτος', 2), ('fringe_sh', '% λεπτων περιθωρ.', 100),
      ('q4_core', '% βασικων 4η', 100), ('q4c_close', '% βασ. 4η κοντινο', 100), ('close_core', '% βασ. τελ.5′ ≤6', 100)]
GROUPS = ('ΚΛΕΙΔΩΜΕΝΗ', 'ΜΑΧΗ ΘΕΣΗΣ 1-6', 'ΜΑΧΗ PLAY-IN', 'ΑΔΙΑΦΟΡΗ', 'TANKING')
for mon, per in ((3, 'ΜΑΡΤΙΟΣ'), (4, 'ΑΠΡΙΛΙΟΣ')):
    P(''); P(f'=== {per} === (τιμη ματς · [Δ απο τον μεσο ορο της ομαδας])')
    P(f'  {"γκρουπ":16s} {"ματς":>5s} | ' + ' | '.join(f'{lab:>20s}' for _, lab, _ in KS))
    for g in GROUPS:
        d = M[(M.mon == mon) & (M.g == g) & M.core_min.notna()]
        if not len(d): continue
        cells = []
        for k, lab, sc in KS:
            if k == 'core_dnp': cells.append(f'{d[k].mean():6.2f}{"":14s}'); continue
            v = d[k].dropna(); dv = (d[k] - d[k + '_avg']).dropna()
            cells.append(f'{sc * v.mean():6.1f} [{sc * dv.mean():+5.1f}] n{len(v):3d}')
        P(f'  {g:16s} {len(d):5d} | ' + ' | '.join(f'{c:>20s}' for c in cells))
# τελευταιες 3 μερες vs νωριτερα (Απριλιος)
M['dt'] = pd.to_datetime(M.date); M['last'] = M.groupby(['sea', 't']).dt.transform('max'); M['dleft'] = (M['last'] - M['dt']).dt.days
P(''); P('=== ΑΠΡΙΛΙΟΣ: τελευταιες 3 μερες vs νωριτερα (Δ λεπτων βασικων · Δ % περιθωριακων · % βασ. 4η κοντινο) ===')
for g in GROUPS:
    for lab, m in (('νωριτερα', M.dleft > 3), ('τελ. 3 μερες', M.dleft <= 3)):
        d = M[(M.mon == 4) & (M.g == g) & m & M.core_min.notna()]
        if len(d) < 10: continue
        P(f'  {g:16s} {lab:12s} n{len(d):4d} · Δ λεπτα βασικων {(d.core_min - d.core_min_avg).mean():+6.1f} · Δ περιθωρ. {100 * (d.fringe_sh - d.fringe_sh_avg).mean():+5.1f}% · '
          f'βασικοι εκτος {d.core_dnp.mean():.2f} · βασ. 4η κοντινο {100 * d.q4c_close.mean():5.1f}% · υπολοιπο μοντελου {d.rm.mean():+5.2f} · αγορα {d.rc.mean():+5.2f}')
M.to_csv(os.path.join(SC, '_t25b_merged.csv'), index=False)
open(os.path.join(SC, 't25b_groups_behavior_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
