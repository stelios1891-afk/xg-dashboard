# -*- coding: utf-8 -*-
"""euro_elo_hist_fetch.py — 5/11/2026: ιστορικο Elo των ομαδων πρωτης κατηγοριας (clubelo_current level 1) των χωρων με αξιες παικτων, απο το chart της σελιδας ομαδας του ClubElo (το API ανα ημερομηνια δινει 502).
Εξοδος: clubelo_cache/level1_hist.json {χωρα: {slug: [[ημ/νια, Elo], ...]}}. 1 αιτημα/δευτ. Ξανατρεχει απο εκει που εμεινε. Για το euro_elo_level (επιπεδο λιγκας απο Elo)."""
import sys, os, re, json, time, glob, unicodedata
import pandas as pd, requests
sys.stdout.reconfigure(encoding='utf-8')
from euro_engine import player_offsets
POFF = player_offsets()
_s = open('euro_inseason_eu_test.py', encoding='utf-8').read(); ns = {}
exec(_s[_s.index('LG_COUNTRY = {'):_s.index('# ================================================================ V0/V4/V5')], ns)
CCS = sorted({ns['LG_COUNTRY'][lg] for lg in POFF if lg in ns['LG_COUNTRY']})
H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36'}
OUT = 'clubelo_cache/level1_hist.json'
RES = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
OLD = {}
for f in glob.glob('clubelo_cache/team_*.json'):
    j = json.load(open(f, encoding='utf-8'))
    if j.get('series'): OLD[j['slug']] = j['series']
C = pd.read_csv('clubelo_current.csv'); C = C[C.level == 1]
def nk(x):
    x = unicodedata.normalize('NFKD', str(x)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', x)
def series(slug):
    if slug in OLD: return OLD[slug]
    r = requests.get(f'https://clubelo.com/{slug}', headers=H, timeout=25); time.sleep(1.0)
    if r.status_code != 200: return None
    ss = [s for s in re.findall(r'<script[^>]*>(.*?)</script>', r.text, flags=re.S) if 'vegaJson' in s]
    if not ss: return None
    s = ss[0]; js, _ = json.JSONDecoder().raw_decode(s[s.find('{'):])
    for v in js['datasets'].values():
        if v and isinstance(v[0], dict) and 'Elo' in v[0] and 'Date' in v[0]:
            return sorted((x['Date'][:10], float(x['Elo'])) for x in v)
    return None
T0 = time.time(); tot = bad = 0
for cc in CCS:
    fp = f'clubelo_cache/country_{cc}.html'
    if not os.path.exists(fp): print(cc, 'χωρις σελιδα χωρας'); continue
    t = open(fp, encoding='utf-8').read()
    links = {}
    for slug, name in re.findall(r'<a href="/([^"/]+)"[^>]*>\s*(?:<span[^>]*>)?\s*([^<]+?)\s*<', t):
        links.setdefault(nk(name), slug); links.setdefault(nk(slug), slug)
    RES.setdefault(cc, {}); miss = []
    for name in C[C.country == cc].name:
        slug = links.get(nk(name))
        if not slug: miss.append(name); continue
        if slug in RES[cc]: continue
        try: se = series(slug)
        except Exception: se = None
        if se: RES[cc][slug] = se; tot += 1
        else: bad += 1
    json.dump(RES, open(OUT, 'w', encoding='utf-8'))
    print(f'{cc}: ομαδες {len(RES[cc])}/{(C.country == cc).sum()} · χωρις συνδεσμο {miss[:6]} [{time.time() - T0:.0f}s]', flush=True)
print('ΤΕΛΟΣ', tot, 'νεες · αποτυχιες', bad, flush=True)
