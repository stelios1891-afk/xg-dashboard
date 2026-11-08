# -*- coding: utf-8 -*-
"""core7_live_replay.py — 21/10/2026: ΠΙΣΤΗ αναπαραγωγη της ΣΗΜΕΡΙΝΗΣ live μηχανης εγχωριων για backtests (Στελιος: «χρησιμοποιησες την ιδια
ακριβως μηχανη με το live;»).
  μηχανη = core7_mech_preds_cur_0.75_6_13~emps.csv (= live: K=8, ραμπα 100→60/40, SoS 0.75 @7-14, κοκκινες εμπειρικες 5/10)
  + ΑΓΚΥΡΑ κοντων γραμμων (core7_anchor.py): offsets ανα ομαδα, μαθαινουν απο το κλεισιμο Pinnacle (football-data AHCh/PCAHH/PCAHA)
    σε αγων. 7+ (λ=0.5, μηδενισμος καθε σεζον), εφαρμογη ΜΟΝΟ αγων. 15+ και |γραμμη| ∈ {0.5, 0.75}: s' = s_μοντελου + o_h − o_a, συνολο ιδιο.
Εξοδος: core7_live_replay.csv (mid, md, xg_h, xg_a, off_s = o_h − o_a ΠΡΟ-αγωνα). Χρηση: xg για κοντες γραμμες 15+ → anchored(r)."""
import os, sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
ENGINE = 'core7_mech_preds_cur_0.75_6_13~emps.csv'
os.environ['CORE7_PREDS'] = ENGINE
src = open('core7_anchor_test.py', encoding='utf-8').read()
pre = src[:src.index('def run(lam, carry):')]
assert 'rows.append(dict(league=r.league,' in pre
pre = pre.replace('rows.append(dict(league=r.league,', "rows.append(dict(mid=str(r['mid']), league=r.league,")
g = {'__name__': 'replay'}
exec(pre, g)
D = g['D']
LAM, LEARN_MD = 0.5, 7
off_s = np.zeros(len(D))
for lg, idx in D.groupby('league').groups.items():
    off = {}; cur = None
    for i in idx:
        r = D.loc[i]
        if r.season != cur: off = {}; cur = r.season
        o = off.get(r.h, 0.0) - off.get(r.a, 0.0); off_s[i] = o
        if r.md >= LEARN_MD and r.s_mkt == r.s_mkt:
            e = r.s_mkt - ((r.xh - r.xa) + o); off[r.h] = off.get(r.h, 0.0) + LAM * e / 2; off[r.a] = off.get(r.a, 0.0) - LAM * e / 2
D['off_s'] = off_s
out = D[['mid', 'league', 'season', 'md', 'xh', 'xa', 'off_s', 'L', 'ah', 'aa', 'gd']].rename(columns={'xh': 'xg_h', 'xa': 'xg_a'})
out.to_csv('core7_live_replay.csv', index=False)
print(f'core7_live_replay.csv: {len(out)} ματς · |offset| μεσο στις 15+: {out[out.md >= 15].off_s.abs().mean():.3f}')


def anchored(xg_h, xg_a, off, md, line_abs):
    """xg που βλεπει το live για ΑΥΤΗ τη γραμμη (αγκυρα μονο 15+ & κοντες)."""
    if md >= 15 and round(line_abs, 2) in (0.5, 0.75):
        T = xg_h + xg_a; s = (xg_h - xg_a) + off
        return max((T + s) / 2, .05), max((T - s) / 2, .05)
    return xg_h, xg_a
