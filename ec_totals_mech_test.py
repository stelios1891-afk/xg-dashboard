# -*- coding: utf-8 -*-
"""ec_totals_mech_test.py — EuroCup ΣΥΝΟΛΑ: ΔΟΚΙΜΕΣ ΜΗΧΑΝΙΣΜΩΝ (5/10/2026, Στελιος «δοκιμασε πραγματα στα συνολα»).
Σημερα live: το συνολο βγαινει απο τη μηχανη του ΧΑΝΤΙΚΑΠ (τυχη .5, περσι .2, μ_w 5, λ 4) — προβλεπει ~1.7 π. χαμηλα.
ΜΗΧΑΝΙΣΜΟΙ (ο καθενας με προ-δηλωμενο πλεγμα):
  Μ1 ΜΗΧΑΝΗ ΣΥΝΟΛΩΝ τυπου Ευρωλιγκας (v2: τυχη .25, περσι .7, επιπεδο λιγκας «κολλητο» μ_w 50, χωρις φθορα) — λ {4, 8}
  Μ2 ΚΑΜΠΥΛΗ ΣΕΖΟΝ (οπως Ευρωλιγκα): συνολο += a + b·(αριθμος αγωνα), a/b απο τις ΑΛΛΕΣ σεζον
  Μ3 ΦΕΤΙΝΑ ΕΓΧΩΡΙΑ ΣΚΟΡ: ταση ομαδας = (ποντοι γηπ+φιλ στα εγχωρια της − μεσος πρωταθληματος), συρρικνωση n/(n+6) προς
     ½·περσινη εγχωρια ταση · συνολο += κd·(ταση γηπ + ταση φιλ), κd {0, .1, .2, .3, .4, .6}
  Μ4 ΕΠΙΠΕΔΟ ΠΡΩΤΑΘΛΗΜΑΤΟΣ: (μεσο συνολο εγχωριου πρωταθληματος − γενικος μεσος) · συνολο += κl·(γηπ + φιλ), κl {0, .25, .5}
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση): LOSO U2018-U2025 (8 σεζον, χωρις αποδοσεις) σε ΟΛΟ το πλεγμα με RMSE συνολου →
  ΑΛΛΑΓΗ αν καλυτερο απο το live σε ≥6/8. Επισης καθε μηχανισμος μονος του πανω στο live (ιδιο κριτηριο).
  EDGE (Crown U2020-25): Κ2 vs κλεισιμο b ≥ .15 ΚΑΙ t ≥ 2 ΚΑΙ θετικο ≥4/6 = ΠΕΡΝΑ · ROI over/under = αναφορα.
Εξοδος: ec_totals_mech_out.txt"""
import sys, io, contextlib, math, itertools, collections
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
EC = {'__name__': 'y'}
exec(open('ec_season_backtest.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", '', 1)
     .replace("open('ec_season_backtest_out.txt', 'w', encoding='utf-8')", "open('_unused_ecsb.txt', 'w', encoding='utf-8')"), EC)
D, run2T, MKT, TOT, GN, seasn = EC['D'], EC['run2T'], EC['MKT'], EC['TOT'], EC['GN'], EC['seasn']
INNER = EC['NS']; MAPD, DOMNS = INNER['MAPD'], INNER['DOMNS']
EVM = EC['EVM']; EV8 = ['U2018', 'U2019', 'U2020', 'U2021', 'U2022', 'U2023', 'U2024', 'U2025']
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
Phi = NormalDist().cdf
# ---- μηχανες ----
ENG = {'live (χαντικαπ)': (9999, 4, 5.0, .5, 5, .2, 4.0, .5), 'v2 λ4': (9999, 4, 6.0, .25, 50, .7, 0.0, 0.0), 'v2 λ8': (9999, 8, 6.0, .25, 50, .7, 0.0, 0.0)}
TP = {k: run2T(*v)[1] for k, v in ENG.items()}
P('μηχανες ετοιμες: ' + ' · '.join(f'{k}: μεση μεροληψια {np.nanmean((TOT - v)[np.isin(seasn, EV8)]):+.2f}' for k, v in TP.items()))
# ---- εγχωρια ταση & επιπεδο ----
DOM = DOMNS['DOM']
LG = collections.defaultdict(list); TM = collections.defaultdict(list)
for k, v in DOM.items():
    L, sea = k.split('_')
    for g in v['games']:
        try: tt = int(g[4]) + int(g[5])
        except Exception: continue
        ts = pd.Timestamp(g[1]).tz_localize(None).timestamp()
        LG[(L, sea)].append((ts, tt))
        for tid in (g[2], g[3]): TM[(L, sea, int(tid))].append((ts, tt))
for d_ in (LG, TM):
    for k in d_: d_[k].sort()
FULLM = {k: np.mean([x[1] for x in v]) for k, v in LG.items()}
SEAM = collections.defaultdict(list)
for (L, sea), m in FULLM.items(): SEAM[sea].append(m)
SEAM = {s: np.mean(v) for s, v in SEAM.items()}
def prev_sea(sea): a = int(sea[:2]); return f'{(a - 1) % 100:02d}-{a % 100:02d}'
TS = np.array([pd.Timestamp(t).tz_localize(None).timestamp() if pd.Timestamp(t).tzinfo else pd.Timestamp(t).timestamp() for t in D.t])
def feats(i, c):
    m = MAPD.get((seasn[i], c))
    if not m: return 0.0, 0.0, 0
    y = int(m[0][1:]); sea = f'{y % 100:02d}-{(y + 1) % 100:02d}'; L, tid = m[2], int(m[1])
    lg = [x[1] for x in LG.get((L, sea), []) if x[0] < TS[i] - 3600]
    tg = [x[1] for x in TM.get((L, sea, tid), []) if x[0] < TS[i] - 3600]
    ps = prev_sea(sea); tp = [x[1] for x in TM.get((L, ps, tid), [])]
    dprev = (np.mean(tp) - FULLM[(L, ps)]) if len(tp) >= 10 and (L, ps) in FULLM else 0.0
    lgm = np.mean(lg) if len(lg) >= 20 else FULLM.get((L, ps), np.nan)
    n = len(tg); dcur = (np.mean(tg) - lgm) if n and np.isfinite(lgm) else 0.0
    trend = (n * dcur + 6 * .5 * dprev) / (n + 6)
    lvl = (lgm - SEAM.get(sea, SEAM.get(ps, lgm))) if np.isfinite(lgm) else 0.0
    return trend, lvl, n
FT = np.zeros(len(D)); FL = np.zeros(len(D)); NN_ = np.zeros(len(D))
for i in range(len(D)):
    th, lh, nh = feats(i, D.home.values[i]); ta, la, na = feats(i, D.away.values[i])
    FT[i] = th + ta; FL[i] = (lh if np.isfinite(lh) else 0) + (la if np.isfinite(la) else 0); NN_[i] = min(nh, na)
P(f'εγχωρια ταση: sd {FT[np.isin(seasn, EV8)].std():.1f} π. · επιπεδο: sd {FL[np.isin(seasn, EV8)].std():.1f} π. · ματς με ≥3 εγχωρια και οι 2: {(NN_ >= 3)[np.isin(seasn, EV8)].mean():.0%}')
# ---- πλεγμα ----
KD = (0, .1, .2, .3, .4, .6); KL = (0, .25, .5)
def rm(v, ss, msk=None):
    m = np.isin(seasn, ss) & np.isfinite(v) & (msk if msk is not None else True); return float(np.sqrt(np.mean((TOT - v)[m] ** 2)))
def curve_fold(v, Y):
    tr = np.isin(seasn, [x for x in EV8 if x != Y] + ['U2017']) & np.isfinite(v)
    b, a = np.polyfit(GN[tr], (TOT - v)[tr], 1); return a, b
def build(eng, kd, kl, cv):
    """προβλεψη με LOSO-καμπυλη: για καθε σεζον Y η καμπυλη απο τις αλλες."""
    v = TP[eng] + kd * FT + kl * FL
    if not cv: return v
    w = v.copy()
    for Y in EV8 + ['U2017']:
        a, b = curve_fold(v, Y); m = seasn == Y; w[m] = v[m] + a + b * GN[m]
    return w
GRID = list(itertools.product(ENG, KD, KL, (0, 1)))
PRED = {g: build(*g) for g in GRID}
BASE = ('live (χαντικαπ)', 0, 0, 0)
P(''); P(f'=== IN-SAMPLE RMSE συνολου U2018-25 · live {rm(PRED[BASE], EV8):.3f} · καλυτερα 8 ===')
for g in sorted(GRID, key=lambda g: rm(PRED[g], EV8))[:8]: P(f'  {g}: {rm(PRED[g], EV8):.3f} (αγων 1-6 {rm(PRED[g], EV8, GN <= 5):.3f})')
def loso(keys, lab):
    held = np.full(len(D), np.nan); ch = []
    for Y in EV8:
        tr = [x for x in EV8 if x != Y]; k = min(keys, key=lambda k: rm(PRED[k], tr)); ch.append(k)
        m = seasn == Y; held[m] = PRED[k][m]
    d = [rm(held, [Y]) - rm(PRED[BASE], [Y]) for Y in EV8]
    ok = sum(x < 0 for x in d) >= 6
    P(f'  {lab:34s} {rm(PRED[BASE], EV8):.3f} → {rm(held, EV8):.3f} · ' + ' '.join(f'{Y[-2:]}:{x:+.2f}' for Y, x in zip(EV8, d)) + f' → {sum(x < 0 for x in d)}/8' + ('  <- ΑΛΛΑΓΗ' if ok else '  <- ✗'))
    P(f'     επιλογες: {collections.Counter(ch).most_common(3)}')
    return held, ok
P(''); P('=== LOSO (καθε μηχανισμος μονος του πανω στο live · μετα ολο το πλεγμα) ===')
H = {}
H['Μ1 μηχανη v2'] = loso([g for g in GRID if g[1:] == (0, 0, 0)], 'Μ1 μηχανη τυπου EL (v2)')
H['Μ2 καμπυλη'] = loso([BASE, ('live (χαντικαπ)', 0, 0, 1)], 'Μ2 καμπυλη σεζον')
H['Μ3 εγχωρια ταση'] = loso([('live (χαντικαπ)', kd, 0, 0) for kd in KD], 'Μ3 φετινα εγχωρια σκορ')
H['Μ4 επιπεδο'] = loso([('live (χαντικαπ)', 0, kl, 0) for kl in KL], 'Μ4 επιπεδο πρωταθληματος')
H['ΟΛΟ το πλεγμα'] = loso(GRID, 'ΟΛΟ το πλεγμα')
# ---- edge vs Crown ----
def k2(x, z):
    b = np.polyfit(x, z, 1)[0]; r_ = z - np.polyval(np.polyfit(x, z, 1), x); se = math.sqrt(np.sum(r_ ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2)); return b, b / se
def cov(mu, T, s):
    if abs(T - round(T)) < 1e-9: po = Phi((mu - T - .5) / s); pu = Phi((T - mu - .5) / s); return po, 1 - po - pu, pu
    po = Phi((mu - T) / s); return po, 0.0, 1 - po
def evaluate(v, lab):
    P(f'  [{lab}]')
    for per, f in (('ολη η σεζον', lambda g: g >= 0), ('αγων 1-6', lambda g: g <= 5), ('αγων 7+', lambda g: g >= 6)):
        ii = [i for i in MKT if seasn[i] in EVM and np.isfinite(v[i]) and f(GN[i])]
        mc = np.array([MKT[i]['c'][1] for i in ii]); a = TOT[ii]; m = v[ii]; ss = seasn[ii]
        b, t = k2(m - mc, a - mc); pers = [np.polyfit((m - mc)[ss == Y], (a - mc)[ss == Y], 1)[0] for Y in EVM if (ss == Y).sum() > 20]
        ok = b >= .15 and t >= 2 and sum(x > 0 for x in pers) >= 4
        cells = []
        for wl, wm, thr in (('μοντελο ≥8%', 1.0, .08), ('μιξη ≥6%', .5, .06)):
            R = {'o': [], 'u': []}
            for i in ii:
                T, mk, oo, ou = MKT[i]['o']; mu = mk + wm * (v[i] - mk); po, pq, pu = cov(mu, T, 16.7)
                eo, eu = po * oo + pq - 1, pu * ou + pq - 1
                if max(eo, eu) >= thr:
                    ov = eo >= eu; q = (TOT[i] - T) * (1 if ov else -1); od = oo if ov else ou
                    R['o' if ov else 'u'].append(((od - 1) if q > 0 else (0 if q == 0 else -1), seasn[i]))
            allr = R['o'] + R['u']; aa = np.array([q[0] for q in allr]); pos = sum(1 for Y in EVM if [q for q in allr if q[1] == Y] and np.mean([q[0] for q in allr if q[1] == Y]) > 0)
            cells.append(f'{wl} ανοιγμα {aa.mean()*100 if len(aa) else 0:+.1f}% ({len(aa)}: over {len(R["o"])}/under {len(R["u"])}, {aa.sum():+.1f}u, {pos}/6)')
        P(f'     {per:12s} λαθος μοντ. {np.sqrt(np.mean((a - m) ** 2)):.2f} / κλεισ. {np.sqrt(np.mean((a - mc) ** 2)):.2f} · Κ2 b {b:+.2f} (t {t:+.1f}, θετ. {sum(x > 0 for x in pers)}/{len(pers)})'
          + ('  ΠΕΡΝΑ' if ok else '  ✗') + ' · ' + ' · '.join(cells))
P(''); P('=== EDGE vs Crown (U2020-25) ===')
evaluate(PRED[BASE], 'live σημερα')
for k, (held, ok) in H.items(): evaluate(held, f'LOSO {k}' + (' (περασε)' if ok else ' (δεν περασε)'))
open('ec_totals_mech_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
