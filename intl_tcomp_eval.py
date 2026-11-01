"""
intl_tcomp_eval.py — ΤΕΣΤ 2/10/2026 (Στελιος «τρεξτο»): T των OVER εθνικων — ΣΗΜΕΡΑ (mix: −0.83 + 0.74·T_κατασταση + 0.58·xG) vs
COMP (καθε κομματι του T με δικο του βαρος, LOSO: |diff|, KO, ΚΟΝΤΙΝΟ, επιπεδο, NL, τελικη, xG ομαδων). Αφορμη: NL B overs 0/5.
ΜΕΤΡΑ: (Α) ακριβεια συνολου γκολ (Poisson log-lik, MAE) ανα σεζον & NL A/B/C/D/λοιπα — LOSO.
       (Β) over ΣΥΝΑΙΝΕΣΗΣ 72ω (intl_window_test, live ρυθμισεις) Crown|SBOBET ανα κατηγορια, mix vs comp.
ΠΡΟ-ΔΗΛΩΣΗ: COMP αντικαθιστα το mix αν (1) log-lik καλυτερο σε ≥4/6 σεζον, (2) over συναινεσης ROI (μεσος Crown/SBOBET) ≥ mix
  ΚΑΙ θετικο ≥4/5 σεζον, (3) στα NL B+C τα overs δεν χειροτερευουν. Δεν αλλαζει τιποτα live.
"""
import sys, os, math, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('intl_model_choice_v3.py', encoding='utf-8').read(); G = {'__name__': 'tc'}
with contextlib.redirect_stdout(open(os.devnull, 'w', encoding='utf-8')):
    exec(src[:src.index('bets = []')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass'), G)
D, T_of = G['D'], G['T_of']
X = pd.read_csv('intl_xg_teamN12.csv', dtype={'mid': str}); X = X[X.n >= 3]; XG = dict(zip(X.mid, X.xgsum))
M = pd.read_csv('intl_matches.csv', dtype={'mid': str}); COMP = dict(zip(M.mid, M.comp))
C = D[D.ctype.isin(['nl', 'qual', 'tourn']) & D.mid.astype(str).isin(XG)].copy()
C['xg'] = C.mid.astype(str).map(XG); C['div'] = C.mid.astype(str).map(COMP).fillna('').map(lambda c: c.replace('NationsLeague', 'NL ') if c.startswith('NationsLeague') else 'λοιπα')
SEAS = sorted(C.season.unique())
def feat(r): return [1.0, abs(r.d_M1) / 100, float(bool(r.ko)), float(bool(r.close)), (r.R_h + r.R_a) / 200, float(r.ctype == 'nl'), float(r.ctype == 'tourn'), r.xg]
F = np.array([feat(r) for r in C.itertuples()]); T0 = np.array([T_of(r.d_M1, r) for r in C.itertuples()]); y = C.tot.values.astype(float)
Tm, Tc = np.zeros(len(C)), np.zeros(len(C)); S = C.season.values
print('ΒΑΡΗ COMP (Μ1) ανα fold — σταθ · |diff| · KO · ΚΟΝΤΙΝΟ · επιπεδο · NL · τελικη · xG')
for s in SEAS:
    tr = S != s
    bm = np.linalg.lstsq(np.column_stack([np.ones(tr.sum()), T0[tr], C.xg.values[tr]]), y[tr], rcond=None)[0]
    bc = np.linalg.lstsq(F[tr], y[tr], rcond=None)[0]
    Tm[~tr] = np.maximum(bm[0] + bm[1] * T0[~tr] + bm[2] * C.xg.values[~tr], .8); Tc[~tr] = np.maximum(F[~tr] @ bc, .8)
    print(f'  {s}: ' + ' · '.join(f'{v:+.2f}' for v in bc) + f'   (mix: {bm[0]:+.2f} {bm[1]:.2f}·T {bm[2]:.2f}·xG)')
bA = np.linalg.lstsq(F, y, rcond=None)[0]
print('  ΟΛΑ: ' + ' · '.join(f'{v:+.2f}' for v in bA) + f'  → «κοντινο» αξιζει {bA[3]:+.2f} γκολ οταν ξερουμε xG (σημερα 0.74×0.49 = +0.36)')
ll = lambda T: np.array([t * math.log(T_) - T_ - math.lgamma(t + 1) for t, T_ in zip(y, T)])
Lm, Lc = ll(Tm), ll(Tc)
print('\n(Α) ΑΚΡΙΒΕΙΑ συνολου γκολ (LOSO) — log-lik ανα ματς (μεγαλυτερο = καλυτερο) · MAE')
print(f'  ΟΛΑ n{len(C)}: mix {Lm.mean():.4f} / comp {Lc.mean():.4f} (Δ {1e3*(Lc.mean()-Lm.mean()):+.1f}×10⁻³) · MAE {np.abs(y-Tm).mean():.3f} / {np.abs(y-Tc).mean():.3f}')
better = 0
for s in SEAS:
    k = S == s; better += Lc[k].mean() > Lm[k].mean()
    print(f'  {s} n{k.sum():4d}: Δ {1e3*(Lc[k].mean()-Lm[k].mean()):+6.1f} · μεσο T mix {Tm[k].mean():.2f} comp {Tc[k].mean():.2f} · γκολ {y[k].mean():.2f}')
print(f'  καλυτερο σε {better}/{len(SEAS)} σεζον')
print('\n  ανα κατηγορια: γκολ · T mix · T comp · Δ log-lik ×10⁻³')
for dv, g in C.groupby('div'):
    k = (C['div'] == dv).values
    print(f'  {dv:7s} n{k.sum():4d}: γκολ {y[k].mean():.2f} · mix {Tm[k].mean():.2f} · comp {Tc[k].mean():.2f} · Δ {1e3*(Lc[k].mean()-Lm[k].mean()):+.1f}')
k = C.close.values.astype(bool)
print(f'  ΚΟΝΤΙΝΑ n{k.sum()}: γκολ {y[k].mean():.2f} · mix {Tm[k].mean():.2f} · comp {Tc[k].mean():.2f}  |  ΜΗ κοντινα n{(~k).sum()}: γκολ {y[~k].mean():.2f} · mix {Tm[~k].mean():.2f} · comp {Tc[~k].mean():.2f}')
# (Β) overs συναινεσης
def cons(f):
    B = pd.read_csv(f, dtype={'mid': str, 'season': str}); B = B[(B.win == '72ω') & (B.rule == 'OVER') & B.model.isin(['M1', 'M2', 'M3'])]
    rows = [g.sort_values('hours').iloc[0] for _, g in B.groupby(['mid', 'book']) if g.model.nunique() >= 2]
    R = pd.DataFrame(rows); R['div'] = R.mid.map(COMP).fillna('').map(lambda c: c.replace('NationsLeague', 'NL ') if c.startswith('NationsLeague') else 'λοιπα'); return R
def fm(y_):
    if len(y_) < 3: return f'n{len(y_):3d}      —     '
    ps = y_.groupby('season').pnl.mean(); return f'n{len(y_):3d} {100*y_.pnl.mean():+6.1f}% {int((ps > 0).sum())}/{len(ps)}'
RM = cons('intl_window_test_proper_ahdogold_TmixN12_gddeepfav_bets.csv'); RC = cons('intl_window_test_proper_ahdogold_TcompN12_gddeepfav_bets.csv')
print('\n(Β) OVER ΣΥΝΑΙΝΕΣΗΣ 72ω — Crown | SBOBET · mix (σημερα) vs comp')
for dv in ['ΟΛΑ'] + sorted(set(RM['div']) | set(RC['div'])):
    cells = []
    for lab, R in (('mix', RM), ('comp', RC)):
        x = R if dv == 'ΟΛΑ' else R[R['div'] == dv]
        cells.append(f"{lab}: {fm(x[x.book == 'Crown'])} | {fm(x[x.book == 'SBOBET'])}")
    print(f'  {dv:7s} ' + '   ·   '.join(cells))
def avg(R, sub=None):
    x = R if sub is None else R[R['div'].isin(sub)]
    return np.mean([x[x.book == b].pnl.mean() for b in ('Crown', 'SBOBET')]), x
am, _ = avg(RM); ac, xc = avg(RC)
pos = int((xc[xc.book == 'Crown'].groupby('season').pnl.mean() > 0).sum())
bm_, _ = avg(RM, ['NL B', 'NL C']); bc_, _ = avg(RC, ['NL B', 'NL C'])
c1, c2, c3 = better >= 4, (ac >= am and pos >= 4), (bc_ >= bm_ - 1e-9)
print(f'\nΚΡΙΣΗ: (1) ακριβεια {better}/{len(SEAS)} {"✓" if c1 else "✗"} · (2) overs {100*am:+.1f}→{100*ac:+.1f}% ({pos} σεζον θετικες Crown) {"✓" if c2 else "✗"} · '
      f'(3) NL B+C {100*bm_:+.1f}→{100*bc_:+.1f}% {"✓" if c3 else "✗"} → {"COMP ΑΝΤΙΚΑΘΙΣΤΑ" if c1 and c2 and c3 else "ΜΕΝΕΙ το σημερινο"}')
