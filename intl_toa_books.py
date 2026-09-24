# -*- coding: utf-8 -*-
"""intl_toa_books.py — ΔΙΑΓΝΩΣΤΙΚΟ (25/9, ερωτηση Στελιου: «δεν υπαρχει αλλη εταιρια που εχει ολες τις αγορες;»).
Ολα τα βιβλια regions eu+uk, markets h2h+spreads+totals (~6 credits): ανα βιβλιο ποσα ματς NL καλυπτει σε καθε αγορα
(χωρια League A = ματς με Pinnacle, και B-D = χωρις Pinnacle) + μεση γκανιοτα ανα αγορα. Μονο προ-ΚΟ ματς."""
import os, sys, datetime, statistics as st, requests
sys.stdout.reconfigure(encoding='utf-8')
K = os.environ['TOA_KEY']; SPORT = 'soccer_uefa_nations_league'
now = datetime.datetime.now(datetime.timezone.utc)
r = requests.get(f'https://api.the-odds-api.com/v4/sports/{SPORT}/odds',
                 params=dict(apiKey=K, regions='eu,uk', markets='h2h,spreads,totals', oddsFormat='decimal'), timeout=60)
print(f"status {r.status_code} · credits left {r.headers.get('x-requests-remaining')} · κοστος {r.headers.get('x-requests-last')}")
ev = [e for e in r.json() if datetime.datetime.fromisoformat(e['commence_time'].replace('Z', '+00:00')) > now]
isA = {e['id']: any(b['key'] == 'pinnacle' for b in e['bookmakers']) for e in ev}
nA = sum(isA.values()); nB = len(ev) - nA
print(f'προ-ΚΟ ματς: {len(ev)} (με Pinnacle = League A: {nA} · χωρις Pinnacle = B-D: {nB})\n')
cov = {}; mg = {}
def over(outs):
    ps = [o.get('price') for o in outs if o.get('price')]
    return sum(1 / p for p in ps) - 1 if len(ps) >= 2 else None
for e in ev:
    grp = 'A' if isA[e['id']] else 'BD'
    for b in e['bookmakers']:
        for m in b['markets']:
            if m['key'] not in ('h2h', 'spreads', 'totals'): continue
            cov.setdefault(b['key'], {}).setdefault((grp, m['key']), 0)
            cov[b['key']][(grp, m['key'])] += 1
            v = over(m['outcomes'])
            if v is not None and v < 0.25:
                mg.setdefault(b['key'], {}).setdefault(m['key'], []).append(v)
rows = []
for bk, c in cov.items():
    rows.append((c.get(('BD', 'spreads'), 0) + c.get(('BD', 'totals'), 0), bk, c))
print(f"{'βιβλιο':18s} | B-D (απο {nB}): 1Χ2 AH  OU | A (απο {nA}): 1Χ2 AH  OU | μεση γκανιοτα 1Χ2 / AH / OU")
for _, bk, c in sorted(rows, reverse=True):
    g = mg.get(bk, {})
    f = lambda k: f"{st.mean(g[k])*100:4.1f}%" if g.get(k) else '  —  '
    print(f"{bk:18s} |        {c.get(('BD','h2h'),0):3d} {c.get(('BD','spreads'),0):3d} {c.get(('BD','totals'),0):3d} |"
          f"        {c.get(('A','h2h'),0):3d} {c.get(('A','spreads'),0):3d} {c.get(('A','totals'),0):3d} | {f('h2h')} / {f('spreads')} / {f('totals')}")
