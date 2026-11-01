# -*- coding: utf-8 -*-
"""t97_totals_clock_entry.py — ΣΥΝΟΛΑ NBA: ΑΝ ΠΑΙΖΑΜΕ ΣΕ ΣΥΓΚΕΚΡΙΜΕΝΗ ΩΡΑ ΕΛΛΑΔΑΣ ΑΝΤΙ ΓΙΑ ΤΟ ΑΝΟΙΓΜΑ (25/10/2026, Στελιος «δεν μπορεις να το
μετρησεις ιστορικα, υπολογιζοντας οτι θα παιζαμε π.χ. 15:00 ωρα Ελλαδας;» — αφορμη: τα ορια Pinnacle στα συνολα ανεβαινουν 1.125 → 3.000 ~15:00-17:00).
ΙΣΤΟΡΙΚΟ: γραμμες Crown με ωρα (5 σεζον), ΝΕΑ μηχανη συνολων (run_all_split, αμυνα .25, HL 45, K 6) + Φ3 + απουσιες (οπως _t35, στο ανοιγμα).
ΣΤΙΓΜΕΣ: ανοιγμα · 15:00 · 17:00 · 21:00 ωρα Ελλαδας της ημερας του ματς (ημερα ΗΠΑ· τα ματς ξεκινουν μετα τα μεσανυχτα Ελλαδας).
Β «ΙΔΙΟ PICK, ΑΡΓΟΤΕΡΗ ΤΙΜΗ»: picks που βγηκαν στο ανοιγμα (edge ≥8%), παιγμενα στη γραμμη/αποδοση της στιγμης → ROI, CLV, ποσο CLV εφυγε.
Γ «ΑΠΟΦΑΣΗ ΣΤΗ ΣΤΙΓΜΗ»: pick μονο αν το edge ειναι ≥8% στην τιμη της στιγμης (ιδιο μοντελο).
Εξοδος: nba_tests/t97_totals_clock_entry_out.txt"""
import os, sys, io, contextlib, datetime as dt
from zoneinfo import ZoneInfo
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
    src = open(os.path.join(SC, 't22_report_timing.py'), encoding='utf-8').read().split("TAUS = (('ανοιγμα'")[0].replace("if os.environ.get('T22_AUDIT'):", "if False:")
    g = {'__file__': os.path.join(SC, 't22_report_timing.py'), '__name__': 'x'}
    with contextlib.redirect_stdout(_B()): exec(src, g)
    sys.stdout.reconfigure(encoding='utf-8')
    SER, SHIFT, mk_t, dD, G22 = g['SER'], g['SHIFT'], g['nt']['mk_t'], g['dD'], g['G']
    GI22 = {(str(dD[k])[:10], G22.home.values[k], G22.away.values[k]): k for k in range(len(G22))}   # ΔΙΟΡΘΩΣΗ: το i του _t35 ΔΕΝ ταιριαζει με το G του t22 (βλ. t56/t75)
    X = pd.read_csv(os.path.join(SC, '_t35_totals.csv')); X = X[X.tau == 'ανοιγμα'].dropna(subset=['T', 'oo', 'ou', 'fair', 'cfair', 'tot']).reset_index(drop=True)
    GI = {(str(GC.date.values[k])[:10], GC.home.values[k], GC.away.values[k]): k for k in range(len(GC))}
    X['g'] = [GI.get((str(d)[:10], h, a)) for d, h, a in zip(X.date, X.home, X.away)]; X = X[X.g.notna()].copy(); X['g'] = X.g.astype(int)
    X = X[[abs(GC.hs.values[k] + GC.as_.values[k] - t) < 0.5 for k, t in zip(X.g, X.tot)]].reset_index(drop=True)
    X['mu'] = X.tt + (TT['new'][X.g.values] - TT['old'][X.g.values]) + X.lev.fillna(0) - 0.5 * X.lo.fillna(0) + 1.0 * X.ld.fillna(0)
    ATH = ZoneInfo('Europe/Athens'); SIG = 18.0; ND = NormalDist()
    def cover(mu, T):
        if abs(T - round(T)) < 1e-9:
            po = ND.cdf((mu - T - 0.5) / SIG); pu = ND.cdf((T - mu - 0.5) / SIG); return po, 1 - po - pu, pu
        po = ND.cdf((mu - T) / SIG); return po, 0.0, 1 - po
    def at(rows, tau):
        pre = [x for x in rows if x[0] <= tau]; return pre[-1] if pre else None
    MOM = (('ανοιγμα', None), ('15:00', 15), ('17:00', 17), ('21:00', 21))
    R = []
    for r in X.itertuples(index=False):
        i = GI22.get((str(r.date)[:10], r.home, r.away))
        if i is None or i not in SER: continue
        sw, tip, r21, r23 = SER[i]
        rows = [[x[0] + SHIFT] + list(x[1:]) for x in (r23 or [])]; rows = [x for x in rows if x[0] <= tip]
        if not rows: continue
        if abs(float(rows[0][1]) - r.T) > 0.01: continue          # ελεγχος: η πρωτη γραμμη = το ανοιγμα του _t35
        close = mk_t(rows[-1]); gd = pd.Timestamp(r.date).date()
        po0, pp0, pu0 = cover(r.mu, float(rows[0][1])); e0o, e0u = po0 * (1 + rows[0][2]) + pp0 - 1, pu0 * (1 + rows[0][3]) + pp0 - 1
        sd0 = 1 if e0o >= e0u else -1; e0 = max(e0o, e0u)
        for lab, hh in MOM:
            if hh is None: tau = rows[0][0]
            else:
                tau = dt.datetime(gd.year, gd.month, gd.day, hh, 0, tzinfo=ATH).timestamp()
                if tau >= tip: continue
            x = at(rows, tau) if tau >= rows[0][0] else rows[0]
            T, oo, ou, fair = float(x[1]), 1 + x[2], 1 + x[3], mk_t(x)
            po, pp, pu = cover(r.mu, T); eo, eu = po * oo + pp - 1, pu * ou + pp - 1
            for kind, sd, e in (('Β', sd0, e0), ('Γ', 1 if eo >= eu else -1, max(eo, eu))):
                if e < .08: continue
                od = oo if sd == 1 else ou; xx = (r.tot - T) * sd
                R.append(dict(sea=r.sea, mon=r.mon, mom=lab, kind=kind, sd=sd, res=(od - 1) if xx > 0 else (0.0 if xx == 0 else -1.0),
                              clv=sd * (close - fair), hrs=(tip - tau) / 3600, T=T))
    D = pd.DataFrame(R)
    def cell(d):
        if not len(d): return '—'
        ps = d.groupby('sea').res.sum()
        return f'{100 * d.res.mean():+5.1f}% ({len(d):4d}, {d.res.sum():+6.1f}μ, θετ {int((ps > 0).sum())}/{d.sea.nunique()}) CLV {d.clv.mean():+.2f}π · {d.hrs.mean():4.1f}ω πριν'
    P('ΣΥΝΟΛΑ NBA · νεα μηχανη · Crown 5 σεζον · edge ≥8%')
    for kind, nm in (('Β', 'Β · ΙΔΙΑ picks του ανοιγματος, παιγμενα αργοτερα'), ('Γ', 'Γ · ΑΠΟΦΑΣΗ στη στιγμη (edge ≥8% στην τιμη τοτε)')):
        P(f'\n=== {nm} ===')
        for lab, _ in MOM:
            d = D[(D.kind == kind) & (D.mom == lab)]
            P(f'  {lab:8s} ολη: {cell(d)} │ Οκτ-Δεκ {100 * d[d.mon.isin([10, 11, 12])].res.mean():+.1f}% ({int(d.mon.isin([10, 11, 12]).sum())})')
    b0 = D[(D.kind == 'Β') & (D.mom == 'ανοιγμα')]
    P(f"\nCLV που «εφυγε» (Β, ιδια picks): " + ' · '.join(f"{lab} {b0.clv.mean() - D[(D.kind == 'Β') & (D.mom == lab)].clv.mean():+.2f}π" for lab, _ in MOM[1:]))
    open(os.path.join(SC, 't97_totals_clock_entry_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
