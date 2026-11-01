"""
uel_league_gap_test.py — 9/10/2026 (Στελιος: «στο UEL να μειωσουμε τη διαφορα δυναμικης λιγκας — Μιλαν, Λατσιο, Μπετις, Λιλ παιζουν με εναλλακτικη»).
Σημερινη αλυσιδα: λ = exp(... + D) × εδρα, μετα ξεφουσκωμα −γ·D/2 (D = s(λιγκα γηπ) − s(λιγκα φιλ), γεφυρες παικτων).
ΕΚΔΟΧΕΣ ΜΟΝΟ για UEL: η διαφορα λιγκας μετραει ρ·D αντι για D (ρ<1 = οι ομαδες ισχυροτερης λιγκας «μικραινουν») και το ξεφουσκωμα γ' ·
  (α) ΣΥΜΜΕΤΡΙΚΑ σε ολα τα ματς UEL · (β) ΜΟΝΟ οταν η ομαδα της ισχυροτερης λιγκας ειναι ΦΙΛΟΞΕΝΟΥΜΕΝΗ (D<0).
LOSO (τιμες απο τις 3 αλλες σεζον UEL, κριση στην 4η).
ΠΡΟ-ΔΗΛΩΣΗ: (1) πιθανοφανεια γκολ UEL καλυτερη σε ≥3/4 σεζον · (2) μεροληψια εκτος φαβορι μικραινει ΚΑΙ εντος φαβορι μενει εντος ±0.15 ·
(3) picks UEL (κλεισιμο, μεσος Crown/SBOBET) καλυτερα απο σημερα σε ≥3/4 σεζον.
"""
import sys, io, math, contextlib, itertools
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('uel_battery.py', encoding='utf-8').read(); src = src[:src.index('P0 = make_picks')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
g = {'__name__': 'lg'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
MIDS, GD, GH, GA, SEA, COMP, LH_N, LA_N, make_picks, fm = (g[k] for k in ('MIDS', 'GD', 'GH', 'GA', 'SEA', 'COMP', 'LH_N', 'LA_N', 'make_picks', 'fm'))
G2 = g['g']; Dv, LH2, LA2, GAM = np.asarray(G2['D'], float), np.asarray(G2['LH2'], float), np.asarray(G2['LA2'], float), G2['GAMMA_LIVE']
UEL = COMP == 'EuropaLeague'
assert np.allclose(np.maximum(LH2 - GAM * Dv / 2, .05)[UEL], LH_N[UEL]), 'ανακατασκευη λ UEL δεν ταιριαζει'
def lam(rho, gam, mode):
    sel = UEL & ((Dv < 0) if mode == 'β' else np.ones(len(Dv), bool))
    r = np.where(sel, rho, 1.0); gg = np.where(sel, gam, GAM)
    lh = LH2 * np.exp((r - 1) * Dv / 2); la = LA2 * np.exp(-(r - 1) * Dv / 2)        # μοιρασμα της αλλαγης στις 2 πλευρες
    lh = np.maximum(lh - gg * r * Dv / 2, .05); la = np.maximum(la + gg * r * Dv / 2, .05)
    return np.where(UEL, lh, LH_N), np.where(UEL, la, LA_N)
def ll(lh, la, m): return float(np.sum(GH[m] * np.log(lh[m]) - lh[m] + GA[m] * np.log(la[m]) - la[m]))
SEAS = ('2223', '2324', '2425', '2526')
P0 = make_picks(LH_N, LA_N); base = P0[P0.comp == 'EuropaLeague']
def bias(lh, la, m):
    s = lh - la; fav_home = s >= 0.5; fav_away = s <= -0.5
    eh = (GD - s)[m & fav_home].mean(); ea = (-(GD - s))[m & fav_away].mean()
    return eh, ea
print(f'ΣΗΜΕΡΑ (UEL): μεροληψια φαβορι εντος {bias(LH_N, LA_N, UEL)[0]:+.3f} · εκτος {bias(LH_N, LA_N, UEL)[1]:+.3f} · picks {fm(base)}')
print(f'   μεσο |D| στα ματς UEL: {np.abs(Dv[UEL]).mean():.2f} · ματς με ισχυροτερη λιγκα φιλοξενουμενη (D<0): {int((UEL & (Dv < 0)).sum())}/{int(UEL.sum())}')
GRID = list(itertools.product((1.0, 0.9, 0.8, 0.7, 0.6, 0.5), (GAM, -0.25, 0.0)))
print('\nΠΛΕΓΜΑ (ολο το δειγμα UEL, μονο για εικονα): Δπιθ γκολ · μεροληψια εντος/εκτος φαβορι')
for mode in ('α', 'β'):
    for rho, gam in GRID:
        lh, la = lam(rho, gam, mode); eh, ea = bias(lh, la, UEL)
        if gam == GAM or rho in (1.0, 0.7, 0.5):
            print(f'   ({mode}) ρ {rho:.1f} γ {gam:+.2f}: Δπιθ {ll(lh, la, UEL) - ll(LH_N, LA_N, UEL):+6.1f} · εντος {eh:+.3f} · εκτος {ea:+.3f}')
print('\nLOSO')
for mode in ('α', 'β'):
    dll = {}; LHa, LAa = LH_N.copy(), LA_N.copy(); ch = {}
    for te in SEAS:
        tr = UEL & (SEA != te); tm = UEL & (SEA == te)
        best = max(GRID, key=lambda p: ll(*lam(p[0], p[1], mode), tr)); ch[te] = best
        lh, la = lam(*best, mode); dll[te] = ll(lh, la, tm) - ll(LH_N, LA_N, tm); LHa[tm] = lh[tm]; LAa[tm] = la[tm]
    eh, ea = bias(LHa, LAa, UEL); P = make_picks(LHa, LAa); x = P[P.comp == 'EuropaLeague']
    ps = x.groupby('sea').pnl.mean(); p0 = base.groupby('sea').pnl.mean()
    c1 = sum(v > 0 for v in dll.values()) >= 3; c2 = abs(ea) < abs(bias(LH_N, LA_N, UEL)[1]) and abs(eh) <= 0.15
    c3 = int((ps.reindex(p0.index).fillna(-9) > p0).sum()) >= 3
    print(f'   ({mode}) τιμες ' + ' '.join(f'{s}:ρ{v[0]:.1f}/γ{v[1]:+.2f}' for s, v in ch.items()))
    print(f'       Δπιθ ' + ' '.join(f'{s}:{v:+.1f}' for s, v in dll.items()) + f' · μεροληψια εντος {eh:+.3f} / εκτος {ea:+.3f}')
    for role, hm, lab in (('fav', True, 'φαβ εντος'), ('fav', False, 'φαβ εκτος'), ('dog', True, 'αουτ εντος'), ('dog', False, 'αουτ εκτος')):
        print(f'       {lab:10s} {fm(x[(x.role == role) & (x.home == hm)])[:30]} · σημερα {fm(base[(base.role == role) & (base.home == hm)])[:30]}')
    print(f'       ΟΛΑ {fm(x)} vs σημερα {fm(base)} → (1){"✓" if c1 else "✗"} (2){"✓" if c2 else "✗"} (3){"✓" if c3 else "✗"} {"ΠΕΡΝΑ" if c1 and c2 and c3 else "ΔΕΝ ΠΕΡΝΑ"}')
