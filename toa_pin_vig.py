# -*- coding: utf-8 -*-
"""toa_pin_vig.py — v2 (εντολη 12/9): γκανιοτα PINNACLE (κυριο AH spread) ανα ωρα
προ σεντρας, ΟΛΟ το CORE7, πρωτες αγωνιστικες 2627.

Offsets: −24h/−12h/−6h/−2h/−5min (ο Στελιος: «απο 24 και μετα» — η EPL εδειξε φλατ 2.5%
πιο πριν). EPL: επαναχρησιμοποιει τα ηδη κατεβασμενα snapshots (v1). Resume-aware.
Κοστος νεων: ~860 αιτηματα × 10 ≈ 8.6k credits. Output: toa_pin_vig_out.txt + raw jsonl.
Τρεχει στο GitHub Actions (TOA_KEY)· τοπικα χωρις κλειδι: graceful exit.
"""
import sys, os, json, time, datetime
import requests
sys.stdout.reconfigure(encoding='utf-8')

KEY = os.environ.get('TOA_KEY')
if not KEY:
    print('TOA_KEY δεν υπαρχει (τοπικο τρεξιμο;) — τιποτα δεν εγινε')
    raise SystemExit(0)

SPORTS = {
    'EPL': 'soccer_epl',
    'LaLiga': 'soccer_spain_la_liga',
    'SerieA': 'soccer_italy_serie_a',
    'Bundesliga': 'soccer_germany_bundesliga',
    'Ligue1': 'soccer_france_ligue_one',
    'Eredivisie': 'soccer_netherlands_eredivisie',
    'PrimeiraLiga': 'soccer_portugal_primeira_liga',
}
OFFS = [('-24h', 24.0), ('-12h', 12.0), ('-6h', 6.0), ('-2h', 2.0), ('closing(-5m)', 5 / 60)]
RAW = 'toa_pin_vig.jsonl'
OUT = 'toa_pin_vig_out.txt'
MAX_REQ = 950   # φρενο κοστους (συνολικο, νεα αιτηματα)

MATCHES = {}
for lg in SPORTS:
    fn = f'data_{lg}_2627.json'
    if not os.path.exists(fn):
        continue
    ms = []
    for mid, m in json.load(open(fn, encoding='utf-8')).items():
        ko = datetime.datetime.strptime(m['date'], '%a, %b %d, %Y, %H:%M UTC').replace(
            tzinfo=datetime.timezone.utc)
        ms.append(dict(mid=mid, ko=ko, home=m['home']['name'], away=m['away']['name']))
    MATCHES[lg] = ms
    print(f'{lg}: {len(ms)} ματς', flush=True)

# ηδη κατεβασμενα (v1 EPL records: χωρις πεδιο lg => EPL)
done = {}
if os.path.exists(RAW):
    for line in open(RAW, encoding='utf-8'):
        try:
            r = json.loads(line)
            done[(r.get('lg', 'EPL'), r['req_ts'])] = r
        except Exception:
            pass
print(f'ηδη στο αρχειο: {len(done)} snapshots', flush=True)

todo = []
for lg, ms in MATCHES.items():
    seen = set()
    for m in ms:
        for lbl, h in OFFS:
            t = (m['ko'] - datetime.timedelta(hours=h)).replace(second=0, microsecond=0)
            ts = t.strftime('%Y-%m-%dT%H:%M:%SZ')
            if (lg, ts) in done or (lg, ts) in seen:
                continue
            seen.add((lg, ts))
            todo.append((lg, ts))
todo = todo[:MAX_REQ]
print(f'νεα αιτηματα: {len(todo)} (×10 credits)', flush=True)

