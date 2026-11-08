"""
intl_dc_test.py — 28/9/2026 (Στελιος: Dixon-Coles «με τον ιδιο ακριβως τροπο» και στις εθνικες). ΜΟΝΟ τεστ.
Ιδιο backtest παραθυρου 72ω με τις live ρυθμισεις (intl_window_test.py: OVER proper, AH hybrid, T mix N12, βαθια φαβορι),
με ΜΟΝΗ αλλαγη τον πινακα σκορ: picks.gd_dist → κανονικο Dixon-Coles (μονο 0-0/1-0/0-1/1-1), ρ ανα σεζον LOSO
(log-lik πραγματικων σκορ με τα λ του Μ1 στα αγωνιστικα απο τις ΑΛΛΕΣ σεζον). Τα over ΔΕΝ επηρεαζονται (Poisson T χωρις boost).
Εξοδος: intl_window_test_..._DC_bets.csv· συγκριση συναινεσης στο intl_dc_eval (κατω, ιδιο αρχειο).
"""
import os, sys, math
os.environ.update(OVER_FORMULA='proper', AH_FORMULA='hybrid', T_MODE='mix', XG_N='12', GD_FIX='deepfav')
sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
import picks
F = [math.factorial(i) for i in range(13)]
_ORIG = picks.gd_dist
def dc_mat(lh, la, rho):
    ph = [math.exp(-lh) * lh ** i / F[i] for i in range(13)]; pa = [math.exp(-la) * la ** j / F[j] for j in range(13)]
    M = np.outer(ph, pa); M[0, 0] *= 1 - lh * la * rho; M[0, 1] *= 1 + lh * rho; M[1, 0] *= 1 + la * rho; M[1, 1] *= 1 - rho
    return M / M.sum()
def dc_gd(lh, la):
    M = dc_mat(lh, la, picks._RHO); d = {}
    for i in range(13):
        for j in range(13): d[i - j] = d.get(i - j, 0) + M[i, j]
    return d
