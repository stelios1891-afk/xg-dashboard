# -*- coding: utf-8 -*-
"""
euro_refresh.py — ΕΒΔΟΜΑΔΙΑΙΑ ανανεωση δεδομενων του ευρωπαικου engine (εντολη Στελιου 10/9).

Τρια sequential βηματα (μια λιγκα/χωρα αποτυγχανει -> συνεχιζει, αναφερει):
  1. FotMob: data_{lg}_{sea}.json για τις 30 ευρω-λιγκες (φετινη σεζον 2627 / 2026
     ημερολογιακες) — ιδια μηχανη με dl.py/mgr_existing_2627_fetch.py (finished ids απο
     το leagues endpoint, parse matchDetails, missing + re-check τελευταιων ημερων για
     αναθεωρησεις Opta). ΔΕΝ αγγιζει CORE7 (καθημερινο data-refresh.yml) ουτε
     MLS/Brazil/Bundesliga2.
  2. Griffis (Ben): μονο οι 9 λιγκες, ΜΟΝΟ φετινες σεζον (2627/2026) απο τα raw CSV του
     Post_Match_App -> replace per league-season στο griffis_matches.csv (idempotent).
     ΔΕΝ αγγιζει το griffis_name_map.json (εχει χειροκινητες διορθωσεις).
  3. ClubElo: clubelo_current.csv απο τις σελιδες χωρων clubelo.com/{CC} (Vega JSON με
     Elo/Level/Federation ανα συλλογο) — το api.clubelo.com ειναι κατω απο 2/9/2026.
     Guard: αν αποτυχουν πολλες χωρες, το παλιο αρχειο ΔΕΝ πειραζεται.

Μετα απο αυτο τρεχει (ξεχωριστα) το euro_live_projections.py για φρεσκο euro_projections.json.
Read-only σε ολα τα αλλα αρχεια. '2627'/'2026' αλλαζουν μια φορα/χρονο (νεα σεζον).
"""
import csv
import gzip
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone, date

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

T0 = time.time()
TODAY = datetime.now(timezone.utc).replace(tzinfo=None)

# ---------------- ρυθμισεις ----------------
SEA_SPLIT = '2627'   # χειμωνιατικες λιγκες (μια φορα/χρονο η αλλαγη)
SEA_CAL = '2026'     # ημερολογιακες λιγκες
RECHECK_DAYS = 8     # εβδομαδιαιο τρεξιμο: ξανακατεβασμα ματς τελευταιων 8 ημερων (αναθεωρησεις Opta)
SLEEP_MATCH = 0.15
SLEEP_LEAGUE = 0.5
SLEEP_CLUBELO = 0.6

# FotMob league ids — απο mgr_uefa_hist_fetch.py / mgr_existing_2627_fetch.py / discover.py
# (τα ιδια ids που εφτιαξαν τα υπαρχοντα data_*.json των ευρω-λιγκων).
# ΠΡΟΣΟΧΗ: AustrianBundesliga = 38 (το 45 των παλιων scripts ειναι Copa Libertadores —
# αυτο ειχε μολυνει τα ιστορικα data_AustrianBundesliga_2122/2223/2324, δες guard στο
# euro_live_projections). Διορθωθηκε + καθαριστηκε το 2627 στις 10/9/2026.
FM_SPLIT = {                                  # σεζον 2627 (2026/2027)
    'AlbaniaKategoriaSuperiore': 260, 'ArmeniaPremierLeague': 118,
    'AustrianBundesliga': 38, 'AzerbaijanPremierLeague': 262, 'Belgium': 40,
    'BosniaPremierLeague': 267, 'BulgariaFirstLeague': 270, 'CroatiaHNL': 252,
    'CyprusFirstDivision': 136, 'CzechFirstLeague': 122, 'DanishSuperLiga': 46,
    'Ekstraklasa': 196, 'GreeceSL': 135, 'HungaryNBI': 212, 'IsraelLigatHaAl': 127,
    'PrimeiraLiga2': 185, 'RomaniaLigaI': 189, 'ScottishPrem': 64,
    'SerbiaSuperLiga': 182, 'SlovakiaNikeLiga': 176, 'SloveniaPrvaLiga': 173,
    'SwissSuperleague': 69, 'TurkishSuperLig': 71, 'UkrainePremierLeague': 441,
}
FM_CAL = {                                    # ημερολογιακη σεζον 2026
    'FinlandVeikkausliiga': 51, 'GeorgiaErovnuliLiga': 439,
    'KazakhstanPremierLeague': 225, 'LatviaVirsliga': 226,
    'LithuaniaALyga': 228, 'NorwayOBOS': 203,
}

