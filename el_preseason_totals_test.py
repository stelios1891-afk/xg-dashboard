# -*- coding: utf-8 -*-
"""el_preseason_totals_test.py — ΠΡΟΕΤΟΙΜΑΣΙΑ ΣΤΑ ΣΥΝΟΛΑ ΠΟΝΤΩΝ της Ευρωλιγκας, αγων 1-10 (1/10/2026, αιτημα Στελιου:
«ισως θελει προσαρμογη επειδη μιλαμε για φιλικα — ισως το συνολο ποντων ειναι λιγο πιο ανοιχτο»).
ΤΑΣΗ ΠΟΝΤΩΝ ομαδας (περσινη σεζον, κοινη κλιμακα): ridge στο ΣΥΝΟΛΟ καθε ματς (ολα τα πρωταθληματα + EL/EuroCup/BCL/FEC):
  συνολο = επιπεδο διοργανωσης + τ_γηπ + τ_φιλ   (τ = ποσους ποντους «φερνει» η ομαδα στα ματς της)
ΔΙΟΡΘΩΣΗ ΦΙΛΙΚΩΝ (ιδεα Στελιου): επιπεδο προετοιμασιας μ_pre(ετος) = μεσος (συνολο − τ_γηπ − τ_φιλ) στα φιλικα/Super Cups του ετους
  → «ποσο πιο ανοιχτα» ειναι · αφαιρειται πριν κριθουν οι ομαδες.
ΦΕΤΙΝΗ ΤΑΣΗ: r_T = Σ(συνολο − μ_pre − τ_γηπ − τ_φιλ)/(n + 4) στα ματς προετοιμασιας (1 Αυγ … πρεμιερα) της ομαδας EL.
1. ΔΙΑΓΝΩΣΗ (ομαδα-σεζον, αγων 1-10): κλιση (πραγμ − μοντελο), (αγορα − μοντελο), (πραγμ − αγορα) στο r_T.
2. ΜΟΝΤΕΛΟ: συνολο αγων ≤10 = v2+Κ2 + κ·(r_T γηπ + r_T φιλ), κ {.25, .5, .75, 1}.
   ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ: LOSO (κ απο τις αλλες σεζον) RMSE συνολου αγων 1-10 καλυτερο απο το live σε ≥4/5 σεζον (2021-25).
   Αναφορα: b, ROI over/under ≥8% αγων 1-10 (Pinnacle closing).
Εξοδος: el_preseason_totals_test_out.txt"""
import sys, json, math, datetime as dt
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
T = {}
src = open('el_total_curve_test.py', encoding='utf-8').read().split("VARS = ")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src, T)
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))
D, IDX, TOT, PRC, SE, RS, RND, C2, probs = (T[k] for k in ('D', 'IDX', 'TOT', 'PRC', 'SE', 'RS', 'RND', 'C2', 'probs'))
ST = 16.7
SEAS = ['E2021', 'E2022', 'E2023', 'E2024', 'E2025']
FG = json.load(open('fs_bk_games.json', encoding='utf-8')); PS = json.load(open('fs_bk_preseason.json', encoding='utf-8'))
def tendency(y):
    """τ ομαδων & επιπεδο ανα διοργανωση απο τα ΣΥΝΟΛΑ ολων των ματς της σεζον y."""
    rows = []
    for key, L in FG.items():
        c, yy = key.split('_')
        if int(yy) != y: continue
        for e in L:
            try: tot = int(e['hs']) + int(e['as_'])
            except Exception: continue
            if e.get('hid') and e.get('aid') and 100 < tot < 260: rows.append((c, e['hid'], e['aid'], float(tot)))
    comps = sorted({r[0] for r in rows}); teams = sorted({r[1] for r in rows} | {r[2] for r in rows})
    ci = {c: i for i, c in enumerate(comps)}; ti = {t: i for i, t in enumerate(teams)}; nc, nt, k = len(comps), len(teams), len(rows)
    A = np.zeros((k + nt, nc + nt)); b = np.zeros(k + nt); r_ = np.arange(k)
    A[r_, [ci[r[0]] for r in rows]] = 1; A[r_, [nc + ti[r[1]] for r in rows]] += 1; A[r_, [nc + ti[r[2]] for r in rows]] += 1; b[:k] = [r[3] for r in rows]
    A[k + np.arange(nt), nc + np.arange(nt)] = math.sqrt(3.0)
    x = np.linalg.lstsq(A, b, rcond=None)[0]
    return {t: x[nc + ti[t]] for t in teams}, {c: x[ci[c]] for c in comps}
