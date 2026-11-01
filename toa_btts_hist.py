"""
toa_btts_hist.py — ΠΡΑΓΜΑΤΙΚΕΣ ιστορικες τιμες BTTS απο το Odds API για τα ΥΠΟΨΗΦΙΑ ματς (27/9/2026, εντολη Στελιου).

Μονο τα ματς οπου η συναινεση ≥2/3 εδινε BTTS Yes με edge ≥8% (pick) ή «λιγο κατω» 5-8% στο τεστ (btts_realprice_candidates.csv,
απο 3/5/2023 — απο τοτε κραταει ιστορικο BTTS το Odds API). Στιγμιοτυπο: 30′ πριν τη σεντρα (οσο πιο κοντα στο κλεισιμο του τεστ).
Κοστος: ιστορικα events 1 credit (κοινο ανα σεντρα) + ιστορικες τιμες event 10 credits (1 αγορα × 1 region eu).
Resumable (toa_btts_hist.jsonl)· σταματα αν τα credits πεσουν κατω απο 3.000. Τρεχει ΜΟΝΟ στο GitHub (TOA_KEY) — toa-btts-hist.yml.
"""
import os, sys, json, datetime as dt
import pandas as pd, requests
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from intl_odds_scan import sim, alias

KEY = os.environ.get('TOA_KEY')
OUT = 'toa_btts_hist.jsonl'
MIN_CREDITS = 3000
SPORT = {'WCQ_UEFA': 'soccer_fifa_world_cup_qualifiers_europe', 'EUROQ': 'soccer_uefa_euro_qualification',
         'NationsLeagueA': 'soccer_uefa_nations_league', 'NationsLeagueB': 'soccer_uefa_nations_league',
         'NationsLeagueC': 'soccer_uefa_nations_league', 'NationsLeagueD': 'soccer_uefa_nations_league',
         'WorldCup': 'soccer_fifa_world_cup', 'EURO': 'soccer_uefa_european_championship'}
API = 'https://api.the-odds-api.com/v4/historical/sports'


def main():
    if not KEY:
        print('TOA_KEY δεν υπαρχει (τοπικα) — τιποτα'); return
    C = pd.read_csv('btts_realprice_candidates.csv', dtype={'mid': str})
    done = set()
    if os.path.exists(OUT):
        done = {json.loads(l)['mid'] for l in open(OUT, encoding='utf-8') if l.strip()}
    ev_cache = {}; rem = None; n = 0
    fh = open(OUT, 'a', encoding='utf-8')
    for r in C.itertuples():
        if r.mid in done or r.comp not in SPORT:
            continue
        ko = dt.datetime.fromisoformat(str(r.date)[:19])
        snap = (ko - dt.timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
        sp = SPORT[r.comp]
        if (sp, snap) not in ev_cache:
            q = requests.get(f'{API}/{sp}/events', params=dict(apiKey=KEY, date=snap), timeout=40)
            rem = q.headers.get('x-requests-remaining')
            ev_cache[(sp, snap)] = (q.json().get('data') or []) if q.status_code == 200 else []
        best, bs = None, 0.0
        for e in ev_cache[(sp, snap)]:
            try:
                ek = dt.datetime.fromisoformat(e['commence_time'].replace('Z', '+00:00')).replace(tzinfo=None)
            except Exception:
                continue
            if abs((ek - ko).total_seconds()) > 3 * 3600:
                continue
            s = sim(alias(e['home_team']), r.hn) + sim(alias(e['away_team']), r.an)
            if s > bs:
                bs, best = s, e
        row = dict(mid=r.mid, date=str(r.date)[:16], comp=r.comp, home=r.hn, away=r.an, band=r.band, e2=r.e2, snap=snap, sport=sp)
        if best is None or bs < 1.1:
            row['status'] = 'no_event'
        else:
            q = requests.get(f"{API}/{sp}/events/{best['id']}/odds",
                             params=dict(apiKey=KEY, date=snap, regions='eu', markets='btts', oddsFormat='decimal'), timeout=40)
            rem = q.headers.get('x-requests-remaining'); n += 1
            books = {}
            if q.status_code == 200:
                for bk in ((q.json().get('data') or {}).get('bookmakers') or []):
                    for mk in bk.get('markets', []):
                        if mk.get('key') == 'btts':
                            o = {x.get('name'): x.get('price') for x in mk.get('outcomes', [])}
                            if o.get('Yes') and o.get('No'):
                                books[bk['key']] = [o['Yes'], o['No']]
            row.update(eid=best['id'], toa_home=best['home_team'], toa_away=best['away_team'], status=('ok' if books else f'no_btts_{q.status_code}'),
                       books=books)
        fh.write(json.dumps(row, ensure_ascii=False) + '\n'); fh.flush()
        print(f"{row['date']} {r.hn}-{r.an}: {row['status']} {len(row.get('books', {}))} βιβλια · credits {rem}", flush=True)
        try:
            if rem is not None and float(rem) < MIN_CREDITS:
                print(f'credits {rem} < {MIN_CREDITS} — σταματαω'); break
        except Exception:
            pass
    fh.close()
    print(f'τελος: {n} τραβηγματα τιμων · credits {rem}')


if __name__ == '__main__':
    main()
