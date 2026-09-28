# -*- coding: utf-8 -*-
"""nba_player_projection.py — NBA: ΠΡΟΒΟΛΗ ΑΞΙΑΣ ΠΑΙΚΤΗ για τη νεα σεζον (28/9/2026, αιτημα Στελιου: «ποσο καλυτερες/χειροτερες
εγιναν οι ομαδες — και οι σταθερες»).
Αξια σεζον = μεσος ορος διαθεσιμων DARKO dpm / LEBRON / BPM (π./100 πανω απο μεσο παικτη). Λεπτα & ηλικια: LEBRON Minutes /
  B-R mp, ηλικια DARKO (αλλιως B-R).
ΜΕΤΡΗΣΗ ΜΟΝΟ ΣΕ ΣΕΖΟΝ ΠΡΙΝ ΤΟ ΤΕΣΤ (ζευγαρια 2015→2016 … 2020→2021):
  (1) v_νεα = a + b·v_περσι + καμπυλη ηλικιας c(ηλικια φετος) — παικτες με ≥300′ και τις δυο σεζον, βαρος λεπτα.
  (2) ΡΟΥΚΙ: αξια & λεπτα/ματς 1ης σεζον ανα ομαδα θεσης draft (1-3, 4-10, 11-20, 21-30, 2ος γυρος, χωρις draft) — drafts 2014-2020.
ΕΛΕΓΧΟΣ εκτος δειγματος 2022-2026: ποσο καλα προβλεπει τη φετινη αξια (RMSE) το «σκετο περσι» vs η προβολη.
Εξοδος: nba_player_proj.json · nba_player_projection_out.txt"""
import sys, re, json, unicodedata
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))
def nk(s):
    s = unicodedata.normalize('NFD', str(s)); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    s = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', s); return ' '.join(re.findall(r'[a-z]+', s))
def load(f): return json.load(open(f'nba_rapm/{f}.json', encoding='utf-8'))
DK, LB = load('DARKO'), load('lebron')
NAME2ID = {}
for r in DK + LB: NAME2ID.setdefault(nk(r['player_name']), str(r['nba_id']))
V = {}; MP = {}; AGE = {}
for r in DK:
    k = (str(r['nba_id']), int(r['season']))
    if r.get('dpm') is not None: V.setdefault(k, {})['dk'] = r['dpm']
    if r.get('age') is not None: AGE[k] = float(r['age'])
for r in LB:
    k = (str(r['nba_id']), int(r['year']))
    if r.get('LEBRON') is not None: V.setdefault(k, {})['lb'] = r['LEBRON']
    if r.get('Minutes'): MP[k] = float(r['Minutes'])
GP = {}
for y in range(2014, 2026):
    t = open(f'bbref_cache/NBA_{y}_advanced.html', encoding='utf-8', errors='ignore').read()
    best = {}
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.S):
        nm = re.search(r'data-stat="name_display"[^>]*>(?:<a[^>]*>)?([^<]+)', tr)
        b = re.search(r'data-stat="bpm"[^>]*>([-\d.]+)<', tr); mp = re.search(r'data-stat="mp"[^>]*>(\d+)<', tr)
        ag = re.search(r'data-stat="age"[^>]*>(\d+)<', tr); g = re.search(r'data-stat="games"[^>]*>(\d+)<', tr)
        if not (nm and mp): continue
        i = NAME2ID.get(nk(nm.group(1)))
        if not i: continue
        m = int(mp.group(1))
        if i in best and best[i][1] >= m: continue
        best[i] = (float(b.group(1)) if b else None, m, int(ag.group(1)) if ag else None, int(g.group(1)) if g else None)
    for i, (b, m, ag, g) in best.items():
        k = (i, y)
        if b is not None: V.setdefault(k, {})['bpm'] = b
        MP.setdefault(k, float(m)); GP[k] = g
        if k not in AGE and ag is not None: AGE[k] = float(ag)
def val(k):
    d = V.get(k)
    return float(np.mean(list(d.values()))) if d else None
# ---- (1) καμπυλη ηλικιας + παλινδρομηση ----
def pairs(years):
    rows = []
    for (i, s), d in V.items():
        if s not in years: continue
        k0 = (i, s - 1)
        v0, v1 = val(k0), val((i, s))
        if v0 is None or v1 is None or MP.get(k0, 0) < 300 or MP.get((i, s), 0) < 300 or (i, s) not in AGE: continue
        rows.append((v0, v1, AGE[(i, s)], MP[(i, s)], s))
    return pd.DataFrame(rows, columns=['v0', 'v1', 'age', 'mp', 's'])
AB = [(0, 21), (21, 23), (23, 25), (25, 27), (27, 29), (29, 31), (31, 33), (33, 99)]
ABL = ['≤20', '21-22', '23-24', '25-26', '27-28', '29-30', '31-32', '33+']
def design(df):
    X = [np.ones(len(df)), df.v0.values] + [((df.age >= lo) & (df.age < hi)).astype(float).values for lo, hi in AB[1:]]
    return np.column_stack(X)
