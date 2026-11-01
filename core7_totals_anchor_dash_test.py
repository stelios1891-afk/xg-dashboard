"""
core7_totals_anchor_dash_test.py — ΤΕΣΤ 1/10/2026 (Στελιος: «το 4 αξιζει τεστ»): ΑΓΚΥΡΑ ΣΥΝΟΛΩΝ στις προβλεψεις του DASHBOARD
(Match Projections: xG, 1Χ2, over/under, BTTS, ακριβες σκορ) — ΟΧΙ picks.
Βαση: core7_goals_gap_rows.csv (αγων. 7+, 4 σεζον, μηχανη live, Crown κλεισιμο συνολου → T_mkt).
Αγκυρα: καθε ομαδα διορθωση o (γκολ)· T' = T + o_h + o_a· μετα το ματς e = T_mkt − T' → o_h, o_a += λ·e/2 (μονο προηγουμενα ματς, md≥6).
Μοιρασια στις δυο ομαδες: (Ι) ΙΣΗ (+ΔT/2 η καθε μια, υπεροχη ιδια) · (Π) ΑΝΑΛΟΓΙΚΗ (λ_h·T'/T, λ_a·T'/T).
λ ∈ {0.2, 0.3, 0.5, 0.7, 1.0}.
ΜΕΤΡΑ: LL συνολου γκολ · LL ακριβους σκορ · Brier over 1.5/2.5/3.5 · Brier BTTS · RPS 1Χ2 — ανα σεζον, Δ vs σημερα.
ΠΡΟ-ΔΗΛΩΣΗ: μια εκδοχη ΜΠΑΙΝΕΙ στο dashboard αν (1) LL συνολου καλυτερο 4/4 σεζον, (2) LL ακριβους σκορ καλυτερο ≥3/4,
  (3) RPS 1Χ2 οχι χειροτερο (Δ ≤ +0.0001) και (4) Brier BTTS οχι χειροτερο. Επιλογη λ: LOSO με κριτηριο LL ακριβους σκορ.
"""
import sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
W = pd.read_csv('core7_goals_gap_rows.csv', dtype={'season': str, 'mid': str}).sort_values(['league', 'date']).reset_index(drop=True)
SEAS = sorted(W.season.unique()); N = len(W)
hg, ag = W.hg.values.astype(int), W.ag.values.astype(int); tg = hg + ag
y1x2 = np.where(hg > ag, 0, np.where(hg == ag, 1, 2))
IDX = np.add.outer(np.arange(13), np.arange(13))

def anchor_T(lam):
    T = (W.xh + W.xa).values; out = T.copy()
    for lg, idx in W.groupby('league').groups.items():
        off = {}; cur = None
        for i in idx:
            r = W.loc[i]
            if r.season != cur: off = {}; cur = r.season
            t = T[i] + off.get(r.h, 0) + off.get(r.a, 0); out[i] = t
            if r.md >= 6:
                e = r.T_mkt - t; off[r.h] = off.get(r.h, 0) + lam * e / 2; off[r.a] = off.get(r.a, 0) + lam * e / 2
    return out

def metrics(lh, la):
    m = dict(ll_t=np.zeros(N), ll_s=np.zeros(N), o15=np.zeros(N), o25=np.zeros(N), o35=np.zeros(N), btts=np.zeros(N), rps=np.zeros(N))
    for i in range(N):
        M = np.asarray(picks.score_matrix_dom(max(lh[i], .05), max(la[i], .05)))
        tot = np.bincount(IDX.ravel(), weights=M.ravel(), minlength=25)
        m['ll_t'][i] = np.log(max(tot[tg[i]], 1e-12))
        m['ll_s'][i] = np.log(max(M[min(hg[i], 12), min(ag[i], 12)], 1e-12))
        for k, L in (('o15', 1), ('o25', 2), ('o35', 3)):
            m[k][i] = (tot[L + 1:].sum() - (tg[i] > L)) ** 2
        pb = 1 - M[0, :].sum() - M[:, 0].sum() + M[0, 0]
        m['btts'][i] = (pb - (hg[i] > 0 and ag[i] > 0)) ** 2
        ph, pd_ = np.tril(M, -1).sum(), np.trace(M)
        c1, c2 = ph, ph + pd_; o1, o2 = (1, 1) if y1x2[i] == 0 else ((0, 1) if y1x2[i] == 1 else (0, 0))
        m['rps'][i] = ((c1 - o1) ** 2 + (c2 - o2) ** 2) / 2
    return m

xh, xa = W.xh.values, W.xa.values; T0 = xh + xa
R = {'ΣΗΜΕΡΑ': metrics(xh, xa)}
for lam in (0.2, 0.3, 0.5, 0.7, 1.0):
    Tn = anchor_T(lam); d = Tn - T0
    R[f'ΙΣΗ λ{lam}'] = metrics(np.maximum(xh + d / 2, .05), np.maximum(xa + d / 2, .05))
    f = Tn / np.maximum(T0, .1)
    R[f'ΑΝΑΛ λ{lam}'] = metrics(xh * f, xa * f)
    print(f'λ {lam} ok', flush=True)
B = R['ΣΗΜΕΡΑ']; S = W.season.values
def per(m, k, better_high):
    return sum(((m[k][S == s].mean() > B[k][S == s].mean()) if better_high else (m[k][S == s].mean() < B[k][S == s].mean())) for s in SEAS)
print('\nΔ vs ΣΗΜΕΡΑ (×10⁻⁴) · σε ( ) σεζον καλυτερες · LL: + = καλυτερο · Brier/RPS: − = καλυτερο')
print(f'  {"εκδοχη":12s} {"LL συνολου":>16s} {"LL σκορ":>16s} {"Brier o1.5":>12s} {"Brier o2.5":>12s} {"Brier o3.5":>12s} {"Brier BTTS":>14s} {"RPS 1Χ2":>14s}')
for lab, m in R.items():
    if lab == 'ΣΗΜΕΡΑ': continue
    c = lambda k, hi: f'{1e4*(m[k].mean()-B[k].mean()):+7.1f} ({per(m, k, hi)}/4)'
    print(f'  {lab:12s} {c("ll_t", True):>16s} {c("ll_s", True):>16s} {1e4*(m["o15"].mean()-B["o15"].mean()):+12.1f} {1e4*(m["o25"].mean()-B["o25"].mean()):+12.1f} '
          f'{1e4*(m["o35"].mean()-B["o35"].mean()):+12.1f} {c("btts", False):>14s} {c("rps", False):>14s}')
print('\nLOSO (κριτηριο LL ακριβους σκορ, ανα τροπο μοιρασιας)')
for mode in ('ΙΣΗ', 'ΑΝΑΛ'):
    labs = [l for l in R if l.startswith(mode)]; tot = 0
    for s in SEAS:
        best = max(labs, key=lambda l: R[l]['ll_s'][S != s].mean())
        tot += (R[best]['ll_s'][S == s].mean() - B['ll_s'][S == s].mean())
        print(f'  {mode} {s}: διαλεγει {best} → LL σκορ Δ {1e4*(R[best]["ll_s"][S == s].mean() - B["ll_s"][S == s].mean()):+.1f}')
print('\nΚΡΙΣΗ:')
for lab, m in R.items():
    if lab == 'ΣΗΜΕΡΑ': continue
    ok = (per(m, 'll_t', True) == 4 and per(m, 'll_s', True) >= 3 and m['rps'].mean() - B['rps'].mean() <= 1e-4 and m['btts'].mean() <= B['btts'].mean())
    print(f'  {lab:12s} {"✓ ΠΕΡΝΑ" if ok else "✗"}')
