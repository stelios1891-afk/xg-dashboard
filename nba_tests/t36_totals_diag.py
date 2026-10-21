# -*- coding: utf-8 -*-
"""t36_totals_diag.py — ΣΥΝΟΛΑ NBA · ΔΙΑΓΝΩΣΗ + ΠΡΩΤΕΣ ΜΗΧΑΝΕΣ (21/10/2026). Βαση _t35_totals.csv (αντιγραφο live, απουσιες απο επισημες αναφορες).
LIVE μοντελο: μ = μηχανη + Φ3 live − 0.5·LO + 1.0·LD (μονο Out) · σ 18 · pick edge ≥8% (μονο του μοντελο).
ΔΙΑΓΝΩΣΗ (περιγραφικα): Δ0 ROI ανα στιγμη/περιοδο/over-under/μεγεθος γραμμης/ζωνες edge · Δ1 μεροληψια ανα μηνα (πραγμ − μοντελο / − αγορα ανοιγ. / − κλεισιμο)
  · Δ2 προβλεπει το μοντελο την ΚΙΝΗΣΗ της αγορας; (μ − ανοιγμα) → (κλεισιμο − ανοιγμα) · Δ3 απουσιες: τις εχει η αγορα; (πραγμ − αγορα) πανω στο LO/LD.
ΜΗΧΑΝΕΣ (ΠΡΟ-ΔΗΛΩΜΕΝΑ, LOSO 5 σεζον, εκτιμηση στις 4 → ελεγχος στην 5η):
  Μ1 ΜΙΞΗ με την αγορα: αγορα_τ + w·(μ − αγορα_τ), w ∈ {0, .1, .2, .3, .5, .7, 1} (επιλογη με RMSE)
  Μ2 ΥΠΟΛΟΙΠΟ: (πραγμ − αγορα_τ) = ridge(μ − αγορα_τ, LO, LD, LOp−LO, LDp−LD, Οκτ-Δεκ, Μαρ-Απρ, γραμμη−225, αγων ≤10)
  PICKS καθε μηχανης: edge ≥ κατωφλι ∈ {4, 6, 8, 10}% (LOSO κατωφλι με μοναδες). ΠΕΡΝΑ αν: RMSE καλυτερο απο την ΑΓΟΡΑ στο τ σε ≥3/5 σεζον
  Ή ROI LOSO > 0 σε ≥4/5 σεζον με CLV > 0 — ΚΑΙ στο ανοιγμα ΚΑΙ στο Τ−30′. Εξοδος: t36_totals_diag_out.txt"""
import os, sys, collections
import numpy as np, pandas as pd
from statistics import NormalDist
SC = os.path.dirname(os.path.abspath(__file__)); sys.stdout.reconfigure(encoding='utf-8')
X = pd.read_csv(os.path.join(SC, '_t35_totals.csv'))
X['mu'] = X.tt + X.lev - 0.5 * X.lo + 1.0 * X.ld
X['per'] = X.mon.map({10: 'Οκτ-Δεκ', 11: 'Οκτ-Δεκ', 12: 'Οκτ-Δεκ', 1: 'Ιαν-Φεβ', 2: 'Ιαν-Φεβ', 3: 'Μαρ-Απρ', 4: 'Μαρ-Απρ'})
SIG = 18.0; N_ = NormalDist(); SE = sorted(X.sea.unique())
def cover(mu, T):
    if abs(T - round(T)) < 1e-9:
        po = N_.cdf((mu - T - 0.5) / SIG); pu = N_.cdf((T - mu - 0.5) / SIG); return po, 1 - po - pu, pu
    po = N_.cdf((mu - T) / SIG); return po, 0.0, 1 - po
def picks(D, col='mu', thr=.08):
    R = []
    for r in D.itertuples(index=False):
        m = getattr(r, col); po, pp, pu = cover(m, r.T); eo, eu = po * r.oo + pp - 1, pu * r.ou + pp - 1
        sd, e, od = (1, eo, r.oo) if eo >= eu else (-1, eu, r.ou)
        if e < thr: continue
        x = (r.tot - r.T) * sd; res = (od - 1) if x > 0 else (0.0 if x == 0 else -1.0)
        cw, cp, cu = cover(r.cfair, r.T); evc = (cw if sd == 1 else cu) * od + cp - 1
        R.append(dict(i=r.i, sea=r.sea, per=r.per, mon=r.mon, sd=sd, e=e, T=r.T, res=res, evc=evc, clv=sd * (r.cfair - r.fair)))
    return pd.DataFrame(R)
