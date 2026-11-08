# -*- coding: utf-8 -*-
"""ec_expert_test.py — ΓΝΩΣΗ ΕΙΔΙΚΩΝ στο EuroCup (1/10/2026, Στελιος: «προτου βγαλουμε συμπερασματα ας βαλουμε και τη γνωση των ειδικων»).
ΠΗΓΕΣ (ec_expert.json <- ec_expert_map.py):
  ΚΑΤΑΤΑΞΕΙΣ πριν την 1η αγωνιστικη: Eurohoops 2018-19…2023-24 · Taking The Charge 2022-23, 2024-25, 2025-26 -> καθε σεζον U2018-U2025 εχει >=1.
  OUTRIGHTS (Wayback): U2023 (1 βιβλιο, 17/20), U2024 (10/20), U2025 (bwin 20/20) πριν την 1η · U2021 μετα ~4 αγωνιστικες (ΜΟΝΟ πληροφοριακα).
ΜΕΤΑΤΡΟΠΗ σε z (μεσος 0, τ.α. ~1): καταταξη -> κανονικο σκορ θεσης Φ^-1(1-(r-1/2)/N) (μεσος οσων πηγων υπαρχουν) ·
  outright -> -ln(αποδοση) τυποποιημενο με κοινο μεσο/τ.α. ολων των τιμων · ομαδα χωρις τιμη = 0 · ΣΥΝΔΥΑΣΜΟΣ = μεσος ολων.
ΜΗΧΑΝΗ: ec_early_test (εγχωρια κ 1 απο 1ο αγωνα + προετοιμασια κ_pre) · αφετηρια += κ_x·z·100/72 (μισο επιθεση/μισο αμυνα) —
  σβηνει μονη της οσο μαζευονται ματς (ιδιο με την προετοιμασια).
ΠΛΕΓΜΑ: κ_pre {0, .25, .5} × κ_x {0, 1, 2, 3, 4, 6} ποντοι ανα 1 z × πηγη {ΚΑΤΑΤΑΞΕΙΣ, OUTRIGHTS, ΣΥΝΔΥΑΣΜΟΣ}.
ΠΡΟ-ΔΗΛΩΜΕΝΟ (γραφτηκε ΠΡΙΝ την εκτελεση): LOSO στις U2018-U2025 με RMSE διαφορας στα ΠΡΩΤΑ 6 ματς.
  ΚΑΤΑΤΑΞΕΙΣ / ΣΥΝΔΥΑΣΜΟΣ ΠΕΡΝΑΝΕ αν καλυτερα απο «χωρις ειδικους» σε >=6/8 σεζον · OUTRIGHTS αν καλυτερα σε 3/3 (U2023-U2025).
  Αναφορα: πρωτα 3 · 7+ · ολα · Κ2/ROI χαντικαπ vs Crown (U2020-U2025) · κλιση υπολοιπου (πραγματικο - βαση) πανω στο zΓ - zΦ.
Εξοδος: ec_expert_test_out.txt"""
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

EV8 = ['U2018', 'U2019', 'U2020', 'U2021', 'U2022', 'U2023', 'U2024', 'U2025']
EX = json.load(open('ec_expert.json', encoding='utf-8'))
_nd = NormalDist()
ZR, ZO, ZC = {}, {}, {}
allv = [-math.log(d['odds']) for S in EX for d in EX[S].values() if 'odds' in d and S != 'U2021']
m0, s0 = float(np.mean(allv)), float(np.std(allv))
for S, tm in EX.items():
    for c, d in tm.items():
        zr = [_nd.inv_cdf(1 - (d[k] - .5) / d[k + '_n']) for k in ('EH', 'TTC') if k in d]
        if zr: ZR[(S, c)] = float(np.mean(zr))
        if 'odds' in d: ZO[(S, c)] = (-math.log(d['odds']) - m0) / s0
        zz = zr + ([ZO[(S, c)]] if (S, c) in ZO else [])
        if zz: ZC[(S, c)] = float(np.mean(zz))
SRC = {'ΚΑΤΑΤΑΞΕΙΣ': ZR, 'OUTRIGHTS': ZO, 'ΣΥΝΔΥΑΣΜΟΣ': ZC}
P(''); P(f'z: καταταξεις {len(ZR)} · outrights {len(ZO)} (μεσος -ln {m0:.2f}, τ.α. {s0:.2f}) · συνδυασμος {len(ZC)}')
GR = [(kp, 0.0, 'Χ') for kp in (0, .25, .5)] + [(kp, kx, s) for s in SRC for kp in (0, .25, .5) for kx in (1, 2, 3, 4, 6)]
PRED = {}
for i, (kp, kx, s) in enumerate(GR):
    PRED[(kp, kx, s)] = run(kp, 1, 1, kx, SRC.get(s))
    if i % 8 == 0: print(f'  {i + 1}/{len(GR)} …', flush=True)
