# -*- coding: utf-8 -*-
"""nfl_sbr_fetch.py — Ιστορικο ΚΑΘΕ αλλαγης γραμμης NFL απο sportsbookreview.com (δωρεαν), σεζον 2019→τωρα.

Πως: καθε ματς εχει σελιδα /betting-odds/nfl-football/line-history/{gameId}/ με ολες τις αλλαγες (ωρα UTC) ανα βιβλιο
για χαντικαπ, συνολα, νικητη. Τα ματς μιας σεζον εχουν σχεδον συνεχομενους κωδικους:
  1) «σποροι»: η σελιδα ολων των αθληματων ανα μερα (/betting-odds/?date=) δινει 3 κωδικους NFL για καθε μερα με ματς
  2) σαρωση ολων των κωδικων γυρω απο τους σπορους (κενα ≤ GAP ενωνονται, +PAD στις ακρες)· οτι δεν ειναι NFL αγνοειται
Resumable: nfl_data/sbr_state.json (σποροι + κωδικοι που ελεγχθηκαν), nfl_data/sbr_lines.jsonl (ενα NFL ματς/γραμμη):
  {id, start, home, away, books: {book: {s: [[t, homeSpread, homeOdds, awayOdds]], t: [[t, total, over, under]],
                                         ml: [[t, homeOdds, awayOdds]]}}}     (περιεχει ΚΑΙ in-play — φιλτραρε t < start)
  python nfl_sbr_fetch.py [σεζον...]      π.χ. python nfl_sbr_fetch.py 2024   (προεπιλογη 2019..φετος)
"""
import json, os, re, sys, time, random, urllib.request
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nfl_data')
OUT, STATE = os.path.join(D, 'sbr_lines.jsonl'), os.path.join(D, 'sbr_state.json')
BASE = 'https://www.sportsbookreview.com'
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36'}
GAP, PAD, SLEEP, WORKERS = 400, 40, 0.6, 3


def page(path, tries=3):
    for k in range(tries):
        try:
            s = urllib.request.urlopen(urllib.request.Request(BASE + path, headers=UA), timeout=40).read().decode('utf-8', 'ignore')
            m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', s, re.S)
            return json.loads(m.group(1))['props'].get('pageProps') if m else None
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(5 * (k + 1))
        except Exception:
            time.sleep(5 * (k + 1))
    return None


def seeds_for(day):
    pp = page(f'/betting-odds/?date={day}')
    if not pp:
        return []
    return [g['gameView']['gameId'] for t in pp.get('oddsTables', []) for g in t['oddsTableModel']['gameRows']
            if g['gameView'].get('leagueName') == 'NFL']


def game(gid):
    pp = page(f'/betting-odds/nfl-football/line-history/{gid}/')
    try:
        lh = pp['lineHistoryModel']['lineHistory']
        g = lh['gameView']
    except Exception:
        return None
    if g.get('leagueName') != 'NFL':
        return {'id': gid, 'lg': g.get('leagueName')}
    books = {}
    for o in lh.get('oddsViews') or []:
        if not o:
            continue
        b = {'s': [[x['oddsDate'], x.get('homeSpread'), x.get('homeOdds'), x.get('awayOdds')] for x in o.get('spreadHistory') or []],
             't': [[x['oddsDate'], x.get('total'), x.get('overOdds'), x.get('underOdds')] for x in o.get('totalHistory') or []],
             'ml': [[x['oddsDate'], x.get('homeOdds'), x.get('awayOdds')] for x in o.get('moneyLineHistory') or []]}
        if b['s'] or b['t'] or b['ml']:
            books[o['sportsbook']] = b
    return {'id': gid, 'lg': 'NFL', 'start': g['startDate'], 'home': g['homeTeam']['shortName'],
            'away': g['awayTeam']['shortName'], 'hs': g.get('homeTeamScore'), 'as': g.get('awayTeamScore'), 'books': books}


def ranges(ids):
    ids = sorted(set(ids))
    out, a, b = [], ids[0], ids[0]
    for i in ids[1:]:
        if i - b <= GAP:
            b = i
        else:
            out.append((a - PAD, b + PAD)); a = b = i
    out.append((a - PAD, b + PAD))
    return out


def main():
    st = json.load(open(STATE, encoding='utf-8')) if os.path.exists(STATE) else {'seeds': {}, 'checked': []}
    checked = set(st['checked'])
    g = pd.read_csv(os.path.join(D, 'games.csv'), low_memory=False)
    now = pd.Timestamp.now(tz='UTC')
    seasons = [int(a) for a in sys.argv[1:]] or list(range(2019, int(g.season.max()) + 1))
    fh = open(OUT, 'a', encoding='utf-8')
    for S in seasons:
        days = sorted(set(g.loc[g.season == S, 'gameday']))
        days = [d for d in days if pd.Timestamp(d, tz='UTC') < now + pd.Timedelta(days=1)]
        for d in days:
            if d in st['seeds']:
                continue
            st['seeds'][d] = seeds_for(d)
            time.sleep(SLEEP)
        json.dump(st, open(STATE, 'w', encoding='utf-8'))
        ids = [i for d in days for i in st['seeds'].get(d, [])]
        if not ids:
            print(S, 'κανενας σπορος'); continue
        R = ranges(ids)
        todo = [i for a, b in R for i in range(a, b + 1) if i not in checked]
        print(f'{S}: {len(days)} μερες, {len(set(ids))} σποροι, ευρη {R}, προς ελεγχο {len(todo)}', flush=True)
        n_nfl = 0
        for k, gid in enumerate(todo):
            r = game(gid)
            checked.add(gid)
            if r and r.get('lg') == 'NFL':
                fh.write(json.dumps(r, separators=(',', ':')) + '\n'); fh.flush(); n_nfl += 1
            if k % 100 == 0:
                st['checked'] = sorted(checked); json.dump(st, open(STATE, 'w', encoding='utf-8'))
                print(f'  [{k}/{len(todo)}] NFL {n_nfl}', flush=True)
            time.sleep(SLEEP + random.random() * 0.3)
        st['checked'] = sorted(checked); json.dump(st, open(STATE, 'w', encoding='utf-8'))
        print(f'{S}: τελος, NFL ματς {n_nfl}', flush=True)


if __name__ == '__main__':
    main()
