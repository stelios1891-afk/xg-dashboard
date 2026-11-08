"""
intl_over_nonclose_dive.py — ΔΙΕΡΕΥΝΗΣΗ: over σε ΜΗ κοντινα ματς (οχι κοντινο, οχι νοκ-αουτ) με το νεο T (26/9/2026, Στελιος: «ηταν με 8%;
μεγαλυτερο κατωφλι; που ειναι η αδυναμια — τεραστιο φαβορι, μεγαλες γραμμες 4.5/5;»). ΠΕΡΙΓΡΑΦΙΚΟ (οχι κανονας): συναινεση 72ω,
Crown/SBOBET μεσος, απο intl_window_test_proper_ahhybrid_overall_TmixN12_gddeepfav_bets.csv.
"""
import sys, os, contextlib, numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0, '.')
src = open('intl_model_choice_v3.py', encoding='utf-8').read(); G = {'__name__': 'dv'}
with contextlib.redirect_stdout(open(os.devnull, 'w', encoding='utf-8')):
    exec(src[:src.index('bets = []')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass'), G)
D = G['D'][['mid', 'd_M1', 'gd', 'tot', 'hs', 'as']].copy(); D['mid'] = D.mid.astype(str)
b = pd.read_csv('intl_window_test_proper_ahhybrid_overall_TmixN12_gddeepfav_bets.csv', dtype={'mid': str, 'season': str})
b = b[(b.win == '72ω') & b.model.isin(['M1', 'M2', 'M3']) & (b.rule == 'OVER')]
C = pd.DataFrame([g.sort_values('hours').iloc[0].to_dict() for _, g in b.groupby(['book', 'mid']) if g.model.nunique() >= 2])
C = C.merge(D, on='mid', how='left'); C['nc'] = ~C.close.astype(bool) & ~C.ko.astype(bool)
C['fav'] = C.d_M1.abs()                  # δυναμη φαβορι (Elo διαφορα Μ1)
C['fav_goals'] = np.where(C.d_M1 >= 0, C.hs, C['as']); C['dog_goals'] = np.where(C.d_M1 >= 0, C['as'], C.hs)
out = []
def P(s=''):
    print(s, flush=True); out.append(s)
def cell(x):
    c, s = x[x.book == 'Crown'], x[x.book == 'SBOBET']
    if len(c) < 8 or len(s) < 8: return f'— (n~{(len(c) + len(s)) // 2})'
    cy = x.groupby('season').pnl.mean()
    return f"{(c.pnl.mean() + s.pnl.mean()) / 2 * 100:+6.1f}% (n~{(len(c) + len(s)) // 2}, {int((cy > 0).sum())}/{cy.size}){' ⚠' if (c.pnl.mean() > 0) != (s.pnl.mean() > 0) else ''}"
N = C[C.nc]; K = C[~C.nc]
P(f'OVER ΣΥΝΑΙΝΕΣΗΣ, ΝΕΟ T — μη κοντινα: {cell(N)} · κοντινα/KO: {cell(K)}')
P('\n1) ΚΑΤΩΦΛΙ EDGE (μη κοντινα)')
for lo in (.08, .12, .16, .20, .25):
    P(f'   edge ≥{lo * 100:.0f}%: {cell(N[N.edge >= lo])}')
P('\n2) ΥΨΟΣ ΓΡΑΜΜΗΣ (μη κοντινα)')
for lab, f in (('≤2.25', N.line <= 2.25), ('2.5-2.75', (N.line >= 2.5) & (N.line <= 2.75)), ('3-3.25', (N.line >= 3) & (N.line <= 3.25)), ('≥3.5', N.line >= 3.5)):
    P(f'   γραμμη {lab:9s}: {cell(N[f])}')
P('\n3) ΔΥΝΑΜΗ ΦΑΒΟΡΙ (Elo διαφορα, μη κοντινα)')
for lab, f in (('150-250', N.fav < 250), ('250-400', (N.fav >= 250) & (N.fav < 400)), ('400-600', (N.fav >= 400) & (N.fav < 600)), ('≥600', N.fav >= 600)):
    x = N[f]; P(f'   {lab:8s}: {cell(x)} · μεσα γκολ {x.tot.mean():.2f} vs γραμμη {x.line.mean():.2f} · φαβ {x.fav_goals.mean():.2f} / αουτσ {x.dog_goals.mean():.2f}')
P('\n4) ΠΟΥ ΧΑΝΕΙ: κατανομη συνολου γκολ στα μη κοντινα over (συναινεση, Crown)')
x = N[N.book == 'Crown']
P('   ' + ' · '.join(f'{k} γκολ: {(x.tot == k).mean() * 100:.0f}%' for k in range(0, 7)) + f' · 7+: {(x.tot >= 7).mean() * 100:.0f}%')
P(f'   φαβορι σκοραρει: 0 γκολ {(x.fav_goals == 0).mean() * 100:.0f}% · 1 {(x.fav_goals == 1).mean() * 100:.0f}% · 2 {(x.fav_goals == 2).mean() * 100:.0f}% · 3+ {(x.fav_goals >= 3).mean() * 100:.0f}% · αουτσαιντερ σκοραρει ≥1: {(x.dog_goals >= 1).mean() * 100:.0f}%')
y = K[K.book == 'Crown']
P(f'   (κοντινα για συγκριση: 0-1 γκολ {(y.tot <= 1).mean() * 100:.0f}% · μη κοντινα 0-1 γκολ {(x.tot <= 1).mean() * 100:.0f}%)')
open('intl_over_nonclose_dive_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
