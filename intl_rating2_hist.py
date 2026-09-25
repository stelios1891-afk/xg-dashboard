"""
intl_rating2_hist.py -- IDIO me to intl_rating2.py (H0-H4, edra), YVRIDIKO seed (diorthosi 25/9/2026, entoli syntonisti):
  (a) CAF omades (osec exoun >=1 mats prin tin 1/7/2019 sti vasi) -> seed eloratings.net telos 2010, walk-forward apo 2011.
  (b) OLES oi ypoloipes omades -> seed eloratings.net telos 2019 AKRIVOS opws to intl_rating2.py.
  Sta mats prin tin 1/7/2019: an kai oi dyo pleures einai mi-CAF -> to mats PARALEIPETAI entelws (den mpainei sto D/rows).
  an h mia pleura einai CAF kai i alli oxi -> ENIMERONETAI MONO i CAF pleura (i mi-CAF menei "pagomeni" sto seed 2019 tis).
  an kai oi dyo CAF -> enimerononte kanonika (opws to hist-all-2010 treximo).
  Apo tin 1/7/2019 kai meta: OLA kanonika (kai oi dyo pleures enimerononte panta), akrivos opws to intl_rating2.py.
  Anaforas treximo me seed-2010-gia-oloys (proto peirama, elegxthike ostoso oti xalage tis mi-CAF UEFA/NL) swthike
  me suffix _hist_all2010 (intl_ratings_h_hist_all2010.csv, intl_preds_H_hist_all2010.csv, intl_hfa_config_hist_all2010.json,
  intl_rating2_hist_all2010_out.txt).
Antigrafo tou intl_rating2.py -- kamia alli allagi orismwn/parallagwn/HFA.
Exodos: intl_ratings_h.csv, intl_preds_H.csv, intl_hfa_config.json (IDIA ONOMATA -- ta arxika (2019-seed-gia-oloys, xoris istorika)
  swthikan _pre_hist prin apo auto).
"""

import sys, json, math
import numpy as np
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
_src = open('intl_rating.py', encoding='utf-8').read(); _ns = {'np': np, 'json': json, 'math': math}
exec(_src[_src.index('def exp_score'):_src.index('# «as» ειναι')], _ns)            # exp_score, margin_mult, adj_xg
exec(_src[_src.index('def sig(x):'):_src.index("EVAL_SEASONS = ")], _ns)
exp_score, margin_mult, adj_xg, fit_ol, probs, rps = _ns['exp_score'], _ns['margin_mult'], _ns['adj_xg'], _ns['fit_ol'], _ns['probs'], _ns['rps']
_ns2 = {}
exec(_src[:_src.index('# ---------- Poisson')].replace("sys.stdout.reconfigure(encoding='utf-8')", ''), _ns2)   # SEED κλπ
K_TYPE, FAV_D, CAP = _ns2['K_TYPE'], _ns2['FAV_D'], _ns2['CAP']
SEED2019 = _ns2['SEED']                       # eloratings.net telos 2019 (idio me intl_rating2.py)
SEED2010 = _ns2['seed_year']('2010')          # eloratings.net telos 2010 (gia CAF walk-forward)
print(f'SEED2019: {len(SEED2019)} omades · SEED2010: {len(SEED2010)} omades')
_ns['GS'] = _ns2['GS']; _ns['CAP'] = CAP

