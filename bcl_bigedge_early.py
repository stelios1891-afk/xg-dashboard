# -*- coding: utf-8 -*-
"""bcl_bigedge_early.py — BCL: ΜΕΓΑΛΕΣ ΔΙΑΦΩΝΙΕΣ ΜΕ ΤΗΝ ΑΓΟΡΑ ΣΤΙΣ ΠΡΩΤΕΣ ΑΓΩΝΙΣΤΙΚΕΣ (13/10/2026, Στελιος «τα τοσο μεγαλα edges σε Περιστερι
και Ρυτας πως εξηγουνται; μπορουμε να εμπιστευτουμε;»). Live φορμουλα χαντικαπ (bcl_engine_preds_live.pkl, ιδια με bcl_backtest_live),
σ 12, edge ≥8%, Crown & Bet365 (μεσος), ανοιγμα & κλεισιμο, 2021-26 (ΧΩΡΙΣ αποδοσεις νικητη — ιστορικα δεν υπαρχουν).
Picks ανα ΜΕΓΕΘΟΣ διαφωνιας (μοντελο − αγορα στο ανοιγμα, ποντοι) × αγων 1-3 / 4+. ΠΕΡΙΓΡΑΦΙΚΟ. Εξοδος: bcl_bigedge_early_out.txt"""
import sys, json, pickle, collections
import numpy as np
from statistics import NormalDist
Phi = NormalDist().cdf
sys.stdout.reconfigure(encoding='utf-8')
D = pickle.load(open('bcl_engine_preds_live.pkl', 'rb')); MK = pickle.load(open('bcl_mk.pkl', 'rb'))
FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
E = {e['id']: e for k, L in FG.items() if k.startswith('BCL_') for e in L if e.get('hs') not in (None, '')}
cnt = collections.Counter(); GN = {}
for k, L in FG.items():
    if not k.startswith('BCL_'): continue
    y = int(k.split('_')[1])
    for e in sorted([x for x in L if x.get('hs') not in (None, '')], key=lambda x: x['ts']):
        cnt[(y, e['hid'])] += 1; cnt[(y, e['aid'])] += 1; GN[e['id']] = max(cnt[(y, e['hid'])], cnt[(y, e['aid'])])
def cover(m_, L, s):
    if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
    pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
def pick(m, L, o1, o2, x):
    pw, pp, pl = cover(m, L, 12.0); e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
    side, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
    if e < .08: return None
    v = x * side; return side, ((od - 1) if v > 0 else (0 if v == 0 else -1))
BANDS = [(0, 4, '<4 π.'), (4, 7, '4-7 π.'), (7, 10, '7-10 π.'), (10, 99, '≥10 π.')]
R = collections.defaultdict(lambda: collections.defaultdict(list))
for k, i in enumerate(D['id']):
    y = int(D['y'][k])
    if i not in E or i not in MK or not np.isfinite(D['FIN'][k]): continue
    act = int(E[i]['hs']) - int(E[i]['as_']); z = '1-3' if GN.get(i, 0) <= 3 else '4+'; m = float(D['FIN'][k])
    vo = [MK[i].get(b, {}).get('o') for b in (3, 8)]; vo = [v for v in vo if v]
    if not vo: continue
    gap = abs(m + np.mean([v[0] for v in vo]))                     # μοντελο (γηπ. διαφορα) − αγορα (= −γραμμη)
    band = next(lab for lo, hi, lab in BANDS if lo <= gap < hi)
    for when in ('o', 'c'):
        us = []
        for b in (3, 8):
            v = MK[i].get(b, {}).get('o')                          # επιλογη στο ΑΝΟΙΓΜΑ
            if not v: continue
            p = pick(m, v[0], v[2], v[3], act + v[0])
            if p is None: continue
            if when == 'o': us.append(p[1])
            else:
                c = MK[i].get(b, {}).get('c')
                if not c: continue
                o = c[2] if p[0] == 1 else c[3]; x = (act + c[0]) * p[0]
                us.append((o - 1) if x > 0 else (0 if x == 0 else -1))
        if us:
            R[(when, z, band)][y].append(float(np.mean(us)))
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def cell(d):
    a = [u for v in d.values() for u in v]
    if not a: return f'{"—":>26}'
    return f'{np.mean(a)*100:+6.1f}% ({len(a):3d}, {sum(1 for v in d.values() if np.mean(v) > 0)}/{len(d)})'
P('BCL ΧΑΝΤΙΚΑΠ · live φορμουλα (χωρις αποδοσεις νικητη) · edge ≥8% στο ανοιγμα · μεσος Crown/Bet365 · ROI (picks, θετικες σεζον)')
P('διαφωνια = |μοντελο − αγορα| στο ανοιγμα σε ποντους· «κλεισιμο» = το ιδιο pick στην τιμη κλεισιματος')
for z in ('1-3', '4+'):
    P(''); P(f'=== αγωνιστικες {z} ===')
    for _, _, lab in BANDS:
        P(f'  {lab:8s} ανοιγμα {cell(R[("o", z, lab)])} · κλεισιμο {cell(R[("c", z, lab)])}')
open('bcl_bigedge_early_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
