# -*- coding: utf-8 -*-
"""
nowgoal_map_extra.py -- Αντιστοιχιση ματς (FotMob data_<λιγκα>_<σεζον>.json) -> Nowgoal ngid για 22 ΕΠΙΠΛΕΟΝ εγχωριες λιγκες.
Ιδια λογικη με nowgoal_map.py / nowgoal_sa_map.py (jsData/matchResult/json/{σεζον}/s{id}_en.json, ημερομηνια +-1 μερα,
ονοματα και των δυο πλευρων) + 2ο περασμα: μαθαινει αντιστοιχιση team-id (FotMob->Nowgoal) απο τα σιγουρα ματς και
τη χρησιμοποιει (μαζι με το σκορ) για τα υπολοιπα.
Εξοδοι: nowgoal_map_extra.json  {our_mid: {ng, lg, sea, date, home, away, eu}}   (eu=1: ομαδα που επαιξε Ευρωπη τη σεζον)
        nowgoal_extra_matches.json {lg_sea: {ngid: {...}}} (ολα τα ματς Nowgoal, ανεξαρτητα απο τα δικα μας)
        nowgoal_map_extra_report.json (στατιστικα ανα λιγκα/σεζον)
Σεζον: 2122..2526 για split-year λιγκες (sea='2223'), ημερολογιακες (Eliteserien/Allsvenskan) sea='2021'..'2025'.
"""
import sys, os, re, json, gzip, time, glob, unicodedata, datetime as dt, urllib.request, http.cookiejar
from collections import defaultdict, Counter
from difflib import SequenceMatcher
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(os.path.dirname(os.path.abspath(__file__)))

CACHE_DIR = 'nowgoal_jsdata'; os.makedirs(CACHE_DIR, exist_ok=True)
# (nowgoal league id, ημερολογιακη?)
LEAGUES = {
    'CzechFirstLeague': (137, 0), 'CroatiaHNL': (133, 0), 'SerbiaSuperLiga': (129, 0), 'SlovakiaNikeLiga': (132, 0),
    'SloveniaPrvaLiga': (247, 0), 'HungaryNBI': (136, 0), 'BulgariaFirstLeague': (131, 0), 'BosniaPremierLeague': (352, 0),
    'UkrainePremierLeague': (119, 0), 'RomaniaLigaI': (124, 0), 'Ekstraklasa': (6, 0), 'AustrianBundesliga': (3, 0),
    'SwissSuperleague': (27, 0), 'DanishSuperLiga': (7, 0), 'Belgium': (5, 0), 'ScottishPrem': (29, 0),
    'TurkishSuperLig': (30, 0), 'GreeceSL': (32, 0), 'CyprusFirstDivision': (159, 0), 'IsraelLigatHaAl': (118, 0),
    'Eliteserien': (22, 1), 'Allsvenskan': (26, 1),
}
SPLIT_SEAS = {'2122': '2021-2022', '2223': '2022-2023', '2324': '2023-2024', '2425': '2024-2025', '2526': '2025-2026'}
CAL_YEARS = ['2021', '2022', '2023', '2024', '2025']

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


_init = [False]
def fetch_json(sea, sid):
    fp = os.path.join(CACHE_DIR, f'{sea}_s{sid}_en.json')
    if os.path.exists(fp) and os.path.getsize(fp) > 2000:
        return json.load(open(fp, encoding='utf-8'))
    if not _init[0]:
        get('https://football.nowgoal26.com/'); _init[0] = True
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
        if len(v) >= 7 and isinstance(v[3], str) and re.match(r'\d{4}-\d{2}-\d{2}', v[3]):
            yield path, v
        else:
            for x in v:
                yield from rows_of(x, path)


def parse(j):
    teams = {int(r[0]): r[1] for r in (j.get('TeamInfo') or j.get('TeamList') or [])}
    out = {}
    for path, row in rows_of(j.get('ScheduleList') or {}):
        try:
            ng = int(row[0]); bj = dt.datetime.strptime(row[3][:16], '%Y-%m-%d %H:%M')
            h, a = int(row[4]), int(row[5])
        except (ValueError, TypeError):
            continue
        utc = bj - dt.timedelta(hours=8)
        out[ng] = dict(date=utc.strftime('%Y-%m-%d'), dt=utc.strftime('%Y-%m-%d %H:%M'), hid=h, aid=a,
                       home=teams.get(h, ''), away=teams.get(a, ''), score=(row[6] or '').strip(),
                       status=row[2], sub=[p for p in path][:2])
    return out


STOP = {'fc', 'cf', 'ac', 'afc', 'fk', 'sk', 'nk', 'sc', 'sv', 'tsv', 'as', 'cs', 'fcsb', 'if', 'bk', 'ik', 'ff', 'sd', 'ud',
        'ks', 'kf', 'rks', 'gks', 'mks', 'ofk', 'hnk', 'nd', 'fc', 'club', 'de', 'the', 'of', 'town', 'city', 'united', 'utd'}
