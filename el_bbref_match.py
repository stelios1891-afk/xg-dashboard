# -*- coding: utf-8 -*-
"""el_bbref_match.py — αντιστοιχιση παικτων Ευρωλιγκας ↔ Basketball-Reference (25/9/2026, αξια παικτων v2).
Για καθε παικτη που επαιξε Ευρωλιγκα στη σεζον E{Y} χωρις λεπτα EL/EC στην E{Y-1} («κενο»): ψαχνουμε τη σεζον του στο B-R με
season_end = Y (δηλ. την προηγουμενη χρονια, π.χ. E2025=2025-26 → B-R 2024-25 = 2025).
Ονομα: χωρις τονους/σημεια, πεζα, ιδιο συνολο λεξεων («VALANCIUNAS, JONAS» = «Jonas Valančiūnas»)· εφεδρικα: επωνυμο + 1ο γραμμα.
Εξοδος: el_bbref_map.csv (el_pid, season, bbref_pid, league, team, mp …) + αναφορα καλυψης."""
import sys, json, re, unicodedata
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')

def norm(s):
    s = unicodedata.normalize('NFD', str(s)); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    s = s.replace('ı', 'i').replace('ł', 'l').replace('ø', 'o').replace('đ', 'd').replace('ß', 'ss')
    if ',' in s:
        last, first = s.split(',', 1); s = first + ' ' + last
    w = [x for x in re.findall(r'[a-z]+', s) if x not in ('jr', 'sr', 'ii', 'iii', 'iv')]
    return w
def key_full(s): return ' '.join(sorted(norm(s)))
def key_short(s):
    w = norm(s); return (w[-1], w[0][0]) if len(w) >= 2 else None

BR = pd.read_csv('bbref_totals.csv')
# NCAA (barttorvik: ετος = ετος ληξης· στηλες κατα toRvik — GP=3, mp/αγ=55, pts/αγ=63)
import glob
nc = []
for f in sorted(glob.glob('ncaa_cache/bt_*.csv')):
    y = int(f[-8:-4])
    try: d = pd.read_csv(f, header=None, low_memory=False)
    except Exception: continue
    nc.append(pd.DataFrame(dict(league='ncaa', season_end=y, player=d[0], pid='ncaa:' + d[32].astype(str), team=d[1],
                                g=pd.to_numeric(d[3], errors='coerce'), mp=pd.to_numeric(d[3], errors='coerce') * pd.to_numeric(d[55], errors='coerce'),
                                pts=pd.to_numeric(d[3], errors='coerce') * pd.to_numeric(d[63], errors='coerce'))))
if nc: BR = pd.concat([BR] + nc, ignore_index=True)
BR = BR[BR.mp.notna() & (BR.mp > 0)]
BR['kf'] = BR.player.map(key_full); BR['ks'] = BR.player.map(key_short)
# ενα γραμμη ανα (παικτης, πρωταθλημα, σεζον): στο NBA κραταμε το συνολο (TOT) αν υπαρχει
BR = BR.sort_values('mp', ascending=False).drop_duplicates(['pid', 'league', 'season_end'])

PL = json.load(open('el_players.json', encoding='utf-8'))
mins, played, names = {}, {}, {}
for k, g in PL.items():
    if 'err' in g or 'ph' not in g: continue
    yr = int(g['season'][1:])
    for side, tc in (('ph', g['hcode']), ('pa', g['acode'])):
        for p in g[side]:
            names[p[0]] = p[1]
            if not p[3]: continue
            played[(p[0], yr)] = played.get((p[0], yr), 0) + p[3]
            if g['comp'] == 'E':
                mins.setdefault((yr, tc), {}); mins[(yr, tc)][p[0]] = mins[(yr, tc)].get(p[0], 0) + p[3]
bio = json.load(open('el_player_bio.json', encoding='utf-8'))
for k, v in bio.items():
    if isinstance(v, dict) and v.get('name'): names.setdefault(k if k.startswith('P') else 'P' + k, v['name'])
people = json.load(open('el_people.json', encoding='utf-8'))
for k, L in people.items():
    for p in L:
        if p['type'] == 'J' and p['code']: names.setdefault('P' + p['code'], p['name'])

targets = []
for (yr, tc), d in mins.items():
    if yr < 2017: continue
    for pid, m in d.items():
        if pid in mins.get((yr - 1, tc), {}): continue
        if played.get((pid, yr - 1), 0) >= 100: continue
        targets.append(dict(el_pid=pid, season=yr, team=tc, el_min=m))
# τρεχουσα σεζον (E2026): οσοι ειναι στο ροστερ χωρις EL/EC περσι
for k, L in people.items():
    if not k.startswith('E2026_'): continue
    tc = k.split('_')[1]
    for p in L:
        if p['type'] != 'J' or not p['code']: continue
        pid = 'P' + p['code']
        if played.get((pid, 2025), 0) >= 100: continue
        targets.append(dict(el_pid=pid, season=2026, team=tc, el_min=None))
