# -*- coding: utf-8 -*-
"""el_moneyline_test.py — ΝΙΚΗΤΗΣ ΑΓΩΝΑ (1-2) Ευρωλιγκας (1/10/2026, Στελιος «τρεξε και νικητη»).
Τιμες: nowgoal_el/ml.jsonl (Crown cid 3 · Bet365 cid 8, καθε αλλαγη, ωρα +8) · μοντελο: live (h_new) → P(νικη γηπ) = Φ(διαφορα / 11.5).
1. ΑΓΟΡΑ: βαθμονομηση ανα ζωνη αποδοσης (κλεισιμο Crown): πραγματικο % νικης vs τιμη (χωρις γκανιοτα) · ROI «στα τυφλα» — υπαρχει
   «ακριβο αουτσαιντερ» (favourite-longshot bias);
2. ΜΟΝΤΕΛΟ: βαθμονομηση των πιθανοτητων νικης μας · log-loss μοντελο vs αγορα.
3. PICKS 1-2: alert (πρωτη τιμη Crown με edge ≥8%, οχι στο τελευταιο 2ωρο οπως το χαντικαπ) — ROI/μοναδες ανα ζωνη αποδοσης, φαβορι/αουτσαιντερ, ανα σεζον.
4. ΣΥΓΚΡΙΣΗ ΜΕ ΧΑΝΤΙΚΑΠ στα ιδια ματς (τι ΠΡΟΣΘΕΤΕΙ το 1-2): ματς με pick 1-2 ΚΑΙ χαντικαπ ιδιας πλευρας / μονο 1-2 / αντιθετη πλευρα.
ΚΡΙΤΗΡΙΟ (δηλωμενο): 1-2 στα picks μονο αν θετικο ROI σε ≥4/5 σεζον ΚΑΙ επιπλεον μοναδες πανω απο το χαντικαπ στα ιδια ματς.
Εξοδος: el_moneyline_test_out.txt"""
import sys, json, math
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
NS = {}
exec(open('el_alert_types.py', encoding='utf-8').read().split('ZZ = {}')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", ''), NS)
D, REC, PR, key, pick, settle, SE5, ACT, LT = (NS[k] for k in ('D', 'REC', 'PR', 'key', 'pick', 'settle', 'SE5', 'ACT', 'LT'))
mapping = LT['mapping']
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))
Phi = NormalDist().cdf; SM = 11.5
ML = {}
for ln in open('nowgoal_el/ml.jsonl', encoding='utf-8'):
    r = json.loads(ln); ML[(r['ngid'], r['cid'])] = r['rows']
G = []
for ng, (i, swap) in mapping.items():
    pos = D.index.get_loc(i)
    if D.phase.values[pos] != 'RS' or D.season.values[pos] not in SE5: continue
    tip = pd.Timestamp(D.t.values[pos]); tip = (tip.tz_localize('UTC') if tip.tzinfo is None else tip).timestamp()
    m = PR.get(key(pos), {}).get('h_new')
    if m is None or not np.isfinite(m): continue
    rec = dict(pos=pos, sea=D.season.values[pos], tip=tip, m=m, act=ACT[pos])
    for cid, nm in ((3, 'c'), (8, 'b')):
        rows = [(x[0] + 8 * 3600, x[1], x[2]) for x in sorted(ML.get((ng, cid), []), key=lambda x: x[0]) if x[1] and x[2] and x[1] > 1 and x[2] > 1]
        rows = [(t, (g if swap else h), (h if swap else g)) for t, h, g in rows if t <= tip + 300]
        rec[nm] = rows
    if rec['c']: G.append(rec)