def norm_s(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9 ]', ' ', s)
def toks(s):
    t = set(norm_s(s).split())
    t2 = t - STOP
    return t2 or t
def sim(a, b):
    ta, tb = toks(a), toks(b)
    if not ta or not tb:
        return 0.0
    # token-overlap με ανοχη προθεματος (>=4 χαρ.)
    ov = 0
    for x in ta:
        for y in tb:
            if x == y or (len(x) >= 4 and len(y) >= 4 and (x.startswith(y) or y.startswith(x))):
                ov += 1; break
    jac = ov / len(ta | tb) if (ta | tb) else 0
    ov2 = ov / min(len(ta), len(tb))
    sq = SequenceMatcher(None, ''.join(sorted(ta)), ''.join(sorted(tb))).ratio()
    sq2 = SequenceMatcher(None, norm_s(a).replace(' ', ''), norm_s(b).replace(' ', '')).ratio()
    return max(jac, 0.8 * ov2, 0.9 * sq2 if sq2 > 0.8 else 0, sq * 0.7)


FD = '%a, %b %d, %Y, %H:%M UTC'
def our_matches(lg, cal):
    """yield (code, sea_key, [matches])"""
    res = []
    files = sorted(glob.glob(f'data_{lg}_*.json'))
    fx = f'fixtures_{lg}_2122.json'          # 2021-22: fixtures_ αρχειο οταν δεν υπαρχει data_ (ιδια μορφη, χωρις σουτ)
    if os.path.exists(fx) and not os.path.exists(f'data_{lg}_2122.json'):
        files.append(fx)
    for f in files:
        code = re.search(r'_(\d{4})\.json$', f).group(1)
        d = json.load(open(f, encoding='utf-8'))
        ms = []
        for mid, m in d.items():
            try:
                try:
                    t = dt.datetime.strptime(m['date'], FD)
                except ValueError:
                    t = dt.datetime.strptime(m['date'][:16], '%Y-%m-%dT%H:%M')   # fixtures_ μορφη
            except Exception:
                continue
            ms.append(dict(mid=str(m.get('mid', mid)), dt=t, date=t.strftime('%Y-%m-%d'),
                           hid=int(m['home']['id']), aid=int(m['away']['id']),
                           home=m['home']['name'], away=m['away']['name'], hs=m.get('hs'), as_=m.get('as')))
        if not ms:
            continue
        if cal:
            yr = Counter(x['dt'].year for x in ms).most_common(1)[0][0]
            sea = str(yr)
            if sea not in CAL_YEARS:
                continue
        else:
            if code not in SPLIT_SEAS:
                continue
            sea = code
        res.append((code, sea, ms))
    return res


# Ευρωπη: ομαδες ανα σεζον
EU = defaultdict(set)
for fn in ('europe_fixtures.json', 'euq_fixtures.json'):
    try:
        for k, v in json.load(open(fn, encoding='utf-8')).items():
            sea = k.split('_')[-1]
            for m in v:
                EU[sea].add(int(m['hid'])); EU[sea].add(int(m['aid']))
    except Exception as e:
        print('EU σφαλμα', fn, e)


def eu_key(sea, cal):
    if cal:
        y = int(sea); return f'{y % 100:02d}{(y + 1) % 100:02d}'
    return sea


def scorestr(m):
    return f"{m['hs']}-{m['as_']}" if m['hs'] is not None else None


def pass1(ms, ngm, byd):
    matched = {}; used = set(); cands = []
    for m in ms:
        d0 = dt.datetime.strptime(m['date'], '%Y-%m-%d')
        for off in (0, -1, 1):
            dd = (d0 + dt.timedelta(days=off)).strftime('%Y-%m-%d')
            for ng in byd.get(dd, []):
                r = ngm[ng]
                sh = sim(m['home'], r['home']); sa = sim(m['away'], r['away'])
                sc = scorestr(m)
                scm = (sc is not None and sc == r['score'].replace(' ', ''))
                if sh >= 0.5 and sa >= 0.5:
                    cands.append((sh + sa + (0.5 if scm else 0) - 0.05 * abs(off), m['mid'], ng, m, r))
    cands.sort(key=lambda x: -x[0])
    return matched, used, cands