# Griffis (Ben) — οι 9 λιγκες του euro engine (ιδια ονοματα/πηγες με griffis_fetch.py)
GRIFFIS = [
    # (display name στο Post_Match_App, δικος μας κωδικος, ημερολογιακη;)
    ('Czech First League', 'CzechFirstLeague', False),
    ('1. HNL', 'CroatiaHNL', False),
    ('Serbian Super Liga', 'SerbiaSuperLiga', False),
    ('Romanian Liga 1', 'RomaniaLigaI', False),
    ('NB I', 'HungaryNBI', False),
    ('Slovak 1. Liga', 'SlovakiaNikeLiga', False),
    ("Ligat Ha'al", 'IsraelLigatHaAl', False),
    ('Veikkausliiga', 'FinlandVeikkausliiga', True),
    ('Virsliga', 'LatviaVirsliga', True),
]
GRIFFIS_SEA_SPLIT = ('26-27', SEA_SPLIT)      # (ονομα στο αρχειο πηγης, δικος μας κωδικος)
GRIFFIS_SEA_CAL = ('2026', SEA_CAL)
G_STAT = 'https://raw.githubusercontent.com/griffisben/Post_Match_App/main/Stat_Files/'
G_CSV = 'griffis_matches.csv'
G_COLS = ['league', 'season', 'date', 'home', 'away', 'hg', 'ag',
          'xg_h', 'xg_a', 'npxg_h', 'npxg_a', 'shots_h', 'shots_a', 'xt_h', 'xt_a']

# ClubElo — οι 50 χωρες του υπαρχοντος clubelo_current.csv
CE_COUNTRIES = ['ALB', 'ARM', 'AUT', 'AZE', 'BEL', 'BIH', 'BLR', 'BUL', 'CRO', 'CYP',
                'CZE', 'DEN', 'ENG', 'ESP', 'EST', 'FIN', 'FRA', 'FRO', 'GEO', 'GER',
                'GRE', 'HUN', 'IRL', 'ISL', 'ISR', 'ITA', 'KAZ', 'KOS', 'LTU', 'LUX',
                'LVA', 'MDA', 'MKD', 'MLT', 'MNE', 'NED', 'NIR', 'NOR', 'POL', 'POR',
                'ROU', 'SCO', 'SRB', 'SUI', 'SVK', 'SVN', 'SWE', 'TUR', 'UKR', 'WAL']
CE_CSV = 'clubelo_current.csv'
CE_MIN_COUNTRIES = 40   # guard: κατω απο τοσες χωρες ΟΚ -> κρατα το παλιο αρχειο

HDR = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                     '(KHTML, like Gecko) Chrome/120 Safari/537.36',
       'Accept': '*/*', 'Referer': 'https://www.fotmob.com/'}


def get(url, tries=3, timeout=30):
    for i in range(tries):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers=HDR),
                                         timeout=timeout).read()
            if raw[:2] == b'\x1f\x8b':
                raw = gzip.decompress(raw)
            return raw
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(1.5 * (i + 1))


def save_json_atomic(obj, path):
    tmp = path + '.tmp'
    json.dump(obj, open(tmp, 'w', encoding='utf-8'))
    os.replace(tmp, path)


# ================================================================ 1. FotMob domestic
def fm_season_param(sea):
    if len(sea) == 4 and int(sea[:2]) < 30:            # '2627' -> 2026%2F2027
        return f'20{sea[:2]}%2F20{sea[2:]}'
    return sea                                          # ημερολογιακη '2026'


