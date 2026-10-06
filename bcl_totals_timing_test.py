# -*- coding: utf-8 -*-
"""bcl_totals_timing_test.py — BCL ΣΥΝΟΛΑ: ΧΡΟΝΙΣΜΟΣ (6/10/2026, Στελιος «τρεξε και το τεστ χρονισμου στα συνολα»).
Ιδια μεθοδος με bcl_timing_test (χαντικαπ). Ιστορικο γραμμης συνολων Nowgoal (t23, Crown + Bet365) 2021-26.
  Σημεια: Bet365 ΑΝΟΙΓΜΑ · 24ω · 12ω · 6ω · 3ω · 1ω · ΚΛΕΙΣΙΜΟ (ιδια ματς: ανοιχτα ≥24ω) · Crown ΑΝΟΙΓΜΑ · 3ω · 1ω · ΚΛΕΙΣΙΜΟ (ανοιχτα ≥6ω).
  Κανονες: (α) live (μοντελο μονο του, σ 17.3, ≥8%) (β) μιξη 50/50 με την αγορα της στιγμης (≥6%).
  Προβλεψεις: καθαρες LOSO της live μηχανης συνολων (bcl_totals_luck_preds.pkl H1: κοινη κλιμακα + διορθωση τυχης).
  + picks ανοιγματος: πού πηγε η γραμμη (υπερ μας = πανω για over, κατω για under) και ποσα ειναι ακομα picks στο κλεισιμο.
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση): «αργοτερα ειναι καλυτερα» μονο αν ενα σημειο ξεπερνα το ανοιγμα σε ≥75% των σεζον ΚΑΙ στα δυο βιβλια.
Εξοδος: bcl_totals_timing_test_out.txt"""
import sys, os, json, math, pickle, collections
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
NN = NormalDist(); Phi = NN.cdf; SIG = 17.3
L = pickle.load(open('bcl_totals_luck_preds.pkl', 'rb')); T0 = pickle.load(open('bcl_totals_preds.pkl', 'rb'))
ids, ys, MODEL, TOT, gno = L['id'], L['y'], L['H1'], T0['tot'], T0['gno']
EV = [2021, 2022, 2023, 2024, 2025]
FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
E = {e['id']: e for k, Lx in FG.items() if k.startswith('BCL_') for e in Lx}
idx = collections.defaultdict(list)
for i, mid in enumerate(ids):
    e = E.get(mid)
    if e and e.get('hs') not in (None, ''): idx[(int(e['hs']), int(e['as_']))].append(i)
ROWS = collections.defaultdict(dict)
for ln in open('nowgoal_bcl/odds.jsonl', encoding='utf-8'):
    r = json.loads(ln)
    if r['t'] == 23 and r['cid'] in (3, 8): ROWS[r['ngid']][r['cid']] = r['rows']
HIST = {3: {}, 8: {}}
for f in sorted(os.listdir('nowgoal_bcl')):
    if not f.startswith('sched_'): continue
    for g in json.load(open('nowgoal_bcl/' + f, encoding='utf-8')):
        if g.get('hs') is None or g['ngid'] not in ROWS: continue
        tip = pd.Timestamp(g['bj']) - pd.Timedelta(hours=8); hit = None
        for key in ((g['hs'], g['as_']), (g['as_'], g['hs'])):
            for i in idx.get(key, []):
                if abs(E[ids[i]]['ts'] - tip.timestamp()) <= 26 * 3600: hit = i; break
            if hit is not None: break
        if hit is None or ys[hit] not in EV or not np.isfinite(MODEL[hit]): continue
        for cid in (3, 8):
            rows = sorted([x for x in ROWS[g['ngid']].get(cid, []) if x[4] == 2 and x[1] is not None and x[2] and x[3] and x[0] + 8 * 3600 <= tip.timestamp() + 600], key=lambda x: x[0])
            if rows: HIST[cid][hit] = (tip.timestamp(), [(x[0] + 8 * 3600, float(x[1]), 1 + x[2], 1 + x[3]) for x in rows])
def at(H, i, cp):
    tip, h = H[i]
    if cp == 'open': return h[0]
    if cp == 'close': return h[-1]
    c = [x for x in h if x[0] <= tip - cp * 3600]
    return c[-1] if c else None
def mexp(T, oo, ou):
    po = (1 / oo) / (1 / oo + 1 / ou); return T + SIG * NN.inv_cdf(min(max(po, 1e-4), 1 - 1e-4))
def cov(mu, T):
    if abs(T - round(T)) < 1e-9:
        po = Phi((mu - T - .5) / SIG); pu = Phi((T - mu - .5) / SIG); return po, 1 - po - pu, pu
    po = Phi((mu - T) / SIG); return po, 0.0, 1 - po
