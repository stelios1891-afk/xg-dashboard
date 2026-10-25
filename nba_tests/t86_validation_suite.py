# -*- coding: utf-8 -*-
"""t86_validation_suite.py — ΟΛΟΙ ΟΙ ΤΡΟΠΟΙ ΕΛΕΓΧΟΥ πανω στο ιδιο ερωτημα (25/10/2026, Στελιος «οκ τρεξτα ολα»).
ΕΡΩΤΗΜΑ (t85): λιγοτερη «τυχη» στην ΑΜΥΝΑ (3P%/FT% αντιπαλων) βελτιωνει τα συνολα NBA;
ΥΠΟΨΗΦΙΟΙ: Χ1 = επιθεση .5 / αμυνα .25 (το καλυτερο κελι του t85 — post-hoc) · Χ2 = επιθεση .5 / αμυνα 0 (απο τη θεωρια: 3P% αντιπαλων
  επαναλαμβανεται r .08 → ολο τυχη). Βαση = LIVE (.5 / .5).
ΤΡΟΠΟΙ:
 1 LOSO (απο t85)            2 WALK-FORWARD (επιλογη μονο απο προηγουμενες σεζον, με RMSE και με μοναδες)
 3 ΣΤΑΘΕΡΟΤΗΤΑ (σε ποσες σεζον καλυτερο, RMSE και μοναδες)
 4 ΖΕΥΓΑΡΩΤΗ ματς-ματς (διαφορα τετραγωνικου σφαλματος, t με ομαδοποιηση ανα ημερα)
 5 BOOTSTRAP μοναδων (ξαναδειγματοληψια ΕΒΔΟΜΑΔΩΝ, 5.000 φορες, P(Χ > live))
 6 ΚΙΝΗΣΗ ΑΓΟΡΑΣ: (δικαιη κλεισιματος − δικαιη ανοιγματος) πανω στο (μοντελο − δικαιη ανοιγματος) → κλιση & συσχετιση ανα σεζον
 7 PLACEBO: η διορθωση Χ − live ΑΝΑΚΑΤΕΜΕΝΗ μεταξυ ματς της ιδιας σεζον (1.000 φορες) → ποσο συχνα βγαζει ≥ τις μοναδες του Χ
 (8 = Ευρωλιγκα: el_luck_split_check.py · 9 = σκια φετος)
Εξοδος: nba_tests/t86_validation_suite_out.txt · cache nba_tests/_t86_cache.npz"""
import os, sys
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
os.chdir(ROOT); sys.path.insert(0, ROOT); sys.path.insert(0, SC)
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import numpy as np
from multiprocessing import Pool
import t85_luck_split as T
CACHE = os.path.join(SC, '_t86_cache.npz')
if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    import pandas as pd
    from statistics import NormalDist
    out = []
    def P(s=''): print(s, flush=True); out.append(str(s))
    K = T.COMBOS
    if os.path.exists(CACHE):
        z = np.load(CACHE); RES = {k: (z[f'm{i}'], z[f't{i}']) for i, k in enumerate(K)}
    else:
        with Pool(5, initializer=T.F._init) as pool: RES = {k: (mg, tt) for k, mg, tt in pool.map(T.run_split, K)}
        np.savez(CACHE, **{f'm{i}': RES[k][0] for i, k in enumerate(K)}, **{f't{i}': RES[k][1] for i, k in enumerate(K)})
    T.F._init(); G = T.F._W['C'].G
    D = pd.read_csv(os.path.join(SC, '_t35_totals.csv'))
    O = D[D.tau == 'ανοιγμα'].dropna(subset=['T', 'oo', 'ou', 'fair', 'cfair', 'tot']).copy().reset_index(drop=True)
    GI = {(str(G.date.values[k])[:10], G.home.values[k], G.away.values[k]): k for k in range(len(G))}
    O['g'] = [GI.get((str(d)[:10], h, a)) for d, h, a in zip(O.date, O.home, O.away)]; O = O[O.g.notna()].copy(); O['g'] = O.g.astype(int)
    O = O[[abs(G.hs.values[k] + G.as_.values[k] - t) < 0.5 for k, t in zip(O.g, O.tot)]].reset_index(drop=True)
    O['mu'] = O.tt + O.lev.fillna(0) - 0.5 * O.lo.fillna(0) + 1.0 * O.ld.fillna(0)
    gi = O.g.values; ys = O.sea.values; SE = sorted(set(ys)); ND = NormalDist(); base = RES[(0.5, 0.5)][1][gi]
    TOT, TL, OO, OU, FA, CF = (O[c].values.astype(float) for c in ('tot', 'T', 'oo', 'ou', 'fair', 'cfair'))
    day = pd.to_datetime(O.date).values.astype('datetime64[D]'); wk = (day - day.min()).astype(int) // 7
    MU = {k: O.mu.values + (RES[k][1][gi] - base) for k in K}
    LIVE, X1, X2 = (0.5, 0.5), (0.5, 0.25), (0.5, 0.0)
    def pick_u(mu):
        """μοναδα ανα ματς (0 αν οχι pick), πλευρα, για edge ≥8% στο ανοιγμα"""
        po = np.array([1 - ND.cdf((t - m) / 18) for t, m in zip(TL, mu)]); eo = po * OO - 1; eu = (1 - po) * OU - 1
        sd = np.where(eo >= eu, 1, -1); e = np.maximum(eo, eu); od = np.where(sd > 0, OO, OU)
        x = (TOT - TL) * sd; u = np.where(x > 0, od - 1, np.where(x == 0, 0.0, -1.0))
        return np.where(e >= .08, u, 0.0), np.where(e >= .08, sd, 0)
    U = {k: pick_u(MU[k]) for k in K}
    rm = lambda k, m: float(np.sqrt(((TOT[m] - MU[k][m]) ** 2).mean()))
    uS = lambda k, m: float(U[k][0][m].sum())
    nm = lambda k: f'επ {k[0]}/αμ {k[1]}'
    # ---- 2 WALK-FORWARD ----
    P('=== 2. WALK-FORWARD (επιλογη μονο απο τις ΠΡΟΗΓΟΥΜΕΝΕΣ σεζον) ===')
    for crit, f in (('με RMSE', lambda k, m: -rm(k, m)), ('με μοναδες', lambda k, m: uS(k, m))):
        tl = [0.0, 0.0]; rr = []
        for s in SE[2:]:
            prev = np.isin(ys, [x for x in SE if x < s]); cur = ys == s
            b = max(K, key=lambda k: f(k, prev)); tl[0] += uS(b, cur); tl[1] += uS(LIVE, cur); rr.append(rm(b, cur) < rm(LIVE, cur))
            P(f'   {crit:10s} {s}: διαλεγει {nm(b):14s} · μοναδες {uS(b, cur):+6.1f} vs live {uS(LIVE, cur):+6.1f} · RMSE {rm(b, cur):.3f} vs {rm(LIVE, cur):.3f}')
        P(f'   {crit:10s} ΣΥΝΟΛΟ 3 σεζον: μοναδες {tl[0]:+.1f} vs live {tl[1]:+.1f} · RMSE καλυτερο {sum(rr)}/3')
    # ---- 3 ΣΤΑΘΕΡΟΤΗΤΑ ----
    P('\n=== 3. ΣΤΑΘΕΡΟΤΗΤΑ: σε ποσες σεζον καλυτερο απο το live ===')
    for k in K:
        if k == LIVE: continue
        a = sum(rm(k, ys == s) < rm(LIVE, ys == s) for s in SE); b = sum(uS(k, ys == s) > uS(LIVE, ys == s) for s in SE)
        P(f'   {nm(k):14s} RMSE {a}/5 · μοναδες {b}/5 · συνολο μοναδων {uS(k, ys == ys) - uS(LIVE, ys == ys):+6.1f}')
    # ---- 4 ΖΕΥΓΑΡΩΤΗ ----
    P('\n=== 4. ΖΕΥΓΑΡΩΤΗ ματς-ματς: (σφαλμα live)² − (σφαλμα Χ)² · + = Χ πιο κοντα · t με ομαδες ανα ημερα ===')
    for k in (X1, X2):
        d = (TOT - MU[LIVE]) ** 2 - (TOT - MU[k]) ** 2
        dd = pd.Series(d).groupby(day).sum().values; t = dd.mean() / (dd.std(ddof=1) / np.sqrt(len(dd)))
        P(f'   {nm(k):14s} μεση διαφορα {d.mean():+.3f} π.² ανα ματς · t {t:+.2f} · ανα σεζον ' + ' '.join(f'{s % 100}:{d[ys == s].mean():+.2f}' for s in SE))
    # ---- 5 BOOTSTRAP ----
    P('\n=== 5. BOOTSTRAP μοναδων (εβδομαδες, 5.000 φορες) ===')
    rng = np.random.default_rng(7); W = np.unique(wk)
    for k in (X1, X2):
        dw = pd.Series(U[k][0] - U[LIVE][0]).groupby(wk).sum().reindex(W, fill_value=0).values
        bs = np.array([dw[rng.integers(0, len(dw), len(dw))].sum() for _ in range(5000)])
        P(f'   {nm(k):14s} διαφορα μοναδων {dw.sum():+.1f} · 90% διαστημα [{np.percentile(bs, 5):+.1f}, {np.percentile(bs, 95):+.1f}] · P(Χ > live) {100 * (bs > 0).mean():.0f}%')
    # ---- 6 ΚΙΝΗΣΗ ΑΓΟΡΑΣ ----
    P('\n=== 6. ΚΙΝΗΣΗ ΑΓΟΡΑΣ: προβλεπει το (μοντελο − ανοιγμα) πού θα παει το κλεισιμο; ===')
    mv = CF - FA
    for k in (LIVE, X1, X2):
        x = MU[k] - FA; b = np.polyfit(x, mv, 1)[0]; r = np.corrcoef(x, mv)[0, 1]
        P(f'   {nm(k):14s} κλιση {b:.3f} (ποσο απο τη διαφωνια μας «ερχεται» η αγορα) · συσχετιση {r:.3f} · ανα σεζον ' + ' '.join(f'{s % 100}:{np.corrcoef(x[ys == s], mv[ys == s])[0, 1]:.3f}' for s in SE))
    r0 = {s: np.corrcoef((MU[LIVE] - FA)[ys == s], mv[ys == s])[0, 1] for s in SE}
    for k in (X1, X2):
        P(f'   {nm(k):14s} συσχετιση καλυτερη απο live σε {sum(np.corrcoef((MU[k] - FA)[ys == s], mv[ys == s])[0, 1] > r0[s] for s in SE)}/5 σεζον')
    # ---- 7 PLACEBO ----
    P('\n=== 7. PLACEBO: η ιδια διορθωση ανακατεμενη μεταξυ ματς (1.000 φορες) ===')
    for k in (X1, X2):
        dlt = MU[k] - MU[LIVE]; real = uS(k, ys == ys) - uS(LIVE, ys == ys); res = []
        for _ in range(1000):
            perm = dlt.copy()
            for s in SE:
                m = np.where(ys == s)[0]; perm[m] = dlt[rng.permutation(m)]
            res.append(pick_u(MU[LIVE] + perm)[0].sum() - uS(LIVE, ys == ys))
        res = np.array(res)
        P(f'   {nm(k):14s} πραγματικο κερδος {real:+.1f}μ · ανακατεμενη: μεσος {res.mean():+.1f}, 95% ως {np.percentile(res, 95):+.1f} · ποσο συχνα ≥ πραγματικο {100 * (res >= real).mean():.1f}%'
          f' · μεγεθος διορθωσης: 90% των ματς ±{np.percentile(np.abs(dlt), 90):.2f} π.')
    open(os.path.join(SC, 't86_validation_suite_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
