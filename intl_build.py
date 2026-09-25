"""
intl_build.py — ΕΝΙΑΙΑ ΒΑΣΗ ΜΑΤΣ ΕΘΝΙΚΩΝ (19/9/2026) για Elo / xElo.
Πηγες:
  data_{comp}_{sea}.json (FotMob, σουτ+xG+σκορ)          -> ματς με xG (και σκορ)
  intl_results_scores.json (FotMob, σκορ-μονο)             -> NL 2018/19, EUROQ 2019, AFCON/AsianCup/GoldCup, WCQ AFC/CAF/CONCACAF
  intl_friendlies_ng.json (Nowgoal INT FRL c1366, σκορ)     -> φιλικα 2019-2026 (ονοματα -> FotMob ids με resolver)
  intl_squads.json (FotMob ενδεκαδες)                       -> αξια ενδεκαδας (mv) ανα πλευρα
Εξοδος: intl_matches.csv — ενα row ανα ματς: date, comp, ctype (friendly/nl/qual/tourn), hid, aid, hn, an, hs, as,
        has_xg, ανα πλευρα: xg_np (raw, χωρις πεναλτι), xg_c40 (συμπιεση cap 0.40), shots json για game-state,
        mv_h, mv_a (αξια ενδεκαδας), neutral, host.
Συμβαση σεζον: 'YY' = Ιουλ-Ιουν (π.χ. 2024-07-01..2025-06-30 -> '2425').
"""
import json, os, glob, re, sys
import pandas as pd
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
import picks

CTYPE = {'Friendlies': 'friendly', 'NationsLeagueA': 'nl', 'NationsLeagueB': 'nl', 'NationsLeagueC': 'nl', 'NationsLeagueD': 'nl',
         'WCQ_UEFA': 'qual', 'EUROQ': 'qual', 'WCQ_CONMEBOL': 'qual', 'WCQ_AFC': 'qual', 'WCQ_CAF': 'qual', 'WCQ_CONCACAF': 'qual',
         'EURO': 'tourn', 'WorldCup': 'tourn', 'CopaAmerica': 'tourn', 'AFCON': 'tourn', 'AsianCup': 'tourn', 'GoldCup': 'tourn', 'AFCONQ': 'qual'}
HOSTS = {('WorldCup', '2022'): {'Qatar'}, ('WorldCup', '2026'): {'USA', 'United States', 'Mexico', 'Canada'},
         ('EURO', '2024'): {'Germany'}, ('EURO', '2020'): set(),      # 2020: πολλαπλες εδρες -> ουδετερο (προσεγγιση)
         ('CopaAmerica', '2024'): {'USA', 'United States'}, ('AFCON', '2023'): {"Côte d'Ivoire", 'Ivory Coast'}, ('AFCON', '2025'): {'Morocco'},
         ('AsianCup', '2023'): {'Qatar'}, ('GoldCup', '2023'): {'USA', 'United States'}, ('GoldCup', '2025'): {'USA', 'United States'}}
CAP = 0.40


def parse_date(s):
    s = str(s)
    for fmt in ('%a, %b %d, %Y, %H:%M', '%Y-%m-%dT%H:%M'):
        try:
            return pd.to_datetime(s.replace(' UTC', '').replace('Z', '')[:16 if fmt.startswith('%Y') else None], format=fmt)
        except Exception:
            pass
    try:
        return pd.to_datetime(s)
    except Exception:
        return pd.NaT


def sea_of(dt):
    y = dt.year if dt.month >= 7 else dt.year - 1
    return f'{str(y)[2:]}{str(y + 1)[2:]}'


def comp_xg(shots):
    return sum(min(s, CAP) + max(s - CAP, 0) * 0.25 for s in shots)   # μαλακη συμπιεση πανω απο το cap


