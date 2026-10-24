# -*- coding: utf-8 -*-
"""t78_picks_by_spread.py — ΠΕΡΙΓΡΑΦΙΚΟ (24/10/2026, Στελιος «μηπως να δουμε και under οταν ειναι κλειστα τα ματς;»): picks μοντελου συνολων
(χωρις boost, ανοιγμα Crown, σ 18, edge ≥8%) ανα |χαντικαπ| × OVER/UNDER + τυφλο under ανα |χαντικαπ|. Εξοδος: t78_picks_by_spread_out.txt"""
import os, sys
SC = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(SC, 't77_boost_picks.py'), encoding='utf-8').read().split("for thr in (10, 11):")[0].replace("'t75_totals_spread_boost.py'", "'t75_totals_spread_boost.py'")
exec(src)
BINS = ((0, 1.5), (1.5, 3), (3, 6), (6, 10), (10, 99))
a = pk('mu', O.asp == O.asp); a = a.merge(O[['i', 'asp']], on='i')
Q('=== PICKS ΜΟΝΤΕΛΟΥ (≥8%) ανα |χαντικαπ| ===')
for lo, hi in BINS:
    for side in ('OVER', 'UNDER'):
        d = a[(a.asp >= lo) & (a.asp < hi) & (a.side == side)]
        Q(line(f'|δ| {lo}-{hi} {side}', d))
Q('\n=== ΤΥΦΛΟ UNDER ανα |χαντικαπ| (ολα τα ματς) ===')
for lo, hi in BINS:
    x = O[(O.asp >= lo) & (O.asp < hi)]
    d = pd.DataFrame([(r['sea'], 'U', settle(r, -1), r['i']) for _, r in x.iterrows()], columns=['sea', 'side', 'u', 'i'])
    Q(line(f'|δ| {lo}-{hi} τυφλο under', d) + f' · under {100 * (x.tot < x["T"]).mean():.1f}%')
Q('\n=== |χαντικαπ| ≤3: UNDER οταν και το μοντελο λεει under (μ < γραμμη / κατα ≥3 π.) ===')
x = O[O.asp <= 3]
for lab, m in (('μοντελο under', x.mu < x['T']), ('μοντελο under ≥3 π.', x.mu <= x['T'] - 3), ('μοντελο over', x.mu > x['T'])):
    y = x[m]; d = pd.DataFrame([(r['sea'], 'U', settle(r, -1), r['i']) for _, r in y.iterrows()], columns=['sea', 'side', 'u', 'i'])
    Q(line(f'{lab} → under', d) + f' · under {100 * (y.tot < y["T"]).mean():.1f}%')
open(os.path.join(SC, 't78_picks_by_spread_out.txt'), 'w', encoding='utf-8').write('\n'.join(out2))
