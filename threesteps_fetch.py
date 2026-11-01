# -*- coding: utf-8 -*-
"""threesteps_fetch.py — στατιστικα παικτων-σεζον απο 3StepsBasket (ανοιχτο API, 25/9/2026, προταση Στελιου).
API: https://ycpcq74tr3.execute-api.eu-central-1.amazonaws.com/prod
  /league/{slug}/clubs-full-stats?competitionId=…  → ομαδες σεζον
  /club/{clubId}/players-stats?competitionId=…      → παικτες ομαδας: box ανα αγωνα + ON-COURT (teamPoints/oppPoints/κατοχες
                                                      οσο ειναι στο παρκε, απο play-by-play) + usg/ast%/trn%/reb% + overallRating
Πρωταθληματα/σεζον: οσα υπαρχουν (Ευρωλιγκα 2019-20+, EuroCup 2020-21+, NBA 2020-21+, ACB/LNB/BBL/BCL/ESAKE/TBF/LBA ~2022+).
Ευγενικα: 0.5 δευτ. μεταξυ κλησεων. Cache: threesteps_cache/. Εξοδος: threesteps_players.csv"""
import os, sys, json, time, urllib.request, urllib.error
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
B = 'https://ycpcq74tr3.execute-api.eu-central-1.amazonaws.com/prod'
CACHE = 'threesteps_cache'; os.makedirs(CACHE, exist_ok=True)
def J(path):
    fn = os.path.join(CACHE, path.strip('/').replace('/', '_').replace('?', '_').replace('=', '_') + '.json')
    if os.path.exists(fn): return json.load(open(fn, encoding='utf-8'))
    for a in range(4):
        try:
            time.sleep(0.5)
            d = json.loads(urllib.request.urlopen(urllib.request.Request(B + path, headers={'User-Agent': 'Mozilla/5.0'}), timeout=40).read())
            json.dump(d, open(fn, 'w', encoding='utf-8'), ensure_ascii=False); return d
        except urllib.error.HTTPError as e:
            if e.code in (400, 404): return None
            time.sleep(10 * (a + 1))
        except Exception:
            time.sleep(5 * (a + 1))
    return None

COMPS = {
 'euroleague': [f'euroleague-{y}' for y in range(2018, 2028)],
 'eurocup': [f'eurocup-{y}' for y in range(2019, 2027)],
 'nba': ['nba-2020', 'nba-2021', 'nba-2022', 'nba23', 'nba24', 'nba25', 'nba26'],
 'acb': ['acb-2021', 'acb-2022', 'acb-2023', 'acb24', 'acb25', 'acb26'],
 'lnb': ['lnb-2021', 'lnb-2022', 'lnb-2023', 'lnb24', 'lnb25', 'lnb26'],
 'bundesliga': ['bbl-2021', 'bbl-2022', 'bbl-2023', 'bbl24', 'bbl25', 'bbl26', 'bbl27'],
 'bcl': ['bcl-2021', 'bcl-2022', 'bcl-23', 'bcl24', 'bcl25', 'bcl26'],
 'esake': ['esake-2022', 'esake-2023', 'esake24', 'gbl24', 'gbl25', 'gbl26'],
 'tbf': ['bsl-2022', 'bsl-2023', 'bsl23', 'bsl24', 'bsl25', 'bsl26'],
 'lba': ['lba-2022', 'lba-2023', 'lba23', 'lba24', 'lba25', 'lba26'],
}
rows = []
for slug, cids in COMPS.items():
    for cid in cids:
        d = J(f'/league/{slug}/clubs-full-stats?competitionId={cid}')
        if not d or not d.get('teams'): continue
        season = d.get('season'); nP = 0
        for t in d['teams']:
            c = J(f"/club/{t['clubId']}/players-stats?competitionId={cid}")
            if not c: continue
            for p in c.get('players', []):
                r = {k: v for k, v in p.items() if not isinstance(v, (dict, list))}
                r.update(league=d.get('league'), slug=slug, cid=cid, season=season, clubId=t['clubId'], club=t.get('teamName'),
                         team_games=t.get('games'))
                rows.append(r); nP += 1
        print(f'{slug:11s} {cid:16s} {season}: ομαδες {len(d["teams"])} · παικτες {nP}', flush=True)
        pd.DataFrame(rows).to_csv('threesteps_players.csv', index=False)
print(f'ΤΕΛΟΣ: {len(rows)} γραμμες παικτη-σεζον')
