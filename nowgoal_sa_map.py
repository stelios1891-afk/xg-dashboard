# -*- coding: utf-8 -*-
"""
nowgoal_sa_map.py -- Nowgoal ματς για Brazil Serie A (s4) και MLS (s21), σεζον 2021-2026 (ημερολογιακα ετη).

1. Κατεβαζει jsData/matchResult/json/{ετος}/s{id}_en.json (cache στο nowgoal_jsdata/) -- MLS: ολα τα sub-leagues
   (League + playoffs), Brazil: R_1..R_38.
2. Γραφει nowgoal_sa_matches.json  {ngid: {lg, sea, date_utc, dt_utc, home, away, score, ht, sub, rnd, status}}
   (ανεξαρτητο απο FotMob, το fetch των odds διαβαζει ΜΟΝΟ αυτο).
3. Ταιριαζει με ΟΣΑ data_Brazil_*.json / data_MLS_*.json υπαρχουν (ημερομηνια +-1 μερα + token-overlap ονοματων
   και στις δυο πλευρες, ισοβαθμια -> σκορ). Γραφει nowgoal_sa_map.json {our_mid: {ng, lg, sea, date, home, away}}
   και τυπωνει match rate + αταιριαστα. Ξανατρεχει ελευθερα οταν εμφανιζονται νεα data_*.json.
Χρηση: python nowgoal_sa_map.py   |   python nowgoal_sa_map.py --remap-only
"""
import sys, os, re, json, gzip, time, glob, unicodedata, datetime as dt, urllib.request, http.cookiejar
from collections import defaultdict, Counter
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(os.path.dirname(os.path.abspath(__file__)))

CACHE_DIR = 'nowgoal_jsdata'; os.makedirs(CACHE_DIR, exist_ok=True)
LEAGUES = {'Brazil': 4, 'MLS': 21}
YEARS = [2021, 2022, 2023, 2024, 2025, 2026]
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
BASE = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36'),
        ('Accept', '*/*'), ('Accept-Encoding', 'gzip')]


def get(u, ref=None):
    op.addheaders = BASE + ([('Referer', ref)] if ref else [])
    r = op.open(u, timeout=25); d = r.read()
    if d[:2] == b'\x1f\x8b':
        d = gzip.decompress(d)
    return d.decode('utf-8', 'replace')


def fetch_json(sea, sid):
    fp = os.path.join(CACHE_DIR, f'{sea}_s{sid}_en.json')
    # τρεχουσα σεζον: ξαναφερνουμε αν το cache ειναι >6 ωρες παλιο
    fresh = os.path.exists(fp) and (sea < YEARS[-1] or time.time() - os.path.getmtime(fp) < 6 * 3600)
    if fresh and os.path.getsize(fp) > 5000:
        return json.load(open(fp, encoding='utf-8'))
    t = get(f'https://football.nowgoal26.com/jsData/matchResult/json/{sea}/s{sid}_en.json',
            ref=f'https://football.nowgoal26.com/league/{sea}/{sid}')
    time.sleep(0.8)
    t = t.lstrip(chr(65279))
    j = json.loads(t)
    json.dump(j, open(fp, 'w', encoding='utf-8'), ensure_ascii=False)
    return j


def rows_of(v, path=()):
    """γραμμη ματς = [ngid, lgid, status, 'YYYY-MM-DD HH:MM', hid, aid, 'h-a', 'hh-ah', ...]"""
    if isinstance(v, dict):
        for k, x in v.items():
            yield from rows_of(x, path + (k,))
    elif isinstance(v, list):
        if len(v) >= 8 and isinstance(v[3], str) and re.match(r'\d{4}-\d{2}-\d{2}', v[3]):
            yield path, v
        else:
            for x in v:
                yield from rows_of(x, path)


def parse(j, lg, year):
    teams = {int(r[0]): r[1] for r in j.get('TeamInfo', [])}
    subs = {f'sub_{s[0]}': s[1] for s in j.get('SubLeagueInfo', [])}
    out = {}
    for path, row in rows_of(j.get('ScheduleList') or {}):
        try:
            ng = int(row[0]); bj = dt.datetime.strptime(row[3], '%Y-%m-%d %H:%M')
            h, a = int(row[4]), int(row[5])
        except (ValueError, TypeError):
            continue
        utc = bj - dt.timedelta(hours=8)
        sub = next((p for p in path if p.startswith('sub_')), None)
        rnd = next((p for p in path if p.startswith('R_')), None)
        out[ng] = dict(lg=lg, sea=str(year), date_utc=utc.strftime('%Y-%m-%d'), dt_utc=utc.strftime('%Y-%m-%d %H:%M'),
                       home=teams.get(h, ''), away=teams.get(a, ''), score=row[6] or '', ht=row[7] or '',
                       sub=subs.get(sub, sub) if sub else 'League', rnd=rnd, status=row[2])
    return out


def main():
    get('https://football.nowgoal26.com/')
    M = {}
    for lg, sid in LEAGUES.items():
        for y in YEARS:
            try:
                rows = parse(fetch_json(y, sid), lg, y)
            except Exception as e:
                print(f'  {lg} {y}: ΣΦΑΛΜΑ {type(e).__name__} {e}'); continue
            M.update({str(k): v for k, v in rows.items()})
            print(f'  {lg} {y}: {len(rows)} ματς · τελευταιο {max(r["dt_utc"] for r in rows.values())}', flush=True)
    json.dump(M, open('nowgoal_sa_matches.json', 'w', encoding='utf-8'), ensure_ascii=False)
    print('Συνολο nowgoal ματς:', len(M), '-> nowgoal_sa_matches.json')
    build_map(M)


