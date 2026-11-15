# -*- coding: utf-8 -*-
"""el_absence_onoff_test.py — EUROLEAGUE: ΑΠΟΥΣΙΕΣ με ON/OFF αντικτυπο απο 3StepsBasket (9/10/2026, Στελιος «δες τα ολα»).
Το el_absence_totals_test με box-«αμυνα» (κλεψ+κοψ+ριμπ) ΔΕΝ επιβεβαιωθηκε. Εδω ο αντικτυπος ειναι ΠΡΑΓΜΑΤΙΚΟΣ: απο bb3s_data.json, για καθε
παικτη-σεζον: ποντοι ομαδας/αντιπαλου ανα 100 κατοχες ΟΣΟ ΕΙΝΑΙ ΜΕΣΑ vs ΟΣΟ ΕΙΝΑΙ ΕΞΩ (on − off).
  onO = επιθεση (+ = η ομαδα σκοραρει περισσοτερο μαζι του) · onD = αμυνα (+ = ο αντιπαλος σκοραρει περισσοτερο μαζι του = κακος αμυντικος)
  μαζεμα προς 0: × n/(n + 1500), n = 1/(1/κατοχες μεσα + 1/κατοχες εξω).
  ΧΩΡΙΣ ΔΙΑΡΡΟΗ: για σεζον S χρησιμοποιειται ΜΟΝΟ η ΠΡΟΗΓΟΥΜΕΝΗ σεζον του παικτη (Ευρωλιγκα + EuroCup, ολες οι ομαδες, σταθμ. κατοχες)·
  χωρις περσινα → 0 (μεσος).
Απουσια = ιδιος ορισμος με το LIVE (≥3/10 φετινα, λεπτα ≥10′, k 1-3 πληρες / 4-10 μισο).
ΠΡΟ-ΔΗΛΩΜΕΝΑ (ΠΡΙΝ την εκτελεση):
 ΣΥΝΟΛΑ (ποντοι ομαδας − μοντελο): W1 λεπτα [δικα, αντιπ.] · W2 + [δικα×z(onO), αντιπ.×z(onD)] · W4 μονο [δικα×z(onO), αντιπ.×z(onD)].
   ΠΕΡΝΑ αν LOSO RMSE συνολου καλυτερο απο «τιποτα» σε ≥4/5 ΚΑΙ οι δυο on/off συντελεστες ιδιο προσημο ≥4/5 (αναμενομενα: δικα×onO < 0,
   αντιπ.×onD < 0 — λειπει καλος αμυντικος (onD αρνητικο) → ο αντιπαλος του βαζει περισσοτερα) ΚΑΙ μοναδες picks συνολων ≥ τιποτα
   ΚΑΙ ΕΠΙΒΕΒΑΙΩΣΗ EuroCup U2020-25 (απλη βαση): σωστο προσημο ≥4/6 σεζον & t ≥ 2 και για τους δυο.
 ΧΑΝΤΙΚΑΠ: H2 = LIVE (0.922·λεπτα) + c·[w × z(onNet)] (φιλ − γηπ). ΠΕΡΝΑ αν LOSO RMSE διαφορας καλυτερο απο LIVE ≥4/5 ΚΑΙ c ιδιο προσημο ≥4/5
   ΚΑΙ μοναδες picks ≥8% ≥ LIVE ΚΑΙ επιβεβαιωση EuroCup (≥4/6, t ≥ 2).
Εξοδος: el_absence_onoff_out.txt"""
import sys, io, contextlib, json, pickle, collections, math, re, unicodedata
import numpy as np, pandas as pd
from statistics import NormalDist
class _B(io.StringIO):
    def reconfigure(self, **k): pass
