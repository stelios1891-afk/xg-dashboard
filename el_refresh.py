# -*- coding: utf-8 -*-
"""el_refresh.py — ΚΑΘΗΜΕΡΙΝΗ ενημερωση Ευρωλιγκας: νεα ματς + προβλεψεις (25/9/2026).
 1. προγραμμα τρεχουσας σεζον (επισημο API) -> el_sched.json[SEASON]
 2. box score για οσα ματς της σεζον παιχτηκαν και λειπουν -> el_box.json
 3. μοντελο v1 (παγωμενο απο el_model_test: HL=120, λ=8, carry=0.7, εδρα 6/100, παραλλαγη L) μεχρι σημερα,
    + δυο κανονες που συμφωνηθηκαν 25/9: (α) νεες ομαδες ξεκινουν κατω απο τη μεση (NEWCOMER_PRIOR),
    (β) «εντος» ματς >300 χλμ απο το πραγματικο σπιτι της ομαδας = ουδετερο (ισραηλινες σε Βελιγραδι/Σοφια κτλ).
 4. -> el_projections.json (επερχομενα ματς: ποντοι, διαφορα, συνολο, πιθανοτητα νικης· ratings ομαδων)
Τρεχει τοπικα ή στο GitHub (χωρις κλειδια)."""
import sys, os, json, math, time, datetime as dt, urllib.request, urllib.error
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
SEASON = 'E2026'
HL, LAM, CARRY, H = 120, 8, 0.7, 6
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

ph, pa = points(D, 'L'); EH = 100 * ph / D.poss.values; EA = 100 * pa / D.poss.values
dnum = np.array([(d - D.date.iloc[0]).days for d in D.date])
prior = {}; mu0 = float((EH.mean() + EA.mean()) / 2); pm0 = float(D.pace.mean())
seasons = sorted(set(D.season) | {SEASON})
state = None
for s in seasons:
    sidx = np.where(D.season.values == s)[0]
    teams = sorted(set(D.home.values[sidx]) | set(D.away.values[sidx]) | ({x['hcode'] for x in S[s]} if s == SEASON else set()))
    ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
    pr = {t: NEWCOMER_PRIOR[t] if (s == SEASON and t in NEWCOMER_PRIOR and t not in prior) else tuple(CARRY * v for v in prior.get(t, (0, 0, 0))) for t in teams}
    o0 = np.array([pr[t][0] for t in teams]); d0 = np.array([pr[t][1] for t in teams]); p0 = np.array([pr[t][2] for t in teams])
    if len(sidx):
        neu = np.array([is_neutral(sd) for sd in [next((y for y in S[s] if f"{s}_{y['code']}" == k), {'phase': ph_, 'hcode': h_}) for k, ph_, h_ in zip(D.key.values[sidx], D.phase.values[sidx], D.home.values[sidx])]])
        hi = np.array([ix[t] for t in D.home.values[sidx]]); ai = np.array([ix[t] for t in D.away.values[sidx]])
        hb = np.where(neu, 0.0, H / 2); dn = dnum[sidx]
        ref = (dt.date.today() - D.date.iloc[0]).days if s == SEASON else dn.max()
        w = 0.5 ** ((ref - dn) / HL)
        mu, O, Dd = fit_eff(hi, ai, EH[sidx], EA[sidx], hb, w, n, o0, d0, LAM, mu0)
        pm, Pc = fit_pace(hi, ai, D.pace.values[sidx], w, n, p0, LAM, pm0)
    else:
        mu, O, Dd, pm, Pc = mu0, o0, d0, pm0, p0
    if s == SEASON:
        state = dict(mu=mu, pm=pm, O={t: O[i] for t, i in ix.items()}, D={t: Dd[i] for t, i in ix.items()}, P={t: Pc[i] for t, i in ix.items()},
                     n={t: int(((D.season == s) & ((D.home == t) | (D.away == t))).sum()) for t in teams})
        CTX = dict(ix=ix, n=n, o0=o0, d0=d0, p0=p0, mu0=mu0, pm0=pm0, sidx=sidx,
                   hi=hi if len(sidx) else None, ai=ai if len(sidx) else None, hb=hb if len(sidx) else None, dn=dnum[sidx])
    else:
        prior = {t: (O[i], Dd[i], Pc[i]) for t, i in ix.items()}; mu0 = mu; pm0 = pm

