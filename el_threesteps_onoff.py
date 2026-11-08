# -*- coding: utf-8 -*-
"""el_threesteps_onoff.py — ON/OFF παικτων Ευρωλιγκας απο 3StepsBasket (play-by-play) + καλυψη «αγνωστων» μεταγραφων (25/9/2026).
on  = 100·(ποντοι ομαδας − αντιπαλου)/κατοχες ΟΣΟ ειναι στο παρκε  (ανα αγωνα × αγωνες)
off = το ιδιο για οταν ΔΕΝ ειναι (συνολα ομαδας − on)
on−off = «καθαρο» +/- του παικτη (ανα 100 κατοχες)
Εξοδος: el_onoff_3s.csv + αναφορα"""
import sys, json, glob, re, unicodedata
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
T = pd.read_csv('threesteps_players.csv', low_memory=False)

# συνολα ομαδων ανα σεζον (ποντοι υπερ/κατα, κατοχες)
team = {}
for f in glob.glob('threesteps_cache/league_*_clubs-full-stats*.json'):
    d = json.load(open(f, encoding='utf-8'))
    if not d or not d.get('teams'): continue
    cid = d['competitionId']
    for t in d['teams']:
        pts = 2 * t['madeTwo'] + 3 * t['madeThree'] + t['madeFt']; opp = 2 * t['oppMadeTwo'] + 3 * t['oppMadeThree'] + t['oppMadeFt']
        team[(cid, t['clubId'])] = dict(pts=pts, opp=opp, poss=(t['offPossessions'] + t['defPossessions']) / 2, games=t['games'])
E = T[T.slug == 'euroleague'].copy()
g = E.gamesPlayed.fillna(0)
E['on_pts'] = E.teamPoints * g; E['on_opp'] = E.oppPoints * g; E['on_poss'] = (E.teamPossessionsNet + E.oppPossessionsNet) / 2 * g
tt = E.apply(lambda r: team.get((r.cid, r.clubId)), axis=1)
E['tm_pts'] = [x['pts'] if x else np.nan for x in tt]; E['tm_opp'] = [x['opp'] if x else np.nan for x in tt]; E['tm_poss'] = [x['poss'] if x else np.nan for x in tt]
E['on'] = 100 * (E.on_pts - E.on_opp) / E.on_poss
E['off'] = 100 * ((E.tm_pts - E.on_pts) - (E.tm_opp - E.on_opp)) / (E.tm_poss - E.on_poss)
E['onoff'] = E['on'] - E['off']
E['tot_min'] = E.mins * g
E['name'] = (E.firstname.fillna('') + ' ' + E.surname.fillna('')).str.strip()
E.to_csv('el_onoff_3s.csv', index=False)
ok = E[(E.tot_min >= 600) & E.onoff.notna()]
print(f'παικτες-σεζον Ευρωλιγκας με on/off: {E.onoff.notna().sum()} (≥600′: {len(ok)}) · σεζον {sorted(E.season.unique())}')
print('ελεγχος: μεσο on−off σταθμισμενο με λεπτα ≈ 0 ;', round(np.average(ok.onoff, weights=ok.tot_min), 2))

# συγκριση με τη δικη μας αξια (el_player_values_v2) και fantasy
def key(s):
    s = unicodedata.normalize('NFD', str(s)); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    if ',' in s: a, b = s.split(',', 1); s = b + ' ' + a
    return ' '.join(sorted(re.findall(r'[a-z]+', s)))
V = pd.read_csv('el_player_values_v2.csv'); V['k'] = V.name.map(key)
SMAP = {'2025-26': 'E2025', '2024-25': 'E2024', '2023-24': 'E2023', '2022-23': 'E2022', '2021-22': 'E2021', '2020-21': 'E2020', '2019-20': 'E2019'}
ok = ok.assign(k=ok.name.map(key), s2=ok.season.map(SMAP))
M = ok.merge(V, left_on=['k', 's2'], right_on=['k', 'season'], how='inner', suffixes=('', '_v'))
print(f'ταιριασμα με δικη μας αξια: {len(M)} · συσχετιση on−off (3steps) με: δικο μας +/- κομματι {np.corrcoef(M.onoff, M.pm)[0,1]:.2f} · δικη μας συνολικη αξια {np.corrcoef(M.onoff, M.value)[0,1]:.2f} · PIR/40 {np.corrcoef(M.onoff, M.pir40)[0,1]:.2f}')
F = pd.read_excel('el_fantasy_prices_2026.xlsx'); F['k'] = F.Player.map(key)
L = ok[ok.season == '2025-26'].merge(F, on='k')
print(f'2025-26: συσχετιση τιμης fantasy με on−off {np.corrcoef(L.Price, L.onoff)[0,1]:.2f} · με on {np.corrcoef(L.Price, L["on"])[0,1]:.2f} · με overallRating 3steps {np.corrcoef(L.Price, L.overallRating)[0,1]:.2f}')
print('')
print('ΣΤΑΘΕΡΟΤΗΤΑ (ιδιος παικτης, διαδοχικες σεζον, ≥600′ και στις δυο): συσχετιση Y με Y+1')
seq = sorted(SMAP)
pairs = []
for a, b in zip(seq[:-1], seq[1:]):
    x = ok[ok.season == a].set_index('id'); y = ok[ok.season == b].set_index('id'); c = x.index.intersection(y.index)
    pairs.append(pd.DataFrame(dict(onoff0=x.loc[c, 'onoff'], onoff1=y.loc[c, 'onoff'], r0=x.loc[c, 'overallRating'], r1=y.loc[c, 'overallRating'], on0=x.loc[c, 'on'], on1=y.loc[c, 'on'])))