def fm_parse(mid):
    """Ιδιο parse με dl.py / mgr_existing_2627_fetch.py (σκορ + shots οπου υπαρχουν)."""
    d = json.loads(get(f'https://www.fotmob.com/api/data/matchDetails?matchId={mid}'))
    c = d['content']; gen = d['general']; head = d.get('header', {})
    teams = head.get('teams', [])
    hs = teams[0].get('score') if len(teams) > 0 else None
    as_ = teams[1].get('score') if len(teams) > 1 else None
    hid = gen['homeTeam']['id']; aid = gen['awayTeam']['id']
    shots = []
    for s in c.get('shotmap', {}).get('shots', []) or []:
        if s.get('isOwnGoal'):
            continue
        shots.append({'tid': s.get('teamId'), 'xg': s.get('expectedGoals'),
                      'min': s.get('min'), 'sit': s.get('situation'),
                      'goal': s.get('eventType') == 'Goal'})
    reds = []
    for e in c.get('matchFacts', {}).get('events', {}).get('events', []) or []:
        if e.get('type') == 'Card' and e.get('card') in ('Red', 'RedYellow'):
            reds.append({'home': bool(e.get('isHome')), 'min': e.get('time')})
    return {'mid': mid, 'date': gen.get('matchTimeUTC') or gen.get('matchTimeUTCDate'),
            'home': {'name': gen['homeTeam']['name'], 'id': hid},
            'away': {'name': gen['awayTeam']['name'], 'id': aid},
            'hs': hs, 'as': as_, 'shots': shots, 'reds': reds}


def fm_match_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(str(s).replace(' UTC', ''), '%a, %b %d, %Y, %H:%M')
    except Exception:
        try:
            return datetime.strptime(str(s)[:10], '%Y-%m-%d')
        except Exception:
            return None


def refresh_fotmob():
    print('=' * 100)
    print('ΒΗΜΑ 1 — FotMob εγχωρια δεδομενα ευρω-λιγκων (φετινη σεζον)')
    print('=' * 100)
    jobs = [(lg, lid, SEA_SPLIT) for lg, lid in sorted(FM_SPLIT.items())] + \
           [(lg, lid, SEA_CAL) for lg, lid in sorted(FM_CAL.items())]
    summary = []   # (lg, sea, status, new, recheck, err, total, last_date)
    ok_leagues = 0
    for lg, lid, sea in jobs:
        path = f'data_{lg}_{sea}.json'
        try:
            d = json.loads(get(f'https://www.fotmob.com/api/data/leagues?id={lid}'
                               f'&season={fm_season_param(sea)}'))
            arr = (d.get('fixtures', {}).get('allMatches')
                   or d.get('matches', {}).get('allMatches') or [])
            ids = [str(m['id']) for m in arr
                   if m.get('status', {}).get('finished')
                   and not m.get('status', {}).get('cancelled')
                   and not m.get('status', {}).get('awarded')]
        except Exception as e:
            summary.append((lg, sea, f'ΣΦΑΛΜΑ leagues: {type(e).__name__} {str(e)[:50]}',
                            0, 0, 0, None, None))
            continue
        done = {}
        if os.path.exists(path):
            try:
                done = json.load(open(path, encoding='utf-8'))
            except Exception:
                done = {}
        missing = [m for m in ids if m not in done]
        recheck = []
        for mid, m in done.items():
            dt = fm_match_date(m.get('date'))
            if dt is None:
                continue
            age = (TODAY - dt).total_seconds() / 86400.0
            if -1.0 <= age <= RECHECK_DAYS:
                recheck.append(str(mid))
        todo, seen = [], set()
        for mid in missing + recheck:
            if mid not in seen:
                seen.add(mid); todo.append(mid)
        err = 0
        for n, mid in enumerate(todo, 1):
            try:
                done[mid] = fm_parse(mid)
            except Exception as e:
                err += 1
                if err <= 3:
                    print(f'  ! {lg} {mid}: {type(e).__name__} {str(e)[:50]}', flush=True)
            if n % 50 == 0:
                save_json_atomic(done, path)
            time.sleep(SLEEP_MATCH)
        if todo:
            save_json_atomic(done, path)
        dts = [fm_match_date(m.get('date')) for m in done.values()]
        dts = [x for x in dts if x]
        last = max(dts).date().isoformat() if dts else '-'
        summary.append((lg, sea, 'OK', len(missing), len(recheck), err, len(done), last))
        ok_leagues += 1
        print(f'[{lg:26s} {sea}] finished={len(ids):3d}  νεα={len(missing):3d}  '
              f're-check={len(recheck):2d}  err={err}  συνολο={len(done):3d}  τελευταιο={last}',
              flush=True)
        time.sleep(SLEEP_LEAGUE)
    print(f'\nFotMob: {ok_leagues}/{len(jobs)} λιγκες ΟΚ  [{time.time()-T0:.0f}s]')
    for lg, sea, st, *_ in summary:
        if st != 'OK':
            print(f'  ΑΠΟΤΥΧΙΑ {lg}/{sea}: {st}')
    return summary, ok_leagues


