# -*- coding: utf-8 -*-
"""ec_timing_factors_test.py — EuroCup ΑΠΟ ΤΗΝ ΑΡΧΗ, βηματα 3 & 4 (5/10/2026, Στελιος «τρεξε τα 2 και 3»).
ΒΗΜΑ 3 — ΧΡΟΝΙΣΜΟΣ: ποτε συμφερει να μπαινουμε; Crown (Nowgoal) ολο το ιστορικο γραμμης χαντικαπ U2020-25.
  Σημεια: ΑΝΟΙΓΜΑ · 12ω · 6ω · 3ω · 1ω πριν · ΚΛΕΙΣΙΜΟ. Σε καθε σημειο: picks με (α) σημερινο κανονα (μοντελο, σ 11.5, ≥8%)
  (β) μιξη 50/50 με την αγορα ΕΚΕΙΝΗΣ της στιγμης (σ 12.3, ≥6%) → πληθος, ROI, θετικες σεζον.
  + για τα picks του ανοιγματος: πού πηγε η γραμμη (CLV σε ποντους) και ποσα ειναι ακομα picks στο κλεισιμο.
  ΠΡΟ-ΔΗΛΩΜΕΝΟ: «αργοτερα ειναι καλυτερα» μονο αν το ROI σε ενα σημειο ξεπερνα το ανοιγμα σε ≥4/6 σεζον (ιδια ματς: ανοιχτα ≥12ω πριν).
ΒΗΜΑ 4 — ΠΑΡΑΓΟΝΤΕΣ ΤΟΥ EUROCUP: ξεκουραση (μερες απο το προηγουμενο ματς, ΟΠΟΙΑΣΔΗΠΟΤΕ διοργανωσης), εγχωριο ματς ≤2 μερες μετα
  (μυαλο στο πρωταθλημα), ταξιδι (αποσταση χωρων), ιδια χωρα, «χαμενη» ομαδα στις 3 τελευταιες της κανονικης περιοδου,
  εδρα στα νοκ-αουτ/πλει-οφ.
  ΜΕΤΡΟ: υπολοιπο vs ΚΛΕΙΣΙΜΟ (πραγματικο − αγορα) πανω στον παραγοντα, και vs ΜΟΝΤΕΛΟ (πραγματικο − live ec1).
  ΠΡΟ-ΔΗΛΩΜΕΝΟ: «η αγορα τον χανει» αν |t| ≥ 2 vs κλεισιμο ΚΑΙ ιδιο προσημο σε ≥4/6 σεζον ΚΑΙ μεγεθος ≥0.5 ποντο.
Εξοδος: ec_timing_factors_out.txt"""
import sys, json, math, pickle, datetime as dt
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
src = open('ec_fresh_engine_test.py', encoding='utf-8').read()
src = src.split("LIVE = (9999, 4, 5.0, .5, 5, .2, 4.0, .5)")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '', 1)
NS = {'__name__': 'x'}
exec(src, NS)
D, GN, MAPD, DOMNS = NS['D'], NS['GN'], NS['MAPD'], NS['DOMNS']
Z = pickle.load(open('ec_fresh_market.pkl', 'rb')); MODEL = Z['live']
ACT = (D.hs - D.as_).values.astype(float); seasn = D.season.values
EVM = ['U2020', 'U2021', 'U2022', 'U2023', 'U2024', 'U2025']
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
NN = NormalDist(); Phi = NN.cdf
# ---- Crown ολο το ιστορικο ----
SCH = {}
for sea in ('20-21', '21-22', '22-23', '23-24', '24-25', '25-26'):
    for g in json.load(open(f'nowgoal_ec/sched_{sea}.json', encoding='utf-8')):
        if g.get('hs') is not None: SCH[g['ngid']] = g
ROWS = {}
for ln in open('nowgoal_ec/odds.jsonl', encoding='utf-8'):
    r = json.loads(ln)
    if r['cid'] == 3 and r['t'] == 21: ROWS[r['ngid']] = r['rows']
