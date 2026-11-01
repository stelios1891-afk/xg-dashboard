# -*- coding: utf-8 -*-
"""t103_totals_absence_pace.py — ΣΥΝΟΛΑ NBA: ΡΥΘΜΟΣ ΤΟΥ ΑΠΟΝΤΑ (25/10/2026, Στελιος «οκ» στον ορισμο).
Ρυθμος παικτη = κατοχες/48 on vs off μεσα στην ομαδα (t103_pace_player_build.py → _t103_pace.pkl), ΠΕΡΣΙΝΗ σεζον (≥300′, αλλιως 0).
ΔΚ = −Σ αποντων (ιδιοι με live: Out στην τελευταια αναφορα πριν το ανοιγμα, ρολος ≥20′) ρυθμος × λεπτα/48.
  Α: συνολο += 2.30·ΔΚ (θεωρια: ~2.3 ποντοι ανα κατοχη για τις 2 ομαδες) · Β: συνολο += c·ΔΚ (c LOSO).
ΒΑΣΗ = LIVE: νεα μηχανη (run_all_split, αμυνα .25, HL 45, K 6) + Φ3 − 0.5·LO + 1.0·LD · ανοιγμα Crown · edge ≥8% · σεζον 2022-23 … 2025-26 (4).
ΚΡΙΤΗΡΙΑ (γραφτηκαν πριν): σφαλμα καλυτερο ≥3/4 · μοναδες & CLV οχι χειροτερα · walk-forward οχι χειροτερο · placebo <5% · Β: c>0 σε ολα τα folds.
Καλουπι: t98_totals_absence_scorers_decay.py. Εξοδος: nba_tests/t103_totals_absence_pace_out.txt"""
import os, sys, io, contextlib, collections, pickle
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
os.chdir(ROOT); sys.path.insert(0, ROOT); sys.path.insert(0, SC)
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import numpy as np, pandas as pd
from statistics import NormalDist
from multiprocessing import Pool
import nba_full_clean_test as F
def job(k):
    F._init()
    return k, (F.run_all((0.7, 8, 60, .5, 5.0, 0.0, 0.0, 0.0))[2] if k == 'old' else F.run_all_split((0.7, 6, 45, .5, 5.0, 0.0, 0.0, 0.0), 0.25)[2])
