# -*- coding: utf-8 -*-
"""brazil_refresh.py — Καθημερινη ενημερωση data_Brazil_2026.json (FotMob, league id=268).

Incremental: κατεβαζει ΜΟΝΟ τα νεα τελειωμενα ματς της τρεχουσας σεζον (2026).
Αντιγραφη της parse() του brazil_fetch.py χωρις το hardcoded chdir του παλιου laptop.
Τρεχει στο data-refresh workflow. '2026' hardcoded — yearly update.
"""
import urllib.request, json, gzip, time, sys, os
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(os.path.dirname(os.path.abspath(__file__)))

SEASON = '2026'
HDR = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36',
       'Accept': '*/*', 'Referer': 'https://www.fotmob.com/'}


def get(url, tries=4):
    for i in range(tries):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=30).read()
            if raw[:2] == b'\x1f\x8b':
                raw = gzip.decompress(raw)
            return json.loads(raw)
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(1.2 * (i + 1))


def parse(mid):
    d = get(f'https://www.fotmob.com/api/data/matchDetails?matchId={mid}')
    c = d['content']; gen = d['general']; head = d.get('header', {}); teams = head.get('teams', [])
    hs = teams[0].get('score') if len(teams) > 0 else None
    as_ = teams[1].get('score') if len(teams) > 1 else None
    hid = gen['homeTeam']['id']; aid = gen['awayTeam']['id']
    shots = []
    for s in c.get('shotmap', {}).get('shots', []) or []:
        if s.get('isOwnGoal'):
            continue
        shots.append({'tid': s.get('teamId'), 'xg': s.get('expectedGoals'),
                      'min': s.get('min'), 'sit': s.get('situation'), 'goal': s.get('eventType') == 'Goal'})
    reds = []
    for e in c.get('matchFacts', {}).get('events', {}).get('events', []) or []:
        if e.get('type') == 'Card' and e.get('card') in ('Red', 'RedYellow'):
            reds.append({'home': bool(e.get('isHome')), 'min': e.get('time')})
    return {'mid': mid, 'date': gen.get('matchTimeUTC') or gen.get('matchTimeUTCDate'),
            'home': {'name': gen['homeTeam']['name'], 'id': hid},
            'away': {'name': gen['awayTeam']['name'], 'id': aid},
            'hs': hs, 'as': as_, 'shots': shots, 'reds': reds}


if __name__ == '__main__':
    path = f'data_Brazil_{SEASON}.json'
    done = {}
    if os.path.exists(path):
        try:
            done = json.load(open(path, encoding='utf-8'))
        except Exception:
            done = {}
    d = get(f'https://www.fotmob.com/api/data/leagues?id=268&season={SEASON}')
    arr = (d.get('matches', {}).get('allMatches') or d.get('fixtures', {}).get('allMatches') or [])
    ids = [m.get('id') for m in arr
           if m.get('status', {}).get('finished') and not m.get('status', {}).get('cancelled')]
    todo = [m for m in ids if str(m) not in done]
    print(f'[Brazil {SEASON}] τελειωμενα={len(ids)} εχω={len(done)} νεα={len(todo)}', flush=True)
    for i, mid in enumerate(todo):
        try:
            done[str(mid)] = parse(mid)
        except Exception as e:
            print(f'   ! {mid}: {str(e)[:40]}', flush=True)
            continue
        time.sleep(0.15)
    if todo:
        json.dump(done, open(path, 'w', encoding='utf-8'))
    print(f'[Brazil {SEASON}] DONE {len(done)} ματς', flush=True)
