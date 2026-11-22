# -*- coding: utf-8 -*-
"""xi_55_model_split.py — 21/10/2026 (Στελιος: «τι picks εχει ακριβως ο πινακας; εβγαζε το μοντελο εκει edge;»).
Τα picks του 55′ (xi_market_timing) = ΜΟΝΟ προς τη μερια της ενδεκαδας, top 10% |φορμουλα|, χωρις ορο edge μοντελου.
Εδω: χωρισμα με το edge του live μοντελου (χωρις / με διορθωση ενδεκαδας) στην τιμη 55′, φαβορι vs αουτσαιντερ."""
import pandas as pd, numpy as np, picks, sys
sys.stdout.reconfigure(encoding='utf-8')
M = pd.read_csv('xi_market_timing_rows.csv', dtype={'mid': str, 'season': str})
P = pd.read_csv('core7_mech_preds_bl_0.6.csv', dtype={'mid': str})[['mid', 'xg_h', 'xg_a']]
M = M.merge(P, on='mid'); SE = sorted(M.season.unique())
def ed(pw, pp, o): return pw * (o - 1) * (1 - picks.MARGIN) - (1 - pw - pp)
rows = []
for bk in ('Crown', 'Bet365'):
    q = M[M.bk == bk]
    for s in SE:
        thr = q[q.season != s].f_gd.abs().quantile(.90); z = q[(q.season == s) & (q.f_gd.abs() >= thr)]
        for r in z.to_dict('records'):
            L, oh, oa = r['L_55′'], r['oh_55′'], r['oa_55′']
            if L != L or r['gd'] != r['gd']: continue
            side = 1 if r['f_gd'] > 0 else -1; ln = -L if side == 1 else L; o = oh if side == 1 else oa
            d0 = picks.gd_dist(max(r['xg_h'], .05), max(r['xg_a'], .05)); d1 = picks.gd_dist(max(r['xg_h'] + r['f_gd'] / 2, .05), max(r['xg_a'] - r['f_gd'] / 2, .05))
            rows.append(dict(bk=bk, season=s, pnl=picks.settle(r['gd'], side, ln, o), e0=ed(*picks.p_cover(d0, side, ln), o), e1=ed(*picks.p_cover(d1, side, ln), o), fav=ln < 0))
R = pd.DataFrame(rows)
def roi(q):
    s = q.groupby('season').pnl.mean(); return f"n {len(q) / 2:4.0f} · ROI {100 * q.pnl.mean():+5.1f}% · σεζον " + ' '.join(f'{100 * v:+.0f}' for v in s.values) + f" ({(s > 0).sum()}/4)"
print('ΟΛΑ:', roi(R))
for lab, lo, hi in (('μοντελο ΚΟΝΤΡΑ (edge < −5%)', -9, -.05), ('ουδετερο', -.05, .05), ('μοντελο ΥΠΕΡ (≥ +5%)', .05, 9)): print(f'   {lab:30s}', roi(R[(R.e0 >= lo) & (R.e0 < hi)]))
for lab, lo, hi in (('μοντ.+ενδ. edge < 0', -9, 0), ('0-5%', 0, .05), ('5-10%', .05, .10), ('≥ 10%', .10, 9)): print(f'   {lab:30s}', roi(R[(R.e1 >= lo) & (R.e1 < hi)]))
print('   φαβορι', roi(R[R.fav])); print('   αουτσαιντερ/0', roi(R[~R.fav]))
print(f'μεσο edge μοντελου: χωρις ενδεκαδα {100 * R.e0.mean():+.1f}% · με {100 * R.e1.mean():+.1f}%')
