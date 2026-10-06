# -*- coding: utf-8 -*-
"""nba_espn.py — NBA LIVE ΔΕΔΟΜΕΝΑ απο τη δημοσια υπηρεσια του ESPN (6/10/2026, Στελιος «φτιαξε τη μηχανη»).
  • ματς (προετοιμασια / κανονικη / πλει-οφ) απο 1/10 της τρεχουσας σεζον: σκορ, box ομαδας (FGA, 3P, FT, OREB, TOV, παρατασεις), λεπτα καθε παικτη
    → nba_espn_games.json {event id: {...}} (σταδιακα — ξανακατεβαζει μονο οσα λειπουν)
  • λιστα τραυματιων (ESPN injuries) → nba_injuries.json {fetched, teams: {ομαδα: [[ονομα, κατασταση], ...]}}
Κωδικοι ομαδων = Basketball-Reference (ιδιοι με nba_gamelogs.csv). Χρηση: python nba_espn.py [--days N]"""
import sys, json, time, datetime as dt, urllib.request
sys.stdout.reconfigure(encoding='utf-8')
H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0'}
B = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba'
AB = {'BKN': 'BRK', 'CHA': 'CHO', 'GS': 'GSW', 'NO': 'NOP', 'NY': 'NYK', 'PHX': 'PHO', 'SA': 'SAS', 'UTAH': 'UTA', 'WSH': 'WAS'}
code = lambda a: AB.get(a, a)
TEAMNAME = {'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BRK', 'Charlotte Hornets': 'CHO', 'Chicago Bulls': 'CHI', 'Cleveland Cavaliers': 'CLE',
            'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN', 'Detroit Pistons': 'DET', 'Golden State Warriors': 'GSW', 'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND',
            'LA Clippers': 'LAC', 'Los Angeles Clippers': 'LAC', 'Los Angeles Lakers': 'LAL', 'Memphis Grizzlies': 'MEM', 'Miami Heat': 'MIA', 'Milwaukee Bucks': 'MIL',
            'Minnesota Timberwolves': 'MIN', 'New Orleans Pelicans': 'NOP', 'New York Knicks': 'NYK', 'Oklahoma City Thunder': 'OKC', 'Orlando Magic': 'ORL',
            'Philadelphia 76ers': 'PHI', 'Phoenix Suns': 'PHO', 'Portland Trail Blazers': 'POR', 'Sacramento Kings': 'SAC', 'San Antonio Spurs': 'SAS',
            'Toronto Raptors': 'TOR', 'Utah Jazz': 'UTA', 'Washington Wizards': 'WAS'}
SEASON_START = dt.date(2026, 10, 1)          # ετησια ενημερωση (οπως '2627' αλλου)
F_G, F_I = 'nba_espn_games.json', 'nba_injuries.json'

def get(u):
    for k in range(3):
        try: return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=40).read())
        except Exception as e:
            if k == 2: raise
            time.sleep(3)

def us_date(iso):
    t = dt.datetime.fromisoformat(iso.replace('Z', '+00:00'))
    try:
        from zoneinfo import ZoneInfo; return t.astimezone(ZoneInfo('America/New_York')).date().isoformat()
    except Exception:
        return (t - dt.timedelta(hours=4)).date().isoformat()

def parse(ev, s):
    comp = ev['competitions'][0]; st = comp['status']['type']
    side = {c['homeAway']: c for c in comp['competitors']}
    rec = dict(id=ev['id'], utc=ev['date'], date=us_date(ev['date']), stype=int(ev['season']['type']), neutral=bool(comp.get('neutralSite')),
               home=code(side['home']['team']['abbreviation']), away=code(side['away']['team']['abbreviation']),
               hs=int(side['home']['score']), as_=int(side['away']['score']), ot=max(0, int(comp['status'].get('period', 4)) - 4), box={}, players={})
    for bt in s['boxscore']['teams']:
        t = code(bt['team']['abbreviation']); v = {x['name']: x['displayValue'] for x in bt['statistics']}
        def mk(k):
            a, b = v[k].split('-'); return int(a), int(b)
        fgm, fga = mk('fieldGoalsMade-fieldGoalsAttempted'); m3, a3 = mk('threePointFieldGoalsMade-threePointFieldGoalsAttempted'); ftm, fta = mk('freeThrowsMade-freeThrowsAttempted')
        rec['box'][t] = dict(fga=fga, fgm=fgm, fg3=m3, fg3a=a3, ft=ftm, fta=fta, orb=int(v.get('offensiveRebounds', 0)), tov=int(v.get('turnovers', v.get('totalTurnovers', 0))))
    for pl in s['boxscore'].get('players', []):
        t = code(pl['team']['abbreviation']); L = []
        for blk in pl.get('statistics', []):
            ki = blk['keys'].index('minutes') if 'minutes' in blk.get('keys', []) else None
            for a in blk.get('athletes', []):
                mn = 0
                if ki is not None and a.get('stats') and not a.get('didNotPlay'):
                    try: mn = int(float(a['stats'][ki] or 0))
                    except Exception: mn = 0
                L.append([a['athlete']['id'], a['athlete']['displayName'], mn])
        rec['players'][t] = L
    return rec if st.get('completed') else None

def main():
    days = int(sys.argv[sys.argv.index('--days') + 1]) if '--days' in sys.argv else None
    try: GM = json.load(open(F_G, encoding='utf-8'))
    except Exception: GM = {}
    today = dt.datetime.now(dt.timezone.utc).date()
    d0 = SEASON_START
    if GM and days is None:
        d0 = max(SEASON_START, dt.date.fromisoformat(max(g['date'] for g in GM.values())) - dt.timedelta(days=2))
    elif days is not None:
        d0 = max(SEASON_START, today - dt.timedelta(days=days))
    new = 0; d = d0
    while d <= today:
        try: sb = get(f'{B}/scoreboard?dates={d:%Y%m%d}&limit=50')
        except Exception as e: print('scoreboard σφαλμα', d, e); d += dt.timedelta(days=1); continue
        for ev in sb.get('events', []):
            if ev['id'] in GM or not ev['competitions'][0]['status']['type'].get('completed'): continue
            try:
                r = parse(ev, get(f'{B}/summary?event={ev["id"]}'))
                if r: GM[ev['id']] = r; new += 1
            except Exception as e: print('summary σφαλμα', ev['id'], e)
        d += dt.timedelta(days=1)
    json.dump(GM, open(F_G, 'w', encoding='utf-8'), ensure_ascii=False)
    c = {1: 0, 2: 0, 3: 0}
    for g in GM.values(): c[g['stype']] = c.get(g['stype'], 0) + 1
    print(f'ESPN: {new} νεα ματς · συνολο {len(GM)} (προετοιμασια {c.get(1, 0)} · κανονικη {c.get(2, 0)} · πλει-οφ {c.get(3, 0)})')
    try:
        inj = get(f'{B}/injuries'); T = {}
        for t in inj.get('injuries', []):
            nm = t.get('displayName', '')
            T[nm] = dict(code=TEAMNAME.get(nm), players=[[x['athlete']['displayName'], x.get('status'), (x.get('type') or {}).get('description')] for x in t.get('injuries', [])])
        json.dump(dict(fetched=dt.datetime.now(dt.timezone.utc).isoformat(timespec='minutes'), teams=T), open(F_I, 'w', encoding='utf-8'), ensure_ascii=False)
        print(f'τραυματιες: {sum(len(v["players"]) for v in T.values())} παικτες σε {len(T)} ομαδες')
    except Exception as e:
        print('injuries σφαλμα', e)

if __name__ == '__main__':
    main()
