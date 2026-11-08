"""euro_dominance_buckets.py — 15/10/2026 (Στελιος: «αν και οι 2 εκτος top-5 ειναι φουσκωμενες, και vs top-5 η διορθωση λιγκας βγαινει σωστα,
ποτε ειναι το προβλημα;»). Ομαδες εκτος top-5, ολα τα ευρωπαικα 2223-2526: λαθος (πραγματικο − μοντελο, γκολ · + υποτιμαμε / − υπερτιμαμε)
ανα ΠΟΣΟ ΚΥΡΙΑΡΧΗ φαινεται η ομαδα στη λιγκα της (t), και ανα αντιπαλο (top-5 / εκτος).
"""
import sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
X = pd.read_pickle('euro_league_team_history_rows.pkl')
TOP5 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}
N = X[~X.lg.isin(TOP5)].copy(); N['opp5'] = N.opp_lg.isin(TOP5)
se = lambda v: v.dropna().std() / np.sqrt(max(v.notna().sum(), 1))
B = ((-9, .3, 'λιγο κυριαρχη (t <0.30)'), (.3, .6, 'μετρια (0.30-0.60)'), (.6, .9, 'κυριαρχη (0.60-0.90)'), (.9, 9, 'ΠΟΛΥ κυριαρχη (≥0.90)'))
for lab, m_ in (('ΟΛΟΙ οι αντιπαλοι', N.t.notna()), ('vs TOP-5', N.opp5), ('vs εκτος top-5', ~N.opp5)):
    print(f'\n{lab}')
    for lo, hi, l in B:
        x = N[m_ & (N.t >= lo) & (N.t < hi)]
        print(f'   {l:26s} n{len(x):4d} · λαθος μοντελου {x.r.mean():+.2f} ±{se(x.r):.2f} · xG-ισοπ. {x.rl.mean():+.2f} · λαθος αγορας {x.rk.mean():+.2f} ±{se(x.rk):.2f}')
    x = N[m_]
    print(f'   {"ΜΕΣΟΣ ΟΡΟΣ":26s} n{len(x):4d} · λαθος μοντελου {x.r.mean():+.2f} ±{se(x.r):.2f} · λαθος αγορας {x.rk.mean():+.2f}')
print('\nπαραδειγματα ομαδων ανα κατηγορια (συχνοτερες):')
for lo, hi, l in B:
    print(f'   {l:26s} ' + ', '.join(f'{k}' for k in N[(N.t >= lo) & (N.t < hi)].lg.value_counts().head(6).index))
