# -*- coding: utf-8 -*-
"""ec_model_test.py — EUROCUP: ιδιο μοντελο με την πρωτη εκδοση Ευρωλιγκας (el_model_test.py) απεναντι στο κλεισιμο Crown (1/10/2026, Στελιος).
Δεδομενα: el_players.json (box scores EuroCup 'U2017'…'U2025', ιδια μορφη με el_box) · nowgoal_ec/odds.jsonl (Crown cid 3: χαντικαπ t 21,
  συνολο t 23, καθε αλλαγη, ut +8ω) · nowgoal_ec/sched_*.json (σκορ & ωρα για αντιστοιχιση).
ΜΟΝΤΕΛΟ: ιδια μηχανη (κατοχες, αποδοτικοτητα επιθεσης/αμυνας, ρυθμος, walk-forward, ridge προς carry × περσινο, εδρα h, παραλλαγη «τυχη»).
ΠΡΟ-ΔΗΛΩΣΗ (γραφτηκε ΠΡΙΝ δουμε αποδοσεις, ΜΙΑ εκτελεση):
  ΡΥΘΜΙΣΗ: HL {30,60,120,9999} × λ {2,4,8,14,24} × carry {0.3,0.5,0.7} × h {2,3,4,5,6} × {raw, L} — RMSE διαφορας στις U2017-U2019 (χωρις αποδοσεις).
  ΚΡΙΣΗ (παγωμενες παραμετροι) στις U2020-U2025 vs Crown κλεισιμο:
    Κ1 ακριβεια (RMSE διαφορας/συνολου μοντελο vs αγορα — αναμενεται αγορα καλυτερη).
    Κ2 «προσθετει πληροφορια»: κλιση b του (πραγματικο − αγορα) πανω στο (μοντελο − αγορα) · ΠΕΡΝΑ αν b ≥ 0.15 ΚΑΙ t ≥ 2 ΚΑΙ b > 0 σε ≥ 4/6 σεζον.
    Κ3 ROI (αναφορα): picks edge ≥8% στην τιμη ΚΛΕΙΣΙΜΑΤΟΣ και στο ΑΝΟΙΓΜΑ Crown (σ 11.5 διαφορα / 16.7 συνολο, οπως η Ευρωλιγκα).
Εξοδος: ec_model_test_out.txt"""
import sys, json, math, re
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
src = open('el_model_test.py', encoding='utf-8').read()
head = src.split('# ---------------- ρυθμιση (χωρις αποδοσεις) ----------------')[0]
head = head.replace("B = json.load(open('el_box.json', encoding='utf-8'))",
                    "B = {k: v for k, v in json.load(open('el_players.json', encoding='utf-8')).items() if v.get('comp') == 'U'}")
head = head.replace("open('el_model_test_out.txt'", "open('_unused_ec.txt'")
NS = {}
exec(head, NS)
D, run, P, out = NS['D'], NS['run'], NS['P'], NS['out']
out.clear(); out.append('EUROCUP — ' + ' '.join(sorted(D.season.unique())) + f' · ματς {len(D)}')
act = (D.hs - D.as_).values.astype(float); tot = (D.hs + D.as_).values.astype(float)
TUNE = D.season.isin(['U2017', 'U2018', 'U2019']).values
import itertools
res = []
for HL, lam, carry, h, var in itertools.product([30, 60, 120, 9999], [2, 4, 8, 14, 24], [0.3, 0.5, 0.7], [2, 3, 4, 5, 6], ['raw', 'L']):
    pr = run(HL, lam, carry, h, var, upto='U2019')
    res.append((math.sqrt(np.mean((act[TUNE] - pr[TUNE, 0]) ** 2)), HL, lam, carry, h, var))
res.sort()
P('=== ΡΥΘΜΙΣΗ U2017-U2019 (RMSE διαφορας, χωρις αποδοσεις) ===')
for r in res[:5]: P(f'  RMSE {r[0]:.3f} · HL {r[1]} · λ {r[2]} · carry {r[3]} · h {r[4]} · {r[5]}')
_, HL, lam, carry, h, var = res[0]
P(f'ΠΑΓΩΜΕΝΟ: HL={HL} λ={lam} carry={carry} h={h} {var}')
PR = run(HL, lam, carry, h, var)
D['m'] = PR[:, 0]; D['tm'] = PR[:, 1]
# ---- αγορα: Crown απο Nowgoal ----
SCH = {}
for sea in ('20-21', '21-22', '22-23', '23-24', '24-25', '25-26'):
    for g in json.load(open(f'nowgoal_ec/sched_{sea}.json', encoding='utf-8')):
        if g.get('hs') is not None: SCH[g['ngid']] = g
ROWS = {}
for ln in open('nowgoal_ec/odds.jsonl', encoding='utf-8'):
    r = json.loads(ln)
    if r['cid'] == 3 and r['t'] in (21, 23): ROWS[(r['ngid'], r['t'])] = r['rows']
idx = {}
for i in range(len(D)):
    idx.setdefault((int(D.hs.values[i]), int(D.as_.values[i])), []).append(i)