PRE_T, NGT, LEVELS = {}, {}, {}
for Y in SEAS:
    y = int(Y[1:]); tau, lev = tendency(y - 1)
    S_el = D[D.season == Y]; start = min(pd.Timestamp(d).date() for d in S_el.date)
    # Flashscore → κωδικος EL
    FS2EL = {}
    idx = {}
    for r in S_el.itertuples(): idx.setdefault((int(r.hs), int(r.as_)), []).append(r)
    for e in FG.get(f'EL_{y}', []):
        try: hs, as_ = int(e['hs']), int(e['as_'])
        except Exception: continue
        d = dt.datetime.fromtimestamp(e['ts'], dt.timezone.utc).date()
        for r in idx.get((hs, as_), []):
            if abs((pd.Timestamp(r.date).date() - d).days) <= 1: FS2EL[e['hid']] = r.home; FS2EL[e['aid']] = r.away; break
    games = []
    for key, L in PS.items():
        for e in L:
            if not e.get('ts'): continue
            d = dt.datetime.fromtimestamp(e['ts'], dt.timezone.utc).date()
            if not (dt.date(y, 8, 1) <= d < start): continue
            try: tot = int(e['hs']) + int(e['as_'])
            except Exception: continue
            if e.get('hid') in tau and e.get('aid') in tau and 100 < tot < 260: games.append((e['hid'], e['aid'], tot - tau[e['hid']] - tau[e['aid']]))
    mu_pre = float(np.mean([g[2] for g in games])) if games else 0.0
    LEVELS[Y] = (mu_pre, lev.get('EL'), lev.get('ACB'), len(games))
    acc = {}
    for h, a, res in games:
        for me in (h, a):
            code = FS2EL.get(me)
            if code: acc.setdefault(code, []).append(res - mu_pre)
    for code, L in acc.items(): PRE_T[(Y, code)] = sum(L) / (len(L) + 4.0); NGT[(Y, code)] = len(L)
P('«ΠΟΣΟ ΑΝΟΙΧΤΑ» ΕΙΝΑΙ ΤΑ ΦΙΛΙΚΑ (επιπεδο συνολου, αφου αφαιρεθει η ταση των ομαδων):')
for Y, (mp, el, acb, n) in LEVELS.items():
    P(f'  {Y[-4:]}: προετοιμασια {mp:.1f} · Ευρωλιγκα {el:.1f} · ACB {acb:.1f} → φιλικα {mp - el:+.1f} π. vs EL ({n} ματς)')
P('ομαδες EL με r_T: ' + ' · '.join(f'{Y[-4:]}: {sum(1 for k in PRE_T if k[0] == Y)} (μεσος {np.mean([NGT[k] for k in NGT if k[0] == Y]):.1f} ματς)' for Y in SEAS))
# ---- 1. διαγνωση ----
DH = D.home.values[IDX]; DA = D.away.values[IDX]; MT = PRC[:, 3]
ok = RS & np.isin(SE, SEAS) & (RND <= 10)
rows = []
for Y in SEAS:
    for code in sorted(set(DH[SE == Y])):
        if (Y, code) not in PRE_T: continue
        m = ok & (SE == Y) & ((DH == code) | (DA == code))
        if not m.any(): continue
        mk = m & np.isfinite(MT)
        rows.append(dict(Y=Y, r=PRE_T[(Y, code)], err=np.mean((TOT - C2)[m]),
                         mkt=np.mean((MT - C2)[mk]) if mk.any() else np.nan, am=np.mean((TOT - MT)[mk]) if mk.any() else np.nan))
R = pd.DataFrame(rows)
P('')
P(f'=== 1. ΔΙΑΓΝΩΣΗ ({len(R)} ομαδες-σεζον, αγων 1-10· + = τα ματς της ομαδας βγηκαν ΠΙΟ ΠΟΛΛΟΙ ποντοι απο …) ===')
for lab, col in (('πραγματικο − μοντελο', 'err'), ('αγορα − μοντελο', 'mkt'), ('πραγματικο − αγορα', 'am')):
    d = R.dropna(subset=[col]); b, a = np.polyfit(d.r, d[col], 1); res = d[col] - (a + b * d.r)
    se = np.sqrt(np.sum(res ** 2) / (len(d) - 2) / np.sum((d.r - d.r.mean()) ** 2))
    per = ' '.join(f'{Y[-2:]}:{np.polyfit(d[d.Y == Y].r, d[d.Y == Y][col], 1)[0]:+.2f}' for Y in SEAS if (d.Y == Y).sum() >= 5)
    P(f'  κλιση {lab:22s} πανω στη φετινη ταση ποντων: {b:+.2f} (t {b / se:+.1f}) · ανα σεζον {per}')
