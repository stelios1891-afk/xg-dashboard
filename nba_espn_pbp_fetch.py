# -*- coding: utf-8 -*-
"""nba_espn_pbp_fetch.py — ESPN play-by-play (αλλαγες παικτων, πεντάδες) για ιστορικα ματς NBA (21/10/2026, Στελιος: «βλεποντας τις
5αδες τους ειδικα στην 4η περιοδο μπορουμε να καταλαβουμε ποια ομαδα θελει νικες — ομαδες που θελουν να χασουν αφηνουν βασικους στον παγκο»).
Για καθε μερα (Ιανουαριος-Απριλιος, σεζον 2021-22…2025-26): scoreboard ESPN → καθε ματς κανονικης περιοδου → summary → ΣΥΜΠΑΓΕΣ:
  ομαδες, βασικοι (starter), λεπτα ανα παικτη (box), και καθε «play» με περιοδο, ρολοι (δευτ. που απομενουν), σκορ, συμμετεχοντες, αν ειναι αλλαγη.
Εξοδος: nba_pbp/pbp_{σεζον}.jsonl (μια γραμμη ανα ματς) · συνεχιζει απο οπου σταματησε (done). Χρηση: python -I nba_espn_pbp_fetch.py"""
import os, sys, json, time, datetime as dt, urllib.request
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(ROOT, 'nba_pbp'); os.makedirs(OUT, exist_ok=True)
B = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba'
H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0'}
AB = {'BKN': 'BRK', 'CHA': 'CHO', 'GS': 'GSW', 'NO': 'NOP', 'NY': 'NYK', 'PHX': 'PHO', 'SA': 'SAS', 'UTAH': 'UTA', 'WSH': 'WAS'}
SEASONS = {2022: ('2022-01-01', '2022-04-10'), 2023: ('2023-01-01', '2023-04-09'), 2024: ('2024-01-01', '2024-04-14'),
           2025: ('2025-01-01', '2025-04-13'), 2026: ('2026-01-01', '2026-04-12')}
def get(u):
    for k in range(4):
        try: return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=40).read())
        except Exception as e:
            if k == 3: raise
            time.sleep(3 + 5 * k)
def clock_s(c):
    try:
        if ':' in c: m, s = c.split(':'); return int(m) * 60 + float(s)
        return float(c)
    except Exception: return None
def compact(ev_id):
    d = get(f'{B}/summary?event={ev_id}')
    comp = d['header']['competitions'][0]
    if comp.get('status', {}).get('type', {}).get('completed') is not True: return None
    teams = {c['id']: (AB.get(c['team']['abbreviation'], c['team']['abbreviation']), c['homeAway']) for c in comp['competitors']}
    box = {}
    for tb in d['boxscore'].get('players', []):
        t = AB.get(tb['team']['abbreviation'], tb['team']['abbreviation']); st = tb['statistics'][0]
        lab = st.get('names') or st.get('labels'); imin = lab.index('MIN') if 'MIN' in lab else 0
        for a in st.get('athletes', []):
            mn = a.get('stats') or []
            box[a['athlete']['id']] = [t, a['athlete']['displayName'], bool(a.get('starter')), (mn[imin] if mn else '0') or '0', bool(a.get('didNotPlay'))]
    plays = []
    for p in d.get('plays', []):
        txt = p.get('text', '')
        plays.append([p.get('period', {}).get('number'), clock_s(p.get('clock', {}).get('displayValue', '')), p.get('homeScore'), p.get('awayScore'),
                      [x['athlete']['id'] for x in p.get('participants', []) if x.get('athlete')], 1 if 'enters the game' in txt else 0,
                      (p.get('team') or {}).get('id')])
    return dict(id=ev_id, date=comp.get('date'), teams={v[1]: v[0] for v in teams.values()}, team_ids={k: v[0] for k, v in teams.items()}, box=box, plays=plays)
def main():
    for s, (a, b) in SEASONS.items():
        fn = os.path.join(OUT, f'pbp_{s}.jsonl'); done = set()
        if os.path.exists(fn):
            for ln in open(fn, encoding='utf-8'):
                try: done.add(json.loads(ln)['id'])
                except Exception: pass
        dd = dt.date.fromisoformat(a); end = dt.date.fromisoformat(b); n = 0
        with open(fn, 'a', encoding='utf-8') as fh:
            while dd <= end:
                try: sb = get(f'{B}/scoreboard?dates={dd:%Y%m%d}')
                except Exception as e: print('scoreboard σφαλμα', dd, e, flush=True); dd += dt.timedelta(days=1); continue
                for ev in sb.get('events', []):
                    if ev['id'] in done or ev.get('season', {}).get('type') not in (2, None): continue
                    try:
                        c = compact(ev['id'])
                        if c: fh.write(json.dumps(c, ensure_ascii=False) + '\n'); n += 1; done.add(ev['id'])
                    except Exception as e: print('summary σφαλμα', ev['id'], e, flush=True)
                    time.sleep(0.4)
                fh.flush(); dd += dt.timedelta(days=1)
                if dd.day == 1 or dd.day == 15: print(f'{s}: {dd} · {n} νεα ματς', flush=True)
        print(f'{s}: ΤΕΛΟΣ · {len(done)} ματς', flush=True)
if __name__ == '__main__':
    main()
