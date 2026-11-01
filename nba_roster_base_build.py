# -*- coding: utf-8 -*-
"""nba_roster_base_build.py — ΒΑΣΗ ΓΙΑ ΤΟ ΡΟΣΤΕΡ ΣΤΟ CLOUD (20/10/2026, Στελιος «ο,τι αλλαγη ειναι κανε την»).
Τρεχει ΤΟΠΙΚΑ μια φορα τον χρονο (θελει nba_player_games.csv, nba_rapm/, bbref_cache/) → nba_roster_base.json (committed).
Με αυτο το nba_live_roster.py τρεχει ΚΑΙ στο GitHub (μεσα στο nba_refresh) → το ρόστερ «1ο ματς» (W1, το τεσταρισμενο) εφαρμοζεται μονο του.
Αξια παικτη (ιδια με nba_roster_adj2 V0) + ΕΠΙΣΤΡΟΦΕΣ (roster_test 20/10, «INJ»): οποιος ΔΕΝ επαιξε περσι αλλα επαιξε ΠΡΟΠΕΡΣΙ → προπερσινη
  αξια & λεπτα/ματς (Haliburton, Lillard, Irving, VanVleet …) · αλλιως περσινη μαζεμενη × λεπτα/(λεπτα+500)· χωρις μετρησεις −1.
players: {ονομα(nk): [αξια, λεπτα/ματς, περσινα συνολικα λεπτα]} · old: {ομαδα: αξια περσινου ρόστερ (περσινα λεπτα στην ομαδα)}."""
import sys, json, io, contextlib
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
CUR = 2027                                   # ετος ληξης τρεχουσας σεζον (ετησια ενημερωση)
src = open('nba_roster_adj2.py', encoding='utf-8').read().split('OUT = {}')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
src = src.replace('for y in range(2020, 2026):', f'for y in range(2020, {CUR}):')
NS = {}
with contextlib.redirect_stdout(io.StringIO()): exec(src, NS)
A, MPT, GPT, shrunk = NS['A'], NS['MPT'], NS['GPT'], NS['shrunk']
def val(p):
    y = CUR - 2 if ((p, CUR - 1) not in MPT and (p, CUR - 2) in MPT) else CUR - 1
    v = shrunk(p, y); mpg = MPT[(p, y)] / GPT[(p, y)] if (p, y) in MPT else None
    return (v if v is not None else -1.0), (mpg if mpg is not None else 15.0)
players = {}
for k, p in A.drop_duplicates(['k', 'pid'])[['k', 'pid']].itertuples(index=False):
    if k and ((p, CUR - 1) in MPT or (p, CUR - 2) in MPT):
        v, mpg = val(p); players[k] = [round(float(v), 3), round(float(mpg), 2), round(float(MPT.get((p, CUR - 1), 0.0)), 1)]
prev = A[A.s == CUR - 1]; old = {}
for t in sorted(set(prev.team)):
    pt = prev[prev.team == t].groupby('pid').MIN.sum()
    old[t] = round(float(np.sum(5 * pt.values / pt.values.sum() * np.array([shrunk(p, CUR - 1) if shrunk(p, CUR - 1) is not None else -1.0 for p in pt.index]))), 4)
json.dump(dict(season=CUR, built='2026-10-20', note='αξια V0 + επιστροφες (προπερσινη αν 0′ περσι)· αγνωστοι −1 με 15′', players=players, old=old),
          open('nba_roster_base.json', 'w', encoding='utf-8'), ensure_ascii=False)
ret = [k for k, p in A.drop_duplicates(['k', 'pid'])[['k', 'pid']].itertuples(index=False) if (p, CUR - 1) not in MPT and (p, CUR - 2) in MPT]
print(f'nba_roster_base.json: {len(players)} παικτες · {len(old)} ομαδες · επιστροφες (προπερσινη αξια): {len(ret)} π.χ. ' +
      ', '.join(f'{k} {players[k][0]:+.2f}' for k in sorted(ret, key=lambda k: -players[k][0])[:6]))
