"""
core7_mech_anchor.py — 28/9/2026 (Στελιος: «αν κρατησουμε την αγκυρα και αφαιρεσουμε κατι που τα κραταει πισω;»). ΜΟΝΟ τεστ.
Για καθε εκδοχη μηχανης (core7_mech_preds_<v>.csv: σημερα / χωρις συμπιεση / πεναλτι 0.76 / και τα δυο / K=4) ΜΕ ΑΓΚΥΡΑ
(λ=0.5, διορθωσεις ομαδων προς closing AH απο ολα τα ματς, μεταφορα σεζον) × DRAW_BOOST {1.13, 1.00}:
μεροληψια φαβορι + picks φαβορι (≤−0.5) & dogs (≥+0.5) (1.70-2.10, edge≥10%, closing Pinnacle), αγωνιστικες 7-14 / 15+.
"""
import sys, io, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
src = open('core7_mech_eval.py', encoding='utf-8').read()
g = {'__name__': 'ma'}
with contextlib.redirect_stdout(_Q()):
    exec(src[:src.index('rows = []')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass'), g)
picks, ODDS, SM, VARS, LAB = g['picks'], g['ODDS'], g['SM'], g['VARS'], g['LAB']

def anchored(P, lam=0.5):
    P = P.sort_values(['league', 'date']).reset_index(drop=True); s_adj = np.zeros(len(P))
    for lg, idx in P.groupby('league').groups.items():
        off = {}
        for i in idx:
            r = P.loc[i]; s = r.s0 + off.get(r.home, 0.0) - off.get(r.away, 0.0); s_adj[i] = s
            if r.s_mkt == r.s_mkt:
                e = r.s_mkt - s; off[r.home] = off.get(r.home, 0.0) + lam * e / 2; off[r.away] = off.get(r.away, 0.0) - lam * e / 2
    P['s'] = s_adj; return P
rows = []
for v in VARS:
    P = pd.read_csv(f'core7_mech_preds_{v}.csv', dtype={'season': str}); P = P[P.gd.notna()].copy(); P['mid'] = P.mid.astype(str)
    P['date'] = pd.to_datetime(P.date); P['xh'] = P.xg_h.clip(.05, 6); P['xa'] = P.xg_a.clip(.05, 6)
    P['s0'] = P.xh - P.xa; P['T'] = P.xh + P.xa; P['s_mkt'] = P.mid.map(SM)
    for anc in (False, True):
        Q = anchored(P) if anc else P.assign(s=P.s0)
        Q = Q[Q.md >= 6]; M = Q[Q.s_mkt.notna()]
        sf = np.sign(M.s_mkt).replace(0, 1); bias = (sf * M.s - sf * M.gd).mean()
        for db in (1.13, 1.00):
            picks.DRAW_BOOST = db; bets = []
            for r in M.itertuples():
                L, ah, aa = ODDS[r.mid]; lh, la = max((r.T + r.s) / 2, .05), max((r.T - r.s) / 2, .05); dist = picks.gd_dist(lh, la)
                for side, ud, odds in ((1, L, ah), (-1, -L, aa)):
                    if abs(ud) < 0.5 or not (1.70 <= odds <= 2.10): continue
                    pw, pp = picks.p_cover(dist, side, ud)
                    if pw * (odds - 1) * (1 - picks.MARGIN) - (1 - pw - pp) >= 0.10:
                        bets.append(('fav' if ud < 0 else 'dog', '7-14' if r.md <= 13 else '15+', r.season, picks.settle(r.gd, side, ud, odds)))
            B = pd.DataFrame(bets, columns=['role', 'win', 'season', 'pnl'])
            res = dict(εκδοχη=LAB[v], αγκυρα='ΝΑΙ' if anc else 'οχι', DB=db, μεροληψια_φαβ=round(bias, 3))
            for role in ('fav', 'dog'):
                for win in ('7-14', '15+'):
                    d = B[(B.role == role) & (B.win == win)]; ps = d.groupby('season').pnl.mean()
                    res[f'{role} {win}'] = f"{len(d)} / {100*d.pnl.mean():+.1f}% / {d.pnl.sum():+.0f}u / {int((ps > 0).sum())}/4" if len(d) else '—'
            rows.append(res)
    print(f'{v} ok', flush=True)
picks.DRAW_BOOST = 1.13
T = pd.DataFrame(rows); pd.set_option('display.width', 300); pd.set_option('display.max_columns', 30)
print('\nΦΑΒΟΡΙ (≤−0.5) — n / ROI / μοναδες / θετικες σεζον')
print(T[['εκδοχη', 'αγκυρα', 'DB', 'μεροληψια_φαβ', 'fav 7-14', 'fav 15+']].to_string(index=False))
print('\nΑΟΥΤΣΑΙΝΤΕΡ (≥+0.5)')
print(T[['εκδοχη', 'αγκυρα', 'DB', 'dog 7-14', 'dog 15+']].to_string(index=False))
