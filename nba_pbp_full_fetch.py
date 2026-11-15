# -*- coding: utf-8 -*-
"""nba_pbp_full_fetch.py — NBA ΠΛΗΡΕΣ play-by-play + box score ανα παικτη (22/10/2026, Στελιος «ξεκινα … και αποθηκευε απο σημερα για τα
φετινα ματς οτι ενδεχομενως θα χρειαστουμε»). Για δικο μας δεικτη τυπου DARKO/LEBRON (box + «διορθωμενο» on/off, walk-forward).
Διαφορα απο nba_espn_pbp_fetch.py: ΟΛΗ η κανονικη περιοδος (οχι μονο Ιαν-Απρ) · καθε φαση με ΕΙΔΟΣ (σουτ/ριμπαουντ/λαθος/φαουλ …, για κατοχες)
· πληρη στατιστικα box καθε παικτη (ESPN keys).
Εξοδος: nba_pbp_full/pbp_{σεζον}.jsonl (μια γραμμη ανα ματς) · συνεχιζει απο οπου σταματησε. Χρηση: python -I nba_pbp_full_fetch.py [2022 2023 …]
compact() χρησιμοποιειται και απο το live (nba_espn.py) για τα φετινα ματς."""
import os, sys, json, time, datetime as dt, urllib.request
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(ROOT, 'nba_pbp_full')
B = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba'
H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0'}
AB = {'BKN': 'BRK', 'CHA': 'CHO', 'GS': 'GSW', 'NO': 'NOP', 'NY': 'NYK', 'PHX': 'PHO', 'SA': 'SAS', 'UTAH': 'UTA', 'WSH': 'WAS'}
SEASONS = {2022: ('2021-10-19', '2022-04-10'), 2023: ('2022-10-18', '2023-04-09'), 2024: ('2023-10-24', '2024-04-14'),
           2025: ('2024-10-22', '2025-04-13'), 2026: ('2025-10-21', '2026-04-12')}
def get(u):
    for k in range(4):
        try: return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=40).read())
        except Exception:
            if k == 3: raise
            time.sleep(3 + 5 * k)
def clock_s(c):
    try:
        if ':' in c: m, s = c.split(':'); return int(m) * 60 + float(s)
        return float(c)
    except Exception: return None
def compact(d, ev_id):
    """summary ESPN (ηδη κατεβασμενο) → συμπαγες ρεκορ, ή None αν το ματς δεν τελειωσε."""
    comp = d['header']['competitions'][0]
    if comp.get('status', {}).get('type', {}).get('completed') is not True: return None
    teams = {c['id']: (AB.get(c['team']['abbreviation'], c['team']['abbreviation']), c['homeAway']) for c in comp['competitors']}
    box = {}
    for tb in d.get('boxscore', {}).get('players', []):
        t = AB.get(tb['team']['abbreviation'], tb['team']['abbreviation'])
        for st in tb.get('statistics', []):
            keys = st.get('keys') or st.get('names') or []
            for a in st.get('athletes', []):
                ath = a.get('athlete') or {}
                if not ath.get('id'): continue
                box[ath['id']] = [t, ath.get('displayName') or ath.get('shortName') or '', bool(a.get('starter')), bool(a.get('didNotPlay')),
                                           dict(zip(keys, a.get('stats') or []))]
    plays = []
    for p in d.get('plays', []):
        plays.append([p.get('period', {}).get('number'), clock_s(p.get('clock', {}).get('displayValue', '')), p.get('homeScore'), p.get('awayScore'),
                      [x['athlete']['id'] for x in p.get('participants', []) if x.get('athlete')], (p.get('type') or {}).get('text'),
                      1 if p.get('scoringPlay') else 0, 1 if p.get('shootingPlay') else 0, p.get('scoreValue'), (p.get('team') or {}).get('id')])
    return dict(id=ev_id, date=comp.get('date'), stype=(d['header'].get('season') or {}).get('type'),
                teams={v[1]: v[0] for v in teams.values()}, team_ids={k: v[0] for k, v in teams.items()}, box=box, plays=plays)
def main():
    os.makedirs(OUT, exist_ok=True)
    want = [int(x) for x in sys.argv[1:]] or list(SEASONS)
    for s in want:
        a, b = SEASONS[s]
        fn = os.path.join(OUT, f'pbp_{s}.jsonl'); done = set()
        if os.path.exists(fn):
            for ln in open(fn, encoding='utf-8'):
                try: done.add(json.loads(ln)['id'])
                except Exception: pass
        dd = dt.date.fromisoformat(a); end = dt.date.fromisoformat(b); n = 0
        with open(fn, 'a', encoding='utf-8') as fh:
            while dd <= end:
                try: sb = get(f'{B}/scoreboard?dates={dd:%Y%m%d}&limit=50')
                except Exception as e: print('scoreboard σφαλμα', dd, e, flush=True); dd += dt.timedelta(days=1); continue
                for ev in sb.get('events', []):
                    if ev['id'] in done or ev.get('season', {}).get('type') not in (2, None): continue
                    try:
                        c = compact(get(f'{B}/summary?event={ev["id"]}'), ev['id'])
                        if c: fh.write(json.dumps(c, ensure_ascii=False) + '\n'); n += 1; done.add(ev['id'])
                    except Exception as e: print('summary σφαλμα', ev['id'], e, flush=True)
                    time.sleep(0.4)
                fh.flush(); dd += dt.timedelta(days=1)
                if dd.day in (1, 15): print(f'{s}: {dd} · {n} νεα ματς', flush=True)
        print(f'{s}: ΤΕΛΟΣ · {len(done)} ματς', flush=True)
if __name__ == '__main__':
    main()
