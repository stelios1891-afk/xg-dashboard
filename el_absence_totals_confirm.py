# -*- coding: utf-8 -*-
"""el_absence_totals_confirm.py — ΕΠΙΒΕΒΑΙΩΣΗ σε ΑΝΕΞΑΡΤΗΤΑ δεδομενα του ευρηματος el_absence_totals_test (9/10/2026):
στην Ευρωλιγκα 2021-25 οι ποντοι μιας ομαδας πεφτουν οταν λειπει δικος της ΣΚΟΡΕΡ (δικα×ποντοι −1.0, 5/5) και ανεβαινουν οταν λειπει
ΑΜΥΝΤΙΚΟΣ του αντιπαλου (αντιπ.×αμυνα +1.4, 5/5)· τα σκετα λεπτα και οι ασιστ ΔΕΝ ειναι σταθερα.
Ανεξαρτητα: EuroCup U2017-U2025 (9 σεζον) + Ευρωλιγκα E2017-E2020 (4 σεζον) — δεν μπηκαν στο τεστ. Δεν υπαρχει live μοντελο εκει →
βαση = απλο: ποντοι ομαδας ≈ μ.ο. επιθεσης της (φετινα ματς πριν) + μ.ο. αμυνας αντιπαλου − μ.ο. λιγκας (μαζεμα 5 ματς) + εδρα.
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση): επιβεβαιωνεται αν ΚΑΙ ΟΙ ΔΥΟ συντελεστες (δικα×ποντοι < 0, αντιπ.×αμυνα > 0) εχουν το σωστο προσημο
σε ≥ 9/13 σεζον ΚΑΙ στο συνολο t ≥ 2. Εξοδος: el_absence_totals_confirm_out.txt"""
import sys, json, collections, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
PL = json.load(open('el_players.json', encoding='utf-8'))
IND = ['E2017', 'E2018', 'E2019', 'E2020'] + [f'U{y}' for y in range(2017, 2026)]
TG = collections.defaultdict(list); GM = []
for k, g in PL.items():
    if 'ph' not in g or 'pa' not in g or g.get('hs') is None: continue
    ts = pd.Timestamp(g['utc']).timestamp()
    for side, tc in (('ph', 'hcode'), ('pa', 'acode')):
        TG[(g['season'], g[tc])].append((ts, {p[0]: (p[3] or 0.0, p[4] or 0, p[13] or 0, (p[14] or 0) + (p[16] or 0) + (p[12] or 0), p[19] or 0) for p in g[side]}))
    if g['season'] in IND: GM.append((g['season'], ts, g['hcode'], g['acode'], float(g['hs']), float(g['as_'])))
for v in TG.values(): v.sort(key=lambda x: x[0])
PH = collections.defaultdict(list)
for L in TG.values():
    for ts, d in L:
        for pid, x in d.items():
            if x[0] > 0: PH[pid].append((ts,) + x)
for v in PH.values(): v.sort()
FE = ('pts', 'ast', 'dfn', 'pm')
def prof(pid, ts):
    h = [x for x in PH[pid] if x[0] < ts - 3600][-60:]
    if not h: return None
    a = np.array([x[1:] for x in h], float); per = a[:, 1:].sum(0) / (a[:, 0].sum() + 200.0) * 40
    return dict(min=float(a[-10:, 0].mean()), **dict(zip(FE, per)))
def absents(sea, team, ts):
    L = TG.get((sea, team), []); prev = [x for x in L if x[0] < ts - 3600]; today = next((x[1] for x in L if abs(x[0] - ts) < 3600), None)
    if today is None: return None
    cnt = collections.Counter(p for _, d in prev[-10:] for p, v in d.items() if v[0] > 0); res = []
    for pid, c in cnt.items():
        if c < 3 or today.get(pid, (0,))[0] > 0: continue
        k = 0
        for _, d in reversed(prev):
            if d.get(pid, (0,))[0] > 0: break
            k += 1
        v = prof(pid, ts)
        if v is None or v['min'] < 10: continue
        v['w'] = v['min'] / 40 * (1.0 if k + 1 <= 3 else (.5 if k + 1 <= 10 else 0.0))
        if v['w'] > 0: res.append(v)
    return res