T = pd.DataFrame(targets).drop_duplicates(['el_pid', 'season', 'team'])
T['name'] = T.el_pid.map(names)

byf = {k: g for k, g in BR.groupby('kf')}; bys = {k: g for k, g in BR.groupby('ks')}
out = []
for r in T.itertuples():
    nm = r.name or ''
    c = byf.get(key_full(nm)); how = 'ονομα'
    if c is None:
        c = bys.get(key_short(nm)); how = 'επωνυμο+αρχικο'
    if c is not None: c = c[c.season_end == r.season]
    if c is None or not len(c):
        out.append(dict(r._asdict(), how='—')); continue
    c = c[~c.league.isin(['euroleague'])]                 # η EL την εχουμε ηδη
    if not len(c):
        out.append(dict(r._asdict(), how='—')); continue
    b = c.sort_values('mp', ascending=False).iloc[0]
    out.append(dict(r._asdict(), how=how, bbref_pid=b.pid, bbref_name=b.player, league=b.league, bteam=b.team, g=b.g, mp=b.mp,
                    n_leagues=c.league.nunique()))
M = pd.DataFrame(out).drop(columns=['Index'])
birth = {}
for k, v in bio.items():
    if isinstance(v, dict) and v.get('birth'): birth[k if k.startswith('P') else 'P' + k] = v['birth']
def why(r):
    if r.how != '—': return 'βρεθηκε: ' + str(r.league)
    if any(played.get((r.el_pid, y), 0) >= 100 for y in range(r.season - 4, r.season - 1)): return 'EL/EC παλαιοτερα (τραυμα/αλλου)'
    b = birth.get(r.el_pid)
    if b and r.season - int(b[:4]) <= 21: return 'νεαρος (≤21)'
    return 'αγνωστο (LKL/BBL/VTB/αλλο)'
M['cat'] = M.apply(why, axis=1)
M.to_csv('el_bbref_map.csv', index=False)

print('=== ΚΑΛΥΨΗ ΤΟΥ ΚΕΝΟΥ (παικτες Ευρωλιγκας χωρις EL/EC την προηγουμενη χρονια) ===')
for yr, g in M.groupby('season'):
    hit = g.how != '—'
    if yr < 2026:
        w = g.el_min.fillna(0)
        print(f'  E{yr}: παικτες {len(g):3d} · βρεθηκαν {hit.mean()*100:5.1f}% · σε λεπτα Ευρωλιγκας {w[hit].sum()/max(w.sum(),1)*100:5.1f}%')
    else:
        print(f'  E{yr} (φετος, ροστερ): παικτες {len(g):3d} · βρεθηκαν {hit.mean()*100:5.1f}%')
print('')
print('ΚΑΤΗΓΟΡΙΕΣ (2021-2025, % λεπτων Ευρωλιγκας των παικτων-κενου):')
q = M[(M.season >= 2021) & (M.season <= 2025)]
cc = q.assign(c=q.cat.where(~q.cat.str.startswith('βρεθηκε'), 'βρεθηκε σε πηγη')).groupby('c').el_min.sum()
print('  ' + ' · '.join(f'{k} {v/cc.sum()*100:.0f}%' for k, v in cc.sort_values(ascending=False).items()))
print('')
print('απο ποιο πρωταθλημα ερχονται (βρεθεντες, 2018-2026):')
print('  ' + ' · '.join(f'{k} {v}' for k, v in M[M.how != '—'].league.value_counts().items()))
print('')
nf = M[(M.cat.str.startswith('αγνωστο')) & (M.season >= 2021)].copy()
nf = nf.sort_values('el_min', ascending=False)
print('ΜΕΓΑΛΥΤΕΡΑ «αγνωστα» κενα (2021+, κατα λεπτα Ευρωλιγκας):')
for r in nf.head(25).itertuples():
    print(f'  E{r.season} {r.team} {r.name} · {r.el_min if r.el_min == r.el_min and r.el_min else "φετος"} λεπτα')
print('')
print('φετος (E2026) — ενδεικτικα: ' + ' · '.join(f'{r.name} ← {r.league} {r.bteam} ({r.mp:.0f}′)' for r in M[(M.season == 2026) & (M.how != '—')].sort_values('mp', ascending=False).head(15).itertuples()))
print('φετος — κατηγοριες: ' + ' · '.join(f'{k} {v}' for k, v in M[M.season == 2026].cat.value_counts().items()))
print('φετος — αγνωστοι: ' + ', '.join(str(x) for x in M[(M.season == 2026) & M.cat.str.startswith('αγνωστο')].name))
