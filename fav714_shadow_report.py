"""
fav714_shadow_report.py — 9/10/2026: αποτελεσματα ΣΚΙΑΣ «κοντα φαβορι 7-14» (dom_fav714_shadow.jsonl, scanner).
Για καθε ματς: η ΤΕΛΕΥΤΑΙΑ καταγραφη πριν τη σεντρα = κλεισιμο (πηγη τιμων scanner = Pinnacle). Pick = αν πληρουσε τον κανονα εκει (q).
Αποτελεσμα απο data_{λιγκα}_2627.json (FotMob ids). Συγκριση: ΟΛΑ τα κοντα φαβορι 7-14 τυφλα (ιδιο αρχειο).
Κριση (Στελιος, τελος σεζον): σκια θετικη και > τυφλα, σε ≥5/7 λιγκες χωρις μεγαλη αρνητικη.
"""
import sys, json, datetime
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')
import picks
LAST = {}
for ln in open('dom_fav714_shadow.jsonl', encoding='utf-8'):
    try: r = json.loads(ln)
    except Exception: continue
    ko = datetime.datetime.fromisoformat(str(r['ko']).replace('Z', '+00:00')); seen = datetime.datetime.fromisoformat(r['seen'].replace('Z', '+00:00'))
    if seen.tzinfo is None: seen = seen.replace(tzinfo=datetime.timezone.utc)
    if seen >= ko: continue
    k = (r['hid'], r['aid'], str(r['ko'])[:10])
    if k not in LAST or r['seen'] > LAST[k]['seen']: LAST[k] = r
RES = {}
for lg in ('EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'PrimeiraLiga', 'Eredivisie'):
    try: d = json.load(open(f'data_{lg}_2627.json', encoding='utf-8'))
    except FileNotFoundError: continue
    for m in d.values():
        if m.get('hs') is None: continue
        day = datetime.datetime.strptime(m['date'], '%a, %b %d, %Y, %H:%M UTC').strftime('%Y-%m-%d')
        RES[(m['home']['id'], m['away']['id'], day)] = m['hs'] - m['as']
rows = []
for k, r in LAST.items():
    gd = RES.get(k)
    if gd is None: continue
    rows.append(dict(lg=r['lg'], q=r['q'], pnl=picks.settle(gd, r['side'], r['hcap'], r['odds'])))
def fm(x):
    return f'n{len(x):3d} · {sum(p["pnl"] for p in x):+6.2f}u · ROI {100 * sum(p["pnl"] for p in x) / len(x):+6.1f}%' if x else 'n  0'
print(f'ΣΚΙΑ κοντα φαβορι 7-14 — κλεισιμο (Pinnacle scanner) · κριθηκαν {len(rows)} ματς · αναμενουν {len(LAST) - len(rows)}')
print('  picks κανονα   ', fm([p for p in rows if p['q']]))
print('  τυφλα ολα      ', fm(rows))
by = defaultdict(list)
for p in rows:
    if p['q']: by[p['lg']].append(p)
for lg, x in sorted(by.items()): print(f'    {lg:13s}', fm(x))
