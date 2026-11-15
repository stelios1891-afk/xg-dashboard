# -*- coding: utf-8 -*-
"""t85_luck_split.py — ΣΥΝΟΛΑ NBA: «ΤΥΧΗ» ΧΩΡΙΣΤΑ ΓΙΑ ΕΠΙΘΕΣΗ ΚΑΙ ΑΜΥΝΑ (25/10/2026, Στελιος «τρεξτο»).
Προελεγχος (pbpstats 150 ομαδα-σεζον, πρωτα 20 ματς → υπολοιπα): 3P% επιθεσης επαναλαμβανεται r .41, FT% .53 · 3P% ΑΝΤΙΠΑΛΩΝ .08, FT% αντιπ. .14
(σχεδον καθαρη τυχη). Το live κραταει 50% της πραγματικης ευστοχιας 3P/FT και στα δυο (luck_eff(0.5) → ιδιοι ποντοι για O και D).
ΑΛΛΑΓΗ: βαθμολογια ΕΠΙΘΕΣΗΣ απο ποντους με w_επ της ευστοχιας 3P/FT · βαθμολογια ΑΜΥΝΑΣ απο ποντους με w_αμ (ξεχωριστο fit ανα μερα,
  ιδια μηχανη/βαρη με το live CFG_T = (0.7, 8, 60, ·, 5, 0, 0, 0), ξεχωριστη αφετηρια O/D απο το αντιστοιχο fit).
  w_επ ∈ {.5, .75, 1} · w_αμ ∈ {0, .25, .5}. Συνολο = live (_t35: μηχανη + Φ3 + απουσιες) + Δ(μηχανη νεα − μηχανη ιδια με live).
ΕΠΙΛΟΓΗ (w_επ, w_αμ): LOSO με RMSE συνολου στις αλλες 4 σεζον.
ΚΡΙΤΗΡΙΑ (εγκριθηκαν πριν): RMSE συνολου καλυτερο απο το live σε ≥4/5 σεζον ΚΑΙ picks συνολων ≥8% ανοιγμα Crown: ROI και CLV οχι χειροτερα
  ΚΑΙ Οκτ-Δεκ ROI οχι χειροτερο. Πληροφορια: αποσταση απο την αγορα, χαντικαπ (μηχανη μονο), παραδειγματα Charlotte 2025-26.
Εξοδος: nba_tests/t85_luck_split_out.txt"""
import os, sys, math, itertools
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
os.chdir(ROOT); sys.path.insert(0, ROOT)
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import numpy as np
from multiprocessing import Pool
import nba_full_clean_test as F
CFG = (0.7, 8, 60, 0.5, 5.0, 0.0, 0.0, 0.0)
COMBOS = list(itertools.product((0.5, 0.75, 1.0), (0.0, 0.25, 0.5)))

