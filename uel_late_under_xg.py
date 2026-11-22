"""uel_late_under_xg.py — 14/10/2026. Συμπληρωμα uel_late_under_test: για τα under Α (≥10%, ≤12ω και ≤72ω) και, για συγκριση, τα over Α (≥8%, ≤12ω):
ΑΞΙΑ ΜΕ ΒΑΣΗ ΤΑ ΤΕΛΙΚΑ xG (πιθανοτητα under/over απο Poisson με τα xG του ματς, ισοπαλιες ×0.85 οπως η μηχανη) → κερδος απο παιχνιδι ή απο φινιρισμα;
"""
import sys, os
NL = chr(10)
def load(fn):
    src = open(fn, encoding='utf-8').read().split("for win in ('≤12ω'")[0]
    g = {'__name__': 'x'}; _R = sys.stdout; sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(src, g); sys.stdout = _R
    return g
sys.stdout.reconfigure(encoding='utf-8')
for fn, lab, th, under in (('uel_late_under_test.py', 'UNDER', .10, True), ('uel_late_over_test.py', 'OVER', .08, False)):
    g = load(fn); ES, XG, MIDS, np = g['ES'], g['XG'], g['MIDS'], g['np']
    for win in (('≤12ω', '≤72ω') if under else ('≤12ω',)):
        F = g['stream'](win, th).copy(); xv = []
        for r in F.itertuples():
            x = XG.get(str(MIDS[r.i]))
            if not x: xv.append(np.nan); continue
            po, pu = ES.p_over(ES.tot_dist(max(x[0], .05), max(x[1], .05), g['DRAW_SCALE']), r.L)
            p, q = (pu, po) if under else (po, pu)
            xv.append(p * (r.od - 1) * (1 - g['picks'].MARGIN) - q)
        F['xv'] = xv
        ps = F.groupby('sea').xv.mean()
        print(f'{lab} {win} ≥{int(th * 100)}%: {len(F) / 2:.0f} picks · ROI πραγματικο {100 * F.pnl.mean():+.1f}% · ΑΞΙΑ ΜΕ ΒΑΣΗ xG {100 * F.xv.mean():+.1f}% ('
              + ' '.join(f'{s[2:]} {100 * v:+.0f}' for s, v in ps.items()) + ')')
