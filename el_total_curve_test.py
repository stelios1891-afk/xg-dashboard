# -*- coding: utf-8 -*-
"""el_total_curve_test.py — ΚΑΜΠΥΛΗ ΣΚΟΡ ΜΕΣΑ ΣΤΗ ΣΕΖΟΝ (25/9/2026, αιτημα Στελιου «δοκιμασε το 1»).
Ευρημα: τα σκορ ανεβαινουν ~7 π. μεσα στη σεζον (αγων 1-3 ≈159 → 26+ ≈166)· αγορα και μοντελο ακολουθουν μισα.
Το live (V1) προσθετει ΣΤΑΘΕΡΑ +1.1 (παρατασεις) → αγων 1-3 μοντελο 2 π. ψηλα, 26+ 2 π. χαμηλα.
ΠΑΡΑΛΛΑΓΕΣ (αντικαθιστουν το +1.1· ολες LOSO: μετρημενες μονο απο τις αλλες σεζον, κανονικη περιοδος):
  Κ1 «σκαλοπατια»: διορθωση = μεσο (πραγματικο − v2) ανα μπλοκ αγωνιστικων 1-3 / 4-6 / 7-10 / 11-17 / 18-25 / 26+
  Κ2 «ευθεια»:     διορθωση = a + b·αγωνιστικη
ΠΡΟ-ΔΗΛΩΜΕΝΑ ΚΡΙΤΗΡΙΑ (ΜΙΑ εκτελεση) — περνα αν σε σχεση με το live (V1):
  (α) RMSE συνολου χαμηλοτερο συνολικα ΚΑΙ σε ≥4/6 σεζον
  (β) κλιση b οχι χαμηλοτερη απο live − 0.02
  (γ) ROI συνολων edge ≥8% ΚΑΙ ≥10% μεγαλυτερο, κερδοφορες σεζον οχι λιγοτερες
Αν περασουν και οι δυο: αυτη με το μεγαλυτερο μεσο ROI (≥8%, ≥10%). Εξοδος: el_total_curve_test_out.txt"""
import sys, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
_o = []
src = open('el_total_level_test.py', encoding='utf-8').read().split("res = {}")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src)
out = _o
def P(s=''):
    print(s, flush=True); out.append(str(s))

rs_all = D[D.phase == 'RS'].sort_values('date'); cnt, gno = {}, {}
for i, r in rs_all.iterrows():
    for t in (r.home, r.away): cnt[(r.season, t)] = cnt.get((r.season, t), 0) + 1
    gno[i] = max(cnt[(r.season, r.home)], cnt[(r.season, r.away)])
RND = np.array([gno.get(i, 99) for i in IDX]).astype(float)
BLOCKS = [(1, 3), (4, 6), (7, 10), (11, 17), (18, 25), (26, 99)]
def blk(r): return next(i for i, (a, b) in enumerate(BLOCKS) if a <= r <= b)
BI = np.array([blk(r) for r in RND])
RES = TOT - T_LO                                           # πραγματικο − v2 (χωρις παρατασεις)
C1 = np.array(T_LO, float); C2 = np.array(T_LO, float); fits = []
for s in SS:
    tr = RS & (SE != s) & np.isin(SE, SS); te = SE == s
    off = {b: RES[tr & (BI == b)].mean() for b in range(len(BLOCKS))}
    C1[te] += np.array([off[b] for b in BI[te]])
    a, bb = np.polyfit(RND[tr], RES[tr], 1)[::-1]
    C2[te] += a + bb * RND[te]
    fits.append((s, off, a, bb))
VARS = {'live (σταθερο +1.1)': VAR['V1'], 'Κ1 σκαλοπατια': C1, 'Κ2 ευθεια': C2}
off_all = {b: RES[RS & (BI == b)].mean() for b in range(len(BLOCKS))}
a_all, b_all = np.polyfit(RND[RS], RES[RS], 1)[::-1]
P('διορθωση (ολες οι σεζον, για αναφορα): Κ1 ' + ' · '.join(f'{a}-{b if b < 99 else "+"}: {off_all[i]:+.1f}' for i, (a, b) in enumerate(BLOCKS))
  + f' | Κ2: {a_all:+.2f} {b_all:+.3f}×αγων (αγων 1 → {a_all + b_all:+.1f}, αγων 34 → {a_all + 34 * b_all:+.1f})')
