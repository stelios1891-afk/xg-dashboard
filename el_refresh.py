# -*- coding: utf-8 -*-
"""el_refresh.py — ΚΑΘΗΜΕΡΙΝΗ ενημερωση Ευρωλιγκας: νεα ματς + προβλεψεις (25/9/2026).
 1. προγραμμα τρεχουσας σεζον (επισημο API) -> el_sched.json[SEASON]
 2. box score για οσα ματς της σεζον παιχτηκαν και λειπουν -> el_box.json
 3. μοντελο: χαντικαπ/1-2 = v1 (HL=120, λ=8, carry=0.7, εδρα 6/100, τυχη 50%)· συνολο = v2 (τυχη 25%, χωρις φθορα, mu_w 50) [25/9],
    + δυο κανονες που συμφωνηθηκαν 25/9: (α) νεες ομαδες ξεκινουν κατω απο τη μεση (NEWCOMER_PRIOR),
    (β) «εντος» ματς >300 χλμ απο το πραγματικο σπιτι της ομαδας = ουδετερο (ισραηλινες σε Βελιγραδι/Σοφια κτλ).
 4. -> el_projections.json (επερχομενα ματς: ποντοι, διαφορα, συνολο, πιθανοτητα νικης· ratings ομαδων)
Τρεχει τοπικα ή στο GitHub (χωρις κλειδια)."""
import sys, os, json, math, time, datetime as dt, urllib.request, urllib.error
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
SEASON = 'E2026'
LAM = 8                                          # βαρος περσινης εικονας (ισοδυναμα ματς)
# ΔΥΟ ΜΗΧΑΝΕΣ (αποφαση Στελιου 25/9, μετα LOSO + ROI με edge σε 6 σεζον):
ENG_SPREAD = dict(luck=0.5, HL=120, carry=0.7, mu_w=5.0, h=6.0)    # χαντικαπ/1-2 = v1 (ROI καλυτερο απο v2 σε ολα τα edge)
ENG_TOTAL = dict(luck=0.25, HL=9999, carry=0.7, mu_w=50.0, h=6.0)  # συνολο = v2 (LOSO b .314 vs .272· edge>=8% +5.5% 6/6 vs +2.0%)
# ΕΙΔΙΚΟΙ στην αρχη σεζον (αποφαση Στελιου 25/9): αρχικο net χαντικαπ = 0.32·ομαδα περσι + 0.42·ειδικοι (τεστ Γ, LOSO 2021-25)
# v1 αρχικο net = 0.7·περσι → νεο = (0.32/0.7)·(v1 αρχικο) + 0.42·(rating θεσης BasketNews). Μονο χαντικαπ/1-2, οχι συνολο.
EXPERTS = json.load(open('el_expert_prior.json', encoding='utf-8')) if os.path.exists('el_expert_prior.json') else None
# ΚΑΜΠΥΛΗ ΣΚΟΡ (25/9, el_total_curve_test.py «Κ2», αποφαση Στελιου): αντι σταθερου +1.1 (παρατασεις), διορθωση που μεγαλωνει
# με τον αριθμο αγωνα της σεζον: +0.34 + 0.098×αγωνιστικη (1η +0.4 · 17η +2.0 · 34η +3.7)· τα σκορ ανεβαινουν ~7 π. μεσα στη σεζον.
# Περιλαμβανει τις παρατασεις. Τεστ: RMSE 16.48→16.44 (5/6) · b .368→.383 · ROI συνολων ≥8% +7.2→+8.2% (6/6).
CURVE_A, CURVE_B = 0.34, 0.098
OT_ADD = 1.1   # (παλια σταθερη διορθωση — κρατιεται μονο για αναφορα)
NEWCOMER_PRIOR = {'BES': (-1.0, 1.0, 0.0)}      # (επιθεση, αμυνα, ρυθμος) ποντοι/100 — Μπεσικτας −2 net (συμφωνια 25/9)
SIGMA_MARGIN, SIGMA_TOTAL = 11.5, 16.7          # διασπορα γυρω απο την αγορα, E2023-25
HDR = {'User-Agent': 'Mozilla/5.0 Chrome/120.0', 'Accept': 'application/json'}