MKT = {}
N = NormalDist()
for ng, g in SCH.items():
    tip = pd.Timestamp(g['bj']) - pd.Timedelta(hours=8)
    hit, sw = None, False
    for i in idx.get((g['hs'], g['as_']), []):
        if abs(pd.Timestamp(D.t.values[i]).tz_localize(None) - tip) <= pd.Timedelta(hours=26): hit = i; break
    if hit is None:
        for i in idx.get((g['as_'], g['hs']), []):
            if abs(pd.Timestamp(D.t.values[i]).tz_localize(None) - tip) <= pd.Timedelta(hours=26): hit, sw = i, True; break
    if hit is None: continue
    tsec = tip.timestamp()
    rec = {}
    for t_ in (21, 23):
        rows = sorted([x for x in ROWS.get((ng, t_), []) if x[4] == 2 and x[1] is not None and x[2] and x[3]], key=lambda x: x[0])
        rows = [x for x in rows if x[0] + 8 * 3600 <= tsec + 600]
        if len(rows) < 1: continue
        for nm, x in (('o', rows[0]), ('c', rows[-1])):
            o1, o2 = 1 + x[2], 1 + x[3]; ph = (1 / o1) / (1 / o1 + 1 / o2)
            if t_ == 21:
                L = -x[1]; mu = -L + 11.5 * N.inv_cdf(min(max(ph, 1e-4), 1 - 1e-4))
                if sw: L, mu, o1, o2 = -L, -mu, o2, o1
                rec[f'sp_{nm}'] = (L, o1, o2, mu)
            else:
                mu = x[1] + 16.7 * N.inv_cdf(min(max(ph, 1e-4), 1 - 1e-4))
                rec[f'tot_{nm}'] = (x[1], o1, o2, mu)
    if rec: MKT[hit] = rec
E = D.loc[sorted(MKT)].copy()
E['mc'] = [MKT[i].get('sp_c', (None,) * 4)[3] for i in E.index]; E['tc'] = [MKT[i].get('tot_c', (None,) * 4)[3] for i in E.index]
E = E[E.season >= 'U2020']
P(f'ματς αξιολογησης με Crown (U2020-U2025): {len(E)} · χαντικαπ {E.mc.notna().sum()} · συνολο {E.tc.notna().sum()}')
Ea = (E.hs - E.as_).values.astype(float); Et = (E.hs + E.as_).values.astype(float)
def k2(y, mod, mk, lab):
    ok = np.isfinite(mk.astype(float)); y, mod, mk = y[ok], mod[ok], mk[ok].astype(float); ss = E.season.values[ok]
    x = mod - mk; z = y - mk; b = np.polyfit(x, z, 1)[0]; r = z - np.polyval(np.polyfit(x, z, 1), x)
    se = math.sqrt(np.sum(r ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2))
    per = {Y: np.polyfit(x[ss == Y], z[ss == Y], 1)[0] for Y in sorted(set(ss)) if (ss == Y).sum() > 30}
    pos = sum(v > 0 for v in per.values())
    P(f'  {lab}: RMSE μοντελο {np.sqrt(np.mean((y - mod) ** 2)):.2f} · αγορα {np.sqrt(np.mean((y - mk) ** 2)):.2f} · Κ2 b {b:+.3f} (t {b/se:+.1f}) · θετικη {pos}/{len(per)} σεζον ['
      + ' '.join(f'{k[-2:]}:{v:+.2f}' for k, v in per.items()) + ']' + ('  → ΠΕΡΝΑ' if b >= 0.15 and b / se >= 2 and pos >= 4 else '  → ✗'))
P(''); P('=== Κ1/Κ2 απεναντι στο κλεισιμο Crown ===')
k2(Ea, E.m.values, E.mc.values, 'ΔΙΑΦΟΡΑ (χαντικαπ)')
k2(Et, E.tm.values, E.tc.values, 'ΣΥΝΟΛΟ')
# ---- Κ3 ROI ----
Phi = N.cdf
def cov(mu, L, s):
    if abs(L - round(L)) < 1e-9:
        pw = Phi((mu + L - 0.5) / s); pl = Phi((-mu - L - 0.5) / s); return pw, 1 - pw - pl
    return Phi((mu + L) / s), 0.0
P(''); P('=== Κ3 ROI picks edge ≥8% (Crown) ===')
for when, lab in (('c', 'ΚΛΕΙΣΙΜΟ'), ('o', 'ΑΝΟΙΓΜΑ')):
    R = {'χαντικαπ': [], 'over': [], 'under': []}
    for i in E.index:
        mk = MKT[i]; s = D.season.values[i]
        if f'sp_{when}' in mk:
            L, o1, o2, _ = mk[f'sp_{when}']; m = D.m.values[i]; pw, pp = cov(m, L, 11.5); pl = 1 - pw - pp
            e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
            side, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
            if e >= 0.08:
                v = (act[i] + L) * side; R['χαντικαπ'].append(((od - 1) if v > 0 else (0 if v == 0 else -1), s))
        if f'tot_{when}' in mk:
            T, oo, ou, _ = mk[f'tot_{when}']; t = D.tm.values[i]; po, pq = cov(t, -T, 16.7); pu = 1 - po - pq
            eo, eu = po * oo + pq - 1, pu * ou + pq - 1
            if max(eo, eu) >= 0.08:
                ov = eo >= eu; v = (tot[i] - T) * (1 if ov else -1); od = oo if ov else ou
                R['over' if ov else 'under'].append(((od - 1) if v > 0 else (0 if v == 0 else -1), s))
    for k, L in R.items():
        if not L: continue
        a = np.array([x[0] for x in L]); ss = [x[1] for x in L]
        per = ' '.join(f'{Y[-2:]}:{np.mean([x[0] for x in L if x[1] == Y])*100:+.0f}%' for Y in sorted(set(ss)))
        pos = sum(1 for Y in set(ss) if np.mean([x[0] for x in L if x[1] == Y]) > 0)
        P(f'  {lab:9s} {k:9s} n {len(a):4d} · ROI {a.mean()*100:+6.1f}% · μοναδες {a.sum():+6.1f} · θετικες {pos}/{len(set(ss))} [{per}]')
open('ec_model_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