def run_split(args):
    w_off, w_def = args
    if 'C' not in F._W: F._init()
    C = F._W['C']; G = C.G
    carry, lam, HL, _, muw, beta, kx, kp = CFG; h = 2.0
    for w in (w_off, w_def):
        if w not in C.EHA: C.EHA[w] = C.luck_eff(w)
    EHo, EAo = C.EHA[w_off]; EHd, EAd = C.EHA[w_def]
    mg = np.full(len(G), np.nan); tt = np.full(len(G), np.nan); prO, prD, prP = {}, {}, {}
    mu0o = float((EHo.mean() + EAo.mean()) / 2); mu0d = float((EHd.mean() + EAd.mean()) / 2); pm0 = float(G.pace.mean())
    for s in C.SEAS:
        sidx = np.where(G.season.values == s)[0]
        teams = sorted(set(G.home.values[sidx]) | set(G.away.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        o0 = carry * np.array([prO.get(t, (0, 0))[0] for t in teams]); d0o = carry * np.array([prO.get(t, (0, 0))[1] for t in teams])
        o0d = carry * np.array([prD.get(t, (0, 0))[0] for t in teams]); d0 = carry * np.array([prD.get(t, (0, 0))[1] for t in teams])
        p0 = carry * np.array([prP.get(t, 0.0) for t in teams])
        hi = np.array([ix[t] for t in G.home.values[sidx]]); ai = np.array([ix[t] for t in G.away.values[sidx]])
        nt = (~G.neutral.values[sidx]).astype(float); hb = nt * h / 2; dn = C.dnum[sidx]; pc = G.pace.values[sidx]
        eho, eao, ehd, ead = EHo[sidx], EAo[sidx], EHd[sidx], EAd[sidx]
        for d in np.unique(dn):
            past = dn < d; cur = np.where(dn == d)[0]
            if past.any():
                w = 0.5 ** ((d - dn[past]) / HL)
                muA, O, _ = F.fit_mu(hi[past], ai[past], eho[past], eao[past], hb[past], w, n, o0, d0o, lam, mu0o, muw)
                muB, _, Dd = F.fit_mu(hi[past], ai[past], ehd[past], ead[past], hb[past], w, n, o0d, d0, lam, mu0d, muw)
                pm, Pc = C.fit_pace(hi[past], ai[past], pc[past], w, n, p0, lam, pm0)
            else:
                muA, muB, O, Dd, pm, Pc = mu0o, mu0d, o0, d0, pm0, p0
            mu = (muA + muB) / 2
            hh, aa = hi[cur], ai[cur]; e_h = mu + O[hh] + Dd[aa] + hb[cur]; e_a = mu + O[aa] + Dd[hh] - hb[cur]; poss = pm + Pc[hh] + Pc[aa]
            mg[sidx[cur]] = poss * (e_h - e_a) / 100; tt[sidx[cur]] = poss * (e_h + e_a) / 100
        w = 0.5 ** ((dn.max() - dn) / HL)
        muA, O, Do = F.fit_mu(hi, ai, eho, eao, hb, w, n, o0, d0o, lam, mu0o, muw)
        muB, Od, Dd = F.fit_mu(hi, ai, ehd, ead, hb, w, n, o0d, d0, lam, mu0d, muw)
        pm, Pc = C.fit_pace(hi, ai, pc, w, n, p0, lam, pm0)
        prO = {t: (O[i], Do[i]) for t, i in ix.items()}; prD = {t: (Od[i], Dd[i]) for t, i in ix.items()}; prP = {t: Pc[i] for t, i in ix.items()}
        mu0o, mu0d, pm0 = muA, muB, pm
    return (w_off, w_def), mg.astype(np.float32), tt.astype(np.float32)

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    import pandas as pd
    from statistics import NormalDist
    out = []
    def P(s=''): print(s, flush=True); out.append(str(s))
    with Pool(min(5, len(COMBOS)), initializer=F._init) as pool:
        RES = {k: (mg, tt) for k, mg, tt in pool.map(run_split, COMBOS)}
    F._init(); C = F._W['C']; G = C.G
    # ελεγχος: (0.5, 0.5) = ιδια μηχανη με το live
    _, mg_l, tt_l, _ = F.run_all(CFG)
    base_mg, base_tt = RES[(0.5, 0.5)]
    ok = np.isfinite(tt_l) & np.isfinite(base_tt)
    P(f'ελεγχος: μηχανη (0.5, 0.5) vs live run_all · μεγιστη διαφορα συνολου {np.nanmax(np.abs(tt_l[ok] - base_tt[ok])):.3f} π.')
    # ---- αγορα / live συνολο (_t35) ----
    D = pd.read_csv(os.path.join(SC, '_t35_totals.csv'))
    O_ = D[D.tau == 'ανοιγμα'].dropna(subset=['T', 'oo', 'ou', 'fair', 'cfair', 'tot']).copy().reset_index(drop=True)
    GI = {(str(G.date.values[k])[:10], G.home.values[k], G.away.values[k]): k for k in range(len(G))}
    O_['g'] = [GI.get((str(d)[:10], h, a)) for d, h, a in zip(O_.date, O_.home, O_.away)]
    O_ = O_[O_.g.notna()].copy(); O_['g'] = O_.g.astype(int)
    O_ = O_[[abs(G.hs.values[k] + G.as_.values[k] - t) < 0.5 for k, t in zip(O_.g, O_.tot)]].reset_index(drop=True)
    O_['mu'] = O_.tt + O_.lev.fillna(0) - 0.5 * O_.lo.fillna(0) + 1.0 * O_.ld.fillna(0)
    SEAS = sorted(O_.sea.unique()); SIG = 18.0; ND = NormalDist()
    P(f'ματς {len(O_)} (ανοιγμα Crown, 5 σεζον) · αγορα (δικαιη γραμμη ανοιγματος) RMSE {np.sqrt(((O_.tot - O_.fair) ** 2).mean()):.3f}')
    gi = O_.g.values
    MU = {k: O_.mu.values + (RES[k][1][gi] - base_tt[gi]) for k in COMBOS}
    rm = lambda k, m: float(np.sqrt(((O_.tot.values[m] - MU[k][m]) ** 2).mean()))
    def picks(mu, m):
        R = []
        for j in np.where(m)[0]:
            r = O_.iloc[j]; po = 1 - ND.cdf((r['T'] - mu[j]) / SIG); eo = po * r['oo'] - 1; eu = (1 - po) * r['ou'] - 1
            sd, e, od = (1, eo, r['oo']) if eo >= eu else (-1, eu, r['ou'])
            if e < .08: continue
            x = (r['tot'] - r['T']) * sd; u = (od - 1) if x > 0 else (0.0 if x == 0 else -1.0)
            R.append((r['sea'], u, sd * (r['cfair'] - r['fair']), int(r['mon'])))
        return pd.DataFrame(R, columns=['sea', 'u', 'clv', 'mon'])
    def cell(d):
        if not len(d): return '—'
        ps = d.groupby('sea').u.sum()
        return f'{100 * d.u.mean():+5.1f}% ({len(d):4d}, {d.u.sum():+6.1f}μ, θετ {int((ps > 0).sum())}/{d.sea.nunique()}) CLV {d.clv.mean():+.2f}π'
    ALL = np.ones(len(O_), bool); ys = O_.sea.values
    P('\n=== ΟΛΕΣ ΟΙ ΕΚΔΟΧΕΣ (ολες οι σεζον, μονο πληροφορια) · RMSE συνολου ανα σεζον · picks ≥8% ===')
    for k in COMBOS:
        P(f"  επ {k[0]:.2f} / αμ {k[1]:.2f}{'  (LIVE)' if k == (0.5, 0.5) else ''}: RMSE " + ' '.join(f'{s % 100}:{rm(k, ys == s):.3f}' for s in SEAS)
          + f' · ολα {rm(k, ALL):.3f} · picks {cell(picks(MU[k], ALL))}')
    sel = {s: min(COMBOS, key=lambda k: rm(k, ys != s)) for s in SEAS}
    P('\nLOSO επιλογη: ' + ' · '.join(f'{s % 100}: επ {sel[s][0]} / αμ {sel[s][1]}' for s in SEAS))
    MUL = np.zeros(len(O_))
    for s in SEAS: MUL[ys == s] = MU[sel[s]][ys == s]
    MU['LOSO'] = MUL; MU['LIVE'] = MU[(0.5, 0.5)]
    better = [rm('LOSO', ys == s) < rm('LIVE', ys == s) - 1e-6 for s in SEAS]
    P(f"RMSE συνολου: live {rm('LIVE', ALL):.3f} → LOSO {rm('LOSO', ALL):.3f} · ανα σεζον " + ' '.join(f"{s % 100}:{rm('LOSO', ys == s) - rm('LIVE', ys == s):+.3f}" for s in SEAS) + f' → καλυτερο {sum(better)}/5')
    od = np.isin(O_.mon.values, (10, 11, 12))
    pa, pb = picks(MU['LIVE'], ALL), picks(MU['LOSO'], ALL); pao, pbo = picks(MU['LIVE'], od), picks(MU['LOSO'], od)
    P(f'\n=== PICKS συνολων ≥8% (ανοιγμα Crown) ===\n  ΟΛΗ ΣΕΖΟΝ  live {cell(pa)}\n             LOSO {cell(pb)}\n  ΟΚΤ-ΔΕΚ    live {cell(pao)}\n             LOSO {cell(pbo)}')
    c1 = sum(better) >= 4; c2 = pb.u.mean() >= pa.u.mean() and pb.clv.mean() >= pa.clv.mean(); c3 = pbo.u.mean() >= pao.u.mean()
    P(f"\nΚΡΙΤΗΡΙΑ: RMSE {sum(better)}/5 (≥4) {'✓' if c1 else '✗'} · ROI & CLV ολης {'✓' if c2 else '✗'} · Οκτ-Δεκ ROI {'✓' if c3 else '✗'} → {'ΠΕΡΝΑΕΙ' if c1 and c2 and c3 else 'ΔΕΝ ΠΕΡΝΑΕΙ'}")
    # ---- πληροφορια: χαντικαπ (μηχανη μονο, ιδια επιλογη) ----
    act_m = G.hs.values[gi] - G.as_.values[gi]
    P('\nΠληροφορια — χαντικαπ (μονο μηχανη, RMSE διαφορας): ' + ' · '.join(
        f"επ {k[0]}/αμ {k[1]} {np.sqrt(np.nanmean((act_m - RES[k][0][gi]) ** 2)):.3f}" for k in ((0.5, 0.5), (1.0, 0.0), (0.75, 0.25))))
    # ---- παραδειγματα Charlotte 2025-26 ----
    P('\n=== ΠΑΡΑΔΕΙΓΜΑΤΑ: Charlotte 2025-26, Δεκεμβριος (live vs LOSO) ===')
    ex = O_[(O_.sea == 2026) & ((O_.home == 'CHO') | (O_.away == 'CHO')) & (O_.mon == 12)].head(4)
    for j, r in ex.iterrows():
        P(f"  {r['date']} {r['away']}@{r['home']} · γραμμη {r['T']} · live {MU['LIVE'][j]:.1f} · νεο {MU['LOSO'][j]:.1f} · πραγματικο {r['tot']:.0f}")
    open(os.path.join(SC, 't85_luck_split_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