ns = {}
with contextlib.redirect_stdout(_B()):
    exec(open('el_line_timing.py', encoding='utf-8').read().split("lp = np.array(lastpre)")[0], ns)
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
D, REC = ns['D'], ns['REC']
NP = pickle.load(open('el_newmodel_preds.pkl', 'rb'))
PL = json.load(open('el_players.json', encoding='utf-8'))
S3 = json.load(open('bb3s_data.json', encoding='utf-8'))
SE = ['E2021', 'E2022', 'E2023', 'E2024', 'E2025']; EC = [f'U{y}' for y in range(2021, 2026)]   # U2020: 3StepsBasket δεν εχει 2019-20 EuroCup → καμια καλυψη (αλλαγη ΠΡΙΝ την εκτελεση: ≥4/5)
Phi = NormalDist().cdf
K_SHR = 1500.0
def tok(s): return [w for w in re.split(r'[^a-z]+', unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode().lower()) if w]
# ---- 3StepsBasket: on/off ανα παικτη-σεζον (σεζον = ετος εναρξης, π.χ. euroleague-2021 = 2020-21 → 2020) ----
PROF = collections.defaultdict(lambda: collections.defaultdict(lambda: np.zeros(7)))   # ονομα-κλειδι → ετος → [Σ onO·n, Σ onD·n, Σ n, κατοχες]
for cid, d in S3.items():
    yr = int(cid.split('-')[1]) - 1
    TT = {t['clubId']: t for t in d.get('teams', [])}
    for club, ps in (d.get('players') or {}).items():
        t = TT.get(club)
        if not t or not ps: continue
        pf = 2 * t['madeTwo'] + 3 * t['madeThree'] + t['madeFt']; pa = 2 * t['oppMadeTwo'] + 3 * t['oppMadeThree'] + t['oppMadeFt']
        op, dp = t['offPossessions'], t['defPossessions']
        tg = t.get('games') or 1
        for p in ps.get('players') or []:
            g = p.get('gamesPlayed') or 0
            if g <= 0 or not p.get('teamPossessionsNet'): continue
            sc = tg / max(g, tg)                         # αν ο παικτης εχει και playoffs που η ομαδα δεν μετρα, κλιμακωση
            ton, tpo = p['teamPoints'] * g * sc, p['teamPossessionsNet'] * g * sc
            oon, opo = p['oppPoints'] * g * sc, p['oppPossessionsNet'] * g * sc
            if op - tpo < 50 or dp - opo < 50 or tpo < 50: continue
            onO = 100 * ton / tpo - 100 * (pf - ton) / (op - tpo); onD = 100 * oon / opo - 100 * (pa - oon) / (dp - opo)
            n = 1 / (1 / tpo + 1 / (op - tpo)); sh = n / (n + K_SHR)
            key = (tuple(tok(p.get('surname'))), (tok(p.get('firstname')) or [''])[0])
            PROF[key][yr] += np.array([onO * sh * tpo, onD * sh * tpo, tpo, p.get('usgRate', 0) * tpo, 0, 0, 0])
def key_of(name):
    s = str(name)
    if ',' in s: sur, fst = s.split(',', 1)
    else: sur, fst = s, ''
    return (tuple(tok(sur)), (tok(fst) or [''])[0])
BYSUR = collections.defaultdict(list)
for k in PROF: BYSUR[k[0]].append(k)
def profile(name, yr):
    k = key_of(name)
    if k not in PROF:
        c = [x for x in BYSUR.get(k[0], []) if x[1][:1] == k[1][:1]]
        if len(c) != 1: return None
        k = c[0]
    v = PROF[k].get(yr - 1)
    if v is None or v[2] <= 0: return None
    return dict(onO=v[0] / v[2], onD=v[1] / v[2], usg=v[3] / v[2])
# ---- ματς παικτων ----
TG = collections.defaultdict(list); NAME = {}; GM = []
for k, g in PL.items():
    if 'ph' not in g or 'pa' not in g or g.get('hs') is None: continue
    ts = pd.Timestamp(g['utc']).timestamp()
    for side, tc in (('ph', 'hcode'), ('pa', 'acode')):
        for p in g[side]: NAME[p[0]] = p[1]
        TG[(g['season'], g[tc])].append((ts, {p[0]: p[3] or 0.0 for p in g[side]}))
    if g['season'] in EC: GM.append((g['season'], ts, g['hcode'], g['acode'], float(g['hs']), float(g['as_'])))