src = open('intl_window_test.py', encoding='utf-8').read()
i0 = src.index('bets = []' + chr(10) + 'WINS')
g = {'__name__': 'intl_dc'}
exec(src[:i0].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass'), g)
D, MODELS, T_final, A_GOAL = g['D'], g['MODELS'], g['T_final'], g['A_GOAL']
# σκορ
M = pd.read_csv('intl_matches.csv', dtype={'mid': str}); SC = dict(zip(M.mid, zip(M.hs, M['as'])))
C = D[D.ctype.isin(['nl', 'qual', 'tourn'])].copy()
C['hs'] = C.mid.astype(str).map(lambda m: SC.get(m, (np.nan, np.nan))[0]); C['as_'] = C.mid.astype(str).map(lambda m: SC.get(m, (np.nan, np.nan))[1])
C = C[C.hs.notna()]
lam = []
for r in C.itertuples():
    d = getattr(r, 'd_M1'); T = T_final(d, r, 'M1'); s = A_GOAL * d; lam.append((max((T + s) / 2, .15), max((T - s) / 2, .15)))
C['lh'] = [a for a, _ in lam]; C['la'] = [b for _, b in lam]
RHOS = [0.0, -0.03, -0.06, -0.09, -0.12, -0.15]; DBV = 1.13
def ll_dc(rho, sub):
    return np.mean([math.log(max(dc_mat(a, b, rho)[min(int(h), 12), min(int(x), 12)], 1e-12)) for a, b, h, x in zip(sub.lh, sub.la, sub.hs, sub.as_)])
def db_mat(lh, la):
    ph = [math.exp(-lh) * lh ** i / F[i] for i in range(13)]; pa = [math.exp(-la) * la ** j / F[j] for j in range(13)]
    Mx = np.outer(ph, pa); np.fill_diagonal(Mx, np.diag(Mx) * DBV); return Mx / Mx.sum()
SEAS = sorted(C.season.unique())
LLS = {r: {s_: ll_dc(r, C[C.season != s_]) for s_ in SEAS} for r in RHOS}
RHO = {s_: max(RHOS, key=lambda r: LLS[r][s_]) for s_ in SEAS}
print('ρ LOSO εθνικες: ' + ' · '.join(f'{s}: {r}' for s, r in RHO.items()))
# ακριβεια (Μ1 λ): ισοπαλιες & RPS 1Χ2 απο τον πινακα σκορ, ανα σεζον
y = np.where(C.hs > C.as_, 2, np.where(C.hs == C.as_, 1, 0))
def p3(Mx): return np.array([np.tril(Mx, -1).sum(), np.trace(Mx), np.triu(Mx, 1).sum()])
def rps(pm, yy):
    o = np.zeros_like(pm); o[np.arange(len(yy)), 2 - yy] = 1
    return float(np.mean(((np.cumsum(pm, 1) - np.cumsum(o, 1)) ** 2)[:, :2].sum(1) / 2))
PB = np.array([p3(db_mat(a, b)) for a, b in zip(C.lh, C.la)]); PD = np.array([p3(dc_mat(a, b, RHO[s])) for a, b, s in zip(C.lh, C.la, C.season)])
print(f'ΑΚΡΙΒΕΙΑ (Μ1, {len(C)} αγωνιστικα): πραγματικες ισοπαλιες {100*(y == 1).mean():.1f}% · ΣΗΜΕΡΑ ×1.13 {100*PB[:, 1].mean():.1f}% RPS {rps(PB, y):.5f} · DC {100*PD[:, 1].mean():.1f}% RPS {rps(PD, y):.5f}')
wins = 0
for s_ in SEAS:
    m = (C.season == s_).values; a, b = rps(PD[m], y[m]), rps(PB[m], y[m]); wins += a < b
    print(f'   {s_}: ΣΗΜΕΡΑ {b:.5f} · DC {a:.5f}')
print(f'   DC καλυτερο σε {wins}/{len(SEAS)} σεζον')
# backtest με DC
picks._RHO = 0.0; picks.gd_dist = dc_gd
body = src[i0:].replace("for r in D.itertuples():\n    if r.dead:\n        continue", "for r in D.itertuples():\n    picks._RHO = RHO_BY_SEASON.get(str(r.season), 0.0)\n    if r.dead:\n        continue", 1)
assert 'RHO_BY_SEASON' in body
body = body.replace("B.to_csv(f'intl_window_test{SUF}_bets.csv'", "B.to_csv(f'intl_window_test{SUF}_DC_bets.csv'").replace("open(f'intl_window_test{SUF}_out.txt'", "open(f'intl_window_test{SUF}_DC_out.txt'")
g['RHO_BY_SEASON'] = {str(k): v for k, v in RHO.items()}
import io, contextlib
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
with contextlib.redirect_stdout(_Q()):
    exec(body, g)
picks.gd_dist = _ORIG
print('DC backtest γραφτηκε: intl_window_test' + g['SUF'] + '_DC_bets.csv')
# ---- συναινεση 72ω: ΣΗΜΕΡΑ vs DC ----
def cons(fn):
    B = pd.read_csv(fn); B = B[B.win == '72ω'].copy(); B['mk'] = np.where(B.rule == 'OVER', 'OVER', B.rule)
    rows = []
    for (mid, book, mk, side), gg in B.groupby(['mid', 'book', 'mk', 'side']):
        if gg.model.nunique() < 2: continue
        gg = gg.sort_values('hours', ascending=False).drop_duplicates('model'); r = gg.iloc[1]
        rows.append(dict(book=book, mk=mk, season=r.season, pnl=r.pnl))
    return pd.DataFrame(rows)
base_fn = 'intl_window_test' + g['SUF'] + '_bets.csv'; dc_fn = 'intl_window_test' + g['SUF'] + '_DC_bets.csv'
out = {}
for lab, fn in (('ΣΗΜΕΡΑ', base_fn), ('DC', dc_fn)):
    Cn = cons(fn); r_ = {}
    for mk in ('ΟΛΑ', 'AH fav', 'AH dog', 'OVER'):
        d = Cn if mk == 'ΟΛΑ' else Cn[Cn.mk == mk]
        roi = np.mean([d[d.book == b].pnl.mean() for b in ('Crown', 'SBOBET')]); u = np.mean([d[d.book == b].pnl.sum() for b in ('Crown', 'SBOBET')])
        ps = d.groupby('season').pnl.mean(); r_[mk] = (roi, u, int((ps > 0).sum()), ps.size, len(d) // 2)
    out[lab] = r_
print('\nΣΥΝΑΙΝΕΣΗ 72ω (μεσος Crown/SBOBET): n · ROI · μοναδες · θετικες σεζον')
for mk in ('ΟΛΑ', 'AH fav', 'AH dog', 'OVER'):
    print(f'  {mk:7s} ' + ' | '.join(f'{lab}: n{v[mk][4]} {100*v[mk][0]:+.1f}% {v[mk][1]:+.1f}u {v[mk][2]}/{v[mk][3]}' for lab, v in out.items()))
b, d_ = out['ΣΗΜΕΡΑ']['ΟΛΑ'], out['DC']['ΟΛΑ']
c2 = d_[0] >= b[0] and d_[1] >= b[1]
print(f"\nΚΡΙΣΗ DC εθνικες: ακριβεια {wins}/{len(SEAS)} {'✓' if wins >= math.ceil(0.75 * len(SEAS)) else '✗'} · συναινεση {100*d_[0]:+.1f}%/{d_[1]:+.1f}u vs {100*b[0]:+.1f}%/{b[1]:+.1f}u {'✓' if c2 else '✗'}")
