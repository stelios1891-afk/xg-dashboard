# -*- coding: utf-8 -*-
"""el_preseason_test.py — ΦΙΛΙΚΑ & SUPER CUPS ως πληροφορια για τις αγων 1-10 της Ευρωλιγκας (30/9/2026, ιδεα Στελιου).
Δεδομενα: fs_bk_preseason.json (Flashscore: club friendlies + Super Cups ACB/LBA/LNB/GBL/TBL/ISR/ABA/EL/DBB) · κοινη κλιμακα
  («Elo» μπασκετ, el_league_strength: ridge σε ολα τα ματς της ΠΕΡΣΙΝΗΣ σεζον — πρωταθληματα + EL/EuroCup/BCL/FEC).
ΑΠΟΔΟΣΗ ΠΡΟΕΤΟΙΜΑΣΙΑΣ ομαδας EL: ματς 1 Αυγ … πρεμιερα EL, αντιπαλος με περσινο rating στην κοινη κλιμακα (αλλιως εξω):
  r = Σ[διαφορα − (R_ομαδας − R_αντιπαλου)] / (n + 4)   (ταβανι ±20, χωρις εδρα — πολλα ουδετερα τουρνουα)
1. ΔΙΑΓΝΩΣΗ (ομαδα-σεζον, αγων 1-10): κλιση του λαθους του μοντελου (πραγμ − μοντ) και της αγορας (αγορα − μοντ, πραγμ − αγορα) στο r.
2. ΜΟΝΤΕΛΟ: αφετηρια + κ·r·100/72, κ {0.25, 0.5, 1}· ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ: LOSO RMSE αγων 1-10 καλυτερο απο το live σε ≥4/5 σεζον.
Εξοδος: el_preseason_test_out.txt"""
import sys, json, math, datetime as dt
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
NS = {}
src = open('el_anchor_test.py', encoding='utf-8').read().split("PRED = {(0.0, 0, 0)")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
src = src.replace("MR = {(Y, lam): market_ratings(Y, lam) for Y in SE5 for lam in (2, 5)}", "MR = {}")
src = src.replace("M = MR[(Y, lam)]", "M = MR.get((Y, lam), {})")
exec(src, NS)
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))
D, SE5, EM, GN, dnum, IDX, PRC, ACT, SE, RS = (NS[k] for k in ('D', 'SE5', 'EM', 'GN', 'dnum', 'IDX', 'PRC', 'ACT', 'SE', 'RS'))
fit_eff, fit_pace, LUCK, ENDS, cfg, S20, dom_shift = (NS[k] for k in ('fit_eff', 'fit_pace', 'LUCK', 'ENDS', 'cfg', 'S20', 'dom_shift'))
# ---- κοινη κλιμακα περσινης σεζον ----
FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
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
    return {t: x[ix[t]] for t in teams}
# ---- Flashscore κωδικος → κωδικος EL (απο τα ματς EL: ημερομηνια ±1 + σκορ) ----
FS2EL = {}
for Y in SE5 + ['E2026']:
    y = int(Y[1:]); fl = FG.get(f'EL_{y}', [])
    sub = D[D.season == Y]
    idx = {}
    for r in sub.itertuples(): idx.setdefault((int(r.hs), int(r.as_)), []).append(r)
    for e in fl:
        try: hs, as_ = int(e['hs']), int(e['as_'])
        except Exception: continue
        dd = dt.datetime.utcfromtimestamp(e['ts']).date()
        for r in idx.get((hs, as_), []):
            if abs((pd.Timestamp(r.date).date() - dd).days) <= 1:
                FS2EL[(Y, e['hid'])] = r.home; FS2EL[(Y, e['aid'])] = r.away; break
