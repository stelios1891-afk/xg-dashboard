"""
goal_stats.py — Goal Stats ανα ομαδα (Total/Home/Away/Last 8) + goal timing ανα 15λεπτο.

Πηγη: data_{league}_{season}.json (τελικα σκορ hs/as + λεπτα γκολ απο shots με goal=true).
Χρησιμοποιει την τελευταια ΠΛΗΡΗ σεζον (2526)· ανανεωση μολις μπουν φετινα αποτελεσματα.
"""
import os, json
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEASON_DEFAULT = '2526'

def _load(league, season):
    with open(os.path.join(ROOT, f'data_{league}_{season}.json'), encoding='utf-8') as fh:
        return json.load(fh)

_NAME2ID = {}
def _matches_by_team(league, season):
    d = _load(league, season)
    teams = defaultdict(list)
    for m in d.values():
        h, a = m['home'], m['away']; hs, as_ = m['hs'], m['as']; date = m['date']
        _NAME2ID[h['name']] = h['id']; _NAME2ID[a['name']] = a['id']
        gmin = defaultdict(list)
        for s in m.get('shots', []):
            if s.get('goal'):
                gmin[s['tid']].append(s.get('min', 0))
        teams[h['name']].append(dict(date=date, is_home=1, gf=hs, ga=as_,
                                     gmf=gmin[h['id']], gma=gmin[a['id']]))
        teams[a['name']].append(dict(date=date, is_home=0, gf=as_, ga=hs,
                                     gmf=gmin[a['id']], gma=gmin[h['id']]))
    return teams

def team_id(name):
    return _NAME2ID.get(name)

def _filter(ms, filt):
    ms = sorted(ms, key=lambda x: x['date'])
    if filt == 'home':  return [m for m in ms if m['is_home']]
    if filt == 'away':  return [m for m in ms if not m['is_home']]
    if filt == 'last8': return ms[-8:]
    return ms

COLS = [('gp', 'GP'), ('avg', 'AVG'), ('o05', '0.5+'), ('o15', '1.5+'), ('o25', '2.5+'),
        ('o35', '3.5+'), ('o45', '4.5+'), ('o55', '5.5+'), ('btts', 'BTTS'), ('cs', 'CS'),
        ('fts', 'FTS'), ('wtn', 'WTN'), ('ltn', 'LTN')]
PCT_COLS = {'o05', 'o15', 'o25', 'o35', 'o45', 'o55', 'btts', 'cs', 'fts', 'wtn', 'ltn'}

def team_stats(league, season=SEASON_DEFAULT, filt='total'):
    teams = _matches_by_team(league, season)
    rows = []
    for name, ms in teams.items():
        f = _filter(ms, filt)
        n = len(f)
        if n == 0:
            continue
        tot = [m['gf'] + m['ga'] for m in f]
        p = lambda c: 100.0 * sum(1 for m in f if c(m)) / n
        ov = lambda k: 100.0 * sum(1 for t in tot if t >= k) / n
        rows.append(dict(team=name, tid=_NAME2ID.get(name), gp=n, avg=sum(tot) / n,
                         o05=ov(1), o15=ov(2), o25=ov(3), o35=ov(4), o45=ov(5), o55=ov(6),
                         btts=p(lambda m: m['gf'] >= 1 and m['ga'] >= 1),
                         cs=p(lambda m: m['ga'] == 0),
                         fts=p(lambda m: m['gf'] == 0),
                         wtn=p(lambda m: m['gf'] > m['ga'] and m['ga'] == 0),
                         ltn=p(lambda m: m['ga'] > m['gf'] and m['gf'] == 0)))
    rows.sort(key=lambda r: -r['avg'])
    return rows

def league_avg(rows):
    if not rows:
        return {}
    keys = [k for k, _ in COLS]
    return {k: sum(r[k] for r in rows) / len(rows) for k in keys}

BUCKETS = ['1-15', '16-30', '31-45', '46-60', '61-75', '76-90']
def _bucket(mn):
    if mn <= 0:
        return 0
    return min((mn - 1) // 15, 5)

def team_timing(league, season=SEASON_DEFAULT, filt='total'):
    """Ανα ομαδα: γκολ ΥΠΕΡ & ΚΑΤΑ σε καθε 15λεπτο (counts + % κατανομη)."""
    teams = _matches_by_team(league, season)
    rows = []
    for name, ms in teams.items():
        f = _filter(ms, filt)
        if not f:
            continue
        gf = [0] * 6; ga = [0] * 6
        for m in f:
            for mn in m['gmf']:
                gf[_bucket(mn)] += 1
            for mn in m['gma']:
                ga[_bucket(mn)] += 1
        tf, ta = sum(gf), sum(ga)
        rows.append(dict(team=name, tid=_NAME2ID.get(name), gp=len(f), gf=gf, ga=ga, tot_f=tf, tot_a=ta,
                         gf_pct=[100 * x / tf if tf else 0 for x in gf],
                         ga_pct=[100 * x / ta if ta else 0 for x in ga]))
    rows.sort(key=lambda r: -r['tot_f'])
    return rows

if __name__ == '__main__':
    import sys
    lg = sys.argv[1] if len(sys.argv) > 1 else 'EPL'
    rows = team_stats(lg)
    print(f'{lg} — Goal Stats (Total, σεζον {SEASON_DEFAULT}) — {len(rows)} ομαδες\n')
    hdr = f"{'TEAM':22s} " + ' '.join(f'{lbl:>5s}' for _, lbl in COLS)
    print(hdr)
    for r in rows:
        line = f"{r['team'][:22]:22s} {r['gp']:>5d} {r['avg']:>5.2f} " + ' '.join(
            f"{r[k]:>4.0f}%" for k, _ in COLS[2:])
        print(line)
    la = league_avg(rows)
    print(f"\n{'League avg':22s} {la['gp']:>5.1f} {la['avg']:>5.2f} " +
          ' '.join(f"{la[k]:>4.0f}%" for k, _ in COLS[2:]))
    print('\n--- timing (πρωτες 3 ομαδες) ---')
    for r in team_timing(lg)[:3]:
        print(f"{r['team'][:18]:18s} FOR {r['gf']} (tot {r['tot_f']})  AGAINST {r['ga']} (tot {r['tot_a']})")
