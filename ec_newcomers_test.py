# -*- coding: utf-8 -*-
"""ec_newcomers_test.py — EuroCup: ΝΕΟΦΕΡΜΕΝΕΣ ομαδες (δεν επαιξαν EuroCup περσι → το μοντελο τις ξεκινα απο τον μεσο ορο) (1/10/2026, Στελιος «ξεκινα με το 1»).
Φετος 15/32 νεες. ΠΗΓΗ: περσινη ΚΟΙΝΗ ΚΛΙΜΑΚΑ (ridge διαφορας ±20, ολα τα ματς: EL/EC/BCL/FIBA Europe Cup + 16 εγχωρια: fs_bk_games + fs_bk_extra,
  ιδιος κωδικος Flashscore σε ολες τις διοργανωσεις) μειον μεσο των ομαδων EuroCup της σεζον → CS (ποντοι/ματς).
ΜΕΤΑΤΡΟΠΗ: αφετηρια νεοφερμενης += κ_n·CS + δ (ΜΟΝΟ νεοφερμενες· οι παλιες κρατανε το carry .7 του περσινου EuroCup).
ΠΛΕΓΜΑ: κ_n {0, .35, .5, .7, 1} × δ {-3..+1} × βαση {χωρις ειδικους, με καταταξεις κ_x 3} · εγχωρια κ1 απο 1ο + προετοιμασια κ.5 σταθερα.
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση): LOSO U2021-U2025 (κοινη κλιμακα υπαρχει απο 2020) με RMSE ΠΡΩΤΩΝ 6 (ολα τα ματς) →
  ΠΕΡΝΑ αν καλυτερο απο κ_n=0,δ=0 σε ≥4/5 σεζον, ΧΩΡΙΣΤΑ για καθε βαση. Αναφορα: ματς με νεοφερμενη, 7+, ολα, αγορα, Κ2, ROI.
Εξοδος: ec_newcomers_test_out.txt"""
import sys, json, math, re, unicodedata, datetime as dt, itertools
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
# ---- βαση EuroCup (D, μηχανη) ----
src = open('el_model_test.py', encoding='utf-8').read().split('# ---------------- ρυθμιση (χωρις αποδοσεις) ----------------')[0]
src = src.replace("B = json.load(open('el_box.json', encoding='utf-8'))",
                  "B = {k: v for k, v in json.load(open('el_players.json', encoding='utf-8')).items() if v.get('comp') == 'U'}")
NS = {}; exec(src, NS)
D, fit_eff, fit_pace, points, P, out = NS['D'], NS['fit_eff'], NS['fit_pace'], NS['points'], NS['P'], NS['out']
out.clear()
HL, LAM, CARRY, H, VAR = 9999, 4, 0.7, 5, 'L'
SEAS = sorted(D.season.unique())
ph_, pa_ = points(D, VAR); EH, EA = 100 * ph_ / D.poss.values, 100 * pa_ / D.poss.values
# ---- εγχωρια Δ (απο el_domestic_rating_test) ----
DOMNS = {}
exec(open('el_domestic_rating_test.py', encoding='utf-8').read().split('# ---- 2. αντιστοιχιση')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
     .replace("open('el_domestic_rating_test_out.txt', 'w'", "open('_unused_ec4.txt', 'w'"), DOMNS)