# ---- 4. προβλεψεις: ΚΑΙ για τα παιγμενα ματς (με οτι ηξερε το μοντελο ΠΡΙΝ απο το ματς) ----
Phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))
_cache = {}
def state_at(cut):
    """ratings με ματς της σεζον ΑΥΣΤΗΡΑ πριν απο τη μερα cut (walk-forward, χωρις να ξερει το αποτελεσμα)."""
    if cut in _cache: return _cache[cut]
    c = CTX; ix = c['ix']
    past = (c['dn'] < cut) if c['hi'] is not None else np.array([], bool)
    if past.any():
        w = 0.5 ** ((cut - c['dn'][past]) / HL); sid = c['sidx'][past]
        mu, O, Dd = fit_eff(c['hi'][past], c['ai'][past], EH[sid], EA[sid], c['hb'][past], w, c['n'], c['o0'], c['d0'], LAM, c['mu0'])
        pm, Pc = fit_pace(c['hi'][past], c['ai'][past], D.pace.values[sid], w, c['n'], c['p0'], LAM, c['pm0'])
    else:
        mu, O, Dd, pm, Pc = c['mu0'], c['o0'], c['d0'], c['pm0'], c['p0']
    st = dict(mu=mu, pm=pm, O={t: O[i] for t, i in ix.items()}, D={t: Dd[i] for t, i in ix.items()}, P={t: Pc[i] for t, i in ix.items()})
    _cache[cut] = st; return st
d0date = D.date.iloc[0]
today_cut = (dt.date.today() - d0date).days + 1
games = []
for x in sorted(S[SEASON], key=lambda y: y['utc']):
    hcode, acode = x['hcode'], x['acode']
    if hcode not in CTX['ix'] or acode not in CTX['ix']: continue
    gdate = pd.Timestamp(x['utc']).date()
    played = bool(x['played']) and x.get('hs') is not None
    st = state_at((gdate - d0date).days) if played or gdate <= dt.date.today() else state_at(today_cut)
    neu = is_neutral(x); hb = 0 if neu else H / 2
    eh = st['mu'] + st['O'][hcode] + st['D'][acode] + hb; ea = st['mu'] + st['O'][acode] + st['D'][hcode] - hb
    poss = st['pm'] + st['P'][hcode] + st['P'][acode]
    mg = poss * (eh - ea) / 100; tt = poss * (eh + ea) / 100
    rec = dict(code=x['code'], round=x['rnd'], phase=x['phase'], utc=x['utc'], home=x['home'], away=x['away'], hcode=hcode, acode=acode,
               venue=x.get('vname'), neutral=neu, pts_h=round(poss * eh / 100, 1), pts_a=round(poss * ea / 100, 1),
               margin=round(mg, 2), total=round(tt, 1), poss=round(poss, 1), p_home=round(Phi(mg / SIGMA_MARGIN), 3),
               played=played, version='v1', hcrest=x.get('hcrest'), acrest=x.get('acrest'))
    if played:
        rec.update(hs=x['hs'], as_=x['as_'])
    games.append(rec)
names = {}
for L in S.values():
    for x in L: names[x['hcode']] = x['home']
ratings = sorted([dict(code=t, name=names.get(t, t), O=round(state['O'][t], 2), D=round(state['D'][t], 2), net=round(state['O'][t] - state['D'][t], 2),
                       pace=round(state['P'][t], 2), games=state['n'][t]) for t in state['O']], key=lambda r: -r['net'])
json.dump(dict(generated=dt.datetime.now(dt.timezone.utc).isoformat(timespec='minutes'), season=SEASON,
               model='v1: ratings O/D/ρυθμος (HL120, λ8, carry0.7, εδρα 6/100, τυχη 3P/FT) + νεες ομαδες κατω απο μεση + ουδετερο εκτος πολης',
               sigma_margin=SIGMA_MARGIN, sigma_total=SIGMA_TOTAL, mu=round(state['mu'], 2), pace=round(state['pm'], 2),
               games=games, ratings=ratings), open('el_projections.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'el_projections.json: {len(games)} ματς ({sum(g["played"] for g in games)} παιγμενα, με προβλεψη «πριν το ματς») · ratings {len(ratings)} ομαδων')
for gm in games[:10]:
    print(f"  {gm['utc'][:16]} {gm['home'][:22]:22s} - {gm['away'][:22]:22s} {gm['pts_h']:5.1f}-{gm['pts_a']:5.1f} · γραμμη γηπ {-gm['margin']:+5.1f} · συνολο {gm['total']:5.1f}{' [ουδετερο]' if gm['neutral'] else ''}")