PS = json.load(open('fs_bk_preseason.json', encoding='utf-8'))
PRE, NG = {}, {}
for Y in SE5:
    y = int(Y[1:]); C = common(y - 1)
    start = min(pd.Timestamp(d).date() for d in D[D.season == Y].date)
    lo = dt.date(y, 8, 1)
    el_ids = {fid: code for (yy, fid), code in FS2EL.items() if yy == Y}
    acc = {}
    for key, L in PS.items():
        comp, yy = key.rsplit('_', 1)
        for e in L:
            dd = dt.datetime.utcfromtimestamp(e['ts']).date() if e.get('ts') else None
            if not dd or not (lo <= dd < start): continue
            try: m = float(np.clip(int(e['hs']) - int(e['as_']), -20, 20))
            except Exception: continue
            for side, me, op, sg in (('h', e.get('hid'), e.get('aid'), 1), ('a', e.get('aid'), e.get('hid'), -1)):
                code = el_ids.get(me)
                if not code or me not in C or op not in C: continue
                acc.setdefault(code, []).append((sg * m - (C[me] - C[op]), comp))
    for code, L in acc.items():
        PRE[(Y, code)] = sum(v for v, _ in L) / (len(L) + 4.0); NG[(Y, code)] = (len(L), sum(1 for _, c in L if c != 'FRIENDLY'))
P('ομαδες EL με ματς προετοιμασιας (αντιπαλοι με rating): ' + ' · '.join(f'{Y[-4:]}: {sum(1 for (yy, c) in PRE if yy == Y)}/{D[D.season == Y].home.nunique()}' for Y in SE5))
P('ματς ανα ομαδα (μεσος): ' + ' · '.join(f'{Y[-4:]}: {np.mean([NG[k][0] for k in NG if k[0] == Y]):.1f} (SC {np.mean([NG[k][1] for k in NG if k[0] == Y]):.1f})' for Y in SE5))
# ---- 1. διαγνωση ----
base = NS['live_like'](0.0, 99, 2)
ACTD = (D.hs - D.as_).values.astype(float); RSM = D.phase.values == 'RS'; SEASD = D.season.values
LINE = NS['LINE']
rows = []
for Y in SE5:
    for code in sorted(set(D[D.season == Y].home)):
        if (Y, code) not in PRE: continue
        m = RSM & (SEASD == Y) & (GN <= 10) & ((D.home.values == code) | (D.away.values == code))
        sg = np.where(D.home.values[m] == code, 1.0, -1.0)
        err = np.mean((ACTD[m] - base[m]) * sg)
        mk = np.isfinite(LINE[m])
        mkt = np.mean(((LINE[m] - base[m]) * sg)[mk]) if mk.any() else np.nan
        am = np.mean(((ACTD[m] - LINE[m]) * sg)[mk]) if mk.any() else np.nan
        rows.append(dict(Y=Y, code=code, r=PRE[(Y, code)], n=NG[(Y, code)][0], err=err, mkt=mkt, am=am))
R = pd.DataFrame(rows)
P('')
P(f'=== 1. ΔΙΑΓΝΩΣΗ ({len(R)} ομαδες-σεζον, αγων 1-10, ανα ομαδα: + = η ομαδα πηγε καλυτερα απο …) ===')
for lab, col in (('πραγματικο − μοντελο', 'err'), ('αγορα − μοντελο', 'mkt'), ('πραγματικο − αγορα', 'am')):
    d = R.dropna(subset=[col])
    b, a = np.polyfit(d.r, d[col], 1); res = d[col] - (a + b * d.r)
    se = np.sqrt(np.sum(res ** 2) / (len(d) - 2) / np.sum((d.r - d.r.mean()) ** 2))
    per = ' '.join(f'{Y[-2:]}:{np.polyfit(d[d.Y == Y].r, d[d.Y == Y][col], 1)[0]:+.2f}' for Y in SE5 if (d.Y == Y).sum() >= 5)
    P(f'  κλιση {lab:22s} πανω στην αποδοση προετοιμασιας: {b:+.2f} (t {b / se:+.1f}) · ανα σεζον {per}')
