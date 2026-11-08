# -*- coding: utf-8 -*-
"""el_value_system_page_test.py — ΙΔΙΟ ΤΕΣΤ με el_value_system_test.py (7 υποψηφιοι, ιδια κριτηρια α-δ) αλλα με ΡΕΑΛΙΣΤΙΚΗ ΓΝΩΣΗ ΑΠΟΝΤΩΝ
(23/10/2026, Στελιος «ναι τρεξτο»): αντι για «ποιος δεν επαιξε» (box score), ο ορισμος N-Gpage του el_gtd_model_test = η σελιδα lineups
ξαναχτισμενη στην ωρα ανοιγματος Crown απο το ιστορικο ειδησεων RotoWire: OUT ×1 · GTD (αμφιβολος / ειδηση τραυματισμου / δεν επαιξε στο
προηγουμενο χωρις νεα) × p (LOSO, ανα πηγη × ρολο) · ολοι οι αλλοι ×0 — ακομα κι αν τελικα δεν επαιξαν.
Αναφορα live σε αυτον τον ορισμο: N-Gpage = 630 picks / +62.3μ (αλλιως STOP). Μηχανισμοι 1-3 (2ο μισο / επομενη σεζον / σταθεροτητα)
δεν εξαρτωνται απο τον ορισμο αποντων → ιδιοι με το el_value_system_test.
Εξοδος: el_value_system_page_test_out.txt"""
import os, sys, io, contextlib, math, time
import numpy as np
ROOT = r'C:\Users\steli\My Drive\Betting Model'; os.chdir(ROOT)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
T0 = time.time()
V = {'__name__': 'v'}
with contextlib.redirect_stdout(_B()): exec(open('el_value_system_test.py', encoding='utf-8').read(), V)
gsrc = open('el_gtd_model_test.py', encoding='utf-8').read().split('def picksA(adj):')[0]
r_ = "def save(): open(os.path.join(ROOT, 'el_gtd_model_test_out.txt'), 'w', encoding='utf-8').write('\\n'.join(out))"
assert gsrc.count(r_) == 1
G = {'__name__': 'g', '__file__': os.path.join(ROOT, 'el_gtd_model_test.py')}
with contextlib.redirect_stdout(_B()): exec(gsrc.replace(r_, 'def save(): return'), G)
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def save(): open('el_value_system_page_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
BI = V['BI']; SE, KS, hrows, hkeys, Yh, ysh = V['SE'], V['KS'], V['hrows'], V['hkeys'], V['Yh'], V['ysh']
blend, gk, rmse, per_match, rnd, loso_ksel = V['blend'], V['gk'], V['rmse'], V['per_match'], V['rnd'], V['loso_ksel']
grows = G['rows']; weight = G['weight']
assert len(grows) == len(hrows) and all(abs(g['ts'] - k[3]) < 1 and g['hc'] == k[1] for g, k in zip(grows, hkeys))
assert np.allclose(np.array([g['act'] - g['m'] for g in grows]), Yh)
# ---- αποντες με βαρος σελιδας ----
AB = []
for g in grows:
    sides = []
    for lst in (g['CA'], g['CH']):                # φιλοξ (+) , γηπ (−)
        sides.append([(p, weight(p, 'N', 'Gp')) for p in lst if weight(p, 'N', 'Gp') > 0 and gk(p['k']) > 0])
    AB.append(sides)
XL = G['XFA'][('N', 'Gp')]
def loso(X):
    h = np.zeros(len(Yh))
    for s in SE:
        m = ysh != s; b = np.linalg.solve(X[m].T @ X[m] + np.eye(X.shape[1]), X[m].T @ Yh[m]); h[ysh == s] = (X @ b)[ysh == s]
    return h
hL = loso(XL); uL, pkL, _ = per_match(hL)
P(f'ματς {len(grows)} · αποντες με βαρος σελιδας > 0: {sum(len(s) for a in AB for s in a)} (μεσο βαρος {np.mean([w for a in AB for s in a for _, w in s]):.2f})')
P(f'ΑΝΑΠΑΡΑΓΩΓΗ live με σελιδα (N-Gpage): picks {int((pkL != 0).sum())} · μοναδες {uL.sum():+.1f}')
if not (int((pkL != 0).sum()) == 630 and abs(uL.sum() - 62.3) < 0.06):
    P('!!! ΔΕΝ αναπαραγεται το N-Gpage (630 / +62.3) — STOP'); save(); sys.exit(1)
P('  ✓ αναπαραγεται (630 picks, +62.3μ)')
def feat(kind, K, comp):
    vals = [[[(p, w, blend(kind, sea, ts, p['pid'], K)) for p, w in side] for side in a] for a, (sea, hc, ac, ts) in zip(AB, hkeys)]
    f = (lambda v: float(v[0])) if kind == 'PIR' else ((lambda v: -float(v[1])) if comp == 'def' else (lambda v: float(v[0] - v[1])))
    sd = float(np.std([f(v) for a in vals for side in a for p, w, v in side if v is not None])); X = np.zeros((len(hrows), 2))
    for i, a in enumerate(vals):
        for side, s in zip(a, (1, -1)):
            for p, w, v in side:
                ww = w * p['min'] / 40 * gk(p['k']) * s; X[i, 0] += ww
                if v is not None: X[i, 1] += ww * f(v) / sd
    return X
CAND = {'1 PIR (live)': (hL, None)}
for nm, kind in (('2 απλο on/off', 'onoff'), ('3 RAPM', 'RAPM'), ('4 δικο box', 'box'), ('5 συνδυασμος Σ', 'Σ'), ('(πληρ.) PIR μιξη', 'PIR')):
    CAND[nm] = loso_ksel({K: feat(kind, K, 'net') for K in KS})
XDEF = {K: feat('Σ', K, 'def')[:, 1] for K in KS}; XNET = {K: feat('Σ', K, 'net')[:, 1] for K in KS}
CAND['6 PIR + αμυνα Σ'] = loso_ksel({K: np.c_[XL, XDEF[K]] for K in KS}); CAND['7 PIR + Σ'] = loso_ksel({K: np.c_[XL, XNET[K]] for K in KS})
order = ['1 PIR (live)', '2 απλο on/off', '3 RAPM', '4 δικο box', '5 συνδυασμος Σ', '6 PIR + αμυνα Σ', '7 PIR + Σ', '(πληρ.) PIR μιξη']
ALLM = np.ones(len(Yh), bool); RES = {}
P(f''); P(f'## ΧΑΝΤΙΚΑΠ με ΣΕΛΙΔΑ ΣΤΟ ΑΝΟΙΓΜΑ — 1481 ματς, LOSO ({time.time() - T0:.0f} δευτ.)')
P(f'  {"υποψηφιος":20s} | RMSE   | ΔRMSE 21 22 23 24 25 (καλ.) | κλιση | picks | μοναδες | ROI    | θετ | ανα σεζον                              | CLV   | 1-10 μ | 11+ μ')
for nm in order:
    h, ks = CAND[nm]; u, pk, cl = per_match(h); d = [rmse(Yh - h, ysh == s) - rmse(Yh - hL, ysh == s) for s in SE]
    per = {s: u[ysh == s].sum() for s in SE}; n = int((pk != 0).sum())
    RES[nm] = dict(h=h, u=u, pk=pk, nb=sum(x < 0 for x in d), U=u.sum(), pos=sum(per[s] > 0 for s in SE))
    sl = float(np.polyfit(h, Yh, 1)[0]) if np.std(h) > 0 else float('nan')
    P(f'  {nm:20s} | {rmse(Yh - h, ALLM):.3f} | ' + ' '.join(f'{x:+.3f}' for x in d) + f' ({RES[nm]["nb"]}/5) | {sl:5.2f} | {n:5d} | {u.sum():+7.1f} | {u.sum() / n * 100:+5.1f}% | '
      f'{RES[nm]["pos"]}/5 | ' + ' '.join(f'{s[-2:]}:{per[s]:+5.1f}' for s in SE) + f' | {np.nanmean(cl):+.2f} | {u[rnd <= 10].sum():+6.1f} | {u[rnd > 10].sum():+6.1f}')
save()
P(''); P('## ΚΟΝΤΡΑ ΜΕ ΤΟ PIR (ανα σεζον, [λεπτα, PIR, υποψηφιος]) → βαρος υποψηφιου > 0 σε ποσες σεζον')
GAM = {}
C6 = order[1:7]
for nm in C6:
    if nm.startswith('6'): xs = {s: XDEF[CAND[nm][1][s]] for s in SE}
    elif nm.startswith('7'): xs = {s: XNET[CAND[nm][1][s]] for s in SE}
    else:
        kind = {'2': 'onoff', '3': 'RAPM', '4': 'box', '5': 'Σ'}[nm[0]]; xs = {s: feat(kind, CAND[nm][1][s], 'net')[:, 1] for s in SE}
    bs = []
    for s in SE:
        m = ysh == s; X = np.c_[XL, xs[s]][m]; bs.append(np.linalg.solve(X.T @ X + np.eye(3), X.T @ Yh[m])[2])
    GAM[nm] = sum(b > 0 for b in bs); P(f'  {nm:20s} ' + ' '.join(f'{s[-2:]}:{b:+.2f}' for s, b in zip(SE, bs)) + f' → {GAM[nm]}/5')
P(''); P('## ΤΥΧΗ: ζευγαρωτη διαφορα μοναδων vs live-σελιδα ± τυπ. σφαλμα · reality check bootstrap 5000 (καλυτερος απο 6)')
Dm = np.c_[[RES[c]['u'] - uL for c in C6]].T; obs = Dm.sum(0); Dc = Dm - Dm.mean(0)
rng = np.random.default_rng(20261023); MX = np.empty(5000); SG = np.empty((5000, len(C6)))
for b in range(5000):
    idx = rng.integers(0, len(Dm), len(Dm)); s_ = Dc[idx].sum(0); MX[b] = s_.max(); SG[b] = s_
PV = {}
for j, c in enumerate(C6):
    PV[c] = float(np.mean(MX >= obs[j]))
    P(f'  {c:20s} Δ {obs[j]:+6.1f} ± {Dm[:, j].std(ddof=1) * math.sqrt(len(Dm)):4.1f} · ματς με αλλο pick {int((RES[c]["pk"] != pkL).sum()):3d} · '
      f'τυχη μονος {float(np.mean(SG[:, j] >= obs[j])):.2f} · ως καλυτερος-απο-6 {PV[c]:.2f} · 11+: Δ {Dm[rnd > 10, j].sum():+5.1f} ± {Dm[rnd > 10, j].std(ddof=1) * math.sqrt((rnd > 10).sum()):4.1f}'
      f' (θετ. σεζον {sum(Dm[(rnd > 10) & (ysh == s), j].sum() > 0 for s in SE)}/5)')
P(''); P('################ ΚΡΙΣΗ (α RMSE ≥4/5 · β μοναδες ≥ live & θετικες ≥4/5 · γ κοντρα ≥4/5 · δ τυχη < 0.10) ################')
uLs = uL.sum(); PASS = []
for c in C6:
    R_ = RES[c]; a = R_['nb'] >= 4; b = R_['U'] >= uLs and R_['pos'] >= 4; g = GAM[c] >= 4; d = PV[c] < 0.10
    if a and b and g and d: PASS.append(c)
    P(f'  {c:20s} α {R_["nb"]}/5 {"✓" if a else "✗"} · β {R_["U"]:+.1f} vs {uLs:+.1f}, θετ {R_["pos"]}/5 {"✓" if b else "✗"} · γ {GAM[c]}/5 {"✓" if g else "✗"} · δ {PV[c]:.2f} {"✓" if d else "✗"} → '
      + ('ΠΕΡΝΑ' if a and b and g and d else 'δεν περνα'))
P('  → ' + (f'ΝΙΚΗΤΗΣ: {min(PASS, key=lambda c: rmse(Yh - RES[c]["h"], ALLM))}' if PASS else 'ΚΑΝΕΝΑΣ δεν περνα · μενει το PIR (live)'))
P(f'\n(χρονος {time.time() - T0:.0f} δευτ.)'); save()