rows = []
squads = json.load(open('intl_squads.json', encoding='utf-8'))
seen = set()
# ---- 1. FotMob με σουτ ----
for f in sorted(glob.glob('data_*.json')):
    comp = re.match(r'data_([A-Za-z_]+?)_(\d{4})\.json$', os.path.basename(f))
    if not comp or comp.group(1) not in CTYPE:
        continue
    comp, sea = comp.group(1), comp.group(2)
    for mid, m in json.load(open(f, encoding='utf-8')).items():
        dt = parse_date(m.get('date'))
        if pd.isna(dt) or m.get('hs') is None:
            continue
        hid, aid = int(m['home']['id']), int(m['away']['id'])
        sh = m.get('shots') or []
        has_xg = bool(m.get('has_xg')) and any(s.get('xg') is not None for s in sh)
        xh = [float(s['xg']) for s in sh if s['tid'] == hid and s.get('sit') != 'Penalty' and s.get('xg') is not None]
        xa = [float(s['xg']) for s in sh if s['tid'] != hid and s.get('sit') != 'Penalty' and s.get('xg') is not None]
        sq = squads.get(str(mid), {})
        hosts = HOSTS.get((comp, sea), None)
        neutral = (CTYPE[comp] == 'tourn') and not (hosts and m['home']['name'] in hosts)
        rows.append(dict(mid=str(mid), src='fotmob', date=dt, season=sea_of(dt), comp=comp, ctype=CTYPE[comp],
                         hid=hid, aid=aid, hn=m['home']['name'], an=m['away']['name'], hs=int(m['hs']), **{'as': int(m['as'])},
                         has_xg=has_xg, xg_h=(sum(xh) if has_xg else np.nan), xg_a=(sum(xa) if has_xg else np.nan),
                         xgc_h=(comp_xg(xh) if has_xg else np.nan), xgc_a=(comp_xg(xa) if has_xg else np.nan),
                         mv_h=(sq.get('h') or {}).get('mv'), mv_a=(sq.get('a') or {}).get('mv'),
                         neutral=bool(neutral), reds=len(m.get('reds') or []),
                         shots=json.dumps([(int(s['tid'] == hid), s.get('min'), round(float(s['xg']), 4), int(bool(s.get('goal'))), s.get('sit') == 'Penalty')
                                           for s in sh if s.get('xg') is not None]) if has_xg else ''))
        seen.add(str(mid))
# ---- 2. FotMob σκορ-μονο ----
for mid, m in json.load(open('intl_results_scores.json', encoding='utf-8')).items():
    if mid in seen or m['comp'] not in CTYPE:
        continue
    dt = parse_date(m['utc'])
    if pd.isna(dt):
        continue
    hosts = HOSTS.get((m['comp'], m['sea']), None)
    neutral = (CTYPE[m['comp']] == 'tourn') and not (hosts and m['hname'] in hosts)
    rows.append(dict(mid=mid, src='fotmob_score', date=dt, season=sea_of(dt), comp=m['comp'], ctype=CTYPE[m['comp']],
                     hid=int(m['hid']), aid=int(m['aid']), hn=m['hname'], an=m['aname'], hs=m['hs'], **{'as': m['as']},
                     has_xg=False, xg_h=np.nan, xg_a=np.nan, xgc_h=np.nan, xgc_a=np.nan, mv_h=None, mv_a=None,
                     neutral=bool(neutral), reds=0, shots=''))
    seen.add(mid)
# ---- 3. Φιλικα Nowgoal -> FotMob ids ----
NAMES = json.load(open('intl_team_ids.json', encoding='utf-8'))
ALIAS = {'Turkey': 'Türkiye', 'Czech Republic': 'Czechia', 'Republic of Ireland': 'Ireland', 'United States': 'USA',
         'Democratic Rep Congo': 'DR Congo', 'St. Vincent Grenadines': 'Saint Vincent and The Grenadines',
         'Saint Kitts and Nevis': 'St. Kitts and Nevis', 'Brunei Darussalam': 'Brunei', 'Macedonia': 'North Macedonia',
         'Korea Republic': 'South Korea', 'Cabo Verde': 'Cape Verde', "Côte d'Ivoire": 'Ivory Coast', 'Curacao': 'Curaçao',
         'United Arab Emirates': 'UAE', 'Republic of the Congo': 'Congo', 'Bosnia-Herzegovina': 'Bosnia and Herzegovina'}
