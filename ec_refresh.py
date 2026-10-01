# -*- coding: utf-8 -*-
"""ec_refresh.py — ΚΑΘΗΜΕΡΙΝΗ ενημερωση EuroCup: προγραμμα + box scores + προβλεψεις (1/10/2026, Στελιος «περνα τη ρυθμιση, ολες
τις ενεργειες για live»). Ιδια μηχανη με τα τεστ (ec_model_test → ec_contrib_test → ec_expert_test → ec_carry_test):
  κατοχες/αποδοτικοτητα, «τυχη» L (3P/FT μισο-δρομο προς περσινο μεσο), HL 9999, λ 4, εδρα 5/100,
  ΑΦΕΤΗΡΙΑ = 0.2 × περσινο EuroCup (νεες 0) + ειδικοι 4·z (Eurohoops + Taking The Charge + αποδοσεις νικητη) + προετοιμασια 0.5·r
  (ec_prior.json ← ec_prior_build.py), + ΦΕΤΙΝΑ ΕΓΧΩΡΙΑ κ 1 απο τον 1ο αγωνα (el_domestic_live: bk_domestic + fs_bk_extra).
  Walk-forward: καθε ματς προβλεπεται με οτι ηταν γνωστο ΠΡΙΝ απο τη μερα του.
ΜΟΝΟ χαντικαπ για picks (τα συνολα EuroCup δεν εχουν τεσταριστει — εμφανιζονται, δεν παιζονται).
Εξοδος: ec_sched.json · ec_box.json · ec_projections.json (ιδια μορφη με el_projections.json)."""
import sys, os, json, math, time, datetime as dt, urllib.request, urllib.error
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
from el_season import Y as _Y
SEASON = f'U{_Y}'
HL, LAM, H, VAR = 9999, 4, 5.0, 'L'
SIGMA_MARGIN, SIGMA_TOTAL = 11.5, 16.7
PRIOR_F = os.environ.get('EC_PRIOR_F', 'ec_prior.json')           # (εναλλακτικο αρχειο μονο για δοκιμες)
PROJ_OUT = os.environ.get('EC_PROJ_F', 'ec_projections.json')
PRIOR = json.load(open(PRIOR_F, encoding='utf-8')) if os.path.exists(PRIOR_F) else {}
if PRIOR.get('season') != SEASON:
    print(f'ΠΡΟΣΟΧΗ: ec_prior.json ειναι για {PRIOR.get("season")} — αφετηρια χωρις ειδικους/προετοιμασια (τρεξε ec_prior_build.py)'); PRIOR = {}
CARRY, KX, KP = PRIOR.get('carry', 0.2), PRIOR.get('kx', 4.0), PRIOR.get('kp', 0.5)
KD = 1.0
DOM_NAME = {'BCR': 'BC Roma SPQR'}       # Roma Basketball (δυο ομαδες Ρωμης στη Lega A: «Maxima Roma» ≠ «BC Roma SPQR»)
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
S = json.load(open('ec_sched.json', encoding='utf-8')) if os.path.exists('ec_sched.json') else {}
g = J(f'https://api-live.euroleague.net/v2/competitions/U/seasons/{SEASON}/games')
if g and g.get('data'):
    S[SEASON] = [dict(code=x['gameCode'], phase=x['phaseType']['code'], rnd=x['round'], utc=x['utcDate'], played=x.get('played'),
                      neutral=x.get('isNeutralVenue'), group=((x.get('group') or {}).get('rawName')),
                      venue=(x.get('venue') or {}).get('code'), vname=(x.get('venue') or {}).get('name'),
                      hcode=x['local']['club']['code'], acode=x['road']['club']['code'],
                      home=x['local']['club']['name'], away=x['road']['club']['name'], hs=x['local']['score'], as_=x['road']['score'],
                      hcrest=((x['local']['club'].get('images') or {}).get('crest')), acrest=((x['road']['club'].get('images') or {}).get('crest')))
                 for x in g['data']]
    json.dump(S, open('ec_sched.json', 'w', encoding='utf-8'), ensure_ascii=False)
