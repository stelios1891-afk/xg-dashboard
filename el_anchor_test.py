# -*- coding: utf-8 -*-
"""el_anchor_test.py — ΑΓΚΥΡΑ ΣΤΗΝ ΑΓΟΡΑ μεσα στο μοντελο χαντικαπ της Ευρωλιγκας (30/9/2026, ιδεα Στελιου — δουλεψε στο ποδοσφαιρο).
Διαφορα απο el_market_prior_test (25/9): εκει μπλεντ ΤΕΛΙΚΗΣ προβλεψης με κριτηριο ROI· εδω η αγορα μπαινει στην ΑΦΕΤΗΡΙΑ του μοντελου
  (οπως η αγκυρα στο ποδοσφαιρο) με κριτηριο ΑΚΡΙΒΕΙΑ.
RATING ΑΓΟΡΑΣ (καθε μερα της σεζον): ridge πανω στις γραμμες κλεισιματος Pinnacle ΟΛΩΝ των ματς που εχουν ηδη παιχτει φετος
  (αναμενομενη διαφορα γηπ = εδρα + R_γηπ − R_φιλ, ουδετερα χωρις εδρα, μαζεμα λ προς 0)· ΠΟΤΕ η γραμμη του ιδιου ματς.
ΑΦΕΤΗΡΙΑ: net = (1−α)·[live: 0.5 περσι + 0.42 ειδικοι] + α·R_αγορας·100/72 (μισο επιθεση/μισο αμυνα) — σβηνει μονη της με τα ματς.
Βαση = live σημερα (Β1 + ειδικοι· φετινα εγχωρια κ .5 ΜΟΝΟ απο τον 11ο αγωνα).
ΠΛΕΓΜΑ: α {0, .25, .5, .75, 1} × ενεργη εως {10ος αγωνας, ολη η σεζον} × λ {2, 5}.
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ: LOSO (ρυθμιση απο τις ΑΛΛΕΣ 4 σεζον, ελαχιστο RMSE αγων 1-10)· ΠΕΡΝΑ αν εκτος-δειγματος RMSE αγων 1-10
  καλυτερο απο τη βαση σε ≥4/5 σεζον. Αναφορα: αγων 5-10, 11+, b, ROI.
Εξοδος: el_anchor_test_out.txt"""
import sys, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
NS = {}
src = open('el_domestic_league_test.py', encoding='utf-8').read().split("PRED = {}\nfor var in")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src, NS)
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))
D, SE5, EM, GN, dnum, IDX, PRC, ACT, SE, RS = (NS[k] for k in ('D', 'SE5', 'EM', 'GN', 'dnum', 'IDX', 'PRC', 'ACT', 'SE', 'RS'))
fit_eff, fit_pace, LUCK, ENDS, cfg, S20, dom_shift = (NS[k] for k in ('fit_eff', 'fit_pace', 'LUCK', 'ENDS', 'cfg', 'S20', 'dom_shift'))
# γραμμη κλεισιματος ανα θεση του D (αναμενομενη διαφορα γηπεδουχου = −L)
LINE = np.full(len(D), np.nan)
for j, i in enumerate(IDX):
    if not np.isnan(PRC[j, 0]): LINE[i] = -PRC[j, 0]
NEUD = (D.ff.values | D.relocated.values)
P(f'γραμμες κλεισιματος στο D: {np.isfinite(LINE).sum()} · σεζον-τεστ ' + ' '.join(f'{Y[-4:]}:{np.isfinite(LINE[D.season.values == Y]).sum()}' for Y in SE5))
def market_ratings(Y, lam):
    """{μερα: (R ομαδων, εδρα)} με τις γραμμες των ματς ΑΥΣΤΗΡΑ πριν απο τη μερα."""
    sidx = np.where(D.season.values == Y)[0]; teams = sorted(set(D.home.values[sidx]) | set(D.away.values[sidx]))
    ix = {t: i for i, t in enumerate(teams)}; n = len(teams); dn = dnum[sidx]; res = {}
    ok = np.isfinite(LINE[sidx])
    for d in np.unique(dn):
        past = np.where((dn < d) & ok)[0]
        if len(past) < 3: continue
        A = np.zeros((len(past) + n, 1 + n)); y = np.zeros(len(past) + n)
        for r, k in enumerate(past):
            j = sidx[k]; A[r, 0] = 0.0 if NEUD[j] else 1.0; A[r, 1 + ix[D.home.values[j]]] = 1; A[r, 1 + ix[D.away.values[j]]] = -1; y[r] = LINE[j]
        A[len(past) + np.arange(n), 1 + np.arange(n)] = math.sqrt(lam)
        x = np.linalg.lstsq(A, y, rcond=None)[0]
        res[d] = {t: x[1 + i] for t, i in ix.items()}
    return res
