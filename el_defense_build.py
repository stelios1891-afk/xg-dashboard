# -*- coding: utf-8 -*-
"""el_defense_build.py — φτιαχνει το el_defense_params.json για το live «PIR + αμυνα» (29/10/2026). Τρεχει ΤΟΠΙΚΑ (χρειαζεται el_pbp_stints.pkl).
ΚΑΘΕ ΝΕΑ ΣΕΖΟΝ ξανατρεξε το (περσινες τιμες = η σεζον που τελειωσε) — και ενημερωσε SEASON/PREV πιο κατω.
Περιεχει: περσινες τιμες Σ (O, D) ανα παικτη · box συντελεστες (prior) · sd αμυνας · B0/B1/B2 (ελαχιστα τετραγωνα, τελεια γνωση E2021-25, οπως 0.56/1.06 του PIR).
ΕΛΕΓΧΟΙ: (1) el_defense.parse = el_rapm_build.parse στα φετινα ματς · (2) el_defense.values (numpy) = ερευνητικο Σ (el_best_index_test, scipy) για E2026."""
import os, sys, io, json, contextlib
import numpy as np
ROOT = r'C:\Users\steli\My Drive\Betting Model'; os.chdir(ROOT); sys.path.insert(0, ROOT)
SEASON, PREV = 'E2026', 'E2025'
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open('el_pird_tests.py', encoding='utf-8').read().split('# ---- σαρωση σαν scanner ----')[0]
s0 = "def save(): open('el_pird_tests_out.txt', 'w', encoding='utf-8').write('" + chr(92) + "n'.join(out))"
assert src.count(s0) == 1
T = {'__name__': 'pird'}
with contextlib.redirect_stdout(_B()): exec(src.replace(s0, 'def save(): return'), T)
sys.stdout.reconfigure(encoding='utf-8')
S = T['S']; BI = S['BI']; N = S['N']
XPDB = np.array([T['featsPD'](i, 0, box=True) for i in range(N)])
assert np.abs(XPDB[:, :2] - S['XBP']).max() < 1e-9
B = S['fitb'](XPDB, np.ones(N, bool))
PIDS, FULL, COEF = BI['PIDS'], BI['FULL'], BI['COEF']
prev = {PIDS[g]: [round(float(v[0]), 5), round(float(v[1]), 5)] for g, v in FULL[('Σ', PREV)].items()}
cf = COEF[PREV]
P_ = dict(season=SEASON, prev_season=PREV, built='2026-10-29', K=500.0, LAM=8000.0, KBOX=float(BI.get('KBOX', 300.0)), sdD=round(float(T['sdD']), 6),
          B0=round(float(B[0]), 4), B1=round(float(B[1]), 4), B2=round(float(B[2]), 4),
          coef=dict(bO=[float(x) for x in cf['bO']], bD=[float(x) for x in cf['bD']], lg=[float(x) for x in cf['lg']]), prev=prev,
          note='κοστος = (B0 + B1·zPIR + B2·zΑΜΥΝΑ)·λεπτα/40·g(k) · zΑΜΥΝΑ = −D/sdD · ελαχιστα τετραγωνα τελειας γνωσης E2021-25 (el_pird_tests)')
json.dump(P_, open('el_defense_params.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print(f'el_defense_params.json: B0 {P_["B0"]:+.4f} · B1 (PIR) {P_["B1"]:+.4f} · B2 (αμυνα) {P_["B2"]:+.4f} · sdD {P_["sdD"]:.4f} · KBOX {P_["KBOX"]} · περσινοι παικτες {len(prev)}')
# ---- ελεγχοι ----
import el_defense as ED, pickle
C = pickle.load(open('el_pbp_stints.pkl', 'rb'))
K26 = sorted(k for k in C if k.startswith(SEASON + '_'))
games, bad = [], 0
for k in K26:
    d = json.load(open(os.path.join('el_pbp', k + '.json'), encoding='utf-8'))
    H, A, st, vec = ED.parse(d['box'], d['pbp'])
    ref = [list(map(list, s[:2])) + list(s[2:]) for s in C[k]['stints']]
    if st != ref: bad += 1
    games.append(dict(st=st, p=vec))
print(f'ελεγχος 1 — κομματια πενταδων ιδια με el_rapm_build σε {len(K26) - bad}/{len(K26)} φετινα ματς')
V = ED.values(P_, games)
COEF[SEASON] = COEF[PREV]
cur = BI['idx_vals'](BI['BYS'][SEASON], SEASON, 'Σ'); A_ = BI['agg']([(k, 1.0) for k in BI['BYS'][SEASON]])
dif = []
for g, c in cur.items():
    pid = PIDS[g]; pv = FULL[('Σ', PREV)].get(g); n = A_[g][15] if g in A_ else 0.0
    pp = pv if pv is not None else np.zeros(2)
    D = ((n * np.array(c) + 500 * np.array(pp)) / (n + 500))[1]
    dif.append(abs(D - V[pid]['D']))
print(f'ελεγχος 2 — D φετος (μιξη) numpy vs ερευνα: {len(dif)} παικτες · μεγιστη διαφορα {max(dif):.2e}')
assert bad == 0 and max(dif) < 1e-3
