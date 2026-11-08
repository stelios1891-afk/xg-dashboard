# -*- coding: utf-8 -*-
"""ucl_under_by_line.py — 19/10/2026 (Στελιος: «το under στο Σιτι-ΑΕΚ απο που προκυπτει; ιστορικα under σε μεγαλα lines (3 και πανω) πως εχουν αποδωσει;
χασαμε Φεγενορντ-Κομο και Ρομα-Ρεαλ»). Live κανονας UCL under: κατηγορια Α, edge ≥10%, 1.70-2.10, μηχανη συνολων (W2 + κ, ισοπαλιες ×0.85),
Crown & SBOBET (μεσος). Τιμη στις 72/48/24/12ω πριν και κλεισιμο · ανα ΓΡΑΜΜΗ: <3 · 3-3.5 · ≥3.75 · νεα μορφη (2425-2526) και ολες."""
import sys, os
_s = open('uel_full_review.py', encoding='utf-8').read().split("print('=' * 100 + NL + '1. ΣΥΝΟΛΑ")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
_TO = sys.stdout; sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(_s); sys.stdout = _TO
sys.stdout.reconfigure(encoding='utf-8')
def snap_ou(mid, bk, h):
    ko = KO.get(mid); seq = TOU.get((mid, bk))
    if not ko or not seq: return None
    cut = ko - h * 3600 if h else ko + 900
    prev = [x for x in seq if x[0] <= cut]
    return prev[-1][1:] if prev else None
I = np.array([i for i in np.where(COMP == 'ChampionsLeague')[0] if SRCC[i] == 'FF']); M = [str(MIDS[i]) for i in I]; S = SEA[I]; TOT = GH[I] + GA[I]
rows = []
for h in (72, 48, 24, 12, 0):
    for k in range(len(I)):
        td = ES.tot_dist(OH[I][k], OA[I][k], DRAW_SCALE)
        for bk in ('Crown', 'SBOBET'):
            s = snap_ou(M[k], bk, h)
            if not s: continue
            L, o, un = s; po, pu = ES.p_over(td, L)
            if not (1.70 <= un <= 2.10): continue
            e = pu * (un - 1) * (1 - picks.MARGIN) - po
            if e < 0.10: continue
            rows.append(dict(h=h, sea=S[k], bk=bk, L=L, mt=OH[I][k] + OA[I][k], tot=TOT[k], pnl=settle(TOT[k], L, un, False)))
D = pd.DataFrame(rows)
def cell(y):
    if not len(y): return '—'
    m = y.groupby('bk').pnl.mean(); n = y.groupby('bk').size().mean(); s = y.groupby('sea').pnl.mean()
    return f'{n:4.0f} picks {100 * m.mean():+6.1f}% {m.mean() * n:+6.1f}μ θετ.σεζ {int((s > 0).sum())}/{len(s)} · γκολ {y.tot.mean():.2f} vs μοντ {y.mt.mean():.2f}'
for per, f in (('ΝΕΑ ΜΟΡΦΗ 2024-26', D.sea.isin(['2425', '2526'])), ('ΟΛΕΣ 2022-26', D.sea.notna())):
    print(f'\n== UCL UNDER ≥10% (κατηγορια Α) · {per} ==')
    for h in (72, 48, 24, 12, 0):
        y0 = D[f & (D.h == h)]
        print(f'  {"κλεισιμο" if h == 0 else str(h) + "ω πριν":9s} ΟΛΑ   {cell(y0)}')
        for lab, lo, hi in (('γραμμη <3', 0, 2.9), ('3 - 3.5', 2.9, 3.6), ('≥3.75', 3.6, 99)):
            print(f'  {"":9s} {lab:9s} {cell(y0[(y0.L >= lo) & (y0.L < hi)])}')
