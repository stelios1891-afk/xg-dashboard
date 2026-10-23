# -*- coding: utf-8 -*-
"""t67_boxB_params_build.py — ΠΑΡΑΜΕΤΡΟΙ για το LIVE «Β» (24/10/2026, Στελιος «περσινο DARKO + LEBRON οπως ειναι, φετινο με το Β · περνα το»).
Β = «δικο μας box» του t65 (η προτερη box του σταδιου 4): ρυθμοι ανα 100 κατοχες ΣΤΟ ΓΗΠΕΔΟ (13 στατιστικα, μαζεμα 150 κατοχες προς τον
μεσο) + λεπτα/ματς + % βασικος → επιθεση O / αμυνα D με βαρη που εμαθαν απο πολυ-σεζονικο RAPM · δεδομενα = φετινα ως το ματς + περσινα × w_prev
· καθαρο O + D → κλιμακα live αξιας (a + c·καθαρο, απο τελικες τιμες δικου δεικτη → μεσος DARKO/LEBRON) · μιξη με περσινο DARKO+LEBRON:
v = (φετινα λεπτα·v_B + 250·v_περσι)/(φετινα λεπτα + 250) (M=250: LOSO 4/4 στο t65_bet).
Για τη σεζον 2026-27 (S=2027): βαρη απο ΟΛΕΣ τις 2022-2026 (στο τεστ: σεζον < S) · w_prev απο ολες τις 2023-26 (στο τεστ LOSO) ·
αντιστοιχιση απο s′ = 2022-2026 · περσινα = αθροισματα 2025-26 ανα παικτη (ESPN id).
Τρεχει ΤΟΠΙΚΑ μια φορα τη σεζον (θελει τα cache του t65 στο scratchpad). Εξοδος: nba_boxB_params.json (ριζα)."""
import os, sys, io, json, pickle, contextlib, collections
import numpy as np
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't65_own_index_build.py'), encoding='utf-8').read().split('# ΣΤΑΔΙΟ 4 — ΣΥΝΔΥΑΣΜΟΣ walk-forward')[0]
r = "def SAVE(): open(OUTF, 'w', encoding='utf-8').write('" + chr(92) + "n'.join(out) + '" + chr(92) + "n')"
assert src.count(r) == 1
G = {'__file__': os.path.join(SC, 't65_own_index_build.py'), '__name__': 't65b'}
with contextlib.redirect_stdout(_B()): exec(src.replace(r, 'def SAVE(): return'), G)
sys.stdout.reconfigure(encoding='utf-8')
SEAS, SDF, PG, FEAT, box_feats, design, normal_eq, solve, LAM2, T65 = (G[k] for k in ('SEAS', 'SDF', 'PG', 'FEAT', 'box_feats', 'design', 'normal_eq', 'solve', 'LAM2', 'T65'))
S = 2027
# ---- βαρη box για S=2027 (ιδιος κωδικας με ΣΤΑΔΙΟ 3, tr = ολες οι σεζον) ----
X, W, YW, pl, GG = design([(s, np.ones(len(SDF[s]['poss']), bool), 1.0) for s in SEAS]); n = len(pl)
A_, b_, mu_ = normal_eq(X, W, YW); B = solve(A_, b_, LAM2, n)
tgtO = dict(zip(pl, B[:n])); tgtD = dict(zip(pl, -B[n:2 * n]))
BF, mu = box_feats([(PG[s], 1.0) for s in SEAS]); BF = BF[BF.index.isin(pl)]
Z = np.c_[np.ones(len(BF)), BF[FEAT].values]; w = BF._min.values; sw = np.sqrt(w)
cO = np.linalg.lstsq(Z * sw[:, None], np.array([tgtO[q] for q in BF.index]) * sw, rcond=None)[0]
cD = np.linalg.lstsq(Z * sw[:, None], np.array([tgtD[q] for q in BF.index]) * sw, rcond=None)[0]
print(f'βαρη S={S}: εκπαιδευση {SEAS} · παικτες {len(BF)} · λ {LAM2}')
# ---- w_prev απο ολες τις 2023-26 (ιδια λογικη με την επιλογη LOSO του σταδιου 4) ----
S4 = pickle.load(open(os.path.join(T65, 'stage4.pkl'), 'rb'))
RM = collections.defaultdict(lambda: [0.0, 0])
for s in [2023, 2024, 2025, 2026]:
    for (k, w_, l_), (a, b) in S4[s]['PRED'].items(): RM[(w_, l_)][0] += a; RM[(w_, l_)][1] += b