# ================================================================ 2. Griffis (Ben)
def griffis_pair(text, lg, sea):
    """Ιδιο pairing με griffis_fetch.py PHASE 2 — rows του stat CSV -> ματς."""
    rows = list(csv.DictReader(text.splitlines()))
    groups = {}
    for r in rows:
        groups.setdefault((r.get('Date', ''), r.get('Match', '')), []).append(r)

    def _pm(match_str, a, b):
        a_h = match_str.startswith(a + ' ')
        a_a = match_str.endswith(' ' + a) or match_str.endswith(a)
        b_h = match_str.startswith(b + ' ')
        b_a = match_str.endswith(' ' + b) or match_str.endswith(b)
        if a_h and b_a and not (a_a and b_h):
            return a, b
        if b_h and a_a and not (b_a and a_h):
            return b, a
        return None

    out, bad = [], 0
    for (dt, ms), grp in groups.items():
        if len(grp) != 2:
            bad += 1
            continue
        r1, r2 = grp
        ha = _pm(ms, r1['Team'], r2['Team'])
        if ha is None:
            bad += 1
            continue
        hrow = r1 if r1['Team'] == ha[0] else r2
        arow = r2 if r1['Team'] == ha[0] else r1
        try:
            hg = int(float(hrow['Goals'])); ag = int(float(arow['Goals']))
        except Exception:
            bad += 1
            continue

        def f(row, key):
            try:
                return float(row[key])
            except Exception:
                return None
        out.append({'league': lg, 'season': sea, 'date': dt,
                    'home': ha[0], 'away': ha[1], 'hg': hg, 'ag': ag,
                    'xg_h': f(hrow, 'xG'), 'xg_a': f(arow, 'xG'),
                    'npxg_h': f(hrow, 'npxG'), 'npxg_a': f(arow, 'npxG'),
                    'shots_h': f(hrow, 'Shots'), 'shots_a': f(arow, 'Shots'),
                    'xt_h': f(hrow, 'xT'), 'xt_a': f(arow, 'xT')})
    return out, bad


