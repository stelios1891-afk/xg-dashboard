"""uecl_category_metrics.py — 12/10/2026 (Στελιος: «ποσες ομαδες ανα κατηγορια; ιστορικα ποσο κοντα στην πραγματικοτητα ειμαστε σε καθε
κατηγορια, συγκριση με αγορα, σε ολα τα metrics που εχουμε χρησιμοποιησει; υποτιμαμε/υπερτιμαμε κατι συστηματικα στη Β ή Γ για διορθωση;
ποια ειναι η αδυναμια μας στα αουτσαιντερ;»). Conference League 4 σεζον (2223-2526), αγορα = κλεισιμο Crown (αλλιως SBOBET).
  1) φετος: ομαδες ανα πηγη, ματς ανα κατηγορια
  2) METRICS ανα κατηγορια: μεροληψια (γκολ ανα πλευρα / συνολο / διαφορα), μεσο τετρ. λαθος, RPS 1Χ2, Brier over 2.5, b (πληροφορια περα απο αγορα)
  3) Β αναλυτικα: πλευρα ΜΕ FotMob vs πλευρα ΧΩΡΙΣ (γκολ / xG / μοντελο / αγορα) + ΔΟΚΙΜΗ διορθωσης συνολου Β με LOSO
  4) ΑΟΥΤΣΑΙΝΤΕΡ (κατηγορια Α): δηλωμενο edge vs πραγματικο, ανα ζωνη edge, εντος/εκτος, φαση — πιθανοτητα καλυψης μοντελο/αγορα/πραγματικη
"""
import sys
exec(open('ucl_nonfm_teams.py', encoding='utf-8').read().split('# ===== 1 =====')[0])
from math import lgamma
NL = chr(10)
# ================= 1 =================
P = json.load(open('euro_projections.json', encoding='utf-8'))
T = {}; catc = collections.Counter(); unc = 0
for m in P['matches']:
    if m['comp'] != 'ConferenceLeague': continue
    if not m.get('covered'): unc += 1; continue
    T[m['home']] = m['src_h']; T[m['away']] = m['src_a']
    fm = [m['src_h'] == 'FotMob', m['src_a'] == 'FotMob']; catc['Α' if all(fm) else ('Β' if any(fm) else 'Γ')] += 1
src_c = collections.Counter(T.values())
print('1. ΦΕΤΟΣ (Conference League, φαση λιγκας): ομαδες ' + ' · '.join(f'{k} {v}' for k, v in src_c.most_common()) +
      f' (+2 χωρις rating: Inter d\'Escaldes, Lincoln) · ματς Α {catc["Α"]} · Β {catc["Β"]} · Γ {catc["Γ"]} · χωρις rating {unc}')
# ================= 2 =================
X = S[S.comp == 'UECL']
rows = []
for i, x in X.groupby('i'):
    h = x[x.venue == 'εντος'].iloc[0]; a = x[x.venue == 'εκτος'].iloc[0]
    rows.append(dict(i=i, sea=h.sea, ph=h.ph, cat=h['cat'], gh=h.g, ga=a.g, lh=h.lam, la=a.lam, oh=h.lou, oa=a.lou, xh=h.xg, xa=a.xg, kh=h.k, ka=a.k,
                     fm_home=h.src == 'FotMob'))
M = pd.DataFrame(rows); M = M[M.kh.notna() & M.ka.notna()].copy()
M['y'] = M.gh - M.ga; M['tg'] = M.gh + M.ga; M['m'] = M.lh - M.la; M['km'] = M.kh - M.ka; M['Tm'] = M.oh + M.oa; M['kT'] = M.kh + M.ka
def rps(D, y):
    p1 = sum(p for k, p in D.items() if k > 0); px = D.get(0, 0); o = [1.0 if y > 0 else 0, 1.0 if y >= 0 else 0]
    c = [p1, p1 + px]; return ((c[0] - o[0]) ** 2 + (c[1] - o[1]) ** 2) / 2
def pov(lh, la, L=2.5):
    po, pu = ES.p_over(ES.tot_dist(lh, la, DRAW_SCALE), L); return po
for r in M.itertuples():
    M.loc[r.Index, 'rps_m'] = rps(sdist(max(r.lh, .05), max(r.la, .05)), r.y)
    M.loc[r.Index, 'rps_k'] = rps(sdist(max(r.kh, .05), max(r.ka, .05)), r.y)
    M.loc[r.Index, 'br_m'] = (pov(r.oh, r.oa) - (r.tg > 2.5)) ** 2
    M.loc[r.Index, 'br_k'] = (pov(r.kh, r.ka) - (r.tg > 2.5)) ** 2
