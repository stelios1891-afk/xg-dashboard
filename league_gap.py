# -*- coding: utf-8 -*-
"""
league_gap.py — Συντελεστες δυσκολιας πρωταθληματων απο τους μετακινουμενους παικτες.

Μοντελο: rating(παικτης, λιγκα) = ικανοτητα + offset(λιγκα) + θορυβος.
Γεφυρες: ιδιος παικτης σε 2 λιγκες σε γειτονικες (η ιδιες) σεζον.
Διορθωση RTM: αφαιρειται η μεση φυσιολογικη μεταβολη σεζον-σε-σεζον ΙΔΙΑΣ λιγκας.
Λυση: σταθμισμενα ελαχιστα τετραγωνα, αγκυρα EPL=0.
Εξοδος: league_offsets.json {leagueKey: offset}
"""
import sys, json, glob
import numpy as np, pandas as pd
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')

# ---- 1. (παικτης, σεζον, λιγκα) -> μεσο rating, βαρος ----
# α) δικο μας αρχειο (ανα ματς) — λιγκες CORE7 + ευρωπαικες διοργανωσεις
PM = json.load(open('player_matches.json', encoding='utf-8'))
TG = pd.read_csv('teamgame_inputs_5s.csv'); TG['season'] = TG.season.astype(str); TG['mid'] = TG['mid'].astype(str)
EU = json.load(open('europe_fixtures.json', encoding='utf-8'))
mid_lg = TG.groupby('mid').league.first().to_dict()
mid_sea = TG.groupby('mid').season.first().to_dict()
eu_info = {}
for comp, rows in EU.items():
    for m in rows:
        eu_info[m['mid']] = (comp, m['utc'][:10])

def sea_end(sea):     # '2425' -> 2025.0
    return 2000 + int(sea[2:]) + 0.0

acc = defaultdict(lambda: [0.0, 0])   # (pid, end_year, lgkey) -> [sum_rt, n]
for mid, rec in PM.items():
    if not rec:
        continue
    if mid in mid_lg:
        key = mid_lg[mid]; end = sea_end(mid_sea[mid])
    elif mid in eu_info:
        comp, d = eu_info[mid]
        key = 'EU_' + comp
        y, mth = int(d[:4]), int(d[5:7])
        end = y + 1.0 if mth >= 7 else float(y)
    else:
        continue
    for sk in ('h', 'a'):
        for p in (rec.get(sk, {}).get('p') or []):
            if p[1] is not None:
                a = acc[(p[0], end, key)]
                a[0] += p[1]; a[1] += 1

# β) careers (συγκεντρωτικα ανα σεζον/λιγκα, χωρις φιλικα)
def career_end(sn):
    s = str(sn)
    try:
        if '/' in s:
            return float(s.split('/')[1])
        return int(s) + 0.5
    except (ValueError, IndexError):
        return None

for f in ('player_career.jsonl', 'player_career_debuts.jsonl'):
    for line in open(f, encoding='utf-8'):
        r = json.loads(line)
        for sn, lgid, lg, apps, rt, fr in r['s']:
            if fr or rt is None or not apps or lg is None:
                continue
            end = career_end(sn)
            if end is None:
                continue
            key = f'{lg}#{lgid}'
            a = acc[(r['pid'], end, key)]
            a[0] += rt * apps; a[1] += apps

# ενοποιηση ονοματων: οι 7 CORE λιγκες εμφανιζονται και στα careers με leagueId
FOT_IDS = {'Premier League#47': 'EPL', 'LaLiga#87': 'LaLiga', 'Serie A#55': 'SerieA',
           'Bundesliga#54': 'Bundesliga', 'Ligue 1#53': 'Ligue1', 'Eredivisie#57': 'Eredivisie',
           'Liga Portugal#61': 'PrimeiraLiga', 'Champions League#42': 'EU_UCL',
           'Europa League#73': 'EU_UEL', 'Conference League#10216': 'EU_UECL'}
rows = []
for (pid, end, key), (s, n) in acc.items():
    if n < 3:
        continue
    rows.append((pid, end, FOT_IDS.get(key, key), s / n, n))
D = pd.DataFrame(rows, columns=['pid', 'end', 'lg', 'rt', 'n'])
print('μοναδες (παικτης×σεζον×λιγκα):', len(D), '· λιγκες:', D.lg.nunique())

# ---- 2. γεφυρες ----
D = D.sort_values(['pid', 'end'])
pairs = []
for pid, g in D.groupby('pid'):
    g = g.reset_index(drop=True)
    for i in range(len(g)):
        for j in range(i + 1, len(g)):
            dt = g.end[j] - g.end[i]
            if dt > 1.5:
                continue
            w = min(g.n[i], g.n[j])
            pairs.append((g.lg[i], g.lg[j], g.rt[j] - g.rt[i], w, dt))
P = pd.DataFrame(pairs, columns=['a', 'b', 'd', 'w', 'dt'])
same = P[P.a == P.b]
rtm = np.average(same.d, weights=same.w)      # φυσιολογικη μεταβολη ιδιας λιγκας
print('RTM βαση (ιδια λιγκα, γειτονικες σεζον): %+.4f (n=%d ζευγη)' % (rtm, len(same)))
X = P[P.a != P.b].copy()
X['d_adj'] = X.d - rtm * (X.dt > 0)           # στις ταυτοχρονες (dt=0) δεν αφαιρειται

# κρατα λιγκες με αρκετο συνολικο βαρος γεφυρων
wsum = defaultdict(float)
for r in X.itertuples():
    wsum[r.a] += r.w; wsum[r.b] += r.w
keep = {k for k, v in wsum.items() if v >= 150}
X = X[X.a.isin(keep) & X.b.isin(keep)]
lgs = sorted(keep)
idx = {l: i for i, l in enumerate(lgs)}
print('λιγκες με αρκετες γεφυρες:', len(lgs), '· ζευγη:', len(X))

# ---- 3. λυση LSQ: d_adj ≈ o[b] − o[a], αγκυρα EPL=0 ----
A = np.zeros((len(X) + 1, len(lgs))); y = np.zeros(len(X) + 1); w = np.zeros(len(X) + 1)
for r_i, r in enumerate(X.itertuples()):
    A[r_i, idx[r.b]] = 1; A[r_i, idx[r.a]] = -1
    y[r_i] = r.d_adj; w[r_i] = np.sqrt(r.w)
A[-1, idx['EPL']] = 1000; y[-1] = 0; w[-1] = 1  # αγκυρα
Aw = A * w[:, None]; yw = y * w
o, *_ = np.linalg.lstsq(Aw, yw, rcond=None)

print()
print('ΣΥΝΤΕΛΕΣΤΕΣ (0 = Premier League· θετικο = ΕΥΚΟΛΟΤΕΡΗ λιγκα, τα ρειτινγκ εκει ειναι "φουσκωμενα"):')
res = sorted(zip(lgs, o), key=lambda x: x[1])
for lg, v in res:
    print('  %-28s %+.3f   (βαρος γεφυρων %.0f)' % (lg, v, wsum[lg]))
json.dump({lg: round(float(v), 4) for lg, v in res}, open('league_offsets.json', 'w', encoding='utf-8'), ensure_ascii=False)
print()
print('αποθηκευτηκε: league_offsets.json')