M = pd.read_csv('intl_matches.csv', dtype={'season': str, 'mid': str}, parse_dates=['date']).sort_values('date').reset_index(drop=True)
import intl_dedupe
M = intl_dedupe.dedupe(M, where='intl_rating2_hist').sort_values('date').reset_index(drop=True)   # 25/9: κλειδι ασφαλειας — διπλα ματς δεν μετρανε
M = M[M['date'] >= '2011-01-01'].reset_index(drop=True).rename(columns={'as': 'ag'})
F = pd.read_csv('intl_venue_flags.csv', dtype={'mid': str}).set_index('mid')
F = intl_dedupe.unique_mid(F, where='intl_rating2_hist: intl_venue_flags', on_index=True)   # 25/9 (β): ενα ματς = μια γραμμη
M = M.join(F, on='mid')
intl_dedupe.assert_unique_mid(M, where='intl_rating2_hist μετα το join')   # 25/9 (β): το join δεν πολλαπλασιαζει ματς
M['old_home'] = (~M.neutral.astype(bool)).astype(int)
M['hsign'] = np.where(M.home_true.notna(), M.home_true.fillna(0) - M.away_at_home.fillna(0), M.old_home)
CONF = {'UEFA': ['NationsLeagueA', 'NationsLeagueB', 'NationsLeagueC', 'NationsLeagueD', 'WCQ_UEFA', 'EUROQ', 'EURO'],
        'CONMEBOL': ['WCQ_CONMEBOL', 'CopaAmerica'], 'CAF': ['WCQ_CAF', 'AFCON'], 'AFC': ['WCQ_AFC', 'AsianCup'], 'CONCACAF': ['WCQ_CONCACAF', 'GoldCup']}
HFA_CONF = {'UEFA': 80, 'CONMEBOL': 120, 'CAF': 80, 'AFC': 65, 'CONCACAF': 60}
comp2conf = {c: k for k, v in CONF.items() for c in v}
M['conf'] = M.comp.map(comp2conf).fillna('OTHER')
ALT = 110
# «συνηθες» υψομετρο εδρας ομαδας: διαμεσος υψομετρου των ματς στη χωρα της (ολο το δειγμα — σταθερο χαρακτηριστικο, οχι αποτελεσμα)
home_elev = M[(M.home_true == 1) & M.elev.notna()].groupby('hid').elev.median().to_dict()

# ---- YVRIDIKO seed: CAF omades (>=1 mats prin tin 1/7/2019) -> 2010 · oloi oi alloi -> 2019 ----
import glob as _glob
CUTOFF = pd.Timestamp('2020-01-01')   # 25/9 (Στελιος): μη-CAF ενημερωνονται ΑΚΡΙΒΩΣ μετα την αφετηρια eloratings τελος 2019 (ηταν 1/7/2019 → 6 μηνες διπλα)
assert CUTOFF == pd.Timestamp('2020-01-01'), 'μη-CAF: η αφετηρια ειναι τελος 2019 -> ενημερωσεις απο 1/1/2020'
assert M.date.min() >= pd.Timestamp('2011-01-01'), 'CAF: αφετηρια τελος 2010 -> κανενα ματς πριν την 1/1/2011'
_CAF_NAMES = set()
for _f in _glob.glob('data_AFCON*.json') + _glob.glob('data_WCQ_CAF*.json'):
    _d = json.load(open(_f, encoding='utf-8'))
    for _m in _d.values():
        _CAF_NAMES.add(_m['home']['name']); _CAF_NAMES.add(_m['away']['name'])
_early = M[M.date < CUTOFF]
_caf_candidates = set(M[M.hn.isin(_CAF_NAMES)].hid) | set(M[M.an.isin(_CAF_NAMES)].aid)
CAF_IDS = {tid for tid in _caf_candidates if ((_early.hid == tid) | (_early.aid == tid)).any()}
print(f'CAF omades (FotMob ids) me >=1 mats prin 1/7/2019: {len(CAF_IDS)}')
SEED = dict(SEED2019)
for _tid in CAF_IDS:
    if _tid in SEED2010:
        SEED[_tid] = SEED2010[_tid]
    else:
        SEED.pop(_tid, None)   # xoris 2010 seed -> xekina apo default 1500.0 (opws to hist_all2010 treximo)
print(f'SEED yvridiko: {len(SEED)} omades (CAF me 2010: {sum(1 for t in CAF_IDS if t in SEED2010)}/{len(CAF_IDS)})')


