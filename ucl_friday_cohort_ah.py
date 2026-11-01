"""ucl_friday_cohort_ah.py — ΧΑΝΤΙΚΑΠ μερος του ucl_friday_cohort (βλ. εκει). Champions League κατηγορια Α, 2223-2526."""
import sys
_s = open('ucl_early_honest.py', encoding='utf-8').read(); exec(_s[:_s.index('CL = {}')])
exec(open('ucl_friday_cohort.py', encoding='utf-8').read())
import euro_shadow_scan as ES
ROWS = {'φαβ': [], 'dog': [], 'dnb': []}
for k_ in range(len(x)):
    if x.cat[k_] != 'A': continue
    m = mids[k_]; i = int(x.i[k_]); ko = KO_.get(m)
    if not ko: continue
    P = points(ko); fri = P[0][1]
    D_ = ES.eu_dist(H4[0][k_], H4[1][k_], .85)
    for bk in ('Crown', 'SBOBET'):
        s0 = snapT(m, bk, (ko - fri) / 3600)
        if not s0: continue
        L0, oh0, oa0 = s0; mk0 = implied_margin(i, L0, oh0, oa0)
        for side, ln, o in ((1, L0, oh0), (-1, -L0, oa0)):
            if not (1.70 <= o <= 2.10): continue
            if ln <= -0.5: kind = 'φαβ'; pw, pp = cover_q(D_, side, ln); th = .10
            elif ln >= 0.5: kind = 'dog'; pw, pp = picks.p_cover(D_, side, ln); th = .04
            elif abs(ln) < .01: kind = 'dnb'; pw, pp = cover_q(D_, side, ln); th = .04
            else: continue
            if edge(pw, pp, o) < th: continue
            for lab, t in P:
                s = snapT(m, bk, 0 if t is None else (ko - t) / 3600)
                if not s: continue
                L, oh, oa = s; lnt = side * L; ot = oh if side == 1 else oa
                ROWS[kind].append(dict(lab=lab, sea=x.sea[k_], bk=bk, pnl=picks.settle(GD[i], side, lnt, ot), od=ot, inz=1.70 <= ot <= 2.10,
                                       mv=side * (implied_margin(i, L, oh, oa) - mk0)))
for kind, nm in (('φαβ', 'ΦΑΒΟΡΙ ≥10%'), ('dog', 'ΑΟΥΤΣΑΙΝΤΕΡ ≥4%'), ('dnb', 'DNB ≥4%')):
    R = pd.DataFrame(ROWS[kind])
    table(R, f'CHAMPIONS LEAGUE · {nm} (κατηγορια Α, 2223-2526) — ΙΔΙΑ picks της Παρασκευης σε καθε σημειο')
    table(R[R.sea.isin(('2425', '2526'))] if len(R) else R, f'   … μονο νεα μορφη (2425-2526)')
