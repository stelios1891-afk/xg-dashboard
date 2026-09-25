"""
intl_fetch.py — ΕΘΝΙΚΕΣ ΟΜΑΔΕΣ: κατεβασμα ματς (σουτ+xG, σκορ, κοκκινες) ΚΑΙ ενδεκαδων/λεπτων απο FotMob.
(19/9/2026 — βημα 1 του «μοντελου εθνικων»· ιδια μορφη με τα data_{lg}_{sea}.json των λιγκων ωστε να
τρεχουν πανω τους οι ιδιοι builders, + intl_squads.json στη μορφη του europe_squads.json.)

Διοργανωσεις (FotMob ids, σεζον ΜΕ xG στα σουτ — απο 2020/21 και μετα· φιλικα ΧΩΡΙΣ xG, μονο σκορ/ενδεκαδες):
  NationsLeagueA/B/C/D 9806-9809 · WCQ_UEFA 10195 · EUROQ 10607 · EURO 50 · WorldCup 77 ·
  WCQ_CONMEBOL 10199 · CopaAmerica 44 · Friendlies 114 (2025, 2026)
Εξοδος: data_{comp}_{sea}.json  (mid, date, home{name,id}, away{name,id}, hs, as, shots[], reds[], comp, round, neutral?)
        intl_squads.json          ({mid: {h:{t, mv, p:{pid:min}}, a:{...}}})
Resumable (υπαρχοντα mids δεν ξανακατεβαινουν). Χρηση: python intl_fetch.py [comp ...]
"""
import sys, os, json, gzip, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
COMPS = {
    'NationsLeagueA': (9806, ['2020/2021', '2022/2023', '2024/2025', '2026/2027']),
    'NationsLeagueB': (9807, ['2020/2021', '2022/2023', '2024/2025', '2026/2027']),
    'NationsLeagueC': (9808, ['2020/2021', '2022/2023', '2024/2025', '2026/2027']),
    'NationsLeagueD': (9809, ['2020/2021', '2022/2023', '2024/2025', '2026/2027']),
    'WCQ_UEFA':       (10195, ['2021/2022', '2025/2026']),
    'EUROQ':          (10607, ['2022/2023', '2023']),
    'EURO':           (50, ['2020', '2024']),
    'WorldCup':       (77, ['2022', '2026']),
    'WCQ_CONMEBOL':   (10199, ['2020/2022', '2023/2025']),
    'CopaAmerica':    (44, ['2024']),
    'Friendlies':     (114, ['2025', '2026']),
    'AFCON':          (289, ['2023', '2025']),
    'AsianCup':       (290, ['2023']),
    'GoldCup':        (298, ['2023', '2025']),
    'WCQ_AFC':        (10197, ['2023/2025']),
    'WCQ_CAF':        (10196, ['2023/2025']),
    'WCQ_CONCACAF':   (10198, ['2024/2025']),
}
HDR = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36',
       'Accept': '*/*', 'Referer': 'https://www.fotmob.com/'}
SQ_F = 'intl_squads.json'


def get(url, tries=3):
    for i in range(tries):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=25).read()
            return gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(1.5 * (i + 1))


def sea_code(s):
    return s[2:4] + s[7:9] if '/' in s else s                # '2024/2025' -> '2425', '2024' -> '2024'


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


def main(only=None):
    squads = json.load(open(SQ_F, encoding='utf-8')) if os.path.exists(SQ_F) else {}
    t0 = time.time(); n_new = 0
    for comp, (lid, seasons) in COMPS.items():
        if only and comp not in only:
            continue
        for sea in seasons:
            code = sea_code(sea); out_f = f'data_{comp}_{code}.json'
            data = json.load(open(out_f, encoding='utf-8')) if os.path.exists(out_f) else {}
            try:
                d = json.loads(get(f'https://www.fotmob.com/api/data/leagues?id={lid}&season={sea.replace("/", "%2F")}'))
            except Exception as e:
                print(f'  {comp} {sea}: leagues ERR {str(e)[:60]}', flush=True); continue
            am = d.get('fixtures', {}).get('allMatches', [])
            fin = [str(m['id']) for m in am if m.get('status', {}).get('finished') and not m.get('status', {}).get('cancelled')]
            todo = [m for m in fin if m not in data]
            print(f'{comp:15s} {sea:10s}: {len(am)} ματς, {len(fin)} τελειωμενα, {len(todo)} νεα', flush=True)
            if not todo:
                continue
            def work(mid):
                try:
                    return mid, parse(mid, comp)
                except Exception as e:
                    return mid, e
            with ThreadPoolExecutor(max_workers=4) as ex:
                for mid, res in ex.map(work, todo):
                    if isinstance(res, Exception):
                        print(f'    ερρ {mid}: {str(res)[:60]}', flush=True); continue
                    rec, sq = res
                    data[mid] = rec
                    if sq:
                        squads[mid] = sq
                    n_new += 1
            json.dump(data, open(out_f, 'w', encoding='utf-8'), ensure_ascii=False)
            json.dump(squads, open(SQ_F, 'w', encoding='utf-8'), ensure_ascii=False)
            nx = sum(1 for m in data.values() if m.get('has_xg'))
            print(f'    -> {out_f}: {len(data)} ματς, {nx} με xG · squads {len(squads)} · {(time.time()-t0)/60:.1f} min', flush=True)
    print(f'ΤΕΛΟΣ: {n_new} νεα ματς σε {(time.time()-t0)/60:.1f} min', flush=True)
    return n_new


if __name__ == '__main__':
    main(set(sys.argv[1:]) or None)