P(f'ματς με τιμες νικητη Crown (RS E2021-25): {len(G)} · με Bet365: {sum(1 for g in G if g["b"])}')
def devig(h, a): ph = (1 / h) / (1 / h + 1 / a); return ph
# ---- 1. αγορα ----
P(''); P('=== 1. ΑΓΟΡΑ (κλεισιμο Crown): πραγματικο % νικης vs τιμη (χωρις γκανιοτα) · ROI αν επαιζες ΟΛΑ στα τυφλα ===')
L = []
for g in G:
    t, h, a = g['c'][-1]; ph = devig(h, a); hw = g['act'] > 0
    L.append(dict(sea=g['sea'], od=h, p=ph, win=hw)); L.append(dict(sea=g['sea'], od=a, p=1 - ph, win=not hw))
Z = pd.DataFrame(L)
for lo, hi in ((1.0, 1.25), (1.25, 1.5), (1.5, 1.8), (1.8, 2.2), (2.2, 3.0), (3.0, 4.5), (4.5, 7.0), (7.0, 99)):
    x = Z[(Z.od >= lo) & (Z.od < hi)]
    if len(x) < 10: continue
    roi = np.where(x.win, x.od - 1, -1).mean()
    pos = sum(1 for s in SE5 if (x.sea == s).any() and np.where(x[x.sea == s].win, x[x.sea == s].od - 1, -1).mean() > 0)
    P(f'  αποδοση {lo:4.2f}-{hi if hi < 99 else "+":>5}: n {len(x):4d} · νικες {x.win.mean():5.1%} · τιμη λεει {x.p.mean():5.1%} · διαφορα {100*(x.win.mean()-x.p.mean()):+5.1f} μον.% · ROI τυφλα {roi*100:+6.1f}% ({pos}/5)')
P(f'  γκανιοτα Crown στο 1-2: {np.mean([1 / g["c"][-1][1] + 1 / g["c"][-1][2] - 1 for g in G])*100:.1f}%')
# ---- 2. μοντελο ----
P(''); P('=== 2. ΜΟΝΤΕΛΟ: πιθανοτητα νικης γηπ = Φ(διαφορα/11.5) — βαθμονομηση & log-loss vs αγορα ===')
pm = np.array([Phi(g['m'] / SM) for g in G]); pk = np.array([devig(g['c'][-1][1], g['c'][-1][2]) for g in G]); y = np.array([g['act'] > 0 for g in G], float)
po = np.array([devig(g['c'][0][1], g['c'][0][2]) for g in G])
ll = lambda p: -np.mean(y * np.log(np.clip(p, 1e-4, 1)) + (1 - y) * np.log(np.clip(1 - p, 1e-4, 1)))
P(f'  log-loss: μοντελο {ll(pm):.4f} · αγορα ανοιγμα {ll(po):.4f} · αγορα κλεισιμο {ll(pk):.4f}')
for lo, hi in ((0, .2), (.2, .35), (.35, .5), (.5, .65), (.65, .8), (.8, 1.01)):
    m_ = (pm >= lo) & (pm < hi)
    if m_.sum() >= 10: P(f'  μοντελο λεει γηπ {lo:.0%}-{min(hi, 1):.0%}: n {m_.sum():4d} · μοντελο {pm[m_].mean():.1%} · πραγματικα {y[m_].mean():.1%} · αγορα {pk[m_].mean():.1%}')
b = np.polyfit(pm - pk, y - pk, 1)[0]
P(f'  «η διαφωνια μας με την αγορα βγαινει;» κλιση (πραγμ − αγορα) πανω στη (μοντελο − αγορα): {b:+.2f}')
# ---- 3. picks 1-2 ----
P(''); P('=== 3. PICKS 1-2 (alert Crown, edge ≥8%, οχι τελευταιο 2ωρο) ===')
def ml_alert(g, thr=0.08):
    for k_, (t, h, a) in enumerate(g['c']):
        if t >= g['tip']: break
        if k_ > 0 and (g['tip'] - t) / 3600 < 2: return None
        p = Phi(g['m'] / SM); eh, ea = p * h - 1, (1 - p) * a - 1
        side, e, od = (1, eh, h) if eh >= ea else (-1, ea, a)
        if e >= thr:
            win = (g['act'] > 0) if side == 1 else (g['act'] < 0)
            return dict(side=side, e=e, od=od, pnl=(od - 1) if win else -1.0, hrs=(g['tip'] - t) / 3600)
    return None
