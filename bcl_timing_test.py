# -*- coding: utf-8 -*-
"""bcl_timing_test.py — BCL ΧΡΟΝΙΣΜΟΣ: ποτε συμφερει να μπαινουμε; (6/10/2026, Στελιος «τρεξε και το τεστ του χρονισμου»).
Ιδια μεθοδος με EuroCup (ec_timing_factors_test βημα 3). Ολο το ιστορικο γραμμης χαντικαπ Nowgoal (Crown + Bet365) 2020-26.
  Σημεια: ΑΝΟΙΓΜΑ · 24ω · 12ω · 6ω · 3ω · 1ω πριν · ΚΛΕΙΣΙΜΟ.
  Κανονες: (α) σημερινος live (μοντελο μονο του, σ 12, ≥8%) (β) μιξη 50/50 με την αγορα ΕΚΕΙΝΗΣ της στιγμης (σ 12.1, ≥6%).
  Προβλεψεις: Α = σημερινη live φορμουλα (bcl_engine_preds_live.pkl, σταθερες ρυθμισεις — αισιοδοξη) · Β = καθαρη LOSO (bcl_engine_preds2f.pkl).
  + για τα picks του ανοιγματος: πού πηγε η γραμμη (CLV σε ποντους) και ποσα ειναι ακομα picks στο κλεισιμο.
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση): «αργοτερα ειναι καλυτερα» μονο αν το ROI σε ενα σημειο ξεπερνα το ανοιγμα σε ≥75% των σεζον
  (ιδια ματς: ανοιχτα ≥24ω πριν στο Bet365 · ≥6ω στην Crown, που ανοιγει ~9ω πριν), ΚΑΙ στα δυο βιβλια.
Εξοδος: bcl_timing_test_out.txt"""
import sys, os, json, math, pickle, collections
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
NN = NormalDist(); Phi = NN.cdf
FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
sc = {e['id']: (int(e['hs']), int(e['as_'])) for k, L in FG.items() if k.startswith('BCL_') for e in L if e.get('hs') not in (None, '')}
PRED = {lab: pickle.load(open(f, 'rb')) for lab, f in (('Α live φορμουλα', 'bcl_engine_preds_live.pkl'), ('Β καθαρη LOSO', 'bcl_engine_preds2f.pkl'))}
D = PRED['Α live φορμουλα']; ids, YS, ACT, T, HID = D['id'], D['y'], D['act'], D['t'], D['hid']
gno = np.zeros(len(ids), int); cnt = collections.Counter()
for i in np.argsort(T): cnt[(YS[i], HID[i])] += 1; gno[i] = cnt[(YS[i], HID[i])]
idx = collections.defaultdict(list)
for i, mid in enumerate(ids):
    if mid in sc: idx[sc[mid]].append(i)
ROWS = collections.defaultdict(dict)
for ln in open('nowgoal_bcl/odds.jsonl', encoding='utf-8'):
    r = json.loads(ln)
    if r['t'] == 21 and r['cid'] in (3, 8): ROWS[r['ngid']][r['cid']] = r['rows']
HIST = {3: {}, 8: {}}
for f in sorted(os.listdir('nowgoal_bcl')):
    if not f.startswith('sched_'): continue
    for g in json.load(open('nowgoal_bcl/' + f, encoding='utf-8')):
        if g.get('hs') is None or g['ngid'] not in ROWS: continue
        tip = pd.Timestamp(g['bj']) - pd.Timedelta(hours=8); hit, sw = None, False
        for (a_, b_), swp in (((g['hs'], g['as_']), False), ((g['as_'], g['hs']), True)):
            for i in idx.get((a_, b_), []):
                if abs((pd.Timestamp(T[i]) - tip).total_seconds()) <= 26 * 3600: hit, sw = i, swp; break
            if hit is not None: break
        if hit is None: continue
        for cid in (3, 8):
            rows = sorted([x for x in ROWS[g['ngid']].get(cid, []) if x[4] == 2 and x[1] is not None and x[2] and x[3] and x[0] + 8 * 3600 <= tip.timestamp() + 600], key=lambda x: x[0])
            if not rows: continue
            def conv(x):
                o1, o2 = 1 + x[2], 1 + x[3]; L = -x[1]; ph = (1 / o1) / (1 / o1 + 1 / o2); mu = -L + 12.0 * NN.inv_cdf(min(max(ph, 1e-4), 1 - 1e-4))
                return (x[0] + 8 * 3600,) + ((-L, -mu, o2, o1) if sw else (L, mu, o1, o2))
            HIST[cid][hit] = (tip.timestamp(), [conv(x) for x in rows])
for cid in (3, 8):
    H = HIST[cid]
    P(f'{"Crown" if cid == 3 else "Bet365"}: {len(H)} ματς με ιστορικο · ανοιγει (διαμεσος) {np.median([(t - h[0][0]) / 3600 for t, h in H.values()]):.0f}ω πριν · '
      f'αλλαγες γραμμης/ματς {np.mean([len(h) for t, h in H.values()]):.0f}')
