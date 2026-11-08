"""euro_rotation_teams.py — 10/10/2026 (Στελιος: «ποιες ομαδες και απο ποια πρωταθληματα συνηθως κανουν ροτεισον? μονο νεο φορματ — τωρα το
κινητρο μενει ως το τελος»). ΜΟΝΟ 2425-2526, ΟΛΑ τα ευρωπαικα ματς (UCL/UEL/UECL) με ενδεκαδα (FotMob).
Rotation = αξια βασικων στο ευρωπαικο ματς / διαμεσος αξιας βασικων στα 5 τελευταια εγχωρια (≤45 μερες πριν) · + αλλαγες απο τη «βασικη» ενδεκαδα
(οι 11 με τις περισσοτερες συμμετοχες στα 5 εγχωρια). ≤0.85 = «εκανε rotation».
Ερωτηματα: ανα λιγκα · ανα ομαδα · ανα φαση · ΣΥΝΗΘΕΙΑ; (μονα/ζυγα ματς της ομαδας: οσοι κανουν rotation στα μισα, το κανουν και στα αλλα μισα;)
"""
import sys, glob, json, pickle, datetime as dt, numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
NEW = ('2425', '2526')
V6 = pickle.load(open('euro_v6_preds.pkl', 'rb'))
META = {str(m): (s, c, p, lh, la, d) for m, s, c, p, lh, la, d in zip(V6['mids'], V6['sea'], V6['comp'], V6['phase'], V6['lg_h'], V6['lg_a'], V6['date'])}
NAMES = {}
for f in glob.glob('data_Europe_*.json'):
    for mid, m in json.load(open(f, encoding='utf-8')).items():
        NAMES[str(mid)] = (int(m['home']['id']), int(m['away']['id']), m['home']['name'], m['away']['name'])
SQ = {}
for fn in ('euro_squads.json', 'core7_squads.json'):
    for mid, v in json.load(open(fn, encoding='utf-8')).items():
        if v: SQ[str(mid)] = v
DATE = {}
for f in glob.glob('data_*.json'):
    if 'Europe' in f: continue
    try: d = json.load(open(f, encoding='utf-8'))
    except Exception: continue
    for mid, m in d.items():
        try: DATE[str(mid)] = pd.Timestamp(dt.datetime.strptime(m['date'], '%a, %b %d, %Y, %H:%M UTC'))
        except Exception: pass
DOMXI = {}
for mid, v in SQ.items():
    t = DATE.get(mid)
    if t is None: continue
    for k in ('h', 'a'):
        x = v.get(k) or {}
        if x.get('t') and x.get('mv'): DOMXI.setdefault(int(x['t']), []).append((t, float(x['mv']), set(x.get('st') or [])))
for k in DOMXI: DOMXI[k].sort(key=lambda z: z[0])
rows = []
for mid, (sea, comp, phase, lgh, lga, ko) in META.items():
    if sea not in NEW or mid not in SQ or mid not in NAMES: continue
    ko = pd.Timestamp(ko)
    for side, tid, name, lg in (('h', NAMES[mid][0], NAMES[mid][2], lgh), ('a', NAMES[mid][1], NAMES[mid][3], lga)):
        x = SQ[mid].get(side) or {}
        if not x.get('mv'): continue
        prev = [z for z in DOMXI.get(tid, []) if ko - pd.Timedelta(days=45) <= z[0] < ko - pd.Timedelta(hours=12)][-5:]
        if len(prev) < 3: continue
        core = {}
        for z in prev:
            for p in z[2]: core[p] = core.get(p, 0) + 1
        top = set(sorted(core, key=lambda p: -core[p])[:11])
        rows.append(dict(sea=sea, comp=comp, phase=phase, team=name, lg=lg, ko=ko, home=side == 'h',
                         ratio=float(x['mv']) / np.median([z[1] for z in prev]), ch=len(set(x.get('st') or []) - top)))
T = pd.DataFrame(rows).sort_values('ko')
T['rot'] = T.ratio <= 0.85
CL = {'ChampionsLeague': 'UCL', 'EuropaLeague': 'UEL', 'ConferenceLeague': 'UECL'}
print(f'ομαδο-ματς νεας μορφης με ενδεκαδα και εγχωριο ιστορικο: {len(T)}')
print('\nΑΝΑ ΔΙΟΡΓΑΝΩΣΗ ΚΑΙ ΦΑΣΗ: αξια ενδεκαδας (διαμεσος) · % rotation (≤0.85) · μεσες αλλαγες')
for cm in CL:
    for ph, t in T[T.comp == cm].groupby('phase'):
        print(f'   {CL[cm]:5s} {ph:7s} n{len(t):4d} · {t.ratio.median():.2f} · {100 * t.rot.mean():3.0f}% · {t.ch.mean():.1f}')
