"""uel_totals_A_assessment.py — 14/10/2026 (Στελιος: «ποια ειναι η διαφορα στα δεδομενα και αλλαξε το προσημο; συνολικη αποτιμηση των συνολων στο
europa στην κατηγορια Α — ποσο καλα προβλεπουμε σε σχεση με την αγορα, κλιση, λαθος κτλ· περιεργο που η αγορα δεν ερχεται προς εμας»).
Live μηχανη συνολων (W2, ισοπαλιες ×0.85), Europa League, FotMob+FotMob, 4 σεζον. Αγορα: Crown (αλλιως SBOBET), ΑΝΟΙΓΜΑ = πρωτη τιμη ≤72ω, ΚΛΕΙΣΙΜΟ.
 0) ΠΡΟΣΗΜΟ 2425: under ≥10% με/χωρις τα picks που εμφανιζονται ΜΟΝΟ στην τελευταια τιμη (h=0)
 1) μεροληψια · μεσο απολυτο λαθος (vs γκολ και vs xG) · 2) πληροφορια μοντελου περα απο την αγορα (κλιση b) · 3) Brier over (γραμμες x.5)
 4) ΚΙΝΗΣΗ ΑΓΟΡΑΣ ανοιγμα→κλεισιμο ως προς τη γνωμη του μοντελου · 5) ανα σεζον
"""
import sys, os
NL = chr(10)
src = open('uel_full_review.py', encoding='utf-8').read().split('# ======================= 1. ΣΥΝΟΛΑ')[0]
src = src.replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
_R = sys.stdout; sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(src); sys.stdout = _R; sys.stdout.reconfigure(encoding='utf-8')
# ---------- 0
rows = []
for i in UEL:
    if SRCC[i] != 'FF': continue
    td = ES.tot_dist(OH[i], OA[i], DRAW_SCALE); tot = GH[i] + GA[i]
    for bk in ('Crown', 'SBOBET'):
        for h in HS:
            s = snap_ou(MIDS[i], bk, h)
            if not s: continue
            L, o, un = s; po, pu = ES.p_over(td, L)
            if 1.70 <= un <= 2.10:
                rows.append(dict(i=i, bk=bk, h=h, sea=SEA[i], e=pu * (un - 1) * (1 - picks.MARGIN) - po, pnl=settle(tot, L, un, False)))
U = pd.DataFrame(rows)
def first_(x): return x.sort_values('h', ascending=False).groupby(['i', 'bk']).head(1)
A0 = first_(U[U.e >= .10]); A1 = first_(U[(U.e >= .10) & (U.h > 0)])
only0 = A0[A0.h == 0]
print('0) UNDER ≥10%, εισοδος ≤72ω — η διαφορα 10/10 vs σημερα')
print(f'   ΜΕ τα picks που βγαινουν μονο στην τελευταια τιμη (10/10):   {cc(A0)}')
print(f'   ΧΩΡΙΣ αυτα (σημερινο τεστ):                                 {cc(A1)}')
print(f'   τα picks «μονο τελευταια τιμη»: {cc(only0)}')
# ---------- 1-5
M = []
for i in UEL:
    if SRCC[i] != 'FF': continue
    for bk in ('Crown', 'SBOBET'):
        sc = snap_ou(MIDS[i], bk, 0)
        if not sc: continue
        so = None
        for h in HS[:-1]:
            so = snap_ou(MIDS[i], bk, h)
            if so: break
        if not so: continue
        Lc, oc, uc = sc; q = (1 / oc) / (1 / oc + 1 / uc)
        po, pu = ES.p_over(ES.tot_dist(OH[i], OA[i], DRAW_SCALE), Lc)
        x = XG.get(str(MIDS[i]))
        M.append(dict(i=i, bk=bk, sea=SEA[i], G=GH[i] + GA[i], X=sum(x) if x else np.nan, mod=OH[i] + OA[i], mo=mtot(*so), mc=mtot(*sc),
                      Lc=Lc, pm=po / (po + pu), pk=q))
        break
M = pd.DataFrame(M)
def ols(x, y):
    X = np.c_[np.ones(len(x)), x]; b, *_ = np.linalg.lstsq(X, y, rcond=None); e = y - X @ b
    se = np.sqrt(np.diag(np.linalg.inv(X.T @ X) * (e @ e) / (len(x) - 2))); return b[1], se[1]