# ---- απλη βαση: επιθεση/αμυνα ομαδων απο τα φετινα ματς πριν ----
GM.sort(key=lambda x: x[1])
rows = []
for sea in IND:
    G = [g for g in GM if g[0] == sea]; sc = collections.defaultdict(list); al = collections.defaultdict(list); allpts = []
    for s_, ts, h, a, hs, as_ in G:
        if len(sc[h]) >= 3 and len(sc[a]) >= 3:
            lg = np.mean(allpts); sh = lambda L: (sum(L) + 5 * lg) / (len(L) + 5)
            ah, aa = absents(sea, h, ts), absents(sea, a, ts)
            if ah is not None and aa is not None:
                rows.append(dict(y=sea, pts=hs, base=sh(sc[h]) + sh(al[a]) - lg, home=1, own=ah, opp=aa))
                rows.append(dict(y=sea, pts=as_, base=sh(sc[a]) + sh(al[h]) - lg, home=0, own=aa, opp=ah))
        sc[h].append(hs); al[h].append(as_); sc[a].append(as_); al[a].append(hs); allpts += [hs, as_]
allp = [p for r in rows for p in r['own']]
MU = {f: np.mean([p[f] for p in allp]) for f in FE}; SD = {f: np.std([p[f] for p in allp]) for f in FE}
z = lambda p, f: (p[f] - MU[f]) / SD[f]
X = np.array([[1, r['home'], sum(p['w'] for p in r['own']), sum(p['w'] for p in r['opp']), sum(p['w'] * z(p, 'pts') for p in r['own']),
               sum(p['w'] * z(p, 'ast') for p in r['own']), sum(p['w'] * z(p, 'dfn') for p in r['opp'])] for r in rows])
Y = np.array([r['pts'] - r['base'] for r in rows]); ys = np.array([r['y'] for r in rows])
NM = ['σταθ.', 'εδρα', 'δικα λεπτα', 'λεπτα αντιπ.', 'δικα×ποντοι', 'δικα×ασιστ', 'αντιπ.×αμυνα']
def ols(m):
    Xm, Ym = X[m], Y[m]; b = np.linalg.lstsq(Xm, Ym, rcond=None)[0]; r_ = Ym - Xm @ b
    se = np.sqrt(np.diag(np.sum(r_ ** 2) / (len(Ym) - X.shape[1]) * np.linalg.inv(Xm.T @ Xm))); return b, se
P(f'ανεξαρτητα ομαδα-ματς: {len(rows)} ({len(rows)//2} ματς) · σεζον {len(IND)} · απουσες {len(allp)}')
b, se = ololo = ols(np.ones(len(rows), bool))
P(''); P('## ΟΛΑ ΜΑΖΙ (ποντοι ομαδας ανα 40′ απουσιας· z ανα 1 τυπ. αποκλιση)')
for j, n in enumerate(NM):
    if j >= 2: P(f'  {n:14s} {b[j]:+.2f} (t {b[j] / se[j]:+.1f})')
P(''); P('## ΑΝΑ ΣΕΖΟΝ')
ok_p, ok_d = 0, 0
for s in IND:
    bb, _ = ols(ys == s); ok_p += bb[4] < 0; ok_d += bb[6] > 0
    P(f'  {s}: δικα×ποντοι {bb[4]:+.2f} · αντιπ.×αμυνα {bb[6]:+.2f} · δικα λεπτα {bb[2]:+.2f} · λεπτα αντιπ. {bb[3]:+.2f} · δικα×ασιστ {bb[5]:+.2f}')
for comp in ('E', 'U'):
    m = np.array([y.startswith(comp) for y in ys]); bb, ss = ols(m)
    P(f'  μονο {"Ευρωλιγκα 2017-20" if comp == "E" else "EuroCup 2017-25"}: δικα×ποντοι {bb[4]:+.2f} (t {bb[4]/ss[4]:+.1f}) · αντιπ.×αμυνα {bb[6]:+.2f} (t {bb[6]/ss[6]:+.1f})')
P('')
okk = ok_p >= 9 and ok_d >= 9 and b[4] / se[4] <= -2 and b[6] / se[6] >= 2
P(f'ΣΩΣΤΟ ΠΡΟΣΗΜΟ: δικα×ποντοι {ok_p}/13 · αντιπ.×αμυνα {ok_d}/13 · t {b[4]/se[4]:+.1f} / {b[6]/se[6]:+.1f} → ' + ('ΕΠΙΒΕΒΑΙΩΝΕΤΑΙ' if okk else 'ΔΕΝ επιβεβαιωνεται'))
P(f'(Ευρωλιγκα 2021-25 στο τεστ: δικα×ποντοι −1.00 · αντιπ.×αμυνα +1.42)')
open('el_absence_totals_confirm_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