def ols(y, x0, x1):
    Xm = np.column_stack([np.ones(len(y)), x0, x1]); b, *_ = np.linalg.lstsq(Xm, y, rcond=None)
    e = y - Xm @ b; cov = np.linalg.inv(Xm.T @ Xm) * (e @ e / max(len(y) - 3, 1)); return b[2], b[2] / np.sqrt(cov[2, 2])
print(NL + '2. ΠΟΣΟ ΚΟΝΤΑ ΣΤΗΝ ΠΡΑΓΜΑΤΙΚΟΤΗΤΑ — ανα κατηγορια (μοντελο vs αγορα κλεισιματος). Μικροτερο = καλυτερο, εκτος απο b.')
for lab, mk in (('4 ΣΕΖΟΝ', M.sea.notna()), ('ΝΕΑ ΜΟΡΦΗ (2425-2526)', M.sea.isin(['2425', '2526']))):
    print(f'   --- {lab} ---')
    for c in ('Α', 'Β', 'Γ'):
        x = M[mk & (M.cat == c)]
        if len(x) < 10: continue
        b1, t1 = ols(x.y.values, x.km.values, (x.m - x.km).values); b2, t2 = ols(x.tg.values, x.kT.values, (x.Tm - x.kT).values)
        b3, t3 = ols((x.xh - x.xa).values, x.km.values, (x.m - x.km).values)
        print(f'   {c} n{len(x):3d} ΜΕΡΟΛΗΨΙΑ πραγμ/μοντ/αγορα: γηπ {x.gh.mean():.2f}/{x.lh.mean():.2f}/{x.kh.mean():.2f} · φιλοξ {x.ga.mean():.2f}/{x.la.mean():.2f}/{x.ka.mean():.2f} · '
              f'συνολο {x.tg.mean():.2f}/{x.Tm.mean():.2f}/{x.kT.mean():.2f} · διαφορα {x.y.mean():+.2f}/{x.m.mean():+.2f}/{x.km.mean():+.2f}')
        print(f'        ΑΚΡΙΒΕΙΑ μοντ vs αγορα: RPS 1Χ2 {x.rps_m.mean():.4f} vs {x.rps_k.mean():.4f} · Brier over2.5 {x.br_m.mean():.4f} vs {x.br_k.mean():.4f} · '
              f'τετρ.λαθος διαφορας {((x.y - x.m) ** 2).mean():.3f} vs {((x.y - x.km) ** 2).mean():.3f} · συνολου {((x.tg - x.Tm) ** 2).mean():.3f} vs {((x.tg - x.kT) ** 2).mean():.3f}')
        print(f'        ΠΛΗΡΟΦΟΡΙΑ b (1 = σωστο μοντελο, 0 = σωστη αγορα): διαφορα γκολ {b1:+.2f} (t {t1:+.1f}) · διαφορα xG {b3:+.2f} (t {t3:+.1f}) · συνολο {b2:+.2f} (t {t2:+.1f})')
# ================= 3 =================
print(NL + '3. ΚΑΤΗΓΟΡΙΑ Β ΑΝΑΛΥΤΙΚΑ — πλευρα ΜΕ FotMob / πλευρα ΧΩΡΙΣ (γκολ που βαζει: πραγμ / xG / μοντελο / αγορα)')
B = X[X.cat == 'Β']
for lab, m_ in (('πλευρα ΜΕ FotMob', B.src == 'FotMob'), ('πλευρα ΧΩΡΙΣ FotMob', B.src != 'FotMob')):
    for v in ('ολα', 'εντος', 'εκτος'):
        x = B[m_ & ((B.venue == v) if v != 'ολα' else True)]
        print(f'   {lab:22s} {v:6s} n{len(x):3d} · γκολ {x.g.mean():.2f} · xG {x.xg.mean():.2f} · μοντελο {x.lam.mean():.2f} · αγορα {x.k.mean():.2f} · '
              f'γκολ−μοντ {(x.g - x.lam).mean():+.2f}±{se(x.g - x.lam):.2f} · γκολ−xG {(x.g - x.xg).mean():+.2f}')
y = M[M.cat == 'Β']
print(f'   ΣΥΝΟΛΟ Β ανα σεζον (πραγμ − μοντελο / πραγμ − αγορα): ' + ' · '.join(f'{s}: {(z.tg - z.Tm).mean():+.2f}/{(z.tg - z.kT).mean():+.2f} (n{len(z)})' for s, z in y.groupby('sea')))
# ΔΟΚΙΜΗ: συνολο Β × c (και οι 2 πλευρες), c απο τις αλλες 3 σεζον (LOSO), κριση: log-lik Poisson στη σεζον-τεστ
LG = lambda k: lgamma(k + 1)
def ll(z, c):
    a = np.maximum(z.oh * c, .05); b = np.maximum(z.oa * c, .05)
    return (z.gh * np.log(a) - a + z.ga * np.log(b) - b - z.gh.map(LG) - z.ga.map(LG)).sum()
