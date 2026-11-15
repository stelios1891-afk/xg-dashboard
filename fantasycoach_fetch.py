# -*- coding: utf-8 -*-
"""fantasycoach_fetch.py — Projected lineups Ligue 1 απο fantasy-coach.fr (πηγη Στελιου, 1/9).

Το site (l1.compos.fantasy-coach.fr) σερβιρει δημοσιο Google Apps Script API:
  ?meta=1            -> λιστα διαθεσιμων αγωνιστικων (ανανεωνεται Πεμ/Παρ)
  ?journee=N         -> 18 ομαδες x {equipe, formation, joueurs[11 επωνυμα], score}
Δομη ΑΝΑ ΟΜΑΔΑ (οχι ανα ματς) -> γραφουμε per-team snapshots στο projected_fc.jsonl·
το dashboard τα ζευγαρωνει με το ματς (home tid + away tid). Ξανατρεξιμο = νεο snapshot.
"""
import sys, json, re, gzip, time, datetime, unicodedata, urllib.request
sys.stdout.reconfigure(encoding='utf-8')

API = ('https://script.google.com/macros/s/'
       'AKfycby7k1DeAKMJFeSLMCHtQntyU0hGseKmN4ZMxuMMDjugFTh-H4wTNvk5TA32CM5By7aMng/exec')
HDR = {'User-Agent': 'Mozilla/5.0', 'Accept': '*/*', 'Accept-Encoding': 'gzip'}
OUT = 'projected_fc.jsonl'
LG = 'Ligue1'


def get(u):
    d = urllib.request.urlopen(urllib.request.Request(u, headers=HDR), timeout=30).read()
    return gzip.decompress(d) if d[:2] == b'\x1f\x8b' else d


def norm(s):
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    return set(re.findall(r'[a-z]{2,}', s))


LAB = json.load(open('lineup_lab.json', encoding='utf-8'))


def team_lookup(name, surnames):
    """Ομαδα = το ροστερ που ταιριαζει τους περισσοτερους απο τους 11 (ονομα = tiebreak).
    (Μαθημα: 'Paris SG' ταιριαζε στην Paris FC με σκετο ονομα — τα ροστερ δεν μπερδευονται.)"""
    best, bs = None, -1.0
    nt = norm(name)
    for tid, t in LAB['teams'].items():
        if t['lg'] != LG:
            continue
        hits = sum(1 for s in surnames if _player_in(t, s))
        score = hits + 0.5 * len(nt & norm(t['name']))
        if score > bs:
            best, bs = tid, score
    return best


def _player_in(team, surname):
    toks = norm(surname.split('(')[0].strip())
    if not toks:
        return False
    return any(len(toks & norm(p['nm'])) >= 1 for p in team['players'])


def player_lookup(tid, surname):
    """Επωνυμο (ισως 'Ονομα (εναλλακτικος)') -> pid στο ροστερ μας."""
    main = surname.split('(')[0].strip()
    toks = norm(main)
    if not toks or not tid:
        return None
    best, bs = None, 0
    for p in LAB['teams'][tid]['players']:
        ov = len(toks & norm(p['nm']))
        if ov > bs:
            best, bs = p['id'], ov
    return best if bs >= 1 else None


if __name__ == '__main__':
    try:
        meta = json.loads(get(API + '?meta=1'))
        journees = sorted(int(x) for x in meta)
    except Exception as e:
        print(f'meta σφαλμα: {type(e).__name__}')
        sys.exit(0)
    if not journees:
        print('καμια διαθεσιμη αγωνιστικη')
        sys.exit(0)
    j = journees[-1]                       # η πιο προσφατη
    try:
        data = json.loads(get(API + '?journee=%d' % j))
    except Exception as e:
        print(f'journee {j} σφαλμα: {type(e).__name__}')
        sys.exit(0)
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='minutes')
    n = 0
    with open(OUT, 'a', encoding='utf-8') as fh:
        for e in (data.get('equipes') or []):
            tid = team_lookup(e.get('equipe'), e.get('joueurs') or [])
            players = []
            for nm in (e.get('joueurs') or []):
                players.append(dict(nm=nm, pid=player_lookup(tid, nm)))
            ok = sum(1 for p in players if p['pid'])
            fh.write(json.dumps(dict(ts=ts, src='fantasy-coach', lg=LG, journee=j,
                                     team=e.get('equipe'), tid=tid,
                                     formation=e.get('formation'), xi=players),
                                ensure_ascii=False) + '\n')
            print('  %-16s -> tid %s · ταιριασμα %d/11' % (e.get('equipe'), tid, ok), flush=True)
            n += 1
    print('ΤΕΛΟΣ: journee %d, %d ομαδες' % (j, n))
