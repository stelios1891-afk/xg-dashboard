"""core7_totals_gap_now.py — 15/10/2026 (Στελιος: «ποσα γκολ πιο κατω απο την αγορα προβλεπαμε τοτε; πως συγκρινεται με το 0.37;»).
Φετος (2627): μοντελο (παγωμενη προ-αγωνα προβλεψη, match_projections_archive) vs αγορα (Pinnacle κλεισιμο συνολου, odds_history) vs πραγματικα,
στα ΙΔΙΑ ματς, ανα λιγκα και αγωνιστικη 1-6 / 7+. Ιστορικο (2223-2526, Crown κλεισιμο) απο core7_goals_gap_rows για συγκριση."""
import sys
_s = open('core7_totals_2627_run.py', encoding='utf-8').read(); exec(_s[:_s.index('rows.sort(')])
import pandas as pd
out = []
for r in rows:
    if r['tg'] is None or not r['seq']: continue
    pre = [x for x in r['seq'] if x[0] <= r['ko'] + dt.timedelta(minutes=15)]
    if not pre: continue
    L, o, u = pre[-1][1][:3]
    s = r['hx'] - r['ax']
    out.append(dict(lg=r['lg'], gw=r['gw'], mod=r['hx'] + r['ax'], mkt=t_mkt(L, o, u, s), tg=r['tg']))
X = pd.DataFrame(out)
def line(y, lab):
    return f'   {lab:22s} n{len(y):4d} │ πραγμ {y.tg.mean():.2f} · μοντελο {y["mod"].mean():.2f} · αγορα {y.mkt.mean():.2f} │ μοντ−αγορα {(y["mod"] - y.mkt).mean():+.2f} · μοντ−πραγμ {(y["mod"] - y.tg).mean():+.2f} · αγορα−πραγμ {(y.mkt - y.tg).mean():+.2f}'
TOP5 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}
print('ΦΕΤΟΣ 2026-27 (ματς με σκορ και κλεισιμο Pinnacle, απο 13/9)')
print(line(X, 'CORE7 ολα'))
print(line(X[X.lg.isin(TOP5)], 'top-5 ολα'))
print(line(X[X.gw >= 7], 'CORE7 αγων. 7+'))
print(line(X[X.gw < 7], 'CORE7 αγων. 1-6'))
for lg in sorted(X.lg.unique()): print(line(X[X.lg == lg], lg))
W = pd.read_csv('core7_goals_gap_rows.csv', dtype={'season': str})
print('ΙΣΤΟΡΙΚΟ 2223-2526 (Crown κλεισιμο, αγων. 7+)')
for lab, m in (('CORE7', W.league.notna()), ('top-5', W.league.isin(TOP5))):
    y = W[m & (W.md >= 6) & W.T_mkt.notna()].rename(columns={'T_mod': 'mod', 'T_mkt': 'mkt'})
    print(line(y, lab))