P(f'  αποδοση προετοιμασιας r: μεσος {R.r.mean():+.2f} · διασπορα {R.r.std():.2f} π.')
# ---- 2. μεσα στο μοντελο ----
def run_pre(kp):
    EH, EA = LUCK[cfg['lw']]; v = np.full(len(D), np.nan)
    for Y in SE5:
        st = ENDS[Y]; prior = st['prior']
        sidx = np.where(D.season.values == Y)[0]
        teams = sorted(set(D.home.values[sidx]) | set(D.away.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        e = np.array([EM[Y].get(t, 0.0) for t in teams]) * cfg['we']
        pr = np.array([kp * PRE.get((Y, t), 0.0) * 100 / 72 for t in teams])
        o0 = np.array([cfg['wt'] * prior.get(t, (0, 0, 0))[0] for t in teams]) + e / 2 + pr / 2
        d0 = np.array([cfg['wt'] * prior.get(t, (0, 0, 0))[1] for t in teams]) - e / 2 - pr / 2
        p0 = np.array([0.7 * prior.get(t, (0, 0, 0))[2] for t in teams])
        hi = np.array([ix[t] for t in D.home.values[sidx]]); ai = np.array([ix[t] for t in D.away.values[sidx]])
        hb = np.where(D.ff.values[sidx] | D.relocated.values[sidx], 0.0, cfg['h'] / 2); dn = dnum[sidx]
        pred = np.full(len(sidx), np.nan)
        for d in np.unique(dn):
            cur = np.where(dn == d)[0]; past = dn < d
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
E10 = RSM & (GN <= 10)
PRED = {0.0: base}
for kp in (0.25, 0.5, 1.0):
    PRED[kp] = np.where(GN > 10, base, run_pre(kp)); print(f'  κ {kp} ετοιμο', flush=True)
def rm(v, ss, msk): m = msk & np.isin(SEASD, ss) & np.isfinite(v); return float(np.sqrt(np.mean((ACTD - v)[m] ** 2)))
P('')
P('=== 2. ΜΕΣΑ ΣΤΟ ΜΟΝΤΕΛΟ (αφετηρια + κ·r) — αγων 1-10 ===')
P('  in-sample: ' + ' · '.join(f'κ {k}: {rm(v, SE5, E10):.3f}' for k, v in PRED.items()))
held = np.full(len(D), np.nan); ch = []
for Y in SE5:
    tr = [s for s in SE5 if s != Y]; k = min(PRED, key=lambda k: rm(PRED[k], tr, E10)); ch.append(k); held[SEASD == Y] = PRED[k][SEASD == Y]
diffs = [rm(held, [Y], E10) - rm(base, [Y], E10) for Y in SE5]; w_ = sum(d < 0 for d in diffs)
P(f'  LOSO κ {ch} · RMSE αγων 1-10 {rm(base, SE5, E10):.3f} → {rm(held, SE5, E10):.3f} · ανα σεζον ' + ' '.join(f'{d:+.3f}' for d in diffs)
  + f' → καλυτερο {w_}/5 → {"ΠΕΡΝΑ" if w_ >= 4 else "✗"}')
open('el_preseason_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
# ---- 3. b, ROI, αγορα (αγων 1-10 / 1-6 / 7-10) ----
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
P('')
P('=== 3. ΑΓΟΡΑ, b, ROI (Pinnacle closing) ===')
for lab, msk in (('αγων 1-10', GJ <= 10), ('αγων 1-6', GJ <= 6), ('αγων 7-10', (GJ >= 7) & (GJ <= 10))):
    P(f'  {lab}: RMSE αγορας {np.sqrt(np.mean((AC - MK)[msk] ** 2)):.3f} · live {np.sqrt(np.mean((AC - base[IDX][jj])[msk] ** 2)):.3f} · με προετοιμασια {np.sqrt(np.mean((AC - held[IDX][jj])[msk] ** 2)):.3f}')
    for nm, v in (('live', base), ('με προετοιμασια (LOSO)', held)):
        b = np.polyfit((v[IDX][jj] - MK)[msk], (AC - MK)[msk], 1)[0]
        P(f'     {nm:24s} b {b:+.3f} · ROI ≥8% {roi(v, msk)} · ≥5% {roi(v, msk, 0.05)} · |διαφωνια| {np.mean(np.abs(v[IDX][jj] - MK)[msk]):.2f}')
open('el_preseason_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