def J(u):
    for a in range(6):
        try:
            time.sleep(0.8)
            return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=HDR), timeout=40).read())
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            time.sleep(60 * (1 + a // 2) if e.code == 429 else 3)
        except Exception:
            time.sleep(3 + 3 * a)
    return None

# ---- 1. προγραμμα ----
S = json.load(open('el_sched.json', encoding='utf-8'))
g = J(f'https://api-live.euroleague.net/v2/competitions/E/seasons/{SEASON}/games')
if g and g.get('data'):
    S[SEASON] = [dict(code=x['gameCode'], phase=x['phaseType']['code'], rnd=x['round'], utc=x['utcDate'], local=x.get('localDate'),
                      tz=x.get('localTimeZone'), played=x.get('played'), neutral=x.get('isNeutralVenue'),
                      venue=(x.get('venue') or {}).get('code'), vname=(x.get('venue') or {}).get('name'), aud=x.get('audience'),
                      hcode=x['local']['club']['code'], acode=x['road']['club']['code'],
                      home=x['local']['club']['name'], away=x['road']['club']['name'], hs=x['local']['score'], as_=x['road']['score'],
                      hcrest=((x['local']['club'].get('images') or {}).get('crest')), acrest=((x['road']['club'].get('images') or {}).get('crest')))
                 for x in g['data']]
    json.dump(S, open('el_sched.json', 'w', encoding='utf-8'), ensure_ascii=False)
print(f'{SEASON}: {len(S.get(SEASON, []))} ματς στο προγραμμα · παιχτηκαν {sum(1 for x in S.get(SEASON, []) if x["played"])}')

# ---- 2. box scores που λειπουν ----
B = json.load(open('el_box.json', encoding='utf-8'))
MAP = dict(pts='Points', fgm2='FieldGoalsMade2', fga2='FieldGoalsAttempted2', fgm3='FieldGoalsMade3', fga3='FieldGoalsAttempted3',
           ftm='FreeThrowsMade', fta='FreeThrowsAttempted', orb='OffensiveRebounds', drb='DefensiveRebounds', tov='Turnovers',
           ast='Assistances', stl='Steals', blk='BlocksFavour', pf='FoulsCommited')
def mins(s):
    try:
        m, sec = str(s).split(':'); return int(m) + int(sec) / 60
    except Exception:
        return None
n_new = 0
for x in S.get(SEASON, []):
    k = f"{SEASON}_{x['code']}"
    if not x['played'] or (k in B and 'err' not in B[k]): continue
    b = J(f"https://live.euroleague.net/api/Boxscore?gamecode={x['code']}&seasoncode={SEASON}")
    rec = dict(season=SEASON, code=x['code'], phase=x['phase'], rnd=x['rnd'], utc=x['utc'], home=x['home'], away=x['away'],
               hcode=x['hcode'], acode=x['acode'], hs=x['hs'], as_=x['as_'])
    if b and b.get('Stats'):
        st = b['Stats']
        for side, t in (('h', st[0]), ('a', st[1])):
            tot = t.get('totr') or {}; rec[side] = {kk: tot.get(v) for kk, v in MAP.items()}
        rec['min'] = mins((st[0].get('totr') or {}).get('Minutes'))
    else:
        rec['err'] = 'no box'
    B[k] = rec; n_new += 1
json.dump(B, open('el_box.json', 'w', encoding='utf-8'), ensure_ascii=False)
print(f'νεα box scores: {n_new}')

# ---- 3. μοντελο ----
src = open('el_model_test.py', encoding='utf-8').read()
src = src[:src.index('# ---------------- walk-forward ----------------')].replace("sys.stdout.reconfigure(encoding='utf-8')", '').replace('P(f', 'pass  # P(f')
ns = {}; exec(src, ns)
src2 = open('el_model_test.py', encoding='utf-8').read(); exec(src2[src2.index('def fit_eff'):src2.index('_PTS = {}')], ns)
D, points, fit_eff, fit_pace = ns['D'], ns['points'], ns['fit_eff'], ns['fit_pace']

# πραγματικο σπιτι ομαδας (για τον κανονα ουδετερου)
_ft = open('el_fatigue_travel.py', encoding='utf-8').read()
_cns = {'math': math, 'np': np}; exec(_ft[_ft.index('CITY = {'):_ft.index('D = pd.read_csv')], _cns)
ll, km = _cns['ll'], _cns['km']
TRUE_HOME = {'TEL': (32.05, 34.79), 'HTA': (32.05, 34.79), 'DUB': (25.21, 55.27), 'BES': (41.04, 29.00), 'PRS': (48.89, 2.36)}
for s in sorted(S):
    for x in S[s]:
        if s <= 'E2022' and x['phase'] == 'RS' and x['hcode'] not in TRUE_HOME and ll(x.get('vname')):
            TRUE_HOME.setdefault(x['hcode'], ll(x['vname']))
def is_neutral(x):
    if x.get('phase') == 'FF' or x.get('neutral'): return True
    th, v = TRUE_HOME.get(x['hcode']), ll(x.get('vname'))
    return bool(th and v and km(th, v) > 300)

LG_PREV = ns['lg_prev']
def luck_eff(w):
    """ποντοι/100 κατοχες με διορθωση τυχης: 3P%/FT% του ματς με βαρος w, υπολοιπο = περσινος μεσος λιγκας."""
    res = []
    for side in ('h', 'a'):
        p3l = np.array([LG_PREV(s)['p3'] for s in D.season]); ftl = np.array([LG_PREV(s)['ft'] for s in D.season])
        m3, a3, mf, af = (D[f'{side}_{c}'].values.astype(float) for c in ('fgm3', 'fga3', 'ftm', 'fta'))
        p3g = np.where(a3 > 0, m3 / np.maximum(a3, 1), p3l); ftg = np.where(af > 0, mf / np.maximum(af, 1), ftl)
        res.append(100 * (D[f'{side}_pts'].values - 3 * m3 + 3 * a3 * (w * p3g + (1 - w) * p3l) - mf + af * (w * ftg + (1 - w) * ftl)) / D.poss.values)
    return res[0], res[1]

def fit_eff_mu(hi, ai, eh, ea, hb, w, n, o0, d0, lam, mu0, mu_w):
    """ιδιο με fit_eff του v1, αλλα με ρυθμιζομενο βαρος mu_w για το επιπεδο λιγκας (v1 = 5)."""
    nG = len(hi); sw = np.sqrt(w)
    A = np.zeros((2 * nG + 2 * n + 1, 1 + 2 * n)); y = np.zeros(2 * nG + 2 * n + 1)
    r0 = np.arange(nG); r1 = nG + r0
    A[r0, 0] = sw; A[r0, 1 + hi] = sw; A[r0, 1 + n + ai] = sw; y[r0] = sw * (eh - hb)
    A[r1, 0] = sw; A[r1, 1 + ai] = sw; A[r1, 1 + n + hi] = sw; y[r1] = sw * (ea + hb)
    sl = math.sqrt(lam); k = np.arange(n)
    A[2 * nG + k, 1 + k] = sl; y[2 * nG + k] = sl * o0; A[2 * nG + n + k, 1 + n + k] = sl; y[2 * nG + n + k] = sl * d0
    A[-1, 0] = math.sqrt(mu_w); y[-1] = math.sqrt(mu_w) * mu0
    x = np.linalg.lstsq(A, y, rcond=None)[0]
    return x[0], x[1:1 + n], x[1 + n:]

dnum = np.array([(d - D.date.iloc[0]).days for d in D.date])
NEU = {}
def build(eng):
    """τρεχει μια «μηχανη» (ENG_*) σε ολες τις σεζον ως σημερα → (state τρεχουσας σεζον, CTX για walk-forward)."""
    EH, EA = luck_eff(eng['luck'])
    HLe, CAe, MUW = eng['HL'], eng['carry'], eng['mu_w']
    prior = {}; mu0 = float((EH.mean() + EA.mean()) / 2); pm0 = float(D.pace.mean()); state = CTX = None
    for s in sorted(set(D.season) | {SEASON}):
        sidx = np.where(D.season.values == s)[0]
        teams = sorted(set(D.home.values[sidx]) | set(D.away.values[sidx]) | ({x['hcode'] for x in S[s]} if s == SEASON else set()))
        ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        pr = {t: NEWCOMER_PRIOR[t] if (s == SEASON and t in NEWCOMER_PRIOR and t not in prior) else tuple(CAe * v for v in prior.get(t, (0, 0, 0))) for t in teams}
        o0 = np.array([pr[t][0] for t in teams]); d0 = np.array([pr[t][1] for t in teams]); p0 = np.array([pr[t][2] for t in teams])
        if eng.get('experts') and EXPERTS and s == EXPERTS['season']:
            for t, i in ix.items():
                if t not in EXPERTS['rating']: continue
                cur = o0[i] - d0[i]
                new = EXPERTS['w_team'] / EXPERTS['v1_carry'] * cur + EXPERTS['w_exp'] * EXPERTS['rating'][t]
                o0[i] += (new - cur) / 2; d0[i] -= (new - cur) / 2
        hi = ai = hb = None
        if len(sidx):
            if s not in NEU:
                NEU[s] = np.array([is_neutral(sd) for sd in [next((y for y in S[s] if f"{s}_{y['code']}" == k), {'phase': ph_, 'hcode': h_}) for k, ph_, h_ in zip(D.key.values[sidx], D.phase.values[sidx], D.home.values[sidx])]])
            hi = np.array([ix[t] for t in D.home.values[sidx]]); ai = np.array([ix[t] for t in D.away.values[sidx]])
            hb = np.where(NEU[s], 0.0, eng['h'] / 2); dn = dnum[sidx]
            ref = (dt.date.today() - D.date.iloc[0]).days if s == SEASON else dn.max()
            w = 0.5 ** ((ref - dn) / HLe)
            mu, O, Dd = fit_eff_mu(hi, ai, EH[sidx], EA[sidx], hb, w, n, o0, d0, LAM, mu0, MUW)
            pm, Pc = fit_pace(hi, ai, D.pace.values[sidx], w, n, p0, LAM, pm0)
        else:
            mu, O, Dd, pm, Pc = mu0, o0, d0, pm0, p0
        if s == SEASON:
            state = dict(mu=mu, pm=pm, O={t: O[i] for t, i in ix.items()}, D={t: Dd[i] for t, i in ix.items()}, P={t: Pc[i] for t, i in ix.items()},
                         n={t: int(((D.season == s) & ((D.home == t) | (D.away == t))).sum()) for t in teams})
            CTX = dict(ix=ix, n=n, o0=o0, d0=d0, p0=p0, mu0=mu0, pm0=pm0, sidx=sidx, hi=hi, ai=ai, hb=hb, dn=dnum[sidx], EH=EH, EA=EA, eng=eng, cache={})
        else:
            prior = {t: (O[i], Dd[i], Pc[i]) for t, i in ix.items()}; mu0 = mu; pm0 = pm
    return state, CTX

# ---- 4. προβλεψεις: ΚΑΙ για τα παιγμενα ματς (με οτι ηξερε το μοντελο ΠΡΙΝ απο το ματς) ----
Phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))
def state_at(c, cut):
    """ratings με ματς της σεζον ΑΥΣΤΗΡΑ πριν απο τη μερα cut (walk-forward, χωρις να ξερει το αποτελεσμα)."""
    if cut in c['cache']: return c['cache'][cut]
    ix, eng = c['ix'], c['eng']
    past = (c['dn'] < cut) if c['hi'] is not None else np.array([], bool)
    if past.any():
        w = 0.5 ** ((cut - c['dn'][past]) / eng['HL']); sid = c['sidx'][past]
        mu, O, Dd = fit_eff_mu(c['hi'][past], c['ai'][past], c['EH'][sid], c['EA'][sid], c['hb'][past], w, c['n'], c['o0'], c['d0'], LAM, c['mu0'], eng['mu_w'])
        pm, Pc = fit_pace(c['hi'][past], c['ai'][past], D.pace.values[sid], w, c['n'], c['p0'], LAM, c['pm0'])
    else:
        mu, O, Dd, pm, Pc = c['mu0'], c['o0'], c['d0'], c['pm0'], c['p0']
    st = dict(mu=mu, pm=pm, O={t: O[i] for t, i in ix.items()}, D={t: Dd[i] for t, i in ix.items()}, P={t: Pc[i] for t, i in ix.items()})
    c['cache'][cut] = st; return st