seasn = D.season.values
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
FAMS = {'ΧΩΡΙΣ ΕΙΔΙΚΟΥΣ': lambda g: g[2] == 'Χ'}
for s in SRC: FAMS[s] = (lambda s_: (lambda g: g[2] == 'Χ' or g[2] == s_))(s)
MASKS = (('ΠΡΩΤΑ 3 ΜΑΤΣ', GN <= 2), ('ΠΡΩΤΑ 6 ΜΑΤΣ', GN <= 5), ('ΜΑΤΣ 7+', GN >= 6), ('ΟΛΑ', GN >= 0))
HELD6 = {}
for lab, msk in MASKS:
    P(''); P(f'=== {lab} · LOSO U2018-U2025 (επιλογη με RMSE στα ιδια ματς των ΑΛΛΩΝ σεζον) · ματς {int((np.isin(seasn, EV8) & msk).sum())} ===')
    HELD = {}
    for fam, ok in FAMS.items():
        held = np.full(len(D), np.nan); ch = []
        for Y in EV8:
            tr = [x for x in EV8 if x != Y]; g = min([g for g in PRED if ok(g)], key=lambda g: rmm(PRED[g], tr, msk)); ch.append(g[:2])
            held[seasn == Y] = PRED[g][seasn == Y]
        HELD[fam] = held
        if fam == 'ΧΩΡΙΣ ΕΙΔΙΚΟΥΣ':
            P(f'  {fam:16s} RMSE {rmm(held, EV8, msk):.3f} · επιλογες (κ_pre, κ_x) {ch}'); continue
        d = [rmm(held, [Y], msk) - rmm(HELD['ΧΩΡΙΣ ΕΙΔΙΚΟΥΣ'], [Y], msk) for Y in EV8]
        ssn = EV8 if fam != 'OUTRIGHTS' else ['U2023', 'U2024', 'U2025']
        good = sum(d[EV8.index(Y)] < 0 for Y in ssn)
        crit = ''
        if lab == 'ΠΡΩΤΑ 6 ΜΑΤΣ': crit = ('  <- ΠΕΡΝΑ' if (good >= 6 if fam != 'OUTRIGHTS' else good == 3) else '  <- ✗')
        P(f'  {fam:16s} RMSE {rmm(held, EV8, msk):.3f} · vs χωρις ' + ' '.join(f'{Y[-2:]}:{x:+.3f}' for Y, x in zip(EV8, d))
          + f' -> καλυτερο {good}/{len(ssn)}{crit} · επιλογες {ch}')
    if lab == 'ΠΡΩΤΑ 6 ΜΑΤΣ': HELD6 = HELD
    for fam, v in HELD.items():
        ii = [i for i in MK if seasn[i] in EV8 and msk[i] and np.isfinite(v[i])]
        if len(ii) < 30: continue
        x = np.array([v[i] - MK[i]['c'][1] for i in ii]); z = np.array([act[i] - MK[i]['c'][1] for i in ii])
        b = np.polyfit(x, z, 1)[0]; r_ = z - np.polyval(np.polyfit(x, z, 1), x); se = math.sqrt(np.sum(r_ ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2))
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
            cells.append(f'{"ανοιγμα" if when == "o" else "κλεισιμο"} {a.mean()*100 if len(a) else 0:+.1f}% ({len(a)}, {a.sum():+.1f} μον., {pos}/{len(ys)})')
        P(f'    αγορα {fam:16s} n {len(ii)} · Κ2 b {b:+.3f} (t {b/se:+.1f}) · ROI ' + ' · '.join(cells))
P(''); P('=== ΚΛΙΣΗ υπολοιπου (πραγματικο - μοντελο χωρις ειδικους) πανω στο zΓηπ - zΦιλ · πρωτα 6 ματς ===')
v0 = HELD6['ΧΩΡΙΣ ΕΙΔΙΚΟΥΣ']
for s, Z in SRC.items():
    ii = [i for i in range(len(D)) if seasn[i] in EV8 and GN[i] <= 5 and np.isfinite(v0[i]) and (seasn[i], D.home.values[i]) in Z and (seasn[i], D.away.values[i]) in Z]
    x = np.array([Z[(seasn[i], D.home.values[i])] - Z[(seasn[i], D.away.values[i])] for i in ii]); y = np.array([act[i] - v0[i] for i in ii])
    b = np.polyfit(x, y, 1)[0]; r_ = y - np.polyval(np.polyfit(x, y, 1), x); se = math.sqrt(np.sum(r_ ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2))
    per = []
    for Y in EV8:
        m = np.array([seasn[i] == Y for i in ii])
        if m.sum() > 15: per.append(f'{Y[-2:]}:{np.polyfit(x[m], y[m], 1)[0]:+.1f}')
    P(f'  {s:12s} n {len(ii)} · {b:+.2f} ποντοι ανα 1 z διαφορας (t {b/se:+.1f}) · ανα σεζον ' + ' '.join(per))
open('ec_expert_test_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
