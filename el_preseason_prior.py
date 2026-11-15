# -*- coding: utf-8 -*-
"""el_preseason_prior.py — ΑΠΟΔΟΣΗ ΠΡΟΕΤΟΙΜΑΣΙΑΣ ομαδων Ευρωλιγκας (1/10/2026, αποφαση Στελιου «το κραταμε» · τεστ el_preseason_test.py:
LOSO κ 0.5 σε 5/5 σεζον, RMSE αγων 1-10 11.304 → 11.185 (4/5), ROI χαντικαπ ≥8% +8.5 → +15.1%).
r = Σ[διαφορα (ταβανι ±20) − (R_ομαδας − R_αντιπαλου)] / (n + 4) σε φιλικα & Super Cups απο 1 Αυγουστου ως την πρεμιερα EL,
    R = κοινη κλιμακα («Elo» μπασκετ) της ΠΕΡΣΙΝΗΣ σεζον (ridge σε ολα τα ματς fs_bk_games: 10 πρωταθληματα + EL/EuroCup/BCL/FEC),
    αντιπαλοι χωρις rating (NBA, μικρα πρωταθληματα) εκτος, χωρις εδρα.
Τρεχει ΜΙΑ φορα τη σεζον, μετα τη ληψη: flashscore_bk_domestic.py (τρεχουσα σεζον) + flashscore_bk_preseason.py.
Χρηση: python el_preseason_prior.py [ετος=2026] → el_preseason_prior.json (διαβαζεται απο el_refresh.py, κ 0.5 στην αφετηρια χαντικαπ).
ΣΥΝΟΛΑ (1/10/2026, Στελιος «περασε το νεο και στα συνολα»· el_preseason_totals_test/_deep: LOSO κ .25 σε 5/5, RMSE αγων 1-10
16.453 → 16.353 (4/5), b .08 → .26, alert Crown ≥6ω +2.7% → +5.4% 4/5): ταση ποντων r_T = Σ(συνολο − μ_pre − τ_γηπ − τ_φιλ)/(n + 4),
τ = ridge περσινων ΣΥΝΟΛΩΝ (επιπεδο ανα διοργανωση + τ ομαδων), μ_pre = ποσο «ανοιχτα» ειναι τα φετινα φιλικα.
Στο el_refresh: συνολο αγων ≤10 += kappa_T·(r_T γηπ + r_T φιλ)."""
import sys, json, math, datetime as dt
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
from el_season import Y as _CY               # 1/10: τρεχουσα σεζον αυτοματα (ηταν 2026)
Y = int(sys.argv[1]) if len(sys.argv) > 1 else _CY
KAPPA = 0.5
KAPPA_T = 0.25
FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
PS = json.load(open('fs_bk_preseason.json', encoding='utf-8'))
_SCH = json.load(open('el_sched.json', encoding='utf-8'))
S = _SCH[f'E{Y}']

def common(y):
    rows = []
    for key, L in FG.items():
        c, yy = key.split('_')
        if int(yy) != y: continue
        for e in L:
            try: m = float(np.clip(int(e['hs']) - int(e['as_']), -20, 20))
            except Exception: continue
            if e.get('hid') and e.get('aid'): rows.append((e['hid'], e['aid'], m))
    teams = sorted({r[0] for r in rows} | {r[1] for r in rows}); ix = {t: i for i, t in enumerate(teams)}; n = len(teams); k = len(rows)
    A = np.zeros((k + n, n + 1)); b = np.zeros(k + n); r_ = np.arange(k)
    A[r_, [ix[r[0]] for r in rows]] = 1; A[r_, [ix[r[1]] for r in rows]] = -1; A[r_, n] = 1; b[:k] = [r[2] for r in rows]
    A[k + np.arange(n), np.arange(n)] = math.sqrt(2)
    x = np.linalg.lstsq(A, b, rcond=None)[0]
    return {t: float(x[ix[t]]) for t in teams}

def tendency(y):
    """ταση ποντων ομαδων (τ) απο τα ΣΥΝΟΛΑ ολων των ματς της σεζον y (επιπεδο ανα διοργανωση) — ιδιο με el_preseason_totals_test.py"""
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
    return {t: float(x[nc + ti[t]]) for t in teams}