def predict(st, hcode, acode, neu, h):
    hb = 0 if neu else h / 2
    eh = st['mu'] + st['O'][hcode] + st['D'][acode] + hb; ea = st['mu'] + st['O'][acode] + st['D'][hcode] - hb
    poss = st['pm'] + st['P'][hcode] + st['P'][acode]
    return poss * (eh - ea) / 100, poss * (eh + ea) / 100, poss

state, CTX = build(dict(ENG_SPREAD, experts=True))   # χαντικαπ/1-2 ΜΕ ειδικους (+ ratings στον πινακα)
_, CTX_V1 = build(ENG_SPREAD)                        # χαντικαπ/1-2 χωρις ειδικους (συγκριση)
_, CTX_T = build(ENG_TOTAL)             # συνολο ποντων
d0date = D.date.iloc[0]
today_cut = (dt.date.today() - d0date).days + 1
GNO, _cnt = {}, {}                      # αριθμος αγωνα της σεζον (max των δυο ομαδων) — οπως στο τεστ της καμπυλης
for y in sorted(S[SEASON], key=lambda y: y['utc']):
    if y['phase'] != 'RS': continue
    for t in (y['hcode'], y['acode']): _cnt[t] = _cnt.get(t, 0) + 1
    GNO[y['code']] = max(_cnt[y['hcode']], _cnt[y['acode']])
