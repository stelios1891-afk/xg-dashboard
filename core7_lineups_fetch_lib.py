"""βιβλιοθηκη (10/10/2026): one(mid) ενδεκαδες + player(pid) αξιες — απο core7_lineups_fetch.py / core7_player_values.py."""
"""core7_lineups_fetch.py — ενδεκαδες (FotMob matchDetails) για ΟΛΑ τα ματς των CORE7 5σ (teamgame_inputs_5s_wf.csv, ~12k), 20/9/2026 — τεστ στρωματος αξιας ροστερ στις CORE7. Resumable."""
import sys, os, json, gzip, time, glob, urllib.request
from concurrent.futures import ThreadPoolExecutor
sys.stdout.reconfigure(encoding='utf-8')
HDR = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36', 'Accept': '*/*', 'Referer': 'https://www.fotmob.com/'}
def get(url, tries=3):
    for i in range(tries):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=25).read()
            return gzip.decompress(raw) if raw[:2] == bytes([0x1f, 0x8b]) else raw
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(1.5 * (i + 1))
def minutes_map(j):
    out = {}
    ps = (j.get('content') or {}).get('playerStats') or {}
    if not isinstance(ps, dict):
        return out
    for pid, v in ps.items():
        if not isinstance(v, dict):
            continue
        mins = None
        st = v.get('stats'); blocks = st if isinstance(st, list) else [st]
        for blk in blocks:
            if not isinstance(blk, dict):
                continue
            sk = blk.get('stats') if isinstance(blk.get('stats'), dict) else blk
            mp = sk.get('Minutes played') if isinstance(sk, dict) else None
            if isinstance(mp, dict):
                s = mp.get('stat'); mins = s.get('value') if isinstance(s, dict) else s
            elif isinstance(mp, (int, float)):
                mins = mp
            if mins is not None:
                break
        try:
            out[int(pid)] = int(mins) if mins is not None else 0
        except Exception:
            pass
    return out


def parse(mid, comp):
    d = json.loads(get(f'https://www.fotmob.com/api/data/matchDetails?matchId={mid}'))
    c = d['content']; gen = d['general']; head = d.get('header', {})
    teams = head.get('teams', [])
    hs = teams[0].get('score') if len(teams) > 0 else None
    as_ = teams[1].get('score') if len(teams) > 1 else None
    hid = gen['homeTeam']['id']; aid = gen['awayTeam']['id']
    shots = []
    for s in (c.get('shotmap') or {}).get('shots', []) or []:
        if s.get('isOwnGoal'):
            continue
        shots.append({'tid': s.get('teamId'), 'xg': s.get('expectedGoals'), 'min': s.get('min'),
                      'sit': s.get('situation'), 'goal': s.get('eventType') == 'Goal'})
    reds = []
    for e in ((c.get('matchFacts') or {}).get('events') or {}).get('events', []) or []:
        if e.get('type') == 'Card' and e.get('card') in ('Red', 'RedYellow'):
            reds.append({'home': bool(e.get('isHome')), 'min': e.get('time')})
    info = (c.get('matchFacts') or {}).get('infoBox') or {}
    stad = info.get('Stadium') or {}
    rec = {'mid': str(mid), 'date': gen.get('matchTimeUTC') or gen.get('matchTimeUTCDate'),
           'home': {'name': gen['homeTeam']['name'], 'id': hid}, 'away': {'name': gen['awayTeam']['name'], 'id': aid},
           'hs': hs, 'as': as_, 'shots': shots, 'reds': reds, 'comp': comp,
           'round': gen.get('leagueRoundName') or gen.get('matchRound'),
           'stadium': (stad.get('name') if isinstance(stad, dict) else stad), 'country': gen.get('countryCode'),
           'has_xg': any(s['xg'] is not None for s in shots)}
    lu = c.get('lineup') or {}; mins = minutes_map(d); sq = {}
    for side, k in (('homeTeam', 'h'), ('awayTeam', 'a')):
        t = lu.get(side) or {}; ids = []
        for grp in ('starters', 'subs'):
            for p in (t.get(grp) or []):
                if p.get('id'):
                    ids.append(int(p['id']))
        if ids:
            sq[k] = {'t': t.get('id'), 'mv': t.get('totalStarterMarketValue'),
                     'st': [int(p['id']) for p in (t.get('starters') or []) if p.get('id')],
                     'p': {str(pid): mins.get(pid, 0) for pid in ids}}
    return rec, (sq or None)



def one(mid):
    try:
        d = json.loads(get(f'https://www.fotmob.com/api/data/matchDetails?matchId={mid}'))
        lu = (d.get('content') or {}).get('lineup') or {}; mins = minutes_map(d); sq = {}
        for side, k in (('homeTeam', 'h'), ('awayTeam', 'a')):
            t = lu.get(side) or {}; ids = []
            for grp in ('starters', 'subs'):
                for p in (t.get(grp) or []):
                    if p.get('id'):
                        ids.append(int(p['id']))
            if ids:
                sq[k] = {'t': t.get('id'), 'mv': t.get('totalStarterMarketValue'), 'st': [int(p['id']) for p in (t.get('starters') or []) if p.get('id')], 'p': {str(pid): mins.get(pid, 0) for pid in ids}}
        return mid, (sq or None)
    except Exception:
        return mid, None


def get_json(u, tries=3):
    for i in range(tries):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(u, headers=HDR), timeout=25).read()
            return json.loads(gzip.decompress(raw) if raw[:2] == bytes([0x1f, 0x8b]) else raw)
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(1.5 * (i + 1))


def player(pid):
    try:
        d = get_json(f'https://www.fotmob.com/api/data/playerData?id={pid}')
        info = {it.get('title'): it.get('value') for it in (d.get('playerInformation') or []) if isinstance(it, dict)}
        mv = (info.get('Market value') or {}).get('numberValue')
        hist = [[v.get('date', '')[:10], v.get('value')] for v in ((d.get('marketValues') or {}).get('values') or []) if v.get('value') is not None]
        pos = ((d.get('positionDescription') or {}).get('primaryPosition') or {}).get('label')
        return pid, dict(name=d.get('name'), pos=pos, mv_now=mv, team=(d.get('primaryTeam') or {}).get('teamName'), hist=hist)
    except Exception:
        return pid, None