fh = open(RAW, 'a', encoding='utf-8')
rem = None
for k, (lg, ts) in enumerate(todo):
    try:
        r = requests.get(f'https://api.the-odds-api.com/v4/historical/sports/{SPORTS[lg]}/odds',
                         params=dict(apiKey=KEY, date=ts, markets='spreads',
                                     bookmakers='pinnacle', oddsFormat='decimal'),
                         timeout=45)
        rem = r.headers.get('x-requests-remaining', rem)
        if r.status_code != 200:
            print(f'  {lg} {ts}: HTTP {r.status_code}', flush=True)
            time.sleep(0.6)
            continue
        js = r.json()
        evs = []
        for ev in js.get('data') or []:
            for b in ev.get('bookmakers', []):
                if b.get('key') != 'pinnacle':
                    continue
                for mk in b.get('markets', []):
                    if mk.get('key') != 'spreads':
                        continue
                    oc = mk.get('outcomes') or []
                    if len(oc) == 2 and all(o.get('price') for o in oc):
                        evs.append(dict(home=ev.get('home_team'), away=ev.get('away_team'),
                                        ct=ev.get('commence_time'),
                                        pt=oc[0].get('point'),
                                        o1=oc[0]['price'], o2=oc[1]['price']))
        rec = dict(lg=lg, req_ts=ts, snap=js.get('timestamp'), events=evs)
        done[(lg, ts)] = rec
        fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
        fh.flush()
        if (k + 1) % 100 == 0:
            print(f'  ... {k+1}/{len(todo)} (remaining {rem})', flush=True)
    except Exception as e:
        print(f'  {lg} {ts}: {type(e).__name__}', flush=True)
    time.sleep(0.35)
fh.close()
print(f'συνολο snapshots: {len(done)} · remaining {rem}', flush=True)


def norm(s):
    return {w for w in str(s).lower().replace('&', ' ').split() if len(w) > 2}


def match_ev(evs, home, away, ko):
    hn, an = norm(home), norm(away)
    best = None; bs = 0
    for e in evs:
        try:
            ct = datetime.datetime.fromisoformat(str(e['ct']).replace('Z', '+00:00'))
        except Exception:
            continue
        if abs((ct - ko).total_seconds()) > 3600:
            continue
        sc = len(hn & norm(e['home'])) + len(an & norm(e['away']))
        if sc > bs:
            bs = sc; best = e
    return best if bs >= 1 else None

lines = ['PINNACLE γκανιοτα (κυριο AH spread) ανα ωρα — CORE7, πρωτες αγωνιστικες 2627']
pool = {lbl: [] for lbl, _ in OFFS}
for lg, ms in MATCHES.items():
    agg = {lbl: [] for lbl, _ in OFFS}
    for m in ms:
        for lbl, h in OFFS:
            t = (m['ko'] - datetime.timedelta(hours=h)).replace(second=0, microsecond=0)
            rec = done.get((lg, t.strftime('%Y-%m-%dT%H:%M:%SZ')))
            if not rec:
                continue
            e = match_ev(rec['events'], m['home'], m['away'], m['ko'])
            if not e:
                continue
            vig = 1 / e['o1'] + 1 / e['o2'] - 1
            agg[lbl].append(vig)
            pool[lbl].append(vig)
    cl = agg['closing(-5m)']
    base = sum(cl) / len(cl) if cl else float('nan')
    row = f'{lg:>13s}: '
    for lbl, _ in OFFS:
        v = agg[lbl]
        row += f'{lbl} {"-" if not v else f"{100*sum(v)/len(v):.2f}%"} (n{len(v)})  '
    lines.append(row)
lines.append('')
cl = pool['closing(-5m)']
base = sum(cl) / len(cl) if cl else float('nan')
lines.append('ΣΥΝΟΛΟ CORE7:')
for lbl, _ in OFFS:
    v = pool[lbl]
    if not v:
        continue
    mu = sum(v) / len(v)
    lines.append(f'  {lbl:>13s} n={len(v):3d}  {100*mu:.2f}%  (Δ vs closing {100*(mu-base):+.2f}pp)')
open(OUT, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