# ---------------- ταιριασμα με FotMob ----------------
STOP = {'fc', 'cf', 'sc', 'ec', 'afc', 'club', 'de', 'da', 'do', 'ac', 'cd', 'cs', 'fk', 'sad', 'the'}


def toks(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'\([^)]*\)', ' ', s)
    return frozenset(re.sub(r'[^a-z0-9 ]', ' ', s).split()) - STOP


# FotMob -> Nowgoal ονοματα (μονο οπου τα tokens δεν αρκουν)
ALIAS = {
    'Atletico MG': 'Atletico Mineiro', 'Atletico-MG': 'Atletico Mineiro', 'Atletico PR': 'Athletico Paranaense',
    'Athletico PR': 'Athletico Paranaense', 'Corinthians': 'Corinthians Paulista', 'Internacional': 'Internacional RS',
    'Vitoria': 'Vitoria BA', 'Botafogo': 'Botafogo RJ', 'Fluminense': 'Fluminense RJ',
    'Sport Recife': 'Sport Club do Recife', 'RB Bragantino': 'Bragantino', 'Red Bull Bragantino': 'Bragantino',
    'Vasco': 'Vasco da Gama', 'America MG': 'America Mineiro', 'America-MG': 'America Mineiro',
    'LA Galaxy': 'Los Angeles Galaxy', 'LAFC': 'Los Angeles FC', 'NYCFC': 'New York City',
    'New York City FC': 'New York City', 'Montreal Impact': 'CF Montreal',
    'D.C. United': 'DC United', 'St. Louis City': 'St. Louis City SC',
}


def parse_fm_date(s):
    try:
        return dt.datetime.strptime(str(s).replace(' UTC', ''), '%a, %b %d, %Y, %H:%M')
    except ValueError:
        try:
            return dt.datetime.strptime(str(s)[:10], '%Y-%m-%d')
        except ValueError:
            return None


def sim(a, b):
    ov = len(a & b)
    return ov / len(a | b) if ov else 0.0


def build_map(M):
    by_date = defaultdict(list)       # (lg, date) -> [ngid]
    for ng, m in M.items():
        by_date[(m['lg'], m['date_utc'])].append(ng)
    ours = []; seen = set()
    for lg in LEAGUES:
        for fp in sorted(glob.glob(f'data_{lg}_*.json')):
            d = json.load(open(fp, encoding='utf-8'))
            for mid, m in d.items():
                t = parse_fm_date(m.get('date'))
                if t is None or (lg, str(m.get('mid', mid))) in seen:
                    continue
                seen.add((lg, str(m.get('mid', mid))))
                ours.append(dict(lg=lg, file=fp, mid=str(m.get('mid', mid)), t=t, home=m['home']['name'], away=m['away']['name'],
                                 score=f"{m.get('hs')}-{m.get('as')}"))
    if not ours:
        print('Δεν βρεθηκαν data_*.json'); return
    cand = []
    for o in ours:
        ht = toks(ALIAS.get(o['home'], o['home'])); at = toks(ALIAS.get(o['away'], o['away']))
        for off in (-1, 0, 1):
            d0 = (o['t'] + dt.timedelta(days=off)).strftime('%Y-%m-%d')
            for ng in by_date.get((o['lg'], d0), []):
                m = M[ng]
                sh = sim(ht, toks(m['home'])); sa = sim(at, toks(m['away']))
                if sh == 0 or sa == 0:
                    continue
                dh = abs((dt.datetime.strptime(m['dt_utc'], '%Y-%m-%d %H:%M') - o['t']).total_seconds()) / 3600
                sc = sh + sa + (0.5 if m['score'] == o['score'] else 0) + (0.3 if dh < 3 else 0)
                cand.append((sc, o['mid'], ng))
    cand.sort(reverse=True)
    used_o, used_n, pairs = set(), set(), {}
    for sc, mid, ng in cand:
        if mid in used_o or ng in used_n:
            continue
        used_o.add(mid); used_n.add(ng); pairs[mid] = ng
    mapping = {}
    stats = defaultdict(lambda: [0, 0]); miss = []
    for o in ours:
        key = (o['lg'], str(o['t'].year))
        stats[key][1] += 1
        ng = pairs.get(o['mid'])
        if ng:
            m = M[ng]
            mapping[o['mid']] = dict(ng=int(ng), lg=o['lg'], sea=m['sea'], date=o['t'].strftime('%Y-%m-%d'), home=o['home'], away=o['away'])
            stats[key][0] += 1
        else:
            miss.append((o['lg'], o['t'].strftime('%Y-%m-%d'), o['home'], o['away']))
    json.dump(mapping, open('nowgoal_sa_map.json', 'w', encoding='utf-8'), ensure_ascii=False)
    print('\nΤΑΙΡΙΑΣΜΑ FotMob->Nowgoal: %d/%d (%.1f%%) -> nowgoal_sa_map.json' % (len(mapping), len(ours), 100 * len(mapping) / len(ours)))
    for k in sorted(stats):
        a, b = stats[k]
        print(f'  {k[0]} {k[1]}: {a}/{b} ({100*a/b:.1f}%)')
    if miss:
        print('αταιριαστα (δειγμα 15):', miss[:15])
        print('ονοματα που δεν ταιριαξαν:', Counter([m[2] for m in miss] + [m[3] for m in miss]).most_common(15))


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--remap-only':
        build_map(json.load(open('nowgoal_sa_matches.json', encoding='utf-8')))
    else:
        main()