ix2 = {}
for i in range(len(D)): ix2.setdefault((int(D.hs.values[i]), int(D.as_.values[i])), []).append(i)
HIST = {}   # i -> (tip_ts, [(ts, L, mu, o1, o2)])
for ng, g in SCH.items():
    tip = pd.Timestamp(g['bj']) - pd.Timedelta(hours=8); hit, sw = None, False
    for (a_, b_), swp in (((g['hs'], g['as_']), False), ((g['as_'], g['hs']), True)):
        for i in ix2.get((a_, b_), []):
            if abs(pd.Timestamp(D.t.values[i]).tz_localize(None) - tip) <= pd.Timedelta(hours=26): hit, sw = i, swp; break
        if hit is not None: break
    if hit is None or seasn[hit] not in EVM: continue
    rows = sorted([x for x in ROWS.get(ng, []) if x[4] == 2 and x[1] is not None and x[2] and x[3] and x[0] + 8 * 3600 <= tip.timestamp() + 600], key=lambda x: x[0])
    if not rows: continue
    def conv(x):
        o1, o2 = 1 + x[2], 1 + x[3]; L = -x[1]; ph = (1 / o1) / (1 / o1 + 1 / o2); mu = -L + 11.5 * NN.inv_cdf(min(max(ph, 1e-4), 1 - 1e-4))
        return (x[0] + 8 * 3600,) + ((-L, -mu, o2, o1) if sw else (L, mu, o1, o2))
    HIST[hit] = (tip.timestamp(), [conv(x) for x in rows])
P(f'ματς με ιστορικο Crown: {len(HIST)} · ωρες πριν το τζαμπολ που ανοιγει (διαμεσος) {np.median([(t - h[0][0]) / 3600 for t, h in HIST.values()]):.1f}')
def at(i, cp):
    tip, h = HIST[i]
    if cp == 'open': return h[0]
    if cp == 'close': return h[-1]
    lim = tip - cp * 3600; c = [x for x in h if x[0] <= lim]
    return c[-1] if c else None
def cover(m_, L, s):
    if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
    pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
def settle(i, side, L, od):
    v = (ACT[i] + L) * side; return (od - 1) if v > 0 else (0 if v == 0 else -1)
RULES = {'σημερινος (μοντελο σ11.5 ≥8%)': (1.0, 11.5, .08), 'μιξη 50/50 (σ12.3 ≥6%)': (.5, 12.3, .06)}
def pick(i, x, rule):
    wm, sg, thr = RULES[rule]; _, L, mk, o1, o2 = x; m_ = mk + wm * (MODEL[i] - mk)
    pw, pp, pl = cover(m_, L, sg); e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
    s, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
    return (s, L, od, e) if e >= thr else None
CPS = ('open', 12, 6, 3, 1, 'close')
P(''); P('################ ΒΗΜΑ 3 — ΧΡΟΝΙΣΜΟΣ ################')
early = {i for i in HIST if (HIST[i][0] - HIST[i][1][0][0]) / 3600 >= 12 and np.isfinite(MODEL[i])}
P(f'  ιδια ματς για συγκριση: {len(early)} (ανοιχτα ≥12ω πριν)')
for rule in RULES:
    P(f'  [{rule}]')
    base = None
    for per, f in (('ολη η σεζον', lambda g: g >= 0), ('αγων 1-6', lambda g: g <= 5)):
        P(f'   {per}:')
        for cp in CPS:
            R = []
            for i in early:
                if not f(GN[i]): continue
                x = at(i, cp)
                if x is None: continue
                p = pick(i, x, rule)
                if p: R.append((settle(i, p[0], p[1], p[2]), seasn[i]))
            a = np.array([q[0] for q in R]); per_s = {Y: np.mean([q[0] for q in R if q[1] == Y]) for Y in EVM if any(q[1] == Y for q in R)}
            if cp == 'open': base = per_s
            better = sum(1 for Y in per_s if Y in base and per_s[Y] > base[Y]) if cp != 'open' else None
            P(f'     {str(cp) + ("ω πριν" if isinstance(cp, int) else ""):10s} picks {len(a):4d} · ROI {a.mean()*100 if len(a) else 0:+6.1f}% · {a.sum():+6.1f}u · θετ. {sum(v > 0 for v in per_s.values())}/{len(per_s)}'
              + (f' · καλυτερο απο ανοιγμα σε {better}/{len(per_s)}' if better is not None else ''))
    # CLV picks ανοιγματος
    clv, still, edge_o, edge_c = [], 0, [], []
    for i in early:
        p = pick(i, at(i, 'open'), rule)
        if not p: continue
        xo, xc = at(i, 'open'), at(i, 'close'); clv.append(p[0] * (xc[2] - xo[2]))
        if pick(i, xc, rule) and pick(i, xc, rule)[0] == p[0]: still += 1
    clv = np.array(clv)
    P(f'   picks ανοιγματος {len(clv)}: η αγορα κινηθηκε ΥΠΕΡ μας {clv.mean():+.2f} ποντους κατα μεσο ορο · υπερ {np.mean(clv > .05)*100:.0f}% / κατα {np.mean(clv < -.05)*100:.0f}% · ακομα pick στο κλεισιμο {still/len(clv)*100:.0f}%')
