# -*- coding: utf-8 -*-
"""t96_absence_offense_coef.py — ΑΠΟΥΣΙΕΣ ΣΤΑ ΣΥΝΟΛΑ: ΣΥΝΤΕΛΕΣΤΗΣ ΧΑΜΕΝΗΣ ΕΠΙΘΕΣΗΣ (25/10/2026, Στελιος «τρεξε το τεστ 3»).
t95: πανω στη νεα μηχανη το cO βγαινει ≈ −0.8 ΣΤΑΘΕΡΑ 5/5 σεζον (live −0.5)· το cD ασταθες → μενει +1.0.
ΕΚΔΟΧΕΣ: cO ∈ {−0.5 (live), −0.65, −0.8, −1.0}, cD = +1.0, μονο Out (οπως live)· πληροφορια: ιδιο με πιθανοτητες αναφορας.
ΚΡΙΤΗΡΙΑ (γραφτηκαν πριν): LOSO-επιλογη (σφαλμα) → σφαλμα καλυτερο ≥4/5 ΚΑΙ μοναδες & CLV οχι χειροτερα ΚΑΙ walk-forward οχι χειροτερο ΚΑΙ placebo < 5% · + ζευγαρωτη t, bootstrap, ανα περιοδο.
Εξοδος: nba_tests/t96_absence_offense_coef_out.txt
ΠΑΛΙΑ ΠΕΡΙΓΡΑΦΗ (t95): — ΞΑΝΑ-ΤΕΣΤ ΠΑΝΩ ΣΤΗ ΝΕΑ ΜΗΧΑΝΗ ΣΥΝΟΛΩΝ (25/10/2026, Στελιος «το περναμε· ποιο κατωφλι; πως αλλαζει η Μ2δ; δες και τις απουσιες»).
ΝΕΑ μηχανη = run_all_split((0.7, 6, 45, .5, 5, 0,0,0), αμυνα .25) · ΠΑΛΙΑ = run_all((0.7, 8, 60, .5, 5, 0,0,0)).
μ = μηχανη + Φ3 + απουσιες (C_O·LO + C_D·LD, μονο Out) — ιδιο με _t35 / live. Ανοιγμα Crown (και Τ−2ω / Τ−30′ για τη Μ2δ). 5 σεζον.
Α ΚΑΤΩΦΛΙ edge {4,6,8,10,12,15}% (παλια vs νεα) · LOSO (μοναδες) · WALK-FORWARD · ανα περιοδο.
Β Μ2δ (t39: αγορα + ridge λ50 πανω σε (μ − αγορα, LO, LD, LOp−LO, LDp−LD, Οκτ-Δεκ, Μαρ-Απρ, γραμμη−225, αγων ≤10, Απριλης)) — ξανα-fit με το ΝΕΟ μ.
  Walk-forward ≥6% (2024←22-23 κ.λπ.) και LOSO κατωφλι · παλια Μ2δ vs νεα Μ2δ vs νεα μηχανη μονη.
Γ ΑΠΟΥΣΙΕΣ πανω στη νεα μηχανη: (πραγμ − μηχανη − Φ3) = a + cO·LO + cD·LD (LOSO)· live −0.5 / +1.0 · και με πιθανοτητες (LOp/LDp).
  ΠΕΡΝΑ (για αλλαγη συντελεστων) αν σφαλμα καλυτερο σε ≥4/5 ΚΑΙ μοναδες/CLV οχι χειροτερα.
Εξοδος: nba_tests/t95_new_totals_retests_out.txt"""
import os, sys
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
os.chdir(ROOT); sys.path.insert(0, ROOT); sys.path.insert(0, SC)
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import numpy as np, pandas as pd
from statistics import NormalDist
from multiprocessing import Pool
import nba_full_clean_test as F
OLD, NEW = (0.7, 8, 60, .5, 5.0, 0.0, 0.0, 0.0), (0.7, 6, 45, .5, 5.0, 0.0, 0.0, 0.0)
def job(k):
    F._init()
    return k, (F.run_all(OLD)[2] if k == 'old' else F.run_all_split(NEW, 0.25)[2])
