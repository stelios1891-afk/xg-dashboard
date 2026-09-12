# -*- coding: utf-8 -*-
"""toa_pin_vig.py — ONE-OFF (εντολη 12/9): γκανιοτα PINNACLE (AH spreads) ανα ωρα
προ σεντρας, στις πρωτες αγωνιστικες EPL 2627 (30 ματς, 20 KO).

Historical snapshots The Odds API στα: KO −72h/−48h/−24h/−12h/−6h/−2h/−5min.
Dedupe ανα λεπτο (~137 αιτηματα × 10 credits ≈ 1.4k). Γκανιοτα = 1/o1 + 1/o2 − 1
στο κυριο spread της Pinnacle. Τρεχει στο GitHub Actions (TOA_KEY) → commit
toa_pin_vig_out.txt + toa_pin_vig.jsonl (raw). Τοπικα χωρις κλειδι: graceful exit.
"""
import sys, os, json, time, datetime
import requests
sys.stdout.reconfigure(encoding='utf-8')

KEY = os.environ.get('TOA_KEY')
if not KEY:
    print('TOA_KEY δεν υπαρχει (τοπικο τρεξιμο;) — τιποτα δεν εγινε')
    raise SystemExit(0)

SPORT = 'soccer_epl'
OFFS = [('-72h', 72.0), ('-48h', 48.0), ('-24h', 24.0), ('-12h', 12.0),
        ('-6h', 6.0), ('-2h', 2.0), ('closing(-5m)', 5 / 60)]
RAW = 'toa_pin_vig.jsonl'
OUT = 'toa_pin_vig_out.txt'
MAX_REQ = 220   # φρενο κοστους

d = json.load(open('data_EPL_2627.json', encoding='utf-8'))
matches = []
for mid, m in d.items():
    ko = datetime.datetime.strptime(m['date'], '%a, %b %d, %Y, %H:%M UTC').replace(
        tzinfo=datetime.timezone.utc)
    matches.append(dict(mid=mid, ko=ko, home=m['home']['name'], away=m['away']['name']))
print(f'ματς: {len(matches)}', flush=True)

# dedup αιτηματα ανα λεπτο
req_ts = {}
for m in matches:
    for lbl, h in OFFS:
        t = (m['ko'] - datetime.timedelta(hours=h)).replace(second=0, microsecond=0)
        req_ts.setdefault(t, None)
req_list = sorted(req_ts)[:MAX_REQ]
print(f'snapshots: {len(req_list)} (×10 credits)', flush=True)

# ηδη κατεβασμενα (resume)
done = {}
if os.path.exists(RAW):
    for line in open(RAW, encoding='utf-8'):
        try:
            r = json.loads(line)
            done[r['req_ts']] = r
        except Exception:
            pass

fh = open(RAW, 'a', encoding='utf-8')
rem = None
for t in req_list:
    ts = t.strftime('%Y-%m-%dT%H:%M:%SZ')
    if ts in done:
        continue
    try:
        r = requests.get(f'https://api.the-odds-api.com/v4/historical/sports/{SPORT}/odds',
                         params=dict(apiKey=KEY, date=ts, markets='spreads',
                                     bookmakers='pinnacle', oddsFormat='decimal'),
                         timeout=45)
        rem = r.headers.get('x-requests-remaining', rem)
        if r.status_code != 200:
            print(f'  {ts}: HTTP {r.status_code}', flush=True)
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
        rec = dict(req_ts=ts, snap=js.get('timestamp'), events=evs)
        done[ts] = rec
        fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
        fh.flush()
    except Exception as e:
        print(f'  {ts}: {type(e).__name__}', flush=True)
    time.sleep(0.4)
fh.close()
print(f'κατεβηκαν {len(done)} snapshots · remaining {rem}', flush=True)

# ---- αντιστοιχιση ματς↔events (TOA ονοματα ~ FotMob: χαλαρο ταιριασμα σε λεξεις) ----
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

lines = [f'PINNACLE γκανιοτα (κυριο AH spread) — EPL 2627, πρωτες αγωνιστικες ({len(matches)} ματς)']
agg = {lbl: [] for lbl, _ in OFFS}
for m in matches:
    for lbl, h in OFFS:
        t = (m['ko'] - datetime.timedelta(hours=h)).replace(second=0, microsecond=0)
        rec = done.get(t.strftime('%Y-%m-%dT%H:%M:%SZ'))
        if not rec:
            continue
        e = match_ev(rec['events'], m['home'], m['away'], m['ko'])
        if not e:
            continue
        vig = 1 / e['o1'] + 1 / e['o2'] - 1
        agg[lbl].append(vig)

lines.append(f'{"offset":>13s} {"n":>4s} {"μεση γκανιοτα":>14s}')
base = (sum(agg['closing(-5m)']) / len(agg['closing(-5m)'])) if agg['closing(-5m)'] else float('nan')
for lbl, _ in OFFS:
    v = agg[lbl]
    if not v:
        lines.append(f'{lbl:>13s}    0        -')
        continue
    mu = sum(v) / len(v)
    lines.append(f'{lbl:>13s} {len(v):4d} {100*mu:13.2f}%  (Δ vs closing {100*(mu-base):+.2f}pp)')
open(OUT, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