for v in TG.values(): v.sort(key=lambda x: x[0])
PH = collections.defaultdict(list)
for L in TG.values():
    for ts, d in L:
        for pid, mn in d.items():
            if mn > 0: PH[pid].append((ts, mn))
for v in PH.values(): v.sort()
NOPROF = collections.Counter()
def absents(sea, team, ts):
    L = TG.get((sea, team), []); prev = [x for x in L if x[0] < ts - 3600]; today = next((x[1] for x in L if abs(x[0] - ts) < 3600), None)
    if today is None: return None
    cnt = collections.Counter(p for _, d in prev[-10:] for p, v in d.items() if v > 0); res = []
    for pid, c in cnt.items():
        if c < 3 or today.get(pid, 0) > 0: continue
        k = 0
        for _, d in reversed(prev):
            if d.get(pid, 0) > 0: break
            k += 1
        h = [mn for t, mn in PH[pid] if t < ts - 3600][-10:]
        if not h or np.mean(h) < 10: continue
        w = np.mean(h) / 40 * (1.0 if k + 1 <= 3 else (.5 if k + 1 <= 10 else 0.0))
        if w <= 0: continue
        pr = profile(NAME[pid], int(sea[1:])); NOPROF[pr is None] += 1
        res.append(dict(w=w, **(pr or dict(onO=0.0, onD=0.0, usg=None))))
    return res
# ---- Ευρωλιγκα 2021-25 με live μοντελο & αγορα συνολων ----
rows = []
for pos, d_ in REC[23].items():
    sea = D.season.values[pos]
    if sea not in SE: continue
    hc, ac = D.home.values[pos], D.away.values[pos]; t = pd.Timestamp(D.t.values[pos]); key = (sea, hc, ac, t.strftime('%Y-%m-%d %H:%M'))
    if key not in NP or NP[key].get('t_new') is None or NP[key].get('h_new') is None: continue
    ts = t.timestamp(); ah, aa = absents(sea, hc, ts), absents(sea, ac, ts)
    if ah is None or aa is None: continue
    hd = REC[21].get(pos)
    rows.append(dict(y=sea, hs=float(D.hs.values[pos]), as_=float(D.as_.values[pos]), T=float(NP[key]['t_new']), M=float(NP[key]['h_new']),
                     ah=ah, aa=aa, op=d_['open'], cl=d_[0], hop=hd['open'] if hd else None, hcl=hd[0] if hd else None))
P(f'Ευρωλιγκα 2021-25: ματς {len(rows)} · απουσιες με περσινο on/off προφιλ {NOPROF[False]} / χωρις {NOPROF[True]} ({NOPROF[False] / max(1, sum(NOPROF.values())):.0%} καλυψη)')
allp = [p for r in rows for p in r['ah'] + r['aa'] if p['usg'] is not None]
SD = {f: np.std([p[f] for p in allp]) for f in ('onO', 'onD')}
P(f'on/off (μετα το μαζεμα) τυπ. αποκλιση: επιθεση {SD["onO"]:.2f} · αμυνα {SD["onD"]:.2f} ποντοι/100 κατοχες')
zf = lambda p, f: p[f] / SD[f]                    # μεσος = 0 (χωρις προφιλ = 0)
NAMES = ['δικα λεπτα', 'λεπτα αντιπ.', 'δικα×onO', 'αντιπ.×onD']
def tfeat(own, opp): return np.array([sum(p['w'] for p in own), sum(p['w'] for p in opp), sum(p['w'] * zf(p, 'onO') for p in own), sum(p['w'] * zf(p, 'onD') for p in opp)])
XH = np.array([tfeat(r['ah'], r['aa']) for r in rows]); XA = np.array([tfeat(r['aa'], r['ah']) for r in rows])
YH = np.array([r['hs'] - (r['T'] + r['M']) / 2 for r in rows]); YA = np.array([r['as_'] - (r['T'] - r['M']) / 2 for r in rows]); YT = YH + YA
ys = np.array([r['y'] for r in rows]); ALL = np.ones(len(rows), bool)
VAR = {'W1 μονο λεπτα': [0, 1], 'W2 λεπτα + on/off': [0, 1, 2, 3], 'W4 μονο on/off': [2, 3]}
def fit(cols, tr):
    X = np.r_[XH[tr][:, cols], XA[tr][:, cols]]; y = np.r_[YH[tr], YA[tr]]
    return np.linalg.solve(X.T @ X + 1.0 * np.eye(len(cols)), X.T @ y)
