# -*- coding: utf-8 -*-
"""bcl_small_versions_report.py — 7/10/2026: ομαδες 9 μικρων πρωταθληματων — μεροληψια & λαθος ανα ζωνη ματς BCL για καθε εκδοχη
(bcl_small_versions.pkl: A σημερα · B μικρα χωρις προσαρμογη · G μικρα + επιπεδο · L{s} επιπεδο + μεταφραση s · N{s} μονο μεταφραση s)
+ LOSO επιλογη s & κριτηριο (στοχος ≥4/5 σεζον, υπολοιπα ≤ +0.01). Εξοδος: bcl_small_versions_out.txt"""
import sys, json, pickle, collections, math, numpy as np
sys.stdout.reconfigure(encoding='utf-8')
import bcl_common as B
SMALL = {'CZE', 'FIN', 'BUL', 'POR', 'SUI', 'CYP', 'DEN', 'GEO', 'SVK'}
D = pickle.load(open('bcl_engine_preds_live.pkl', 'rb')); V = pickle.load(open('bcl_small_versions.pkl', 'rb'))
ids, ys = D['id'], D['y']; pos = {i: k for k, i in enumerate(ids)}
def arr(pr):
    v = np.full(len(ids), np.nan)
    for mid, (p, y) in pr.items():
        if mid in pos: v[pos[mid]] = p
    return v
A = arr(V['A']); M1 = (D['FIN'] - .75 * A) / .25
PR = {k: .25 * M1 + .75 * arr(v) for k, v in V.items()}
FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
E = {e['id']: e for k, L in FG.items() if k.startswith('BCL_') for e in L if e.get('hs') not in (None, '')}
rows = B.load(pre=False, extra2=True, include=('CZE', 'FIN')); by = collections.defaultdict(list)
for r in rows: by[r[0]].append(r)
MC = {y: B._main_comp(v) for y, v in by.items()}
cnt = collections.Counter(); GN = {}
for k, L in FG.items():
    if not k.startswith('BCL_'): continue
    y = int(k.split('_')[1])
    for e in sorted([x for x in L if x.get('hs') not in (None, '')], key=lambda x: x['ts']):
        h, a = B.ALIAS.get(e['hid'], e['hid']), B.ALIAS.get(e['aid'], e['aid']); cnt[(y, h)] += 1; cnt[(y, a)] += 1; GN[e['id']] = (cnt[(y, h)], cnt[(y, a)])
EV = [2021, 2022, 2023, 2024, 2025]
act = np.array([(int(E[i]['hs']) - int(E[i]['as_'])) if i in E else np.nan for i in ids], float)
sgn = np.zeros(len(ids)); gsm = np.zeros(len(ids), int); tgt = np.zeros(len(ids), bool)
for k, i in enumerate(ids):
    if i not in E: continue
    y = int(ys[k]); e = E[i]; h, a = B.ALIAS.get(e['hid'], e['hid']), B.ALIAS.get(e['aid'], e['aid'])
    lg = lambda t: MC.get(y, {}).get(t) or MC.get(y - 1, {}).get(t)
    sh, sa = lg(h) in SMALL, lg(a) in SMALL
    if sh or sa: tgt[k] = True
    if sh != sa: sgn[k] = 1 if sh else -1; gsm[k] = GN[i][0] if sh else GN[i][1]
ev = np.isin(ys, EV)
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
BINS = [('1-3', 1, 3), ('4-6', 4, 6), ('7-10', 7, 10), ('11+', 11, 99)]
def rm(v, m): m = m & np.isfinite(v) & np.isfinite(act); return float(np.sqrt(np.mean((act - v)[m] ** 2)))
P('ΜΕΡΟΛΗΨΙΑ ομαδων μικρων (πραγμ − προβλ, − = τις υπερεκτιμαμε) ανα ζωνη ματς BCL · ΛΑΘΟΣ στοχου · λαθος υπολοιπων')
P('εκδοχη      ' + ' '.join(f'{b[0]:>7s}' for b in BINS) + '   στοχος  υπολοιπα')
for k in ['A', 'B', 'G'] + [x for x in PR if x[0] in 'LN']:
    v = PR[k]; cells = []
    for lab, a, b in BINS:
        m = ev & (sgn != 0) & (gsm >= a) & (gsm <= b) & np.isfinite(v)
        cells.append(f'{np.mean((act - v)[m] * sgn[m]):+7.2f}')
    P(f'{k:10s} ' + ' '.join(cells) + f'   {rm(v, tgt & ev):6.3f}  {rm(v, ~tgt & ev):6.3f}')
P(''); P('ΚΡΙΣΗ (στοχος καλυτερα απο Α σε ≥4/5 σεζον, υπολοιπα ≤ +0.01) — LOSO επιλογη s')
base = PR['A']
for fam in ('L', 'N'):
    ks = [x for x in PR if x[0] == fam]
    held = np.full(len(ids), np.nan); ch = []
    for Y in EV:
        kb = min(ks, key=lambda k: rm(PR[k], tgt & ev & (ys != Y))); ch.append(kb); m = ys == Y; held[m] = PR[kb][m]
    d = [rm(held, tgt & (ys == Y)) - rm(base, tgt & (ys == Y)) for Y in EV]; dr = rm(held, ~tgt & ev) - rm(base, ~tgt & ev)
    ok = sum(x < 0 for x in d) >= 4 and dr <= .01
    P(f'  {"επιπεδο + μεταφραση" if fam == "L" else "μονο μεταφραση"}: LOSO {ch} · στοχος {rm(base, tgt & ev):.3f} → {rm(held, tgt & ev):.3f} · ' + ' '.join(f'{x:+.2f}' for x in d)
      + f' → {sum(x < 0 for x in d)}/5 · υπολοιπα {dr:+.3f}' + ('  <- ΚΕΡΔΙΖΕΙ' if ok else '  ✗'))
open('bcl_small_versions_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