def cell(d):
    if d is None or not len(d): return '        —'
    ps = d.groupby('sea').res.sum()
    return f'{100 * d.res.mean():+6.1f}% ({len(d):4d}, {d.res.sum():+6.1f}μ, {int((ps > 0).sum())}/{d.sea.nunique()}) CLV {d.clv.mean():+.2f}'
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
P('NBA ΣΥΝΟΛΑ · ΔΙΑΓΝΩΣΗ · 5 σεζον · σ 18 · αντιγραφο live + επισημες αναφορες')
# ---------- Δ0 ----------
P(''); P('=== Δ0 · LIVE picks ≥8% ===')
PK = {tau: picks(X[X.tau == tau]) for tau in ('ανοιγμα', 'Τ−2ω', 'Τ−30′')}
for tau, pk in PK.items():
    P(f'  {tau:8s} ολα {cell(pk)} | over {cell(pk[pk.sd == 1])} | under {cell(pk[pk.sd == -1])}')
    if tau == 'ανοιγμα':
        for per in ('Οκτ-Δεκ', 'Ιαν-Φεβ', 'Μαρ-Απρ'): P(f'     {per:8s} {cell(pk[pk.per == per])} | over {cell(pk[(pk.per == per) & (pk.sd == 1)])} | under {cell(pk[(pk.per == per) & (pk.sd == -1)])}')
        P('     γραμμη: ' + ' · '.join(f'{lo}-{hi}: {100 * pk[(pk['T'] >= lo) & (pk['T'] < hi)].res.mean():+.0f}% ({len(pk[(pk['T'] >= lo) & (pk['T'] < hi)])})' for lo, hi in ((0, 215), (215, 225), (225, 235), (235, 999))))
        P('     ζωνες edge (δηλωμενο / αναμενομενο απο κλεισιμο / πραγματικο): ' + ' · '.join(
            f'{lo}-{hi}%: {100 * x.e.mean():.0f}/{100 * x.evc.mean():+.0f}/{100 * x.res.mean():+.0f}% ({len(x)})' for lo, hi in ((8, 10), (10, 14), (14, 20), (20, 99)) for x in [pk[(pk.e >= lo / 100) & (pk.e < hi / 100)]]))
# ---------- Δ1 ----------
P(''); P('=== Δ1 · ΜΕΡΟΛΗΨΙΑ ανα μηνα (μεσο: πραγματικο − ...) · ανοιγμα ===')
O = X[X.tau == 'ανοιγμα']
for m in (10, 11, 12, 1, 2, 3, 4):
    d = O[O.mon == m]
    P(f'  μηνας {m:2d} n {len(d):4d} · − μοντελο {(d.tot - d.mu).mean():+5.2f} · − αγορα ανοιγ. {(d.tot - d.fair).mean():+5.2f} · − κλεισ. {(d.tot - d.cfair).mean():+5.2f} · '
      f'μοντελο − αγορα {(d.mu - d.fair).mean():+5.2f} · RMSE μοντ {np.sqrt(((d.tot - d.mu) ** 2).mean()):.2f} / αγορα {np.sqrt(((d.tot - d.fair) ** 2).mean()):.2f}')