print(f'{SEASON}: {len(S.get(SEASON, []))} ματς · παιχτηκαν {sum(1 for x in S.get(SEASON, []) if x["played"])}')

# ---- 2. box scores ----
B = json.load(open('ec_box.json', encoding='utf-8'))
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
json.dump(B, open('ec_box.json', 'w', encoding='utf-8'), ensure_ascii=False)
print(f'νεα box scores: {n_new}')

# ---- 3. μηχανη (ιδια με τα τεστ EuroCup) ----
src = open('el_model_test.py', encoding='utf-8').read().split('# ---------------- ρυθμιση (χωρις αποδοσεις) ----------------')[0]
src = src.replace("B = json.load(open('el_box.json', encoding='utf-8'))", "B = json.load(open('ec_box.json', encoding='utf-8'))")
src = src.replace("sys.stdout.reconfigure(encoding='utf-8')", '').replace("open('el_model_test_out.txt', 'w'", "open('_unused_ecr.txt', 'w'")
ns = {}
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    exec(src, ns)
D, fit_eff, fit_pace, points = ns['D'], ns['fit_eff'], ns['fit_pace'], ns['points']
SEAS = sorted(set(D.season) | {SEASON})
ph_, pa_ = points(D, VAR); EH, EA = 100 * ph_ / D.poss.values, 100 * pa_ / D.poss.values
d0date = D.date.iloc[0]
dnum = np.array([(d - d0date).days for d in D.date])
today_cut = (dt.date.today() - d0date).days + 1
# φετινα εγχωρια (κ 1, απο τον 1ο αγωνα): Nowgoal 10 λιγκες + Flashscore 6 (Πολωνια, Ρουμανια, Αγγλια, BNXT, Λετονια-Εσθονια, Ουκρανια)
DOMSHIFT = None
try:
    import el_domestic_live
    XT = json.load(open('fs_bk_extra.json', encoding='utf-8')); XID, extra = {}, {}
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
        if games or y == _Y: extra[kk] = dict(teams=teams, games=games)
    _ect = {}
    for x in S.get(SEASON, []): _ect[x['hcode']] = x['home']; _ect[x['acode']] = x['away']
    _ect.update({c: n for c, n in DOM_NAME.items() if c in _ect})       # ονομα στο εγχωριο οπου οι λεξεις δεν αρκουν
    DOMSHIFT, _dinfo, _ddelta = el_domestic_live.build_shifts(_ect, d0date, extra=extra, kappa=KD)
    print('φετινα εγχωρια: ' + ' · '.join(f'{c} {_ddelta(c, today_cut):+.1f}' for c in sorted(_dinfo)) + f' (αντιστοιχισμενες {len(_dinfo)}/{len(_ect)})')
    _miss = sorted(set(_ect) - set(_dinfo))
    if _miss: print('  χωρις εγχωρια ομαδα:', _miss)
except Exception as _e:
    print('ΠΡΟΣΟΧΗ: φετινα εγχωρια απενεργα —', _e); DOMSHIFT = None

# ιστορικες σεζον: ιδια αλυσιδα με το τεστ (ec_carry_test): carry + ειδικοι (καταταξεις + αποδοσεις νικητη οπου υπαρχουν) — ετσι
# το περσινο τελος που «μεταφερεται» ειναι ιδιο με του τεστ (η προετοιμασια των παλιων σεζον παραλειπεται: μικρη επιδραση στο τελος σεζον)
from statistics import NormalDist as _ND
ZH = {}
try:
    _EX = json.load(open('ec_expert.json', encoding='utf-8')); _OR = json.load(open('ec_outrights.json', encoding='utf-8'))
    for _S, _tm in _EX.items():
        _od = {c: d['odds'] for c, d in _tm.items() if 'odds' in d}
        _uo = _S in _OR and _OR[_S].get('after_round', 0) <= 1 and len(_od) >= 0.8 * len(_tm)
        if _uo:
            _lv = {c: -math.log(o) for c, o in _od.items()}; _m, _s = np.mean(list(_lv.values())), np.std(list(_lv.values()))
        for c, d in _tm.items():
            zz = [_ND().inv_cdf(1 - (d[k] - .5) / d[k + '_n']) for k in ('EH', 'TTC') if k in d] + ([(_lv[c] - _m) / _s] if _uo and c in _lv else [])
            if zz: ZH[(_S, c)] = float(np.mean(zz))
