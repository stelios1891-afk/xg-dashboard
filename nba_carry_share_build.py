# -*- coding: utf-8 -*-
"""nba_carry_share_build.py — ΤΟΠΙΚΑ (θελει nba_player_games.csv): μεριδιο περσινων λεπτων που «εμειναν» ανα ομαδα → nba_carry_share.json
(20/10/2026, Στελιος «το 4 ... μπορουμε να το περασουμε»· nba_tests/t4_carry_roster: carry_ομαδας = 1.0·share^0.5, RMSE αγων 1-15 4/5, ROI Οκτ-Δεκ ιδιο).
share = Σ περσινα λεπτα ΣΤΗΝ ΙΔΙΑ ομαδα των παικτων του ρόστερ 1ου ματς / συνολο περσινων λεπτων ομαδας.
Γραφει: share για τις ιστορικες σεζον (ιδιος υπολογισμος με το τεστ) + prev_min = περσινα λεπτα ανα ομαδα/παικτη (κανονικοποιημενο ονομα)
για τη ΦΕΤΙΝΗ σεζον, ωστε το nba_refresh (cloud) να βγαζει το φετινο share απο το ρόστερ 1ου ματς (ESPN) ή το αναμενομενο ρόστερ."""
import os, sys, json, io, contextlib
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
ROOT = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
ns = {'__name__': 'x', '__file__': os.path.join(ROOT, 'nba_tests', 't4_carry_roster.py')}
src = open(os.path.join(ROOT, 'nba_tests', 't4_carry_roster.py'), encoding='utf-8').read()
src = src[:src.index('fit_mu = F.fit_mu')]
cwd = os.getcwd(); os.chdir(ROOT)
with contextlib.redirect_stdout(_B()):
    exec(compile(src, os.path.join(ROOT, 'nba_tests', 't4_carry_roster.py'), 'exec'), ns)
os.chdir(cwd)
SHARE = ns['SHARE']
from nba_absence import nk
MAP = {'BKN': 'BRK', 'CHA': 'CHO', 'PHX': 'PHO'}
P = pd.read_csv(os.path.join(ROOT, 'nba_player_games.csv'), usecols=['PLAYER_NAME', 'TEAM_ABBREVIATION', 'MIN', 'season', 'stype'], low_memory=False)
last = sorted(P.season.unique())[-1]                     # π.χ. '2025-26'
cur_end = int(last[:4]) + 2                              # 2027
p = P[(P.season == last) & (P.stype == 'RS')]
prev = {}
for (t, n), m in p.groupby(['TEAM_ABBREVIATION', 'PLAYER_NAME']).MIN.sum().items():
    prev.setdefault(MAP.get(t, t), {})[nk(n)] = round(float(m), 1)
out = dict(note='μεριδιο περσινων λεπτων που εμειναν (nba_carry_share_build.py)· live: carry_ομαδας = c0·share^pow μονο στο χαντικαπ',
           c0=1.0, pow=0.5, share={f'{s}|{t}': round(v, 4) for (s, t), v in SHARE.items()}, prev_season=last, prev_min={str(cur_end): prev})
json.dump(out, open(os.path.join(ROOT, 'nba_carry_share.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print(f'share ιστορικα: {len(SHARE)} ομαδες-σεζον · prev_min {cur_end}: {len(prev)} ομαδες ({last})')