MR = {(Y, lam): market_ratings(Y, lam) for Y in SE5 for lam in (2, 5)}
def run(alpha, until, lam, kappa):
    EH, EA = LUCK[cfg['lw']]; v = np.full(len(D), np.nan)
    for Y in SE5:
        st = ENDS[Y]; prior = st['prior']
        sidx = np.where(D.season.values == Y)[0]
        teams = sorted(set(D.home.values[sidx]) | set(D.away.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        e = np.array([EM[Y].get(t, 0.0) for t in teams]) * cfg['we']
        o0b = np.array([cfg['wt'] * prior.get(t, (0, 0, 0))[0] for t in teams]) + e / 2
        d0b = np.array([cfg['wt'] * prior.get(t, (0, 0, 0))[1] for t in teams]) - e / 2
        p0 = np.array([0.7 * prior.get(t, (0, 0, 0))[2] for t in teams])
        hi = np.array([ix[t] for t in D.home.values[sidx]]); ai = np.array([ix[t] for t in D.away.values[sidx]])
        hb = np.where(D.ff.values[sidx] | D.relocated.values[sidx], 0.0, cfg['h'] / 2); dn = dnum[sidx]; gn = GN[sidx]
        pred = np.full(len(sidx), np.nan); M = MR[(Y, lam)]
        for d in np.unique(dn):
            cur = np.where(dn == d)[0]; past = dn < d
            o0, d0 = o0b.copy(), d0b.copy()
            if alpha and d in M and (until >= 99 or gn[cur].min() <= until):
                mr = np.array([M[d][t] * 100 / 72 for t in teams]); net = o0 - d0
                sh = alpha * (mr - net); o0 = o0 + sh / 2; d0 = d0 - sh / 2
            if kappa:
                sh2 = np.array([kappa * dom_shift(S20, Y, t, d) * 100 / 72 for t in teams]); o0 = o0 + sh2 / 2; d0 = d0 - sh2 / 2
            if past.any():
                w = 0.5 ** ((d - dn[past]) / cfg['HL'])
                mu, O, Dd = fit_eff(hi[past], ai[past], EH[sidx][past], EA[sidx][past], hb[past], w, n, o0, d0, cfg['lam'], st['mu0'])
                pm, Pc = fit_pace(hi[past], ai[past], D.pace.values[sidx][past], w, n, p0, cfg['lam'], st['pm0'])
            else:
                mu, O, Dd, pm, Pc = st['mu0'], o0, d0, st['pm0'], p0
            hh, aa, hbb = hi[cur], ai[cur], hb[cur]
            pred[cur] = (pm + Pc[hh] + Pc[aa]) * ((mu + O[hh] + Dd[aa] + hbb) - (mu + O[aa] + Dd[hh] - hbb)) / 100
        v[sidx] = pred
    return np.where(GN >= 7, v * cfg['sf'], v)
def live_like(alpha, until, lam):
    a = run(alpha, until, lam, 0.0); b = run(alpha, until, lam, 0.5)
    return np.where(GN > 10, b, a)                          # φετινα εγχωρια μονο απο τον 11ο αγωνα (οπως live)
PRED = {(0.0, 0, 0): live_like(0.0, 99, 2)}
print('  βαση ετοιμη', flush=True)
for lam in (2, 5):
    for until in (10, 99):
        for alpha in (0.25, 0.5, 0.75, 1.0):
            PRED[(alpha, until, lam)] = live_like(alpha, until, lam); print(f'  α {alpha} εως {until} λ {lam} ετοιμο', flush=True)
ACTD = (D.hs - D.as_).values.astype(float); RSM = D.phase.values == 'RS'; SEASD = D.season.values
E10 = RSM & (GN <= 10); E510 = RSM & (GN >= 5) & (GN <= 10); M11 = RSM & (GN > 10)
def rm(v, ss, msk): m = msk & np.isin(SEASD, ss) & np.isfinite(v); return float(np.sqrt(np.mean((ACTD - v)[m] ** 2)))
base = PRED[(0.0, 0, 0)]
P('')
P('=== IN-SAMPLE RMSE (5 σεζον): αγων 1-10 · 5-10 · 11+ · ολη ===')
for k, v in PRED.items():
    lab = 'ΒΑΣΗ (live)' if k[0] == 0 else f'α {k[0]:<4} εως {"10ο" if k[1] == 10 else "ολη"} λ {k[2]}'
    P(f'  {lab:22s} {rm(v, SE5, E10):.3f} · {rm(v, SE5, E510):.3f} · {rm(v, SE5, M11):.3f} · {rm(v, SE5, RSM):.3f}')
jj = np.array([j for j in range(len(IDX)) if RS[j] and not np.isnan(PRC[j, 0]) and SE[j] in SE5])
L_, OH, OA = PRC[jj, 0], PRC[jj, 1], PRC[jj, 2]; AC = ACT[jj]; SJ = SE[jj]; GJ = GN[IDX[jj]]; MK = -L_
Phi = np.vectorize(lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2))))
isint = np.abs(L_ - np.round(L_)) < 1e-9
def roi(v, msk, thr=0.08):
    m = v[IDX][jj]
    pw = np.where(isint, Phi((m + L_ - 0.5) / 11.5), Phi((m + L_) / 11.5)); pl = np.where(isint, Phi((-m - L_ - 0.5) / 11.5), 1 - pw); pp = 1 - pw - pl
    eh, ea = pw * OH + pp - 1, pl * OA + pp - 1
    side = np.where(eh >= ea, 1, -1); e = np.maximum(eh, ea); od = np.where(side == 1, OH, OA)
    vv = (AC + L_) * side; pr = np.where(vv > 0, od - 1, np.where(vv == 0, 0.0, -1.0)); sel = (e >= thr) & msk
    pos_ = sum(1 for s in SE5 if (sel & (SJ == s)).any() and pr[sel & (SJ == s)].mean() > 0)
    return f'{pr[sel].mean()*100:+.1f}% ({sel.sum()}) {pos_}/5' if sel.any() else '—'
