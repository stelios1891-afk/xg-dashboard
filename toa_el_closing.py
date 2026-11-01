# -*- coding: utf-8 -*-
"""toa_el_closing.py — CLOSING αποδοσεις Ευρωλιγκας απο TOA historical (24/9/2026).
Για καθε μοναδικη ωρα τζαμπολ (συγχωνευση 10λ) των σεζον EL_SEASONS: ενα snapshot 5' ΠΡΙΝ
(spreads,totals · region eu · 20 credits). Κρατα τα ματς του snapshot που
ξεκινουν μεσα σε 20' απο τη στιγμη του snapshot (= closing) με ΟΛΑ τα βιβλια.
Resumable (el_closing_done.json)· δικλιδα credits: σταματα αν remaining < FLOOR.
Τρεχει ΜΟΝΟ στο GitHub (TOA_KEY secret). Εξοδος: toa_el_closing.jsonl (μια γραμμη ανα ματς/snapshot)."""
import os, sys, json, datetime as dt
import requests
sys.stdout.reconfigure(encoding='utf-8')
KEY = os.environ.get('TOA_KEY')
if not KEY:
    print('TOA_KEY λειπει (μονο GitHub)'); sys.exit(0)
SEASONS = os.environ.get('EL_SEASONS', 'E2025,E2024,E2023').split(',')
FLOOR = int(os.environ.get('TOA_FLOOR', '25000'))
OUT, DONE = 'toa_el_closing.jsonl', 'el_closing_done.json'
done = set(json.load(open(DONE))) if os.path.exists(DONE) else set()
G = json.load(open('el_games_2020_2025.json', encoding='utf-8'))

times = []
for s in SEASONS:
    ts = sorted({dt.datetime.fromisoformat(r['utc'].replace('Z', '+00:00')) for r in G[s]})
    m = []
    for t in ts:
        if not m or (t - m[-1]).total_seconds() > 600:
            m.append(t)
    times += [(s, t) for t in m]
todo = [(s, t) for s, t in times if t.isoformat() not in done]
print(f'σεζον {SEASONS}: {len(times)} ωρες τζαμπολ · εκκρεμουν {len(todo)} · floor {FLOOR}', flush=True)

n = 0; left = None
with open(OUT, 'a', encoding='utf-8') as fo:
    for s, t in todo:
        snap = (t - dt.timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%SZ')
        try:
            r = requests.get('https://api.the-odds-api.com/v4/historical/sports/basketball_euroleague/odds',
                             params=dict(apiKey=KEY, regions='eu', markets='spreads,totals', oddsFormat='decimal', date=snap), timeout=40)
        except Exception as e:
            print(f'  {snap}: {type(e).__name__}'); continue
        left = int(r.headers.get('x-requests-remaining') or 0)
        if r.status_code != 200:
            print(f'  {snap}: HTTP {r.status_code} {r.text[:120]}');
            if r.status_code in (401, 429): break
            continue
        j = r.json(); ts = j.get('timestamp'); k = 0
        for g in j.get('data') or []:
            ct = dt.datetime.fromisoformat(g['commence_time'].replace('Z', '+00:00'))
            if -600 <= (ct - t).total_seconds() <= 900:     # τα ματς ΑΥΤΗΣ της ωρας (closing)
                fo.write(json.dumps(dict(season=s, tip=t.isoformat(), snap_ts=ts, id=g['id'], commence=g['commence_time'],
                                         home=g['home_team'], away=g['away_team'], bookmakers=g.get('bookmakers', [])),
                                    ensure_ascii=False) + '\n'); k += 1
        done.add(t.isoformat()); n += 1
        if n % 25 == 0:
            fo.flush(); json.dump(sorted(done), open(DONE, 'w'))
            print(f'  {n}/{len(todo)} · credits left {left}', flush=True)
        if left is not None and left < FLOOR:
            print(f'ΔΙΚΛΙΔΑ: credits {left} < {FLOOR} — σταματω'); break
json.dump(sorted(done), open(DONE, 'w'))
print(f'ΤΕΛΟΣ: {n} snapshots τωρα · συνολο done {len(done)} · credits left {left}')
