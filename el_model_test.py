# -*- coding: utf-8 -*-
"""el_model_test.py — ΕΥΡΩΛΙΓΚΑ: πρωτο ιστορικο τεστ μοντελου vs closing Pinnacle (24/9/2026).

ΜΟΝΤΕΛΟ (MVP της ερευνας, basketball_methodology_research.md):
  κατοχες/ματς = FGA + 0.44·FTA − ORB + TOV (μεσος δυο ομαδων), ανα 40'.
  Αποδοτικοτητα (ποντοι/100 κατοχες): y = mu + O_επιθεσης + D_αμυνας_αντιπαλου ± h/2 (h = εδρα, 0 στο Final Four).
  Ρυθμος: pace = pm + P_h + P_a.
  Walk-forward: για καθε μερα ματς, fit ΜΟΝΟ με ματς της τρεχουσας σεζον ΠΡΙΝ απο αυτη τη μερα,
  βαρος 0.5^(ηλικια/HL μερες), ridge προς prior = carry × τελικο rating περσινης σεζον (νεες ομαδες: 0),
  ισχυς prior λ (σε ισοδυναμες παρατηρησεις — σαν το K του n/(n+K)).
  Προβλεψη: poss × (eff_h − eff_a)/100 = διαφορα · poss × (eff_h + eff_a)/100 = συνολο.
  Παραλλαγη L («τυχη»): στους ποντους, 3P% και FT% του ματς μισο-δρομο προς τον περσινο μεσο λιγκας.

ΠΡΟ-ΔΗΛΩΣΗ (γραφτηκε ΠΡΙΝ ανοιχτουν αποδοσεις· ΜΙΑ εκτελεση):
  ΡΥΘΜΙΣΗ: HL ∈ {30,60,120,9999}, λ ∈ {2,4,8,14,24}, carry ∈ {0.3,0.5,0.7}, h ∈ {2,3,4,5,6} (ποντοι/100),
    παραλλαγη ∈ {raw, L} — επιλογη με RMSE διαφορας στις E2021+E2022 (χωρις αποδοσεις· E2020 εκτος: αδεια γηπεδα).
  ΚΡΙΣΗ (παγωμενες παραμετροι) στις E2023-E2025 vs Pinnacle closing (fallback: διαμεσος βιβλιων):
    Κ1 ακριβεια: RMSE/MAE διαφορας & συνολου — μοντελο vs αγορα (αναμενεται αγορα καλυτερη).
    Κ2 «προσθετει πληροφορια»: κλιση b του (πραγματικο − αγορα) πανω στο (μοντελο − αγορα).
       ΠΕΡΝΑ αν b ≥ 0.15 ΚΑΙ t ≥ 2 (ενωμενο) ΚΑΙ b > 0 σε ≥ 2/3 σεζον. Ξεχωριστα για διαφορα και συνολο.
    Κ3 ROI στις closing τιμες Pinnacle οπου |μοντελο − αγορα| ≥ 2/4 ποντοι (διαφορα) ή ≥ 3/6 (συνολο) — ΑΝΑΦΟΡΑ μονο.
Εξοδος: el_model_test_out.txt, el_model_preds.csv
"""
import sys, json, math, itertools, unicodedata, re, datetime as dt
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))

# ---------------- δεδομενα ----------------
B = json.load(open('el_box.json', encoding='utf-8'))
rows = []
for k, g in B.items():
    if 'err' in g or not g.get('h') or g['h'].get('pts') is None:
        continue
    h, a = g['h'], g['a']
    gm = (g.get('min') or 200) / 5.0
    ph = h['fga2'] + h['fga3'] + 0.44 * h['fta'] - h['orb'] + h['tov']
    pa = a['fga2'] + a['fga3'] + 0.44 * a['fta'] - a['orb'] + a['tov']
    poss = (ph + pa) / 2
    if ph < 40 or pa < 40 or h['pts'] != g['hs'] or a['pts'] != g['as_']:
        continue   # χαλασμενο box απο την πηγη (2 ματς: E2017_14, E2018_21)
    rows.append(dict(key=k, season=g['season'], phase=g['phase'], utc=g['utc'], home=g['hcode'], away=g['acode'],
                     hname=g['home'], aname=g['away'], hs=g['hs'], as_=g['as_'], gmin=gm, poss=poss, pace=poss * 40 / gm,
                     **{f'h_{c}': h[c] for c in ('pts', 'fgm3', 'fga3', 'ftm', 'fta')},
                     **{f'a_{c}': a[c] for c in ('pts', 'fgm3', 'fga3', 'ftm', 'fta')}))
