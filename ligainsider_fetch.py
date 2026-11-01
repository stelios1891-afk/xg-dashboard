# -*- coding: utf-8 -*-
"""ligainsider_fetch.py — Projected lineups Bundesliga απο ligainsider.de (πηγη Στελιου, 1/9).

Η αρχικη σελιδα καθε ομαδας (/slug/id/) ΕΙΝΑΙ το "Aufstellung": γηπεδο με την
επερχομενη 11αδα. Παρσαρισμα: μπλοκ player_name με href slug πληρους ονοματος
(π.χ. /jobe-bellingham_38153/)· οι εναλλακτικοι εχουν σημανση next_sub στο τμημα
τους και ΔΕΝ μετρανε. Per-team snapshots στο projected_fc.jsonl (ιδιο σχημα με
fantasy-coach) -> το dashboard τα ζευγαρωνει ηδη μονο του.
"""
import sys, json, re, gzip, time, datetime, unicodedata, urllib.request
sys.stdout.reconfigure(encoding='utf-8')

BASE = 'https://www.ligainsider.de'
HDR = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36',
       'Accept': 'text/html,*/*', 'Accept-Encoding': 'gzip'}
OUT = 'projected_fc.jsonl'
LG = 'Bundesliga'


def get(u):
    d = urllib.request.urlopen(urllib.request.Request(u, headers=HDR), timeout=25).read()
    return gzip.decompress(d) if d[:2] == b'\x1f\x8b' else d


def norm(s):
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    return set(re.findall(r'[a-z]{2,}', s))


LAB = json.load(open('lineup_lab.json', encoding='utf-8'))


def team_lookup(name, fullnames):
    """Ομαδα = το ροστερ που ταιριαζει τους περισσοτερους παικτες (ονομα tiebreak)."""
    best, bs = None, -1.0
    nt = norm(name)
    for tid, t in LAB['teams'].items():
        if t['lg'] != LG:
            continue
        hits = 0
        for fn in fullnames:
            toks = norm(fn)
            if any(len(toks & norm(p['nm'])) >= 1 for p in t['players']):
                hits += 1
        score = hits + 0.5 * len(nt & norm(t['name']))
        if score > bs:
            best, bs = tid, score
    return best


def player_lookup(tid, fullname):
    toks = norm(fullname)
    if not toks or not tid:
        return None
    best, bs = None, 0
    for p in LAB['teams'][tid]['players']:
        ov = len(toks & norm(p['nm']))
        if ov > bs:
            best, bs = p['id'], ov
    return best if bs >= 1 else None


def parse_team(url):
    """Βασικοι = ο ΠΡΩΤΟΣ παικτης καθε player_position_column (11 κολονες θεσεων στο
    γηπεδο)· οι εναλλακτικοι (next_sub) ερχονται δευτεροι μεσα στην ιδια κολονα."""
    h = get(BASE + url).decode('utf-8', 'replace')
    pat = re.compile(r'<div class="player_name"><a href="/([a-z0-9-]+)_\d+/"[^>]*>([^<]+)</a>')
    starters = []
    for seg in h.split('<div class="player_position_column')[1:]:
        m = pat.search(seg)
        if m:
            starters.append((m.group(1).replace('-', ' '), m.group(2).strip()))
    return starters


if __name__ == '__main__':
    try:
        h = get(BASE + '/').decode('utf-8', 'replace')
    except Exception as e:
        print(f'homepage σφαλμα: {type(e).__name__}')
        sys.exit(0)
    team_urls = sorted(set(re.findall(r'href="(/[a-z0-9-]+/\d+/)"', h)))
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='minutes')
    n = 0
    with open(OUT, 'a', encoding='utf-8') as fh:
        for u in team_urls:
            try:
                starters = parse_team(u)
            except Exception as e:
                print(f'  {u}: {type(e).__name__}', flush=True)
                continue
            if len(starters) < 11:
                print(f'  {u}: μονο {len(starters)} βασικοι — παραλειπεται', flush=True)
                continue
            starters = starters[:11]
            site_name = u.strip('/').rsplit('/', 1)[0].replace('-', ' ')
            tid = team_lookup(site_name, [fn for fn, _ in starters])
            players = [dict(nm=lbl, pid=player_lookup(tid, fn)) for fn, lbl in starters]
            ok = sum(1 for p in players if p['pid'])
            fh.write(json.dumps(dict(ts=ts, src='ligainsider', lg=LG, journee=None,
                                     team=site_name, tid=tid, formation=None, xi=players),
                                ensure_ascii=False) + '\n')
            print('  %-28s -> tid %s · ταιριασμα %d/11' % (site_name, tid, ok), flush=True)
            n += 1
            time.sleep(0.8)
    print('ΤΕΛΟΣ: %d ομαδες' % n)