PK = []
for g in G:
    r = ml_alert(g)
    if r: PK.append(dict(r, sea=g['sea'], pos=g['pos']))
Q = pd.DataFrame(PK)
def line(lab, x):
    if len(x) == 0: P(f'  {lab:34s} —'); return
    pos = sum(1 for s in SE5 if (x.sea == s).any() and x[x.sea == s].pnl.mean() > 0)
    P(f'  {lab:34s} n {len(x):4d} · ROI {x.pnl.mean()*100:+6.1f}% · μοναδες {x.pnl.sum():+6.1f} · {pos}/5 · [' + ' '.join(f'{s[-2:]}:{x[x.sea == s].pnl.sum():+.1f}' for s in SE5) + ']')
line('ΟΛΑ', Q)
line('ΦΑΒΟΡΙ (αποδοση <2.0)', Q[Q.od < 2.0])
line('ΑΟΥΤΣΑΙΝΤΕΡ 2.0-3.0', Q[(Q.od >= 2.0) & (Q.od < 3.0)])
line('ΑΟΥΤΣΑΙΝΤΕΡ 3.0-5.0', Q[(Q.od >= 3.0) & (Q.od < 5.0)])
line('ΑΟΥΤΣΑΙΝΤΕΡ 5.0+', Q[Q.od >= 5.0])
# ---- 4. συγκριση με χαντικαπ ----
P(''); P('=== 4. 1-2 vs ΧΑΝΤΙΚΑΠ στα ιδια ματς (χαντικαπ = alert Crown, edge ≥8%, κανονας 2ωρου) ===')
HC = {}
for p, r in REC[21].items():
    m = PR.get(key(p), {}).get('h_new')
    if m is None or not np.isfinite(m): continue
    ser, tip = r['ser'], r['tip']
    for k_, row in enumerate(ser):
        if row[0] >= tip: break
        side, e, od = pick(21, m, row)
        if e < 0.08: continue
        if k_ > 0 and (tip - row[0]) / 3600 < 2: break
        HC[p] = dict(side=side, pnl=settle(21, p, side, row, od), line=row[2] * side); break
grp = {}
for _, q in Q.iterrows():
    h = HC.get(q.pos)
    k = 'ΜΟΝΟ 1-2 (κανενα χαντικαπ)' if h is None else ('ΙΔΙΑ πλευρα με χαντικαπ' if h['side'] == q.side else 'ΑΝΤΙΘΕΤΗ πλευρα απο χαντικαπ')
    grp.setdefault(k, []).append((q.pnl, h['pnl'] if h else None, q.od, q.sea))
for k, v in grp.items():
    a = [x[0] for x in v]; hh = [x[1] for x in v if x[1] is not None]
    P(f'  {k:32s} n {len(v):4d} · 1-2 {sum(a):+6.1f} μον. ({np.mean(a)*100:+.1f}%) · χαντικαπ ιδιων ματς {sum(hh):+6.1f} μον. ({len(hh)}) · μεση αποδοση 1-2 {np.mean([x[2] for x in v]):.2f}')
v = grp.get('ΙΔΙΑ πλευρα με χαντικαπ', [])
for lo, hi, lab in ((1.0, 2.0, 'φαβορι'), (2.0, 3.0, 'αουτσ. 2-3'), (3.0, 99, 'αουτσ. 3+')):
    x = [e for e in v if lo <= e[2] < hi]
    if x: P(f'    ιδια πλευρα · {lab:10s} n {len(x):3d} · 1-2 {sum(e[0] for e in x):+5.1f} μον. · χαντικαπ {sum(e[1] for e in x):+5.1f} μον.')
P(f'  ΣΥΝΟΛΟ χαντικαπ picks (ολα τα ματς): {len(HC)} · {sum(h["pnl"] for h in HC.values()):+.1f} μον.')
open('el_moneyline_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
