# -*- coding: utf-8 -*-
"""t98_totals_absence_scorers_decay.py — ΣΥΝΟΛΑ NBA: ΑΠΟΥΣΙΕΣ (1) ΣΚΟΡΕΡ ΜΕ ΦΕΤΙΝΟΥΣ ΠΟΝΤΟΥΣ · (2) ΣΒΗΣΙΜΟ ΜΑΚΡΟΧΡΟΝΙΩΝ ΑΠΟΝΤΩΝ
(25/10/2026, Στελιος «τρεξτα ολα — υποτιμαμε τους σκορερ;»). Νεα μηχανη συνολων (run_all_split, αμυνα .25, HL 45, K 6) + Φ3, ανοιγμα Crown, 5 σεζον.
ΒΑΣΗ = live: −0.5·LO + 1.0·LD (περσινες αξιες επιθ/αμυνας, μονο Out, ρολος ≥20′) — ξαναϋπολογισμενο εδω (ελεγχος = ιδιο με _t35).
(1) ΣΚΟΡΕΡ: SC = Σ αποντων (φετινοι ποντοι/λεπτο − ποντοι/λεπτο ομαδας) × λεπτα · συνολο += c·SC (c με LOSO· αναμενεται c < 0).
(2) ΣΒΗΣΙΜΟ: βαρος καθε αποντα αναλογα με τα ΣΥΝΕΧΟΜΕΝΑ ματς της ομαδας που λειπει ηδη (k):
    Δ1 k ≥10 → ½ · Δ2 k ≥5 → ½, k ≥15 → ¼ · Δ3 k ≥10 → 0 (η βαθμολογια της ομαδας τον εχει ηδη «χασει»).
ΚΡΙΤΗΡΙΑ (γραφτηκαν πριν): σφαλμα καλυτερο απο τη βαση ≥4/5 ΚΑΙ μοναδες & CLV οχι χειροτερα ΚΑΙ walk-forward οχι χειροτερο ΚΑΙ placebo < 5%.
Εξοδος: nba_tests/t98_totals_absence_scorers_decay_out.txt"""
import os, sys, io, contextlib, collections
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
    A = g['g']['A']; HM = g['g']['HM']
    # ---- φετινοι ποντοι: (pid, ομαδα, σεζον) → [(ημερα, λεπτα, ποντοι)] · ματς ομαδας ανα ημερα ----
    PG = pd.read_csv(os.path.join(ROOT, 'nba_player_games.csv'), usecols=['PLAYER_ID', 'GAME_ID', 'PTS'])
    PG['PLAYER_ID'] = PG.PLAYER_ID.astype(str); PG['GAME_ID'] = PG.GAME_ID.astype(str).str.zfill(10)
    A2 = A[A.MIN > 0].copy(); A2['PLAYER_ID'] = A2.PLAYER_ID.astype(str); A2['GAME_ID'] = A2.GAME_ID.astype(str).str.zfill(10)
    A2 = A2.merge(PG, on=['PLAYER_ID', 'GAME_ID'], how='left'); A2['dd'] = A2.d.values.astype('datetime64[D]')
    HP = collections.defaultdict(list); TP = collections.defaultdict(lambda: [0.0, 0.0])
    for r in A2.sort_values('dd').itertuples(index=False):
        HP[(r.pid, r.team, int(r.s))].append((r.dd, float(r.MIN), float(r.PTS) if r.PTS == r.PTS else 0.0))
    TDAYS = collections.defaultdict(list)
    for k_ in range(len(G22)):
        for t in (G22.home.values[k_], G22.away.values[k_]): TDAYS[(t, int(g['SEAS_G'][k_]))].append(dD[k_])
    for k_ in TDAYS: TDAYS[k_] = sorted(set(TDAYS[k_]))
    import bisect
    TAG = collections.defaultdict(lambda: collections.defaultdict(lambda: [0.0, 0.0]))
    for (pid, tt, ss), L in HP.items():
        for dd_, mn, pt in L: a_ = TAG[(tt, ss)][dd_]; a_[0] += pt; a_[1] += mn
    TCUM = {}
    for k_, dct in TAG.items():
        ds = sorted(dct); cp = np.cumsum([dct[x][0] for x in ds]); cm = np.cumsum([dct[x][1] for x in ds]); TCUM[k_] = (ds, cp, cm)
    def team_ppm(t, s, d):                                   # ποντοι/λεπτο ομαδας ως τοτε (ολοι οι παικτες)
        c_ = TCUM.get((t, s))
        if not c_: return None
        j = bisect.bisect_left(c_[0], d)
        return float(c_[1][j - 1] / c_[2][j - 1]) if j > 0 and c_[2][j - 1] > 0 else None
    TPPM = {}
    def absents(t, d, s, tau):
        """[(xo, xd, sc, k)] για τους Out ρολου (≥20′) — xo/xd οπως το live, sc = (ποντοι/λεπτο − ομαδας) × λεπτα, k = συνεχομενα ματς απουσιας"""
        res = []
        if (t, s, d) not in TPPM: TPPM[(t, s, d)] = team_ppm(t, s, d)
        tp = TPPM[(t, s, d)]
        for k, stt in status_at(t, d, tau).items():
            if stt != 'Out': continue
            pid = K2P.get((k, t, s))
            if pid is None: continue
            m = mins(pid, t, s, d)
            if m is None or m < 20: continue
            o_, d_ = odval(pid, s - 1); xo = (o_ + 0.5) * m / 48; xd = (d_ + 0.5) * m / 48
            H = [x for x in HP.get((pid, t, s), []) if x[0] < d]
            pm = sum(x[2] for x in H) / max(1e-9, sum(x[1] for x in H)) if H else None
            sc = (pm - tp) * m if (pm is not None and tp is not None) else 0.0
            last = H[-1][0] if H else None
            kk = sum(1 for dd_ in TDAYS.get((t, s), []) if last is not None and last < dd_ < d)
            res.append((xo, xd, sc, kk))
        return res
    X = pd.read_csv(os.path.join(SC, '_t35_totals.csv')); X = X[X.tau == 'ανοιγμα'].dropna(subset=['T', 'oo', 'ou', 'fair', 'cfair', 'tot']).reset_index(drop=True)
    GI = {(str(GC.date.values[k])[:10], GC.home.values[k], GC.away.values[k]): k for k in range(len(GC))}
    GI22 = {(str(dD[k])[:10], G22.home.values[k], G22.away.values[k]): k for k in range(len(G22))}
    X['g'] = [GI.get((str(d)[:10], h, a)) for d, h, a in zip(X.date, X.home, X.away)]; X['i2'] = [GI22.get((str(d)[:10], h, a)) for d, h, a in zip(X.date, X.home, X.away)]
    X = X[X.g.notna() & X.i2.notna()].copy(); X['g'] = X.g.astype(int); X['i2'] = X.i2.astype(int)
    X = X[[abs(GC.hs.values[k] + GC.as_.values[k] - t) < 0.5 for k, t in zip(X.g, X.tot)]].reset_index(drop=True)
    X['eng'] = X.tt + (TT['new'][X.g.values] - TT['old'][X.g.values]) + X.lev.fillna(0)
    FE = []
    for r in X.itertuples(index=False):
        i = r.i2; sw, tip, r21, r23 = SER[i]; rr = [[x[0] + SHIFT] + list(x[1:]) for x in (r23 or [])]
        tau = rr[0][0] if rr else tip; s = int(r.sea); d = dD[i]
        L = absents(r.home, d, s, tau) + absents(r.away, d, s, tau)
        def wsum(fn): return (sum(fn(k) * xo for xo, xd, sc, k in L), sum(fn(k) * xd for xo, xd, sc, k in L))
        rec = dict(LO=sum(x[0] for x in L), LD=sum(x[1] for x in L), SC=sum(x[2] for x in L))
        for nm, fn in (('Δ1', lambda k: 0.5 if k >= 10 else 1.0), ('Δ2', lambda k: 0.25 if k >= 15 else (0.5 if k >= 5 else 1.0)), ('Δ3', lambda k: 0.0 if k >= 10 else 1.0)):
            rec[f'LO_{nm}'], rec[f'LD_{nm}'] = wsum(fn)
        FE.append(rec)
    FE = pd.DataFrame(FE); X = pd.concat([X, FE], axis=1)
    P(f'ελεγχος: LO/LD εδω vs _t35 · μεγ. διαφορα LO {np.abs(X.LO - X.lo).max():.3f} · LD {np.abs(X.LD - X.ld).max():.3f} · ματς {len(X)} · με SC≠0 {int((X.SC != 0).sum())}')
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
    MU = {'LIVE': BASE}
    # (1) σκορερ: c με LOSO
    res0 = Y - BASE; scv = X.SC.values; cS = {}
    for s in SE:
        tr = ys != s; cS[s] = float((scv[tr] @ res0[tr]) / (scv[tr] @ scv[tr] + 1.0))
    MU['ΣΚΟΡΕΡ'] = BASE + np.array([cS[s] for s in ys]) * scv
    for nm in ('Δ1', 'Δ2', 'Δ3'): MU[nm] = X.eng.values - 0.5 * X[f'LO_{nm}'].values + 1.0 * X[f'LD_{nm}'].values
    U = {k: pu(v) for k, v in MU.items()}
    rm = lambda k, m: float(np.sqrt(np.mean((Y[m] - MU[k][m]) ** 2)))
    P(f"ΣΚΟΡΕΡ: c ανα fold (ποντοι συνολου ανα 1 «επιπλεον ποντο» του αποντα πανω απο την ομαδα) " + ' '.join(f'{s % 100}:{cS[s]:+.3f}' for s in SE) + ' (αναμενεται < 0)')
    for k in MU:
        u, c = U[k]; ps = {s: u[ys == s].sum() for s in SE}; od_ = X.mon.isin([10, 11, 12]).values
        line = f"  {k:7s} σφαλμα {rm(k, ys == ys):.3f} (" + ' '.join(f'{s % 100}:{rm(k, ys == s):.3f}' for s in SE) + f') · μοναδες {u.sum():+6.1f} (θετ {sum(v > 0 for v in ps.values())}/5, Οκτ-Δεκ {u[od_].sum():+.1f}) · CLV {np.nanmean(c):+.2f}'
        if k != 'LIVE':
            bet = sum(rm(k, ys == s) < rm('LIVE', ys == s) for s in SE)
            dd = pd.Series((Y - BASE) ** 2 - (Y - MU[k]) ** 2).groupby(day).sum().values; t = dd.mean() / (dd.std(ddof=1) / np.sqrt(len(dd)))
            dw = pd.Series(u - U['LIVE'][0]).groupby(wk).sum().values; bs = np.array([dw[rng.integers(0, len(dw), len(dw))].sum() for _ in range(2000)])
            wf = [0.0, 0.0]
            for s in SE[2:]: wf[0] += u[ys == s].sum(); wf[1] += U['LIVE'][0][ys == s].sum()
            dlt = MU[k] - BASE; real = dw.sum(); rs = []
            for _ in range(150):
                perm = dlt.copy()
                for s in SE:
                    m = np.where(ys == s)[0]; perm[m] = dlt[rng.permutation(m)]
                rs.append(pu(BASE + perm)[0].sum() - U['LIVE'][0].sum())
            pl = 100 * (np.array(rs) >= real).mean()
            ok = bet >= 4 and u.sum() >= U['LIVE'][0].sum() and np.nanmean(c) >= np.nanmean(U['LIVE'][1]) and wf[0] >= wf[1] and pl < 5
            line += f' │ καλυτερο {bet}/5 · t {t:+.2f} · Δμοναδες {real:+.1f} (P {100 * (bs > 0).mean():.0f}%) · WF {wf[0]:+.1f} vs {wf[1]:+.1f} · placebo {pl:.0f}% → {"ΠΕΡΝΑΕΙ" if ok else "✗"}'
        P(line)
    kk = [x for x in X.LO_Δ3.values]
    P(f"\nποσα ματς επηρεαζει το σβησιμο (Δ3: LO αλλαζει): {int((np.abs(X.LO_Δ3 - X.LO) > 1e-9).sum())} απο {len(X)}")
    open(os.path.join(SC, 't98_totals_absence_scorers_decay_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
