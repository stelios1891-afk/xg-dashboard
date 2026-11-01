# -*- coding: utf-8 -*-
"""bcl_lowinfo_test.py — BCL: picks σε ματς με ομαδα ΛΙΓΩΝ ΔΕΔΟΜΕΝΩΝ (7/10/2026, Στελιος «μηπως ειναι καλυτερος μηχανισμος να μη βγαζει
καθολου picks για αυτες τις ομαδες;»).
«Λιγα δεδομενα» = η ομαδα ειχε < Ν επισημα ματς (ολες οι διοργανωσεις της κοινης κλιμακας, χωρις φιλικα, χωρις Τσεχια/Φινλανδια) τις
τελευταιες 365 μερες πριν το ματς· Ν {10, 15, 20, 30}. Προβλεψεις: live φορμουλα (χαντικαπ & συνολα, χωρις Τσεχια/Φινλανδια). Αγορα: Crown/Bet365 ανοιγμα.
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση): κανονας «χωρις picks οταν μια ομαδα εχει < Ν» ΠΕΡΝΑ αν τα picks που κοβει ειναι αρνητικα σε ≥4/5 σεζον
(με ≥3 picks) ΚΑΙ το ROI ολων ανεβαινει — και στα δυο βιβλια. Εξοδος: bcl_lowinfo_out.txt"""
import sys, os, json, pickle, collections
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
import bcl_common as B
Pp = pickle.load(open('bcl_periph_preds.pkl', 'rb'))
ids, ys = Pp['ids'], Pp['ys']; H = Pp['H']["('h', 'noCF')"]; T = Pp['T']["('t', 'noCF')"]
rows = [r for r in B.load(pre=False) if r[5] is not None]
games_by_team = collections.defaultdict(list)
for r in rows:
    for t in (r[3], r[4]): games_by_team[t].append(r[2])
for v in games_by_team.values(): v.sort()
FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
E = {e['id']: e for k, L in FG.items() if k.startswith('BCL_') for e in L if e.get('hs') not in (None, '')}
import bisect
def n_before(t, ts):
    v = games_by_team.get(B.ALIAS.get(t, t), []); return bisect.bisect_left(v, ts) - bisect.bisect_left(v, ts - 365 * 86400)
NMIN = np.full(len(ids), np.nan); act = np.full(len(ids), np.nan); tot = np.full(len(ids), np.nan)
for k, i in enumerate(ids):
    if i not in E: continue
    e = E[i]; NMIN[k] = min(n_before(e['hid'], e['ts']), n_before(e['aid'], e['ts']))
    act[k] = int(e['hs']) - int(e['as_']); tot[k] = int(e['hs']) + int(e['as_'])
ND = NormalDist(); Phi = ND.cdf
MKH = pickle.load(open('bcl_mk.pkl', 'rb'))
ROWS = collections.defaultdict(dict)
for ln in open('nowgoal_bcl/odds.jsonl', encoding='utf-8'):
    r = json.loads(ln)
    if r['t'] == 23 and r['cid'] in (3, 8): ROWS[r['ngid']][r['cid']] = sorted([x for x in r['rows'] if x[4] == 2 and x[1] is not None and x[2] and x[3]], key=lambda x: x[0])
idx = collections.defaultdict(list)
for k, i in enumerate(ids):
    if i in E: idx[(int(E[i]['hs']), int(E[i]['as_']))].append(k)
MKT = {}
for f in sorted(os.listdir('nowgoal_bcl')):
    if not f.startswith('sched_'): continue
    for g in json.load(open('nowgoal_bcl/' + f, encoding='utf-8')):
        if g.get('hs') is None or g['ngid'] not in ROWS: continue
        tip = (pd.Timestamp(g['bj']) - pd.Timedelta(hours=8)).timestamp(); hit = None
        for key in ((g['hs'], g['as_']), (g['as_'], g['hs'])):
            for k in idx.get(key, []):
                if abs(E[ids[k]]['ts'] - tip) <= 26 * 3600: hit = k; break
            if hit is not None: break
        if hit is not None:
            MKT[ids[hit]] = {cid: (float(R_[0][1]), 1 + R_[0][2], 1 + R_[0][3]) for cid, R_ in ROWS[g['ngid']].items() if R_}
def cover(m_, L, s):
    if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
    pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
EV = [2021, 2022, 2023, 2024, 2025]
def picks(kind, book):
    R = []
    for k, i in enumerate(ids):
        if ys[k] not in EV or not np.isfinite(NMIN[k]): continue
        if kind == 'h':
            v = H[k]; mk = (MKH.get(i) or {}).get(book)
            if not mk or not np.isfinite(v): continue
            L, _, o1, o2 = mk['o']; pw, pp, pl = cover(v, L, 12.0); x = act[k] + L
        else:
            v = T[k]; mk = (MKT.get(i) or {}).get(book)
            if not mk or not np.isfinite(v): continue
            L, o1, o2 = mk; pw, pp, pl = cover(v, -L, 17.3); x = tot[k] - L
        e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1; s_, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
        if e < .08: continue
        q = x * s_; R.append((int(ys[k]), NMIN[k], (od - 1) if q > 0 else (0 if q == 0 else -1)))
    return pd.DataFrame(R, columns=['y', 'n', 'u'])
def cell(z):
    if not len(z): return '—'
    pos = sum(1 for Y in EV if (z.y == Y).sum() >= 3 and z[z.y == Y].u.mean() > 0); ny = sum(1 for Y in EV if (z.y == Y).sum() >= 3)
    return f'{z.u.mean()*100:+.1f}% ({len(z)}, {z.u.sum():+.1f}u, θετ {pos}/{ny})'
P(f'Ματς BCL 2021-26 με προβλεψη: ελαχιστο ματς ομαδας (365 μερες) — διαμεσος {np.nanmedian(NMIN[np.isin(ys, EV)]):.0f} · <10: {int(((NMIN < 10) & np.isin(ys, EV)).sum())} · <20: {int(((NMIN < 20) & np.isin(ys, EV)).sum())} · <30: {int(((NMIN < 30) & np.isin(ys, EV)).sum())}')
for kind, nm in (('h', 'ΧΑΝΤΙΚΑΠ'), ('t', 'ΣΥΝΟΛΑ')):
    P(''); P(f'################ {nm} (ROI ≥8%, ανοιγμα) ################')
    for book, bn in ((3, 'Crown'), (8, 'Bet365')):
        Z = picks(kind, book); P(f'  [{bn}] ολα: {cell(Z)}')
        for N in (10, 15, 20, 30):
            low = Z[Z.n < N]; rest = Z[Z.n >= N]
            neg = sum(1 for Y in EV if (low.y == Y).sum() >= 3 and low[low.y == Y].u.mean() < 0); ny = sum(1 for Y in EV if (low.y == Y).sum() >= 3)
            ok = ny >= 4 and neg >= 4 and len(rest) and rest.u.mean() > Z.u.mean()
            P(f'    ομαδα με <{N:2d} ματς: {cell(low):34s} · υπολοιπα {cell(rest):34s} · αρνητικα σε {neg}/{ny}' + ('  ✓' if ok else '  ✗'))
open('bcl_lowinfo_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