if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    out = []
    def P(s=''): print(s, flush=True); out.append(str(s))
    with Pool(2) as p: TT = dict(p.map(job, ['old', 'new']))
    F._init(); G = F._W['C'].G
    X = pd.read_csv(os.path.join(SC, '_t35_totals.csv')).dropna(subset=['T', 'oo', 'ou', 'fair', 'cfair', 'tot']).reset_index(drop=True)
    GI = {(str(G.date.values[k])[:10], G.home.values[k], G.away.values[k]): k for k in range(len(G))}
    X['g'] = [GI.get((str(d)[:10], h, a)) for d, h, a in zip(X.date, X.home, X.away)]; X = X[X.g.notna()].copy(); X['g'] = X.g.astype(int)
    X = X[[abs(G.hs.values[k] + G.as_.values[k] - t) < 0.5 for k, t in zip(X.g, X.tot)]].reset_index(drop=True)
    X['lev'] = X.lev.fillna(0); X['per'] = X.mon.map({10: 'Οκτ-Δεκ', 11: 'Οκτ-Δεκ', 12: 'Οκτ-Δεκ', 1: 'Ιαν-Φεβ', 2: 'Ιαν-Φεβ', 3: 'Μαρ-Απρ', 4: 'Μαρ-Απρ'})
    X['eng_old'] = X.tt; X['eng_new'] = X.tt + (TT['new'][X.g.values] - TT['old'][X.g.values])
    for v in ('old', 'new'): X[f'mu_{v}'] = X[f'eng_{v}'] + X.lev - 0.5 * X.lo + 1.0 * X.ld
    ND = NormalDist(); SIG = 18.0
    def cover(mu, T):
        if abs(T - round(T)) < 1e-9:
            po = ND.cdf((mu - T - 0.5) / SIG); pu = ND.cdf((T - mu - 0.5) / SIG); return po, 1 - po - pu, pu
        po = ND.cdf((mu - T) / SIG); return po, 0.0, 1 - po
    def picks(D, col, thr):
        R = []
        for r in D.itertuples(index=False):
            po, pp, pu = cover(getattr(r, col), r.T); eo, eu = po * r.oo + pp - 1, pu * r.ou + pp - 1
            sd, e, od = (1, eo, r.oo) if eo >= eu else (-1, eu, r.ou)
            if e < thr: continue
            x = (r.tot - r.T) * sd; R.append((r.sea, r.per, sd, e, (od - 1) if x > 0 else (0.0 if x == 0 else -1.0), sd * (r.cfair - r.fair)))
        return pd.DataFrame(R, columns=['sea', 'per', 'sd', 'e', 'res', 'clv'])
    def cell(d):
        if d is None or not len(d): return '—'
        ps = d.groupby('sea').res.sum()
        return f'{100 * d.res.mean():+5.1f}% ({len(d):4d}, {d.res.sum():+6.1f}μ, θετ {int((ps > 0).sum())}/{d.sea.nunique()}) CLV {d.clv.mean():+.2f}'
    O = X[X.tau == 'ανοιγμα'].reset_index(drop=True); SE = sorted(O.sea.unique()); ys = O.sea.values; Y = O.tot.values
    day = pd.to_datetime(O.date).values.astype('datetime64[D]'); wk = (day - day.min()).astype(int) // 7
    rng = np.random.default_rng(17)
    def pu(mu):
        u = np.zeros(len(O)); c = np.full(len(O), np.nan)
        for j, r in enumerate(O.itertuples(index=False)):
            po, pp, pq = cover(mu[j], r.T); eo, eu = po * r.oo + pp - 1, pq * r.ou + pp - 1
            sd, e, od = (1, eo, r.oo) if eo >= eu else (-1, eu, r.ou)
            if e < .08: continue
            x = (r.tot - r.T) * sd; u[j] = (od - 1) if x > 0 else (0.0 if x == 0 else -1.0); c[j] = sd * (r.cfair - r.fair)
        return u, c
    base = (O.eng_new + O.lev).values
    for lab, lo, ld in (('μονο Out (οπως live)', O.lo.values, O.ld.values), ('με πιθανοτητες αναφορας', O.lop.values, O.ldp.values)):
        P(f'\n################ {lab} · cD = +1.0 · νεα μηχανη · ανοιγμα Crown · edge ≥8% ################')
        CO = (-0.5, -0.65, -0.8, -1.0); MU = {c: base + c * lo + 1.0 * ld for c in CO}; U = {c: pu(MU[c]) for c in CO}
        rm = lambda c, m: float(np.sqrt(np.mean((Y[m] - MU[c][m]) ** 2)))
        for c in CO:
            u, cl = U[c]; ps = {s: u[ys == s].sum() for s in SE}; od_ = O.per.values == 'Οκτ-Δεκ'
            P(f"  cO {c:+.2f}{' (LIVE)' if c == -0.5 else '       '} σφαλμα {rm(c, ys == ys):.3f} (" + ' '.join(f'{s % 100}:{rm(c, ys == s):.3f}' for s in SE)
              + f') · μοναδες {u.sum():+6.1f} (θετ {sum(v > 0 for v in ps.values())}/5, Οκτ-Δεκ {u[od_].sum():+.1f}) · picks {int((u != 0).sum())} · CLV {np.nanmean(cl):+.2f}')
        for c in CO[1:]:
            bet = sum(rm(c, ys == s) < rm(-0.5, ys == s) for s in SE)
            dd = pd.Series((Y - MU[-0.5]) ** 2 - (Y - MU[c]) ** 2).groupby(day).sum().values; t = dd.mean() / (dd.std(ddof=1) / np.sqrt(len(dd)))
            dw = pd.Series(U[c][0] - U[-0.5][0]).groupby(wk).sum().values; bs = np.array([dw[rng.integers(0, len(dw), len(dw))].sum() for _ in range(3000)])
            P(f'  cO {c:+.2f} vs live: σφαλμα καλυτερο {bet}/5 · ζευγαρωτη t {t:+.2f} · Δμοναδες {dw.sum():+.1f} (bootstrap P {100 * (bs > 0).mean():.0f}%)')
        sel = {s: min(CO, key=lambda c: rm(c, ys != s)) for s in SE}
        LM = np.zeros(len(O)); LU = np.zeros(len(O)); LC = np.full(len(O), np.nan)
        for s in SE: m = ys == s; LM[m] = MU[sel[s]][m]; LU[m] = U[sel[s]][0][m]; LC[m] = U[sel[s]][1][m]
        bet = sum(np.sqrt(np.mean((Y - LM)[ys == s] ** 2)) < rm(-0.5, ys == s) for s in SE)
        wf = [0.0, 0.0]; ch = []
        for s in SE[2:]:
            prev = np.isin(ys, [x for x in SE if x < s]); cur = ys == s; b = min(CO, key=lambda c: rm(c, prev))
            wf[0] += U[b][0][cur].sum(); wf[1] += U[-0.5][0][cur].sum(); ch.append(f'{s % 100}:{b:+.2f}')
        dlt = LM - MU[-0.5]; real = LU.sum() - U[-0.5][0].sum(); res = []
        for _ in range(200):
            perm = dlt.copy()
            for s in SE:
                m = np.where(ys == s)[0]; perm[m] = dlt[rng.permutation(m)]
            res.append(pu(MU[-0.5] + perm)[0].sum() - U[-0.5][0].sum())
        pl = 100 * (np.array(res) >= real).mean()
        ok = bet >= 4 and LU.sum() >= U[-0.5][0].sum() and np.nanmean(LC) >= np.nanmean(U[-0.5][1]) and wf[0] >= wf[1] and pl < 5
        P(f"  LOSO: {' · '.join(f'{s % 100}:{sel[s]:+.2f}' for s in SE)} · σφαλμα καλυτερο {bet}/5 · μοναδες {LU.sum():+.1f} vs {U[-0.5][0].sum():+.1f} · CLV {np.nanmean(LC):+.2f} vs {np.nanmean(U[-0.5][1]):+.2f}")
        P(f"  WALK-FORWARD: {' · '.join(ch)} → {wf[0]:+.1f} vs live {wf[1]:+.1f} · PLACEBO ≥ πραγματικο {pl:.1f}% → {'ΠΕΡΝΑΕΙ' if ok else 'ΔΕΝ ΠΕΡΝΑΕΙ'}")
    open(os.path.join(SC, 't96_absence_offense_coef_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
