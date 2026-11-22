# -*- coding: utf-8 -*-
"""nfl_toa_hist.py — Ιστορικες γραμμες NFL ανα ωρα απο The Odds API (historical snapshots), σεζον 2020→τωρα.

Snapshots (καθε ενα δινει ΟΛΑ τα επομενα ματς NFL εκεινη τη στιγμη):
  • ΚΑΘΗΜΕΡΙΝΑ 16:00 UTC απο 10 μερες πριν την πρεμιερα ως τον Super Bowl → πρωτη εμφανιση γραμμης + διαδρομη ανα μερα
  • για καθε ΩΡΑ ΕΝΑΡΞΗΣ (ΤΝF, Κυρ 1μμ/4μμ, SNF, MNF...): KO−3ω και KO−30′ → «αργη» τιμη και κλεισιμο
Αγορες spreads+totals · βιβλια pinnacle, draftkings, fanduel, betmgm, bovada (≤10 = ενα «region» → 20 credits/snapshot).
Resumable (οτι εχει κατεβει δεν ξαναχρεωνεται) · σταματα αν τα credits πεσουν κατω απο FLOOR.
Τρεχει στο GitHub Actions (TOA_KEY) μεσω .github/workflows/nfl-toa-hist.yml. Εξοδος: nfl_data/toa_hist.jsonl
  {req_ts, snap_ts, kind, ev:[[id, commence, home, away, {book: {s:[[name, point, price]...], t:[[name, point, price]...], u:last_update}}]]}
  python nfl_toa_hist.py --count   → μονο μετραει ποσα snapshots/credits θελει (χωρις κλειδι)
"""
import sys, os, json, time, datetime as dt
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')

OUT = 'nfl_data/toa_hist.jsonl'
SPORT = 'americanfootball_nfl'
BOOKS = 'pinnacle,draftkings,fanduel,betmgm,bovada'
FLOOR = int(os.environ.get('NFL_TOA_FLOOR', '25000'))
SEASONS = [2025, 2024, 2023, 2022, 2021, 2020, 2026]      # νεοτερες πρωτα, φετινη στο τελος
UTC = dt.timezone.utc


def plan():
    g = pd.read_csv('nfl_data/games.csv', low_memory=False)
    g = g[g.season.isin(SEASONS) & g.result.notna() & g.gametime.notna()]
    # ωρα ET → UTC (Νεα Υορκη)
    ko = pd.to_datetime(g.gameday + ' ' + g.gametime).dt.tz_localize('America/New_York').dt.tz_convert('UTC')
    g = g.assign(ko=ko)
    want = []
    for s in SEASONS:
        x = g[g.season == s]
        if x.empty:
            continue
        d0 = (x.ko.min() - pd.Timedelta(days=10)).normalize() + pd.Timedelta(hours=16)
        d = d0
        while d <= x.ko.max():
            want.append(('daily', d))
            d += pd.Timedelta(days=1)
        for k in sorted(set(x.ko)):
            want.append(('ko-3h', k - pd.Timedelta(hours=3)))
            want.append(('ko-30m', k - pd.Timedelta(minutes=30)))
    now = pd.Timestamp.now(tz='UTC')
    want = [(k, t) for k, t in want if t < now and t >= pd.Timestamp('2020-06-07', tz='UTC')]
    return [(k, t.strftime('%Y-%m-%dT%H:%M:%SZ')) for k, t in want]


def compact(ev):
    bk = {}
    for b in ev.get('bookmakers', []):
        r = {'u': b.get('last_update')}
        for m in b.get('markets', []):
            key = {'spreads': 's', 'totals': 't'}.get(m.get('key'))
            if key:
                r[key] = [[o.get('name'), o.get('point'), o.get('price')] for o in m.get('outcomes', [])]
        bk[b['key']] = r
    return [ev.get('id'), ev.get('commence_time'), ev.get('home_team'), ev.get('away_team'), bk]


def main():
    todo_all = plan()
    done = set()
    if os.path.exists(OUT):
        for line in open(OUT, encoding='utf-8'):
            try:
                done.add(json.loads(line)['req_ts'])
            except Exception:
                pass
    todo = [(k, t) for k, t in todo_all if t not in done]
    todo = list(dict.fromkeys(todo))
    print(f'snapshots: συνολο {len(todo_all)} · ηδη {len(done)} · μενουν {len(todo)} (~{20 * len(todo)} credits)', flush=True)
    if '--count' in sys.argv:
        return
    import requests
    KEY = os.environ.get('TOA_KEY')
    if not KEY:
        raise SystemExit('TOA_KEY δεν βρεθηκε στο environment.')
    rem = None
    fh = open(OUT, 'a', encoding='utf-8')
    for i, (kind, ts) in enumerate(todo):
        if rem is not None and int(float(rem)) < FLOOR:
            print(f'ΣΤΟΠ: credits {rem} < {FLOOR}', flush=True)
            break
        try:
            r = requests.get(f'https://api.the-odds-api.com/v4/historical/sports/{SPORT}/odds',
                             params=dict(apiKey=KEY, date=ts, markets='spreads,totals', bookmakers=BOOKS,
                                         oddsFormat='decimal'), timeout=45)
            rem = r.headers.get('x-requests-remaining', rem)
            if r.status_code != 200:
                print(f'  {kind} {ts}: HTTP {r.status_code} {r.text[:150]}', flush=True)
                if r.status_code in (401, 429):
                    break
                time.sleep(1)
                continue
            js = r.json()
            evs = [compact(e) for e in js.get('data') or []]
            fh.write(json.dumps(dict(req_ts=ts, snap_ts=js.get('timestamp'), kind=kind, ev=evs),
                                ensure_ascii=False, separators=(',', ':')) + '\n')
            fh.flush()
            if i % 25 == 0:
                print(f'  [{i}/{len(todo)}] {kind} {ts}: {len(evs)} ματς · credits {rem}', flush=True)
        except Exception as e:
            print(f'  {kind} {ts}: {type(e).__name__} {e}', flush=True)
            time.sleep(2)
    print(f'τελος · credits {rem}', flush=True)


if __name__ == '__main__':
    main()