D = pd.DataFrame(rows)
D['t'] = pd.to_datetime(D.utc, utc=True); D = D.sort_values('t').reset_index(drop=True)
D['date'] = D.t.dt.date
D['neutral'] = (D.phase == 'FF').astype(int)
SEAS = sorted(D.season.unique())
P(f'ματς: {len(D)} · σεζον {SEAS} · μεσος ρυθμος {D.pace.mean():.1f} κατοχες/40 · ποντοι/100 {100*(D.h_pts+D.a_pts).sum()/(2*D.poss.sum()):.1f}')
P(f'  εδρα (ωμη): γηπεδουχος κερδιζει {(D[D.neutral==0].hs > D[D.neutral==0].as_).mean()*100:.1f}% · διαφορα {(D[D.neutral==0].hs - D[D.neutral==0].as_).mean():+.2f}')

# ποσοστα λιγκας ανα σεζον (για την παραλλαγη L χρησιμοποιουμε της ΠΡΟΗΓΟΥΜΕΝΗΣ)
LG = {}
for s, g in D.groupby('season'):
    LG[s] = dict(p3=(g.h_fgm3.sum() + g.a_fgm3.sum()) / (g.h_fga3.sum() + g.a_fga3.sum()),
                 ft=(g.h_ftm.sum() + g.a_ftm.sum()) / (g.h_fta.sum() + g.a_fta.sum()))
def lg_prev(s):
    i = SEAS.index(s); return LG[SEAS[i - 1]] if i > 0 else LG[s]

def points(df, var):
    if var == 'raw':
        return df.h_pts.values.astype(float), df.a_pts.values.astype(float)
    res = []
    for side in ('h', 'a'):
        p3l = np.array([lg_prev(s)['p3'] for s in df.season]); ftl = np.array([lg_prev(s)['ft'] for s in df.season])
        m3, a3, mf, af = (df[f'{side}_{c}'].values.astype(float) for c in ('fgm3', 'fga3', 'ftm', 'fta'))
        p3g = np.where(a3 > 0, m3 / np.maximum(a3, 1), p3l); ftg = np.where(af > 0, mf / np.maximum(af, 1), ftl)
        adj = df[f'{side}_pts'].values - 3 * m3 + 3 * a3 * (0.5 * p3g + 0.5 * p3l) - mf + af * (0.5 * ftg + 0.5 * ftl)
        res.append(adj)
    return res[0], res[1]

# ---------------- walk-forward ----------------
def fit_eff(hi, ai, eh, ea, hb, w, n, o0, d0, lam, mu0):
    nG = len(hi); sw = np.sqrt(w)
    A = np.zeros((2 * nG + 2 * n + 1, 1 + 2 * n)); y = np.zeros(2 * nG + 2 * n + 1)
    r0 = np.arange(nG); r1 = nG + r0
    A[r0, 0] = sw; A[r0, 1 + hi] = sw; A[r0, 1 + n + ai] = sw; y[r0] = sw * (eh - hb)
    A[r1, 0] = sw; A[r1, 1 + ai] = sw; A[r1, 1 + n + hi] = sw; y[r1] = sw * (ea + hb)
    sl = math.sqrt(lam); k = np.arange(n)
    A[2 * nG + k, 1 + k] = sl; y[2 * nG + k] = sl * o0
    A[2 * nG + n + k, 1 + n + k] = sl; y[2 * nG + n + k] = sl * d0
    A[-1, 0] = math.sqrt(5.0); y[-1] = math.sqrt(5.0) * mu0
    x = np.linalg.lstsq(A, y, rcond=None)[0]
    return x[0], x[1:1 + n], x[1 + n:]

def fit_pace(hi, ai, pc, w, n, p0, lam, pm0):
    nG = len(hi); sw = np.sqrt(w)
    A = np.zeros((nG + n + 1, 1 + n)); y = np.zeros(nG + n + 1); r0 = np.arange(nG)
    A[r0, 0] = sw; A[r0, 1 + hi] += sw; A[r0, 1 + ai] += sw; y[r0] = sw * pc
    sl = math.sqrt(lam); k = np.arange(n)
    A[nG + k, 1 + k] = sl; y[nG + k] = sl * p0
    A[-1, 0] = math.sqrt(5.0); y[-1] = math.sqrt(5.0) * pm0
    x = np.linalg.lstsq(A, y, rcond=None)[0]
    return x[0], x[1:]

