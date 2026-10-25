# -*- coding: utf-8 -*-
"""t99_totals_refs_17.py — ΣΥΝΟΛΑ NBA: ΔΙΑΙΤΗΤΕΣ ΠΑΝΩ ΣΤΗ ΝΕΑ ΜΗΧΑΝΗ, ΣΤΗΝ ΕΙΣΟΔΟ ΤΩΝ 17:00 (25/10/2026, Στελιος «τρεξτα ολα»).
Οι διαιτητες ανακοινωνονται ~16:00 ωρα Ελλαδας (9πμ ET) → ΔΕΝ ειναι γνωστοι στο ανοιγμα· χρησιμευουν μονο αν παιζουμε αργοτερα (π.χ. 17:00, οριο ~3.000).
ΔΕΙΚΤΗΣ ΤΡΙΑΔΑΣ = t42 (μεσο πραγμ − αγορα ανοιγματος στα 60 προηγουμενα ματς καθε διαιτητη, ≥20, μαζεμα 40· μεσος της τριαδας).
ΣΤΙΣ 17:00: Β = picks του ανοιγματος παιγμενα 17:00 · Β+Φ = ιδια, ΕΚΤΟΣ αν ο δεικτης τριαδας ειναι κοντρα ≥ θ (θ .5 / 1.0) ·
  Γ = αποφαση στις 17:00 (μ) · Γ+Δ = αποφαση στις 17:00 με μ + c·δεικτης (c LOSO).
ΚΡΙΤΗΡΙΑ: Β+Φ ή Γ+Δ ΠΕΡΝΑ αν μοναδες > Β(17:00) ΚΑΙ CLV οχι χειροτερο ΚΑΙ οχι χειροτερο σε ≥4/5 σεζον.
Εξοδος: nba_tests/t99_totals_refs_17_out.txt
ΠΑΛΙΑ ΠΕΡΙΓΡΑΦΗ t97: — ΣΥΝΟΛΑ NBA: ΑΝ ΠΑΙΖΑΜΕ ΣΕ ΣΥΓΚΕΚΡΙΜΕΝΗ ΩΡΑ ΕΛΛΑΔΑΣ ΑΝΤΙ ΓΙΑ ΤΟ ΑΝΟΙΓΜΑ (25/10/2026, Στελιος «δεν μπορεις να το
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
    import json as _js, collections as _co
    REF = {}
    for s_ in (2022, 2023, 2024, 2025, 2026):
        for ln in open(os.path.join(ROOT, f'nba_refs/refs_{s_}.jsonl'), encoding='utf-8'):
            q = _js.loads(ln); REF[(q['date'], q['home'])] = q['refs']
    def refs_of(d, h):
        for k in (0, -1, 1):
            x = REF.get(((pd.Timestamp(d) + pd.Timedelta(days=k)).strftime('%Y-%m-%d'), h))
            if x: return x
        return None
    X = X.sort_values('date').reset_index(drop=True); X['res'] = X.tot - X.fair; hist = _co.defaultdict(list); idx = []
    for r in X.itertuples(index=False):
        rf = refs_of(r.date, r.home); vals = []
        if rf:
            for nm in rf[:3]:
                h = hist[nm][-60:]
                if len(h) >= 20: vals.append(np.mean(h) * len(h) / (len(h) + 40))
        idx.append(np.mean(vals) if len(vals) >= 2 else 0.0)
        if rf:
            for nm in rf[:3]: hist[nm].append(r.res)
    X['crew'] = idx
    ATH = ZoneInfo('Europe/Athens'); SIG = 18.0; ND = NormalDist()
    def cover(mu, T):
        if abs(T - round(T)) < 1e-9:
            po = ND.cdf((mu - T - 0.5) / SIG); pu = ND.cdf((T - mu - 0.5) / SIG); return po, 1 - po - pu, pu
        po = ND.cdf((mu - T) / SIG); return po, 0.0, 1 - po
    def at(rows, tau):
        pre = [x for x in rows if x[0] <= tau]; return pre[-1] if pre else None
    REC = []
    for r in X.itertuples(index=False):
        i = GI22.get((str(r.date)[:10], r.home, r.away))
        if i is None or i not in SER: continue
        sw, tip, r21, r23 = SER[i]
        rows = [[x[0] + SHIFT] + list(x[1:]) for x in (r23 or [])]; rows = [x for x in rows if x[0] <= tip]
        if not rows or abs(float(rows[0][1]) - r.T) > 0.01: continue
        gd = pd.Timestamp(r.date).date(); tau = dt.datetime(gd.year, gd.month, gd.day, 17, 0, tzinfo=ATH).timestamp()
        if tau >= tip: continue
        x0 = rows[0]; x = at(rows, tau) if tau >= rows[0][0] else rows[0]
        po0, pp0, pu0 = cover(r.mu, float(x0[1])); e0o, e0u = po0 * (1 + x0[2]) + pp0 - 1, pu0 * (1 + x0[3]) + pp0 - 1
        REC.append(dict(sea=r.sea, mon=r.mon, mu=r.mu, crew=r.crew, tot=r.tot, sd0=1 if e0o >= e0u else -1, e0=max(e0o, e0u),
                        T=float(x[1]), oo=1 + x[2], ou=1 + x[3], fair=mk_t(x), close=mk_t(rows[-1]), res17=r.tot - mk_t(x)))
    D = pd.DataFrame(REC); ys = D.sea.values; SE = sorted(set(ys))
    def settle(r, sd):
        od = r.oo if sd == 1 else r.ou; xx = (r.tot - r.T) * sd; return (od - 1) if xx > 0 else (0.0 if xx == 0 else -1.0)
    def run(mode, thr=None, cvec=None):
        R = []
        for j, r in enumerate(D.itertuples(index=False)):
            if mode == 'Β':
                if r.e0 < .08: continue
                sd = r.sd0
                if thr is not None and sd * r.crew <= -thr: continue
            else:
                mu = r.mu + (cvec[j] * r.crew if cvec is not None else 0.0)
                po, pp, pu = cover(mu, r.T); eo, eu = po * r.oo + pp - 1, pu * r.ou + pp - 1
                if max(eo, eu) < .08: continue
                sd = 1 if eo >= eu else -1
            R.append((r.sea, settle(r, sd), sd * (r.close - r.fair)))
        return pd.DataFrame(R, columns=['sea', 'res', 'clv'])
    def cell(d):
        ps = d.groupby('sea').res.sum()
        return f'{100 * d.res.mean():+5.1f}% ({len(d):4d}, {d.res.sum():+6.1f}μ, θετ {int((ps > 0).sum())}/{d.sea.nunique()}) CLV {d.clv.mean():+.2f}π'
    P(f'ματς με γραμμη 17:00: {len(D)} · με δεικτη τριαδας ≠0: {int((D.crew != 0).sum())} · κλιση (πραγμ − αγορα 17:00) πανω στον δεικτη {np.polyfit(D.crew[D.crew != 0], D.res17[D.crew != 0], 1)[0]:+.2f}')
    b = run('Β'); P(f'  Β   (picks ανοιγματος, τιμη 17:00)        {cell(b)}')
    for th in (0.5, 1.0):
        f_ = run('Β', thr=th); bs = b.groupby('sea').res.sum(); fs = f_.groupby('sea').res.sum()
        P(f'  Β+Φ θ={th} (κοβει αν η τριαδα ειναι κοντρα) {cell(f_)} · σεζον οχι χειροτερη {sum(fs.get(s, 0) >= bs.get(s, 0) for s in SE)}/5')
    gm = run('Γ'); P(f'  Γ   (αποφαση 17:00, μοντελο)             {cell(gm)}')
    cv = np.zeros(len(D))
    for s in SE:
        tr = (ys != s) & (D.crew.values != 0); xx = D.crew.values[tr]; yy = (D.tot - D.mu).values[tr]; cv[ys == s] = (xx @ yy) / (xx @ xx + 1.0)
    gd_ = run('Γ', cvec=cv); P(f'  Γ+Δ (αποφαση 17:00, μ + c·δεικτης, c LOSO ~{cv.mean():+.2f}) {cell(gd_)}')
    open(os.path.join(SC, 't99_totals_refs_17_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
