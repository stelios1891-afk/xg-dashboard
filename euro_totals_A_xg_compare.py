"""euro_totals_A_xg_compare.py — 14/10/2026 (Στελιος: «στο Champions League ή στο Conference, εκει που εχουμε live τα συνολα, φαινεται κατι
διαφορετικο; φαινεται στα τελικα xG οτι προβλεπουμε καλυτερα;»). ΙΔΙΑ αποτιμηση με uel_totals_A_assessment για UCL / UEL / UECL, κατηγορια Α,
live μηχανη συνολων (W2, ισοπαλιες ×0.85, κ UCL νεας μορφης). + τα LIVE picks συνολων (UCL over ≥4% / under ≥10% · UECL over ≥−2% · UEL για
συγκριση over ≥4% / under ≥10%), πρωτη εμφανιση ≤72ω (χωρις την τελευταια τιμη): ROI πραγματικο vs ΑΞΙΑ ΜΕ ΒΑΣΗ ΤΑ ΤΕΛΙΚΑ xG.
"""
import sys, os
NL = chr(10)
src = open('uel_full_review.py', encoding='utf-8').read().split('# ======================= 1. ΣΥΝΟΛΑ')[0]
src = src.replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
_R = sys.stdout; sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(src); sys.stdout = _R; sys.stdout.reconfigure(encoding='utf-8')
def ols(x, y):
    X = np.c_[np.ones(len(x)), x]; b, *_ = np.linalg.lstsq(X, y, rcond=None); e = y - X @ b
    se = np.sqrt(np.diag(np.linalg.inv(X.T @ X) * (e @ e) / (len(x) - 2))); return b[1], se[1]
RULES = {'ChampionsLeague': (('over', .04), ('under', .10)), 'ConferenceLeague': (('over', -.02),), 'EuropaLeague': (('over', .04), ('under', .10))}
for cm, lab, live in (('ChampionsLeague', 'CHAMPIONS LEAGUE', 'live over 4% / under 10%'), ('ConferenceLeague', 'CONFERENCE', 'live over −2%'),
                      ('EuropaLeague', 'EUROPA', 'ΟΧΙ live — για συγκριση')):
    IDX = [i for i in np.where(COMP == cm)[0] if SRCC[i] == 'FF']
    M = []; P = []
    for i in IDX:
        td = ES.tot_dist(OH[i], OA[i], DRAW_SCALE); x = XG.get(str(MIDS[i])); tot = GH[i] + GA[i]
        tdx = ES.tot_dist(max(x[0], .05), max(x[1], .05), DRAW_SCALE) if x else None
        done = False
        for bk in ('Crown', 'SBOBET'):
            sc = snap_ou(MIDS[i], bk, 0)
            if not sc: continue
            so = None
            for h in HS[:-1]:
                so = snap_ou(MIDS[i], bk, h)
                if so: break
            if so and not done:
                Lc, oc, uc = sc; po, pu = ES.p_over(td, Lc)
                M.append(dict(sea=SEA[i], G=tot, X=sum(x) if x else np.nan, mod=OH[i] + OA[i], mo=mtot(*so), mc=mtot(*sc), Lc=Lc,
                              pm=po / (po + pu), pk=(1 / oc) / (1 / oc + 1 / uc)))
                done = True
            for side, th in RULES[cm]:
                for h in HS[:-1]:
                    s = snap_ou(MIDS[i], bk, h)
                    if not s: continue
                    L, o, un = s; po, pu = ES.p_over(td, L); od = o if side == 'over' else un
                    if not (1.70 <= od <= 2.10): continue
                    pw, pl = (po, pu) if side == 'over' else (pu, po)
                    if pw * (od - 1) * (1 - picks.MARGIN) - pl < th: continue
                    xv = np.nan
                    if tdx is not None:
                        qo, qu = ES.p_over(tdx, L); qw, ql = (qo, qu) if side == 'over' else (qu, qo); xv = qw * (od - 1) * (1 - picks.MARGIN) - ql
                    P.append(dict(sea=SEA[i], bk=bk, side=side, pnl=settle(tot, L, od, side == 'over'), xv=xv))
                    break
    M = pd.DataFrame(M); P = pd.DataFrame(P); xx = M[M.X.notna()]
    print(f'{NL}===== {lab} κατηγορια Α ({live}) — {len(M)} ματς')
    print(f'   μεσοι: γκολ {M.G.mean():.2f} · xG {xx.X.mean():.2f} · μοντελο {M["mod"].mean():.2f} · κλεισιμο {M.mc.mean():.2f}')
    print(f'   μεσο απολυτο λαθος vs xG: μοντελο {np.abs(xx.X - xx["mod"]).mean():.3f} · κλεισιμο {np.abs(xx.X - xx.mc).mean():.3f}   '
          f'(vs γκολ: {np.abs(M.G - M["mod"]).mean():.3f} / {np.abs(M.G - M.mc).mean():.3f})')
    b1, s1 = ols((M['mod'] - M.mc).values, (M.G - M.mc).values); b2, s2 = ols((xx['mod'] - xx.mc).values, (xx.X - xx.mc).values)
    print(f'   ΠΛΗΡΟΦΟΡΙΑ μοντελου περα απο το κλεισιμο: προς γκολ b {b1:+.2f} ±{s1:.2f} · ΠΡΟΣ xG b {b2:+.2f} ±{s2:.2f} (t {b2 / s2:+.1f})')
    h = M[(M.Lc * 2) % 2 == 1]; yv = (h.G > h.Lc).astype(float)
    print(f'   Brier over (x.5, {len(h)}): μοντελο {((h.pm - yv) ** 2).mean():.4f} · αγορα {((h.pk - yv) ** 2).mean():.4f}')
    b3, s3 = ols((M['mod'] - M.mo).values, (M.mc - M.mo).values); d = M['mod'] - M.mo
    print(f'   ΚΙΝΗΣΗ ΑΓΟΡΑΣ προς μοντελο: κλιση {b3:+.2f} (t {b3 / s3:+.1f}) · οταν μοντελο over ≥0.3: {(M.mc - M.mo)[d >= .3].mean():+.2f} (n{(d >= .3).sum()}) · '
          f'οταν under ≥0.3: {(M.mc - M.mo)[d <= -.3].mean():+.2f} (n{(d <= -.3).sum()})')
    for nw, ss in (('4 σεζον', SEAS), ('νεα μορφη', NEW)):
        b2, s2 = ols((xx[xx.sea.isin(ss)]['mod'] - xx[xx.sea.isin(ss)].mc).values, (xx[xx.sea.isin(ss)].X - xx[xx.sea.isin(ss)].mc).values)
        line = f'   [{nw}] πληροφορια προς xG b {b2:+.2f} ±{s2:.2f}'
        for side, th in RULES[cm]:
            y = P[(P.side == side) & P.sea.isin(ss)]
            if len(y): line += f' · {side} ≥{int(th * 100)}%: {len(y) / 2:.0f} picks ROI {100 * y.pnl.mean():+.1f}% / ΑΞΙΑ xG {100 * y.xv.mean():+.1f}%'
        print(line)