idx = {n: picks.norm(n) for n in NAMES}
BAD = re.compile(r'U-?\d\d|Women|\(W\)|\bW\b|Youth|Amateur|Reserve|Beta|Legends|All Star|XI\b', re.I)
_cache = {}


def resolve(n):
    if n in _cache:
        return _cache[n]
    if BAD.search(n):
        _cache[n] = None; return None
    for n2 in (n, ALIAS.get(n)):                 # πρωτα το αμεσο ονομα, μετα το alias
        if n2 and n2 in NAMES:
            _cache[n] = int(NAMES[n2]); return _cache[n]      # 25/9: ΑΚΕΡΑΙΟΣ (ηταν κειμενο → τα διπλα δεν πιανονταν)
    n2 = ALIAS.get(n, n)
    tn = picks.norm(n2); best = None; bs = 0; bj = 0
    for raw, tg in idx.items():
        ov = len(tn & tg)
        if ov and (ov > bs or (ov == bs and ov / len(tn | tg) > bj)):
            bs = ov; bj = ov / len(tn | tg); best = raw
    # απαιτουμε πληρη καλυψη των tokens του ονοματος (αλλιως 'Spain U21'->Spain κλπ)
    _cache[n] = int(NAMES[best]) if best and tn == idx[best] else None
    return _cache[n]


nf = 0; unres = {}
existing_pairs = {(r['hid'], r['aid'], r['date'].strftime('%Y-%m-%d')) for r in rows}
for ng, m in json.load(open('intl_friendlies_ng.json', encoding='utf-8')).items():
    h = resolve(m['home']); a = resolve(m['away'])
    if h is None or a is None:
        for nm, r in ((m['home'], h), (m['away'], a)):
            if r is None and not BAD.search(nm):
                unres[nm] = unres.get(nm, 0) + 1
        continue
    dt = parse_date(m['dt']) - pd.Timedelta(hours=8)          # Πεκινο -> UTC
    key = (h, a, dt.strftime('%Y-%m-%d'))
    if key in existing_pairs or (h, a, (dt + pd.Timedelta(days=1)).strftime('%Y-%m-%d')) in existing_pairs:
        continue
    rows.append(dict(mid=f'ng{ng}', src='nowgoal_friendly', date=dt, season=sea_of(dt), comp='Friendlies', ctype='friendly',
                     hid=h, aid=a, hn=m['home'], an=m['away'], hs=m['hs'], **{'as': m['as']}, has_xg=False,
                     xg_h=np.nan, xg_a=np.nan, xgc_h=np.nan, xgc_a=np.nan, mv_h=None, mv_a=None, neutral=False, reds=0, shots=''))
    nf += 1
M = pd.DataFrame(rows).sort_values('date').reset_index(drop=True)
# 22/9/2026: ΔΙΠΛΑ ματς (ιδιο FotMob mid σε δυο αρχεια φιλικων 2025/2026, ή ιδιο ζευγος-ημερα απο δυο πηγες) -> κρατα το πρωτο (FotMob πριν Nowgoal)
# 25/9/2026: ΚΛΕΙΔΙ ΑΣΦΑΛΕΙΑΣ (intl_dedupe): ιδιο ζευγος ομαδων (και ανεστραμμενο) μεσα σε 1 ημερα = ιδιο ματς· κρατα FotMob.
import intl_dedupe
_n0 = len(M)
M = intl_dedupe.dedupe(M, where='intl_build').sort_values('date').reset_index(drop=True)
intl_dedupe.assert_clean(M, where='intl_build')          # ΔΕΝ γραφεται ποτε αρχειο με διπλα
print(f'διπλα που αφαιρεθηκαν: {_n0 - len(M)}')
M.to_csv('intl_matches.csv', index=False)
print(f'ματς συνολο {len(M)} · με xG {int(M.has_xg.sum())} · φιλικα απο Nowgoal {nf}')
print(M.groupby(['ctype', 'season']).size().unstack(fill_value=0))
print('\nανεπιλυτα ονοματα φιλικων (top 25):', sorted(unres.items(), key=lambda x: -x[1])[:25])
