# -*- coding: utf-8 -*-
"""toa_hist_pull.py — Ιστορικα snapshots The Odds API για τα ΠΑΙΓΜΕΝΑ ματς 26/27.

Για καθε μοναδικο KO (EPL/LaLiga/SerieA, ματς που εχουν ηδη παιχτει): ενα historical
snapshot στις KO−24h με Asian Handicap (spreads) Pinnacle + Bet365.
Σκοπος: συγκριση με τις nowgoal γραμμες (Crown/Bet365) — ειναι παρομοιες οι πηγες;

Κοστος: ~10 credits/snapshot (1 market × bookmakers<=10) → ~570 credits συνολο.
Resumable (ξανατρεξιμο δεν ξαναχρεωνει οσα εχουν ηδη κατεβει).
Τρεχει στο GitHub Actions (TOA_KEY secret) μεσω .github/workflows/toa-hist.yml.
Εξοδος: toa_hist_2627.jsonl — {sport, lg, req_ts, snap_ts, events:[...]}.
"""
import sys, os, json, time, datetime
import requests
sys.stdout.reconfigure(encoding='utf-8')

OUT = 'toa_hist_2627.jsonl'
LGS = {'EPL': 'soccer_epl', 'LaLiga': 'soccer_spain_la_liga', 'SerieA': 'soccer_italy_serie_a'}
KEY = os.environ.get('TOA_KEY')
if not KEY:
    raise SystemExit('TOA_KEY δεν βρεθηκε στο environment.')

now = datetime.datetime.now(datetime.timezone.utc)

done = set()
if os.path.exists(OUT):
    for line in open(OUT, encoding='utf-8'):
        try:
            r = json.loads(line)
            done.add((r['sport'], r['req_ts']))
        except Exception:
            pass

todo = []
for lg, sport in LGS.items():
    d = json.load(open(f'data_{lg}_2627.json', encoding='utf-8'))
    kos = set()
    for m in d.values():
        ko = datetime.datetime.strptime(m['date'], '%a, %b %d, %Y, %H:%M UTC').replace(
            tzinfo=datetime.timezone.utc)
        if ko < now:
            kos.add(ko)
    for ko in sorted(kos):
        req_ts = (ko - datetime.timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%SZ')
        if (sport, req_ts) not in done:
            todo.append((lg, sport, req_ts))

print(f'snapshots προς κατεβασμα: {len(todo)} (ηδη: {len(done)})', flush=True)
rem = used = None
fh = open(OUT, 'a', encoding='utf-8')
for lg, sport, req_ts in todo:
    try:
        r = requests.get(f'https://api.the-odds-api.com/v4/historical/sports/{sport}/odds',
                         params=dict(apiKey=KEY, date=req_ts, markets='spreads',
                                     bookmakers='pinnacle,bet365', oddsFormat='decimal'),
                         timeout=45)
        rem = r.headers.get('x-requests-remaining', rem)
        used = r.headers.get('x-requests-used', used)
        if r.status_code != 200:
            print(f'  {lg} {req_ts}: HTTP {r.status_code} {r.text[:120]}', flush=True)
            time.sleep(1.0)
            continue
        js = r.json()
        events = []
        for ev in js.get('data') or []:
            bks = []
            for b in ev.get('bookmakers', []):
                mkts = [m for m in b.get('markets', []) if m.get('key') == 'spreads']
                if mkts:
                    bks.append(dict(key=b['key'], markets=mkts))
            events.append(dict(id=ev.get('id'), commence_time=ev.get('commence_time'),
                               home_team=ev.get('home_team'), away_team=ev.get('away_team'),
                               bookmakers=bks))
        fh.write(json.dumps(dict(sport=sport, lg=lg, req_ts=req_ts,
                                 snap_ts=js.get('timestamp'), events=events),
                            ensure_ascii=False) + '\n')
        fh.flush()
        print(f'  {lg} {req_ts}: snap {js.get("timestamp")} · {len(events)} events', flush=True)
    except Exception as e:
        print(f'  {lg} {req_ts}: {type(e).__name__}', flush=True)
    time.sleep(0.8)
fh.close()
print(f'ΤΕΛΟΣ · used {used} · remaining {rem}', flush=True)
