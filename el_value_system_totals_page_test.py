# -*- coding: utf-8 -*-
"""el_value_system_totals_page_test.py — ΣΥΝΟΛΑ Ευρωλιγκας: συστημα αξιας παικτη με ΡΕΑΛΙΣΤΙΚΗ ΓΝΩΣΗ ΑΠΟΝΤΩΝ (23/10/2026, Στελιος «τρεξτο»).
Αποντες = οτι εβλεπε το live ΣΥΝΟΛΩΝ στο ανοιγμα Crown (ορισμος N-G0 του el_gtd_model_test: ειδηση ΕΚΤΟΣ/ΜΑΛΛΟΝ ΕΚΤΟΣ ως το ανοιγμα ×1·
GTD δεν μετρανε στα συνολα, οπως στο live). Αναφορα: live 3StepsBasket περσινο on/off W4+alias σε αυτον τον ορισμο = 536 picks / +54.7μ (αλλιως STOP).
ΥΠΟΨΗΦΙΟΙ (επιθεση O / αμυνα D ανα παικτη, μιξη περσι+φετος (n·φετ + K·περσ)/(n+K), K ∈ {500..4000} LOSO απο RMSE εκπαιδευσης):
  2 δικο απλο on/off · 3 RAPM · 4 δικο box · 5 συνδυασμος Σ   — τυπος W4: ποντοι ομαδας += bO·Σ δικα w·O/sd + bD·Σ αντιπ. w·D/sd, LOSO, ridge 1.
ΚΡΙΤΗΡΙΑ (ιδια με χαντικαπ): α RMSE συνολου καλυτερο απο live ≥4/5 · β μοναδες ≥ live & θετικες ≥4/5 · γ κοντρα: εντος σεζον
  [live O, live D, υποψ. O, υποψ. D] → ΚΑΙ οι δυο συντελεστες του υποψηφιου με το αναμενομενο προσημο (<0) σε ≥4/5 · δ reality check
  (καλυτερος απο 4) p < 0.10.
Εξοδος: el_value_system_totals_page_test_out.txt"""
import os, sys, io, contextlib, math, time
import numpy as np
ROOT = r'C:\Users\steli\My Drive\Betting Model'; os.chdir(ROOT)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
T0 = time.time()
V = {'__name__': 'v'}
with contextlib.redirect_stdout(_B()): exec(open('el_value_system_test.py', encoding='utf-8').read(), V)
gsrc = open('el_gtd_model_test.py', encoding='utf-8').read().split('# ======================= 4. ΠΙΝΑΚΕΣ')[0]
r_ = "def save(): open(os.path.join(ROOT, 'el_gtd_model_test_out.txt'), 'w', encoding='utf-8').write('\\n'.join(out))"
assert gsrc.count(r_) == 1
G = {'__name__': 'g', '__file__': os.path.join(ROOT, 'el_gtd_model_test.py')}
with contextlib.redirect_stdout(_B()): exec(gsrc.replace(r_, 'def save(): return'), G)
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def save(): open('el_value_system_totals_page_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
blend, KS, SE, rmse = V['blend'], V['KS'], V['SE'], V['rmse']
rowsB, ysB, YT, YH, YA, tp, weight, gk = G['rowsB'], G['ysB'], G['YT'], G['YH'], G['YAw'], G['tp'], G['weight'], G['gk']
rndB = np.array([r['rnd'] if (r['rnd'] and r.get('rnd')) else 99 for r in rowsB])
TGB = G['TGB']; rnd = np.array([sum(1 for x in TGB.get((r['y'], r['hc']), []) if x[0] < r['ts'] - 3600) + 1 for r in rowsB])
def per_match(adj):
    u = np.zeros(len(rowsB)); pk = np.zeros(len(rowsB)); cl = np.full(len(rowsB), np.nan)
    for i, (r, a) in enumerate(zip(rowsB, adj)):
        o = r['op']; T_, oo, ou = o[2], o[3], o[4]; po, pp, pu = tp(r['T'] + a, T_); eo, eu = po * oo + pp - 1, pu * ou + pp - 1
        sd, e, od = (1, eo, oo) if eo >= eu else (-1, eu, ou)
        if e >= .08:
            x = (r['hs'] + r['as_'] - T_) * sd; u[i] = (od - 1) if x > 0 else (0 if x == 0 else -1); pk[i] = sd; cl[i] = (r['cl'][1] - o[1]) * sd
    return u, pk, cl
hL = G['HELD_B'][('N', 'G0')]; uL, pkL, _ = per_match(hL)
P(f'ματς {len(rowsB)} · αποντες (ειδηση ΕΚΤΟΣ ως το ανοιγμα): {sum(1 for r in rowsB for p in r["CH"] + r["CA"] if weight(p, "N", "G0") > 0)}')
P(f'ΑΝΑΠΑΡΑΓΩΓΗ live συνολων με ειδησεις στο ανοιγμα (N-G0): picks {int((pkL != 0).sum())} · μοναδες {uL.sum():+.1f}')
if not (int((pkL != 0).sum()) == 536 and abs(uL.sum() - 54.7) < 0.06):
    P('!!! ΔΕΝ αναπαραγεται (536 / +54.7) — STOP'); save(); sys.exit(1)
P('  ✓ αναπαραγεται (536 picks, +54.7μ)')
# live χαρακτηριστικα (για την κοντρα)
FL = [G['featB'](r, 'N', 'G0') for r in rowsB]; XHL = np.array([f[0] for f in FL]); XAL = np.array([f[1] for f in FL])
def feat(kind, K):
    XH = np.zeros((len(rowsB), 2)); XA = np.zeros((len(rowsB), 2)); allv = []
    vals = []
    for r in rowsB:
        sides = []
        for lst in (r['CH'], r['CA']):
            sides.append([(p, weight(p, 'N', 'G0'), blend(kind, r['y'], r['ts'], p['pid'], K)) for p in lst if weight(p, 'N', 'G0') > 0])
        vals.append(sides); allv += [v for s in sides for _, _, v in s if v is not None]
    sO, sD = float(np.std([v[0] for v in allv])), float(np.std([v[1] for v in allv]))
    for i, (h_, a_) in enumerate(vals):
        def side(own, opp): return (sum(w * p['w'] * (v[0] / sO if v is not None else 0) for p, w, v in own), sum(w * p['w'] * (v[1] / sD if v is not None else 0) for p, w, v in opp))
        XH[i] = side(h_, a_); XA[i] = side(a_, h_)
    return XH, XA
def fit_pred(XH, XA, tr, m):
    X = np.r_[XH[tr], XA[tr]]; y = np.r_[YH[tr], YA[tr]]; b = np.linalg.solve(X.T @ X + np.eye(X.shape[1]), X.T @ y); return XH @ b + XA @ b, b
def loso_ksel(FK):
    h = np.zeros(len(rowsB)); ks = {}
    for s in SE:
        tr = ysB != s; best = None
        for K, (XH, XA) in FK.items():
            p_, b = fit_pred(XH, XA, tr, None); e = rmse(YT - p_, tr)
            if best is None or e < best[0]: best = (e, K, p_)
        ks[s] = best[1]; h[ysB == s] = best[2][ysB == s]
    return h, ks
CAND = {'1 live on/off 3Steps': (hL, None)}
FEAT = {}
for nm, kind in (('2 δικο απλο on/off', 'onoff'), ('3 RAPM', 'RAPM'), ('4 δικο box', 'box'), ('5 συνδυασμος Σ', 'Σ')):
    FEAT[nm] = {K: feat(kind, K) for K in KS}; CAND[nm] = loso_ksel(FEAT[nm])
    P(f'  {nm} ετοιμο ({time.time() - T0:.0f} δευτ.)')
CAND['(πληρ.) χωρις διορθωση'] = (np.zeros(len(rowsB)), None)
ALLM = np.ones(len(rowsB), bool); RES = {}
P(''); P('## ΣΥΝΟΛΑ με ΕΙΔΗΣΕΙΣ ΣΤΟ ΑΝΟΙΓΜΑ — 1563 ματς 2021-22…2025-26, LOSO · ΔRMSE συνολου vs live (ποντοι, − = καλυτερο) · κλιση (1 = σωστο μεγεθος) · picks συνολων ≥8% ανοιγμα Crown')
P(f'  {"υποψηφιος":24s} | RMSE   | ΔRMSE 21 22 23 24 25 (καλ.) | κλιση | picks | μοναδες | ROI    | θετ | ανα σεζον                              | CLV   | over μ/n | under μ/n | 1-10 μ | 11+ μ')
for nm, (h, ks) in CAND.items():
    u, pk, cl = per_match(h); d = [rmse(YT - h, ysB == s) - rmse(YT - hL, ysB == s) for s in SE]
    per = {s: u[ysB == s].sum() for s in SE}; n = int((pk != 0).sum())
    RES[nm] = dict(h=h, u=u, pk=pk, nb=sum(x < 0 for x in d), U=u.sum(), pos=sum(per[s] > 0 for s in SE))
    sl = float(np.polyfit(h, YT, 1)[0]) if np.std(h) > 0 else float('nan')
    P(f'  {nm:24s} | {rmse(YT - h, ALLM):.3f} | ' + ' '.join(f'{x:+.3f}' for x in d) + f' ({RES[nm]["nb"]}/5) | {sl:5.2f} | {n:5d} | {u.sum():+7.1f} | {u.sum() / max(n, 1) * 100:+5.1f}% | '
      f'{RES[nm]["pos"]}/5 | ' + ' '.join(f'{s[-2:]}:{per[s]:+5.1f}' for s in SE) + f' | {np.nanmean(cl):+.2f} | {u[pk == 1].sum():+5.1f}/{int((pk == 1).sum())} | {u[pk == -1].sum():+5.1f}/{int((pk == -1).sum())}'
      f' | {u[rnd <= 10].sum():+6.1f} | {u[rnd > 10].sum():+6.1f}' + (f' · K {"/".join(str(ks[s]) for s in SE)}' if ks else ''))
save()
C4 = ['2 δικο απλο on/off', '3 RAPM', '4 δικο box', '5 συνδυασμος Σ']
P(''); P('## ΚΟΝΤΡΑ ΜΕ ΤΟ LIVE (εντος σεζον [live O, live D, υποψ. O, υποψ. D]) → συντελεστες υποψηφιου (αναμενομενο < 0 και τα δυο)')
GAM = {}
for nm in C4:
    good = 0; txt = []
    for s in SE:
        m = ysB == s; XH_, XA_ = FEAT[nm][CAND[nm][1][s]]
        X = np.r_[np.c_[XHL, XH_][m], np.c_[XAL, XA_][m]]; y = np.r_[YH[m], YA[m]]; b = np.linalg.solve(X.T @ X + np.eye(4), X.T @ y)
        good += (b[2] < 0 and b[3] < 0); txt.append(f'{s[-2:]}: O {b[2]:+.2f} D {b[3]:+.2f}')
    GAM[nm] = good; P(f'  {nm:24s} ' + ' · '.join(txt) + f' → και τα δυο <0 σε {good}/5')
P(''); P('## ΤΥΧΗ: ζευγαρωτη διαφορα μοναδων vs live ± τυπ. σφαλμα · reality check bootstrap 5000 (καλυτερος απο 4)')
Dm = np.c_[[RES[c]['u'] - uL for c in C4]].T; obs = Dm.sum(0); Dc = Dm - Dm.mean(0)
rng = np.random.default_rng(20261023); MX = np.empty(5000); SG = np.empty((5000, len(C4)))
for b in range(5000):
    idx = rng.integers(0, len(Dm), len(Dm)); s_ = Dc[idx].sum(0); MX[b] = s_.max(); SG[b] = s_
PV = {}
for j, c in enumerate(C4):
    PV[c] = float(np.mean(MX >= obs[j]))
    P(f'  {c:24s} Δ {obs[j]:+6.1f} ± {Dm[:, j].std(ddof=1) * math.sqrt(len(Dm)):4.1f} · ματς με αλλο pick {int((RES[c]["pk"] != pkL).sum()):3d} · τυχη μονος {float(np.mean(SG[:, j] >= obs[j])):.2f}'
      f' · ως καλυτερος-απο-4 {PV[c]:.2f} · 11+: Δ {Dm[rnd > 10, j].sum():+5.1f} ± {Dm[rnd > 10, j].std(ddof=1) * math.sqrt((rnd > 10).sum()):4.1f}')
P(''); P('################ ΚΡΙΣΗ (α RMSE ≥4/5 · β μοναδες ≥ live & θετικες ≥4/5 · γ κοντρα ≥4/5 · δ τυχη < 0.10) ################')
uLs = uL.sum(); PASS = []
for c in C4:
    R_ = RES[c]; a = R_['nb'] >= 4; b = R_['U'] >= uLs and R_['pos'] >= 4; g = GAM[c] >= 4; d = PV[c] < 0.10
    if a and b and g and d: PASS.append(c)
    P(f'  {c:24s} α {R_["nb"]}/5 {"✓" if a else "✗"} · β {R_["U"]:+.1f} vs {uLs:+.1f}, θετ {R_["pos"]}/5 {"✓" if b else "✗"} · γ {GAM[c]}/5 {"✓" if g else "✗"} · δ {PV[c]:.2f} {"✓" if d else "✗"} → '
      + ('ΠΕΡΝΑ' if a and b and g and d else 'δεν περνα'))
P('  → ' + (f'ΝΙΚΗΤΗΣ: {min(PASS, key=lambda c: rmse(YT - RES[c]["h"], ALLM))}' if PASS else 'ΚΑΝΕΝΑΣ δεν περνα · μενει το live'))
P(f'\n(χρονος {time.time() - T0:.0f} δευτ.)'); save()
