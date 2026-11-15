"""
southam_diag.py — 5/10/2026 (Στελιος: «τι προβλεπουμε ανα αγορα και τι βγαινει; γιατι χανουμε στα αουτσαιντερ; ταξιδια/αποσταση στο MLS;»).
Μηχανη v2 (νεες κοκκινες), τελικες γραμμες Crown (+SBOBET για ROI), κανονικη περιοδος, αγωνιστικη ≥7.
(Α) ΒΑΘΜΟΝΟΜΗΣΗ ΑΝΑ ΑΓΟΡΑ: για καθε κατηγορια στοιχηματος, «ποσοστο καλυψης» (νικη 1 · μισο-νικη .75 · επιστροφη .5 · μισο-ηττα .25 · ηττα 0):
    τι λεει το ΜΟΝΤΕΛΟ · τι λεει η ΑΓΟΡΑ (χωρις γκανιοτα) · τι ΕΓΙΝΕ. Μοντελο > πραγματικο = υπερτιμαμε.
(Β) ΤΑ ΔΙΚΑ ΜΑΣ αουτσαιντερ (κανονας: +0.5 και πανω, παλια τεταρτα, edge ≥10%, 1.70-2.10): που χανουμε — ανα παραγοντα.
(Γ) ΠΑΡΑΓΟΝΤΕΣ: υπολοιπο ΜΟΝΤΕΛΟΥ (γκολ − μοντελο) vs υπολοιπο ΑΓΟΡΑΣ (γκολ − αγορα) ανα ταξιδι/ζωνες ωρας/υψομετρο/συνθετικο/
    ξεκουραση/κυπελλα/παραθυρα FIFA/φαση σεζον. Αν το μοντελο εχει σταθερο λαθος σε εναν παραγοντα που η αγορα ΔΕΝ εχει → η αγορα τον
    τιμολογει, εμεις οχι → διορθωνεται.
"""
import sys, json, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks, southam_common as C
from southam_geo import GEO
R = pd.read_csv('southam_phase3_rows_v2emps.csv', dtype={'mid': str, 'season': str})
R = R[(R.per != '1-6') & (R.win == 'close')].copy()
_PP = pd.read_csv('southam_preds.csv', dtype={'mid': str}).set_index('mid')     # ονοματα FotMob (ιδια με τη γεωγραφια) αντι Nowgoal
R['kh'] = R.mid.map(_PP.home_name).map(C.key); R['ka'] = R.mid.map(_PP.away_name).map(C.key)
print('ονοματα χωρις γεωγραφια:', sorted(set(R.kh[~R.kh.isin(GEO)]) | set(R.ka[~R.ka.isin(GEO)]))[:10])
def hav(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    return 6371 * 2 * math.asin(math.sqrt(math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2))
g = lambda k, i: GEO[k][i] if k in GEO else np.nan
R['km'] = [hav(GEO[h], GEO[a]) if h in GEO and a in GEO else np.nan for h, a in zip(R.kh, R.ka)]
R['tz'] = [g(h, 2) - g(a, 2) for h, a in zip(R.kh, R.ka)]                  # +: ο φιλοξενουμενος ερχεται απο δυση (χανει ωρες)
R['altgap'] = [g(h, 3) - g(a, 3) for h, a in zip(R.kh, R.ka)]
R['turf_mis'] = [int(g(h, 4) == 1 and g(a, 4) == 0) for h, a in zip(R.kh, R.ka)]
# ξεκουραση: προγραμμα λιγκας (FotMob) + κυπελλα
P = pd.read_csv('southam_preds.csv', dtype={'mid': str}, parse_dates=['ko'])
cups = pd.DataFrame(json.load(open('southam_cups.json', encoding='utf-8')))
cups['d'] = pd.to_datetime(cups.utc, utc=True).dt.tz_localize(None).dt.normalize()
games = {}
for r in P.itertuples():
    for nm in (r.home_name, r.away_name): games.setdefault(C.key(nm), []).append((r.ko.normalize(), 'L'))
for r in cups.itertuples():
    for nm in (r.home, r.away): games.setdefault(C.key(nm), []).append((r.d, r.comp))
for k in games: games[k] = sorted(set(games[k]))
R['d'] = pd.to_datetime(R.ko, unit='s').dt.normalize()
def rest(k, d):
    pr = [x for x in games.get(k, []) if x[0] < d]; nx = [x for x in games.get(k, []) if x[0] > d]
    return ((d - pr[-1][0]).days if pr else np.nan, pr[-1][1] if pr else None, (nx[0][0] - d).days if nx else np.nan, nx[0][1] if nx else None)
RS = [rest(h, d) + rest(a, d) for h, a, d in zip(R.kh, R.ka, R.d)]
R[['rest_h', 'pc_h', 'next_h', 'nc_h', 'rest_a', 'pc_a', 'next_a', 'nc_a']] = pd.DataFrame(RS, index=R.index)
CONT = {'Libertadores', 'Sudamericana', 'ConcacafCC', 'LeaguesCup', 'ClubWorldCup', 'CopaDoBrasil', 'USOpenCup'}
# παραθυρα FIFA: μερες με ≥10 επισημα ματς εθνικων
IM = pd.read_csv('intl_matches.csv', usecols=['date', 'ctype'], parse_dates=['date'])
fd = IM[IM.ctype.isin(['nl', 'qual', 'tourn'])].date.dt.normalize().value_counts(); FIFA = set(fd[fd >= 10].index)
R['fifa'] = [int(any((d + pd.Timedelta(days=k)) in FIFA for k in (-2, -1, 0, 1, 2))) for d in R.d]
# ---- προβλεψεις ----
def parts(x): return [x] if (x * 4) % 2 == 0 else [x - .25, x + .25]
def cov_model(dist, side, ln):
    c = 0.
    for L in parts(ln):
        w, p = picks.p_cover(dist, side, L); c += (w + 0.5 * p) / len(parts(ln))
    return c
def cov_act(gd, side, ln):
    return (picks.settle(gd, side, ln, 2.0) + 1) / 2
rows = []
for r in R.itertuples():
    dist = picks.gd_dist_dom(max(r.lh_base, .05), max(r.la_base, .05))
    for side, ln, o, oo in ((1, r.ah, r.oh, r.oa), (-1, -r.ah, r.oa, r.oh)):
        pm = (1 / o) / (1 / o + 1 / oo)
        pw, pp = picks.p_cover(dist, side, ln); e = pw * (o - 1) * (1 - picks.MARGIN) - (1 - pw - pp)
        rows.append(dict(mid=r.mid, league=r.league, season=r.season, book=r.book, home=side == 1, line=ln, odds=o,
                         c_mod=cov_model(dist, side, ln), c_mkt=pm, c_act=cov_act(r.gd, side, ln), edge=e,
                         pick=(ln >= 0.5 and 1.70 <= o <= 2.10 and e >= 0.10), pnl=picks.settle(r.gd, side, ln, o)))
S = pd.DataFrame(rows).merge(R[['mid', 'book', 'km', 'tz', 'altgap', 'turf_mis', 'rest_h', 'rest_a', 'pc_h', 'pc_a', 'nc_h', 'nc_a', 'next_h', 'next_a', 'fifa', 'md', 'per']],
                             on=['mid', 'book'])
S.to_pickle('southam_diag_sides.pkl')
cr = S[S.book == 'Crown']
def calib(d):
    if len(d) < 30: return f'n{len(d):4d}'
    return (f'n{len(d):4d} · μοντελο {100*d.c_mod.mean():5.1f}% · αγορα {100*d.c_mkt.mean():5.1f}% · ΕΓΙΝΕ {100*d.c_act.mean():5.1f}% '
            f'(±{100*d.c_act.std()/np.sqrt(len(d)):.1f}) → μοντελο−πραγματ. {100*(d.c_mod.mean()-d.c_act.mean()):+5.1f} · αγορα−πραγματ. {100*(d.c_mkt.mean()-d.c_act.mean()):+5.1f}')
print('\n(Α) ΒΑΘΜΟΝΟΜΗΣΗ ΧΑΝΤΙΚΑΠ (Crown κλεισιμο, ΟΛΑ τα ματς αγων ≥7) — «ποσοστο καλυψης»')
for lg in ('Brazil', 'MLS'):
    print(f' [{lg}]')
    x = cr[cr.league == lg]
    for home in (True, False):
        for lo, hi, lab in ((-9, -1.1, '≤−1.25'), (-1.1, -0.4, '−0.5/−1'), (-0.4, 0.4, '−0.25..+0.25'), (0.4, 1.1, '+0.5/+1'), (1.1, 9, '≥+1.25')):
            print(f'   {"ΓΗΠ" if home else "ΦΙΛ"} {lab:13s} ' + calib(x[(x.home == home) & (x.line > lo) & (x.line <= hi)]))
    print(f'   ΜΟΝΟ ΟΣΑ ΜΑΣ ΑΡΕΣΟΥΝ (edge ≥10%):')
    for lo, hi, lab in ((-9, -0.4, 'φαβορι'), (-0.4, 0.4, 'μικρες'), (0.4, 9, 'αουτσαιντερ')):
        y = x[(x.edge >= 0.10) & (x.line > lo) & (x.line <= hi)]
        print(f'     {lab:12s} ' + calib(y) + (f' · ROI {100*y.pnl.mean():+.1f}%' if len(y) >= 30 else ''))
# ---- συνολα ----
print('\n(Α2) ΒΑΘΜΟΝΟΜΗΣΗ ΣΥΝΟΛΩΝ (Crown κλεισιμο): P(over) μοντελο / αγορα / εγινε')
Rt = R[R.book == 'Crown'].dropna(subset=['ou'])
for lg in ('Brazil', 'MLS'):
    x = Rt[Rt.league == lg]
    for lo, hi in ((0, 2.3), (2.3, 2.6), (2.6, 2.9), (2.9, 3.1), (3.1, 9)):
        y = x[(x.ou > lo) & (x.ou <= hi)]
        if len(y) < 30: continue
        cm = []; ca = []; ck = []
        for r in y.itertuples():
            Pm = picks.score_matrix_dom(max(r.lh_base, .05), max(r.la_base, .05)); tg = {}
            for a in range(13):
                for b in range(13): tg[a + b] = tg.get(a + b, 0) + Pm[a, b]
            c = 0.
            for L in parts(r.ou):
                c += (sum(p for k, p in tg.items() if k - L > .01) + 0.5 * sum(p for k, p in tg.items() if abs(k - L) < .01)) / len(parts(r.ou))
            cm.append(c); ck.append((1 / r.ov) / (1 / r.ov + 1 / r.un))
            a_ = 0.
            for L in parts(r.ou): a_ += (1 if r.tg - L > .01 else (0.5 if abs(r.tg - L) < .01 else 0)) / len(parts(r.ou))
            ca.append(a_)
        print(f'  {lg:6s} γραμμη {lo}-{hi if hi < 9 else "∞"}: n{len(y):4d} · μοντελο {100*np.mean(cm):5.1f}% · αγορα {100*np.mean(ck):5.1f}% · ΕΓΙΝΕ {100*np.mean(ca):5.1f}%')
# ---- (Β) τα δικα μας αουτσαιντερ ----
print('\n(Β) ΤΑ ΔΙΚΑ ΜΑΣ ΑΟΥΤΣΑΙΝΤΕΡ (κανονας CORE7) — ROI (μεσος βιβλιων) & μοντελο/εγινε καλυψη, ανα παραγοντα')
pk = S[S.pick]
def bst(d):
    if len(d) < 16: return f'n{len(d)//2:3d}'
    return f'n{len(d)//2:3d} ROI {100*d.pnl.mean():+6.1f}% · μοντ {100*d.c_mod.mean():.0f}% / αγορ {100*d.c_mkt.mean():.0f}% / εγινε {100*d.c_act.mean():.0f}%'
for lg in ('Brazil', 'MLS'):
    x = pk[pk.league == lg]
    print(f' [{lg}] ΟΛΑ {bst(x)}')
    print(f'   γηπεδουχος dog {bst(x[x.home])} | φιλοξ. dog {bst(x[~x.home])}')
    print(f'   φιλοξ. dog ανα ταξιδι: ' + ' | '.join(f'{lo}-{hi}km {bst(x[~x.home & (x.km >= lo) & (x.km < hi)])}' for lo, hi in ((0, 1000), (1000, 2500), (2500, 9999))))
    if lg == 'MLS':
        print(f'   φιλοξ. dog ζωνες ωρας: ' + ' | '.join(f'{z}ω {bst(x[~x.home & (x.tz.abs() == z)])}' for z in (0, 1, 2, 3)))
        print(f'   φιλοξ. dog σε υψομετρο (Κολοραντο/RSL): {bst(x[~x.home & (x.altgap > 1000)])} | σε συνθετικο {bst(x[~x.home & (x.turf_mis == 1)])}')
    print(f'   παραθυρο FIFA {bst(x[x.fifa == 1])} | εκτος {bst(x[x.fifa == 0])}')
    rd = np.where(x.home, x.rest_h - x.rest_a, x.rest_a - x.rest_h)
    print(f'   ξεκουραση dog − αντιπαλου: ' + ' | '.join(f'{lab} {bst(x[(rd >= lo) & (rd < hi)])}' for lo, hi, lab in ((-99, -2, '≤−3'), (-2, 2, '±1'), (2, 99, '≥+2'))))
    print(f'   παραθυρο: 7-14 {bst(x[x.per == "7-14"])} | 15+ {bst(x[x.per == "15+"])}')
    print(f'   βαθος: +0.5/+0.75 {bst(x[x.line <= 0.75])} | +1 και πανω {bst(x[x.line >= 1])}')
# ---- (Γ) παραγοντες: υπολοιπο μοντελου vs αγορας ----
print('\n(Γ) ΠΑΡΑΓΟΝΤΕΣ — μεσο υπολοιπο (γκολ γηπεδουχου − προβλεψη) για ΜΟΝΤΕΛΟ και ΑΓΟΡΑ · θετικο = ο γηπεδουχος τα πηγε καλυτερα απο την προβλεψη')
F = R[R.book == 'Crown'].copy()
F['r_mod'] = F.gd - F.sup; F['r_mkt'] = F.gd - F.msup; F['rx_mod'] = (F.h_xg_act - F.a_xg_act) - F.sup
F['restd'] = F.rest_h.clip(upper=10) - F.rest_a.clip(upper=10)
def rr(d, lab):
    if len(d) < 30: return f'   {lab:34s} n{len(d):4d}'
    se = d.r_mod.std() / np.sqrt(len(d)); ps = d.groupby('season').r_mod.mean()
    return (f'   {lab:34s} n{len(d):4d} · ΜΟΝΤΕΛΟ {d.r_mod.mean():+.3f} (t {d.r_mod.mean()/se:+.1f}, {int((ps > 0).sum())}/{len(ps)} σεζον) · '
            f'ΑΓΟΡΑ {d.r_mkt.mean():+.3f} (t {d.r_mkt.mean()/(d.r_mkt.std()/np.sqrt(len(d))):+.1f}) · xG μοντελου {d.rx_mod.mean():+.3f}')
for lg in ('Brazil', 'MLS'):
    x = F[F.league == lg]
    print(f' [{lg}] ΟΛΑ'); print(rr(x, 'ολα τα ματς'))
    print('  ΤΑΞΙΔΙ φιλοξενουμενου:')
    for lo, hi in ((0, 500), (500, 1500), (1500, 2500), (2500, 9999)): print(rr(x[(x.km >= lo) & (x.km < hi)], f'{lo}-{hi} km'))
    if lg == 'MLS':
        print('  ΖΩΝΕΣ ΩΡΑΣ (φιλοξ. ερχεται απο δυση + / ανατολη −):')
        for z in (-3, -2, -1, 0, 1, 2, 3): print(rr(x[x.tz == z], f'διαφορα {z:+d}ω'))
    print('  ΥΨΟΜΕΤΡΟ (γηπεδο − εδρα φιλοξ.):')
    for lo, hi in ((-9999, -500), (-500, 500), (500, 9999)): print(rr(x[(x.altgap >= lo) & (x.altgap < hi)], f'{lo}..{hi} m'))
    print('  ΣΥΝΘΕΤΙΚΟ (γηπ. συνθετικο, φιλοξ. φυσικο):'); print(rr(x[x.turf_mis == 1], 'ναι')); print(rr(x[x.turf_mis == 0], 'οχι'))
    print('  ΞΕΚΟΥΡΑΣΗ γηπ − φιλοξ (μερες):')
    for lo, hi in ((-99, -3), (-3, -1), (-1, 2), (2, 4), (4, 99)): print(rr(x[(x.restd >= lo) & (x.restd < hi)], f'{lo}..{hi}'))
    print('  ΚΥΠΕΛΛΑ/ΗΠΕΙΡΩΤΙΚΑ:')
    print(rr(x[x.pc_a.isin(CONT) & (x.rest_a <= 4)], 'φιλοξ. επαιξε κυπελλο ≤4 μερες πριν'))
    print(rr(x[x.pc_h.isin(CONT) & (x.rest_h <= 4)], 'γηπ. επαιξε κυπελλο ≤4 μερες πριν'))
    print(rr(x[x.nc_h.isin(CONT) & (x.next_h <= 4)], 'γηπ. εχει κυπελλο σε ≤4 μερες'))
    print(rr(x[x.nc_a.isin(CONT) & (x.next_a <= 4)], 'φιλοξ. εχει κυπελλο σε ≤4 μερες'))
    print('  ΠΑΡΑΘΥΡΟ FIFA (±2 μερες):'); print(rr(x[x.fifa == 1], 'ναι')); print(rr(x[x.fifa == 0], 'οχι'))
    print('  ΦΑΣΗ ΣΕΖΟΝ:')
    for lo, hi in ((7, 15), (15, 25), (25, 99)): print(rr(x[(x.md >= lo) & (x.md < hi)], f'αγωνιστικη {lo}-{hi - 1}'))
    # πολλαπλη παλινδρομηση υπολοιπου μοντελου & αγορας
    X = pd.DataFrame(dict(km=np.log1p(x.km.fillna(x.km.median()) / 1000), tz=x.tz.fillna(0), alt=(x.altgap.fillna(0) > 1000).astype(float),
                          turf=x.turf_mis.astype(float), rest=x.restd.fillna(0).clip(-5, 5), fifa=x.fifa.astype(float)))
    X = X.loc[:, X.std() > 1e-9]
    A = np.c_[np.ones(len(X)), X.values]
    print('  ΠΟΛΛΑΠΛΗ ΠΑΛΙΝΔΡΟΜΗΣΗ (συντελεστης, t) — ΜΟΝΤΕΛΟ | ΑΓΟΡΑ:')
    for tgt in ('r_mod', 'r_mkt'):
        y = x[tgt].values; b, *_ = np.linalg.lstsq(A, y, rcond=None); e = y - A @ b
        se = np.sqrt(np.diag(np.linalg.pinv(A.T @ A)) * (e @ e) / (len(y) - A.shape[1]))
        print(f'    {"ΜΟΝΤΕΛΟ" if tgt == "r_mod" else "ΑΓΟΡΑ  "}: ' + ' · '.join(f'{c} {b[i+1]:+.3f} (t {b[i+1]/se[i+1]:+.1f})' for i, c in enumerate(X.columns)) + f' · σταθερα {b[0]:+.3f} (t {b[0]/se[0]:+.1f})')
