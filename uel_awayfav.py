"""
uel_awayfav.py — 9/10/2026 (Στελιος: «σπασε τα εκτος εδρας φαβορι σε δυναμικες· ειναι κυριως top-5; οι ΜΕΣΑΙΕΣ των top-5 (Λατσιο, Θελτα,
Μπετις) κανουν ροτεισον στη League Phase»). ΠΕΡΙΓΡΑΦΙΚΟ, 2223-2526, σημερινη ευρωπαικη αλυσιδα.
Φαβορι = φαβορι ΜΟΝΤΕΛΟΥ με |υπεροχη| ≥0.5. Για καθε φαβορι: λιγκα, ΘΕΣΗ ΣΤΟ ΠΕΡΣΙΝΟ ΠΡΩΤΑΘΛΗΜΑ (απο τα data_*.json, CORE7 μονο),
δυναμη (υπεροχη μοντελου). Μετρα: πραγματικο − μοντελο για το φαβορι σε xG και γκολ · πραγματικο − αγορα (διαφορα γκολ) ·
picks φαβορι (σημερινος κανονας UEL @4, μεσος Crown/SBOBET). Συγκριση: εντος εδρας φαβορι, και UCL/UECL.
"""
import sys, io, json, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('uel_home_why.py', encoding='utf-8').read(); src = src[:src.index("print('1. ΕΔΡΑ")].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
g = {'__name__': 'af'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
MIDS, COMP, SEA, PHASE, NEW, GD, GH, GA, LH_N, LA_N, SM, LGH, LGA, TEAMS, FM, XH, XA = (g[k] for k in (
    'MIDS', 'COMP', 'SEA', 'PHASE', 'NEW', 'GD', 'GH', 'GA', 'LH_N', 'LA_N', 'SM', 'LGH', 'LGA', 'TEAMS', 'FM', 'XH', 'XA'))
P0 = g['g']['P0']
TOP5 = ['EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1']
CORE7 = TOP5 + ['PrimeiraLiga', 'Eredivisie']
def prev(s): return f'{int(s[:2]) - 1:02d}{int(s[2:]) - 1:02d}'
POS = {}
for lg in CORE7:
    for sea in ('2122', '2223', '2324', '2425'):
        try: d = json.load(open(f'data_{lg}_{sea}.json', encoding='utf-8'))
        except FileNotFoundError: continue
        pts, gdf = {}, {}
        for m in d.values():
            if m.get('hs') is None: continue
            h, a = m['home']['id'], m['away']['id']; hs, as_ = m['hs'], m['as']
            for t in (h, a): pts.setdefault(t, 0); gdf.setdefault(t, 0)
            pts[h] += 3 if hs > as_ else (1 if hs == as_ else 0); pts[a] += 3 if as_ > hs else (1 if hs == as_ else 0)
            gdf[h] += hs - as_; gdf[a] += as_ - hs
        for r_, t in enumerate(sorted(pts, key=lambda t: (-pts[t], -gdf[t])), 1): POS[(t, sea)] = r_
rows = []
SMOD = LH_N - LA_N
for i, mid in enumerate(MIDS):
    if abs(SMOD[i]) < 0.5 or mid not in TEAMS or not np.isfinite(XH[i]): continue
    fh = SMOD[i] > 0; t = TEAMS[mid][0] if fh else TEAMS[mid][1]; lg = LGH[i] if fh else LGA[i]
    fx, fg, fl = (XH[i], GH[i], LH_N[i]) if fh else (XA[i], GA[i], LA_N[i])
    pos = POS.get((t, prev(SEA[i]))) if lg in CORE7 else None
    sgn = 1 if fh else -1
    rows.append(dict(i=i, comp=COMP[i], sea=SEA[i], phase=PHASE[i], new=NEW[i], home=fh, lg=lg, top5=lg in TOP5, pos=pos, sup=abs(SMOD[i]),
                     ex=fx - fl, eg=fg - fl, ek=(GD[i] - SM[i]) * sgn if np.isfinite(SM[i]) else np.nan, ed=(GD[i] - SMOD[i]) * sgn))
F = pd.DataFrame(rows)
def cls(r):
    if not r.top5: return 'ΟΧΙ top-5'
    if r.pos is None: return 'top-5 (χωρις περσινη θεση)'
    return 'top-5 ΜΕΓΑΛΗ (περσι 1-4)' if r.pos <= 4 else ('top-5 ΜΕΣΑΙΑ (περσι 5-10)' if r.pos <= 10 else 'top-5 κατω (11+)')
F['cls'] = F.apply(cls, axis=1)
F['dyn'] = pd.cut(F.sup, [0.49, 1.0, 1.5, 9], labels=['0.5-1', '1-1.5', '≥1.5'])
# picks φαβορι ανα ματς (μεσος βιβλιων)
PK = P0[P0.role == 'fav'].groupby('i').pnl.mean()
F['pick'] = F.i.map(PK)
def line(d, lab):
    if len(d) < 8: return f'   {lab:30s} n{len(d):4d}'
    ps = d.groupby('sea').ed.mean(); pk = d.pick.dropna()
    return (f'   {lab:30s} n{len(d):4d} · φαβορι xG−μοντελο {d.ex.mean():+.2f} · γκολ−μοντελο {d.eg.mean():+.2f} · διαφορα γκολ−μοντελο {d.ed.mean():+.2f}±{d.ed.std() / np.sqrt(len(d)):.2f} ({int((ps < 0).sum())}/{ps.size} σεζ <0)'
            f' · −αγορα {d.ek.mean():+.2f} · picks {len(pk):3d} ' + (f'{100 * pk.mean():+.0f}%' if len(pk) >= 5 else '—'))
for comp in ('EuropaLeague', 'ChampionsLeague', 'ConferenceLeague'):
    for hlab, hv in (('ΕΚΤΟΣ', False), ('ΕΝΤΟΣ', True)):
        x = F[(F.comp == comp) & (F.home == hv)]
        print(f'\n[{comp} — φαβορι {hlab} εδρας] ολα:'); print(line(x, 'ολα'))
        for k, v in x.groupby('cls'): print(line(v, k))
        for k, v in x.groupby('dyn', observed=True): print(line(v, f'δυναμη {k}'))
        if comp == 'EuropaLeague':
            for k, v in x.groupby('phase'): print(line(v, f'φαση {k}'))
            for k, v in x[x.top5].groupby('dyn', observed=True): print(line(v, f'top-5 & δυναμη {k}'))
x = F[(F.comp == 'EuropaLeague') & ~F.home & F.top5]
print('\nUEL εκτος φαβορι top-5 — ποιες ομαδες (περσινη θεση, ματς, διαφορα γκολ−μοντελο):')
NAMES = {}
for k_, lst in json.load(open('europe_fixtures.json', encoding='utf-8')).items():
    for m in lst: NAMES[m['hid']] = m['hname']; NAMES[m['aid']] = m['aname']
x = x.assign(team=[NAMES.get(TEAMS[MIDS[i]][1], '?') for i in x.i])
print(x.groupby(['team', 'lg']).agg(n=('ed', 'size'), θεση=('pos', 'first'), λαθος=('ed', 'mean')).sort_values('n', ascending=False).head(25).round(2).to_string())
