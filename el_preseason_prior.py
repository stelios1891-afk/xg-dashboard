# -*- coding: utf-8 -*-
"""el_preseason_prior.py — ΑΠΟΔΟΣΗ ΠΡΟΕΤΟΙΜΑΣΙΑΣ ομαδων Ευρωλιγκας (1/10/2026, αποφαση Στελιου «το κραταμε» · τεστ el_preseason_test.py:
LOSO κ 0.5 σε 5/5 σεζον, RMSE αγων 1-10 11.304 → 11.185 (4/5), ROI χαντικαπ ≥8% +8.5 → +15.1%).
r = Σ[διαφορα (ταβανι ±20) − (R_ομαδας − R_αντιπαλου)] / (n + 4) σε φιλικα & Super Cups απο 1 Αυγουστου ως την πρεμιερα EL,
    R = κοινη κλιμακα («Elo» μπασκετ) της ΠΕΡΣΙΝΗΣ σεζον (ridge σε ολα τα ματς fs_bk_games: 10 πρωταθληματα + EL/EuroCup/BCL/FEC),
    αντιπαλοι χωρις rating (NBA, μικρα πρωταθληματα) εκτος, χωρις εδρα.
Τρεχει ΜΙΑ φορα τη σεζον, μετα τη ληψη: flashscore_bk_domestic.py (τρεχουσα σεζον) + flashscore_bk_preseason.py.
Χρηση: python el_preseason_prior.py [ετος=2026] → el_preseason_prior.json (διαβαζεται απο el_refresh.py, κ 0.5 στην αφετηρια χαντικαπ)."""
import sys, json, math, datetime as dt
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
Y = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
KAPPA = 0.5
FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
PS = json.load(open('fs_bk_preseason.json', encoding='utf-8'))
S = json.load(open('el_sched.json', encoding='utf-8'))[f'E{Y}']

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

C = common(Y - 1)
# κωδικος Flashscore → κωδικος EL (ματς EL της σεζον: ημερομηνια ±1 + σκορ)
FS2EL = {}
for e in FG.get(f'EL_{Y}', []):
    try: hs, as_ = int(e['hs']), int(e['as_'])
    except Exception: continue
    d = dt.datetime.fromtimestamp(e['ts'], dt.timezone.utc).date()
    for x in S:
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
teams = sorted({x['hcode'] for x in S} | {x['acode'] for x in S})
R = {c: round(sum(acc.get(c, [])) / (len(acc.get(c, [])) + 4.0), 3) for c in teams}
json.dump(dict(season=f'E{Y}', kappa=KAPPA, generated=dt.datetime.now(dt.timezone.utc).isoformat(timespec='minutes'),
               r=R, n={c: len(acc.get(c, [])) for c in teams}, mapped=len(set(FS2EL.values()))),
          open('el_preseason_prior.json', 'w', encoding='utf-8'), indent=1)
print(f'E{Y}: αντιστοιχισμενες {len(set(FS2EL.values()))}/{len(teams)} · ' + ' · '.join(f'{c} {R[c]:+.2f}({len(acc.get(c, []))})' for c in sorted(R, key=lambda c: -R[c])))