tok = DOMNS['tok']; D0 = DOMNS['D0']
# ---- (α) επιπλεον πρωταθληματα απο Flashscore, σε μορφη bk_domestic ----
XT = json.load(open('fs_bk_extra.json', encoding='utf-8')); XID = {}
for key, L in XT.items():
    lg, y = key.split('_'); y = int(y); kk = f'{lg}_{y % 100:02d}-{(y + 1) % 100:02d}'
    teams, games = {}, []
    for e in L:
        try: hs, as_ = int(e['hs']), int(e['as_'])
        except Exception: continue
        if not e.get('hid') or not e.get('aid') or not e.get('ts'): continue
        ih = XID.setdefault((lg, e['hid']), 900000 + len(XID)); ia = XID.setdefault((lg, e['aid']), 900000 + len(XID))
        teams[str(ih)] = e['home']; teams[str(ia)] = e['away']
        games.append([e['id'], dt.datetime.fromtimestamp(e['ts'], dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S'), ih, ia, str(hs), str(as_), 1])
    if games: DOMNS['DOM'][kk] = dict(teams=teams, games=games)
DOMNS['LEAGUES'][:] = sorted({k.split('_')[0] for k in DOMNS['DOM']})
S20, NAMES = DOMNS['dom_series'](20)
# ---- (β) σταθερη αντιστοιχιση (Nowgoal με παλια ονοματα χορηγων) ----
MANUAL = {'TOR': ('LBA', 4730), 'BRE': ('LBA', 3936), 'UNK': ('VTB', 942), 'DAR': ('TBL', 1098), 'GAL': ('TBL', 1010),
          'BES': ('TBL', 1127), 'PAI': ('LNB', 915), 'MAN': ('ACB', 1815), 'PAT': ('GBL', 5413)}
S0keys = list(S20.keys())
MAPD = {}
for Y in SEAS:
    es = 'E' + Y[1:]
    sub = D[D.season == Y]; tn = {}
    for r in sub.itertuples(): tn.setdefault(r.home, r.hname); tn.setdefault(r.away, r.aname)
    cands = [k for k in S0keys if k[0] == es]
    for code, nm in tn.items():
        if code in MANUAL and (es, MANUAL[code][1], MANUAL[code][0]) in S20:
            MAPD[(Y, code)] = (es, MANUAL[code][1], MANUAL[code][0]); continue
        te = tok(nm)
        sc = sorted([(len(te & tok(NAMES.get((L, t), ''))) / max(1, len(tok(NAMES.get((L, t), '')))), (es_, t, L)) for (es_, t, L) in cands], reverse=True)
        if sc and sc[0][0] >= 0.5: MAPD[(Y, code)] = sc[0][1]
def dshift(Y, code, dday):
    k = MAPD.get((Y, code))
    if not k or k not in S20: return 0.0
    v = 0.0
    for dd, x in S20[k]:
        if dd <= dday - 1: v = x
        else: break
    return v
P(f'EuroCup ματς {len(D)} · αντιστοιχιση με εγχωριο: ' + ' '.join(f'{Y[-2:]}:{sum(1 for k in MAPD if k[0] == Y)}/{len(set(D[D.season == Y].home))}' for Y in SEAS))
# ---- προετοιμασια ----
FG = json.load(open('fs_bk_games.json', encoding='utf-8')); PS = json.load(open('fs_bk_preseason.json', encoding='utf-8'))
def common(y):
    rows = []
    for key, L in FG.items():
        c, yy = key.split('_')
        if int(yy) != y: continue
        for e in L:
            try: m = float(np.clip(int(e['hs']) - int(e['as_']), -20, 20))
            except Exception: continue
            if e.get('hid') and e.get('aid'): rows.append((e['hid'], e['aid'], m))
    if not rows: return {}
    teams = sorted({r[0] for r in rows} | {r[1] for r in rows}); ix = {t: i for i, t in enumerate(teams)}; n = len(teams); k = len(rows)
    A = np.zeros((k + n, n + 1)); b = np.zeros(k + n); r_ = np.arange(k)
    A[r_, [ix[r[0]] for r in rows]] = 1; A[r_, [ix[r[1]] for r in rows]] = -1; A[r_, n] = 1; b[:k] = [r[2] for r in rows]
    A[k + np.arange(n), np.arange(n)] = math.sqrt(2)
    x = np.linalg.lstsq(A, b, rcond=None)[0]
    return {t: float(x[ix[t]]) for t in teams}
PRE = {}
for Y in SEAS:
    y = int(Y[1:])
    if f'EC_{y}' not in FG: continue
    C = common(y - 1); sub = D[D.season == Y]
    start = min(pd.Timestamp(t).date() for t in sub.t)
    FS2 = {}
    idx = {}
    for r in sub.itertuples(): idx.setdefault((int(r.hs), int(r.as_)), []).append(r)
    for e in FG.get(f'EC_{y}', []):
        try: hs, as_ = int(e['hs']), int(e['as_'])
        except Exception: continue
        d = dt.datetime.fromtimestamp(e['ts'], dt.timezone.utc).date()
        for r in idx.get((hs, as_), []):
            if abs((pd.Timestamp(r.t).date() - d).days) <= 1: FS2[e['hid']] = r.home; FS2[e['aid']] = r.away; break
    acc = {}
    for key, L in PS.items():
        for e in L:
            if not e.get('ts'): continue
            d = dt.datetime.fromtimestamp(e['ts'], dt.timezone.utc).date()
            if not (dt.date(y, 8, 1) <= d < start): continue
            try: m = float(np.clip(int(e['hs']) - int(e['as_']), -20, 20))
            except Exception: continue
            for me, op, sg in ((e.get('hid'), e.get('aid'), 1), (e.get('aid'), e.get('hid'), -1)):
                code = FS2.get(me)
                if code and me in C and op in C: acc.setdefault(code, []).append(sg * m - (C[me] - C[op]))
    for code, L in acc.items(): PRE[(Y, code)] = sum(L) / (len(L) + 4.0)
P('προετοιμασια (ομαδες με r): ' + ' '.join(f'{Y[-2:]}:{sum(1 for k in PRE if k[0] == Y)}' for Y in SEAS))
# ---- μηχανη με μετατοπισεις ----
dnum = np.array([(pd.Timestamp(t).tz_localize(None) - pd.Timestamp(D0)).days if pd.Timestamp(t).tzinfo else (pd.Timestamp(t) - pd.Timestamp(D0)).days for t in D.t])
GN = np.zeros(len(D), int)
for Y in SEAS:
    cnt = {}
    for i in np.where(D.season.values == Y)[0]:
        h_, a_ = D.home.values[i], D.away.values[i]
        GN[i] = max(cnt.get(h_, 0), cnt.get(a_, 0)); cnt[h_] = cnt.get(h_, 0) + 1; cnt[a_] = cnt.get(a_, 0) + 1
def run(kp, kd, F, kx=0.0, XS=None):
    preds = np.full(len(D), np.nan); prior = {}
    mu0 = float((EH.mean() + EA.mean()) / 2); pm0 = float(D.pace.mean())
    for s in SEAS:
        sidx = np.where(D.season.values == s)[0]
        teams = sorted(set(D.home.values[sidx]) | set(D.away.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        hi = np.array([ix[t] for t in D.home.values[sidx]]); ai = np.array([ix[t] for t in D.away.values[sidx]])
        hb = np.where(D.neutral.values[sidx] == 1, 0.0, H / 2)
        pre = np.array([(kp * PRE.get((s, t), 0.0) + kx * (XS or {}).get((s, t), 0.0)) * 100 / 72 for t in teams])
        o0b = np.array([CARRY * prior.get(t, (0, 0, 0))[0] for t in teams]) + pre / 2
        d0b = np.array([CARRY * prior.get(t, (0, 0, 0))[1] for t in teams]) - pre / 2
        p0 = np.array([CARRY * prior.get(t, (0, 0, 0))[2] for t in teams])
        dn = dnum[sidx]; eh = EH[sidx]; ea = EA[sidx]; pc = D.pace.values[sidx]; gn = GN[sidx]
        for d in np.unique(dn):
            past = dn < d; cur = np.where(dn == d)[0]
            use_dom = kd > 0 and (gn[cur] >= F - 1).any()
            if use_dom:
                sh = np.array([kd * dshift(s, t, d) * 100 / 72 for t in teams]); o0 = o0b + sh / 2; d0 = d0b - sh / 2
            else:
                o0, d0 = o0b, d0b
            if past.any():
                w = 0.5 ** ((d - dn[past]) / HL)
                mu, O, Dd = fit_eff(hi[past], ai[past], eh[past], ea[past], hb[past], w, n, o0, d0, LAM, mu0)
                pm, Pc = fit_pace(hi[past], ai[past], pc[past], w, n, p0, LAM, pm0)
            else:
                mu, O, Dd, pm, Pc = mu0, o0, d0, pm0, p0
            if use_dom and not (gn[cur] >= F - 1).all():          # μικτη μερα: ματς κατω απο F → χωρις εγχωρια
                if past.any():
                    mu_b, O_b, D_b = fit_eff(hi[past], ai[past], eh[past], ea[past], hb[past], w, n, o0b, d0b, LAM, mu0)
                else:
                    mu_b, O_b, D_b = mu0, o0b, d0b
            for j in cur:
                if use_dom and gn[j] < F - 1:
                    m_, O_, D_ = mu_b, O_b, D_b
                else:
                    m_, O_, D_ = mu, O, Dd
                e_h = m_ + O_[hi[j]] + D_[ai[j]] + hb[j]; e_a = m_ + O_[ai[j]] + D_[hi[j]] - hb[j]
                preds[sidx[j]] = (pm + Pc[hi[j]] + Pc[ai[j]]) * (e_h - e_a) / 100
        w = 0.5 ** ((dn.max() - dn) / HL)
        mu, O, Dd = fit_eff(hi, ai, eh, ea, hb, w, n, o0b, d0b, LAM, mu0)
        pm, Pc = fit_pace(hi, ai, pc, w, n, p0, LAM, pm0)
        prior = {t: (O[i], Dd[i], Pc[i]) for t, i in ix.items()}; mu0 = mu; pm0 = pm
    return preds
act = (D.hs - D.as_).values.astype(float)
EVS = ['U2021', 'U2022', 'U2023', 'U2024', 'U2025']
def rm(v, ss): m = np.isin(D.season.values, ss) & np.isfinite(v); return float(np.sqrt(np.mean((act - v)[m] ** 2)))

EV = ['U2021', 'U2022', 'U2023', 'U2024', 'U2025']
seasn = D.season.values
# ---- ειδικοι (καταταξεις) ----
EX = json.load(open('ec_expert.json', encoding='utf-8')); _nd = NormalDist(); ZR = {}
for S, tm in EX.items():
    for c, d in tm.items():
        zr = [_nd.inv_cdf(1 - (d[k] - .5) / d[k + '_n']) for k in ('EH', 'TTC') if k in d]
        if zr: ZR[(S, c)] = float(np.mean(zr))
# ---- κοινη κλιμακα ΠΕΡΣΙΝΗΣ σεζον: fs_bk_games (EL/EC/BCL/FEC/10 εγχωρια) + fs_bk_extra (6 εγχωρια) ----
def common2(y):
    rows = []
    for key, L in list(FG.items()) + list(XT.items()):
        c, yy = key.split('_')
        if int(yy) != y: continue
        for e in L:
            try: m = float(np.clip(int(e['hs']) - int(e['as_']), -20, 20))
            except Exception: continue
            if e.get('hid') and e.get('aid'): rows.append((e['hid'], e['aid'], m))
    teams = sorted({r[0] for r in rows} | {r[1] for r in rows}); ix = {t: i for i, t in enumerate(teams)}; n = len(teams); k = len(rows)
    A = np.zeros((k + n, n + 1)); b = np.zeros(k + n); r_ = np.arange(k)
    A[r_, [ix[r[0]] for r in rows]] = 1; A[r_, [ix[r[1]] for r in rows]] = -1; A[r_, n] = 1; b[:k] = [r[2] for r in rows]
    A[k + np.arange(n), np.arange(n)] = math.sqrt(2)
    x = np.linalg.lstsq(A, b, rcond=None)[0]
    return {t: float(x[ix[t]]) for t in teams}
CS = {}      # (Y, code) -> περσινη κοινη δυναμη (ποντοι/ματς) μειον μεσο ομαδων EuroCup της σεζον
NEW = {}     # (Y, code) -> True αν ΔΕΝ επαιξε EuroCup περσι
cover = []
for Y in EV:
    y = int(Y[1:]); C = common2(y - 1); sub = D[D.season == Y]
    prev = set(D.home.values[seasn == f'U{y - 1}']) | set(D.away.values[seasn == f'U{y - 1}'])
    teams = sorted(set(sub.home) | set(sub.away))
    FS2 = {}; idx = {}
    for r in sub.itertuples(): idx.setdefault((int(r.hs), int(r.as_)), []).append(r)
    for e in FG.get(f'EC_{y}', []):
        try: hs, as_ = int(e['hs']), int(e['as_'])
        except Exception: continue
        d = dt.datetime.fromtimestamp(e['ts'], dt.timezone.utc).date()
        for r in idx.get((hs, as_), []):
            if abs((pd.Timestamp(r.t).date() - d).days) <= 1: FS2[r.home] = e['hid']; FS2[r.away] = e['aid']; break
    raw = {t: C[FS2[t]] for t in teams if t in FS2 and FS2[t] in C}
    mu = float(np.mean(list(raw.values())))
    for t in teams:
        NEW[(Y, t)] = t not in prev
        if t in raw: CS[(Y, t)] = raw[t] - mu
    nn = [t for t in teams if t not in prev]
    cover.append(f'{Y[-2:]}: νεες {len(nn)}/{len(teams)} (με περσινη δυναμη {sum(1 for t in nn if t in raw)})')
P(''); P('ΝΕΟΦΕΡΜΕΝΕΣ & ΚΟΙΝΗ ΚΛΙΜΑΚΑ: ' + ' · '.join(cover))
nv = [CS[k] for k in CS if NEW[k]]; ov = [CS[k] for k in CS if not NEW[k]]
P(f'  περσινη κοινη δυναμη (vs μεσο EuroCup): νεοφερμενες {np.mean(nv):+.2f} (n {len(nv)}) · παλιες {np.mean(ov):+.2f} (n {len(ov)})')
# ---- ποσο «ειναι» οι νεοφερμενες στην πραγματικοτητα: τελικη δυναμη σεζον ----
def ls_rating(ii, y):
    teams = sorted(set(D.home.values[ii]) | set(D.away.values[ii])); ix = {t: k for k, t in enumerate(teams)}; n = len(teams)
    X = np.zeros((len(ii), n + 1))
    for r, i in enumerate(ii):
        X[r, ix[D.home.values[i]]] = 1; X[r, ix[D.away.values[i]]] = -1; X[r, n] = 0 if D.neutral.values[i] == 1 else 1
    A = X.T @ X + np.diag([0.5] * n + [0.0]); b = np.linalg.solve(A, X.T @ y)
    return {t: b[k] for t, k in ix.items()}
fin = {}
for Y in EV:
    si = np.where(seasn == Y)[0]; f = ls_rating(si, act[si])
    for t, v in f.items(): fin[(Y, t)] = v
kk = [k for k in CS if NEW[k]]
x = np.array([CS[k] for k in kk]); yv = np.array([fin[k] for k in kk])
b_ = np.polyfit(x, yv, 1)
P(f'  νεοφερμενες: τελικη δυναμη μεσος {yv.mean():+.2f} · κλιση τελικης πανω στην περσινη κοινη {b_[0]:+.2f} (r {np.corrcoef(x, yv)[0, 1]:.2f}) · σταθερα {b_[1]:+.2f}')
kk = [k for k in CS if not NEW[k]]
x = np.array([CS[k] for k in kk]); yv = np.array([fin[k] for k in kk])
P(f'  παλιες:       τελικη δυναμη μεσος {yv.mean():+.2f} · κλιση {np.polyfit(x, yv, 1)[0]:+.2f} (r {np.corrcoef(x, yv)[0, 1]:.2f})')
# ---- μηχανη: μετατοπιση ΜΟΝΟ στις νεοφερμενες = κ_n·CS + δ ----
def shifts(kn, dl):
    return {k: kn * CS.get(k, 0.0) + dl for k in NEW if NEW[k]}
GR = []
for kx in (0, 3):
    for kn in (0, .35, .5, .7, 1):
        for dl in (-3, -2, -1, 0, 1):
            GR.append((kx, kn, dl))
PRED = {}
for i, (kx, kn, dl) in enumerate(GR):
    XS = dict(shifts(kn, dl))
    for k, z in ZR.items():
        if kx: XS[k] = XS.get(k, 0.0) + kx * z
    PRED[(kx, kn, dl)] = run(.5, 1, 1, 1.0, XS)
    if i % 10 == 0: print(f'  {i + 1}/{len(GR)} …', flush=True)
def rmm(v, ss, msk): m = np.isin(seasn, ss) & np.isfinite(v) & msk; return float(np.sqrt(np.mean((act - v)[m] ** 2)))
N = NormalDist(); Phi = N.cdf
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
MK = {}
for ng, g in SCH.items():
    tip = pd.Timestamp(g['bj']) - pd.Timedelta(hours=8); hit, sw = None, False
    for (a_, b_), swp in (((g['hs'], g['as_']), False), ((g['as_'], g['hs']), True)):
        for i in ix2.get((a_, b_), []):
            if abs(pd.Timestamp(D.t.values[i]).tz_localize(None) - tip) <= pd.Timedelta(hours=26): hit, sw = i, swp; break
        if hit is not None: break
    if hit is None: continue
    rows = sorted([x for x in ROWS.get(ng, []) if x[4] == 2 and x[1] is not None and x[2] and x[3] and x[0] + 8 * 3600 <= tip.timestamp() + 600], key=lambda x: x[0])
    if not rows: continue
    def conv(x):
        o1, o2 = 1 + x[2], 1 + x[3]; L = -x[1]; ph = (1 / o1) / (1 / o1 + 1 / o2); mu = -L + 11.5 * N.inv_cdf(min(max(ph, 1e-4), 1 - 1e-4))
        return (-L, -mu, o2, o1) if sw else (L, mu, o1, o2)
    MK[hit] = dict(o=conv(rows[0]), c=conv(rows[-1]))
MO = np.full(len(D), np.nan); MC = np.full(len(D), np.nan)
for i in MK: MO[i] = MK[i]['o'][1]; MC[i] = MK[i]['c'][1]
INV = np.array([NEW.get((seasn[i], D.home.values[i]), False) or NEW.get((seasn[i], D.away.values[i]), False) for i in range(len(D))])
MASKS = (('ΠΡΩΤΑ 6 (ολα)', GN <= 5), ('ΠΡΩΤΑ 6 με νεοφερμενη', (GN <= 5) & INV), ('7+ με νεοφερμενη', (GN >= 6) & INV), ('ΟΛΑ', GN >= 0))
for kx, lab_x in ((0, 'ΧΩΡΙΣ ειδικους'), (3, 'ΜΕ ειδικους (κ_x 3)')):
    P(''); P(f'######## ΒΑΣΗ: εγχωρια κ1 + προετοιμασια κ.5 + {lab_x} ########')
    for lab, msk in MASKS:
        base = PRED[(kx, 0, 0)]
        held = np.full(len(D), np.nan); ch = []
        for Y in EV:
            tr = [x for x in EV if x != Y]
            g = min([g for g in PRED if g[0] == kx], key=lambda g: rmm(PRED[g], tr, (GN <= 5)))    # επιλογη ΠΑΝΤΑ με πρωτα 6 (ολα)
            ch.append(g[1:]); held[seasn == Y] = PRED[g][seasn == Y]
        d = [rmm(held, [Y], msk) - rmm(base, [Y], msk) for Y in EV]
        mm = msk & np.isfinite(MO)
        crit = ('  <- ΠΕΡΝΑ' if sum(x < 0 for x in d) >= 4 else '  <- ✗') if lab == 'ΠΡΩΤΑ 6 (ολα)' else ''
        P(f'  {lab:22s} n {int((np.isin(seasn, EV) & msk).sum())} · RMSE {rmm(base, EV, msk):.3f} -> {rmm(held, EV, msk):.3f} · ' + ' '.join(f'{Y[-2:]}:{x:+.3f}' for Y, x in zip(EV, d))
          + f' -> {sum(x < 0 for x in d)}/5{crit} · αγορα ανοιγμα {rmm(MO, EV, mm):.3f} κλεισ. {rmm(MC, EV, mm):.3f} (μοντ. στα ιδια {rmm(base, EV, mm):.3f}->{rmm(held, EV, mm):.3f})')
        if lab == 'ΠΡΩΤΑ 6 (ολα)': P(f'     επιλογες (κ_n, δ): {ch}')
        for fam, v in (('πριν', base), ('μετα', held)):
            ii = [i for i in MK if seasn[i] in EV and msk[i] and np.isfinite(v[i])]
            x = np.array([v[i] - MK[i]['c'][1] for i in ii]); z = np.array([act[i] - MK[i]['c'][1] for i in ii])
            bb = np.polyfit(x, z, 1)[0]; r_ = z - np.polyval(np.polyfit(x, z, 1), x); se = math.sqrt(np.sum(r_ ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2))
            cells = []
            for when in ('o', 'c'):
                R = []
                for i in ii:
                    L_, _, o1, o2 = MK[i][when]; m = v[i]
                    if abs(L_ - round(L_)) < 1e-9: pw = Phi((m + L_ - .5) / 11.5); pl = Phi((-m - L_ - .5) / 11.5)
                    else: pw = Phi((m + L_) / 11.5); pl = 1 - pw
                    pp = 1 - pw - pl; e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
                    side, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
                    if e >= .08:
                        vv = (act[i] + L_) * side; R.append(((od - 1) if vv > 0 else (0 if vv == 0 else -1), seasn[i]))
                a = np.array([q[0] for q in R]); ys = sorted(set(q[1] for q in R))
                pos = sum(1 for Y in ys if np.mean([q[0] for q in R if q[1] == Y]) > 0)
                cells.append(f'{"ανοιγμα" if when == "o" else "κλεισ."} {a.mean()*100 if len(a) else 0:+.1f}% ({len(a)}, {a.sum():+.1f}u, {pos}/{len(ys)})')
            P(f'       {fam}: Κ2 b {bb:+.3f} (t {bb/se:+.1f}) · ROI ' + ' · '.join(cells))
# ---- in-sample χαρτης (πρωτα 6 ολα) ----
P(''); P('=== IN-SAMPLE RMSE πρωτα 6 (U2021-25), γραμμες κ_n, στηλες δ ===')
for kx in (0, 3):
    P(f'  κ_x {kx}:  δ = -3 / -2 / -1 / 0 / +1')
    for kn in (0, .35, .5, .7, 1):
        P(f'    κ_n {kn:<4}: ' + ' '.join(f'{rmm(PRED[(kx, kn, dl)], EV, GN <= 5):.3f}' for dl in (-3, -2, -1, 0, 1)))
open('ec_newcomers_test_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