TR = pairs(range(2016, 2022)); TE = pairs(range(2022, 2027))
w = TR.mp.values
coef = np.linalg.lstsq(design(TR) * np.sqrt(w)[:, None], TR.v1.values * np.sqrt(w), rcond=None)[0]
a, b = coef[0], coef[1]; ages = dict(zip(ABL, [0.0] + list(coef[2:])))
P(f'(1) προβολη (μετρημενη σε {len(TR)} ζευγαρια 2015→2021): v_νεα = {a:+.2f} + {b:.2f}·v_περσι + ηλικια')
P('    ηλικια (φετος): ' + ' · '.join(f'{k} {v + a:+.2f}' for k, v in ages.items()) + '   (π./100 που προστιθενται για παικτη μεσου επιπεδου)')
def proj(v0, age):
    j = next(n for n, (lo, hi) in enumerate(AB) if lo <= age < hi)
    return a + b * v0 + (coef[1 + j] if j > 0 else 0.0)
for nm, D in (('εκπαιδευση', TR), ('ΕΚΤΟΣ ΔΕΙΓΜΑΤΟΣ 2022-26', TE)):
    ww = D.mp.values
    r0 = np.sqrt(np.average((D.v1 - D.v0) ** 2, weights=ww)); rb = np.sqrt(np.average((D.v1 - b * D.v0 - a) ** 2, weights=ww))
    rp = np.sqrt(np.average((D.v1 - [proj(x, y) for x, y in zip(D.v0, D.age)]) ** 2, weights=ww))
    P(f'    {nm:24s} ({len(D)}): σφαλμα προβλεψης φετινης αξιας — σκετο περσι {r0:.3f} · + παλινδρομηση {rb:.3f} · + ηλικια {rp:.3f}')
    for s in sorted(D.s.unique()) if 'ΕΚΤΟΣ' in nm else []:
        d = D[D.s == s]; wd = d.mp.values
        P(f'      {s}: {np.sqrt(np.average((d.v1 - d.v0) ** 2, weights=wd)):.3f} → {np.sqrt(np.average((d.v1 - [proj(x, y) for x, y in zip(d.v0, d.age)]) ** 2, weights=wd)):.3f}')
# ---- (2) ρουκι ανα θεση draft ----
PB = [(1, 3, '1-3'), (4, 10, '4-10'), (11, 20, '11-20'), (21, 30, '21-30'), (31, 60, '2ος γυρος')]
DRAFT = {}
for y in range(2014, 2026):
    t = open(f'bbref_cache/draft_{y}.html', encoding='utf-8', errors='ignore').read()
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.S):
        pk = re.search(r'data-stat="pick_overall"[^>]*>(?:<a[^>]*>)?(\d+)<', tr); nm = re.search(r'data-stat="player"[^>]*>(?:<a[^>]*>)?([^<]+)', tr)
        if pk and nm: DRAFT[nk(nm.group(1))] = (y, int(pk.group(1)))
def bucket(pick): return next(l for lo, hi, l in PB if lo <= pick <= hi)
first_season = {}
for (i, s) in list(MP):
    if MP[(i, s)] > 0 and (i not in first_season or s < first_season[i]): first_season[i] = s
ID2NAME = {}
for r in DK + LB: ID2NAME.setdefault(str(r['nba_id']), nk(r['player_name']))
rk = {l: [] for *_, l in PB}; rk['χωρις draft'] = []
for i, s in first_season.items():
    if not (2016 <= s <= 2021): continue
    v = val((i, s))
    if v is None: continue
    dr = DRAFT.get(ID2NAME.get(i, ''))
    mpg = MP[(i, s)] / GP[(i, s)] if GP.get((i, s)) else None
    lab = bucket(dr[1]) if dr and dr[0] == s - 1 else ('χωρις draft' if not dr else None)
    if lab: rk[lab].append((v, MP[(i, s)], mpg))
ROOK = {}
P('(2) ρουκι (1η σεζον, drafts 2015-2020): ')
for l, L in rk.items():
    if not L: continue
    A_ = np.array([(x[0], x[1]) for x in L]); mp_ = [x[2] for x in L if x[2]]
    ROOK[l] = dict(v=round(float(np.average(A_[:, 0], weights=A_[:, 1])), 2), mpg=round(float(np.median(mp_)), 1), n=len(L))
    P(f'    {l:12s}: αξια {ROOK[l]["v"]:+.2f} · λεπτα/ματς {ROOK[l]["mpg"]:.1f} · n {len(L)}')
json.dump(dict(a=a, b=b, age_bins=AB, age_coef=[0.0] + list(coef[2:]), rookie=ROOK,
               draft={k: v for k, v in DRAFT.items()}, ages={f'{i}|{s}': v for (i, s), v in AGE.items()}),
          open('nba_player_proj.json', 'w', encoding='utf-8'), ensure_ascii=False)
open('nba_player_projection_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