def rmse(v, m): return float(np.sqrt(np.mean(v[m] ** 2)))
P(''); P('################ ΣΥΝΟΛΑ ################')
P('## ΣΥΝΤΕΛΕΣΤΕΣ (ποντοι ομαδας ανα 40′ απουσιας· z = ανα 1 τυπ. αποκλιση on/off)')
HELD, OKS = {}, {}
for nm, cols in VAR.items():
    b = fit(cols, ALL); per = {s: fit(cols, ys == s) for s in SE}; P(f'  {nm}:'); same_ok = True
    for j, c in enumerate(cols):
        same = sum(1 for s in SE if np.sign(per[s][j]) == np.sign(b[j]))
        if c >= 2 and same < 4: same_ok = False
        P(f'     {NAMES[c]:14s} {b[j]:+.2f} · ανα σεζον ' + ' '.join(f'{s[-2:]}:{per[s][j]:+.2f}' for s in SE) + f' (ιδιο προσημο {same}/5)')
    h = np.zeros(len(rows))
    for Yr in SE:
        bb = fit(cols, ys != Yr); m = ys == Yr; h[m] = XH[m][:, cols] @ bb + XA[m][:, cols] @ bb
    HELD[nm] = h; OKS[nm] = same_ok
def tp(t, T_):
    if abs(T_ - round(T_)) < 1e-9: po = 1 - Phi((T_ + .5 - t) / 16.7); pu = Phi((T_ - .5 - t) / 16.7); return po, 1 - po - pu, pu
    po = 1 - Phi((T_ - t) / 16.7); return po, 0.0, 1 - po
def tpicks(adj):
    U = collections.defaultdict(list); mv = []
    for r, a in zip(rows, adj):
        o = r['op']; T_, oo, ou = o[2], o[3], o[4]; po, pp, pu = tp(r['T'] + a, T_); eo, eu = po * oo + pp - 1, pu * ou + pp - 1
        sd, e, od = (1, eo, oo) if eo >= eu else (-1, eu, ou)
        if e < .08: continue
        x = (r['hs'] + r['as_'] - T_) * sd; U[r['y']].append((od - 1) if x > 0 else (0 if x == 0 else -1)); mv.append((r['cl'][1] - o[1]) * sd)
    u = [x for v in U.values() for x in v]
    return sum(u), f"{len(u):4d} picks · {sum(u):+6.1f}μ · ROI {np.mean(u)*100:+5.1f}% (θετ {sum(1 for s in SE if U[s] and np.mean(U[s]) > 0)}/5) · " + ' '.join(f"{s[-2:]}:{sum(U[s]):+.1f}" for s in SE) + f" · CLV {np.mean(mv):+.2f}"
u0, s0 = tpicks(np.zeros(len(rows)))
P(''); P(f'## LOSO RMSE συνολου (χωρις {rmse(YT, ALL):.3f}) & PICKS συνολων ≥8% ανοιγμα')
P(f'  χωρις διορθωση          ' + s0)
TOT_OK = {}
for nm in VAR:
    h = HELD[nm]; d0 = [rmse(YT - h, ys == s) - rmse(YT, ys == s) for s in SE]; u, s_ = tpicks(h)
    TOT_OK[nm] = sum(x < 0 for x in d0) >= 4 and OKS[nm] and u >= u0
    P(f'  {nm:22s} RMSE {rmse(YT - h, ALL):.3f} · ' + ' '.join(f'{x:+.3f}' for x in d0) + f' → {sum(x < 0 for x in d0)}/5')
    P(f'  {"":22s} {s_}' + ('   <- περνα στην EL (εκκρεμει EuroCup)' if TOT_OK[nm] and nm != 'W1 μονο λεπτα' else ''))
