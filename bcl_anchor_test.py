# -*- coding: utf-8 -*-
"""bcl_anchor_test.py — BCL ΧΑΝΤΙΚΑΠ: ΑΓΚΥΡΩΣΗ ΣΤΗΝ ΑΓΟΡΑ (21/10/2026, Στελιος «το 1 τρεξτο» — οπως η μηχανη συνολων NBA Μ2).
Βαση: live φορμουλα (bcl_engine_preds_live.pkl FIN, ΧΩΡΙΣ αποδοσεις νικητη — ιστορικα δεν υπαρχουν· στο live μενουν), αγορα Crown & Bet365 (bcl_mk.pkl),
2020-21…2025-26. «Αγορα» = μεσος δικαιος (χωρις γκανιοτα) των διαθεσιμων βιβλιων στη στιγμη· pick αποτιμαται σε ΚΑΘΕ βιβλιο χωριστα (οπως bcl_bigedge).
ΜΗΧΑΝΕΣ (γραφτηκαν πριν το τρεξιμο):
  LIVE  : μοντελο FIN, σ 12, edge ≥8%
  Α1 ΜΙΞΗ: αγορα + w·(FIN − αγορα), w ∈ {.1,.2,.3,.5,.7,1} (LOSO με RMSE)
  Α2 ΥΠΟΛΟΙΠΟ: αγορα + b1·(FIN − αγορα) + b2·(FIN − αγορα)·[ματς 1-3] + b3·[ματς 1-3]  (ridge, LOSO)
  σ των Α1/Α2 = τυπικη αποκλιση (πραγμ − προβλεψη) στις σεζον εκπαιδευσης · κατωφλι edge ∈ {4,6,8,10}% LOSO με μοναδες.
ΠΡΟ-ΔΗΛΩΜΕΝΟ: μια μηχανη Α αντικαθιστα το LIVE αν (στο ΑΝΟΙΓΜΑ) LOSO μοναδες > LIVE ΚΑΙ ROI > 0 σε ≥4/6 σεζον ΚΑΙ CLV > 0 ΚΑΙ
  walk-forward (εκπαιδευση μονο σε προηγουμενες σεζον, ελεγχος 2022-25) ROI > 0 σε ≥3/4. Περιγραφικα: κλεισιμο, μεγαλες διαφωνιες, ματς 1-3.
Εξοδος: bcl_anchor_test_out.txt"""
import sys, json, pickle, collections
import numpy as np
from statistics import NormalDist
Phi = NormalDist().cdf
sys.stdout.reconfigure(encoding='utf-8')
D = pickle.load(open('bcl_engine_preds_live.pkl', 'rb')); MK = pickle.load(open('bcl_mk.pkl', 'rb'))
FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
cnt = collections.Counter(); GN = {}
for k, L in FG.items():
    if not k.startswith('BCL_'): continue
    y = int(k.split('_')[1])
    for e in sorted([x for x in L if x.get('hs') not in (None, '')], key=lambda x: x['ts']):
        cnt[(y, e['hid'])] += 1; cnt[(y, e['aid'])] += 1; GN[e['id']] = max(cnt[(y, e['hid'])], cnt[(y, e['aid'])])
rows = []
for k, i in enumerate(D['id']):
    if i not in MK or not np.isfinite(D['FIN'][k]) or not np.isfinite(D['act'][k]): continue
    bk = {b: MK[i][b] for b in (3, 8) if b in MK[i] and MK[i][b].get('o') and MK[i][b].get('c')}
    if not bk: continue
    fo = float(np.mean([v['o'][1] for v in bk.values()])); fc = float(np.mean([v['c'][1] for v in bk.values()]))
    rows.append(dict(i=i, y=int(D['y'][k]), act=float(D['act'][k]), fin=float(D['FIN'][k]), fo=fo, fc=fc, early=float(GN.get(i, 9) <= 3), bk=bk))
Y = np.array([r['y'] for r in rows]); SE = sorted(set(Y)); ACT = np.array([r['act'] for r in rows])
FIN = np.array([r['fin'] for r in rows]); FO = np.array([r['fo'] for r in rows]); EARLY = np.array([r['early'] for r in rows])
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def cover(m_, L, s):
    if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
    pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
def evaluate(pred, sig, thr, mask=None, when='o'):
    """→ λιστα (y, res, clv) — ενα pick ανα βιβλιο"""
    R = []
    for j, r in enumerate(rows):
        if mask is not None and not mask[j]: continue
        s_ = sig[j] if np.ndim(sig) else sig; th = thr[j] if np.ndim(thr) else thr
        for b, v in r['bk'].items():
            L, _, o1, o2 = v[when]; pw, pp, pl = cover(pred[j], L, s_); e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
            sd, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
            if e < th: continue
            x = (r['act'] + L) * sd; res = (od - 1) if x > 0 else (0.0 if x == 0 else -1.0)
            R.append((r['y'], res, sd * (v['c'][1] - v['o'][1]) if when == 'o' else 0.0, abs(pred[j] - (-L)), r['early']))
    return R
