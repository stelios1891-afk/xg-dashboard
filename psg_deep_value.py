# -*- coding: utf-8 -*-
"""psg_deep_value.py — 19/10/2026. Τι «βλεπει» η αγορα για την Παρι που δεν βλεπει το μοντελο; Υποψηφιος ΓΕΝΙΚΟΣ μηχανισμος: αξια ενδεκαδας.
«Τι λεει η αξια» = a + b·ln(αξια γηπ / αξια φιλοξ) (euro_team_value.pkl = συνηθισμενη ενδεκαδα πριν το ματς, γνωστη απο πριν), ευθεια LOSO ανα σεζον
πανω στην πραγματικη διαφορα γκολ ολων των ευρωπαικων. Μετα: (αξια − μοντελο) για Παρι/ομαδες, και ποσο εξηγει το (πραγμ − μοντελο) ΓΕΝΙΚΑ.
+ εγχωριο φινιρισμα (γκολ − xG) Παρι vs ευρωπαικο (μεταφερεται;)."""
import sys, pickle, json, os
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
D = pd.read_pickle('psg_deep_rows.pkl'); TV = pickle.load(open('euro_team_value.pkl', 'rb'))
D['km'] = D.kgd - D.mgd
D['lv'] = [np.log(TV[m][0] / TV[m][1]) * (1 if h else -1) if m in TV and TV[m][0] and TV[m][1] else np.nan for m, h in zip(D.mid, D.home)]
H = D[D.home & D.lv.notna()].copy()
VF = {}
for s in sorted(H.sea.unique()):
    tr = H[H.sea != s]; VF[s] = np.polyfit(tr.lv, tr.gd, 1)
D['vgd'] = [(VF[s][0] * lv + VF[s][1]) * (1 if h else 1) if np.isfinite(lv) else np.nan for s, lv, h in zip(D.sea, D.lv, D.home)]
# για φιλοξ: lv ηδη με προσημο ομαδας, αλλα ο σταθερος ορος = εδρα → για φιλοξενουμενο: −(b·(−lv) + a) = b·lv − a
D.loc[~D.home, 'vgd'] = [(VF[s][0] * lv - VF[s][1]) if np.isfinite(lv) else np.nan for s, lv in zip(D[~D.home].sea, D[~D.home].lv)]
D['vm'] = D.vgd - D.mgd
print(f'καλυψη αξιας: {D.lv.notna().mean():.0%} των ομαδα-ματς · ευθεια (ολες οι σεζον): διαφορα = {np.polyfit(H.lv, H.gd, 1)[1]:+.2f} + {np.polyfit(H.lv, H.gd, 1)[0]:.2f}·ln(λογος αξιας)')
V = D[D.lv.notna()]
P = V[V.team == 'Paris Saint-Germain']
print(f'\nΠΑΡΙ ({len(P)} ματς με αξια): πραγμ {P.gd.mean():+.2f} · μοντελο {P.mgd.mean():+.2f} · αγορα {P.kgd.mean():+.2f} · ΑΞΙΑ {P.vgd.mean():+.2f}')
for s, y in P.groupby('sea'):
    print(f'   {s}: n={len(y):2d} πραγμ {y.gd.mean():+.2f} · μοντ {y.mgd.mean():+.2f} · αγορα {y.kgd.mean():+.2f} · αξια {y.vgd.mean():+.2f} · (αξια−μοντ {y.vm.mean():+.2f}, αγορα−μοντ {y.km.mean():+.2f})')
print('\nΓΕΝΙΚΑ (ολες οι ομαδες-ματς με αξια): εξηγει η (αξια − μοντελο) την αποκλιση πραγμ − μοντελο και το (αγορα − μοντελο);')
for x, y_, lab in (('vm', 'rd', 'αξια−μοντ → πραγμ−μοντ'), ('vm', 'km', 'αξια−μοντ → αγορα−μοντ'), ('km', 'rd', 'αγορα−μοντ → πραγμ−μοντ')):
    b = np.polyfit(V[x], V[y_], 1); r = np.corrcoef(V[x], V[y_])[0, 1]
    print(f'   {lab:26s} r = {r:+.3f} (n={len(V)}) · κλιση {b[0]:+.2f}')
# LOSO μιξη: μοντελο + w·(αξια − μοντ) → σφαλμα
for w in (0, .1, .2, .3, .5):
    e = V.rd - w * V.vm; print(f'   μιξη αξιας w={w:.1f}: RMSE διαφορας {np.sqrt((e ** 2).mean()):.4f}' + (f'  · Παρι πραγμ−νεο μοντ {(P.rd - w * P.vm).mean():+.2f}' if w else ''))
T = V.groupby('team').agg(n=('rd', 'size'), vm=('vm', 'mean'), km=('km', 'mean'), rd=('rd', 'mean'))
T = T[T.n >= 25]
print(f'\nΑΝΑ ΟΜΑΔΑ (≥25 ματς με αξια, {len(T)}): corr(αξια−μοντ, αγορα−μοντ) = {np.corrcoef(T.vm, T.km)[0, 1]:+.2f} · corr(αξια−μοντ, πραγμ−μοντ) = {np.corrcoef(T.vm, T.rd)[0, 1]:+.2f}')
print('   μεγαλυτερο (αξια−μοντ): ' + ' · '.join(f'{t[:16]} {r.vm:+.2f} (αγ {r.km:+.2f}, πρ {r.rd:+.2f})' for t, r in T.sort_values('vm', ascending=False).head(8).iterrows()))
print('   μεγαλυτερο (αγορα−μοντ): ' + ' · '.join(f'{t[:16]} {r.km:+.2f} (αξ {r.vm:+.2f}, πρ {r.rd:+.2f})' for t, r in T.sort_values('km', ascending=False).head(8).iterrows()))
# ---- εγχωριο φινιρισμα Παρι vs ευρωπαικο ----
print('\nΦΙΝΙΡΙΣΜΑ: εγχωρια (Ligue 1, γκολ − xG 90λ) vs ευρωπαικα — Παρι ανα σεζον')
for s in ('2122', '2223', '2324', '2425', '2526'):
    fn = f'data_Ligue1_{s}.json'
    if not os.path.exists(fn): continue
    a = []
    for m in json.load(open(fn, encoding='utf-8')).values():
        nm = (m['home']['name'], m['away']['name'])
        if 'Paris Saint-Germain' not in nm or not m.get('shots'): continue
        H_ = nm[0] == 'Paris Saint-Germain'; pid = m['home']['id'] if H_ else m['away']['id']
        xf = sum(x['xg'] for x in m['shots'] if x.get('xg') is not None and x['min'] <= 90 and int(x['tid']) == int(pid))
        xa = sum(x['xg'] for x in m['shots'] if x.get('xg') is not None and x['min'] <= 90 and int(x['tid']) != int(pid))
        gf, ga = (m['hs'], m['as']) if H_ else (m['as'], m['hs']); a.append((gf - xf, xa - ga))
    a = np.array(a); e = D[(D.team == 'Paris Saint-Germain') & (D.sea == s)]
    print(f'   {s}: Ligue 1 n={len(a)} επιθεση γκολ−xG {a[:, 0].mean():+.2f} · αμυνα xG−γκολ {a[:, 1].mean():+.2f}' +
          (f' │ Ευρωπη n={len(e)} επιθεση {(e.gf - e.xf).mean():+.2f} · αμυνα {(e.xa - e.ga).mean():+.2f}' if len(e) else ''))
