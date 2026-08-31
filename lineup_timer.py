# -*- coding: utf-8 -*-
"""
lineup_timer.py — Χρονομετρηση: ποτε εμφανιζονται οι ανακοινωμενες 11αδες στο FotMob.
Ματς: Championship 1/9/2026. Polling ανα ~25s στο παραθυρο [KO-100', KO-25'].
Εξοδος: lineup_timing.jsonl (μια γραμμη ανα πλευρα οταν πρωτοεμφανιστει 11αδα).
"""
import sys, os, json, time, gzip, urllib.request, datetime
sys.stdout.reconfigure(encoding='utf-8')
HDR = {'User-Agent': 'Mozilla/5.0', 'Accept': '*/*', 'Referer': 'https://www.fotmob.com/'}
UTC = datetime.timezone.utc

FIX = [
    (5836791, '2026-09-01T18:45:00Z', 'Lincoln - Blackburn'),
    (5836792, '2026-09-01T18:45:00Z', 'Portsmouth - Derby'),
    (5836793, '2026-09-01T18:45:00Z', 'Preston - Bristol City'),
    (5836794, '2026-09-01T18:45:00Z', 'Sheffield Utd - Bolton'),
    (5836796, '2026-09-01T18:45:00Z', 'Swansea - Watford'),
    (5836797, '2026-09-01T18:45:00Z', 'West Ham - Wolves'),
    (5836790, '2026-09-01T19:00:00Z', 'Birmingham - Southampton'),
    (5836795, '2026-09-01T19:00:00Z', 'Stoke - Norwich'),
]
OUT = 'lineup_timing.jsonl'


def fetch(fid):
    raw = urllib.request.urlopen(urllib.request.Request(
        f'https://www.fotmob.com/api/data/matchDetails?matchId={fid}', headers=HDR), timeout=20).read()
    if raw[:2] == b'\x1f\x8b':
        raw = gzip.decompress(raw)
    return json.loads(raw)


ko = {fid: datetime.datetime.fromisoformat(u.replace('Z', '+00:00')) for fid, u, _ in FIX}
nm = {fid: n for fid, _, n in FIX}
seen = {}
if os.path.exists(OUT):
    for line in open(OUT, encoding='utf-8'):
        try:
            r = json.loads(line)
            seen[(r['fid'], r['side'])] = True
        except Exception:
            pass

first_win = min(ko.values()) - datetime.timedelta(minutes=100)
last_end = max(ko.values()) - datetime.timedelta(minutes=20)
print(f'παραθυρο: {first_win:%H:%M} - {last_end:%H:%M} UTC · {len(FIX)} ματς', flush=True)

fh = open(OUT, 'a', encoding='utf-8')
while datetime.datetime.now(UTC) < last_end:
    now = datetime.datetime.now(UTC)
    if now < first_win:
        time.sleep(min(120, (first_win - now).total_seconds()))
        continue
    for fid, u, n in FIX:
        if (fid, 'h') in seen and (fid, 'a') in seen:
            continue
        if not (ko[fid] - datetime.timedelta(minutes=100) <= now <= ko[fid]):
            continue
        try:
            j = fetch(fid)
        except Exception as e:
            print(f'  ερρ {fid}: {type(e).__name__}', flush=True)
            continue
        lu = (j.get('content') or {}).get('lineup') or {}
        for side, k in (('homeTeam', 'h'), ('awayTeam', 'a')):
            if (fid, k) in seen:
                continue
            st = [p for p in ((lu.get(side) or {}).get('starters') or []) if p.get('id')]
            if len(st) == 11:
                t = datetime.datetime.now(UTC)
                mins_before = (ko[fid] - t).total_seconds() / 60
                rec = dict(fid=fid, match=nm[fid], side=k, seen=t.isoformat(timespec='seconds'),
                           ko=u, mins_before_ko=round(mins_before, 2))
                fh.write(json.dumps(rec, ensure_ascii=False) + '\n'); fh.flush()
                seen[(fid, k)] = True
                print(f'ΕΝΔΕΚΑΔΑ: {nm[fid]} [{k}] στο -{mins_before:.1f}min', flush=True)
        time.sleep(1.2)
    time.sleep(22)
fh.close()
print('ΤΕΛΟΣ χρονομετρησης', flush=True)