def block(x, lab):
    xx = x[x.X.notna()]
    print(f'{NL}=== {lab}: {len(x)} ματς')
    print(f'   1) ΜΕΣΟΙ: γκολ {x.G.mean():.2f} · xG {xx.X.mean():.2f} · ΜΟΝΤΕΛΟ {x['mod'].mean():.2f} · αγορα ανοιγμα {x.mo.mean():.2f} · κλεισιμο {x.mc.mean():.2f}')
    for nm, c in (('ΜΟΝΤΕΛΟ', 'mod'), ('ανοιγμα', 'mo'), ('κλεισιμο', 'mc')):
        print(f'      {nm:9s} μεσο απολυτο λαθος vs γκολ {np.abs(x.G - x[c]).mean():.3f} · vs xG {np.abs(xx.X - xx[c]).mean():.3f} · '
              f'συσχετιση με xG {np.corrcoef(xx.X, xx[c])[0, 1]:.3f}')
    for tg, nm in (('G', 'γκολ'), ('X', 'xG')):
        y = xx if tg == 'X' else x
        b, s = ols((y['mod'] - y.mc).values, (y[tg] - y.mc).values)
        print(f'   2) ΠΛΗΡΟΦΟΡΙΑ μοντελου περα απο το κλεισιμο ({nm}): κλιση b {b:+.2f} ±{s:.2f} (t {b / s:+.1f})  [0 = τιποτα νεο · 1 = μοντελο σωστο]')
    b, s = ols((x['mod'] - x.mo).values, (x.G - x.mo).values)
    print(f'      ... περα απο το ΑΝΟΙΓΜΑ (γκολ): κλιση b {b:+.2f} ±{s:.2f} (t {b / s:+.1f})')
    h = x[(x.Lc * 2) % 1 == 0]; h = h[(h.Lc * 2) % 2 == 1]
    yv = (h.G > h.Lc).astype(float)
    print(f'   3) BRIER over (γραμμες x.5 στο κλεισιμο, {len(h)} ματς): μοντελο {((h.pm - yv) ** 2).mean():.4f} · αγορα {((h.pk - yv) ** 2).mean():.4f} · '
          f'P(over) μοντελο {h.pm.mean():.3f} / αγορα {h.pk.mean():.3f} / πραγμ {yv.mean():.3f}')
    b, s = ols((x['mod'] - x.mo).values, (x.mc - x.mo).values)
    d = x['mod'] - x.mo
    print(f'   4) ΚΙΝΗΣΗ ΑΓΟΡΑΣ (κλεισιμο − ανοιγμα) ως προς (μοντελο − ανοιγμα): κλιση {b:+.3f} ±{s:.3f} (t {b / s:+.1f})')
    for lo, hi, l in ((-9, -0.3, 'μοντελο ΧΑΜΗΛΟΤΕΡΑ ≥0.3 (under)'), (-0.3, 0.3, 'κοντα (±0.3)'), (0.3, 9, 'μοντελο ΨΗΛΟΤΕΡΑ ≥0.3 (over)')):
        y = x[(d >= lo) & (d < hi)]; yx = y[y.X.notna()]
        print(f'      {l:34s} n{len(y):4d} · κινηση αγορας {(y.mc - y.mo).mean():+.3f} · γκολ − κλεισιμο {(y.G - y.mc).mean():+.2f} · xG − κλεισιμο {(yx.X - yx.mc).mean():+.2f} · '
              f'μοντελο − κλεισιμο {(y["mod"] - y.mc).mean():+.2f}')
block(M, 'EUROPA ΚΑΤΗΓΟΡΙΑ Α — 4 σεζον')
print(NL + '5) ΑΝΑ ΣΕΖΟΝ: γκολ / xG / μοντελο / κλεισιμο · κλιση πληροφοριας (γκολ, xG) · Brier μοντελο−αγορα')
for s in SEAS:
    x = M[M.sea == s]; xx = x[x.X.notna()]
    b1, s1 = ols((x['mod'] - x.mc).values, (x.G - x.mc).values); b2, s2 = ols((xx['mod'] - xx.mc).values, (xx.X - xx.mc).values)
    h = x[(x.Lc * 2) % 2 == 1]; yv = (h.G > h.Lc).astype(float)
    print(f'   {s}: n{len(x):3d} · {x.G.mean():.2f} / {xx.X.mean():.2f} / {x["mod"].mean():.2f} / {x.mc.mean():.2f} · b γκολ {b1:+.2f}±{s1:.2f} · b xG {b2:+.2f}±{s2:.2f} · '
          f'Brier Δ {((h.pm - yv) ** 2).mean() - ((h.pk - yv) ** 2).mean():+.4f}')