GMAX = max(GNO.values()) if GNO else 34
games = []
for x in sorted(S[SEASON], key=lambda y: y['utc']):
    hcode, acode = x['hcode'], x['acode']
    if hcode not in CTX['ix'] or acode not in CTX['ix']: continue
    gdate = pd.Timestamp(x['utc']).date()
    played = bool(x['played']) and x.get('hs') is not None
    cut = (gdate - d0date).days if played or gdate <= dt.date.today() else today_cut
    neu = is_neutral(x)
    mg, tt1, poss = predict(state_at(CTX, cut), hcode, acode, neu, ENG_SPREAD['h'])
    mg1, tt1, _ = predict(state_at(CTX_V1, cut), hcode, acode, neu, ENG_SPREAD['h'])
    _, tt, _ = predict(state_at(CTX_T, cut), hcode, acode, neu, ENG_TOTAL['h'])
    tt += CURVE_A + CURVE_B * GNO.get(x['code'], GMAX)
    rec = dict(code=x['code'], round=x['rnd'], phase=x['phase'], utc=x['utc'], home=x['home'], away=x['away'], hcode=hcode, acode=acode,
               venue=x.get('vname'), neutral=neu, pts_h=round((tt + mg) / 2, 1), pts_a=round((tt - mg) / 2, 1),
               margin=round(mg, 2), total=round(tt, 1), poss=round(poss, 1), p_home=round(Phi(mg / SIGMA_MARGIN), 3),
               played=played, version='v3', hcrest=x.get('hcrest'), acrest=x.get('acrest'),
               versions={'v1': dict(pts_h=round((tt1 + mg1) / 2, 1), pts_a=round((tt1 - mg1) / 2, 1), margin=round(mg1, 2), total=round(tt1, 1),
                                    p_home=round(Phi(mg1 / SIGMA_MARGIN), 3))})
    if played:
        rec.update(hs=x['hs'], as_=x['as_'])
    games.append(rec)
