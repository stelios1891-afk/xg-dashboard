"""uel_totals_under_check.py — 15/10/2026 (Στελιος: «βοηθαει καποια διορθωση στα συνολα;»). Ελεγχος: το under με xG 100% / ισοπαλιες ×1.00
βγαζει ΚΑΤΙ ΝΕΟ ή απλως περισσοτερα under (σαν χαμηλοτερο κατωφλι); Συγκριση με τη βαση σε κατωφλια 2-10% με ιδιο περιπου πληθος picks,
και επικαλυψη picks. Επισης: βαση με/χωρις φετινα ευρωπαικα σε over/under."""
import sys
_s = open('uel_totals_mechanisms.py', encoding='utf-8').read(); exec(_s[:_s.index('SEAS_ = sorted')])
SEAS_ = sorted(set(S))
def u(y): return y.groupby('bk').pnl.sum().mean() if len(y) else 0.0
def cell(y):
    if len(y) == 0: return '—'
    m = y.groupby('bk').pnl.mean(); n = y.groupby('bk').size().mean()
    return f'{n:4.0f} {100 * m.mean():+5.1f}% {m.mean() * n:+6.1f}μ │ ' + ' '.join(f'{u(y[y.sea == s]):+5.1f}' for s in SEAS_)
def picks_th(oh, oa, ds, side, th, win=72):
    MK[:] = [('X', side, th, win)]; _, P = run(oh, oa, ds); return P
print('UNDER ≤72ω — βαση (xG 60%, ×0.85) σε χαμηλοτερα κατωφλια vs διορθωσεις στο 10%  · picks/βιβλιο · ROI · μοναδες │ ανα σεζον 22/23/24/25')
for th in (.10, .08, .06, .04, .02):
    print(f'   βαση ≥{int(th * 100):2d}%              {cell(picks_th(OH0, OA0, .85, "under", th))}')
X1 = rp(P('bl1.0'), P('bl0.6'))
U100 = picks_th(*X1, .85, 'under', .10); print(f'   xG 100% ≥10%          {cell(U100)}')
UD1 = picks_th(OH0, OA0, 1.0, 'under', .10); print(f'   ισοπαλιες ×1.00 ≥10%  {cell(UD1)}')
B6 = picks_th(OH0, OA0, .85, 'under', .04)
k0 = set(zip(B6.k, B6.bk)); kx = set(zip(U100.k, U100.bk))
print(f'   επικαλυψη xG100≥10% με βαση≥4%: κοινα {len(k0 & kx) / 2:.0f} · μονο xG100 {len(kx - k0) / 2:.0f} {cell(U100[[t not in k0 for t in zip(U100.k, U100.bk)]])}')
print(f'{NL}ΦΕΤΙΝΑ ΕΥΡΩΠΑΙΚΑ στα συνολα (βαρος 0 vs 0.5 = live)')
I5 = ris('0.5')
for nm, side, th, win in (('OVER ≥8% ≤12ω', 'over', .08, 12), ('UNDER ≥10% ≤72ω', 'under', .10, 72)):
    print(f'   {nm:16s} βαρος 0:   {cell(picks_th(OH0, OA0, .85, side, th, win))}')
    print(f'   {"":16s} βαρος 0.5: {cell(picks_th(*I5, .85, side, th, win))}')
print(f'{NL}ΑΝΑ ΒΙΒΛΙΟ (ROI) — under ≥10% ≤72ω')
for nm, Pk in (('βαση', picks_th(OH0, OA0, .85, 'under', .10)), ('xG 100%', U100), ('μονο xG100 (34)', U100[[t not in k0 for t in zip(U100.k, U100.bk)]])):
    print(f'   {nm:16s} ' + ' · '.join(f'{b} {len(Pk[Pk.bk == b])} {100 * Pk[Pk.bk == b].pnl.mean():+.1f}%' for b in ('Crown', 'SBOBET')))