def run(mode):
    R = dict(SEED); rows = []
    scale = 1.0; raw = adj = 0.0
    for r in M[M.has_xg].itertuples():
        a, b = adj_xg(r.shots, 0, 'gs'); raw += r.xg_h + r.xg_a; adj += a + b
    scale = raw / adj
    res_h = {}; res_a = {}          # για H4: λιστες υπολοιπων εντος/εκτος ανα ομαδα (μονο παρελθον)
    for r in M.itertuples():
        is_early = r.date < CUTOFF
        h_caf = r.hid in CAF_IDS; a_caf = r.aid in CAF_IDS
        if is_early and not h_caf and not a_caf:
            continue                        # δυο μη-CAF πριν 1/7/2019 -> εκτος δικου μας ελεγχου, παραλειπεται εντελως
        update_h = (not is_early) or h_caf  # μη-CAF παγωμενη πριν 1/7/2019 (χρησιμοποιειται σαν αντιπαλος, δεν ενημερωνεται)
        update_a = (not is_early) or a_caf
        rh = R.get(r.hid, 1500.0); ra = R.get(r.aid, 1500.0)
        if mode == 'H0':
            h = 80 * r.old_home
        else:
            base = 80 if mode == 'H1' else HFA_CONF.get(r.conf, 80)
            h = base * r.hsign
            if mode in ('H3', 'H4') and r.hsign == 1 and pd.notna(r.elev) and r.elev >= 1500 and home_elev.get(r.aid, 0) < 1000:
                h += ALT
            if mode == 'H4':
                def team_h(tid):
                    lh = res_h.get(tid, []); la = res_a.get(tid, [])
                    if len(lh) < 3 or len(la) < 3:
                        return 0.0
                    est = (np.mean(lh) - np.mean(la)) / 2; n = min(len(lh), len(la))
                    return est * n / (n + 10)
                if r.hsign == 1:
                    h += max(min(team_h(r.hid) / 0.0049, 150), -150)
                elif r.hsign == -1:
                    h -= max(min(team_h(r.aid) / 0.0049, 150), -150)
        d = rh + h - ra
        E = 1 / (1 + 10 ** (-d / 400)); gd = int(r.hs) - int(r.ag)
        rows.append(dict(mid=r.mid, date=r.date, season=r.season, ctype=r.ctype, comp=r.comp, hid=r.hid, aid=r.aid, diff=d, gd=gd))
        # ενημερωση H4 υπολοιπων (μετα την προβλεψη: μονο παρελθον)
        if mode == 'H4':
            d0 = rh - ra; resid = gd - 0.0049 * d0
            if r.hsign == 1:
                if update_h: res_h.setdefault(r.hid, []).append(resid)
                if update_a: res_a.setdefault(r.aid, []).append(-resid)
            elif r.hsign == -1:
                if update_a: res_h.setdefault(r.aid, []).append(-resid)
                if update_h: res_a.setdefault(r.hid, []).append(resid)
        # Elo + xElo (B): μεσος των δυο ενημερωσεων (ιδιο με E0 και X3 ξεχωριστα, blend στο diff — εδω απλοποιηση: ενημερωση με S = 0.5*S_res + 0.5*S_x)
        S_res = 1.0 if gd > 0 else (0.5 if gd == 0 else 0.0)
        if r.has_xg:
            fav = 1 if d >= FAV_D else (-1 if d <= -FAV_D else 0)
            xh, xa = adj_xg(r.shots, fav, 'gs'); xh *= scale; xa *= scale
            S = 0.5 * S_res + 0.5 * exp_score(xh, xa); mm = margin_mult(round(0.5 * gd + 0.5 * (xh - xa)))
        else:
            S = S_res; mm = margin_mult(gd)
        K = K_TYPE.get(r.ctype, 30) * mm
        if update_h: R[r.hid] = rh + K * (S - E)
        if update_a: R[r.aid] = ra - K * (S - E)
    return pd.DataFrame(rows), R