# ---- ΧΑΝΤΙΚΑΠ ----
P(''); P('################ ΧΑΝΤΙΚΑΠ ################')
YM = YH - YA
xl = np.array([sum(p['w'] for p in r['aa']) - sum(p['w'] for p in r['ah']) for r in rows]); live = 0.922 * xl
xn = np.array([sum(p['w'] * (zf(p, 'onO') - zf(p, 'onD')) for p in r['aa']) - sum(p['w'] * (zf(p, 'onO') - zf(p, 'onD')) for p in r['ah']) for r in rows]) / math.sqrt(2)
R0 = YM - live
cfit = lambda m: float((xn[m] @ R0[m]) / (xn[m] @ xn[m] + 1.0))
per = {s: cfit(ys == s) for s in SE}; call = cfit(ALL)
hh = np.zeros(len(rows))
for Yr in SE: hh[ys == Yr] = cfit(ys != Yr) * xn[ys == Yr]
d = [rmse(R0 - hh, ys == s) - rmse(R0, ys == s) for s in SE]
P(f'  c (επιπλεον ποντοι ανα 40′ απουσιας ανα 1 τυπ. αποκλιση on/off net) {call:+.2f} · ανα σεζον ' + ' '.join(f'{s[-2:]}:{v:+.2f}' for s, v in per.items())
  + f' (ιδιο προσημο {sum(1 for v in per.values() if np.sign(v) == np.sign(call))}/5)')
P(f'  RMSE διαφορας: χωρις {rmse(YM, ALL):.3f} · LIVE {rmse(R0, ALL):.3f} · LIVE+on/off {rmse(R0 - hh, ALL):.3f} · vs LIVE ' + ' '.join(f'{x:+.3f}' for x in d) + f' → {sum(x < 0 for x in d)}/5')
def hpicks(adj):
    U = collections.defaultdict(list)
    for r, a in zip(rows, adj):
        if not r['hop']: continue
        L, o1, o2 = r['hop'][2:]; m = r['M'] + a
        if abs(L - round(L)) < 1e-9: pw = Phi((m + L - .5) / 11.5); pl = Phi((-m - L - .5) / 11.5)
        else: pw = Phi((m + L) / 11.5); pl = 1 - pw
        pp = 1 - pw - pl; e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1; sd, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
        if e >= .08: x = (r['hs'] - r['as_'] + L) * sd; U[r['y']].append((od - 1) if x > 0 else (0 if x == 0 else -1))
    u = [x for v in U.values() for x in v]
    return sum(u), f"{len(u):4d} picks · {sum(u):+6.1f}μ · ROI {np.mean(u)*100:+5.1f}% (θετ {sum(1 for s in SE if U[s] and np.mean(U[s]) > 0)}/5) · " + ' '.join(f"{s[-2:]}:{sum(U[s]):+.1f}" for s in SE)
P('  picks ≥8% χωρις      ' + hpicks(np.zeros(len(rows)))[1])
ul, sl = hpicks(live); P('  picks ≥8% LIVE       ' + sl)
un, sn = hpicks(live + hh); P('  picks ≥8% LIVE+on/off ' + sn)
HC_OK = sum(x < 0 for x in d) >= 4 and sum(1 for v in per.values() if np.sign(v) == np.sign(call)) >= 4 and un >= ul
# ---- ΕΠΙΒΕΒΑΙΩΣΗ EuroCup U2020-25 (απλη βαση) ----
P(''); P('################ ΕΠΙΒΕΒΑΙΩΣΗ EuroCup 2021-25 (απλη βαση: επιθεση ομαδας + αμυνα αντιπαλου − μεσος, μαζεμα 5, + εδρα) ################')
GM.sort(key=lambda x: x[1]); er = []
for sea in EC:
    G = [g for g in GM if g[0] == sea]; sc = collections.defaultdict(list); al = collections.defaultdict(list); allpts = []
    for s_, ts, h, a, hs, as_ in G:
        if len(sc[h]) >= 3 and len(sc[a]) >= 3:
            lg = np.mean(allpts); sh = lambda L: (sum(L) + 5 * lg) / (len(L) + 5)
            ah, aa = absents(sea, h, ts), absents(sea, a, ts)
            if ah is not None and aa is not None:
                er.append((sea, hs - (sh(sc[h]) + sh(al[a]) - lg), 1, ah, aa)); er.append((sea, as_ - (sh(sc[a]) + sh(al[h]) - lg), 0, aa, ah))
        sc[h].append(hs); al[h].append(as_); sc[a].append(as_); al[a].append(hs); allpts += [hs, as_]