except Exception as _e:
    print('ΠΡΟΣΟΧΗ: ιστορικοι ειδικοι απενεργοι —', _e)
def build():
    prior = {}; mu0 = float((EH.mean() + EA.mean()) / 2); pm0 = float(D.pace.mean()); CTX = None
    for s in SEAS:
        sidx = np.where(D.season.values == s)[0]
        teams = sorted(set(D.home.values[sidx]) | set(D.away.values[sidx]) | ({x['hcode'] for x in S[s]} | {x['acode'] for x in S[s]} if s == SEASON else set()))
        ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        cr = CARRY
        if s == SEASON and PRIOR:
            ex = np.array([(KX * PRIOR['z'].get(t, 0.0) + KP * PRIOR['pre'].get(t, 0.0)) * 100 / 72 for t in teams])
        else:
            ex = np.array([KX * ZH.get((s, t), 0.0) * 100 / 72 for t in teams])
        o0 = np.array([cr * prior.get(t, (0, 0, 0))[0] for t in teams]) + ex / 2
        d0 = np.array([cr * prior.get(t, (0, 0, 0))[1] for t in teams]) - ex / 2
        p0 = np.array([cr * prior.get(t, (0, 0, 0))[2] for t in teams])
        hi = np.array([ix[t] for t in D.home.values[sidx]], int); ai = np.array([ix[t] for t in D.away.values[sidx]], int)
        hb = np.where(D.neutral.values[sidx] == 1, 0.0, H / 2)
        if s == SEASON:
            CTX = dict(ix=ix, n=n, tl=teams, o0=o0, d0=d0, p0=p0, mu0=mu0, pm0=pm0, sidx=sidx, hi=hi, ai=ai, hb=hb, dn=dnum[sidx], cache={},
                       prev={t: prior.get(t) for t in teams})
        elif len(sidx):
            w = np.ones(len(sidx))
            mu, O, Dd = fit_eff(hi, ai, EH[sidx], EA[sidx], hb, w, n, o0, d0, LAM, mu0)
            pm, Pc = fit_pace(hi, ai, D.pace.values[sidx], w, n, p0, LAM, pm0)
            prior = {t: (O[i], Dd[i], Pc[i]) for t, i in ix.items()}; mu0 = mu; pm0 = pm
    return CTX
CTX = build()
def state_at(c, cut):
    if cut in c['cache']: return c['cache'][cut]
    o0, d0 = c['o0'], c['d0']
    if DOMSHIFT:
        sh = np.array([DOMSHIFT(t, cut) for t in c['tl']]); o0 = o0 + sh / 2; d0 = d0 - sh / 2
    past = c['dn'] < cut if len(c['dn']) else np.array([], bool)
    if past.any():
        w = 0.5 ** ((cut - c['dn'][past]) / HL); sid = c['sidx'][past]
        mu, O, Dd = fit_eff(c['hi'][past], c['ai'][past], EH[sid], EA[sid], c['hb'][past], w, c['n'], o0, d0, LAM, c['mu0'])
        pm, Pc = fit_pace(c['hi'][past], c['ai'][past], D.pace.values[sid], w, c['n'], c['p0'], LAM, c['pm0'])
    else:
        mu, O, Dd, pm, Pc = c['mu0'], o0, d0, c['pm0'], c['p0']
    st = dict(mu=mu, pm=pm, O={t: O[i] for t, i in c['ix'].items()}, D={t: Dd[i] for t, i in c['ix'].items()}, P={t: Pc[i] for t, i in c['ix'].items()})
    c['cache'][cut] = st; return st
