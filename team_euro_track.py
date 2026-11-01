"""team_euro_track.py — 14/10/2026 (Στελιος: «δεν μοιαζουν τοσο λαθη οσο τα παρουσιαζουμε — ο Ολυμπιακος ειναι οντως δυνατος, η διορθωση λιγκας
του κοβει δυναμη»). Ιστορικο ομαδας στα ευρωπαικα (κατηγορια Α, 4 σεζον, ολες οι διοργανωσεις): απο τη σκοπια της ομαδας,
ΜΟΝΤΕΛΟ vs ΑΓΟΡΑ (κλεισιμο) vs xG vs γκολ, ανα ματς + μεσοι ορους. Ομαδες: Olympiacos, Union St.Gilloise, Milan.
"""
import sys, os, json
_TO = sys.stdout
exec(open('uel_home_away_fav_diag.py', encoding='utf-8').read().split("print('1) ΑΝΑΛΥΣΗ ΛΑΘΟΥΣ")[0])
sys.stdout = _TO; sys.stdout.reconfigure(encoding='utf-8')
NM = {}
import glob
for f in glob.glob('data_Europe_*.json'):
    for k, m in json.load(open(f, encoding='utf-8')).items(): NM[str(k)] = (m['home']['name'], m['away']['name'])
C['mid'] = [str(MIDS[i]) for i in C.i]
for team in ('Olympiacos', 'Union St.Gilloise', 'Milan'):
    rows = []
    for r in C.itertuples():
        h, a = NM.get(r.mid, ('', ''))
        if team not in (h, a): continue
        s = 1 if h == team else -1
        rows.append(dict(sea=r.sea, comp=r.comp[:3], opp=a if s == 1 else h, ven='εντος' if s == 1 else 'εκτος', mdl=s * r.mgd, mk=s * r.kgd, xg=s * r.xgd, gd=s * r.gd))
    X = pd.DataFrame(rows)
    if len(X) == 0: print(team, 'κανενα'); continue
    print(f'{chr(10)}===== {team}: {len(X)} ευρωπαικα ματς (κατηγορια Α) · ΜΟΝΤΕΛΟ {X.mdl.mean():+.2f} · ΑΓΟΡΑ {X.mk.mean():+.2f} · xG {X.xg.mean():+.2f} · γκολ {X.gd.mean():+.2f}'
          f' │ μοντελο − xG {(X.mdl - X.xg).mean():+.2f} ±{(X.mdl - X.xg).std() / np.sqrt(len(X)):.2f} · αγορα − xG {(X.mk - X.xg).mean():+.2f}')
    for v in ('εντος', 'εκτος'):
        y = X[X.ven == v]
        if len(y): print(f'   {v}: n{len(y)} · μοντελο {y.mdl.mean():+.2f} · αγορα {y.mk.mean():+.2f} · xG {y.xg.mean():+.2f} · γκολ {y.gd.mean():+.2f}')