names = {}
for L in S.values():
    for x in L: names[x['hcode']] = x['home']
ratings = sorted([dict(code=t, name=names.get(t, t), O=round(state['O'][t], 2), D=round(state['D'][t], 2), net=round(state['O'][t] - state['D'][t], 2),
                       pace=round(state['P'][t], 2), games=state['n'][t]) for t in state['O']], key=lambda r: -r['net'])
json.dump(dict(generated=dt.datetime.now(dt.timezone.utc).isoformat(timespec='minutes'), season=SEASON,
               model='v3: χαντικαπ/1-2 = v1 + ΕΙΔΙΚΟΙ αρχης σεζον (0.32 ομαδα + 0.42 BasketNews) (HL120, λ8, εδρα 6/100, τυχη 3P/FT 50%) · συνολο = v2 (τυχη 25%, χωρις φθορα, επιπεδο λιγκας σταθερο) + καμπυλη σεζον 0.34+0.098×αγων (με παρατασεις) · νεες ομαδες κατω απο μεση · ουδετερο εκτος πολης',
               sigma_margin=SIGMA_MARGIN, sigma_total=SIGMA_TOTAL, mu=round(state['mu'], 2), pace=round(state['pm'], 2),
               games=games, ratings=ratings), open('el_projections.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'el_projections.json: {len(games)} ματς ({sum(g["played"] for g in games)} παιγμενα, με προβλεψη «πριν το ματς») · ratings {len(ratings)} ομαδων')
for gm in games[:10]:
    print(f"  {gm['utc'][:16]} {gm['home'][:22]:22s} - {gm['away'][:22]:22s} {gm['pts_h']:5.1f}-{gm['pts_a']:5.1f} · γραμμη γηπ {-gm['margin']:+5.1f} · συνολο {gm['total']:5.1f}{' [ουδετερο]' if gm['neutral'] else ''}")