def predict(st, h, a, neu):
    hb = 0 if neu else H / 2
    eh = st['mu'] + st['O'][h] + st['D'][a] + hb; ea = st['mu'] + st['O'][a] + st['D'][h] - hb
    poss = st['pm'] + st['P'][h] + st['P'][a]
    return poss * (eh - ea) / 100, poss * (eh + ea) / 100, poss
Phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))
games = []
for x in sorted(S[SEASON], key=lambda y: y['utc']):
    h, a = x['hcode'], x['acode']
    gdate = pd.Timestamp(x['utc']).date()
    played = bool(x['played']) and x.get('hs') is not None
    cut = (gdate - d0date).days if played or gdate <= dt.date.today() else today_cut
    neu = bool(x.get('neutral'))
    mg, tt, poss = predict(state_at(CTX, cut), h, a, neu)
    rec = dict(code=x['code'], round=x['rnd'], phase=x['phase'], group=x.get('group'), utc=x['utc'], home=x['home'], away=x['away'], hcode=h, acode=a,
               venue=x.get('vname'), neutral=neu, pts_h=round((tt + mg) / 2, 1), pts_a=round((tt - mg) / 2, 1), margin=round(mg, 2), total=round(tt, 1),
               poss=round(poss, 1), p_home=round(Phi(mg / SIGMA_MARGIN), 3), played=played, version='ec1', hcrest=x.get('hcrest'), acrest=x.get('acrest'))
    if played: rec.update(hs=x['hs'], as_=x['as_'])
    games.append(rec)
st = state_at(CTX, today_cut)
names = {}
for x in S[SEASON]: names[x['hcode']] = x['home']; names[x['acode']] = x['away']
ngm = {t: int(((D.season == SEASON) & ((D.home == t) | (D.away == t))).sum()) for t in CTX['tl']}
ratings = sorted([dict(code=t, name=names.get(t, t), O=round(st['O'][t], 2), D=round(st['D'][t], 2), net=round(st['O'][t] - st['D'][t], 2),
                       pace=round(st['P'][t], 2), games=ngm[t], new=CTX['prev'].get(t) is None,
                       z=PRIOR.get('z', {}).get(t), pre=PRIOR.get('pre', {}).get(t)) for t in CTX['tl']], key=lambda r: -r['net'])
json.dump(dict(generated=dt.datetime.now(dt.timezone.utc).isoformat(timespec='minutes'), season=SEASON, comp='EuroCup',
               model=f'ec1: αφετηρια {CARRY:g}×περσινο EuroCup + ειδικοι {KX:g}·z (Eurohoops/Taking The Charge/αποδοσεις νικητη) + προετοιμασια {KP:g}·r · '
                     f'φετινα εγχωρια κ {KD:g} απο τον 1ο αγωνα · HL {HL} · λ {LAM} · εδρα {H:g}/100 · τυχη 3P/FT · μονο χαντικαπ για picks',
               sigma_margin=SIGMA_MARGIN, sigma_total=SIGMA_TOTAL, mu=round(st['mu'], 2), pace=round(st['pm'], 2), prior_src=PRIOR.get('src'),
               games=games, ratings=ratings), open(PROJ_OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'{PROJ_OUT}: {len(games)} ματς ({sum(g["played"] for g in games)} παιγμενα) · ratings {len(ratings)}')
for r in ratings[:6] + ratings[-3:]:
    print(f"  {r['code']} {r['name'][:28]:28s} net {r['net']:+5.1f}/100 · ματς {r['games']}{' · νεα' if r['new'] else ''}")
for gm in [g_ for g_ in games if not g_['played']][:8]:
    print(f"  {gm['utc'][:16]} {gm['home'][:24]:24s} - {gm['away'][:24]:24s} γραμμη γηπ {-gm['margin']:+5.1f} · συνολο {gm['total']:5.1f}")