wp, lam = min(RM, key=lambda g: RM[g][0] / RM[g][1])
print(f'w_prev {wp} (λ {lam}) · RMSE επομενης εβδομαδας {np.sqrt(RM[(wp, lam)][0] / RM[(wp, lam)][1]):.3f}')
# ---- αντιστοιχιση κλιμακας (ιδιο με t65_bet.mapping, s′ = 2022-2026) ----
FN = pickle.load(open(os.path.join(T65, 'final.pkl'), 'rb')); FINAL, E2N = FN['FINAL'], FN['E2N']
DK, LB = {}, {}
for rr in json.load(open(os.path.join(ROOT, 'nba_rapm', 'DARKO.json'), encoding='utf-8')):
    if rr.get('dpm') is not None: DK[(str(rr['nba_id']), int(rr['season']))] = rr['dpm']
for rr in json.load(open(os.path.join(ROOT, 'nba_rapm', 'lebron.json'), encoding='utf-8')):
    if rr.get('LEBRON') is not None and rr.get('nba_id'): LB[(str(rr['nba_id']), int(rr['year']))] = rr['LEBRON']
cwd = os.getcwd(); os.chdir(ROOT)
rsrc = open(os.path.join(ROOT, 'nba_roster_adj.py'), encoding='utf-8').read().split('OUT, ABS = {}, {}')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
R_ = {}
with contextlib.redirect_stdout(_B()): exec(rsrc, R_)
os.chdir(cwd); sys.stdout.reconfigure(encoding='utf-8'); MPT = R_['MPT']
Xm, Ym, Wm = [], [], []
for s_ in SEAS:
    for e, v in FINAL[s_].items():
        nid = E2N.get(e)
        if nid is None: continue
        vs = [o for o in (DK.get((nid, s_)), LB.get((nid, s_))) if o is not None]; mp = MPT.get((nid, s_), 0.0)
        if not vs or mp <= 0: continue
        Xm.append(v[0]); Ym.append(float(np.mean(vs)) * mp / (mp + 500)); Wm.append(mp)
Xm, Ym, Wm = np.array(Xm), np.array(Ym), np.array(Wm); Zm = np.c_[np.ones(len(Xm)), Xm]; sw = np.sqrt(Wm)
ac = np.linalg.lstsq(Zm * sw[:, None], Ym * sw, rcond=None)[0]
print(f'αντιστοιχιση: a {ac[0]:+.3f} · c {ac[1]:.3f} · corr {np.corrcoef(Xm, Ym)[0, 1]:.3f} · n {len(Xm)}')
# ---- περσινα (2025-26) αθροισματα ανα παικτη ----
df = PG[2026]; cols = ['poss', 'min', 'st'] + [f'f{k}' for k in range(13)]
agg = df.groupby('p')[cols].sum(); cnt = df.groupby('p').size()
prev = {str(p): [round(float(x), 3) for x in row] + [int(cnt[p])] for p, row in zip(agg.index, agg.values)}
out = dict(built='2026-10-24', season=S, prev_season=2026, M=250.0, P0=150.0, wp=float(wp), a=float(ac[0]), c=float(ac[1]),
           cO=[float(x) for x in cO], cD=[float(x) for x in cD], mu=[float(x) for x in mu], feat=FEAT,
           prev_cols=cols + ['g'], prev=prev, note='NBA φετινη αξια «Β» (δικο μας box) — nba_tests/t67_boxB_params_build.py · t65/t66')
json.dump(out, open(os.path.join(ROOT, 'nba_boxB_params.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print(f'nba_boxB_params.json · περσινοι παικτες {len(prev)}')
