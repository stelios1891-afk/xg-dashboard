# -*- coding: utf-8 -*-
"""bcl_mix_test.py — BCL ΧΑΝΤΙΚΑΠ: ΜΙΞΗ ΜΕ ΤΗΝ ΑΓΟΡΑ / σ / ΟΡΙΟ (8/10/2026, Στελιος «οκ ξεκινα»).
Αφορμη: edges 69/61/44% στην 1η αγωνιστικη (υπερ-σιγουρο μοντελο) · backtest: ματς 1-3 θετικα, 4+ −9.7% (0/5). Ιδιο με EuroCup (ec_sigma_edge_test).
Προβλεψη: m* = μ_αγορας(ανοιγμα) + w·(μοντελο − μ_αγορας). Σημερα: w 1 (μονο μοντελο), σ 12, οριο 8%.
Πλεγμα: w {1, .75, .5, .35, .25} × σ {11, 12, 13, 14.5, 16} × οριο {4, 6, 8, 10, 12%}. Μοντελο = live φορμουλα (bcl_engine_preds_live FIN).
Αγορα: Crown (3) & Bet365 (8), ανοιγμα (και κλεισιμο για αναφορα). Σεζον 2021-26.
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση):
 Κ1 ΒΑΘΜΟΝΟΜΗΣΗ: log-loss καλυψης στο ανοιγμα (και τα δυο βιβλια)· LOSO επιλογη (w, σ) → ΠΕΡΝΑ αν καλυτερο απο το σημερινο σε ≥4/5 σεζον.
 Κ2 ΧΡΗΜΑΤΑ: LOSO επιλογη (w, σ, οριο) με μοναδες στο ανοιγμα (μεσος Crown/Bet365) → ΠΕΡΝΑ αν οι μοναδες της κρατημενης σεζον ≥ σημερινες σε ≥4/5.
 Αναφορα ανα ζωνη ματς (1-3 / 4+, μεγαλυτερος αριθμος ματς BCL των 2 ομαδων) & κλεισιμο. Εξοδος: bcl_mix_out.txt"""
import sys, json, pickle, collections, math, itertools
import numpy as np
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
Phi = NormalDist().cdf
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
D = pickle.load(open('bcl_engine_preds_live.pkl', 'rb')); MK = pickle.load(open('bcl_mk.pkl', 'rb'))
FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
E = {e['id']: e for k, L in FG.items() if k.startswith('BCL_') for e in L if e.get('hs') not in (None, '')}
cnt = collections.Counter(); GN = {}
for k, L in FG.items():
    if not k.startswith('BCL_'): continue
    y = int(k.split('_')[1])
    for e in sorted([x for x in L if x.get('hs') not in (None, '')], key=lambda x: x['ts']):
        cnt[(y, e['hid'])] += 1; cnt[(y, e['aid'])] += 1; GN[e['id']] = max(cnt[(y, e['hid'])], cnt[(y, e['aid'])])
EV = [2021, 2022, 2023, 2024, 2025]
G = []      # (y, gn, act, model, {book: (L, mu, o1, o2) ανοιγμα}, {book: κλεισιμο})
for k, i in enumerate(D['id']):
    y = int(D['y'][k])
    if y not in EV or i not in E or i not in MK or not np.isfinite(D['FIN'][k]): continue
    op = {b: v['o'] for b, v in MK[i].items() if 'o' in v and b in (3, 8)}; cl = {b: v['c'] for b, v in MK[i].items() if 'c' in v and b in (3, 8)}
    if not op: continue
    G.append((y, GN.get(i, 0), int(E[i]['hs']) - int(E[i]['as_']), float(D['FIN'][k]), op, cl))
P(f'ματς με αγορα 2021-26: {len(G)} · ' + ' '.join(f'{Y}:{sum(1 for g in G if g[0] == Y)}' for Y in EV))
def cover(m_, L, s):
    if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
    pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
W = (1.0, .75, .5, .35, .25); S = (11.0, 12.0, 13.0, 14.5, 16.0); TH = (.04, .06, .08, .10, .12)
def evaluate(w, s, when='o'):
    """→ ανα σεζον: log-loss λιστα, και picks [(y, gn, edge, κερδος)] ανα βιβλιο"""
    ll = collections.defaultdict(list); pk = []
    for y, gn, act, m, op, cl in G:
        src = op if when == 'o' else cl
        for b, (L, mu, o1, o2) in src.items():
            mm = mu + w * (m - mu); pw, pp, pl = cover(mm, L, s); x = act + L
            p_ = pw if x > 0 else (pl if x < 0 else max(pp, 1e-6)); ll[y].append(-math.log(max(p_, 1e-6)))
            e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1; side, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
            v = x * side; pk.append((y, gn, e, (od - 1) if v > 0 else (0 if v == 0 else -1), b))
    return ll, pk