C = common(Y - 1)
# κωδικος Flashscore → κωδικος EL (ματς EL της σεζον: ημερομηνια ±1 + σκορ)
# 1/10: ΚΑΙ απο τα περσινα ματς EL (ο κωδικος Flashscore ειναι σταθερος) → αντιστοιχιση ΠΡΙΝ την πρεμιερα· οι νεες ομαδες μετα την 1η αγων.
FS2EL = {}
for e, SS in [(e, _SCH.get(f'E{Y - 1}', [])) for e in FG.get(f'EL_{Y - 1}', [])] + [(e, S) for e in FG.get(f'EL_{Y}', [])]:
    try: hs, as_ = int(e['hs']), int(e['as_'])
    except Exception: continue
    d = dt.datetime.fromtimestamp(e['ts'], dt.timezone.utc).date()
    for x in SS:
        if x.get('played') and x.get('hs') == hs and x.get('as_') == as_ and abs((dt.date.fromisoformat(x['utc'][:10]) - d).days) <= 1:
            FS2EL[e['hid']] = x['hcode']; FS2EL[e['aid']] = x['acode']
start = min(dt.date.fromisoformat(x['utc'][:10]) for x in S)
acc = {}
for key, L in PS.items():
    for e in L:
        if not e.get('ts'): continue
        d = dt.datetime.fromtimestamp(e['ts'], dt.timezone.utc).date()
        if not (dt.date(Y, 8, 1) <= d < start): continue
        try: m = float(np.clip(int(e['hs']) - int(e['as_']), -20, 20))
        except Exception: continue
        for me, op, sg in ((e.get('hid'), e.get('aid'), 1), (e.get('aid'), e.get('hid'), -1)):
            code = FS2EL.get(me)
            if code and me in C and op in C: acc.setdefault(code, []).append(sg * m - (C[me] - C[op]))
# ---- συνολα: ταση ποντων ----
TAU = tendency(Y - 1); gT = []
for key, L in PS.items():
    for e in L:
        if not e.get('ts'): continue
        d = dt.datetime.fromtimestamp(e['ts'], dt.timezone.utc).date()
        if not (dt.date(Y, 8, 1) <= d < start): continue
        try: tot = int(e['hs']) + int(e['as_'])
        except Exception: continue
        if e.get('hid') in TAU and e.get('aid') in TAU and 100 < tot < 260: gT.append((e['hid'], e['aid'], tot - TAU[e['hid']] - TAU[e['aid']]))
MU_PRE = float(np.mean([g[2] for g in gT])) if gT else 0.0
accT = {}
for h, a, res in gT:
    for me in (h, a):
        code = FS2EL.get(me)
        if code: accT.setdefault(code, []).append(res - MU_PRE)
teams = sorted({x['hcode'] for x in S} | {x['acode'] for x in S})
RT = {c: round(sum(accT.get(c, [])) / (len(accT.get(c, [])) + 4.0), 3) for c in teams}
R = {c: round(sum(acc.get(c, [])) / (len(acc.get(c, [])) + 4.0), 3) for c in teams}
json.dump(dict(season=f'E{Y}', kappa=KAPPA, generated=dt.datetime.now(dt.timezone.utc).isoformat(timespec='minutes'),
               r=R, n={c: len(acc.get(c, [])) for c in teams}, mapped=len(set(FS2EL.values())),
               kappa_T=KAPPA_T, rT=RT, nT={c: len(accT.get(c, [])) for c in teams}, mu_pre=round(MU_PRE, 2)),
          open('el_preseason_prior.json', 'w', encoding='utf-8'), indent=1)
print(f'E{Y}: αντιστοιχισμενες {len(set(FS2EL.values()))}/{len(teams)} · ' + ' · '.join(f'{c} {R[c]:+.2f}({len(acc.get(c, []))})' for c in sorted(R, key=lambda c: -R[c])))
print(f'ΣΥΝΟΛΑ: μ_pre {MU_PRE:+.1f} ({len(gT)} ματς) · ' + ' · '.join(f'{c} {RT[c]:+.2f}({len(accT.get(c, []))})' for c in sorted(RT, key=lambda c: -RT[c])))