def cell(R):
    if not R: return '        —'
    a = np.array([x[1] for x in R]); ys = [x[0] for x in R]
    ps = collections.defaultdict(float)
    for y_, r_ in zip(ys, a): ps[y_] += r_
    return f'{100 * a.mean():+6.1f}% ({len(a):4d}, {a.sum():+6.1f}μ, {sum(1 for v in ps.values() if v > 0)}/{len(set(ys))}) CLV {np.mean([x[2] for x in R]):+.2f}'
def units_by(R):
    u = collections.defaultdict(float)
    for x in R: u[x[0]] += x[1]
    return u
P(f'BCL ΧΑΝΤΙΚΑΠ · ΑΓΚΥΡΩΣΗ ΣΤΗΝ ΑΓΟΡΑ · ματς {len(rows)} ({dict(collections.Counter(Y))}) · ματς 1-3: {int(EARLY.sum())}')
rm = lambda p, m: float(np.sqrt(np.mean((ACT[m] - p[m]) ** 2)))
P('  RMSE ανα σεζον · αγορα ανοιγ. / LIVE: ' + ' · '.join(f'{s}: {rm(FO, Y == s):.2f}/{rm(FIN, Y == s):.2f}' for s in SE))
LIVE = evaluate(FIN, 12.0, .08)
P(f'  LIVE (σ 12, ≥8%) ανοιγμα: {cell(LIVE)} · κλεισιμο {cell(evaluate(FIN, 12.0, .08, when="c"))}')
# ---------- μηχανες ----------
def fitA1(tr):
    WS = (.1, .2, .3, .5, .7, 1.0); w = min(WS, key=lambda w: np.mean((ACT[tr] - (FO[tr] + w * (FIN[tr] - FO[tr]))) ** 2))
    pr = FO + w * (FIN - FO); return pr, float(np.std(ACT[tr] - pr[tr])), w
def fitA2(tr):
    X = np.c_[FIN - FO, (FIN - FO) * EARLY, EARLY]; y = ACT - FO
    b = np.linalg.solve(X[tr].T @ X[tr] + 20 * np.eye(3), X[tr].T @ y[tr]); pr = FO + X @ b
    return pr, float(np.std(ACT[tr] - pr[tr])), tuple(np.round(b, 2))
THR = (.04, .06, .08, .10)
for nm, fit in (('Α1 ΜΙΞΗ', fitA1), ('Α2 ΥΠΟΛΟΙΠΟ', fitA2)):
    P(''); P(f'=== {nm} ===')
    held_pred = np.zeros(len(rows)); held_sig = np.zeros(len(rows)); held_thr = np.zeros(len(rows)); info = {}
    for s in SE:
        tr = Y != s; pr, sg, par = fit(tr)
        U = {th: sum(units_by(evaluate(pr, sg, th, mask=tr)).values()) for th in THR}
        th = max(THR, key=lambda t: U[t]); te = Y == s
        held_pred[te] = pr[te]; held_sig[te] = sg; held_thr[te] = th; info[s] = (par, round(sg, 2), th)
    P('  παραμετροι ανα σεζον (w ή b · σ · κατωφλι): ' + ' · '.join(f'{s}: {v}' for s, v in info.items()))
    P('  RMSE LOSO: ' + ' · '.join(f'{s}: {rm(held_pred, Y == s):.2f}' for s in SE) + f' · καλυτερο απο αγορα {sum(rm(held_pred, Y == s) < rm(FO, Y == s) for s in SE)}/6')
    R = evaluate(held_pred, held_sig, held_thr)
    uL, uA = units_by(LIVE), units_by(R)
    P(f'  LOSO ανοιγμα: {cell(R)} · LIVE {cell(LIVE)} · μοναδες Α − LIVE {sum(uA.values()) - sum(uL.values()):+.1f}')
    P('     ανα σεζον μοναδες Α / LIVE: ' + ' · '.join(f'{s}: {uA.get(s, 0):+.1f}/{uL.get(s, 0):+.1f}' for s in SE))
    for lab, f in (('ματς 1-3', lambda x: x[4] == 1), ('ματς 4+', lambda x: x[4] == 0), ('διαφωνια ≥7 π.', lambda x: x[3] >= 7)):
        P(f'     {lab:14s} Α {cell([x for x in R if f(x)])} · LIVE {cell([x for x in LIVE if f(x)])}')
    # walk-forward
    WF = []
    for s in [x for x in SE if x >= 2022]:
        tr = Y < s; pr, sg, par = fit(tr)
        U = {th: sum(units_by(evaluate(pr, sg, th, mask=tr)).values()) for th in THR}; th = max(THR, key=lambda t: U[t])
        WF += evaluate(pr, sg, th, mask=(Y == s))
    uW = units_by(WF)
    ok = (sum(uA.values()) > sum(uL.values()) and sum(1 for s in SE if uA.get(s, 0) > 0) >= 4 and np.mean([x[2] for x in R]) > 0
          and sum(1 for s in [x for x in SE if x >= 2022] if uW.get(s, 0) > 0) >= 3)
    P(f'  WALK-FORWARD 2022-25: {cell(WF)} · ανα σεζον ' + ' · '.join(f'{s}: {uW.get(s, 0):+.1f}' for s in SE if s >= 2022))
    P(f'  → {nm}: {"ΠΕΡΝΑ" if ok else "ΔΕΝ περνα"}')
open('bcl_anchor_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