R = {(w, s): evaluate(w, s) for w in W for s in S}
RC = {(w, s): evaluate(w, s, 'c') for w in W for s in S}
BASE = (1.0, 12.0, .08)
def units(pk, th, ys, zone=None):
    sel = [p for p in pk if p[0] in ys and p[2] >= th and (zone is None or (zone == 'early') == (p[1] <= 3))]
    return sum(p[3] for p in sel) / 2, len(sel) / 2         # /2 = μεσος δυο βιβλιων
P(''); P('## Κ1 ΒΑΘΜΟΝΟΜΗΣΗ (log-loss καλυψης, ανοιγμα· μικροτερο = καλυτερο) — in-sample 2021-26')
for w in W: P(f'  w {w:<4} ' + ' '.join(f'σ{s:g}:{np.mean([x for v in R[(w, s)][0].values() for x in v]):.4f}' for s in S))
ch, d = [], []
for Y in EV:
    tr = [x for x in EV if x != Y]
    kb = min(R, key=lambda k: np.mean([x for y_ in tr for x in R[k][0][y_]])); ch.append(kb)
    d.append(np.mean(R[kb][0][Y]) - np.mean(R[BASE[:2]][0][Y]))
P(f'  LOSO (w, σ): {ch} · διαφορα log-loss ανα σεζον ' + ' '.join(f'{x:+.4f}' for x in d) + f' → καλυτερα {sum(x < 0 for x in d)}/5' + ('  <- ΠΕΡΝΑ' if sum(x < 0 for x in d) >= 4 else '  ✗'))
P(''); P('## ΧΡΗΜΑΤΑ in-sample: μοναδες (picks) στο ΑΝΟΙΓΜΑ, μεσος Crown/Bet365 — ολα · αγων 1-3 · 4+')
P(f'  ΣΗΜΕΡΑ w1 σ12 8%: ' + ' · '.join(f'{lab} {units(R[(1.0, 12.0)][1], .08, EV, z)[0]:+.1f}μ ({units(R[(1.0, 12.0)][1], .08, EV, z)[1]:.0f})' for lab, z in (('ολα', None), ('1-3', 'early'), ('4+', 'late'))))
best = sorted(((units(R[(w, s)][1], th, EV)[0], w, s, th) for w in W for s in S for th in TH), reverse=True)[:12]
for u, w, s, th in best:
    P(f'  w {w:<4} σ {s:<4g} οριο {th*100:.0f}%: ' + ' · '.join(f'{lab} {units(R[(w, s)][1], th, EV, z)[0]:+.1f}μ ({units(R[(w, s)][1], th, EV, z)[1]:.0f})' for lab, z in (('ολα', None), ('1-3', 'early'), ('4+', 'late')))
      + f' · κλεισιμο {units(RC[(w, s)][1], th, EV)[0]:+.1f}μ · ανα σεζον ' + ' '.join(f'{Y % 100}:{units(R[(w, s)][1], th, [Y])[0]:+.1f}' for Y in EV))
P(''); P('## ΣΗΜΕΡΙΝΟΣ κανονας ανα σεζον & ζωνη (ανοιγμα): ' + ' '.join(f'{Y % 100}: 1-3 {units(R[(1.0, 12.0)][1], .08, [Y], "early")[0]:+.1f} / 4+ {units(R[(1.0, 12.0)][1], .08, [Y], "late")[0]:+.1f}' for Y in EV))
P(''); P('## Κ2 LOSO (w, σ, οριο) με μοναδες ανοιγματος')
keys = [(w, s, th) for w in W for s in S for th in TH]
ch, dd, tot_h, tot_b = [], [], 0, 0
for Y in EV:
    tr = [x for x in EV if x != Y]
    kb = max(keys, key=lambda k: units(R[k[:2]][1], k[2], tr)[0]); ch.append(kb)
    uh = units(R[kb[:2]][1], kb[2], [Y])[0]; ub = units(R[BASE[:2]][1], BASE[2], [Y])[0]; dd.append(uh - ub); tot_h += uh; tot_b += ub
P(f'  LOSO επιλογες {ch}')
P(f'  μοναδες κρατημενης σεζον − σημερινες: ' + ' '.join(f'{x:+.1f}' for x in dd) + f' → καλυτερα ή ισα {sum(x >= 0 for x in dd)}/5 · συνολο {tot_h:+.1f}μ vs σημερα {tot_b:+.1f}μ' + ('  <- ΠΕΡΝΑ' if sum(x >= 0 for x in dd) >= 4 else '  ✗'))
for zone, lab in (('early', '1-3'), ('late', '4+')):
    kz = [(w, s, th) for w in W for s in S for th in TH]; chz, uz, ubz = [], 0, 0
    for Y in EV:
        tr = [x for x in EV if x != Y]; kb = max(kz, key=lambda k: units(R[k[:2]][1], k[2], tr, zone)[0]); chz.append(kb)
        uz += units(R[kb[:2]][1], kb[2], [Y], zone)[0]; ubz += units(R[BASE[:2]][1], BASE[2], [Y], zone)[0]
    P(f'  ζωνη {lab}: LOSO {chz} · {uz:+.1f}μ vs σημερα {ubz:+.1f}μ')
open('bcl_mix_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