EY = np.array([e[1] for e in er]); Ey = np.array([e[0] for e in er])
EX = np.array([[1, e[2]] + list(tfeat(e[3], e[4])) + [sum(p['w'] * (zf(p, 'onO') - zf(p, 'onD')) for p in e[3]) / math.sqrt(2)] for e in er])
def ols(m, cols):
    Xm, Ym = EX[m][:, cols], EY[m]; b = np.linalg.lstsq(Xm, Ym, rcond=None)[0]; r_ = Ym - Xm @ b
    se = np.sqrt(np.diag(np.sum(r_ ** 2) / (len(Ym) - len(cols)) * np.linalg.inv(Xm.T @ Xm))); return b, se
cols = [0, 1, 2, 3, 4, 5]; b, se = ols(np.ones(len(EY), bool), cols)
P(f'  ομαδα-ματς {len(er)} · δικα×onO {b[4]:+.2f} (t {b[4]/se[4]:+.1f}) · αντιπ.×onD {b[5]:+.2f} (t {b[5]/se[5]:+.1f}) · δικα λεπτα {b[2]:+.2f} · λεπτα αντιπ. {b[3]:+.2f}')
okO = okD = 0
for s in EC:
    bb, _ = ols(Ey == s, cols); okO += bb[4] < 0; okD += bb[5] < 0
    P(f'    {s}: δικα×onO {bb[4]:+.2f} · αντιπ.×onD {bb[5]:+.2f}')
EC_TOT = okO >= 4 and okD >= 4 and b[4] / se[4] <= -2 and b[5] / se[5] <= -2
P(f'  σωστο προσημο: δικα×onO (<0) {okO}/5 · αντιπ.×onD (<0) {okD}/5 → ' + ('ΕΠΙΒΕΒΑΙΩΝΕΤΑΙ' if EC_TOT else 'ΔΕΝ επιβεβαιωνεται'))
# χαντικαπ στο EuroCup: ποντοι ομαδας ~ ... + δικα×onNet (αναμενομενο > 0: λειπει θετικος παικτης → η ομαδα χανει) — στη διαφορα
cols2 = [0, 1, 2, 3, 6]; b2, se2 = ols(np.ones(len(EY), bool), cols2); okN = sum(ols(Ey == s, cols2)[0][4] < 0 for s in EC)
EC_HC = okN >= 4 and b2[4] / se2[4] <= -2
P(f'  χαντικαπ: δικα×onNet {b2[4]:+.2f} (t {b2[4]/se2[4]:+.1f}, σωστο προσημο <0 σε {okN}/5) → ' + ('ΕΠΙΒΕΒΑΙΩΝΕΤΑΙ' if EC_HC else 'ΔΕΝ επιβεβαιωνεται'))
P(''); P('################ ΑΠΟΦΑΣΗ (προ-δηλωμενα κριτηρια) ################')
for nm in ('W2 λεπτα + on/off', 'W4 μονο on/off'): P(f'  ΣΥΝΟΛΑ {nm}: EL {"✓" if TOT_OK[nm] else "✗"} · EuroCup {"✓" if EC_TOT else "✗"} → ' + ('ΠΕΡΝΑ' if TOT_OK[nm] and EC_TOT else 'ΔΕΝ ΠΕΡΝΑ'))
P(f'  ΧΑΝΤΙΚΑΠ LIVE+on/off: EL {"✓" if HC_OK else "✗"} · EuroCup {"✓" if EC_HC else "✗"} → ' + ('ΠΕΡΝΑ' if HC_OK and EC_HC else 'ΔΕΝ ΠΕΡΝΑ'))
open('el_absence_onoff_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