# κινηση γραμμης ανα ωρα (ποσο αλλαζει η αγορα)
mv = {cp: np.mean([abs(at(i, cp)[2] - at(i, 'close')[2]) for i in early if at(i, cp)]) for cp in ('open', 12, 6, 3, 1)}
P('  μεση αποσταση αγορας απο το κλεισιμο (ποντοι): ' + ' · '.join(f'{k}: {v:.2f}' for k, v in mv.items()))
# ================= ΒΗΜΑ 4 =================
P(''); P('################ ΒΗΜΑ 4 — ΠΑΡΑΓΟΝΤΕΣ ΤΟΥ EUROCUP ################')
COORD = {'ACB': (40.4, -3.7), 'LBA': (41.9, 12.5), 'GBL': (37.98, 23.7), 'TBL': (41.0, 29.0), 'LNB': (48.85, 2.35), 'BBL': (52.5, 13.4),
         'LKL': (54.7, 25.3), 'VTB': (55.75, 37.6), 'ABA': (44.8, 20.5), 'ISR': (32.1, 34.8), 'PLK': (52.2, 21.0), 'ROM': (44.4, 26.1),
         'GBR': (51.5, -0.1), 'BNX': (50.85, 4.35), 'LEL': (56.95, 24.1), 'UKR': (50.45, 30.5)}
def km(a, b):
    (la1, lo1), (la2, lo2) = COORD[a], COORD[b]; p = math.pi / 180
    h = math.sin((la2 - la1) * p / 2) ** 2 + math.cos(la1 * p) * math.cos(la2 * p) * math.sin((lo2 - lo1) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))
DOM = DOMNS['DOM']
domdates = {}
for key, v in DOM.items():
    L, sea = key.split('_')
    for g in v['games']:
        t = pd.Timestamp(g[1]).tz_localize(None).timestamp()
        for tid in (g[2], g[3]): domdates.setdefault((L, sea, int(tid)), []).append(t)
for k in domdates: domdates[k].sort()
ecdates = {}
TS = np.array([pd.Timestamp(t).tz_localize(None).timestamp() if pd.Timestamp(t).tzinfo else pd.Timestamp(t).timestamp() for t in D.t])
for i in range(len(D)):
    for c in (D.home.values[i], D.away.values[i]): ecdates.setdefault((seasn[i], c), []).append(TS[i])
def team_info(i, c):
    Y = seasn[i]; t = TS[i]; m = MAPD.get((Y, c)); L = m[2] if m else None
    alld = list(ecdates.get((Y, c), []))
    dd = []
    if m:
        y = int(m[0][1:]); dd = domdates.get((L, f'{y % 100:02d}-{(y + 1) % 100:02d}', int(m[1])), [])
    prev = [x for x in alld + dd if x < t - 3600]; nxt = [x for x in dd if x > t + 3600]
    rest = min(7.0, (t - max(prev)) / 86400) if prev else 7.0
    dom_next = min(7.0, (min(nxt) - t) / 86400) if nxt else 7.0
    return L, rest, dom_next, bool(m)
# ρεκορ για «χαμενη» ομαδα (κανονικη περιοδος)
rs_total = {}
for Y in set(seasn):
    s = D[(D.season == Y) & (D.phase == 'RS')]
    for c in set(s.home) | set(s.away): rs_total[(Y, c)] = int(((s.home == c) | (s.away == c)).sum())
rec = {}; REC = {}
for i in np.argsort(TS):
    Y = seasn[i]; h, a = D.home.values[i], D.away.values[i]
    REC[i] = {c: rec.get((Y, c), (0, 0)) for c in (h, a)}
    if D.phase.values[i] == 'RS':
        hw = ACT[i] > 0
        rec[(Y, h)] = (rec.get((Y, h), (0, 0))[0] + hw, rec.get((Y, h), (0, 0))[1] + 1); rec[(Y, a)] = (rec.get((Y, a), (0, 0))[0] + (not hw), rec.get((Y, a), (0, 0))[1] + 1)
