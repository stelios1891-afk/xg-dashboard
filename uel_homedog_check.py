"""uel_homedog_check.py — 9/10 (Στελιος: «αν κοβαμε τα φαβορι εκτος, γιατι δεν βρισκουμε αουτσαιντερ εντος με αξια;»).
UEL, FotMob+FotMob, 2223-2526: για ΟΛΟΥΣ τους αουτσαιντερ εντος (1.70-2.10): τι edge τους δινει το μοντελο, τι λεει η αγορα, τι εγινε.
Και picks αουτσαιντερ εντος με χαμηλοτερα κατωφλια (≥0%, ≥4%) στο κλεισιμο και −24ω — περιγραφικο."""
import sys, io, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('uel_timing.py', encoding='utf-8').read(); src = src[:src.index('B = pd.DataFrame(rows)')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
g = {'__name__': 'hd'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
MIDS, GD, SEA, COMP, FM, picks, LH_N, LA_N, sdist, edge, snap = (g[k] for k in ('MIDS', 'GD', 'SEA', 'COMP', 'FM', 'picks', 'LH_N', 'LA_N', 'sdist', 'edge', 'snap'))
R = []
for i, mid in enumerate(MIDS):
    if COMP[i] != 'EuropaLeague' or not FM[i]: continue
    dist = sdist(LH_N[i], LA_N[i])
    for bk in ('Crown', 'SBOBET'):
        for h in (24, 0):
            s = snap(mid, bk, h)
            if not s: continue
            L, oh, oa = s
            if L < 0.5 or not (1.70 <= oh <= 2.10): continue          # γηπεδουχος αουτσαιντερ (παιρνει ≥ +0.5)
            pw, pp = picks.p_cover(dist, 1, L); e = edge(pw, pp, oh)
            R.append(dict(sea=SEA[i], book=bk, h=h, e=e, sup_mod=LH_N[i] - LA_N[i], line=L, pnl=picks.settle(GD[i], 1, L, oh)))
D = pd.DataFrame(R)
def c(d):
    if len(d) < 4: return f'n{len(d) / 2:4.0f}'
    ps = d.groupby('sea').pnl.mean(); return f'n{len(d) / d.book.nunique():4.0f} {100 * d.pnl.mean():+6.1f}% {int((ps > 0).sum())}/{ps.size}'
for h in (0, 24):
    x = D[D.h == h]; lab = 'κλεισιμο' if h == 0 else '24ω πριν'
    print(f'[{lab}] ΟΛΟΙ οι αουτσαιντερ εντος: {c(x)} · edge μοντελου: μεσος {100 * x.e.mean():+.1f}% · ≥10% σε {100 * (x.e >= .10).mean():.0f}% · ≥4% σε {100 * (x.e >= .04).mean():.0f}% · ≥0% σε {100 * (x.e >= 0).mean():.0f}%')
    for lo, lab2 in ((0.10, '≥10% (σημερινος κανονας)'), (0.04, '≥4%'), (0.0, '≥0%'), (-9, 'ολοι')):
        print(f'     edge {lab2:26s} {c(x[x.e >= lo])}')
    print(f'     edge <0 (το μοντελο λεει «οχι»)  {c(x[x.e < 0])}')
# ---- με διορθωση εδρας UEL (h: γηπεδουχος λ×h, φιλοξενουμενος λ÷h· LOSO στο uel_battery εδινε 1.02-1.06) ----
print('\nΜΕ ΔΙΟΡΘΩΣΗ ΕΔΡΑΣ UEL — picks αουτσαιντερ ΕΝΤΟΣ και φαβορι ΕΝΤΟΣ (κλεισιμο | 24ω πριν)')
for hcor in (1.0, 1.04, 1.08):
    out = []
    for i, mid in enumerate(MIDS):
        if COMP[i] != 'EuropaLeague' or not FM[i]: continue
        dist = sdist(LH_N[i] * hcor, LA_N[i] / hcor)
        for bk in ('Crown', 'SBOBET'):
            for h in (24, 0):
                s = snap(mid, bk, h)
                if not s: continue
                L, oh, oa = s
                if not (1.70 <= oh <= 2.10) or abs(L) < 0.5: continue
                role = 'dog' if L > 0 else 'fav'
                pw, pp = picks.p_cover(dist, 1, L) if role == 'dog' else g['cover_q'](dist, 1, L)
                e = edge(pw, pp, oh)
                out.append(dict(sea=SEA[i], book=bk, h=h, role=role, e=e, pnl=picks.settle(GD[i], 1, L, oh)))
    O = pd.DataFrame(out)
    cells = []
    for role, thr in (('dog', 0.04), ('dog', 0.10), ('fav', 0.04)):
        for h in (0, 24):
            cells.append(f'{role}≥{int(thr * 100)}% {"κλ" if h == 0 else "24ω"} {c(O[(O.role == role) & (O.h == h) & (O.e >= thr)])}')
    print(f'   εδρα ×{hcor}: ' + ' · '.join(cells))