GRID = np.round(np.arange(0.80, 1.11, 0.01), 2)
print('   ΔΟΚΙΜΗ διορθωσης: γκολ και των 2 πλευρων ×c στα ματς Β (c απο τις αλλες 3 σεζον) → log-lik στη σεζον-τεστ (+ = καλυτερη προβλεψη)')
oks = 0
for s in sorted(y.sea.unique()):
    tr, te = y[y.sea != s], y[y.sea == s]
    c = GRID[np.argmax([ll(tr, g) for g in GRID])]; d = ll(te, c) - ll(te, 1.0); oks += d > 0
    print(f'      τεστ {s}: c = {c:.2f} · Δlog-lik {d:+.2f} (n{len(te)})')
print(f'      c με ολες τις σεζον: {GRID[np.argmax([ll(y, g) for g in GRID])]:.2f} · καλυτερο εκτος δειγματος σε {oks}/4 σεζον')
# ================= 4 =================
print(NL + '4. ΑΟΥΤΣΑΙΝΤΕΡ (κατηγορια Α, γραμμη ≥+0.5, 1.70-2.10, πρωτη τιμη ≤72ω) — τι λεμε εμεις, τι λεει η αγορα, τι εγινε')
HS = (72, 60, 48, 36, 24, 18, 12, 8, 6, 4, 2, 1, 0)
R = []
for i in M[M.cat == 'Α'].i:
    for bk in ('Crown', 'SBOBET'):
        got = False
        for h in HS:
            s = snap_ah(MIDS[i], bk, h)
            if not s or got: continue
            L, oh_, oa_ = s
            for side, ln, o, oo in ((1, L, oh_, oa_), (-1, -L, oa_, oh_)):
                if ln < 0.5 or not (1.70 <= o <= 2.10): continue
                D = sdist(max(LH_N[i], .05), max(LA_N[i], .05)); pw, pp = picks.p_cover(D, side, ln); e = edge(pw, pp, o)
                pq, ppq = cover_q(D, side, ln)
                pk = (1 / o) / (1 / o + 1 / oo)            # αγορα (χωρις γκανιοτα)
                res = picks.settle(GD[i], side, ln, o)
                R.append(dict(i=i, bk=bk, h=h, sea=SEA[i], home=side == 1, ph=V6['phase'][VI[str(MIDS[i])]], e=e, pw=pw / max(1 - pp, 1e-9),
                              pq=pq / max(1 - ppq, 1e-9), pk=pk, win=(res > 0) * 1.0 + (abs(res) < 1e-9) * 0.5 * 0 , pnl=res,
                              cover=1.0 if res > 0.5 * (o - 1) else (0.5 if res > 0 else (0.0 if res < -0.5 else (0.25 if res < 0 else 0.5)))))
                got = True
R = pd.DataFrame(R)
def cc(x):
    if len(x) == 0: return '—'
    m = x.groupby('bk').pnl.mean(); n = x.groupby('bk').size().mean()
    return (f'{n:4.0f} picks {100 * m.mean():+6.1f}% · καλυψη: μοντελο {100 * x.pw.mean():.0f}% (σωστα τεταρτα {100 * x.pq.mean():.0f}%) · αγορα {100 * x.pk.mean():.0f}% · '
            f'ΠΡΑΓΜ {100 * x.cover.mean():.0f}%')
print(f'   ολα τα dogs:        {cc(R)}')
for lo, hi in ((-1, 0), (0, .04), (.04, .10), (.10, .16), (.16, 9)):
    print(f'   edge {lo:+.0%}…{hi if hi < 9 else 1:.0%}: {cc(R[(R.e >= lo) & (R.e < hi)])}')
x10 = R[R.e >= .10]
for lab, m_ in (('≥10% εντος', x10.home), ('≥10% εκτος', ~x10.home), ('≥10% φαση λιγκας', x10.ph == 'league'), ('≥10% νοκ-αουτ', x10.ph == 'KO'),
                ('≥10% νεα μορφη', x10.sea.isin(['2425', '2526'])), ('≥10% παλια μορφη', ~x10.sea.isin(['2425', '2526']))):
    print(f'   {lab:18s} {cc(x10[m_])}')
print('   (ΤΥΦΛΑ, χωρις μοντελο, ολα τα dogs κατηγοριας Α: ' + ' · '.join(f'{l} {cc(R[m_])}' for l, m_ in (('εντος', R.home), ('εκτος', ~R.home))) + ')')