def refresh_griffis():
    print('\n' + '=' * 100)
    print('ΒΗΜΑ 2 — Griffis (Ben): 9 λιγκες, φετινες σεζον -> griffis_matches.csv')
    print('=' * 100)
    if not os.path.exists(G_CSV):
        print(f'ΣΦΑΛΜΑ: δεν υπαρχει {G_CSV} — δεν φτιαχνω απο το μηδεν (θελει ιστορικο). Πασο.')
        return [], 0
    fresh = {}     # (lg, sea) -> rows
    summary = []   # (lg, sea, status, old_n, new_n, last_date)
    old_rows = list(csv.DictReader(open(G_CSV, encoding='utf-8')))
    old_cnt = {}
    for r in old_rows:
        old_cnt[(r['league'], str(r['season']))] = old_cnt.get((r['league'], str(r['season'])), 0) + 1
    for disp, lg, is_cal in GRIFFIS:
        sea_disp, sea = GRIFFIS_SEA_CAL if is_cal else GRIFFIS_SEA_SPLIT
        url = G_STAT + urllib.parse.quote(f'{disp} {sea_disp}.csv')
        try:
            raw = get(url, timeout=30)
            text = raw.decode('utf-8-sig', errors='replace')
        except Exception as e:
            summary.append((lg, sea, f'ΣΦΑΛΜΑ fetch: {type(e).__name__} {str(e)[:40]}',
                            old_cnt.get((lg, sea), 0), None, None))
            time.sleep(0.25)
            continue
        rows, bad = griffis_pair(text, lg, sea)
        old_n = old_cnt.get((lg, sea), 0)
        if len(rows) < old_n:
            summary.append((lg, sea, f'ΠΑΣΟ: πηγη εδωσε {len(rows)} < {old_n} υπαρχοντα (guard)',
                            old_n, len(rows), None))
            time.sleep(0.25)
            continue
        fresh[(lg, sea)] = rows
        last = max((r['date'] for r in rows), default='-')
        summary.append((lg, sea, 'OK', old_n, len(rows), last))
        print(f'[{lg:24s} {sea}] πηγη={len(rows):3d} ματς (bad {bad})  '
              f'ειχαμε={old_n:3d}  νεα={len(rows)-old_n:+3d}  τελευταιο={last}', flush=True)
        time.sleep(0.25)

    if fresh:
        # replace in place: οι παλιες γραμμες των (lg, sea) αντικαθιστανται στη θεση τους
        out, done_keys = [], set()
        for r in old_rows:
            key = (r['league'], str(r['season']))
            if key in fresh:
                if key not in done_keys:
                    done_keys.add(key)
                    out.extend(fresh[key])
                continue
            out.append(r)
        for key, rows in fresh.items():
            if key not in done_keys:
                out.extend(rows)
        tmp = G_CSV + '.tmp'
        with open(tmp, 'w', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=G_COLS)
            w.writeheader()
            for r in out:
                w.writerow(r)
        os.replace(tmp, G_CSV)
        print(f'\nΓραφτηκε {G_CSV}: {len(out)} γραμμες ({len(fresh)}/9 λιγκες ανανεωθηκαν)')
        # ενημερωτικο: ομαδες φετος χωρις εγγραφη στο name map (θα σκιπαρονται στο load_griffis)
        try:
            nmap = json.load(open('griffis_name_map.json', encoding='utf-8'))
            miss = sorted({f'{k[0]}: {nm}' for k, rows in fresh.items() for r in rows
                           for nm in (r['home'], r['away'])
                           if not (nmap.get(f'{k[0]}|{nm}') or {}).get('fotmob')})
            if miss:
                print('ΠΡΟΣΟΧΗ — ομαδες χωρις fotmob match στο griffis_name_map.json '
                      '(οι αγωνες τους σκιπαρονται):')
                for m in miss:
                    print('  ' + m)
        except Exception as e:
            print(f'(ελεγχος name map απετυχε: {e})')
    else:
        print('Καμια λιγκα δεν ανανεωθηκε — το griffis_matches.csv εμεινε ως εχει.')
    for lg, sea, st, *_ in summary:
        if st != 'OK':
            print(f'  {lg}/{sea}: {st}')
    return summary, len(fresh)


# ================================================================ 3. ClubElo current
def clubelo_country(cc):
    """Σελιδα χωρας clubelo.com/{CC} -> λιστα dicts (country,name,federation,level,elo)."""
    last_err = None
    for scheme in ('https', 'http'):
        try:
            t = get(f'{scheme}://clubelo.com/{cc}', tries=2, timeout=25).decode('utf-8', 'replace')
            break
        except Exception as e:
            last_err = e
            t = None
    if t is None:
        raise last_err
    out = []
    for s in re.findall(r'<script[^>]*>(.*?)</script>', t, flags=re.S):
        if '"datasets"' not in s:
            continue
        i = s.find('{')
        try:
            js, _ = json.JSONDecoder().raw_decode(s[i:])
        except Exception:
            continue
        for v in js.get('datasets', {}).values():
            if not (v and isinstance(v[0], dict)):
                continue
            if not ({'Elo', 'Name', 'Level', 'FedURL'} <= set(v[0])) or 'Date' in v[0]:
                continue
            for e in v:
                if e.get('FedURL') != cc:
                    continue
                out.append({'country': cc, 'name': str(e['Name']),
                            'federation': str(e.get('Federation', '')),
                            'level': int(e['Level']), 'elo': round(float(e['Elo']), 1)})
    # dedup by name (κρατα την πρωτη εμφανιση)
    seen, ded = set(), []
    for e in out:
        if e['name'] in seen:
            continue
        seen.add(e['name']); ded.append(e)
    return ded


