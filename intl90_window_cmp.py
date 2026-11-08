# -*- coding: utf-8 -*-
"""intl90_window_cmp.py — συγκριση παλιων (τελικο σκορ) vs νεων (90') bets του intl_window_test (live ρυθμιση: proper/dogold/TmixN12/deepfav),
Crown 72ω (και closing): OVER ολα / μονο KO / κοντινο-οχι-KO · συναινεση >=2/3 μοντελων · AH σε KO · 1Χ2 φαβ σε KO (intl_model_choice_v3, closing)."""
import sys, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
F = 'intl_window_test_proper_ahdogold_TmixN12_gddeepfav_bets.csv'
out = []
def P(s=''):
    print(s); out.append(s)
def st(g):
    if len(g) < 3: return f'n{len(g):4d}        —'
    s = g.groupby('season').pnl.mean(); t = g.pnl.mean() / (g.pnl.std(ddof=1) / math.sqrt(len(g))) if len(g) > 2 and g.pnl.std() > 0 else float('nan')
    return f'n{len(g):4d} {g.pnl.mean()*100:+6.1f}% t{t:+4.1f} {int((s > 0).sum())}/{s.size}'
B = {m: pd.read_csv(f'intl90_work/{m}/{F}', dtype={'mid': str, 'season': str}) for m in ('old', 'new')}
def cons(b):
    """συναινεση: >=2 απο τα 3 μοντελα δινουν ιδιο κανονα (OVER / ιδια πλευρα AH) στο ιδιο ματς· pnl = μεσος των μοντελων που συμφωνουν."""
    b = b.copy(); b['key'] = b.rule.where(b.rule == 'OVER', 'AH' + b.side.astype(str))
    g = b.groupby(['mid', 'key']).agg(season=('season', 'first'), ko=('ko', 'first'), close=('close', 'first'), rule=('rule', 'first'), nm=('model', 'nunique'), pnl=('pnl', 'mean')).reset_index()
    return g[g.nm >= 2]
for book in ('Crown', 'SBOBET'):
    for win in ('72ω', 'closing'):
        P(f'===== {book} · {win} · ROI παλιο (τελικο) → νεο (90′) =====')
        for lab, f in (('OVER ολα', lambda b: b.rule == 'OVER'), ('OVER μονο KO', lambda b: (b.rule == 'OVER') & b.ko),
                       ('OVER κοντινο, οχι KO', lambda b: (b.rule == 'OVER') & ~b.ko), ('AH ολα', lambda b: b.rule.str.startswith('AH')),
                       ('AH σε KO', lambda b: b.rule.str.startswith('AH') & b.ko)):
            cells = []
            for mdl in ('M1', 'M2', 'M3', 'ΣΥΝ'):
                o, n = B['old'], B['new']
                o = o[(o.book == book) & (o.win == win)]; n = n[(n.book == book) & (n.win == win)]
                if mdl == 'ΣΥΝ': o, n = cons(o), cons(n)
                else: o, n = o[o.model == mdl], n[n.model == mdl]
                cells.append(f'{mdl}: {st(o[f(o)])} → {st(n[f(n)])}')
            P(f'  {lab:22s} ' + ' | '.join(cells))
# ποια KO overs αλλαξαν αποτελεσμα (Crown 72ω, Μ3)
o = B['old']; n = B['new']
k = ['mid', 'model', 'book', 'win', 'rule']
X = o[(o.rule == 'OVER') & o.ko & (o.book == 'Crown') & (o.win == '72ω')].merge(n[(n.rule == 'OVER') & n.ko & (n.book == 'Crown') & (n.win == '72ω')], on=k, how='outer', suffixes=('_o', '_n'))
ch = X[(X.pnl_o.fillna(-9) != X.pnl_n.fillna(-9))]
P(f'\nCrown 72ω KO OVER bets που αλλαξαν (ολα τα μοντελα): {len(ch)} απο {len(X)}  · μοναδικα ματς {ch.mid.nunique()}')
open('intl90_window_cmp_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
