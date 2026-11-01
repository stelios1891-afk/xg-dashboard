"""euro_limits_timeline.py — 16/10/2026 (Στελιος: «απο το ιστορικο καταγραφης των οριων δειξε μου ποτε ανοιξαν τα ορια σιγα σιγα»).
euro_odds_hist.jsonl (Pinnacle, πεδιο lim απο 10/10): για καθε ματς, το οριο που ισχυε σε καθε σημειο χρονου πριν τη σεντρα (τελευταια
καταγραφη πριν απο εκεινη τη στιγμη) → διαμεσος / ελαχ.-μεγ. ανα διοργανωση & αγωνιστικη, για χαντικαπ (spreads), συνολα (totals), 1Χ2 (h2h).
+ για καθε ματς: ποτε (ωρες πριν, και μερα/ωρα Ελλαδας) αλλαξε το οριο και σε ποιο επιπεδο."""
import json, sys, collections, datetime as dt
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
GR = dt.timedelta(hours=3)
R = collections.defaultdict(list)
for l in open('euro_odds_hist.jsonl', encoding='utf-8'):
    r = json.loads(l)
    if r.get('lim'): R[r['mid']].append(r)
def T(s):
    d = dt.datetime.fromisoformat(s.replace('Z', '+00:00'))
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
P = {m['mid']: m for m in json.load(open('euro_projections.json', encoding='utf-8'))['matches']}
HS = (240, 168, 144, 120, 96, 72, 48, 36, 24, 12, 6, 3, 1, 0)
G = collections.defaultdict(list); FIRST = {}
NOW = dt.datetime.now(dt.timezone.utc)
for mid, rs in R.items():
    rs.sort(key=lambda r: r['t']); ko = T(rs[0]['ko']); m = P.get(mid, {})
    key = (rs[0]['comp'], m.get('round', '?'), (ko + GR).strftime('%d/%m'))
    for h in HS:
        cut = ko - dt.timedelta(hours=h); prev = [r for r in rs if T(r['t']) <= cut] if cut <= NOW else []   # μελλον → κενο
        G[(key, h)].append(prev[-1]['lim'] if prev else None)
    ch = []; last = None
    for r in rs:
        if T(r['t']) > ko: break
        v = (r['lim'].get('spreads'), r['lim'].get('totals'), r['lim'].get('h2h'))
        if v != last: ch.append(((ko - T(r['t'])).total_seconds() / 3600, (T(r['t']) + GR).strftime('%a %d/%m %H:%M'), v)); last = v
    FIRST[(key, mid)] = (m.get('home', '?'), m.get('away', '?'), ch)
keys = sorted({k for k, _ in G}, key=lambda k: (k[2][3:], k[2][:2], k[0]))
for key in keys:
    print(f'\n{"=" * 120}\n{key[0]} αγωνιστικη {key[1]} · σεντρα {key[2]} · ματς {len(G[(key, 0)])}')
    print('   ωρες πριν │ ' + ' │ '.join(f'{h:>5d}ω' if h else 'σεντρα' for h in HS))
    for j, nm in ((0, 'spreads'), (1, 'totals'), (2, 'h2h')):
        cells = []
        for h in HS:
            v = [x[nm] for x in G[(key, h)] if x and x.get(nm)]
            cells.append(f'{int(np.median(v)):>6d}' if v else '     —')
        print(f'   {"χαντικαπ" if j == 0 else ("συνολα  " if j == 1 else "1Χ2     ")}  │ ' + ' │ '.join(cells))
# παραδειγμα αλλαγων για ενα-δυο ματς ανα αγωνιστικη
print(f'\n{"=" * 120}\nΑΛΛΑΓΕΣ ΟΡΙΟΥ ΑΝΑ ΜΑΤΣ (χαντικαπ / συνολα / 1Χ2) — 2 ματς ανα αγωνιστικη, ωρα Ελλαδας')
seen = collections.Counter()
for (key, mid), (h, a, ch) in sorted(FIRST.items(), key=lambda x: (x[0][0][2][3:], x[0][0][2][:2], x[0][0][0])):
    if seen[key] >= 2: continue
    seen[key] += 1
    print(f'   {key[0][:10]} {key[2]} {h} – {a}: ' + ' → '.join(f'{c[1]} ({c[0]:.0f}ω) {c[2][0]}/{c[2][1]}/{c[2][2]}' for c in ch))