# ---------- Δ2 ----------
P(''); P('=== Δ2 · ΠΡΟΒΛΕΠΕΙ ΤΟ ΜΟΝΤΕΛΟ ΤΗΝ ΚΙΝΗΣΗ ΤΗΣ ΑΓΟΡΑΣ; (μ − ανοιγμα) → (κλεισιμο − ανοιγμα) ===')
z = O.mu - O.fair; mv = O.cfair - O.fair
P(f'  κλιση {np.polyfit(z, mv, 1)[0]:+.3f} · r {np.corrcoef(z, mv)[0, 1]:+.3f} · οταν |μ − ανοιγμα| ≥ 5: η αγορα κινειται προς το μοντελο {np.mean(np.sign(mv[np.abs(z) >= 5]) == np.sign(z[np.abs(z) >= 5])) * 100:.0f}% των φορων (n {int((np.abs(z) >= 5).sum())})')
P(f'  και μετα το κλεισιμο: (πραγμ − κλεισιμο) πανω στο (μ − κλεισιμο): κλιση {np.polyfit(O.mu - O.cfair, O.tot - O.cfair, 1)[0]:+.3f}')
# ---------- Δ3 ----------
P(''); P('=== Δ3 · ΑΠΟΥΣΙΕΣ: τις εχει η αγορα; (πραγμ − αγορα) = a + bO·LO + bD·LD ===')
for tau in ('ανοιγμα', 'Τ−30′'):
    d = X[(X.tau == tau) & ((X.lo > 0) | (X.ld > 0))]
    A = np.c_[np.ones(len(d)), d.lo, d.ld]; b = np.linalg.lstsq(A, (d.tot - d.fair).values, rcond=None)[0]
    b2 = np.linalg.lstsq(A, (d.mu.values * 0 + (d.fair - d.tt - d.lev).values), rcond=None)[0]
    P(f'  {tau:8s} n {len(d)} · υπολοιπο αγορας: bO {b[1]:+.2f} · bD {b[2]:+.2f} (0 = η αγορα τα εχει) · η ιδια η αγορα «μετρα»: LO {b2[1]:+.2f} · LD {b2[2]:+.2f} (live: −0.5 / +1.0)')
# ---------- ΜΗΧΑΝΕΣ ----------
def feats(D):
    return np.c_[D.mu - D.fair, D.lo, D.ld, D.lop - D.lo, D.ldp - D.ld, (D.per == 'Οκτ-Δεκ').astype(float), (D.per == 'Μαρ-Απρ').astype(float), D['T'] - 225, (D.gn <= 10).astype(float)]
P(''); P('=== ΜΗΧΑΝΕΣ (LOSO) ===')
for tau in ('ανοιγμα', 'Τ−30′'):
    D = X[X.tau == tau].reset_index(drop=True); ys = D.sea.values; y = (D.tot - D.fair).values
    # Μ1
    WS = (0, .1, .2, .3, .5, .7, 1.0); m1 = np.zeros(len(D)); ch1 = {}
    for s in SE:
        tr = ys != s; w = min(WS, key=lambda w: np.mean((y[tr] - w * (D.mu - D.fair).values[tr]) ** 2)); ch1[s] = w
        m1[ys == s] = D.fair.values[ys == s] + w * (D.mu - D.fair).values[ys == s]
    # Μ2
    Xf = feats(D); m2 = np.zeros(len(D));
    for s in SE:
        tr = ys != s; A = np.c_[np.ones(tr.sum()), Xf[tr]]; b = np.linalg.solve(A.T @ A + 50 * np.eye(A.shape[1]), A.T @ y[tr])
        m2[ys == s] = D.fair.values[ys == s] + np.c_[np.ones((ys == s).sum()), Xf[ys == s]] @ b
    D['m1'] = m1; D['m2'] = m2
    rm = lambda c, s: np.sqrt(np.mean((D.tot[ys == s] - D[c][ys == s]) ** 2))
    P(f'  {tau}: Μ1 w ανα σεζον {ch1}')
    for c in ('fair', 'mu', 'm1', 'm2'):
        bet = sum(rm(c, s) < rm('fair', s) - 1e-9 for s in SE)
        P(f'     {c:5s} RMSE ' + ' · '.join(f'{s}: {rm(c, s):.3f}' for s in SE) + f' · καλυτερο απο την αγορα {bet}/5')
    for c in ('mu', 'm1', 'm2'):
        U = {th: picks(D, col=c, thr=th / 100) for th in (4, 6, 8, 10)}
        UU = {th: (U[th].groupby('sea').res.sum().reindex(SE, fill_value=0) if len(U[th]) else pd.Series(0.0, index=SE)) for th in U}
        lo_ = []; chs = []
        for s in SE:
            th = max(U, key=lambda t: UU[t].drop(s).sum()); chs.append(th)
            d_ = U[th]; lo_.append(d_[d_.sea == s] if len(d_) else d_)
        L_ = pd.concat(lo_) if lo_ else pd.DataFrame()
        P(f'     picks {c:3s} ' + ' · '.join(f'{th}%: {cell(U[th])}' for th in (4, 8)) + f' | LOSO κατωφλι {chs}: {cell(L_)}')
open(os.path.join(SC, 't36_totals_diag_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
