"""ucl_friday_cohort_tot.py — ΣΥΝΟΛΑ μερος του ucl_friday_cohort (βλ. εκει). Over Α ≥4% · Over Β ≥4% (×1.22) · Under Α ≥10%."""
import sys, os, pickle
_s = open('ucl_early_honest_totals.py', encoding='utf-8').read(); _s = _s[:_s.index("print(f'αλλαγη συνολου")]
_s = _s.replace("I = np.array([i for i in np.where(COMP == 'ChampionsLeague')[0] if SRCC[i] == 'FF'])",
                "I = np.array([i for i in np.where(COMP == 'ChampionsLeague')[0] if SRCC[i] in ('FF', 'BF', 'FG')])", 1)
exec(_s)
exec(open('ucl_friday_cohort.py', encoding='utf-8').read())
CAT = np.array(['A' if SRCC[i] == 'FF' else 'B' for i in I])
FMH = np.array([_V['src_h'][_VI[str(MIDS[i])]] == 'shots' for i in I])
oh4, oa4 = H4
oh4 = np.where((CAT == 'B') & FMH, oh4 * 1.22, oh4); oa4 = np.where((CAT == 'B') & ~FMH, oa4 * 1.22, oa4)
ROWS = {'overA': [], 'overB': [], 'underA': []}
for k in range(len(I)):
    m = M[k]; ko = KO.get(m)
    if not ko: continue
    P = points(ko); fri = P[0][1]
    td = ES.tot_dist(oh4[k], oa4[k], DRAW_SCALE)
    for bk in ('Crown', 'SBOBET'):
        s0 = snap_ou(m, bk, (ko - fri) / 3600)
        if not s0: continue
        L0, o0, u0 = s0; po, pu = ES.p_over(td, L0); T0 = mtot(L0, o0, u0)
        for side, od, pw, pl_, th in (('over', o0, po, pu, .04), ('under', u0, pu, po, .10)):
            key = side + CAT[k]
            if key not in ROWS or not (1.70 <= od <= 2.10) or pw * (od - 1) * (1 - picks.MARGIN) - pl_ < th: continue
            for lab, t in P:
                s = snap_ou(m, bk, 0 if t is None else (ko - t) / 3600)
                if not s: continue
                L, o, un = s; ot = o if side == 'over' else un
                ROWS[key].append(dict(lab=lab, sea=S[k], bk=bk, pnl=settle(TOT[k], L, ot, side == 'over'), od=ot, inz=1.70 <= ot <= 2.10,
                                      mv=(mtot(L, o, un) - T0) * (1 if side == 'over' else -1)))
for key, nm in (('overA', 'OVER ≥4% κατηγορια Α'), ('overB', 'OVER ≥4% κατηγορια Β (×1.22)'), ('underA', 'UNDER ≥10% κατηγορια Α')):
    R = pd.DataFrame(ROWS[key])
    table(R[R.sea.isin(('2425', '2526'))] if len(R) else R, f'CHAMPIONS LEAGUE · {nm} — ΝΕΑ ΜΟΡΦΗ 2425-2526 — ΙΔΙΑ picks της Παρασκευης')
    table(R, f'   … και τα 4 χρονια 2223-2526')
