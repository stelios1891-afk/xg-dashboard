"""
core7_drawboost_test.py — 28/9/2026 ΤΕΣΤ 1: ΜΕΓΕΘΟΣ ΔΙΟΡΘΩΣΗΣ ΙΣΟΠΑΛΙΩΝ (Στελιος: «το 1.13 ειναι η Dixon-Coles διορθωση — γιατι να αλλαξει;»).
Μηχανη = live (core7_mech_preds_base.csv, χωρις αγκυρα), CORE7 2223-2526, αγωνιστικες 7+.
ΕΚΔΟΧΕΣ πινακα σκορ:  DB x ∈ {1.00, 1.04, 1.08, 1.13 (σημερα)} = πολλαπλασιασμος ΟΛΩΝ των ισοπαλων σκορ (οπως picks.gd_dist)
                       DC ρ = κανονικο Dixon-Coles (διορθωνει ΜΟΝΟ 0-0 / 1-0 / 0-1 / 1-1), ρ με μεγιστη πιθανοφανεια στα πραγματικα σκορ.
ΠΡΟ-ΔΗΛΩΣΗ: (1) ακριβεια — για καθε σεζον η παραμετρος (x ή ρ) επιλεγεται απο τις ΑΛΛΕΣ 3 (log-lik 1Χ2) και μετρα στην 4η: RPS καλυτερο
  απο 1.13 σε ≥3/4 σεζον· (2) dogs 15+ (κανονες live, closing Pinnacle) ROI ≥ σημερα ΚΑΙ μοναδες ≥ σημερα. ΠΕΡΝΑ μονο αν (1) ΚΑΙ (2).
Πληροφοριακα: προβλεπομενες vs πραγματικες ισοπαλιες, dogs 7-14.
"""
import sys, io, math, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
src = open('core7_mech_eval.py', encoding='utf-8').read()
g = {'__name__': 'db'}
with contextlib.redirect_stdout(_Q()):
    exec(src[:src.index('rows = []')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass'), g)
picks, ODDS = g['picks'], g['ODDS']
P = pd.read_csv('core7_mech_preds_base.csv', dtype={'season': str}); P = P[(P.md >= 6) & P.gd.notna()].copy(); P['mid'] = P.mid.astype(str)
TG = pd.read_csv('teamgame_inputs_5s_wf.csv', dtype={'season': str}); TG['mid'] = TG.mid.astype(str)
SC = {m: (int(gm[gm.is_home == 1].gf.iloc[0]), int(gm[gm.is_home == 0].gf.iloc[0])) for m, gm in TG.groupby('mid') if len(gm) == 2}
P['hg'] = P.mid.map(lambda m: SC.get(m, (np.nan, np.nan))[0]); P['ag'] = P.mid.map(lambda m: SC.get(m, (np.nan, np.nan))[1])
P = P[P.hg.notna()].reset_index(drop=True)
P['xh'] = P.xg_h.clip(.05, 6); P['xa'] = P.xg_a.clip(.05, 6)
SEAS = sorted(P.season.unique()); y = np.where(P.gd > 0, 2, np.where(P.gd == 0, 1, 0))
print(f'ματς (αγων. 7+, με σκορ): {len(P)} · πραγματικες ισοπαλιες {100*(P.gd == 0).mean():.1f}%')
F = [math.factorial(i) for i in range(13)]
def mat(lh, la, kind, par):
    ph = np.array([math.exp(-lh) * lh ** i / F[i] for i in range(13)]); pa = np.array([math.exp(-la) * la ** j / F[j] for j in range(13)])
    M = np.outer(ph, pa)
    if kind == 'DB':
        for i in range(13): M[i, i] *= par
    else:
        r = par; M[0, 0] *= 1 - lh * la * r; M[0, 1] *= 1 + lh * r; M[1, 0] *= 1 + la * r; M[1, 1] *= 1 - r
    return M / M.sum()
def gd_of(M):
    d = {}
    for i in range(13):
        for j in range(13): d[i - j] = d.get(i - j, 0) + M[i, j]
    return d
def p3(M):
    return np.array([np.tril(M, -1).sum(), np.trace(M), np.triu(M, 1).sum()])
def rps(pm, yy):
    o = np.zeros_like(pm); o[np.arange(len(yy)), 2 - yy] = 1
    return float(np.mean(((np.cumsum(pm, 1) - np.cumsum(o, 1)) ** 2)[:, :2].sum(1) / 2))
GRID = {'DB': [1.00, 1.02, 1.04, 1.06, 1.08, 1.10, 1.13, 1.16], 'DC': [0.0, -0.03, -0.06, -0.09, -0.12, -0.15]}
PM = {}; LL = {}
for kind, vals in GRID.items():
    for v in vals:
        pm = np.zeros((len(P), 3)); ll = np.zeros(len(P))
        for i, (a, b, h_, a_) in enumerate(zip(P.xh, P.xa, P.hg.astype(int), P.ag.astype(int))):
            M = mat(a, b, kind, v); pm[i] = p3(M); ll[i] = math.log(max(M[min(h_, 12), min(a_, 12)], 1e-12))
        PM[(kind, v)] = pm; LL[(kind, v)] = ll
    print(f'  {kind} πλεγμα ok', flush=True)
print('\nΑ. ΒΑΘΜΟΝΟΜΗΣΗ (ολα τα ματς): ισοπαλιες προβλεπομενες · RPS 1Χ2 · log-lik σκορ')
for k in PM:
    print(f'  {k[0]} {k[1]:+.2f}: ισοπαλιες {100*PM[k][:, 1].mean():.1f}% · RPS {rps(PM[k], y):.5f} · log-lik σκορ {LL[k].mean():.4f}')
sel = {}
for kind in GRID:
    for s_ in SEAS:
        tr = (P.season != s_).values
        sel[(kind, s_)] = max(GRID[kind], key=lambda v: LL[(kind, v)][tr].mean())
print('\nLOSO επιλογες (απο τις αλλες 3 σεζον, log-lik σκορ): ' + ' · '.join(f'{k[0]} {k[1]}: {v}' for k, v in sel.items()))
def loso_pm(kind):
    pm = np.zeros((len(P), 3))
    for s_ in SEAS:
        m = (P.season == s_).values; pm[m] = PM[(kind, sel[(kind, s_)])][m]
    return pm
def dogs(kind, par_of_season):
    out = []
    for i, r in enumerate(P.itertuples()):
        if r.mid not in ODDS: continue
        L, ah, aa = ODDS[r.mid]; d = gd_of(mat(r.xh, r.xa, kind, par_of_season(r.season)))
        for side, ud, odds in ((1, L, ah), (-1, -L, aa)):
            if ud >= 0.5 and 1.70 <= odds <= 2.10:
                pw, pp = picks.p_cover(d, side, ud)
                if pw * (odds - 1) * (1 - picks.MARGIN) - (1 - pw - pp) >= 0.10:
                    out.append(('7-14' if r.md <= 13 else '15+', r.season, picks.settle(r.gd, side, ud, odds)))
    return pd.DataFrame(out, columns=['win', 'season', 'pnl'])
res = {}
ARMS = [('ΣΗΜΕΡΑ DB 1.13', 'DB', lambda s: 1.13), ('DB LOSO', 'DB', lambda s: sel[('DB', s)]), ('Dixon-Coles LOSO', 'DC', lambda s: sel[('DC', s)])] + \
       [(f'DB {v:.2f} (σταθερο)', 'DB', (lambda vv: (lambda s: vv))(v)) for v in (1.00, 1.04, 1.08)]
base_rps = {s_: rps(PM[('DB', 1.13)][(P.season == s_).values], y[(P.season == s_).values]) for s_ in SEAS}
for name, kind, f in ARMS:
    pm = np.zeros((len(P), 3))
    for s_ in SEAS:
        m = (P.season == s_).values; pm[m] = PM[(kind, round(f(s_), 2) if kind == 'DB' else f(s_))][m]
    row = {'ισοπ%': round(100 * pm[:, 1].mean(), 1), 'RPS': round(rps(pm, y), 5)}
    row['RPS σεζον καλυτερα'] = sum(rps(pm[(P.season == s_).values], y[(P.season == s_).values]) < base_rps[s_] - 1e-9 for s_ in SEAS)
    B = dogs(kind, f)
    for w_ in ('7-14', '15+'):
        d = B[B.win == w_]; ps = d.groupby('season').pnl.mean()
        row[f'dogs {w_}'] = f'{len(d)} / {100*d.pnl.mean():+.1f}% / {d.pnl.sum():+.0f}u / {int((ps > 0).sum())}/4'
        row[f'_roi{w_}'] = d.pnl.mean(); row[f'_u{w_}'] = d.pnl.sum()
    res[name] = row; print(f'  {name} ok', flush=True)
T = pd.DataFrame(res).T; pd.set_option('display.width', 250)
print('\nΒ. ΕΚΔΟΧΕΣ (πραγματικες ισοπαλιες {:.1f}%)'.format(100 * (P.gd == 0).mean()))
print(T[['ισοπ%', 'RPS', 'RPS σεζον καλυτερα', 'dogs 7-14', 'dogs 15+']].to_string())
b = res['ΣΗΜΕΡΑ DB 1.13']
for name in ('DB LOSO', 'Dixon-Coles LOSO'):
    r = res[name]; c1 = r['RPS σεζον καλυτερα'] >= 3; c2 = r['_roi15+'] >= b['_roi15+'] and r['_u15+'] >= b['_u15+']
    print(f"ΚΡΙΣΗ {name}: ακριβεια {r['RPS σεζον καλυτερα']}/4 {'✓' if c1 else '✗'} · dogs 15+ {100*r['_roi15+']:+.1f}%/{r['_u15+']:+.0f}u vs {100*b['_roi15+']:+.1f}%/{b['_u15+']:+.0f}u {'✓' if c2 else '✗'} → {'ΠΕΡΝΑ' if c1 and c2 else 'ΔΕΝ ΠΕΡΝΑ'}")
