# -*- coding: utf-8 -*-
"""bcl_small_posthoc_test.py — BCL: ποινη για ομαδες 9 μικρων πρωταθληματων ΜΟΝΟ στην τελικη προβλεψη (7/10/2026, Στελιος «τρεξτο»).
Αφορμη: η ποινη μεσα στα ratings (bcl_small_start_test) χαλουσε λιγο τους αντιπαλους (+0.022 σε 643 ματς). Εδω τα ratings ΜΕΝΟΥΝ ιδια:
προβλεψη ματς με «μικρη» ομαδα += δ·k/(k+n) (n = ματς που εχει ηδη παιξει η ομαδα φετος στην κοινη κλιμακα: ευρωπαικα + φιλικα).
δ {−2,−4,−6,−8} × k {1.5, 3, 6, ∞ (χωρις σβησιμο)}. ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση): LOSO 2021-26 με λαθος στα ματς-στοχο →
ΠΕΡΝΑ αν πεφτει σε ≥4/5 σεζον (τα υπολοιπα ματς ΔΕΝ αλλαζουν εξ ορισμου). Αναφορα: μεροληψια ανα ζωνη & picks ≥8% ανοιγμα.
Εξοδος: bcl_small_posthoc_out.txt"""
import sys, json, pickle, collections, math
import numpy as np
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
import bcl_common as B, bcl_small_start_test as T
Phi = NormalDist().cdf
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
LG, MC = T.small_teams(); tl = lambda y, t: LG.get((y, t)) or LG.get((y - 1, t))
D = pickle.load(open('bcl_engine_preds_live.pkl', 'rb')); ids, ys = D['id'], D['y']; base = np.array(D['FIN'], float)
MK = pickle.load(open('bcl_mk.pkl', 'rb'))
FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
E = {e['id']: e for k, L in FG.items() if k.startswith('BCL_') for e in L if e.get('hs') not in (None, '')}
# n = ματς της ομαδας φετος ΠΡΙΝ το ματς, σε οτι βλεπει η κοινη κλιμακα (χωρις εγχωρια μικρων)
rows = B.load(pre=True); seen = collections.Counter(); NB = {}
for r in rows:
    NB[r[7]] = (seen[(r[0], r[3])], seen[(r[0], r[4])])
    if r[5] is not None: seen[(r[0], r[3])] += 1; seen[(r[0], r[4])] += 1
cnt = collections.Counter(); GN = {}
for k, L in FG.items():
    if not k.startswith('BCL_'): continue
    y = int(k.split('_')[1])
    for e in sorted([x for x in L if x.get('hs') not in (None, '')], key=lambda x: x['ts']):
        h, a = B.ALIAS.get(e['hid'], e['hid']), B.ALIAS.get(e['aid'], e['aid']); cnt[(y, h)] += 1; cnt[(y, a)] += 1; GN[e['id']] = (cnt[(y, h)], cnt[(y, a)])
N = len(ids); act = np.full(N, np.nan); sh = np.zeros(N); sa = np.zeros(N); nh = np.zeros(N); na = np.zeros(N); sgn = np.zeros(N); gsm = np.zeros(N, int)
for k, i in enumerate(ids):
    if i not in E: continue
    y = int(ys[k]); h, a = B.ALIAS.get(E[i]['hid'], E[i]['hid']), B.ALIAS.get(E[i]['aid'], E[i]['aid'])
    act[k] = int(E[i]['hs']) - int(E[i]['as_']); sh[k] = bool(tl(y, h)); sa[k] = bool(tl(y, a)); nh[k], na[k] = NB.get(i, (0, 0))
    if sh[k] != sa[k]: sgn[k] = 1 if sh[k] else -1; gsm[k] = GN[i][0] if sh[k] else GN[i][1]
tgt = (sh + sa) > 0; EV = [2021, 2022, 2023, 2024, 2025]; ev = np.isin(ys, EV)
def pred(d, kk):
    f = (lambda n: kk / (kk + n)) if kk else (lambda n: 1.0 + 0 * n)
    return base + d * sh * f(nh) - d * sa * f(na)
GRID = [(d, kk) for d in (-2, -4, -6, -8) for kk in (1.5, 3, 6, None)]
PR = {g: pred(*g) for g in GRID}; PR[(0, None)] = base
def rm(v, m): m = m & np.isfinite(v) & np.isfinite(act); return float(np.sqrt(np.mean((act - v)[m] ** 2)))
BINS = [('1-3', 1, 3), ('4-6', 4, 6), ('7-10', 7, 10), ('11+', 11, 99)]
P(f'ματς-στοχος {int((tgt & ev).sum())} · μεροληψια (− = υπερεκτιμηση) ανα ζωνη · λαθος στοχου')
for g in [(0, None)] + GRID:
    v = PR[g]; cells = []
    for lab, a, b in BINS:
        m = ev & (sgn != 0) & (gsm >= a) & (gsm <= b); cells.append(f'{np.mean((act - v)[m] * sgn[m]):+6.2f}')
    P(f'  δ {g[0]:+d} k {str(g[1] or "∞"):4s} ' + ' '.join(cells) + f'  · {rm(v, tgt & ev):.3f}')
held = np.full(N, np.nan); ch = []
for Y in EV:
    gb = min(GRID, key=lambda g: rm(PR[g], tgt & ev & (ys != Y))); ch.append(gb); m = ys == Y; held[m] = PR[gb][m]
d = [rm(held, tgt & (ys == Y)) - rm(base, tgt & (ys == Y)) for Y in EV]
P(''); P(f'ΚΡΙΣΗ LOSO {[f"δ{g[0]} k{g[1] or chr(8734)}" for g in ch]} · στοχος {rm(base, tgt & ev):.3f} → {rm(held, tgt & ev):.3f} · ' + ' '.join(f'{x:+.2f}' for x in d)
  + f' → {sum(x < 0 for x in d)}/5 · υπολοιπα ±0 (ιδια)' + ('  <- ΠΕΡΝΑ' if sum(x < 0 for x in d) >= 4 else '  ✗'))
# picks ≥8% στο ανοιγμα, live κανονας
def cover(m_, L, s=12.0):
    if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
    pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
def picks(v, msk):
    U = collections.defaultdict(list)
    for k, i in enumerate(ids):
        if not msk[k] or i not in MK or not np.isfinite(v[k]): continue
        for book in (3, 8):
            if book not in MK[i] or 'o' not in MK[i][book]: continue
            L, _, o1, o2 = MK[i][book]['o']; pw, pp, pl = cover(v[k], L); e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
            s, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
            if e >= .08: x = (act[k] + L) * s; U[book].append(((od - 1) if x > 0 else (0 if x == 0 else -1), int(ys[k])))
    return ' · '.join(f"{'Crown' if b == 3 else 'B365'} {np.mean([u for u, _ in U[b]])*100:+.1f}% ({len(U[b])}, θετ {sum(1 for Y in EV if [u for u, y in U[b] if y == Y] and np.mean([u for u, y in U[b] if y == Y]) > 0)}/5)" for b in (3, 8) if U[b])
P(''); P('PICKS ≥8% ανοιγμα στα ματς-στοχο: σημερα ' + picks(base, tgt & ev)); P('                              LOSO   ' + picks(held, tgt & ev))
open('bcl_small_posthoc_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
