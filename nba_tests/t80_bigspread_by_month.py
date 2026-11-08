# -*- coding: utf-8 -*-
"""t80_bigspread_by_month.py — ΠΕΡΙΓΡΑΦΙΚΟ (24/10/2026, Στελιος «στα χαντικαπ πανω απο 10 τον Οκτ-Δεκ δεν εμφανιζεται το ιδιο μοτιβο;»):
ανα περιοδο (Οκτ-Δεκ / Ιαν-Φεβ / Μαρ-Απρ) × |χαντικαπ| ≥10 / <10: πραγμ − γραμμη, τυφλο over, picks μοντελου (με/χωρις boost) over/under. Εξοδος: t80_*_out.txt"""
import os, sys
SC = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(SC, 't77_boost_picks.py'), encoding='utf-8').read().split("for thr in (10, 11):")[0]
exec(src)
a0 = pk('mu', O.asp == O.asp).merge(O[['i', 'asp', 'mon']], on='i'); a1 = pk('mu_σκα', O.asp == O.asp).merge(O[['i', 'asp', 'mon']], on='i')
PER = (('Οκτ-Δεκ', (10, 11, 12)), ('Ιαν-Φεβ', (1, 2)), ('Μαρ-Απρ', (3, 4)))
for lab, ms in PER:
    Q(f'\n=== {lab} ===')
    for zl, zm in (('|χαντ| ≥10', lambda d: d.asp >= 10), ('|χαντ| <10', lambda d: d.asp < 10)):
        x = O[O.mon.isin(ms) & zm(O)]
        bo = pd.DataFrame([(r['sea'], 'O', settle(r, 1), r['i']) for _, r in x.iterrows()], columns=['sea', 'side', 'u', 'i'])
        Q(f'  {zl}: ματς {len(x)} · πραγμ − γραμμη {(x.tot - x["T"]).mean():+.2f} · − μοντελο {x.rm.mean():+.2f}')
        Q(line('   τυφλο over', bo))
        for nm, A in (('picks χωρις boost', a0), ('picks με boost', a1)):
            y = A[A.mon.isin(ms) & zm(A)]
            Q(line(f'   {nm} ΟΛΑ', y)); Q(line(f'   {nm} OVER', y[y.side == 'OVER'])); Q(line(f'   {nm} UNDER', y[y.side == 'UNDER']))
open(os.path.join(SC, 't80_bigspread_by_month_out.txt'), 'w', encoding='utf-8').write('\n'.join(out2))