held = np.full(len(D), np.nan); ch = []
for Y in SE5:
    tr = [s for s in SE5 if s != Y]
    k = min(PRED, key=lambda k: rm(PRED[k], tr, E10)); ch.append(k); held[SEASD == Y] = PRED[k][SEASD == Y]
P('')
P('LOSO επιλογες: ' + ' | '.join(f'{Y[-4:]}: ' + ('βαση' if k[0] == 0 else f'α {k[0]} εως {"10ο" if k[1] == 10 else "ολη"} λ {k[2]}') for Y, k in zip(SE5, ch)))
for nm, msk in (('αγων 1-10', E10), ('αγων 5-10', E510), ('αγων 11+', M11), ('ολη η σεζον', RSM)):
    diffs = [rm(held, [Y], msk) - rm(base, [Y], msk) for Y in SE5]; w_ = sum(d < 0 for d in diffs)
    P(f'  {nm:12s}: βαση {rm(base, SE5, msk):.3f} → αγκυρα {rm(held, SE5, msk):.3f} · ανα σεζον ' + ' '.join(f'{d:+.3f}' for d in diffs)
      + f' → καλυτερο {w_}/5' + (f' → {"ΠΕΡΝΑ" if w_ >= 4 else "✗"}' if nm == 'αγων 1-10' else ''))
P('')
for nm, v in (('βαση (live)', base), ('με αγκυρα (LOSO)', held)):
    for lab, msk in (('αγων 1-10', GJ <= 10), ('αγων 5-10', (GJ >= 5) & (GJ <= 10)), ('11+', GJ > 10), ('ολη', np.ones(len(jj), bool))):
        fin = np.isfinite(v[IDX][jj]) & msk
        b = np.polyfit((v[IDX][jj] - MK)[fin], (AC - MK)[fin], 1)[0]
        P(f'  {nm:18s} {lab:10s}: b {b:+.3f} · ROI ≥8% {roi(v, msk)} · ≥5% {roi(v, msk, 0.05)} · μεση |διαφωνια με αγορα| {np.nanmean(np.abs(v[IDX][jj] - MK)[msk]):.2f}')
open('el_anchor_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