RULES = {'live (μοντελο ≥8%)': (1.0, .08), 'μιξη 50/50 (≥6%)': (.5, .06)}
def pick(i, x, rule):
    wm, thr = RULES[rule]; _, T, oo, ou = x; mk = mexp(T, oo, ou); mu = mk + wm * (MODEL[i] - mk)
    po, pq, pu = cov(mu, T); eo, eu = po * oo + pq - 1, pu * ou + pq - 1
    if max(eo, eu) < thr: return None
    return (1, T, oo) if eo >= eu else (-1, T, ou)
def settle(i, s, T, od):
    q = (TOT[i] - T) * s; return (od - 1) if q > 0 else (0 if q == 0 else -1)
verdict = collections.defaultdict(dict)
for cid in (3, 8):
    H = HIST[cid]; bk = 'Crown' if cid == 3 else 'Bet365'
    EH = 24 if cid == 8 else 6; CPS = ('open', 24, 12, 6, 3, 1, 'close') if cid == 8 else ('open', 3, 1, 'close')
    early = [i for i in H if (H[i][0] - H[i][1][0][0]) / 3600 >= EH]
    P(''); P(f'===== {bk} · ματς {len(H)} · ανοιγει (διαμεσος) {np.median([(t - h[0][0]) / 3600 for t, h in H.values()]):.0f}ω πριν · ιδια ματς (ανοιχτα ≥{EH}ω): {len(early)} =====')
    for rule in RULES:
        P(f'  [{rule}]')
        for per, f in (('ολη η σεζον', lambda g: True), ('ματς 1-3', lambda g: g <= 3), ('ματς 4+', lambda g: g > 3)):
            P(f'   {per}:'); base = None
            for cp in CPS:
                R = []
                for i in early:
                    if not f(gno[i]): continue
                    x = at(H, i, cp)
                    if x is None: continue
                    p = pick(i, x, rule)
                    if p: R.append((settle(i, *p), int(ys[i]), p[0]))
                a = np.array([q[0] for q in R]) if R else np.zeros(0)
                per_s = {Y: np.mean([q[0] for q in R if q[1] == Y]) for Y in sorted({q[1] for q in R})}
                if cp == 'open': base = per_s
                better = sum(1 for Y in per_s if Y in base and per_s[Y] > base[Y]) if cp != 'open' else None
                nb = len([Y for Y in per_s if Y in base])
                if better is not None and per == 'ολη η σεζον': verdict[(rule, cp)][bk] = better >= math.ceil(.75 * nb)
                nov = sum(1 for q in R if q[2] == 1)
                P(f'     {str(cp) + ("ω πριν" if isinstance(cp, int) else ""):10s} picks {len(a):4d} (over {nov}) · ROI {a.mean() * 100 if len(a) else 0:+6.1f}% · {a.sum():+6.1f}u · θετ. {sum(v > 0 for v in per_s.values())}/{len(per_s)}'
                  + (f' · καλυτερο απο ανοιγμα σε {better}/{nb}' if better is not None else ''))
        clv, still = [], 0
        for i in early:
            p = pick(i, at(H, i, 'open'), rule)
            if not p: continue
            xo, xc = at(H, i, 'open'), at(H, i, 'close'); clv.append(p[0] * (xc[1] - xo[1]))
            q = pick(i, xc, rule)
            if q and q[0] == p[0]: still += 1
        clv = np.array(clv)
        if len(clv): P(f'   picks ανοιγματος {len(clv)}: η γραμμη κινηθηκε ΥΠΕΡ μας {clv.mean():+.2f} π. · υπερ {np.mean(clv > .05) * 100:.0f}% / κατα {np.mean(clv < -.05) * 100:.0f}% · ακομα pick στο κλεισιμο {still / len(clv) * 100:.0f}%')
    mv = {cp: np.mean([abs(at(H, i, cp)[1] - at(H, i, 'close')[1]) for i in early if at(H, i, cp)]) for cp in CPS if cp != 'close'}
    P('  μεση αποσταση γραμμης απο το κλεισιμο (ποντοι): ' + ' · '.join(f'{k}: {v:.2f}' for k, v in mv.items()))
P(''); P('################ ΚΡΙΣΗ (ολη η σεζον, ≥75% σεζον ΚΑΙ στα δυο βιβλια — κοινα σημεια 3ω/1ω/κλεισιμο) ################')
anyok = False
for (rule, cp), v in verdict.items():
    if all(v.get(b) for b in ('Crown', 'Bet365')): P(f'  ✓ {rule} · {cp}: ΚΑΛΥΤΕΡΟ ΑΠΟ ΤΟ ΑΝΟΙΓΜΑ'); anyok = True
if not anyok: P('  ✗ κανενα σημειο δεν ξεπερνα το ανοιγμα')
open('bcl_totals_timing_test_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
