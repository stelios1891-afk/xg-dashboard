"""southam_t2_totals.py — 5/10/2026 ΟΜΑΔΑ 2: ΕΠΙΠΕΔΟ ΓΚΟΛ / ΣΥΝΟΛΑ. Η υπεροχη μενει της βασης· αλλαζει μονο το συνολο.
Παραλλαγες: (α) κυλιομενος συντελεστης πραγματικα/μοντελο των προηγουμενων N ματς (N 150/300/600/1000)
(β) αλλη μιξη xG/γκολ ΜΟΝΟ για το συνολο (0.4 / 0.8 / 1.0· βαση 0.6) (γ) συνδυασμοι. Κυριο μετρο: Tg & Tx (+ Tm)."""
import sys, numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import southam_tune as T
base = T.run()
V = {}
def add(nm, P, conv=0): V[nm] = T.evaluate(P, conv=conv).set_index('mid')
add('βαση', base)
for N in (150, 300, 600, 1000): add(f'συντελ. N{N}', base, N)
for b in (0.4, 0.8, 1.0): add(f'συνολο μιξη {b}', T.split_run({}, {'blend': b}))
for b in (0.4, 0.8): add(f'μιξη {b}+N300', T.split_run({}, {'blend': b}), 300)
add('συνολο χωρις ραμπα', T.split_run({}, {'ramp': False}))
add('συνολο decay .99', T.split_run({}, {'decay': 0.99}))
B = V['βαση']
for lg in ('Brazil', 'MLS'):
    b = B[B.league == lg]; seas = sorted(b.season.unique())
    print(f'\n[{lg}] Δ×1000 (αρνητικο = καλυτερο) [σεζον καλυτερες] · μεσο λαθος συνολου (πραγματικα − μοντελο) ανα σεζον')
    for nm, E in V.items():
        e = E[E.league == lg]; row = []
        for m in ('Tg', 'Tx', 'Tm', 'LL'):
            d = (e[m] - b[m]).dropna(); bs = sum(1 for s in seas if d[e.loc[d.index, 'season'] == s].mean() < 0)
            row.append(f'{m} {1000*d.mean():+6.2f}±{1000*d.std()/np.sqrt(len(d)):4.2f}[{bs}/{len(seas)}]')
        print(f'  {nm:20s} ' + '  '.join(row))
    for m in ('Tg', 'Tx'):
        per = {nm: E[E.league == lg].groupby('season')[m].mean() for nm, E in V.items()}
        gains = []; ch = []
        for s in seas:
            best = min(per, key=lambda nm: np.mean([per[nm][o] for o in seas if o != s])); ch.append(best); gains.append(per[best][s] - per['βαση'][s])
        print(f'  LOSO [{m}]: ' + ' · '.join(f'{s}→{c}' for s, c in zip(seas, ch)) + ' · κερδος εκτος: ' + ' '.join(f'{1000*g:+.1f}' for g in gains) + f' · {sum(g < 0 for g in gains)}/{len(gains)}')
# bias ανα σεζον
P = base[(base.stage == 'regular') & (base.md >= 7)]
print('\nμεσο (πραγματικα γκολ − μοντελο) / (πραγματικο xG − μοντελο) ανα σεζον:')
for lg in ('Brazil', 'MLS'):
    g = P[P.league == lg]
    print(f'  {lg}: ' + ' '.join(f'{s}: {(x.hg + x.ag - x.lh - x.la).mean():+.2f}/{(x.hx + x.ax - x.lh - x.la).mean():+.2f}' for s, x in g.groupby('season')))