Pp = pd.concat(pairs)
print(f'  on−off {np.corrcoef(Pp.onoff0, Pp.onoff1)[0,1]:.2f} · on {np.corrcoef(Pp.on0, Pp.on1)[0,1]:.2f} · overallRating {np.corrcoef(Pp.r0, Pp.r1)[0,1]:.2f}  ({len(Pp)} ζευγη)')
V2 = V[V['min'] >= 600].copy()
pv = []
for a, b in zip(sorted(V2.season.unique())[:-1], sorted(V2.season.unique())[1:]):
    x = V2[V2.season == a].set_index('pid'); y = V2[V2.season == b].set_index('pid'); c = x.index.intersection(y.index)
    pv.append(pd.DataFrame(dict(v0=x.loc[c, 'value'], v1=y.loc[c, 'value'], p0=x.loc[c, 'pm'], p1=y.loc[c, 'pm'], b0=x.loc[c, 'box'], b1=y.loc[c, 'box'])))
Pv = pd.concat(pv)
print(f'  (δικη μας) αξια {np.corrcoef(Pv.v0, Pv.v1)[0,1]:.2f} · +/- κομματι {np.corrcoef(Pv.p0, Pv.p1)[0,1]:.2f} · στατιστικα κομματι {np.corrcoef(Pv.b0, Pv.b1)[0,1]:.2f}  ({len(Pv)} ζευγη)')
print('')
top = ok[ok.season == '2025-26'].sort_values('onoff', ascending=False)
print('2025-26 on−off κορυφη: ' + ' · '.join(f'{r.name} {r.onoff:+.1f}' for r in top.head(12).itertuples()))
print('2025-26 on−off πατος: ' + ' · '.join(f'{r.name} {r.onoff:+.1f}' for r in top.tail(8).itertuples()))
for nm in ('Mike James', 'Nadir Hifi', 'TJ Shorts', 'Shane Larkin', 'Nikola Milutinov', 'Sasha Vezenkov', 'Kendrick Nunn', 'Carsen Edwards'):
    r = ok[(ok.season == '2025-26') & (ok.name.str.lower() == nm.lower())]
    if len(r): r = r.iloc[0]; print(f'  {nm}: on {r["on"]:+.1f} · off {r["off"]:+.1f} · on−off {r.onoff:+.1f} · 3steps rating {r.overallRating}')

# ---- καλυψη «αγνωστων» μεταγραφων με 3steps (Bundesliga, BCL κτλ) ----
print('')
Mp = pd.read_csv('el_bbref_map.csv')
unk = Mp[Mp.get('cat', pd.Series(dtype=str)).astype(str).str.startswith('αγνωστο')] if 'cat' in Mp else Mp[Mp.how == '—']
T['k'] = (T.firstname.fillna('') + ' ' + T.surname.fillna('')).map(key)
SE = {'2021-22': 2022, '2022-23': 2023, '2023-24': 2024, '2024-25': 2025, '2025-26': 2026, '2020-21': 2021, '2019-20': 2020}
T['season_end'] = T.season.map(SE)
hit = []
for r in unk.itertuples():
    c = T[(T.k == key(r.name)) & (T.season_end == r.season) & (T.slug != 'euroleague')]
    hit.append((r.season, r.name, c.sort_values('mins', ascending=False).iloc[0].league if len(c) else None, r.el_min))
H = pd.DataFrame(hit, columns=['season', 'name', 'league', 'el_min'])
for s, g_ in H.groupby('season'):
    w = g_.el_min.fillna(0)
    print(f'  E{s}: «αγνωστοι» {len(g_)} → βρεθηκαν στο 3steps {g_.league.notna().sum()}' + (f' ({w[g_.league.notna()].sum()/max(w.sum(),1)*100:.0f}% των λεπτων τους)' if s < 2026 else '') + ' · ' + ', '.join(f'{n} ({l})' for n, l in zip(g_.name, g_.league) if l)[:300])
