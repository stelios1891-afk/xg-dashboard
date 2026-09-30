"""
core7_fav15_threshold.py — ΤΕΣΤ 1/10/2026 (Στελιος: «να μπει κανονικα οπως τα αουτσαιντερ· το μονο ερωτημα ειναι το κατωφλι edge»).
Φαβορι 15+ (md≥14): γραμμη ≤ −0.5, αποδοση 1.70-2.10, μηχανη LIVE (σωστο SoS 0.75 @7-14, cur_0.75_6_13), αγκυρα .7, σωστα τεταρτα.
Κατωφλι edge ∈ {0, 2.5, 5, 7.5, 10, 12.5, 15, 20}%. Κλεισιμο Pinnacle (football-data) + Crown + Bet365 (Nowgoal).
ΠΡΟ-ΔΗΛΩΣΗ: το κατωφλι επιλεγεται με LOSO (απο τις αλλες 3 σεζον, κριτηριο μοναδες μεσος 3 βιβλιων).
  Αλλαζει απο το 10% (= κατωφλι των dogs) ΜΟΝΟ αν (α) το LOSO συνολο > LOSO του σταθερου 10% ΚΑΙ (β) το ιδιο κατωφλι
  επιλεγεται σε ≥3/4 folds. Αλλιως 10%. Πληροφοριακα: κοντες/βαθιες, ROI ανα ζωνη edge. Δεν αλλαζει τιποτα live.
"""
import sys, io, os, json, glob, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
src = open('core7_anchor_test.py', encoding='utf-8').read()
pre = src[:src.index('res = {}')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass')
g = {'__name__': 'f15'}
with contextlib.redirect_stdout(_Q()):
    exec(pre, g)
D, run, picks = g['D'], g['run'], g['picks']
key = ['league', 'season', 'h', 'a', 'date']
P = pd.read_csv('core7_mech_preds_cur_0.75_6_13.csv', dtype={'season': str, 'mid': str}); P['date'] = pd.to_datetime(P.date)
m = D[key].merge(P[['league', 'season', 'home_name', 'away_name', 'date', 'xg_h', 'xg_a', 'mid']],
                 left_on=key, right_on=['league', 'season', 'home_name', 'away_name', 'date'], how='left')
assert len(m) == len(D) and m.xg_h.notna().mean() > .99
D['xh'] = m.xg_h.clip(.05, 6).values; D['xa'] = m.xg_a.clip(.05, 6).values; D['mid'] = m.mid.values
S0, SA = run(0, 0), run(0.5, 0); T = (D.xh + D.xa).values; S7 = S0 + 0.7 * (SA - S0)
SEAS = sorted(D.season.unique())
def parse_line(gs):
    try:
        p = [float(x) for x in str(gs).split('/')]
        if len(p) == 2 and p[0] < 0: p[1] = -abs(p[1])
        return sum(p) / len(p)
    except Exception:
        return None
NG = {}
for f in glob.glob('nowgoal_odds/*.jsonl'):
    b = os.path.basename(f)
    if '_U' in b or '_deep' in b: continue
    for ln in open(f, encoding='utf-8'):
        try: r = json.loads(ln)
        except Exception: continue
        if r.get('cid') not in (3, 8) or not r.get('ah'): continue
        best = None
        for mt, u, gg, dn in r['ah']:
            gl = parse_line(gg)
            try: oh, oa = float(u) + 1, float(dn) + 1
            except (TypeError, ValueError): continue
            if gl is None or mt is None or oh <= 1 or oa <= 1: continue
            if best is None or mt > best[0]: best = (mt, -gl, oh, oa)
        if best: NG[(str(r['mid']), 'Crown' if r['cid'] == 3 else 'Bet365')] = best[1:]
def ev_ok(dist, side, ln, o):
    parts = [ln] if (ln * 4) % 2 == 0 else [ln - .25, ln + .25]; e = 0
    for L in parts:
        pw = sum(v for k, v in dist.items() if side * k + L > 0.01); pp = sum(v for k, v in dist.items() if abs(side * k + L) < 0.01)
        e += (pw * (o - 1) * (1 - picks.MARGIN) - (1 - pw - pp)) / len(parts)
    return e
rows = []
for i in np.where((D.md >= 14).values)[0]:
    r = D.loc[i]
    dist = picks.gd_dist_dom(max((T[i] + S7[i]) / 2, .05), max((T[i] - S7[i]) / 2, .05))
    for bk, q in (('Pinnacle', (r.L, r.ah, r.aa) if r.L == r.L else None), ('Crown', NG.get((r.mid, 'Crown'))), ('Bet365', NG.get((r.mid, 'Bet365')))):
        if q is None or q[0] != q[0] or abs(q[0]) < 0.5: continue
        L, oh, oa = q; side = 1 if L < 0 else -1; ud = -abs(L); o = oh if side == 1 else oa
        if not (1.70 <= o <= 2.10): continue
        rows.append(dict(book=bk, season=r.season, depth='κοντες' if ud > -1 else 'βαθιες', edge=ev_ok(dist, side, ud, o), pnl=picks.settle(r.gd, side, ud, o)))
B = pd.DataFrame(rows); BK = ('Pinnacle', 'Crown', 'Bet365')
THR = [0.0, 0.025, 0.05, 0.075, 0.10, 0.125, 0.15, 0.20]
def u(th, seas, depth=None):
    x = B[(B.edge >= th) & B.season.isin(seas)]
    if depth: x = x[x.depth == depth]
    return np.mean([x[x.book == bk].pnl.sum() for bk in BK])
def fm(x):
    if len(x) < 5: return f'n{len(x):4d}          —        '
    ps = x.groupby('season').pnl.mean()
    return f'n{len(x):4d} {100*x.pnl.mean():+6.1f}% {x.pnl.sum():+6.1f}u {int((ps > 0).sum())}/4'
print('ΦΑΒΟΡΙ 15+ ανα κατωφλι edge — Pinnacle | Crown | Bet365 · μεσος 3 βιβλιων (μοναδες, picks/σεζον)')
for th in THR:
    x = B[B.edge >= th]
    n_se = np.mean([len(x[x.book == bk]) for bk in BK]) / 4
    print(f'  ≥{100*th:4.1f}%  ' + ' | '.join(fm(x[x.book == bk]) for bk in BK) + f' · μεσος {u(th, SEAS):+6.1f}u ({n_se:.0f}/σεζον)')
print('\nανα σεζον (μεσος 3 βιβλιων, μοναδες)')
for th in THR:
    print(f'  ≥{100*th:4.1f}%  ' + ' '.join(f'{s}: {u(th, [s]):+5.1f}' for s in SEAS))
print('\nκοντες (−0.5/−0.75) | βαθιες (≤−1) — μεσος 3 βιβλιων')
for th in THR:
    print(f'  ≥{100*th:4.1f}%  κοντες {u(th, SEAS, "κοντες"):+6.1f}u · βαθιες {u(th, SEAS, "βαθιες"):+6.1f}u')
print('\nανα ΖΩΝΗ edge (οχι σωρευτικα) — μεσος 3 βιβλιων')
edges = THR + [9.9]
for lo, hi in zip(edges[:-1], edges[1:]):
    x = B[(B.edge >= lo) & (B.edge < hi)]
    print(f'  {100*lo:4.1f}-{100*hi if hi < 9 else 999:5.1f}%  ' + ' | '.join(fm(x[x.book == bk]) for bk in BK))
print('\nLOSO — κατωφλι απο τις αλλες 3 σεζον')
tot = tot10 = 0; chosen = []
for s in SEAS:
    oth = [x for x in SEAS if x != s]; th = max(THR, key=lambda t: u(t, oth)); chosen.append(th)
    tot += u(th, [s]); tot10 += u(0.10, [s])
    print(f'  {s}: διαλεγει ≥{100*th:.1f}% → {u(th, [s]):+5.1f}u (σταθερο 10%: {u(0.10, [s]):+5.1f}u)')
mode = max(set(chosen), key=chosen.count)
print(f'  ΣΥΝΟΛΟ LOSO {tot:+.1f}u vs σταθερο 10% {tot10:+.1f}u · πιο συχνη επιλογη ≥{100*mode:.1f}% ({chosen.count(mode)}/4)')
ch = tot > tot10 and chosen.count(mode) >= 3
print(f'\nΚΡΙΣΗ: {"ΑΛΛΑΖΕΙ σε ≥" + format(100*mode, ".1f") + "%" if ch else "ΜΕΝΕΙ 10%"}')

print(chr(10) + 'ΛΕΠΤΕΣ ΖΩΝΕΣ edge (1 μοναδα) — ολα τα βιβλια μαζι (picks, ROI, μοναδες μεσου βιβλιου, σεζον θετικες)')
for lo in np.arange(0.05, 0.20, 0.01):
    x = B[(B.edge >= lo) & (B.edge < lo + 0.01)]
    ps = x.groupby('season').pnl.mean()
    print(f'  {100*lo:4.0f}-{100*lo+1:3.0f}%  n{len(x):4d} ROI {100*x.pnl.mean():+6.1f}% · {x.pnl.sum()/3:+5.1f}u · {int((ps > 0).sum())}/4 · ±{100*x.pnl.std()/np.sqrt(max(len(x),1)):.0f}%')
x = B[B.edge >= 0.05]; c = np.corrcoef(x.edge, x.pnl)[0, 1]
print(f'  συσχετιση edge ↔ αποτελεσμα (edge ≥5%): {c:+.3f} (n{len(x)})')