def at(H, i, cp):
    tip, h = H[i]
    if cp == 'open': return h[0]
    if cp == 'close': return h[-1]
    c = [x for x in h if x[0] <= tip - cp * 3600]
    return c[-1] if c else None
def cover(m_, L, s):
    if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
    pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
def settle(i, side, L, od):
    v = (ACT[i] + L) * side; return (od - 1) if v > 0 else (0 if v == 0 else -1)
RULES = {'σημερινος (μοντελο ≥8%)': (1.0, 12.0, .08), 'μιξη 50/50 (≥6%)': (.5, 12.1, .06)}
def pick(MODEL, i, x, rule):
    wm, sg, thr = RULES[rule]; _, L, mk, o1, o2 = x; m_ = mk + wm * (MODEL[i] - mk)
    pw, pp, pl = cover(m_, L, sg); e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
    s, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
    return (s, L, od, e) if e >= thr else None
CPS = ('open', 24, 12, 6, 3, 1, 'close')
verdict = collections.defaultdict(dict)
for plab, PD in PRED.items():
    MODEL = PD['FIN']
    P(''); P(f'################ ΠΡΟΒΛΕΨΕΙΣ {plab} ################')
    for cid in (3, 8):
        H = HIST[cid]; bk = 'Crown' if cid == 3 else 'Bet365'
        EH = 24 if cid == 8 else 6; CPS = ('open', 24, 12, 6, 3, 1, 'close') if cid == 8 else ('open', 3, 1, 'close')
        early = [i for i in H if (H[i][0] - H[i][1][0][0]) / 3600 >= EH and np.isfinite(MODEL[i])]
        P(f' ===== {bk} · ιδια ματς (ανοιχτα ≥{EH}ω πριν): {len(early)} =====')
        for rule in RULES:
            P(f'  [{rule}]')
            for per, f in (('ολη η σεζον', lambda g: True), ('ματς 1-3', lambda g: g <= 3), ('ματς 4+', lambda g: g > 3)):
                P(f'   {per}:')
                base = None
                for cp in CPS:
                    R = []
                    for i in early:
                        if not f(gno[i]): continue
                        x = at(H, i, cp)
                        if x is None: continue
                        p = pick(MODEL, i, x, rule)
                        if p: R.append((settle(i, p[0], p[1], p[2]), int(YS[i])))
                    a = np.array([q[0] for q in R]) if R else np.zeros(0)
                    per_s = {Y: np.mean([q[0] for q in R if q[1] == Y]) for Y in sorted({q[1] for q in R})}
                    if cp == 'open': base = per_s
                    better = sum(1 for Y in per_s if Y in base and per_s[Y] > base[Y]) if cp != 'open' else None
                    nb = len([Y for Y in per_s if Y in base])
                    if better is not None and per == 'ολη η σεζον': verdict[(plab, rule, cp)][bk] = better >= math.ceil(.75 * nb)
                    P(f'     {str(cp) + ("ω πριν" if isinstance(cp, int) else ""):10s} picks {len(a):4d} · ROI {a.mean()*100 if len(a) else 0:+6.1f}% · {a.sum():+6.1f}u · θετ. {sum(v > 0 for v in per_s.values())}/{len(per_s)}'
                      + (f' · καλυτερο απο ανοιγμα σε {better}/{nb}' if better is not None else ''))
            clv, still = [], 0
            for i in early:
                p = pick(MODEL, i, at(H, i, 'open'), rule)
                if not p: continue
                xo, xc = at(H, i, 'open'), at(H, i, 'close'); clv.append(p[0] * (xc[2] - xo[2]))
                q = pick(MODEL, i, xc, rule)
                if q and q[0] == p[0]: still += 1
            clv = np.array(clv)
            if len(clv): P(f'   picks ανοιγματος {len(clv)}: η αγορα κινηθηκε ΥΠΕΡ μας {clv.mean():+.2f} π. · υπερ {np.mean(clv > .05)*100:.0f}% / κατα {np.mean(clv < -.05)*100:.0f}% · ακομα pick στο κλεισιμο {still/len(clv)*100:.0f}%')
        mv = {cp: np.mean([abs(at(H, i, cp)[2] - at(H, i, 'close')[2]) for i in early if at(H, i, cp)]) for cp in CPS if cp != 'close'}
        P('  μεση αποσταση αγορας απο το κλεισιμο (ποντοι): ' + ' · '.join(f'{k}: {v:.2f}' for k, v in mv.items()))
P(''); P('################ ΚΡΙΣΗ (ολη η σεζον, καλυτερο απο ανοιγμα σε ≥75% σεζον ΚΑΙ στα δυο βιβλια — κοινα σημεια 3ω/1ω/κλεισιμο) ################')
for (plab, rule, cp), v in verdict.items():
    if all(v.get(b) for b in ('Crown', 'Bet365')): P(f'  ✓ {plab} · {rule} · {cp}ω πριν: ΚΑΛΥΤΕΡΟ ΑΠΟ ΤΟ ΑΝΟΙΓΜΑ')
P('  (οτι δεν εμφανιζεται: ✗ — το ανοιγμα δεν ξεπερνιεται)')
open('bcl_timing_test_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
