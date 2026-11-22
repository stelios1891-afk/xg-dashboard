# -*- coding: utf-8 -*-
"""
toa_outrights_fetch.py — Outright αποδοσεις (πρωταθλητης / υποβιβασμος / top4) απο The Odds API
για τις CORE7 λιγκες, 2026-09-22.

TOA_KEY: inline env var (NEVER σε αρχειο).
"""
import os, sys, json, time, datetime, csv
import requests

sys.stdout.reconfigure(encoding='utf-8')

BASE = 'https://api.the-odds-api.com/v4'

CORE7_KEYWORDS = {
    'EPL': ['epl'],
    'LaLiga': ['la_liga', 'spain'],
    'SerieA': ['italy', 'serie_a'],
    'Bundesliga': ['germany', 'bundesliga'],
    'Ligue1': ['france', 'ligue_one'],
    'PrimeiraLiga': ['portugal', 'primeira'],
    'Eredivisie': ['netherlands', 'eredivisie'],
}

def _key():
    k = os.environ.get('TOA_KEY')
    if not k:
        raise RuntimeError("TOA_KEY δεν βρεθηκε στο environment (inline).")
    return k
def step1_list_sports():
    r = requests.get(f'{BASE}/sports/', params=dict(apiKey=_key(), all='true'), timeout=30)
    r.raise_for_status()
    sports = r.json()
    matches = []
    for s in sports:
        key = s.get('key', '')
        if any(tag in key for tag in ('winner', 'relegation', 'top_4', 'top4')):
            for lg, kws in CORE7_KEYWORDS.items():
                if any(kw in key for kw in kws):
                    matches.append((lg, s))
                    break
    return matches, r.headers

def step2_fetch_outrights(sport_key):
    attempts = ['outrights', 'outrights_lay', None]
    last_err = []
    for mk in attempts:
        params = dict(apiKey=_key(), regions='eu,uk', oddsFormat='decimal')
        if mk:
            params['markets'] = mk
        r = requests.get(f'{BASE}/sports/{sport_key}/odds', params=params, timeout=45)
        if r.status_code == 200:
            data = r.json()
            if data:
                return data, r.headers, mk, last_err
            else:
                last_err.append((mk, 'empty list'))
        else:
            last_err.append((mk, f'{r.status_code}: {r.text[:200]}'))
    return [], (r.headers if 'r' in dir() else {}), None, last_err
