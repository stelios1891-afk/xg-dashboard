# -*- coding: utf-8 -*-
"""
season_sim_dc_test.py — 29/9/2026 (Στελιος: «6 — season projections με Dixon-Coles»). ΜΟΝΟ τεστ.
Ιδιο harness με season_sim_combo_test.py (season_sim_tests.run_cell, N=10.000, ιδιο seed, cutoffs now/10/15/20/30,
2223-2425 train + 2526 κριση), ΜΕΘΟΔΟΣ = η live D1 (P1 χωρις SoS + αξια c=0.05). Δυο εκδοχες ΠΑΝΩ ΣΤΑ ΙΔΙΑ ratings:
  D1_db = σημερα: δειγματοληψια σκορ Poisson × DRAW_BOOST 1.13 σε ολη τη διαγωνιο (rejection)
  D1_dc = κανονικο Dixon-Coles οπως τα εγχωρια live (picks.DC_RHO_DOM −0.03, τ μονο 0-0/1-0/0-1/1-1, rejection)
ΠΡΟ-ΔΗΛΩΣΗ: το D1_dc ΠΕΡΝΑ (για συνεπεια με τα εγχωρια) αν log-loss train ΟΧΙ χειροτερο απο D1_db πανω απο 0.0005
ΚΑΙ cov80 train μεσα [0.72, 0.88]. Βελτιωση αναφερεται (ΔLL, σεζον).
"""
import os, sys, time
import numpy as np, pandas as pd
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'dashboard'))
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
_keep = open('season_sim_tests_out.txt', encoding='utf-8').read()
import season_sim_tests as T
T.OUT_F.close()
open('season_sim_tests_out.txt', 'w', encoding='utf-8').write(_keep)
T.OUT_F = open('season_sim_dc_test_out.txt', 'w', encoding='utf-8')
log = T.log
import picks, season_sim as SS, season_sim_validate as SV

_ORIG = SS.sample_scores
MODE = {'m': 'db'}
def sample_dc(lam_h, lam_a, rng, draw_boost=None):
    """Poisson + Dixon-Coles τ με rejection: αποδοχη με πιθανοτητα τ(i,j)/τ_max (τ_max = max(1−λμρ, 1−ρ, 1) για ρ<0)."""
    if MODE['m'] != 'dc':
        return _ORIG(lam_h, lam_a, rng, draw_boost)
    r = picks.DC_RHO_DOM
    lh = np.broadcast_to(lam_h, np.broadcast(lam_h, lam_a).shape) if np.ndim(lam_h) else lam_h
    la = np.broadcast_to(lam_a, np.broadcast(lam_h, lam_a).shape) if np.ndim(lam_a) else lam_a
    def tau(gh, ga, l1, l2):
        t = np.ones(gh.shape)
        t = np.where((gh == 0) & (ga == 0), 1 - l1 * l2 * r, t)
        t = np.where((gh == 0) & (ga == 1), 1 + l1 * r, t)
        t = np.where((gh == 1) & (ga == 0), 1 + l2 * r, t)
        t = np.where((gh == 1) & (ga == 1), 1 - r, t)
        return t
    def tmax(l1, l2):
        return np.maximum(np.maximum(1 - l1 * l2 * r, 1 - r), 1.0)
    gh = rng.poisson(lh); ga = rng.poisson(la)
    L1 = np.broadcast_to(lh, gh.shape); L2 = np.broadcast_to(la, gh.shape)
    redo = rng.random(gh.shape) > tau(gh, ga, L1, L2) / tmax(L1, L2)
    while redo.any():
        idx = np.nonzero(redo)
        nh = rng.poisson(L1[idx]); na = rng.poisson(L2[idx])
        gh[idx] = nh; ga[idx] = na
        redo = np.zeros_like(redo)
        redo[idx] = rng.random(nh.shape) > tau(nh, na, L1[idx], L2[idx]) / tmax(L1[idx], L2[idx])
    return gh, ga
SS.sample_scores = sample_dc

# ελεγχος δειγματοληπτη: ισοπαλια MC vs αναλυτικο DC
rng = np.random.default_rng(7); MODE['m'] = 'dc'
lh, la = np.full(400000, 1.5), np.full(400000, 1.1)
gh, ga = sample_dc(lh, la, rng)
an = picks.score_matrix_dom(1.5, 1.1)
log(f"ελεγχος DC δειγματοληπτη (λ 1.5/1.1): ισοπαλια MC {np.mean(gh == ga):.4f} vs αναλυτικο {np.trace(an):.4f} · 0-0 {np.mean((gh == 0) & (ga == 0)):.4f} vs {an[0, 0]:.4f}")
MODE['m'] = 'db'

CFG = dict(K=8.0, blend='ramp', sos='none', p1=True, c=0.05)
def main():
    t0 = time.time()
    now_md = SV.current_md()
    M, id2name = SS.load_5s()
    log(f"XI values: {T.build_team_xi(M)} ομαδα-ματς · N={T.N_RUNS}")
    rows = []
    for lg in SS.CORE7:
        cuts = [('now', now_md[lg])] + [(str(k), k) for k in T.CUTS[1:]]
        for sea in T.ALL4:
            G = M[(M.league == lg) & (M.season == sea)].reset_index(drop=True)
            Gprev = M[(M.league == lg) & (M.season == SS.SEASONS5[SS.SEASONS5.index(sea) - 1])].reset_index(drop=True)
            for kl, k in cuts:
                for mode, name in (('db', 'D1_db'), ('dc', 'D1_dc')):
                    MODE['m'] = mode
                    rows.extend(T.run_cell(lg, sea, G, Gprev, k, kl, id2name, {name: CFG}))
                MODE['m'] = 'db'
            log(f"  {lg:13s} {sea} ok [{time.time()-t0:6.0f}s]")
        pd.DataFrame(rows).to_pickle('season_sim_dc_rows.pkl')
    R = pd.DataFrame(rows); R.to_pickle('season_sim_dc_rows.pkl')
    T.main_table(R, ['D1_db', 'D1_dc'], "SEASON PROJECTIONS: D1 με DRAW_BOOST 1.13 (σημερα) vs κανονικο Dixon-Coles ρ −0.03 (log-loss: χαμηλοτερο = καλυτερο)")
    a = SV.agg(R[(R.method == 'D1_db') & R.sea.isin(T.TRAIN)]); b = SV.agg(R[(R.method == 'D1_dc') & R.sea.isin(T.TRAIN)])
    seas = [(s, SV.agg(R[(R.method == 'D1_db') & (R.sea == s)])['ll_mean'], SV.agg(R[(R.method == 'D1_dc') & (R.sea == s)])['ll_mean']) for s in T.ALL4]
    better = sum(dc < db for _, db, dc in seas)
    ok = (b['ll_mean'] <= a['ll_mean'] + 0.0005) and (0.72 <= b['cov80'] <= 0.88)
    log(f"\nΚΡΙΣΗ: log-loss train DC {b['ll_mean']:.4f} vs σημερα {a['ll_mean']:.4f} (Δ {b['ll_mean'] - a['ll_mean']:+.4f}) · καλυτερο σε {better}/4 σεζον · "
        f"cov80 {b['cov80']:.3f} → {'ΠΕΡΝΑ' if ok else 'ΔΕΝ ΠΕΡΝΑ'} · σεζον: " + ' · '.join(f'{s} {db:.4f}→{dc:.4f}' for s, db, dc in seas))
    log(f"ΤΕΛΟΣ ({time.time()-t0:.0f}s)")
    T.OUT_F.close()

if __name__ == '__main__':
    main()