def pass2_one(m, ngm, byd, used, tmap):
    d0 = dt.datetime.strptime(m['date'], '%Y-%m-%d')
    best = None; sc = scorestr(m)
    for off in (0, -1, 1):
        dd = (d0 + dt.timedelta(days=off)).strftime('%Y-%m-%d')
        for ng in byd.get(dd, []):
            if ng in used:
                continue
            r = ngm[ng]
            hk = tmap.get(m['hid']) == r['hid']; ak = tmap.get(m['aid']) == r['aid']
            scm = (sc is not None and sc == r['score'].replace(' ', ''))
            sh = sim(m['home'], r['home']); sa = sim(m['away'], r['away'])
            ok = (hk and ak) or ((hk or ak) and scm and max(sh, sa) > 0.3) or (scm and sh >= 0.35 and sa >= 0.35)
            if ok:
                s = (2 if hk else 0) + (2 if ak else 0) + sh + sa + (1 if scm else 0) - 0.05 * abs(off)
                if best is None or s > best[0]:
                    best = (s, ng)
    return best


mapping = {}; ng_all = {}; report = {}; misses_all = []
for lg, (sid, cal) in LEAGUES.items():
    ours_by_sea = our_matches(lg, cal)
    seas_needed = CAL_YEARS if cal else list(SPLIT_SEAS)
    ng_by_sea = {}
    for sea in seas_needed:
        nsea = sea if cal else SPLIT_SEAS[sea]
        try:
            ng_by_sea[sea] = parse(fetch_json(nsea, sid))
        except Exception as e:
            print(f'  {lg} {nsea}: ΣΦΑΛΜΑ λήψης {type(e).__name__} {str(e)[:80]}', flush=True)
            ng_by_sea[sea] = {}
        ng_all[f'{lg}_{sea}'] = {str(k): v for k, v in ng_by_sea[sea].items()}
    tid_votes = defaultdict(Counter)
    state = {}
    for code, sea, ms in ours_by_sea:
        ngm = ng_by_sea.get(sea, {})
        byd = defaultdict(list)
        for ng, r in ngm.items():
            byd[r['date']].append(ng)
        matched, used, cands = pass1(ms, ngm, byd)
        for s, mid, ng, m, r in cands:
            if mid in matched or ng in used:
                continue
            matched[mid] = ng; used.add(ng)
            tid_votes[m['hid']][r['hid']] += 1; tid_votes[m['aid']][r['aid']] += 1
        state[sea] = (code, ms, ngm, byd, matched, used)
    tmap = {k: c.most_common(1)[0][0] for k, c in tid_votes.items() if c.most_common(1)[0][1] >= 2}
    for sea, (code, ms, ngm, byd, matched, used) in state.items():
        for m in ms:
            if m['mid'] in matched:
                continue
            b = pass2_one(m, ngm, byd, used, tmap)
            if b:
                matched[m['mid']] = b[1]; used.add(b[1])
        eu = EU.get(eu_key(sea, cal), set())
        n_eu = n_eu_m = 0
        for m in ms:
            is_eu = int(m['hid'] in eu or m['aid'] in eu)
            n_eu += is_eu
            if m['mid'] in matched:
                mapping[m['mid']] = dict(ng=int(matched[m['mid']]), lg=lg, sea=sea, date=m['date'],
                                         home=m['home'], away=m['away'], eu=is_eu)
                n_eu_m += is_eu
            else:
                misses_all.append((lg, sea, m['date'], m['home'], m['away'], m['hs'], m['as_']))
        report[f'{lg}_{sea}'] = dict(ours=len(ms), mapped=len(matched), ng_matches=len(ngm), eu=n_eu, eu_mapped=n_eu_m, ng_id=sid)
        print(f'  {lg:22s} {sea} s{sid}: ours {len(ms):4d} NG {len(ngm):4d} mapped {len(matched):4d} '
              f'({len(matched) / len(ms) * 100:5.1f}%) eu {n_eu_m}/{n_eu}', flush=True)
    have = {s for _, s, _ in ours_by_sea}
    for sea in seas_needed:
        if sea not in have:
            report[f'{lg}_{sea}'] = dict(ours=0, mapped=0, ng_matches=len(ng_by_sea.get(sea, {})), eu=0, eu_mapped=0, ng_id=sid)
            print(f'  {lg:22s} {sea} s{sid}: ΔΕΝ υπαρχει data_ αρχειο · NG {len(ng_by_sea.get(sea, {}))} ματς', flush=True)

json.dump(mapping, open('nowgoal_map_extra.json', 'w', encoding='utf-8'), ensure_ascii=False)
json.dump(ng_all, open('nowgoal_extra_matches.json', 'w', encoding='utf-8'), ensure_ascii=False)
json.dump(report, open('nowgoal_map_extra_report.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
tot = sum(r['ours'] for r in report.values())
print(f'\nΤΑΙΡΙΑΣΜΑ: {len(mapping)}/{tot} ({len(mapping) / max(tot, 1) * 100:.1f}%) · eu: {sum(v["eu"] for v in mapping.values())}')
if misses_all:
    cc = Counter((m[0], m[1]) for m in misses_all)
    print('αταιριαστα ανα λιγκα-σεζον:', dict(cc))
    for m in misses_all[:40]:
        print('  ', m)