if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    out = []
    def P(s=''): print(s, flush=True); out.append(str(s))
    with Pool(2) as p: TT = dict(p.map(job, ['old', 'new']))
    F._init(); GC = F._W['C'].G
    class _B(io.StringIO):
        def reconfigure(self, **k): pass
    src = open(os.path.join(SC, 't35_totals_build.py'), encoding='utf-8').read().split('rows = []')[0]
    g = {'__file__': os.path.join(SC, 't35_totals_build.py'), '__name__': 'x'}
    with contextlib.redirect_stdout(_B()): exec(src, g)
    sys.stdout.reconfigure(encoding='utf-8')
    status_at, K2P, mins, odval, SER, SHIFT, G22, dD, mk_t = (g[x] for x in ('status_at', 'K2P', 'mins', 'odval', 'SER', 'SHIFT', 'G', 'dD', 'mk_t'))
    PACE = pickle.load(open(os.path.join(SC, '_t103_pace.pkl'), 'rb'))
    NMS = pd.read_csv(os.path.join(ROOT, 'nba_player_games.csv'), usecols=['PLAYER_ID', 'PLAYER_NAME']).drop_duplicates('PLAYER_ID')
    NM = dict(zip(NMS.PLAYER_ID.astype(str), NMS.PLAYER_NAME))
    miss = collections.Counter()
    def absents(t, d, s, tau):
        res = []
        for k, stt in status_at(t, d, tau).items():
            if stt != 'Out': continue
            pid = K2P.get((k, t, s))
            if pid is None: continue
            m = mins(pid, t, s, d)
            if m is None or m < 20: continue
            o_, d_ = odval(pid, s - 1); xo = (o_ + 0.5) * m / 48; xd = (d_ + 0.5) * m / 48
            pv = PACE.get(s - 1, {}).get(str(pid))
            if pv is None or pv[1] < 300: miss['χωρις περσινο ρυθμο'] += 1; pc = 0.0
            else: miss['με ρυθμο'] += 1; pc = pv[0]
            res.append((xo, xd, -pc * m / 48, f"{NM.get(str(pid), pid)} ({t}, ρυθμος {pc:+.1f}, {m:.0f}′)"))
        return res
    X = pd.read_csv(os.path.join(SC, '_t35_totals.csv')); X = X[X.tau == 'ανοιγμα'].dropna(subset=['T', 'oo', 'ou', 'fair', 'cfair', 'tot']).reset_index(drop=True)
    GI = {(str(GC.date.values[k])[:10], GC.home.values[k], GC.away.values[k]): k for k in range(len(GC))}
    GI22 = {(str(dD[k])[:10], G22.home.values[k], G22.away.values[k]): k for k in range(len(G22))}
    X['g'] = [GI.get((str(d)[:10], h, a)) for d, h, a in zip(X.date, X.home, X.away)]; X['i2'] = [GI22.get((str(d)[:10], h, a)) for d, h, a in zip(X.date, X.home, X.away)]
    X = X[X.g.notna() & X.i2.notna()].copy(); X['g'] = X.g.astype(int); X['i2'] = X.i2.astype(int)
    X = X[[abs(GC.hs.values[k] + GC.as_.values[k] - t) < 0.5 for k, t in zip(X.g, X.tot)]].reset_index(drop=True)
    X = X[X.sea.astype(int) >= 2023].reset_index(drop=True)
    X['eng'] = X.tt + (TT['new'][X.g.values] - TT['old'][X.g.values]) + X.lev.fillna(0)
    FE = []
    for r in X.itertuples(index=False):
        i = r.i2; sw, tip, r21, r23 = SER[i]; rr = [[x[0] + SHIFT] + list(x[1:]) for x in (r23 or [])]
        tau = rr[0][0] if rr else tip; s = int(r.sea); d = dD[i]
        L = absents(r.home, d, s, tau) + absents(r.away, d, s, tau)
        FE.append(dict(LO=sum(x[0] for x in L), LD=sum(x[1] for x in L), DK=sum(x[2] for x in L), WHO=' · '.join(x[3] for x in L)))
    FE = pd.DataFrame(FE); X = pd.concat([X, FE], axis=1)
    P(f'ελεγχος: LO/LD εδω vs _t35 · μεγ. διαφορα LO {np.abs(X.LO - X.lo).max():.3f} · LD {np.abs(X.LD - X.ld).max():.3f} · ματς {len(X)} · αποντες (Out ρολου): ' + ' · '.join(f'{k} {v}' for k, v in miss.items()))
    ys = X.sea.values; SE = sorted(set(ys)); Y = X.tot.values; ND = NormalDist(); SIG = 18.0; rng = np.random.default_rng(23)
    day = pd.to_datetime(X.date).values.astype('datetime64[D]'); wk = (day - day.min()).astype(int) // 7
    def cover(mu, T):
        if abs(T - round(T)) < 1e-9:
            po = ND.cdf((mu - T - 0.5) / SIG); pu = ND.cdf((T - mu - 0.5) / SIG); return po, 1 - po - pu, pu
        po = ND.cdf((mu - T) / SIG); return po, 0.0, 1 - po
    def pu(mu):
        u = np.zeros(len(X)); c = np.full(len(X), np.nan)
        for j, r in enumerate(X.itertuples(index=False)):
            po, pp, pq = cover(mu[j], r.T); eo, eu = po * r.oo + pp - 1, pq * r.ou + pp - 1
            sd, e, od = (1, eo, r.oo) if eo >= eu else (-1, eu, r.ou)
            if e < .08: continue
            x = (r.tot - r.T) * sd; u[j] = (od - 1) if x > 0 else (0.0 if x == 0 else -1.0); c[j] = sd * (r.cfair - r.fair)
        return u, c
    BASE = X.eng.values - 0.5 * X.LO.values + 1.0 * X.LD.values
    dk = X.DK.values; res0 = Y - BASE; nz = np.abs(dk) > 1e-9
    P(f'ΔΚ (κατοχες που αλλαζουν απο τους αποντες): ματς με ΔΚ≠0 {int(nz.sum())} απο {len(X)} · |ΔΚ| μεσος (οπου ≠0) {np.abs(dk[nz]).mean():.2f} κατοχες'
      f' · ματς με |2.3·ΔΚ| ≥0.5 π. {int((np.abs(2.3 * dk) >= 0.5).sum())} · ≥1.5 π. {int((np.abs(2.3 * dk) >= 1.5).sum())}')
    cS, cW = {}, {}
    for s in SE:
        tr = ys != s; cS[s] = float((dk[tr] @ res0[tr]) / (dk[tr] @ dk[tr] + 1.0))
        pr = ys < s; cW[s] = float((dk[pr] @ res0[pr]) / (dk[pr] @ dk[pr] + 1.0)) if pr.any() else 2.30
    cAll = float((dk @ res0) / (dk @ dk + 1.0))
    P(f"Β: c (ποντοι συνολου ανα 1 κατοχη, θεωρια ~+2.3) LOSO " + ' '.join(f'{s % 100}:{cS[s]:+.2f}' for s in SE) + f' · ολα μαζι {cAll:+.2f} · walk-forward ' + ' '.join(f'{s % 100}:{cW[s]:+.2f}' for s in SE))
    MU = {'LIVE': BASE, 'Α 2.30': BASE + 2.30 * dk, 'Β LOSO': BASE + np.array([cS[s] for s in ys]) * dk}
    MUW = {'Α 2.30': MU['Α 2.30'], 'Β LOSO': BASE + np.array([cW[s] for s in ys]) * dk}
    U = {k: pu(v) for k, v in MU.items()}; UW = {k: pu(v) for k, v in MUW.items()}
    rm = lambda mu, m: float(np.sqrt(np.mean((Y[m] - mu[m]) ** 2)))
    od_ = X.mon.isin([10, 11, 12]).values
    for k in MU:
        u, c = U[k]; ps = {s: u[ys == s].sum() for s in SE}; pk = int((~np.isnan(c)).sum())
        line = (f"  {k:7s} σφαλμα {rm(MU[k], ys == ys):.3f} (" + ' '.join(f'{s % 100}:{rm(MU[k], ys == s):.3f}' for s in SE)
                + f') · μοναδες {u.sum():+6.1f} σε {pk} picks ({100 * u.sum() / max(pk, 1):+.1f}%, θετ {sum(v > 0 for v in ps.values())}/4, Οκτ-Δεκ {u[od_].sum():+.1f}) · CLV {np.nanmean(c):+.2f}')
        if k != 'LIVE':
            bet = sum(rm(MU[k], ys == s) < rm(BASE, ys == s) for s in SE)
            dd = pd.Series((Y - BASE) ** 2 - (Y - MU[k]) ** 2).groupby(day).sum().values; t = dd.mean() / (dd.std(ddof=1) / np.sqrt(len(dd)))
            dw = pd.Series(u - U['LIVE'][0]).groupby(wk).sum().values; bs = np.array([dw[rng.integers(0, len(dw), len(dw))].sum() for _ in range(2000)])
            wf = (UW[k][0].sum(), U['LIVE'][0].sum())
            dlt = MU[k] - BASE; real = dw.sum(); rs = []
            for _ in range(150):
                perm = dlt.copy()
                for s in SE:
                    m = np.where(ys == s)[0]; perm[m] = dlt[rng.permutation(m)]
                rs.append(pu(BASE + perm)[0].sum() - U['LIVE'][0].sum())
            pl = 100 * (np.array(rs) >= real).mean()
            csign = all(v > 0 for v in cS.values()) if k.startswith('Β') else True
            ok = bet >= 3 and u.sum() >= U['LIVE'][0].sum() and np.nanmean(c) >= np.nanmean(U['LIVE'][1]) and wf[0] >= wf[1] and pl < 5 and csign
            line += f' │ καλυτερο {bet}/4 · t {t:+.2f} · Δμοναδες {real:+.1f} (P {100 * (bs > 0).mean():.0f}%) · WF {wf[0]:+.1f} vs {wf[1]:+.1f} · placebo {pl:.0f}% → {"ΠΕΡΝΑΕΙ" if ok else "✗"}'
        P(line)
    cL, cA = U['LIVE'][1], U['Α 2.30'][1]; uL, uA = U['LIVE'][0], U['Α 2.30'][0]
    P('\nΜΕ ΜΕΓΑΛΟ ΔΚ (|2.3·ΔΚ| ≥1.5 π.): ' + ' · '.join(
        f"{k}: σφαλμα {rm(MU[k], np.abs(2.3 * dk) >= 1.5):.2f}, μεσο υπολοιπο (πραγμ.−προβλ.) {np.mean((Y - MU[k])[np.abs(2.3 * dk) >= 1.5]):+.2f}" for k in MU))
    big = np.abs(2.3 * dk) >= 1.5
    P(f"  ελεγχος κατευθυνσης: οπου ΔΚ<0 (λειπει γρηγορος) μεσο υπολοιπο LIVE {np.mean(res0[big & (dk < 0)]):+.2f} ({int((big & (dk < 0)).sum())} ματς) · οπου ΔΚ>0 (λειπει αργος) {np.mean(res0[big & (dk > 0)]):+.2f} ({int((big & (dk > 0)).sum())}) — αν ο ρυθμος μετραει: πρωτο <0, δευτερο >0")
    ch = [j for j in np.argsort(-np.abs(dk)) if np.isnan(cL[j]) != np.isnan(cA[j])][:2]
    P('\nΠΑΡΑΔΕΙΓΜΑΤΑ (2 με το μεγαλυτερο |ΔΚ| + 2 οπου αλλαζει το pick):')
    for j in list(np.argsort(-np.abs(dk))[:2]) + ch:
        r = X.iloc[j]
        P(f"  {str(r.date)[:10]} {r.away}@{r.home} · γραμμη {r['T']:g} · LIVE {BASE[j]:.1f} → Α {MU['Α 2.30'][j]:.1f} · πραγματικο {r.tot:.0f}"
          f" · pick LIVE {'ναι' if not np.isnan(cL[j]) else 'οχι'} ({uL[j]:+.2f}) / Α {'ναι' if not np.isnan(cA[j]) else 'οχι'} ({uA[j]:+.2f}) · αποντες: {r.WHO}")
    open(os.path.join(SC, 't103_totals_absence_pace_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
