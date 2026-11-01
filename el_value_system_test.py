# -*- coding: utf-8 -*-
"""el_value_system_test.py — EUROLEAGUE ΧΑΝΤΙΚΑΠ: ΠΛΗΡΕΣ ΤΕΣΤ ΣΥΣΤΗΜΑΤΟΣ ΑΞΙΑΣ ΠΑΙΚΤΗ (23/10/2026, Στελιος «ναι» στον ορισμο).
Ερωτημα: ποιο συστημα αξιας δινει το σωστοτερο κοστος απουσιας στο ΧΑΝΤΙΚΑΠ — και ειναι η διαφορα απο το PIR πραγματικη ή τυχη;
ΥΠΟΔΟΜΗ: el_best_index_test.py ΣΤΑΔΙΑ 1 + 2Α ΑΥΤΟΥΣΙΑ (exec, χωρις να γραφει το δικο του αρχειο) — τα κομματια του (1Α/1Γ, ΧΑΝΤΙΚΑΠ LOSO,
  κλιση, CLV) ειναι οι μηχανισμοι 1, 2, 4, 5, 7, 8 για τους υποψηφιους 1-5. Εδω προστιθενται:
  ΥΠΟΨΗΦΙΟΙ 6 «PIR + αμυνα» = live [w, w·zPIR] + w·z(−D του Σ μιξη) · 7 «PIR + Σ» = live [w, w·zPIR] + w·z(καθαρο Σ μιξη)
    (K μιξης ∈ {500,1000,2000,4000} επιλογη LOSO με RMSE εκπαιδευσης, οπως οι αλλοι· ridge 1).
  ΜΗΧ. 3 σταθεροτητα: συσχετιση καθαρης τιμης S → S+1 (ιδιος παικτης, ≥1000 κατοχες και στις δυο, E2017-25).
  ΜΗΧ. 6 κοντρα: ανα σεζον (εντος σεζον) [w, w·zPIR, w·z(υποψηφιου)] → βαρος υποψηφιου > 0 σε ποσες σεζον.
  ΜΗΧ. 9 τυχη: ζευγαρωτη διαφορα μοναδων/ματς vs live ± τυπ. σφαλμα · «reality check» bootstrap 5000 (κεντραρισμενες διαφορες
    → πιθανοτητα ο ΚΑΛΥΤΕΡΟΣ απο τους 6 να φτασει το προβαδισμα του υποψηφιου απο τυχη).
ΚΡΙΤΗΡΙΑ (προ-δηλωμενα): αντικαθιστα το PIR αν (α) RMSE καλυτερο απο live ≥4/5 (β) μοναδες ≥ live & θετικες ≥4/5
  (γ) κοντρα: θετικο βαρος ≥4/5 σεζον (δ) reality check p < 0.10. Πολλοι → καλυτερο RMSE. Κανενας → PIR.
Εξοδος: el_value_system_test_out.txt"""
import os, sys, io, contextlib, math, collections, time
import numpy as np
ROOT = r'C:\Users\steli\My Drive\Betting Model'; os.chdir(ROOT)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open('el_best_index_test.py', encoding='utf-8').read().split('# ================= ΣΤΑΔΙΟ 2Β: ΣΥΝΟΛΑ')[0]
r = "def save(): open(os.path.join(ROOT, 'el_best_index_test_out.txt'), 'w', encoding='utf-8').write('\\n'.join(out))"
assert src.count(r) == 1
src = src.replace(r, "def save(): return")
BI = {'__name__': 'bi'}
T0 = time.time()
with contextlib.redirect_stdout(_B()): exec(src, BI)
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def save(): open('el_value_system_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
P('################ ΜΕΡΟΣ Α — ΑΠΟ ΤΟ el_best_index_test (μηχανισμοι 1, 2, 4, 5, 7, 8 για υποψηφιους 1-5) ################')
for s in BI['out']:
    if 'ετοιμη (' in s or 'ετοιμο:' in s or 'ΣΥΝΟΛΟ/100' in s: continue
    P(s)
P(f'(υποδομη ετοιμη σε {time.time() - T0:.0f} δευτ.)'); save()
SE, KS, hrows, hkeys, Yh, ysh = BI['SE'], BI['KS'], BI['hrows'], BI['hkeys'], BI['Yh'], BI['ysh']
XL, hL, HNEW, blend, gk, rmse, Phi, LAB = BI['XL'], BI['hL'], BI['HNEW'], BI['blend'], BI['gk'], BI['rmse'], BI['Phi'], BI['LAB']
FULL, BYS, agg, SEAS, PIDS, NAME, PID = BI['FULL'], BI['BYS'], BI['agg'], BI['SEAS'], BI['PIDS'], BI['NAME'], BI['PID']
ALLM = np.ones(len(Yh), bool)
# ---- υποψηφιοι 6/7 ----
def comp_feat(K, comp):
    vals = [[[(p, blend('Σ', sea, ts, p['pid'], K)) for p in r[side]] for side in ('aa', 'ah')] for r, (sea, hc, ac, ts) in zip(hrows, hkeys)]
    f = (lambda v: -float(v[1])) if comp == 'def' else (lambda v: float(v[0] - v[1]))
    sd = float(np.std([f(v) for rv in vals for side in rv for p, v in side if v is not None])); x = np.zeros(len(hrows))
    for i, rv in enumerate(vals):
        for side, s in zip(rv, (1, -1)):
            for p, v in side:
                if v is not None: x[i] += p['min'] / 40 * gk(p['k']) * s * f(v) / sd
    return x
def loso_ksel(XK):
    """XK: K → πινακας χαρακτηριστικων · → κρατημενη προβλεψη με K επιλεγμενο στις 4 σεζον εκπαιδευσης"""
    h = np.zeros(len(Yh)); ks = {}
    for s in SE:
        m = ysh != s; best = None
        for K, X in XK.items():
            b = np.linalg.solve(X[m].T @ X[m] + np.eye(X.shape[1]), X[m].T @ Yh[m]); e = rmse(Yh - X @ b, m)
            if best is None or e < best[0]: best = (e, K, b)
        ks[s] = best[1]; h[ysh == s] = (XK[best[1]] @ best[2])[ysh == s]
    return h, ks
XDEF = {K: comp_feat(K, 'def') for K in KS}; XNET = {K: comp_feat(K, 'net') for K in KS}
h6, k6 = loso_ksel({K: np.c_[XL, XDEF[K]] for K in KS}); h7, k7 = loso_ksel({K: np.c_[XL, XNET[K]] for K in KS})
P(''); P(f'## ΥΠΟΨΗΦΙΟΙ 6/7 ετοιμοι ({time.time() - T0:.0f} δευτ.)')
CAND = {'1 PIR (live)': (hL, None), '2 απλο on/off': (HNEW['onoff']['hs'], HNEW['onoff']['ksel']), '3 RAPM': (HNEW['RAPM']['hs'], HNEW['RAPM']['ksel']),
        '4 δικο box': (HNEW['box']['hs'], HNEW['box']['ksel']), '5 συνδυασμος Σ': (HNEW['Σ']['hs'], HNEW['Σ']['ksel']),
        '6 PIR + αμυνα Σ': (h6, k6), '7 PIR + Σ': (h7, k7), '(πληρ.) PIR μιξη': (HNEW['PIR']['hs'], HNEW['PIR']['ksel'])}
# ---- picks ανα ματς ----
def per_match(adj):
    u = np.zeros(len(hrows)); pk = np.zeros(len(hrows)); cl = np.full(len(hrows), np.nan)
    for i, (r, a) in enumerate(zip(hrows, adj)):
        L, o1, o2 = r['op']; m = r['m'] + a
        if abs(L - round(L)) < 1e-9: pw = Phi((m + L - .5) / 11.5); pl = Phi((-m - L - .5) / 11.5)
        else: pw = Phi((m + L) / 11.5); pl = 1 - pw
        pp = 1 - pw - pl; e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1; sd, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
        if e >= .08:
            x = (r['act'] + L) * sd; u[i] = (od - 1) if x > 0 else (0 if x == 0 else -1); pk[i] = sd; cl[i] = (r['mc'] - r['mo']) * sd
    return u, pk, cl
TGH = BI['nsH']['TG']
rnd = np.array([sum(1 for x in TGH.get((sea, hc), []) if x[0] < ts - 3600) + 1 for sea, hc, ac, ts in hkeys])
def slope(h, m):
    return float(np.polyfit(h[m], Yh[m], 1)[0]) if np.std(h[m]) > 0 else float('nan')
uL, pkL, _ = per_match(hL)
RES = {}
P(''); P('################ ΜΕΡΟΣ Β — ΟΛΟΙ ΟΙ 7 ΥΠΟΨΗΦΙΟΙ ΜΑΖΙ (ΧΑΝΤΙΚΑΠ, 1481 ματς E2021-25, LOSO) ################')
P('## Μηχ. 4 ακριβεια (ΔRMSE διαφορας vs live, ποντοι, − = καλυτερο) · 5 κλιση (1 = σωστο μεγεθος) · 7 picks ≥8% ανοιγμα · 8 CLV (ποντοι γραμμης προς το pick)')
P(f'  {"υποψηφιος":20s} | RMSE   | ΔRMSE 21 22 23 24 25 (καλ.) | κλιση | picks | μοναδες | ROI    | θετ | ανα σεζον                         | CLV   | K')
for nm, (h, ks) in CAND.items():
    u, pk, cl = per_match(h); d = [rmse(Yh - h, ysh == s) - rmse(Yh - hL, ysh == s) for s in SE]
    per = {s: u[(ysh == s) & (pk != 0)].sum() for s in SE}; n = int((pk != 0).sum())
    RES[nm] = dict(h=h, u=u, pk=pk, d=d, nb=sum(x < 0 for x in d), U=u.sum(), n=n, pos=sum(1 for s in SE if per[s] > 0))
    P(f'  {nm:20s} | {rmse(Yh - h, ALLM):.3f} | ' + ' '.join(f'{x:+.3f}' for x in d) + f' ({RES[nm]["nb"]}/5) | {slope(h, ALLM) if np.std(h) > 0 else float("nan"):5.2f} | {n:5d} | {u.sum():+7.1f} | '
      f'{u.sum() / n * 100:+5.1f}% | {RES[nm]["pos"]}/5 | ' + ' '.join(f'{s[-2:]}:{per[s]:+5.1f}' for s in SE) + f' | {np.nanmean(cl):+.2f} | ' + ('/'.join(str(ks[s]) for s in SE) if ks else '—'))
P(''); P('## Μηχ. 7β — ΑΓΩΝΙΣΤΙΚΕΣ 1-10 (γηπεδουχος ≤9 φετινα πριν) vs 11+ · picks · μοναδες · ROI')
for nm in CAND:
    u, pk = RES[nm]['u'], RES[nm]['pk']
    P(f'  {nm:20s} ' + ' | '.join(f'{lab}: {int(((pk != 0) & m).sum()):3d} · {u[m].sum():+6.1f}μ · {u[m].sum() / max(1, ((pk != 0) & m).sum()) * 100:+5.1f}%'
                                   for lab, m in (('1-10', rnd <= 10), ('11+', rnd > 10))))
save()
# ---- Μηχ. 6: κοντρα με το PIR ----
P(''); P('## Μηχ. 6 — ΚΟΝΤΡΑ ΜΕ ΤΟ PIR: ανα σεζον (μονο τα ματς της σεζον) [λεπτα, PIR, υποψηφιος] → βαρος υποψηφιου (ποντοι ανα 40′ απουσιας ανα 1 τυπ.απ.· > 0 = προσθετει πληροφορια πανω στο PIR)')
GAM = {}
def cand_x(nm, s):
    if nm.startswith('6'): return XDEF[k6[s]]
    if nm.startswith('7'): return XNET[k7[s]]
    key = {'2': 'onoff', '3': 'RAPM', '4': 'box', '5': 'Σ'}[nm[0]]; return HNEW[key]['HK'][HNEW[key]['ksel'][s]][2][:, 1]
for nm in [c for c in CAND if c[0] in '234567']:
    bs = []
    for s in SE:
        m = ysh == s; X = np.c_[XL, cand_x(nm, s)][m]; b = np.linalg.solve(X.T @ X + np.eye(3), X.T @ Yh[m]); bs.append(b)
    GAM[nm] = sum(b[2] > 0 for b in bs)
    P(f'  {nm:20s} βαρος υποψηφιου ' + ' '.join(f'{s[-2:]}:{b[2]:+.2f}' for s, b in zip(SE, bs)) + f' → θετικο {GAM[nm]}/5 · βαρος PIR στην ιδια ' + ' '.join(f'{b[1]:+.2f}' for b in bs))
save()
# ---- Μηχ. 3: σταθεροτητα ----
P(''); P('## Μηχ. 3 — ΣΤΑΘΕΡΟΤΗΤΑ: συσχετιση καθαρης τιμης του ιδιου παικτη S → S+1 (≥1000 κατοχες και στις δυο σεζον) · E2017→E2025')
POS = {S: {p: v[15] for p, v in agg([(k, 1.0) for k in BYS[S]]).items()} for S in SEAS if 'E2017' <= S <= 'E2025'}
S1 = [s for s in SEAS if 'E2017' <= s <= 'E2025']
for kind in ['PIR', 'onoff', 'RAPM', 'box', 'Σ']:
    cs = []; ns_ = []
    for a, b in zip(S1, S1[1:]):
        A_, B_ = FULL[(kind, a)], FULL[(kind, b)]
        ps = [p for p in A_ if p in B_ and POS[a].get(p, 0) >= 1000 and POS[b].get(p, 0) >= 1000]
        f = (lambda v: float(v[0])) if kind == 'PIR' else (lambda v: float(v[0] - v[1]))
        x = np.array([f(A_[p]) for p in ps]); y = np.array([f(B_[p]) for p in ps]); cs.append(np.corrcoef(x, y)[0, 1]); ns_.append(len(ps))
    P(f'  {LAB[kind]:22s} μεση {np.mean(cs):.2f} · ανα ζευγαρι ' + ' '.join(f'{c:.2f}' for c in cs) + f' · παικτες/ζευγαρι ~{int(np.mean(ns_))}')
save()
# ---- Μηχ. 9: τυχη ----
P(''); P('## Μηχ. 9 — ΤΥΧΗ: ζευγαρωτη διαφορα μοναδων vs live (± τυπ. σφαλμα) · reality check bootstrap 5000 (ο καλυτερος απο τους 6 υποψηφιους 2-7)')
C6 = [c for c in CAND if c[0] in '234567']
Dm = np.c_[[RES[c]['u'] - uL for c in C6]].T; obs = Dm.sum(0); Dc = Dm - Dm.mean(0)
rng = np.random.default_rng(20261023); MX = np.empty(5000); SGL = np.empty((5000, len(C6)))
for b in range(5000):
    idx = rng.integers(0, len(Dm), len(Dm)); s_ = Dc[idx].sum(0); MX[b] = s_.max(); SGL[b] = s_
PV = {}
for j, c in enumerate(C6):
    se_ = Dm[:, j].std(ddof=1) * math.sqrt(len(Dm)); PV[c] = float(np.mean(MX >= obs[j])); p1 = float(np.mean(SGL[:, j] >= obs[j]))
    P(f'  {c:20s} Δμοναδες {obs[j]:+6.1f} ± {se_:4.1f} · ματς με αλλο pick {int((RES[c]["pk"] != pkL).sum()):3d} · '
      f'πιθ. τυχης ΜΟΝΟΣ του {p1:.2f} · πιθ. τυχης ως καλυτερος-απο-6 {PV[c]:.2f}')
save()
# ---- ΚΡΙΣΗ ----
P(''); P('################ ΚΡΙΣΗ (προ-δηλωμενα: α RMSE ≥4/5 · β μοναδες ≥ live & θετικες ≥4/5 · γ κοντρα ≥4/5 · δ τυχη < 0.10) ################')
uLs = RES['1 PIR (live)']['U']; PASS = []
for c in C6:
    R_ = RES[c]; a = R_['nb'] >= 4; b = R_['U'] >= uLs and R_['pos'] >= 4; g = GAM[c] >= 4; d = PV[c] < 0.10
    if a and b and g and d: PASS.append(c)
    P(f'  {c:20s} α {R_["nb"]}/5 {"✓" if a else "✗"} · β {R_["U"]:+.1f} vs {uLs:+.1f}, θετ {R_["pos"]}/5 {"✓" if b else "✗"} · γ {GAM[c]}/5 {"✓" if g else "✗"} · δ {PV[c]:.2f} {"✓" if d else "✗"} → '
      + ('ΠΕΡΝΑ' if a and b and g and d else 'δεν περνα'))
if PASS:
    w = min(PASS, key=lambda c: rmse(Yh - RES[c]['h'], ALLM)); P(f'  → ΝΙΚΗΤΗΣ (καλυτερο RMSE μεταξυ οσων περνουν): {w}')
else: P('  → ΚΑΝΕΝΑΣ δεν περνα ολα τα κριτηρια · μενει το PIR (live)')
save()
# ---- ΠΑΡΑΔΕΙΓΜΑΤΑ ----
P(''); P('## ΠΑΡΑΔΕΙΓΜΑΤΑ Α — παικτες που ο Σ βαζει ΠΟΛΥ πιο ψηλα απο το PIR (E2024, ≥1500 κατοχες, z μεσα στους ιδιους παικτες) · O/D σε ποντους/100 κατοχες')
S = 'E2024'; ps = [p for p in FULL[('Σ', S)] if p in FULL[('PIR', S)] and POS[S].get(p, 0) >= 1500]
zp = np.array([FULL[('PIR', S)][p][0] for p in ps]); zs = np.array([FULL[('Σ', S)][p][0] - FULL[('Σ', S)][p][1] for p in ps])
zp = (zp - zp.mean()) / zp.std(); zs = (zs - zs.mean()) / zs.std(); gap = zs - zp
for lab_, order in (('Σ >> PIR', np.argsort(-gap)[:6]), ('PIR >> Σ', np.argsort(gap)[:6])):
    P(f'  {lab_}:')
    for i in order:
        v = FULL[('Σ', S)][ps[i]]
        P(f'    {NAME.get(PIDS[ps[i]], PIDS[ps[i]])[:24]:24s} z PIR {zp[i]:+.2f} · z Σ {zs[i]:+.2f} · Σ επιθεση {v[0]:+.2f} · Σ αμυνα {v[1]:+.2f} (− = ο αντιπαλος βαζει λιγοτερα)')
P(''); P('## ΠΑΡΑΔΕΙΓΜΑΤΑ Β — 3 ματς οπου live και Σ διαφωνουν περισσοτερο (διορθωση απουσιων υπερ γηπεδουχου, ποντοι) · πραγματικο − μοντελο χωρις απουσιες')
hS = RES['5 συνδυασμος Σ']['h']; order = np.argsort(-np.abs(hS - hL))[:3]
import datetime as dt
for i in order:
    r = hrows[i]; sea, hc, ac, ts = hkeys[i]
    ab = ', '.join(f'{NAME.get(p["pid"], p["pid"])} ({"γηπ" if side == "ah" else "φιλ"}, {p["min"]:.0f}′)' for side in ('ah', 'aa') for p in r[side] if gk(p['k']) > 0)
    P(f'  {sea} {hc}-{ac} {dt.datetime.fromtimestamp(ts, dt.timezone.utc):%Y-%m-%d} · αποντες: {ab}')
    P(f'      διορθωση live {hL[i]:+.2f} · Σ {hS[i]:+.2f} · πραγματικο − μοντελο {Yh[i]:+.1f} → πιο κοντα: {"Σ" if abs(Yh[i] - hS[i]) < abs(Yh[i] - hL[i]) else "live"}'
      f' · pick live {["κανενα", "γηπ", "φιλ"][int(RES["1 PIR (live)"]["pk"][i]) if RES["1 PIR (live)"]["pk"][i] >= 0 else 2]} / Σ {["κανενα", "γηπ", "φιλ"][int(RES["5 συνδυασμος Σ"]["pk"][i]) if RES["5 συνδυασμος Σ"]["pk"][i] >= 0 else 2]}')
P(f'\n(συνολικος χρονος {time.time() - T0:.0f} δευτ.)'); save()