print('\nΑΝΑ ΛΙΓΚΑ (UEL+UECL, ≥12 ομαδο-ματς) — ταξινομηση κατα % rotation:')
U = T[T.comp != 'ChampionsLeague']
g = U.groupby('lg').agg(n=('rot', 'size'), rot=('rot', 'mean'), ratio=('ratio', 'median'), ch=('ch', 'mean'), teams=('team', 'nunique')).query('n >= 12').sort_values('rot', ascending=False)
for lg, r in g.iterrows():
    print(f'   {lg:26s} n{r.n:3.0f} ({r.teams:.0f} ομαδες) · rotation {100 * r.rot:3.0f}% · αξια {r.ratio:.2f} · αλλαγες {r.ch:.1f}')
print('   (UCL για συγκριση: ' + ' · '.join(f'{lg} {100 * x.rot.mean():.0f}% (n{len(x)})' for lg, x in T[T.comp == 'ChampionsLeague'].groupby('lg') if len(x) >= 20) + ')')
print('\nΑΝΑ ΟΜΑΔΑ (UEL+UECL, ≥6 ευρωπαικα στη νεα μορφη) — οι 15 με το ΠΙΟ ΣΥΧΝΟ rotation και οι 10 με το λιγοτερο:')
gt = U.groupby(['team', 'lg']).agg(n=('rot', 'size'), rot=('rot', 'mean'), ratio=('ratio', 'median'), ch=('ch', 'mean')).query('n >= 6').sort_values('rot', ascending=False)
for (tm, lg), r in gt.head(15).iterrows():
    print(f'   {tm[:24]:24s} {lg[:16]:16s} n{r.n:2.0f} · rotation {100 * r.rot:3.0f}% · αξια {r.ratio:.2f} · αλλαγες {r.ch:.1f}')
print('   ...')
for (tm, lg), r in gt.tail(10).iterrows():
    print(f'   {tm[:24]:24s} {lg[:16]:16s} n{r.n:2.0f} · rotation {100 * r.rot:3.0f}% · αξια {r.ratio:.2f} · αλλαγες {r.ch:.1f}')
# ---- ΣΥΝΗΘΕΙΑ: μονα vs ζυγα ματς της ιδιας ομαδας (ιδια σεζον) ----
print('\nΣΥΝΗΘΕΙΑ; για καθε ομαδα-σεζον με ≥4 ευρωπαικα: rotation στα ΜΟΝΑ ματς vs στα ΖΥΓΑ (UEL+UECL)')
A = []
for (tm, sea), t in U.groupby(['team', 'sea']):
    if len(t) < 4: continue
    t = t.sort_values('ko'); odd = t.iloc[0::2]; even = t.iloc[1::2]
    A.append(dict(team=tm, sea=sea, r_odd=odd.rot.mean(), r_even=even.rot.mean(), x_odd=np.log(odd.ratio).mean(), x_even=np.log(even.ratio).mean()))
A = pd.DataFrame(A)
print(f'   ομαδες-σεζον: {len(A)} · συσχετιση % rotation μονα↔ζυγα {np.corrcoef(A.r_odd, A.r_even)[0, 1]:+.2f} · συσχετιση αξιας ενδεκαδας {np.corrcoef(A.x_odd, A.x_even)[0, 1]:+.2f}')
hi = A[A.r_odd >= 0.5]; lo = A[A.r_odd == 0]
print(f'   οσες εκαναν rotation στα μισα+ των μονων: στα ζυγα κανουν {100 * hi.r_even.mean():.0f}% (n{len(hi)}) · οσες ΔΕΝ εκαναν ποτε στα μονα: στα ζυγα {100 * lo.r_even.mean():.0f}% (n{len(lo)})')
# απο σεζον σε σεζον (ιδια ομαδα 2425 → 2526)
S = U.groupby(['team', 'sea']).rot.mean().unstack()
S = S.dropna()
if len(S) > 5:
    print(f'   ιδια ομαδα 2425 → 2526 (n{len(S)} ομαδες): συσχετιση % rotation {np.corrcoef(S["2425"], S["2526"])[0, 1]:+.2f}')
T.to_pickle('euro_rotation_rows.pkl')
