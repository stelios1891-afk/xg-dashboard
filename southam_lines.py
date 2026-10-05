"""
southam_lines.py — 5/10/2026: ΓΡΑΜΜΕΣ Βραζιλιας/MLS (Nowgoal, Crown & SBOBET) σε χρονικα σημεια → southam_lines.csv.
Μια γραμμη ανα (ματς, βιβλιο, χρονος): χαντικαπ γηπεδουχου (αρνητικο = δινει) + αποδοσεις (δεκαδικες), συνολο + over/under.
Χρονοι: ανοιγμα · 72ω · 48ω · 24ω · 12ω · 3ω · κλεισιμο (τελευταια pre-match ≤ σεντρα+15′). Μετα-δεδομενα: σκορ, φαση (League/playoff), FotMob mid.
"""
import json, glob, os, sys
from datetime import datetime, timezone
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
MT = json.load(open('nowgoal_sa_matches.json', encoding='utf-8'))
MAP = json.load(open('nowgoal_sa_map.json', encoding='utf-8'))
NG2MID = {str(v['ng']): k for k, v in MAP.items()}
BOOK = {3: 'Crown', 31: 'SBOBET'}
WIN = [('open', None), ('72h', 72), ('48h', 48), ('24h', 24), ('12h', 12), ('3h', 3), ('close', 0)]

def pl(g):
    try:
        p = [float(x) for x in str(g).split('/')]
        if len(p) == 2 and p[0] < 0: p[1] = -abs(p[1])
        return sum(p) / len(p)
    except Exception:
        return None

def series(lst, ko, sign):
    out = []
    for t, u, g, d in lst or []:
        gl = pl(g)
        try: out.append((int(t), sign * gl, float(u) + 1, float(d) + 1))
        except (TypeError, ValueError): pass
    return sorted(x for x in out if x[0] <= ko + 900)

rows = []
for f in sorted(glob.glob('nowgoal_odds/*_Brazil.jsonl') + glob.glob('nowgoal_odds/*_MLS.jsonl')):
    for ln in open(f, encoding='utf-8'):
        r = json.loads(ln); ng = str(r['ng']); m = MT.get(ng)
        if not m or r['cid'] not in BOOK or not m.get('score') or '-' not in str(m['score']): continue
        try:
            hg, ag = (int(x) for x in m['score'].split('-'))
            ko = int(datetime.strptime(m['dt_utc'], '%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc).timestamp())
        except Exception:
            continue
        A = series(r.get('ah'), ko, -1); O = series(r.get('ou'), ko, 1)
        if not A: continue
        for w, h in WIN:
            def pick(S):
                if not S: return None
                if h is None: return S[0]
                s = [x for x in S if x[0] <= (ko + 900 if h == 0 else ko - h * 3600)]
                return s[-1] if s else None
            a = pick(A); o = pick(O)
            if a is None: continue
            rows.append(dict(ng=ng, mid=NG2MID.get(ng), league=m['lg'], season=str(m['sea']), ko=ko, date=m['date_utc'],
                             home=m['home'], away=m['away'], hg=hg, ag=ag, sub=m.get('sub'), rnd=m.get('rnd'),
                             book=BOOK[r['cid']], win=w, hrs=(ko - a[0]) / 3600,
                             ah=a[1], oh=a[2], oa=a[3],
                             ou=o[1] if o else None, ov=o[2] if o else None, un=o[3] if o else None))
L = pd.DataFrame(rows)
L.to_csv('southam_lines.csv', index=False)
print(f'southam_lines.csv: {len(L)} γραμμες · ματς {L.ng.nunique()}')
print(L[L.win == 'close'].groupby(['league', 'season', 'book']).size().unstack().to_string())
print('φασεις:', L.drop_duplicates('ng').groupby(['league', 'sub']).size().to_dict())
