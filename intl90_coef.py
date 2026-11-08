# -*- coding: utf-8 -*-
"""intl90_coef.py — τρεχει ΜΕΣΩ intl90_harness.py (old|new). Ποσο «μολυσμενα» ηταν τα νοκ-αουτ + refit του OLS συνολου (ιδιες προδιαγραφες με intl_integrate Μ1 / intl_xg_totals ctx / live τυπο με επιπεδο)
+ τσεπη «over × νοκ-αουτ» (closing Crown, τυφλα, ιδιο με intl_market_pockets) ανα σεζον."""
import sys, os, json
import numpy as np, pandas as pd
exec(open('intl_integrate.py', encoding='utf-8').read().split("# ===================== Μ1 =====================")[0])
MM = pd.read_csv('intl_matches.csv', dtype={'season': str, 'mid': str})
ET = set(MM[MM.et].mid)
D['et'] = D.mid.isin(ET)
P_(f'δειγμα D (αγωνιστικα 2122-2526 με Crown): {len(D)} · KO {int(D.ko.sum())} · KO με παραταση/πεναλτι {int((D.ko & D.et).sum())}')
for lab, m in (('ΚΟ ολα', D.ko), ('ΚΟ με O/U', D.ko & D.ou_line.notna()), ('ομιλοι με O/U', ~D.ko & D.ou_line.notna())):
    d = D[m]; P_(f'  {lab:14s} n={len(d)} γκολ {d.tot.mean():.3f} · γραμμη {d.ou_line.mean():.3f} · ισοπαλιες {(d.gd == 0).mean()*100:.0f}%')
# ολη η βαση (ολοι οι τυποι/σεζον): KO με παραταση
MM['tot'] = MM.hs + MM['as']
P_(f"ολη η βαση: ματς με παραταση/πεναλτι {int(MM.et.sum())} · μεσο γκολ σε αυτα {MM[MM.et].tot.mean():.3f}")
def fit(d, cols):
    X = np.column_stack([np.ones(len(d))] + [c(d) for c in cols])
    b, *_ = np.linalg.lstsq(X, d.tot.values.astype(float), rcond=None)
    res = d.tot.values - X @ b; s2 = res @ res / (len(d) - X.shape[1]); se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    return b, se
F_ = {'|diff|/100': lambda d: d['diff'].abs() / 100, 'KO': lambda d: d.ko.astype(float), 'κοντινο': lambda d: d.close.astype(float),
      'επιπεδο': lambda d: (d.R_h + d.R_a) / 200, 'NL': lambda d: (d.ctype == 'nl').astype(float), 'τουρνουα': lambda d: (d.ctype == 'tourn').astype(float)}
SPECS = {'Μ1 (intl_integrate, fit 2122-2425)': (FIT, ['|diff|/100', 'KO', 'κοντινο', 'NL', 'τουρνουα']),
         'ctx ολο το δειγμα 2122-2526': (np.ones(len(D), bool), ['|diff|/100', 'KO', 'κοντινο', 'NL', 'τουρνουα']),
         'live+επιπεδο ολο το δειγμα': (np.ones(len(D), bool), ['|diff|/100', 'KO', 'κοντινο', 'επιπεδο', 'NL', 'τουρνουα']),
         'live+επιπεδο, μονο O/U ματς': (D.ou_line.notna().values, ['|diff|/100', 'KO', 'κοντινο', 'επιπεδο', 'NL', 'τουρνουα'])}
for lab, (msk, cols) in SPECS.items():
    d = D[np.asarray(msk)].dropna(subset=['diff', 'R_h', 'R_a']); b, se = fit(d, [F_[c] for c in cols])
    P_(f'  OLS {lab:34s} n={len(d)}: σταθ {b[0]:+.2f} · ' + ' · '.join(f'{c} {b[i+1]:+.2f}(±{se[i+1]:.2f})' for i, c in enumerate(cols)))
# ---- τυφλη τσεπη over × KO (closing Crown, ιδια με intl_market_pockets: over της closing γραμμης) ----
def settle(total, line, odds):
    q = round(line * 4) / 4
    if abs(q * 2 - round(q * 2)) > 1e-9: return 0.5 * settle(total, q - .25, odds) + 0.5 * settle(total, q + .25, odds)
    return odds - 1 if total > q else (0.0 if abs(total - q) < 1e-9 else -1.0)
K = D[D.ko & D.ou_line.notna() & D.ou_o.notna()].copy()
K['p_over'] = [settle(int(t), float(l), float(o)) for t, l, o in zip(K.tot, K.ou_line, K.ou_o)]
K['p_under'] = [settle(-int(t), -float(l), float(o)) for t, l, o in zip(K.tot, K.ou_line, K.ou_u)]
for side in ('over', 'under'):
    p = K[f'p_{side}']; t = p.mean() / (p.std(ddof=1) / np.sqrt(len(p)))
    P_(f'  τυφλο {side} × KO (Crown closing): n={len(p)} ROI {p.mean()*100:+.1f}% t {t:+.1f} [' + ' '.join(f'{s}:{v*100:+.0f}' for s, v in p.groupby(K.season).mean().items()) + ']')
E = D[D.ko & D.et].merge(MM[['mid', 'hn', 'an']], on='mid', how='left')
P_('  KO με παραταση/πεναλτι στο δειγμα: ' + ' | '.join(f'{a}-{b} {s} {h}-{g} (O/U {l})' for a, b, s, h, g, l in zip(E.hn, E.an, E.season, E.hs, E['as'], E.ou_line)))
open('intl90_coef_' + os.environ.get('I90MODE', 'x') + '_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