SEAS = ['2021', '2122', '2223', '2324', '2425', '2526']
table = []; preds = {}
for mode in ['H0', 'H1', 'H2', 'H3', 'H4']:
    D, R = run(mode); D['y'] = np.where(D.gd > 0, 2, np.where(D.gd == 0, 1, 0)); preds[mode] = (D, R)
    C = D[D.ctype.isin(['nl', 'qual', 'tourn'])]
    row = dict(variant=mode); allP = []; ally = []
    for s in SEAS:
        tr = C[(C.season != s)]; te = C[C.season == s]
        p = fit_ol(tr['diff'].values, tr['y'].values); Pm = probs(te['diff'].values, p)
        row[s] = round(rps(Pm, te['y'].values), 4); allP.append(Pm); ally.append(te['y'].values)
    row['ALL'] = round(rps(np.vstack(allP), np.concatenate(ally)), 4); row['n'] = len(C)
    # ανα ομοσπονδια (ALL)
    for k in ['UEFA', 'CONMEBOL', 'CAF', 'AFC']:
        sub = C[C.comp.isin(CONF[k])]; allP = []; ally = []
        for s in SEAS:
            tr = C[C.season != s]; te = sub[sub.season == s]
            if len(te) < 15:
                continue
            p = fit_ol(tr['diff'].values, tr['y'].values); allP.append(probs(te['diff'].values, p)); ally.append(te['y'].values)
        row[k] = round(rps(np.vstack(allP), np.concatenate(ally)), 4) if allP else np.nan
    table.append(row)
T = pd.DataFrame(table).set_index('variant'); pd.set_option('display.width', 220)
print('=== RPS LOSO (αγωνιστικα) — παραλλαγες εδρας πανω στο B (Elo+xElo ενιαιο) — YVRIDIKO seed (CAF 2010 / mi-CAF 2019)')
print(T.to_string())
base = T.loc['H0']
for v in T.index[1:]:
    better = sum(1 for s in SEAS if T.loc[v, s] < base[s])
    print(f'  {v}: ΔRPS {T.loc[v, "ALL"] - base["ALL"]:+.4f} · καλυτερο σε {better}/6 σεζον · {"ΠΕΡΝΑ" if (T.loc[v, "ALL"] < base["ALL"] and better >= 4) else "—"}')
# τρεχοντα ratings της καλυτερης (ή H3) για τις προβολες
best = min(T.index[1:], key=lambda v: T.loc[v, 'ALL'])
# 25/9/2026: στο αυτοματο refresh (intl_refresh.py) το Μοντελο 1 ΚΛΕΙΔΩΝΕΙ στο H3 (η επιλογη του Στελιου)· αν τα νεα δεδομενα
# προτιμουν αλλη παραλλαγη, απλως προειδοποιει — καμια σιωπηλη αλλαγη μοντελου.
import os as _os
if _os.environ.get('INTL_PIN_VARIANT'):
    if best != _os.environ['INTL_PIN_VARIANT']:
        print(f"ΠΡΟΕΙΔΟΠΟΙΗΣΗ: τα δεδομενα προτιμουν {best} (RPS {T.loc[best, 'ALL']}) αντι για {_os.environ['INTL_PIN_VARIANT']} (RPS {T.loc[_os.environ['INTL_PIN_VARIANT'], 'ALL']}) — μενει {_os.environ['INTL_PIN_VARIANT']}")
    best = _os.environ['INTL_PIN_VARIANT']
D, R = preds[best]
names = {}
for r in M.itertuples():
    names[r.hid] = r.hn; names[r.aid] = r.an
L = pd.Series(R, name='R').to_frame(); L['name'] = L.index.map(names)
last = M.groupby('hid')['date'].max().combine(M.groupby('aid')['date'].max(), max)
L['last_match'] = L.index.map(last); L = L[L['last_match'] >= '2025-01-01'].sort_values('R', ascending=False)
L.to_csv('intl_ratings_h.csv'); D.to_csv('intl_preds_H.csv', index=False)
json.dump(dict(variant=best, hfa_conf=HFA_CONF, alt=ALT, home_elev={str(k): v for k, v in home_elev.items()}), open('intl_hfa_config.json', 'w', encoding='utf-8'))
print(f'\nκαλυτερη παραλλαγη: {best} -> intl_ratings_h.csv, intl_preds_H.csv, intl_hfa_config.json')
print(L.head(12)[['name', 'R']].round(0).to_string())
