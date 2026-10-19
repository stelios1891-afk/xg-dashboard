# -*- coding: utf-8 -*-
"""ucl_over_vs_under.py — 19/10/2026 (Στελιος: «τι ποσοστο ειναι τα under σε συγκριση με τα over στα συνολα του Champions League;»).
UCL κατηγορια Α, μηχανη συνολων live, τιμη 48ω πριν (Crown/SBOBET μεσος): (1) picks over (≥4%) vs under (≥10%) — ποσα, ROI, ανα σεζον ·
(2) ΒΑΣΗ: ποσο συχνα το ματς πηγε over/under της κυριας γραμμης κλεισιματος (χωρις μοντελο) + τυφλο over/under στο κλεισιμο."""
import sys, os
_s = open('uel_full_review.py', encoding='utf-8').read().split("print('=' * 100 + NL + '1. ΣΥΝΟΛΑ")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
_KEEP = sys.stdout; sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(_s); sys.stdout = _KEEP
sys.stdout.reconfigure(encoding='utf-8')
def snap_ou(mid, bk, h):
    ko = KO.get(mid); seq = TOU.get((mid, bk))
    if not ko or not seq: return None
    cut = ko - h * 3600 if h else ko + 900
    prev = [x for x in seq if x[0] <= cut]
    return prev[-1][1:] if prev else None
I = np.array([i for i in np.where(COMP == 'ChampionsLeague')[0] if SRCC[i] == 'FF']); M = [str(MIDS[i]) for i in I]; S = SEA[I]; TOT = GH[I] + GA[I]
P, B = [], []
for k in range(len(I)):
    td = ES.tot_dist(OH[I][k], OA[I][k], DRAW_SCALE)
    for bk in ('Crown', 'SBOBET'):
        c = snap_ou(M[k], bk, 0)
        if c:
            L, o, u = c
            B.append(dict(sea=S[k], bk=bk, over=TOT[k] > L, under=TOT[k] < L, po=settle(TOT[k], L, o, True), pu=settle(TOT[k], L, u, False)))
        s = snap_ou(M[k], bk, 48)
        if not s: continue
        L, o, un = s; po, pu = ES.p_over(td, L)
        for side, od, pw, pl_, th in (('over', o, po, pu, .04), ('under', un, pu, po, .10)):
            if 1.70 <= od <= 2.10 and pw * (od - 1) * (1 - picks.MARGIN) - pl_ >= th:
                P.append(dict(sea=S[k], bk=bk, side=side, pnl=settle(TOT[k], L, od, side == 'over')))
P, B = pd.DataFrame(P), pd.DataFrame(B)
for per, ss in (('ΝΕΑ ΜΟΡΦΗ 2024-26', ['2425', '2526']), ('ΟΛΕΣ 2022-26', ['2223', '2324', '2425', '2526'])):
    p, b = P[P.sea.isin(ss)], B[B.sea.isin(ss)]
    n = p.groupby(['side', 'bk']).size().groupby('side').mean(); tot = n.sum()
    print(f'\n== {per} ==')
    print(f'  ΒΑΣΗ ({len(b) // 2} ματς): πηγε OVER της γραμμης κλεισιματος {100 * b.over.mean():.0f}% · UNDER {100 * b.under.mean():.0f}% · '
          f'τυφλο over στο κλεισιμο {100 * b.po.mean():+.1f}% · τυφλο under {100 * b.pu.mean():+.1f}%')
    for sd in ('over', 'under'):
        y = p[p.side == sd]; m = y.groupby('bk').pnl.mean(); s = y.groupby('sea').pnl.mean()
        print(f'  PICKS {sd.upper():5s}: {n.get(sd, 0):4.0f} ({100 * n.get(sd, 0) / tot:.0f}% των picks συνολων) · ROI {100 * m.mean():+.1f}% · μοναδες {m.mean() * n.get(sd, 0):+.1f} · '
              + ' '.join(f'{k}:{100 * v:+.0f}%' for k, v in s.items()))