def main():
    print("=== BHMA 1: sports list (δωρεαν) ===")
    matches, hdrs = step1_list_sports()
    print(f"x-requests-remaining={hdrs.get('x-requests-remaining')} x-requests-used={hdrs.get('x-requests-used')}")
    if not matches:
        print("ΚΑΝΕΝΑ market winner/relegation/top4 δεν βρεθηκε για CORE7 λιγκες.")
    # διαγνωστικο: ΟΛΑ τα soccer keys με outrights (για να δουμε πως ονομαζονται)
    try:
        r_all = requests.get(f'{BASE}/sports/', params=dict(apiKey=_key(), all='true'), timeout=30).json()
        print('=== ΟΛΑ τα soccer sports με has_outrights=True ===')
        for s_ in r_all:
            if str(s_.get('key', '')).startswith('soccer') and s_.get('has_outrights'):
                print(f"  {s_.get('key')} | {s_.get('title')} | active={s_.get('active')}")
        print('=== soccer keys που περιεχουν winner/relegation/top ===')
        for s_ in r_all:
            k_ = str(s_.get('key', ''))
            if k_.startswith('soccer') and any(t in k_ for t in ('winner', 'relegation', 'top')):
                print(f"  {k_} | {s_.get('title')} | active={s_.get('active')} | outrights={s_.get('has_outrights')}")
        print(f"(συνολο sports: {len(r_all)}, soccer: {sum(1 for s_ in r_all if str(s_.get('key', '')).startswith('soccer'))})")
        print('=== ΟΛΑ τα soccer sports (key | title | active) ===')
        for s_ in r_all:
            if str(s_.get('key', '')).startswith('soccer'):
                print(f"  {s_.get('key')} | {s_.get('title')} | active={s_.get('active')}")
    except Exception as e_:
        print('diag error', e_)
    by_league = {}
    for lg, s in matches:
        by_league.setdefault(lg, []).append(s)
        print(f"  {lg}: key={s.get('key')} title={s.get('title')} active={s.get('active')} has_outrights={s.get('has_outrights')}")
    print("\n=== BHMA 2: outrights fetch ανα key ===")
    total_cost = 0
    raw_out = {}
    errors = {}
    last_headers = hdrs
    for lg, slist in by_league.items():
        for s in slist:
            key = s.get('key')
            data, headers, used_market, errs = step2_fetch_outrights(key)
            last_headers = headers or last_headers
            cost = headers.get('x-requests-last')
            try:
                cost_i = int(cost) if cost is not None else None
            except ValueError:
                cost_i = None
            if cost_i:
                total_cost += cost_i
            print(f"  {lg} / {key}: market_used={used_market} events={len(data)} cost={cost_i} errors={errs}")
            if data:
                raw_out[key] = dict(league=lg, fetched_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                     sport_key=key, market_used=used_market, events=data)
            else:
                errors[key] = errs
    with open('toa_outrights_2627.json', 'w', encoding='utf-8') as f:
        json.dump(raw_out, f, ensure_ascii=False, indent=2)
    print(f"\nΑποθηκευτηκε toa_outrights_2627.json ({len(raw_out)} keys με δεδομενα)")
    print(f"x-requests-remaining={last_headers.get('x-requests-remaining')} τελικο")
    print(f"Συνολικο κοστος (αθροισμα x-requests-last): {total_cost}")

    rows = []
    overround_report = []
    for key, obj in raw_out.items():
        lg = obj['league']
        for ev in obj['events']:
            market_name_guess = None
            for bm in ev.get('bookmakers', []):
                book = bm.get('key')
                for mk in bm.get('markets', []):
                    mkey = mk.get('key')
                    outcomes = mk.get('outcomes', [])
                    if not outcomes:
                        continue
                    mclass = 'winner'
                    tk = (key or '').lower()
                    if 'relegation' in tk:
                        mclass = 'relegation'
                    elif 'top_4' in tk or 'top4' in tk:
                        mclass = 'top4'
                    s_inv = sum(1.0/o['price'] for o in outcomes if o.get('price'))
                    for o in outcomes:
                        price = o.get('price')
                        if not price:
                            continue
                        implied = 1.0/price
                        implied_norm = implied / s_inv if s_inv else None
                        rows.append(dict(league=lg, market=mclass, sport_key=key, team=o.get('name'),
                                          book=book, odds=price, implied=implied, implied_norm=implied_norm))
                    overround_report.append((lg, mclass, key, book, s_inv))
    from collections import defaultdict
    best = defaultdict(float)
    pin = {}
    for r in rows:
        k = (r['league'], r['market'], r['team'])
        if r['odds'] > best[k]:
            best[k] = r['odds']
        if r['book'] == 'pinnacle':
            pin[k] = r['odds']
    for r in rows:
        k = (r['league'], r['market'], r['team'])
        r['best_odds'] = best[k]
        r['pinnacle_odds'] = pin.get(k)

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dashboard'))
    try:
        import picks as engine
        from league_config import ALIAS_TOA
    except Exception as e:
        print(f"WARN: δεν φορτωθηκε picks/league_config: {e}")
        engine = None
        ALIAS_TOA = {}

    fm_teams = {}
    for lg in CORE7_KEYWORDS:
        fn = f'data_{lg}_2627.json'
        if os.path.exists(fn):
            with open(fn, encoding='utf-8') as f:
                d = json.load(f)
            names = set()
            for mid, g in d.items():
                names.add(g['home']['name']); names.add(g['away']['name'])
            fm_teams[lg] = names

    inv_alias = {v: k for k, v in ALIAS_TOA.items()}

    def norm(s):
        return s.lower().replace('.', '').replace('-', ' ').strip()

    unmatched = []
    for r in rows:
        lg = r['league']
        team = r['team']
        candidates = fm_teams.get(lg, set())
        fm_name = None
        if team in candidates:
            fm_name = team
        elif team in inv_alias and inv_alias[team] in candidates:
            fm_name = inv_alias[team]
        else:
            tn = norm(team)
            for c in candidates:
                if norm(c) == tn or tn in norm(c) or norm(c) in tn:
                    fm_name = c
                    break
        r['fotmob_name'] = fm_name
        if fm_name is None:
            unmatched.append((lg, team))
    fieldnames = ['league', 'market', 'team', 'fotmob_name', 'book', 'odds', 'implied',
                  'implied_norm', 'best_odds', 'pinnacle_odds', 'sport_key']
    with open('toa_outrights_2627.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fieldnames})
    print(f"\nΑποθηκευτηκε toa_outrights_2627.csv ({len(rows)} γραμμες)")

    print("\n=== Overround ανα book/market ===")
    seen = set()
    for lg, mclass, key, book, s_inv in overround_report:
        sig = (lg, mclass, key, book)
        if sig in seen:
            continue
        seen.add(sig)
        print(f"  {lg} {mclass} {key} {book}: overround={s_inv:.4f}")

    if unmatched:
        print("\n=== ΑΤΑΙΡΙΑΣΤΑ ονοματα ===")
        for lg, team in sorted(set(unmatched)):
            print(f"  {lg}: '{team}'")
    else:
        print("\nΟλα τα ονοματα ταιριαξαν.")

if __name__ == '__main__':
    main()
