# -*- coding: utf-8 -*-
"""t104_totals_by_period.py — ΣΥΝΟΛΑ NBA ΑΝΑ ΠΕΡΙΟΔΟ: ΠΟΥ ΕΙΝΑΙ ΚΟΝΤΑ ΣΤΟ 0% ΚΑΙ ΤΙ ΔΙΑΦΕΡΕΙ (25/10/2026, Στελιος «τα συνολα την περιοδο
που ειναι κοντα στο 0% μπορουν να αναλυθουν και να συγκριθουν με τις υπολοιπες;»). ΠΕΡΙΓΡΑΦΙΚΟ — δεν αλλαζει τιποτα.
LIVE μηχανη συνολων (νεα μηχανη + Φ3 − 0.5·LO + 1.0·LD) · ανοιγμα Crown · edge ≥8% · 5 σεζον 2021-22 … 2025-26.
Ανα μηνα: picks/ROI/μοναδες/σεζον θετικες/CLV · Over vs Under · μεσο edge · μεροληψια μοντελου (πραγμ.−μοντελο) & αγορας (πραγμ.−ανοιγμα)
· σφαλμα μοντελου vs ανοιγματος vs κλεισιματος · κινηση γραμμης · ογκος απουσιων. Cache: nba_tests/_t104_totals_live.csv"""
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

    def absents(t, d, s, tau):
        res = []
        for k, stt in status_at(t, d, tau).items():
            if stt != 'Out': continue
            pid = K2P.get((k, t, s))
            if pid is None: continue
            m = mins(pid, t, s, d)
            if m is None or m < 20: continue
            o_, d_ = odval(pid, s - 1); res.append(((o_ + 0.5) * m / 48, (d_ + 0.5) * m / 48))
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
        FE.append(dict(LO=sum(x[0] for x in L), LD=sum(x[1] for x in L), NABS=len(L)))
    FE = pd.DataFrame(FE); X = pd.concat([X, FE], axis=1)
    P(f'ελεγχος: LO/LD εδω vs _t35 · μεγ. διαφορα LO {np.abs(X.LO - X.lo).max():.3f} · LD {np.abs(X.LD - X.ld).max():.3f} · ματς {len(X)}')
    X['mu'] = X.eng - 0.5 * X.LO + 1.0 * X.LD
    ND = NormalDist(); SIG = 18.0
    def cover(mu, T):
        if abs(T - round(T)) < 1e-9:
            po = ND.cdf((mu - T - 0.5) / SIG); pu = ND.cdf((T - mu - 0.5) / SIG); return po, 1 - po - pu, pu
        po = ND.cdf((mu - T) / SIG); return po, 0.0, 1 - po
    SD, E, RES, CLV = [], [], [], []
    for r in X.itertuples(index=False):
        po, pp, pq = cover(r.mu, r.T); eo, eu = po * r.oo + pp - 1, pq * r.ou + pp - 1
        sd, e, od = (1, eo, r.oo) if eo >= eu else (-1, eu, r.ou)
        x = (r.tot - r.T) * sd
        SD.append(sd); E.append(e); RES.append((od - 1) if x > 0 else (0.0 if x == 0 else -1.0)); CLV.append(sd * (r.cfair - r.fair))
    X['side'], X['edge'], X['res'], X['clv'] = SD, E, RES, CLV
    X['pick'] = X.edge >= .08
    X['day'] = pd.to_datetime(X.date)
    X[['date', 'sea', 'mon', 'home', 'away', 'T', 'oo', 'ou', 'fair', 'cfair', 'tot', 'eng', 'LO', 'LD', 'NABS', 'mu', 'side', 'edge', 'res', 'clv', 'pick']].to_csv(os.path.join(SC, '_t104_totals_live.csv'), index=False)
    PER = (('Οκτ', [10]), ('Νοε', [11]), ('Δεκ', [12]), ('Ιαν', [1]), ('Φεβ', [2]), ('Μαρ', [3]), ('Απρ', [4]))
    def row(nm, m):
        d = X[m]; k = d[d.pick]
        ps = k.groupby('sea').res.sum(); ov = k[k.side == 1]; un = k[k.side == -1]
        f = lambda z: f'{100 * z.res.mean():+5.1f}% ({len(z):3d})' if len(z) else '   —      '
        P(f"  {nm:8s} picks {len(k):4d} ({100 * len(k) / max(len(d), 1):3.0f}% των {len(d):4d} ματς) · ROI {100 * k.res.mean():+5.1f}% · μοναδες {k.res.sum():+6.1f} · θετ {int((ps > 0).sum())}/{k.sea.nunique()}"
          f" · CLV {k.clv.mean():+.2f}π · Over {f(ov)} · Under {f(un)} · μεσο edge {100 * k.edge.mean():4.1f}%")
    P('\n=== Α · ΑΠΟΤΕΛΕΣΜΑ PICKS ΑΝΑ ΜΗΝΑ (edge ≥8%, ανοιγμα Crown, 5 σεζον) ===')
    for nm, ms in PER: row(nm, X.mon.isin(ms))
    row('ΟΛΑ', X.mon == X.mon)
    P('\n=== Β · ΠΟΙΟΣ ΚΑΝΕΙ ΛΑΘΟΣ ΑΝΑ ΜΗΝΑ (ΟΛΑ τα ματς, οχι μονο picks) — ποντοι συνολου ===')
    P('  μηνας    ματς · πραγμ.−μοντελο (μεροληψια) · πραγμ.−ανοιγμα · πραγμ.−κλεισιμο · σφαλμα μοντελο / ανοιγμα / κλεισιμο · κινηση ανοιγμα→κλεισιμο · μοντελο−ανοιγμα (|μεσο|) · αποντες/ματς')
    for nm, ms in PER + (('ΟΛΑ', list(range(1, 13))),):
        d = X[X.mon.isin(ms)]; rm = lambda v: float(np.sqrt(np.mean(v ** 2)))
        P(f"  {nm:8s} {len(d):4d} · {np.mean(d.tot - d.mu):+5.2f} · {np.mean(d.tot - d.fair):+5.2f} · {np.mean(d.tot - d.cfair):+5.2f}"
          f" · {rm(d.tot - d.mu):5.2f} / {rm(d.tot - d.fair):5.2f} / {rm(d.tot - d.cfair):5.2f} · {np.mean(d.cfair - d.fair):+5.2f} · {np.mean(np.abs(d.mu - d.fair)):4.2f} · {d.NABS.mean():.2f}")
    P('\n=== Γ · ΑΝΑ ΣΕΖΟΝ: ROI picks ανα περιοδο (μοναδες σε παρενθεση) ===')
    GR = (('Οκτ-Δεκ', [10, 11, 12]), ('Ιαν-Φεβ', [1, 2]), ('Μαρ-Απρ', [3, 4]))
    for s in sorted(X.sea.unique()):
        d = X[(X.sea == s) & X.pick]
        P(f"  {int(s) - 1}-{int(s) % 100:02d}: " + ' · '.join(f"{nm} {100 * d[d.mon.isin(ms)].res.mean():+5.1f}% ({d[d.mon.isin(ms)].res.sum():+5.1f}μ, {int(d.mon.isin(ms).sum())})" for nm, ms in GR))
    P('\n=== Δ · ΑΝΑ ΖΩΝΗ EDGE ανα περιοδο (ROI · picks) ===')
    for lo, hi in ((.08, .12), (.12, .20), (.20, 9)):
        P(f"  edge {100 * lo:.0f}-{'' if hi > 1 else f'{100 * hi:.0f}'}%: " + ' · '.join(
            f"{nm} {100 * X[X.pick & X.mon.isin(ms) & (X.edge >= lo) & (X.edge < hi)].res.mean():+5.1f}% ({int((X.pick & X.mon.isin(ms) & (X.edge >= lo) & (X.edge < hi)).sum())})" for nm, ms in GR))
    open(os.path.join(SC, 't104_totals_by_period_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
