# -*- coding: utf-8 -*-
"""
lineup_timer.py — Χρονομετρηση v2: ΠΟΤΕ η 11αδα στο FotMob γινεται ΕΠΙΣΗΜΗ.

Μαθημα απο v1 (1/9): το FotMob σερβιρει lineupType='lastStarting11' (περσινη 11αδα ως
placeholder) ΜΕΡΕΣ πριν το ματς — ο ελεγχος «υπαρχουν 11 starters» πυροδοτουσε αμεσως.
v2: καταγραφουμε ΚΑΘΕ αλλαγη του (lineupType, συνθεση starters) ανα πλευρα, με χρονο.
Ετσι βλεπουμε και την ταξινομια των τυπων (lastStarting11 -> predicted? -> confirmed?)
και το ακριβες λεπτο της επισημης ανακοινωσης.

Ματς: Championship 2/9/2026. Παραθυρο: [KO-120', KO-5'], poll ~20s.
Εξοδος: lineup_timing.jsonl (append).
"""
import sys, json, gzip, time, datetime, urllib.request
sys.stdout.reconfigure(encoding='utf-8')

HDR = {'User-Agent': 'Mozilla/5.0', 'Accept': '*/*', 'Referer': 'https://www.fotmob.com/'}
UTC = datetime.timezone.utc

FIX = [
    (5836799, '2026-09-02T18:45:00Z', 'Millwall - Wrexham'),
    (5836800, '2026-09-02T18:45:00Z', 'QPR - Cardiff'),
    (5836801, '2026-09-02T18:45:00Z', 'West Brom - Charlton'),
    (5836798, '2026-09-02T19:00:00Z', 'Burnley - Middlesbrough'),
]
OUT = 'lineup_timing.jsonl'


def fetch(fid):
    u = f'https://www.fotmob.com/api/data/matchDetails?matchId={fid}'
    d = urllib.request.urlopen(urllib.request.Request(u, headers=HDR), timeout=20).read()
    if d[:2] == b'\x1f\x8b':
        d = gzip.decompress(d)
    return json.loads(d)


def state_of(lu, side):
    t = lu.get('lineupType')
    st = tuple(sorted(p.get('id') for p in ((lu.get(side) or {}).get('starters') or []) if p.get('id')))
    return (t, st)


ko = {f: datetime.datetime.fromisoformat(u.replace('Z', '+00:00')) for f, u, n in FIX}
nm = {f: n for f, u, n in FIX}
first_win = min(ko.values()) - datetime.timedelta(minutes=120)
last_win = max(ko.values()) - datetime.timedelta(minutes=5)
print(f'παραθυρο: {first_win:%H:%M} - {last_win:%H:%M} UTC · {len(FIX)} ματς', flush=True)

prev = {}
fh = open(OUT, 'a', encoding='utf-8')
while True:
    now = datetime.datetime.now(UTC)
    if now > last_win:
        break
    if now < first_win:
        time.sleep(min(120, (first_win - now).total_seconds()))
        continue
    for fid, u, n in FIX:
        if not (ko[fid] - datetime.timedelta(minutes=120) <= now <= ko[fid] - datetime.timedelta(minutes=5)):
            continue
        try:
            j = fetch(fid)
            lu = (j.get('content') or {}).get('lineup') or {}
            for side, k in (('homeTeam', 'h'), ('awayTeam', 'a')):
                cur = state_of(lu, side)
                key = (fid, k)
                if key not in prev:
                    prev[key] = cur
                    t = datetime.datetime.now(UTC)
                    rec = dict(src='fotmob', event='initial', fid=fid, match=nm[fid], side=k,
                               lineupType=cur[0], n_starters=len(cur[1]),
                               seen=t.isoformat(timespec='seconds'), ko=u,
                               mins_before_ko=round((ko[fid] - t).total_seconds() / 60, 2))
                    fh.write(json.dumps(rec, ensure_ascii=False) + '\n'); fh.flush()
                    print(f'ΑΡΧΙΚΟ {nm[fid]} [{k}]: type={cur[0]} n={len(cur[1])}', flush=True)
                elif cur != prev[key]:
                    t = datetime.datetime.now(UTC)
                    changed = sum(1 for p in cur[1] if p not in prev[key][1])
                    rec = dict(src='fotmob', event='change', fid=fid, match=nm[fid], side=k,
                               type_from=prev[key][0], type_to=cur[0],
                               starters_changed=changed, n_starters=len(cur[1]),
                               seen=t.isoformat(timespec='seconds'), ko=u,
                               mins_before_ko=round((ko[fid] - t).total_seconds() / 60, 2))
                    fh.write(json.dumps(rec, ensure_ascii=False) + '\n'); fh.flush()
                    print(f'ΑΛΛΑΓΗ {nm[fid]} [{k}]: {prev[key][0]} -> {cur[0]} ({changed} νεοι) στο -{rec["mins_before_ko"]:.1f}min', flush=True)
                    prev[key] = cur
        except Exception as e:
            print(f'  ερρ {fid}: {type(e).__name__}', flush=True)
    time.sleep(20)
fh.close()
print('ΤΕΛΟΣ χρονομετρησης', flush=True)