P('')
P('=== ΜΕΣΗ ΜΕΡΟΛΗΨΙΑ (πραγμ − μοντελο) ανα μπλοκ, κανονικη περιοδος ===')
P(f'{"":22s} ' + ' '.join(f'{f"{a}-{b if b < 99 else chr(43)}":>7s}' for a, b in BLOCKS))
for k, v in VARS.items():
    P(f'{k:22s} ' + ' '.join(f'{np.mean((TOT - v)[RS & (BI == i)]):+7.1f}' for i in range(len(BLOCKS))))
P('')
res = {}
P('=== (α) RMSE συνολου ανα σεζον ===')
for k, v in VARS.items():
    per = {s: np.sqrt(np.mean((TOT - v)[RS & (SE == s)] ** 2)) for s in SS}
    res[k] = dict(rmse=np.sqrt(np.mean((TOT - v)[RS & np.isin(SE, SS)] ** 2)), per=per)
    P(f'  {k:22s} ολο {res[k]["rmse"]:.3f} | ' + ' '.join(f'{s[-2:]}:{per[s]:.2f}' for s in SS))
P('')
P('=== (β) κλιση b (πραγμ − closing πανω στο μοντελο − closing) ===')
for k, v in VARS.items():
    m = RS & np.isin(SE, SS); res[k]['b'] = np.polyfit((v - MT)[m], (TOT - MT)[m], 1)[0]
    P(f'  {k:22s} b {res[k]["b"]:+.3f}')
P('')
P('=== (γ) ROI ΣΥΝΟΛΩΝ (Pinnacle closing) ===')
jj = [j for j in range(len(IDX)) if RS[j] and not np.isnan(PRC[j, 0])]
for k, v in VARS.items():
    bt = tot_bets(v); bt['rnd'] = RND[jj]
    res[k]['bets'] = bt
    for thr in (0.05, 0.08, 0.10, 0.15):
        g = bt[bt.edge >= thr]; pos = sum(1 for s in SS if len(g[g.season == s]) and g[g.season == s].p.mean() > 0)
        res[k][thr] = (g.p.mean() * 100, pos)
        sides = ' · '.join(f'{r_} {g[g.role == r_].p.mean()*100:+.1f}% ({(g.role == r_).sum()})' for r_ in ('over', 'under'))
        P(f'  {k:22s} ≥{thr*100:2.0f}%: {g.p.mean()*100:+5.1f}% ({len(g)}, {g.p.sum():+.1f}u) {pos}/6 | {sides}')
    P('')
P('=== ΑΝΑ ΠΕΡΙΟΔΟ (edge ≥8%): over / under ===')
for k in VARS:
    bt = res[k]['bets']; bt = bt[bt.edge >= 0.08]; cells = []
    for lab, lo, hi in (('1-6', 1, 6), ('7-10', 7, 10), ('11+', 11, 99)):
        x = bt[(bt.rnd >= lo) & (bt.rnd <= hi)]
        cells.append(f'{lab}: over {x[x.role == "over"].p.mean()*100:+.1f}% ({(x.role == "over").sum()}) · under {x[x.role == "under"].p.mean()*100:+.1f}% ({(x.role == "under").sum()})')
    P(f'  {k:22s} ' + ' | '.join(cells))
P('')
P('=== ΚΡΙΤΗΡΙΑ ===')
base = res['live (σταθερο +1.1)']; passed = []
for k in ('Κ1 σκαλοπατια', 'Κ2 ευθεια'):
    r = res[k]
    a_ = r['rmse'] < base['rmse'] and sum(r['per'][s] < base['per'][s] for s in SS) >= 4
    b_ = r['b'] >= base['b'] - 0.02
    c_ = all(r[t][0] > base[t][0] and r[t][1] >= base[t][1] for t in (0.08, 0.10))
    P(f'  {k:18s} (α) {"✓" if a_ else "✗"} ({sum(r["per"][s] < base["per"][s] for s in SS)}/6)  (β) {"✓" if b_ else "✗"}  (γ) {"✓" if c_ else "✗"}')
    if a_ and b_ and c_: passed.append(k)
if passed:
    best = max(passed, key=lambda k: res[k][0.08][0] + res[k][0.10][0]); P(f'→ ΠΕΡΝΑ: {best}')
else:
    P('→ ΚΑΜΙΑ δεν περνα· μενει το live')
open('el_total_curve_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
