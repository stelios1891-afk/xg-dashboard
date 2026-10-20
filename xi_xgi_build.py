# -*- coding: utf-8 -*-
"""xi_xgi_build.py — 21/10/2026: xGI (xG + xA ανα 90′) ΑΝΑ ΠΑΙΚΤΗ → επιθετικη δυναμη ενδεκαδας (μονο πληροφορια ΠΡΙΝ το ματς).
Ρυθμος παικτη = φθινων (0.95/εμφανιση) αθροισμα xGI / φθινοντα 90λεπτα, με ΣΥΡΡΙΚΝΩΣΗ προς τον μεσο της θεσης του (K = 5 × 90′ ψευδο-λεπτα):
  ο αντικαταστατης με λιγα λεπτα μετραει σχεδον οσο ο μεσος παικτης της θεσης του (απαντα στο «μικρο δειγμα του αντικαταστατη»).
Ενδεκαδα: A = αθροισμα ρυθμων των 11 βασικων (+ χωριστα xG-μονο και xA-μονο) · Δ = A σημερα − φθινων (0.9) μεσος προηγουμενων (μονο πρωταθλημα).
Πηγες: player_xgi.jsonl (λεπτα, xG, xA ανα παικτη/ματς) · core7_squads.json (βασικοι) · player_matches.json (θεσεις).  ΕΞΟΔΟΣ: xi_xgi_rows.csv"""
import sys, json, glob, re, collections, datetime as dt
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
LG = ('EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'Eredivisie', 'PrimeiraLiga')
FM = {}
for lg in LG:
    for f in glob.glob(f'data_{lg}_*.json'):
        for k, v in json.load(open(f, encoding='utf-8')).items():
            try: d = dt.datetime.strptime(v['date'], '%a, %b %d, %Y, %H:%M UTC')
            except Exception: continue
            FM[str(k)] = dict(date=d, hid=v['home']['id'], aid=v['away']['id'])
SQ = json.load(open('core7_squads.json', encoding='utf-8'))
PM = json.load(open('player_matches.json', encoding='utf-8'))
X = {}
for l in open('player_xgi.jsonl', encoding='utf-8'):
    r = json.loads(l); X[r['mid']] = r['p']
ORDER = sorted([k for k in FM if k in SQ and SQ[k].get('h') and SQ[k].get('a') and k in X], key=lambda k: FM[k]['date'])
POS = {}
for k in ORDER:
    for s in ('h', 'a'):
        for e in ((PM.get(k) or {}).get(s) or {}).get('p', []) or []:
            POS[str(e[0])] = e[3] if e[3] in (0, 1, 2, 3) else 2
# μεσος ρυθμος ανα θεση (απο ολα τα δεδομενα — μονο για τη συρρικνωση)
acc = collections.defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])
for k in ORDER:
    for pid, (mn, xg, xa) in X[k].items():
        if mn and mn > 0:
            a = acc[POS.get(pid, 2)]; a[0] += xg; a[1] += xa; a[2] += mn / 90.0
MU = {p: ((v[0] + v[1]) / v[2], v[0] / v[2], v[1] / v[2]) for p, v in acc.items() if v[2] > 0}
K = 5.0
ST = {}                  # pid -> [Σw·xgi, Σw·xg, Σw·xa, Σw·90s]
BASE = collections.defaultdict(dict)
OUT = []
def rate(pid):
    s = ST.get(pid); mu = MU.get(POS.get(pid, 2), (0.3, 0.2, 0.1))
    if not s: return mu
    return tuple((s[i] + K * mu[i]) / (s[3] + K) for i in range(3))
for k in ORDER:
    m = FM[k]; sq = SQ[k]; rec = dict(mid=k)
    for fs, tid in (('h', m['hid']), ('a', m['aid'])):
        st = [str(p) for p in sq[fs]['st']]
        rs = [rate(p) for p in st]
        vals = {'XGI': sum(r[0] for r in rs), 'XG': sum(r[1] for r in rs), 'XA': sum(r[2] for r in rs),
                'XGIat': sum(r[0] for p, r in zip(st, rs) if POS.get(p, 2) in (2, 3))}
        for me, S in vals.items():
            b = BASE[tid].get(me)
            rec[f'{me}_{fs}'] = S - b if b is not None else np.nan
            rec[f'{me}_{fs}_lvl'] = S
            BASE[tid][me] = S if b is None else 0.9 * b + 0.1 * S
    OUT.append(rec)
    for pid, (mn, xg, xa) in X[k].items():
        if not mn or mn <= 0: continue
        s = ST.get(pid, [0.0, 0.0, 0.0, 0.0])
        ST[pid] = [s[0] * 0.95 + (xg + xa), s[1] * 0.95 + xg, s[2] * 0.95 + xa, s[3] * 0.95 + mn / 90.0]
pd.DataFrame(OUT).to_csv('xi_xgi_rows.csv', index=False)
print('ετοιμο xi_xgi_rows.csv', len(OUT), '· μεσοι ρυθμοι θεσεων (xGI/90):', {p: round(v[0], 3) for p, v in MU.items()})
