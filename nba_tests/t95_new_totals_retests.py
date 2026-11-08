# -*- coding: utf-8 -*-
"""t95_new_totals_retests.py — ΞΑΝΑ-ΤΕΣΤ ΠΑΝΩ ΣΤΗ ΝΕΑ ΜΗΧΑΝΗ ΣΥΝΟΛΩΝ (25/10/2026, Στελιος «το περναμε· ποιο κατωφλι; πως αλλαζει η Μ2δ; δες και τις απουσιες»).
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
    O = X[X.tau == 'ανοιγμα'].reset_index(drop=True); SE = sorted(O.sea.unique())
    # ================= Α ΚΑΤΩΦΛΙ =================
    P('################ Α · ΚΑΤΩΦΛΙ (ανοιγμα Crown) ################')
    TH = (4, 6, 8, 10, 12, 15); PK = {}
    for v in ('old', 'new'):
        P(f'  -- {"ΠΑΛΙΑ" if v == "old" else "ΝΕΑ"} μηχανη --')
        for th in TH:
            p = picks(O, f'mu_{v}', th / 100); PK[(v, th)] = p
            P(f'   ≥{th:2d}%: {cell(p):58s} · Οκτ-Δεκ {cell(p[p.per == "Οκτ-Δεκ"])} · Μαρ-Απρ {100 * p[p.per == "Μαρ-Απρ"].res.mean():+.1f}%')
    sel = {s: max(TH, key=lambda th: PK[('new', th)][PK[('new', th)].sea != s].res.sum()) for s in SE}
    L = pd.concat([PK[('new', sel[s])][PK[('new', sel[s])].sea == s] for s in SE])
    P(f"  ΝΕΑ · LOSO κατωφλι: {' · '.join(f'{s % 100}:{sel[s]}%' for s in SE)} → {cell(L)}")
    wf, wl = [], []
    for s in SE[2:]:
        b = max(TH, key=lambda th: PK[('new', th)][PK[('new', th)].sea < s].res.sum()); d = PK[('new', b)]; wf.append(d[d.sea == s]); wl.append(f'{s % 100}:{b}%')
    P(f"  ΝΕΑ · WALK-FORWARD: {' · '.join(wl)} → {cell(pd.concat(wf))} · (σταθερο 8%: {cell(PK[('new', 8)][PK[('new', 8)].sea >= SE[2]])})")
    # ================= Β Μ2δ =================
    P('\n################ Β · Μ2δ ΠΑΝΩ ΣΤΗ ΝΕΑ ΜΗΧΑΝΗ (αγορα + ridge λ50) ################')
    def feats(D, col):
        return np.c_[D[col] - D.fair, D.lo, D.ld, D.lop - D.lo, D.ldp - D.ld, (D.per == 'Οκτ-Δεκ').astype(float), (D.per == 'Μαρ-Απρ').astype(float),
                     D['T'] - 225, (D.gn <= 10).astype(float), (D.mon == 4).astype(float)]
    def fitp(D, Xf, y, tr, te):
        A = np.c_[np.ones(tr.sum()), Xf[tr]]; b = np.linalg.solve(A.T @ A + 50 * np.eye(A.shape[1]), A.T @ y[tr])
        return D.fair.values[te] + np.c_[np.ones(te.sum()), Xf[te]] @ b, b
    for tau in ('ανοιγμα', 'Τ−2ω', 'Τ−30′'):
        D = X[X.tau == tau].reset_index(drop=True); ys = D.sea.values; y = (D.tot - D.fair).values
        P(f'  === {tau} ===')
        for v in ('old', 'new'):
            Xf = feats(D, f'mu_{v}'); lo = np.zeros(len(D)); wfp = np.full(len(D), np.nan)
            for s in SE: lo[ys == s] = fitp(D, Xf, y, ys != s, ys == s)[0]
            for s in SE[2:]: wfp[ys == s] = fitp(D, Xf, y, ys < s, ys == s)[0]
            D[f'lo_{v}'] = lo; D[f'wf_{v}'] = wfp
            rm = np.sqrt(np.mean((D.tot - lo) ** 2)); rmk = np.sqrt(np.mean((D.tot - D.fair) ** 2))
            w = picks(D[D.sea >= SE[2]], f'wf_{v}', .06)
            P(f"    Μ2δ με {'ΠΑΛΙΑ' if v == 'old' else 'ΝΕΑ'} μηχανη: σφαλμα LOSO {rm:.3f} (αγορα {rmk:.3f}) · walk-forward ≥6% {cell(w)}")
            if tau == 'ανοιγμα':
                for th in (4, 6, 8, 10):
                    p = picks(D, f'lo_{v}', th / 100); P(f'       LOSO ≥{th:2d}%: {cell(p):58s} · Οκτ-Δεκ {100 * p[p.per == "Οκτ-Δεκ"].res.mean():+.1f}% ({len(p[p.per == "Οκτ-Δεκ"])}) · Μαρ-Απρ {100 * p[p.per == "Μαρ-Απρ"].res.mean():+.1f}%')
        if tau == 'ανοιγμα':
            _, b = fitp(D, feats(D, 'mu_new'), y, np.ones(len(D), bool), np.ones(len(D), bool))
            nm = ['σταθερα', 'μ−αγορα', 'LO', 'LD', 'LOp−LO', 'LDp−LD', 'Οκτ-Δεκ', 'Μαρ-Απρ', 'γραμμη−225', 'αγων≤10', 'Απριλης']
            P('    συντελεστες ΝΕΑΣ Μ2δ (ολα): ' + ' · '.join(f'{n} {c:+.3f}' for n, c in zip(nm, b)))
    # ================= Γ ΑΠΟΥΣΙΕΣ =================
    P('\n################ Γ · ΑΠΟΥΣΙΕΣ ΠΑΝΩ ΣΤΗ ΝΕΑ ΜΗΧΑΝΗ (ανοιγμα) ################')
    ys = O.sea.values; base = (O.eng_new + O.lev).values; y = O.tot.values - base
    for lab, cO_, cD_ in (('Out μονο', 'lo', 'ld'), ('με πιθανοτητες', 'lop', 'ldp')):
        A_ = np.c_[O[cO_].values, O[cD_].values]
        per = {s: np.linalg.lstsq(np.c_[np.ones((ys == s).sum()), A_[ys == s]], y[ys == s], rcond=None)[0][1:] for s in SE}
        loso = np.zeros(len(O))
        for s in SE:
            tr = ys != s; b = np.linalg.lstsq(np.c_[np.ones(tr.sum()), A_[tr]], y[tr], rcond=None)[0]; loso[ys == s] = b[1] * A_[ys == s, 0] + b[2] * A_[ys == s, 1]
        live = -0.5 * O.lo.values + 1.0 * O.ld.values
        rmL = {s: np.sqrt(np.mean((y - live)[ys == s] ** 2)) for s in SE}; rmN = {s: np.sqrt(np.mean((y - loso)[ys == s] ** 2)) for s in SE}
        O['mu_abs'] = base + loso; p1 = picks(O, 'mu_new', .08); p2 = picks(O, 'mu_abs', .08)
        P(f'  {lab}: cO ανα σεζον ' + ' '.join(f'{s % 100}:{per[s][0]:+.2f}' for s in SE) + ' · cD ' + ' '.join(f'{s % 100}:{per[s][1]:+.2f}' for s in SE) + ' (live −0.5 / +1.0)')
        P(f'     σφαλμα καλυτερο απο live {sum(rmN[s] < rmL[s] for s in SE)}/5 · picks live {cell(p1)} · νεοι συντελεστες {cell(p2)}')
    open(os.path.join(SC, 't95_new_totals_retests_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
