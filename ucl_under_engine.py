"""
ucl_under_engine.py — 10/10/2026 (Στελιος: «η μηχανη των under: πως ειναι φτιαγμενη, πως συγκρινεται με αγορα και πραγματικοτητα, που χανει,
κλιση, προβλεψη — οτι τεστ δειχνει κατι»). Champions League, ΝΕΑ μορφη (2425-26) = live· παλια (2223-24) μονο για συγκριση.
ΜΗΧΑΝΗ (ιδια για over/under, live ζευγος xgh_ou/xga_ou): ratings με πεναλτι 0.76 (W2), χωρις γ, κ ×1.16 στο φαβορι UCL νεας μορφης,
ανεξαρτητα Poisson γκολ γηπ/φιλ, ΜΕ ενισχυση ισοπαλιων ×1.13 (εγχωρια DRAW_BOOST — ενω τα ευρωπαικα 1Χ2 χρησιμοποιουν ×0.85),
τιμολογηση τεταρτων (euro_shadow_scan.tot_dist / p_over).
1. ΒΑΘΜΟΝΟΜΗΣΗ: μοντελο vs πραγματικα vs αγορα (κλεισιμο, Crown)· ανα επιπεδο μοντελου· ΚΛΙΣΕΙΣ: πραγμ ~ μοντελο, πραγμ ~ αγορα,
   (πραγμ − αγορα) ~ (μοντελο − αγορα) = πληροφορια πανω απο την αγορα.
2. ΠΙΘΑΝΟΤΗΤΑ UNDER στην κυρια γραμμη: μοντελο vs συχνοτητα vs αγορα, Brier.
3. UNDER picks @4% στο κλεισιμο (μεσος Crown/SBOBET): που χανουν — ανα γραμμη, επιπεδο μοντελου, διαφορα με αγορα, δυναμη φαβορι.
4. ΠΑΡΑΛΛΑΓΗ ισοπαλιων στα συνολα: ×1.13 (σημερα) / ×1.00 / ×0.85 (οπως το 1Χ2 Ευρωπης) — Brier & ROI under/over.
5. ΧΡΟΝΙΣΜΟΣ under (ροη πρωτης εμφανισης).
"""
import sys, io, math, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import euro_shadow_scan as ES
import picks
src = open('euro_totals_test.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
src = src[:src.index("CMP = ('ChampionsLeague',)")]
g = {'__name__': 'ue'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
R, OH, OA, MIDS, SEA, GH, GA, snap_ou, settle, mtot = (g[k] for k in ('R', 'OH', 'OA', 'MIDS', 'SEA', 'GH', 'GA', 'snap_ou', 'settle', 'mtot'))
R = R.assign(new=R.sea.isin(['2425', '2526']), sup=[abs(OH[i] - OA[i]) for i in R.i])
def c(x):
    if len(x) == 0: return '—'
    m = x.groupby('bk').pnl.agg(['mean', 'size']); ps = x.groupby('sea').pnl.mean()
    return f'{m["size"].mean():4.0f} picks {100 * m["mean"].mean():+6.1f}% (' + ' '.join(f'{s} {100 * v:+.0f}' for s, v in ps.items()) + ')'
def ols(x, y):
    X = np.c_[np.ones(len(x)), x]; b, *_ = np.linalg.lstsq(X, y, rcond=None); e = y - X @ b
    se = math.sqrt(np.linalg.inv(X.T @ X)[1, 1] * (e @ e) / (len(y) - 2)); return b[1], se
K = R[(R.h == 0) & (R.side == 'under') & (R.bk == 'Crown')].drop_duplicates('i')
print('1. ΒΑΘΜΟΝΟΜΗΣΗ (κλεισιμο Crown, ενα ανα ματς)')
for lab, m in (('ΝΕΑ μορφη', K.new), ('παλια μορφη', ~K.new)):
    x = K[m]
    b1, s1 = ols(x.model.values, x.tot.values); b2, s2 = ols(x.mt.values, x.tot.values); b3, s3 = ols((x.model - x.mt).values, (x.tot - x.mt).values)
    print(f'   {lab:12s} n{len(x):4d} · γκολ {x.tot.mean():.2f} · μοντελο {x.model.mean():.2f} · αγορα {x.mt.mean():.2f} · κλιση γκολ~μοντελο {b1:.2f}±{s1:.2f} · γκολ~αγορα {b2:.2f}±{s2:.2f} · '
          f'πληροφορια (γκολ−αγορα)~(μοντ−αγορα) {b3:+.2f}±{s3:.2f}')
x = K[K.new]
print('   ΝΕΑ μορφη ανα επιπεδο μοντελου: ' + ' · '.join(f'{lab}: n{len(y)} μοντ {y.model.mean():.2f} πραγμ {y.tot.mean():.2f} αγορα {y.mt.mean():.2f}' for lab, y in
      (('<2.7', x[x.model < 2.7]), ('2.7-3.1', x[(x.model >= 2.7) & (x.model < 3.1)]), ('3.1-3.5', x[(x.model >= 3.1) & (x.model < 3.5)]), ('≥3.5', x[x.model >= 3.5]))))
print('   ΝΕΑ μορφη ανα (μοντελο − αγορα): ' + ' · '.join(f'{lab}: n{len(y)} πραγμ−αγορα {(y.tot - y.mt).mean():+.2f}' for lab, y in
      (('μοντ ΚΑΤΩ ≥0.3 (under)', x[x.model - x.mt <= -0.3]), ('−0.3..−0.1', x[(x.model - x.mt > -0.3) & (x.model - x.mt <= -0.1)]), ('±0.1', x[(x.model - x.mt).abs() < 0.1]),
       ('+0.1..+0.3', x[(x.model - x.mt >= 0.1) & (x.model - x.mt < 0.3)]), ('μοντ ΠΑΝΩ ≥0.3 (over)', x[x.model - x.mt >= 0.3]))))
# ---- 2. πιθανοτητα under ----
print('\n2. P(UNDER) ΣΤΗΝ ΚΥΡΙΑ ΓΡΑΜΜΗ (κλεισιμο Crown, χωρις push) — μοντελο vs συχνοτητα vs αγορα')
rows = []
for r in K.itertuples():
    td = ES.tot_dist(OH[r.i], OA[r.i]); po, pu = ES.p_over(td, r.L)
    s = snap_ou(MIDS[r.i], 'Crown', 0); L, o, un = s; q = (1 / un) / (1 / o + 1 / un)
    if abs(r.tot - L) < 1e-9: continue
    y = 1.0 if r.tot < L else (0.0 if r.tot > L else 0.5)
    if (L * 4) % 2 != 0: continue                                  # μονο καθαρες γραμμες (x.5 / ακεραιες) για καθαρη συγκριση
    rows.append(dict(new=r.new, pm=pu / max(po + pu, 1e-9), pk=q, y=y))
P = pd.DataFrame(rows)
for lab, m in (('ΝΕΑ', P.new), ('παλια', ~P.new)):
    x = P[m]
    print(f'   {lab:6s} n{len(x)} · μεση P(under) μοντελο {x.pm.mean():.3f} · αγορα {x.pk.mean():.3f} · πραγματικη συχνοτητα {x.y.mean():.3f} · Brier μοντελο {((x.pm - x.y) ** 2).mean():.4f} vs αγορα {((x.pk - x.y) ** 2).mean():.4f}')
x = P[P.new]
print('   ΝΕΑ ανα επιπεδο P(under) μοντελου: ' + ' · '.join(f'{lo:.2f}-{hi:.2f}: n{len(y)} μοντ {y.pm.mean():.2f} αγορα {y.pk.mean():.2f} πραγμ {y.y.mean():.2f}'
      for lo, hi in ((0, .40), (.40, .48), (.48, .55), (.55, 1)) for y in [x[(x.pm >= lo) & (x.pm < hi)]] if len(y)))
# ---- 3. που χανουν τα under ----
print('\n3. UNDER @4% ΣΤΟ ΚΛΕΙΣΙΜΟ (ζωνη 1.70-2.10, μεσος Crown/SBOBET) — που χανουν')
Z = R[(R.h == 0) & R.inz & (R.side == 'under') & (R.e >= .04)]
for lab, m in (('ΝΕΑ μορφη', Z.new), ('παλια μορφη', ~Z.new)):
    print(f'   {lab:12s} {c(Z[m])}')
Zn = Z[Z.new]
for title, groups in (('γραμμη', (('≤2.5', Zn.L <= 2.5), ('2.75-3', (Zn.L > 2.5) & (Zn.L <= 3)), ('≥3.25', Zn.L > 3))),
                      ('επιπεδο μοντελου', (('<2.7', Zn.model < 2.7), ('2.7-3.1', (Zn.model >= 2.7) & (Zn.model < 3.1)), ('≥3.1', Zn.model >= 3.1))),
                      ('μοντελο κατω απο αγορα', (('0.1-0.3', (Zn.mt - Zn.model).between(0.1, 0.3)), ('0.3-0.5', (Zn.mt - Zn.model).between(0.3, 0.5)), ('>0.5', Zn.mt - Zn.model > 0.5))),
                      ('δυναμη φαβορι (υπεροχη μοντελου)', (('ισορροπημενο <0.5', Zn.sup < .5), ('φαβορι 0.5-1.2', (Zn.sup >= .5) & (Zn.sup < 1.2)), ('μεγαλο φαβορι ≥1.2', Zn.sup >= 1.2))),
                      ('edge', (('4-8%', Zn.e < .08), ('8-12%', (Zn.e >= .08) & (Zn.e < .12)), ('≥12%', Zn.e >= .12)))):
    print(f'   ανα {title}: ' + ' · '.join(f'{lab} {c(Zn[m])}' for lab, m in groups))
# ---- 4. παραλλαγη ισοπαλιων ----
print('\n4. ΕΝΙΣΧΥΣΗ ΙΣΟΠΑΛΙΩΝ ΣΤΑ ΣΥΝΟΛΑ (νεα μορφη): ×1.13 σημερα / ×1.00 / ×0.85')
def tot_dist_b(lh, la, boost):
    F = [math.factorial(i) for i in range(13)]
    ph = [math.exp(-max(lh, .05)) * max(lh, .05) ** i / F[i] for i in range(13)]; pa = [math.exp(-max(la, .05)) * max(la, .05) ** j / F[j] for j in range(13)]
    tot = {}; s = 0.0
    for i in range(13):
        for j in range(13):
            p = ph[i] * pa[j] * (boost if i == j else 1.0); tot[i + j] = tot.get(i + j, 0.0) + p; s += p
    return {t: p / s for t, p in tot.items()}
B0 = R[(R.h == 0) & R.inz & R.new]
for boost in (1.13, 1.00, 0.85):
    out = []; br = []
    for r in B0.itertuples():
        td = tot_dist_b(OH[r.i], OA[r.i], boost); po, pu = ES.p_over(td, r.L)
        pw, pl_ = (po, pu) if r.side == 'over' else (pu, po)
        e = pw * (r.od - 1) * (1 - picks.MARGIN) - pl_
        if e >= .04: out.append(dict(side=r.side, bk=r.bk, sea=r.sea, pnl=r.pnl))
        if r.side == 'under' and r.bk == 'Crown' and (r.L * 4) % 2 == 0 and r.tot != r.L:
            br.append((pu / max(po + pu, 1e-9) - (1.0 if r.tot < r.L else 0.0)) ** 2)
    O = pd.DataFrame(out)
    print(f'   ×{boost:.2f}: Brier P(under) {np.mean(br):.4f} · UNDER {c(O[O.side == "under"])} · OVER {c(O[O.side == "over"])}')
# ---- 5. χρονισμος ----
F = pd.read_pickle('euro_totals_first.pkl')
X = F[(F.side == 'under') & F.sea.isin(['2425', '2526'])]
print('\n5. ΧΡΟΝΙΣΜΟΣ UNDER (νεα μορφη, ροη πρωτης εμφανισης @4%) — κινηση: + = η αγορα ΚΑΤΕΒΑΣΕ τα γκολ μετα (προς το under μας)')
print(f'   ΟΛΑ {c(X)} · κινηση μετα {X.mv_after.mean():+.2f}')
for hi, lo, wl in ((72, 72, '72ω'), (60, 48, '60-48ω'), (36, 24, '36-24ω'), (18, 12, '18-12ω'), (8, 4, '8-4ω'), (2, 0, '2ω-κλεισ')):
    y = X[(X.h <= hi) & (X.h >= lo)]
    if len(y): print(f'      βγηκε {wl:9s} {c(y)} · κοντρα πριν {y.mv_before.mean():+.2f} · κινηση μετα {y.mv_after.mean():+.2f}')