MC = np.full(len(D), np.nan)
for i in HIST: MC[i] = HIST[i][1][-1][2]
F = {k: np.full(len(D), np.nan) for k in ('rest_diff', 'home_b2b', 'away_b2b', 'home_domnext', 'away_domnext', 'travel_k', 'same_country', 'dead_side', 'ko_home')}
cover_ok = 0
for i in HIST:
    h, a = D.home.values[i], D.away.values[i]
    Lh, rh, nh, okh = team_info(i, h); La, ra, na, oka = team_info(i, a)
    if okh and oka: cover_ok += 1
    F['rest_diff'][i] = rh - ra
    F['home_b2b'][i] = float(rh <= 1.6); F['away_b2b'][i] = float(ra <= 1.6)
    F['home_domnext'][i] = float(nh <= 2.2) if okh else np.nan; F['away_domnext'][i] = float(na <= 2.2) if oka else np.nan
    if Lh in COORD and La in COORD:
        F['travel_k'][i] = km(Lh, La) / 1000; F['same_country'][i] = float(Lh == La)
    if D.phase.values[i] == 'RS':
        st = []
        for c, s in ((h, 1), (a, -1)):
            w_, n_ = REC[i][c]; left = rs_total.get((seasn[i], c), 99) - n_
            st.append(s if (left <= 3 and n_ >= 5 and w_ / n_ <= .3) else 0)
        F['dead_side'][i] = float(sum(st)) if sum(abs(x) for x in st) == 1 else 0.0   # +1 = ο γηπ «χαμενος», −1 = ο φιλ
    else:
        F['ko_home'][i] = 1.0
P(f'  ματς με αγορα {len(HIST)} · και οι 2 ομαδες με εγχωριο προγραμμα: {cover_ok}')
LAB = {'rest_diff': 'διαφορα ξεκουρασης (μερες, γηπ − φιλ)', 'home_b2b': 'γηπ επαιξε ≤1.5 μερα πριν', 'away_b2b': 'φιλ επαιξε ≤1.5 μερα πριν',
       'home_domnext': 'γηπ εχει εγχωριο ≤2 μερες μετα', 'away_domnext': 'φιλ εχει εγχωριο ≤2 μερες μετα',
       'travel_k': 'ταξιδι φιλ (χιλιαδες χλμ)', 'same_country': 'ιδια χωρα', 'dead_side': '«χαμενη» ομαδα (+1 γηπ / −1 φιλ), 3 τελευταιες RS',
       'ko_home': 'νοκ-αουτ/πλει-οφ (μονο σταθερα = εδρα)'}
for k, x in F.items():
    ii = np.array([i for i in HIST if np.isfinite(x[i]) and np.isfinite(MODEL[i])])
    if k == 'ko_home':
        for lab_, base_ in (('vs κλεισιμο', MC), ('vs μοντελο', MODEL)):
            r = ACT[ii] - base_[ii]; per = [np.mean(r[seasn[ii] == Y]) for Y in EVM if (seasn[ii] == Y).sum() >= 5]
            P(f'  {LAB[k]:44s} n {len(ii):4d} · {lab_}: γηπ {r.mean():+.2f} (t {r.mean()/(r.std()/math.sqrt(len(r))):+.1f}) · σεζον ' + ' '.join(f'{p:+.1f}' for p in per))
        continue
    nz = ii if k in ('rest_diff', 'travel_k') else ii[x[ii] != 0]
    if len(nz) < 20: P(f'  {LAB[k]:44s} λιγα ({len(nz)})'); continue
    cells = []; flag = ''
    for lab_, base_ in (('vs κλεισιμο', MC), ('vs μοντελο', MODEL)):
        r = ACT[ii] - base_[ii]; xx = x[ii]
        if k in ('rest_diff', 'travel_k'):
            b = np.polyfit(xx, r, 1)[0]; rr = r - np.polyval(np.polyfit(xx, r, 1), xx); se = math.sqrt(np.sum(rr ** 2) / (len(xx) - 2) / np.sum((xx - xx.mean()) ** 2))
            per = [np.polyfit(xx[seasn[ii] == Y], r[seasn[ii] == Y], 1)[0] for Y in EVM if (seasn[ii] == Y).sum() >= 20]
            eff = b * (np.std(xx))
        else:
            sel = xx != 0; v = r[sel] * np.sign(xx[sel]); b = v.mean(); se = v.std() / math.sqrt(len(v))
            per = [np.mean(v[seasn[ii][sel] == Y]) for Y in EVM if (seasn[ii][sel] == Y).sum() >= 3]; eff = b
        same = sum(np.sign(p) == np.sign(b) for p in per)
        cells.append(f'{lab_} {b:+.2f} (t {b/se:+.1f}, ιδιο προσημο {same}/{len(per)})')
        if lab_ == 'vs κλεισιμο' and abs(b / se) >= 2 and same >= 4 and abs(eff) >= .5: flag = '  ← Η ΑΓΟΡΑ ΤΟΝ ΧΑΝΕΙ'
    P(f'  {LAB[k]:44s} n {len(nz):4d} · ' + ' · '.join(cells) + flag)
P('  (μοναδα: ποντοι διαφορας γηπεδουχου ανα μοναδα του παραγοντα· για σημαιες = διαφορα οταν ισχυει, απο τη μερια που δειχνει η σημαια)')
open('ec_timing_factors_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