P(f'  φετινη ταση r_T: διασπορα {R.r.std():.2f} π.')
# ---- 2. μεσα στο μοντελο ----
def adj(kp):
    t = np.array(C2, float).copy()
    for j in range(len(IDX)):
        if RND[j] <= 10 and SE[j] in SEAS:
            t[j] += kp * (PRE_T.get((SE[j], DH[j]), 0.0) + PRE_T.get((SE[j], DA[j]), 0.0))
    return t
PRED = {0.0: np.array(C2, float)}
for kp in (0.25, 0.5, 0.75, 1.0): PRED[kp] = adj(kp)
E10 = RS & (RND <= 10)
def rm(v, ss): m = E10 & np.isin(SE, ss); return float(np.sqrt(np.mean((TOT - v)[m] ** 2)))
P('')
P('=== 2. ΜΕΣΑ ΣΤΟ ΜΟΝΤΕΛΟ (συνολο αγων ≤10 + κ·(r_T γηπ + r_T φιλ)) ===')
P('  in-sample RMSE αγων 1-10: ' + ' · '.join(f'κ {k}: {rm(v, SEAS):.3f}' for k, v in PRED.items()))
held = np.array(C2, float).copy(); ch = []
for Y in SEAS:
    tr = [s for s in SEAS if s != Y]; k = min(PRED, key=lambda k: rm(PRED[k], tr)); ch.append(k); held[SE == Y] = PRED[k][SE == Y]
base = PRED[0.0]
diffs = [rm(held, [Y]) - rm(base, [Y]) for Y in SEAS]; w_ = sum(d < 0 for d in diffs)
P(f'  LOSO κ {ch} · RMSE αγων 1-10 {rm(base, SEAS):.3f} → {rm(held, SEAS):.3f} · ανα σεζον ' + ' '.join(f'{d:+.3f}' for d in diffs) + f' → καλυτερο {w_}/5 → {"ΠΕΡΝΑ" if w_ >= 4 else "✗"}')
def tot_roi(tt, msk, thr=0.08):
    res = {'over': [], 'under': []}
    for j in range(len(IDX)):
        if not msk[j] or np.isnan(PRC[j, 3]): continue
        TL, ov, un = PRC[j, 3], PRC[j, 4], PRC[j, 5]
        po, pq, pu = probs(tt[j], -TL, ST); eo, eu = po * ov + pq - 1, pu * un + pq - 1
        over, e, o = (True, eo, ov) if eo >= eu else (False, eu, un)
        if e < thr: continue
        v = (TOT[j] - TL) * (1 if over else -1)
        res['over' if over else 'under'].append(((o - 1) if v > 0 else (0 if v == 0 else -1), SE[j]))
    f = lambda L: f'{np.mean([x[0] for x in L])*100:+.1f}% ({len(L)}) {sum(1 for s in SEAS if any(x[1] == s for x in L) and np.mean([x[0] for x in L if x[1] == s]) > 0)}/5' if L else '—'
    return f"over {f(res['over'])} · under {f(res['under'])} · ολα {f(res['over'] + res['under'])}"
m10 = E10 & np.isin(SE, SEAS) & np.isfinite(MT)
P('')
P(f'=== 3. ΑΓΟΡΑ / b / ROI αγων 1-10 (Pinnacle closing) · RMSE αγορας {np.sqrt(np.mean((TOT - MT)[m10] ** 2)):.3f} ===')
for nm, v in (('live (v2+Κ2)', base), ('με προετοιμασια (LOSO)', held)):
    b = np.polyfit((v - MT)[m10], (TOT - MT)[m10], 1)[0]
    P(f'  {nm:24s} RMSE {np.sqrt(np.mean((TOT - v)[m10] ** 2)):.3f} · b {b:+.3f} · ROI ≥8% {tot_roi(v, m10)}')
open('el_preseason_totals_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
