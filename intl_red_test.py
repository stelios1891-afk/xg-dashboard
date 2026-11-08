"""
intl_red_test.py — 5/10/2026 (Στελιος): κοκκινες στο ΜΟΝΤΕΛΟ 1 εθνικων (Elo + xElo, H3 live). Σημερα: ΚΑΜΙΑ διορθωση κοκκινων
(το xElo παιρνει το xG με διορθωση game-state μονο). Τεστ: + red_modes.LIVE_MODE ('emps') πανω στο xG καθε πλευρας
(xh·fr + term), και 'none' (σημερινο). Μετρο: RPS LOSO 1Χ2 (ordered logit), αγωνιστικα ματς, ανα σεζον — οπως intl_rating2_hist.
ΔΕΝ γραφει κανενα αρχειο (το intl_rating2_hist.py γραφει τα live — εδω κοβεται πριν).
"""
import sys, json, glob, os, re
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import red_modes
src = open('intl_rating2_hist.py', encoding='utf-8').read()
pre = src[:src.index("SEAS = ['2021'")].replace(chr(10) + "sys.stdout.reconfigure(encoding='utf-8')" + chr(10), chr(10) + 'pass' + chr(10))
pre = pre.replace("xh, xa = adj_xg(r.shots, fav, 'gs'); xh *= scale; xa *= scale",
                  "xh, xa = adj_xg(r.shots, fav, 'gs'); xh *= scale; xa *= scale\n            _ra = RADJ.get(r.mid) if RED_ON else None\n            if _ra: xh = max(xh * _ra[0][0] + _ra[0][1], 0.0); xa = max(xa * _ra[1][0] + _ra[1][1], 0.0)")
assert 'RADJ.get' in pre
M0 = pd.read_csv('intl_matches.csv', dtype={'mid': str})
need = set(M0[(M0.reds > 0) & M0.has_xg].mid)
RADJ = {}
for f in glob.glob('data_*.json'):
    try: d = json.load(open(f, encoding='utf-8'))
    except Exception: continue
    if not isinstance(d, dict): continue
    for mid in need & set(d):
        m = d[mid]
        if not m.get('reds'): continue
        a = red_modes.team_adj(m, red_modes.LIVE_MODE); H, A = int(m['home']['id']), int(m['away']['id'])
        RADJ[mid] = ((a[H]['fr'], a[H]['term']), (a[A]['fr'], a[A]['term']))
print(f'ματς εθνικων με κοκκινη & xG: {len(need)} · βρεθηκαν στα data_*.json: {len(RADJ)}')
res = {}
for on in (False, True):
    g = {'__name__': 'irt', 'RADJ': RADJ, 'RED_ON': on}
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        exec(pre, g)
    D, R = g['run']('H3'); D['y'] = np.where(D.gd > 0, 2, np.where(D.gd == 0, 1, 0))
    C = D[D.ctype.isin(['nl', 'qual', 'tourn'])]
    row = {}; allP = []; ally = []
    for s in ['2021', '2122', '2223', '2324', '2425', '2526']:
        tr = C[C.season != s]; te = C[C.season == s]
        p = g['fit_ol'](tr['diff'].values, tr['y'].values); Pm = g['probs'](te['diff'].values, p)
        row[s] = g['rps'](Pm, te['y'].values); allP.append(Pm); ally.append(te['y'].values)
    row['ΟΛΑ'] = g['rps'](np.vstack(allP), np.concatenate(ally)); row['n'] = len(C)
    res['ΜΕ κοκκινες (emps)' if on else 'σημερα (καμια)'] = row
T = pd.DataFrame(res).T; print(T.round(5).to_string())
b = T.iloc[0]; n = T.iloc[1]
print(f"Δ RPS {1000*(n['ΟΛΑ'] - b['ΟΛΑ']):+.3f} ×10⁻³ · καλυτερο σε {sum(n[s] < b[s] for s in ['2021','2122','2223','2324','2425','2526'])}/6 σεζον")