_PTS = {}
def run(HL, lam, carry, h, var, upto=None):
    if var not in _PTS:
        ph, pa = points(D, var); _PTS[var] = (100 * ph / D.poss.values, 100 * pa / D.poss.values)
    EH, EA = _PTS[var]
    preds = np.full((len(D), 2), np.nan)
    prior = {}; mu0 = float((EH.mean() + EA.mean()) / 2); pm0 = float(D.pace.mean())
    dnum = np.array([(d - D.date.iloc[0]).days for d in D.date])
    for s in SEAS:
        if upto and s > upto:
            break
        sidx = np.where(D.season.values == s)[0]
        teams = sorted(set(D.home.values[sidx]) | set(D.away.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        hi_all = np.array([ix[t] for t in D.home.values[sidx]]); ai_all = np.array([ix[t] for t in D.away.values[sidx]])
        hb_all = np.where(D.neutral.values[sidx] == 1, 0.0, h / 2)
        o0 = np.array([carry * prior.get(t, (0, 0, 0))[0] for t in teams]); d0 = np.array([carry * prior.get(t, (0, 0, 0))[1] for t in teams])
        p0 = np.array([carry * prior.get(t, (0, 0, 0))[2] for t in teams])
        dn = dnum[sidx]; eh = EH[sidx]; ea = EA[sidx]; pc = D.pace.values[sidx]
        for d in np.unique(dn):
            past = dn < d; cur = np.where(dn == d)[0]
            if past.any():
                w = 0.5 ** ((d - dn[past]) / HL)
                mu, O, Dd = fit_eff(hi_all[past], ai_all[past], eh[past], ea[past], hb_all[past], w, n, o0, d0, lam, mu0)
                pm, Pc = fit_pace(hi_all[past], ai_all[past], pc[past], w, n, p0, lam, pm0)
            else:
                mu, O, Dd, pm, Pc = mu0, o0, d0, pm0, p0
            hh, aa, hb = hi_all[cur], ai_all[cur], hb_all[cur]
            e_h = mu + O[hh] + Dd[aa] + hb; e_a = mu + O[aa] + Dd[hh] - hb
            poss = pm + Pc[hh] + Pc[aa]
            preds[sidx[cur], 0] = poss * (e_h - e_a) / 100; preds[sidx[cur], 1] = poss * (e_h + e_a) / 100
        w = 0.5 ** ((dn.max() - dn) / HL)
        mu, O, Dd = fit_eff(hi_all, ai_all, eh, ea, hb_all, w, n, o0, d0, lam, mu0)
        pm, Pc = fit_pace(hi_all, ai_all, pc, w, n, p0, lam, pm0)
        prior = {t: (O[i], Dd[i], Pc[i]) for t, i in ix.items()}; mu0 = mu; pm0 = pm
    return preds

# ---------------- ρυθμιση (χωρις αποδοσεις) ----------------
TUNE = D.season.isin(['E2021', 'E2022']).values
act = (D.hs - D.as_).values.astype(float)
best = None; P(); P('=== ΡΥΘΜΙΣΗ στις E2021+E2022 (RMSE διαφορας, χωρις αποδοσεις) ===')
grid = list(itertools.product([30, 60, 120, 9999], [2, 4, 8, 14, 24], [0.3, 0.5, 0.7], [2, 3, 4, 5, 6], ['raw', 'L']))
res = []
for HL, lam, carry, h, var in grid:
    pr = run(HL, lam, carry, h, var, upto='E2022')
    rm = math.sqrt(np.mean((act[TUNE] - pr[TUNE, 0]) ** 2)); res.append((rm, HL, lam, carry, h, var))
res.sort()
for r in res[:8]:
    P(f'  RMSE {r[0]:.3f} · HL {r[1]} · λ {r[2]} · carry {r[3]} · h {r[4]} · {r[5]}')
for v in ('raw', 'L'):
    bv = [r for r in res if r[5] == v][0]; P(f'  καλυτερο {v}: RMSE {bv[0]:.3f}')
_, HL, lam, carry, h, var = res[0]
P(f'ΠΑΓΩΜΕΝΟ: HL={HL} λ={lam} carry={carry} h={h} παραλλαγη={var}')
PR = run(HL, lam, carry, h, var)
D['m_model'] = PR[:, 0]; D['t_model'] = PR[:, 1]

# ---------------- αγορα: TOA closing ----------------
def tok(s):
    s = unicodedata.normalize('NFD', str(s)); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    return set(w for w in re.findall(r'[a-z]{3,}', s) if w not in ('basketball', 'basket', 'club', 'the', 'sport'))
ODDS = [json.loads(l) for l in open('toa_el_closing.jsonl', encoding='utf-8')]
byid = {}
for o in ODDS:
    byid[o['id']] = o
mk = {}
EV = D[D.season.isin(['E2023', 'E2024', 'E2025'])]
for o in byid.values():
    ct = pd.Timestamp(o['commence'])
    c = EV[(EV.t - ct).abs() <= pd.Timedelta(minutes=25)]
    if not len(c):
        continue
    th, ta = tok(o['home']), tok(o['away'])
    sc = [(len(th & tok(r.hname)) + len(ta & tok(r.aname)) - 0.5 * (len(th & tok(r.aname)) + len(ta & tok(r.hname))), i) for i, r in c.iterrows()]
    sc.sort(reverse=True)
    if len(c) > 1 and sc[0][0] <= 0:
        continue
    i = sc[0][1]; r = D.loc[i]
    flip = len(th & tok(r.aname)) > len(th & tok(r.hname))
    hn_toa, an_toa = (o['away'], o['home']) if flip else (o['home'], o['away'])   # ονομα TOA του ΕΠΙΣΗΜΟΥ γηπεδουχου/φιλοξ.
    def line(bk):
        sp = tt = None
        for m in bk['markets']:
            if m['key'] == 'spreads':
                hh_ = [x for x in m['outcomes'] if x['name'] == hn_toa]; aa_ = [x for x in m['outcomes'] if x['name'] == an_toa]
                if hh_ and aa_ and hh_[0].get('point') is not None:
                    sp = (hh_[0]['point'], hh_[0]['price'], aa_[0]['price'])
            if m['key'] == 'totals':
                ov = [x for x in m['outcomes'] if x['name'] == 'Over']; un = [x for x in m['outcomes'] if x['name'] == 'Under']
                if ov and un:
                    tt = (ov[0]['point'], ov[0]['price'], un[0]['price'])
        return sp, tt
    pin = [b for b in o['bookmakers'] if b['key'] == 'pinnacle']
    sp = tt = None; src = 'pinnacle'
    if pin:
        sp, tt = line(pin[0])
    if not sp or not tt or len(sp) < 3:
        allsp = [line(b) for b in o['bookmakers']]
        spl = [x[0] for x in allsp if x[0] and len(x[0]) == 3]; ttl = [x[1] for x in allsp if x[1]]
        if not sp or len(sp) < 3:
            sp = (float(np.median([x[0] for x in spl])), 1.91, 1.91) if spl else None; src = 'median'
        if not tt and ttl:
            tt = (float(np.median([x[0] for x in ttl])), 1.91, 1.91); src = 'median'
    if sp and tt and len(sp) == 3:
        mk[i] = dict(spread=float(sp[0]), sp_h=sp[1], sp_a=sp[2], total=float(tt[0]), ov=tt[1], un=tt[2], src=src)
M = pd.DataFrame.from_dict(mk, orient='index')
E = D.loc[M.index].join(M)
P(); P(f'=== ΚΡΙΣΗ E2023-E2025: ματς με closing {len(E)} (απο {len(EV)}) · Pinnacle {int((E.src=="pinnacle").sum())} ===')
E['m_mkt'] = -E.spread; E['act'] = E.hs - E.as_; E['tot'] = E.hs + E.as_
E.to_csv('el_model_preds.csv', index=False)

def tt_(x):
    x = np.asarray(x, float); return x.mean() / (x.std(ddof=1) / math.sqrt(len(x)))

P(); P('Κ1 ΑΚΡΙΒΕΙΑ (χαμηλοτερο = καλυτερο)')
for lab, a, mm, mo in (('διαφορα', E.act, E.m_mkt, E.m_model), ('συνολο', E.tot, E.total, E.t_model)):
    P(f'  {lab:8s} RMSE αγορα {math.sqrt(((a-mm)**2).mean()):.2f} · μοντελο {math.sqrt(((a-mo)**2).mean()):.2f} · '
      f'MAE αγορα {(a-mm).abs().mean():.2f} · μοντελο {(a-mo).abs().mean():.2f} · μεροληψια μοντελου {(a-mo).mean():+.2f}')
for s, g in E.groupby('season'):
    P(f'    {s}: διαφορα RMSE αγορα {math.sqrt(((g.act-g.m_mkt)**2).mean()):.2f} / μοντελο {math.sqrt(((g.act-g.m_model)**2).mean()):.2f} · '
      f'συνολο {math.sqrt(((g.tot-g.total)**2).mean()):.2f} / {math.sqrt(((g.tot-g.t_model)**2).mean()):.2f}')

P(); P('Κ2 ΠΡΟΣΘΕΤΕΙ ΠΛΗΡΟΦΟΡΙΑ; κλιση b του (πραγματικο − αγορα) πανω στο (μοντελο − αγορα)')
verdict = {}
for lab, a, mm, mo in (('διαφορα', 'act', 'm_mkt', 'm_model'), ('συνολο', 'tot', 'total', 't_model')):
    x = (E[mo] - E[mm]).values; y = (E[a] - E[mm]).values
    b = np.polyfit(x, y, 1)[0]; res_ = y - np.poly1d(np.polyfit(x, y, 1))(x)
    se = res_.std(ddof=2) / (x.std() * math.sqrt(len(x))); per = []
    for s, g in E.groupby('season'):
        xs = (g[mo] - g[mm]).values; ys = (g[a] - g[mm]).values; per.append(np.polyfit(xs, ys, 1)[0])
    ok = b >= 0.15 and b / se >= 2 and sum(p > 0 for p in per) >= 2
    verdict[lab] = ok
    P(f'  {lab:8s} b = {b:+.3f} (t {b/se:.1f}) · ανα σεζον ' + ' / '.join(f'{p:+.2f}' for p in per) +
      f' · sd διαφωνιας {x.std():.2f} π. → {"ΠΕΡΝΑ" if ok else "ΔΕΝ ΠΕΡΝΑ"}')

P(); P('Κ3 ROI στο closing (αναφορα)')
def settle_sp(act_margin, line_home, side, odds):
    v = act_margin + line_home if side == 1 else -(act_margin + line_home)
    return (odds - 1) if v > 0 else (0.0 if v == 0 else -1.0)
for thr in (2, 4):
    pnl = []; per = {}
    for _, r in E.iterrows():
        dff = r.m_model - r.m_mkt
        if abs(dff) < thr:
            continue
        side = 1 if dff > 0 else -1; odds = r.sp_h if side == 1 else r.sp_a
        p = settle_sp(r.act, r.spread, side, odds); pnl.append(p); per.setdefault(r.season, []).append(p)
    if pnl:
        P(f'  διαφορα |μοντελο−αγορα| ≥ {thr}: n {len(pnl)} · ROI {np.mean(pnl)*100:+.1f}% (t {tt_(pnl):.1f}) · ' +
          ' '.join(f'{s} {np.mean(v)*100:+.1f}%({len(v)})' for s, v in sorted(per.items())))
for thr in (3, 6):
    pnl = []; per = {}
    for _, r in E.iterrows():
        dff = r.t_model - r.total
        if abs(dff) < thr:
            continue
        over = dff > 0; odds = r.ov if over else r.un; v = (r.tot - r.total) * (1 if over else -1)
        p = (odds - 1) if v > 0 else (0.0 if v == 0 else -1.0); pnl.append(p); per.setdefault(r.season, []).append(p)
    if pnl:
        P(f'  συνολο |μοντελο−αγορα| ≥ {thr}: n {len(pnl)} · ROI {np.mean(pnl)*100:+.1f}% (t {tt_(pnl):.1f}) · ' +
          ' '.join(f'{s} {np.mean(v)*100:+.1f}%({len(v)})' for s, v in sorted(per.items())))
P(); P(f'Διασπορα πραγματικου γυρω απο την αγορα: διαφορα σ = {(E.act-E.m_mkt).std():.2f} π. · συνολο σ = {(E.tot-E.total).std():.2f} π.')
P(f'ΕΤΥΜΗΓΟΡΙΑ Κ2: διαφορα {"ΠΕΡΝΑ" if verdict["διαφορα"] else "ΔΕΝ ΠΕΡΝΑ"} · συνολο {"ΠΕΡΝΑ" if verdict["συνολο"] else "ΔΕΝ ΠΕΡΝΑ"}')
open('el_model_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
