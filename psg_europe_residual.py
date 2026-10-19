# -*- coding: utf-8 -*-
"""psg_europe_residual.py — 19/10/2026 (Στελιος: «θεωρω οτι υποτιμαμε την Παρι — στο πρωταθλημα δεν φορτσαρει, στην Ευρωπη ειναι αλλη ομαδα»).
Ευρωπαικα ματς της Παρι 2022-26 (σημερινη αλυσιδα, harness uel_full_review): γκολ/διαφορα πραγματικα vs μοντελο, ανα σεζον.
Συγκριση: ολες οι ομαδες top-5 λιγκων σε UCL (ιδιο μετρο) — ειναι η Παρι εξαιρεση; + τα φετινα (euro_projections, τελειωμενα)."""
import sys, os, json, glob
_s = open('uel_full_review.py', encoding='utf-8').read().split("print('=' * 100 + NL + '1. ΣΥΝΟΛΑ")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
_TO = sys.stdout; sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(_s); sys.stdout = _TO
sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
NM = {}
for f in glob.glob('data_Europe_*.json'):
    for mid, m in json.load(open(f, encoding='utf-8')).items(): NM[str(mid)] = (m['home']['name'], m['away']['name'])
R = []
for i, mid in enumerate(MIDS):
    h, a = NM.get(str(mid), (None, None))
    if h is None: continue
    for side, tm in ((1, h), (-1, a)):
        R.append(dict(team=tm, comp=COMP[i], sea=SEA[i], home=side == 1, gf=GH[i] if side == 1 else GA[i], ga=GA[i] if side == 1 else GH[i],
                      mf=LH_N[i] if side == 1 else LA_N[i], ma=LA_N[i] if side == 1 else LH_N[i]))
D = pd.DataFrame(R); D['rd'] = (D.gf - D.ga) - (D.mf - D.ma); D['rf'] = D.gf - D.mf; D['ra'] = D.ga - D.ma
P = D[D.team == 'Paris Saint-Germain']
print(f'ΠΑΡΙ ευρωπαικα 2022-26: {len(P)} ματς')
print(f'   {"σεζον":8s} {"ματς":>5s} │ {"διαφορα πραγμ":>13s} {"μοντελο":>8s} {"πραγμ−μοντ":>11s} │ {"γκολ βαζει":>10s} {"μοντ":>6s} │ {"τρωει":>6s} {"μοντ":>6s}')
for s, y in list(P.groupby('sea')) + [('ΟΛΑ', P)]:
    print(f'   {s:8s} {len(y):5d} │ {(y.gf - y.ga).mean():+13.2f} {(y.mf - y.ma).mean():+8.2f} {y.rd.mean():+11.2f} │ {y.gf.mean():10.2f} {y.mf.mean():6.2f} │ {y.ga.mean():6.2f} {y.ma.mean():6.2f}')
print(f'   (αβεβαιοτητα ±{P.rd.std() / np.sqrt(len(P)):.2f} στο πραγμ−μοντ)')
U = D[D.comp == 'ChampionsLeague']
tm = U.groupby('team').agg(n=('rd', 'size'), rd=('rd', 'mean')); tm = tm[tm.n >= 15].sort_values('rd', ascending=False)
print(f'\nΟΜΑΔΕΣ με ≥15 ματς UCL 2022-26 — ποιες ξεπερνουν/υστερουν το μοντελο (διαφορα πραγμ−μοντ ανα ματς):')
for t, r in tm.head(8).iterrows(): print(f'   +  {t:28s} {int(r.n):3d} ματς  {r.rd:+.2f}')
print('   ...')
for t, r in tm.tail(5).iterrows(): print(f'   −  {t:28s} {int(r.n):3d} ματς  {r.rd:+.2f}')
print(f'   διασπορα που περιμενεις απο τυχη μονο (±1 SD για 30 ματς): ±{U.rd.std() / np.sqrt(30):.2f}')
PJ = json.load(open('euro_projections.json', encoding='utf-8'))
F = [m for v in PJ.values() if isinstance(v, list) and v and isinstance(v[0], dict) and 'mid' in v[0] for m in v if m.get('finished') and 'Paris Saint-Germain' in (m['home'], m['away'])]
print('\nΦΕΤΙΝΑ (προβλεψη οπως ειναι τωρα στο αρχειο):')
for m in F:
    print(f"   {m['utc'][:10]} {m['home']} - {m['away']} {m.get('score')} · μοντελο {m.get('xgh', 0):.2f}-{m.get('xga', 0):.2f}")