def refresh_clubelo():
    print('\n' + '=' * 100)
    print('ΒΗΜΑ 3 — ClubElo: clubelo_current.csv απο σελιδες χωρων')
    print('=' * 100)
    rows, ok, fail = [], [], []
    for cc in CE_COUNTRIES:
        try:
            r = clubelo_country(cc)
            if not r:
                raise ValueError('0 συλλογοι στη σελιδα')
            rows.extend(r); ok.append(cc)
        except Exception as e:
            fail.append((cc, f'{type(e).__name__} {str(e)[:40]}'))
        time.sleep(SLEEP_CLUBELO)
    print(f'ΟΚ {len(ok)}/{len(CE_COUNTRIES)} χωρες, {len(rows)} συλλογοι  [{time.time()-T0:.0f}s]')
    if fail:
        print('  αποτυχιες: ' + ', '.join(f'{cc} ({msg})' for cc, msg in fail))
    if len(ok) < CE_MIN_COUNTRIES:
        print(f'GUARD: μονο {len(ok)} χωρες (<{CE_MIN_COUNTRIES}) — το {CE_CSV} ΔΕΝ πειραζεται.')
        return len(ok), False
    # για χωρες που απετυχαν: κρατα τις παλιες γραμμες τους (αν υπαρχει παλιο αρχειο)
    if fail and os.path.exists(CE_CSV):
        keep = {cc for cc, _ in fail}
        try:
            for r in csv.DictReader(open(CE_CSV, encoding='utf-8')):
                if r['country'] in keep:
                    rows.append({'country': r['country'], 'name': r['name'],
                                 'federation': r['federation'], 'level': r['level'],
                                 'elo': r['elo'], '_old': True})
            print(f'  κρατηθηκαν οι παλιες γραμμες για: {", ".join(sorted(keep))}')
        except Exception as e:
            print(f'  (αδυνατη η διατηρηση παλιων γραμμων: {e})')
    fetched = str(date.today())
    tmp = CE_CSV + '.tmp'
    with open(tmp, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['country', 'name', 'federation', 'level', 'elo', 'fetched'])
        for e in rows:
            w.writerow([e['country'], e['name'], e['federation'], e['level'], e['elo'], fetched])
    os.replace(tmp, CE_CSV)
    print(f'Γραφτηκε {CE_CSV}: {len(rows)} γραμμες (fetched {fetched})')
    return len(ok), True


# ================================================================ MAIN
if __name__ == '__main__':
    print(f'euro_refresh — {TODAY:%Y-%m-%d %H:%M} UTC  (σεζον {SEA_SPLIT}/{SEA_CAL})')
    fm_sum, fm_ok = refresh_fotmob()
    try:
        g_sum, g_ok = refresh_griffis()
    except Exception as e:
        print(f'ΣΦΑΛΜΑ Griffis (μη κρισιμο, συνεχιζω): {type(e).__name__}: {e}')
        g_sum, g_ok = [], 0
    try:
        ce_ok, ce_wrote = refresh_clubelo()
    except Exception as e:
        print(f'ΣΦΑΛΜΑ ClubElo (μη κρισιμο, συνεχιζω): {type(e).__name__}: {e}')
        ce_ok, ce_wrote = 0, False

    print('\n' + '=' * 100)
    print('ΣΥΝΟΨΗ')
    print('=' * 100)
    n_new = sum(s[3] for s in fm_sum if s[2] == 'OK')
    print(f'FotMob:  {fm_ok}/{len(fm_sum)} λιγκες ΟΚ, {n_new} νεα ματς συνολικα')
    for lg, sea, st, new, rc, err, tot, last in fm_sum:
        if st == 'OK' and (new or err):
            print(f'  {lg:26s} {sea}: +{new} ματς (err {err}), τελευταιο {last}')
    print(f'Griffis: {g_ok}/9 λιγκες ανανεωθηκαν')
    print(f'ClubElo: {ce_ok}/{len(CE_COUNTRIES)} χωρες' +
          ('' if ce_wrote else '  (το αρχειο ΔΕΝ ξαναγραφτηκε)'))
    print(f'ΤΕΛΟΣ [{time.time()-T0:.0f}s]')
    if fm_ok == 0:
        sys.exit(1)   # ολικη αποτυχια FotMob (δικτυο/μπλοκ) -> κοκκινο στο Actions
