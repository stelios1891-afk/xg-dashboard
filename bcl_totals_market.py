# -*- coding: utf-8 -*-
"""bcl_totals_market.py — αξιολογηση προβλεψεων ΣΥΝΟΛΟΥ BCL απεναντι στην αγορα (Nowgoal t23) — κοινο κομματι του bcl_totals_test (6/10/2026).
evaluate(ids, ys, TOT, TT, gno, FIN, P): Κ2, τυφλο under, ROI μοντελο ≥8% / μιξη 50/50 ≥6% (ανοιγμα/κλεισιμο, Crown/Bet365, over/under, ματς 1-3 / 4+)."""
import os, json, math, collections
import numpy as np, pandas as pd
from statistics import NormalDist
EV = [2021, 2022, 2023, 2024, 2025]
def evaluate(ids, ys, TOT, TT, gno, FIN, P):
    NN = NormalDist(); Phi = NN.cdf
    FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
    sc = {e['id']: (int(e['hs']), int(e['as_'])) for k, L in FG.items() if k.startswith('BCL_') for e in L if e.get('hs') not in (None, '')}
    idx = collections.defaultdict(list)
    for i, mid in enumerate(ids):
        if mid in sc: idx[sc[mid]].append(i)
    ROWS = collections.defaultdict(dict)
    for ln in open('nowgoal_bcl/odds.jsonl', encoding='utf-8'):
        r = json.loads(ln)
        if r['t'] == 23 and r['cid'] in (3, 8): ROWS[r['ngid']][r['cid']] = sorted([x for x in r['rows'] if x[4] == 2 and x[1] is not None and x[2] and x[3]], key=lambda x: x[0])
    MK = {}
    for f in sorted(os.listdir('nowgoal_bcl')):
        if not f.startswith('sched_'): continue
        for g in json.load(open('nowgoal_bcl/' + f, encoding='utf-8')):
            if g.get('hs') is None or g['ngid'] not in ROWS: continue
            tip = pd.Timestamp(g['bj']) - pd.Timedelta(hours=8); hit = None
            for key in ((g['hs'], g['as_']), (g['as_'], g['hs'])):
                for i in idx.get(key, []):
                    if abs((pd.Timestamp(TT[i]) - tip).total_seconds()) <= 26 * 3600: hit = i; break
                if hit is not None: break
            if hit is None: continue
            rec = {c: dict(o=(float(R[0][1]), 1 + R[0][2], 1 + R[0][3]), c=(float(R[-1][1]), 1 + R[-1][2], 1 + R[-1][3])) for c, R in ROWS[g['ngid']].items() if R}
            if rec: MK[hit] = rec
    ii = [i for i in MK if ys[i] in EV and np.isfinite(FIN[i]) and 3 in MK[i]]
    SIG = float(np.std([TOT[i] - MK[i][3]['c'][0] for i in ii]))
    def mexp(T, oo, ou):
        po = (1 / oo) / (1 / oo + 1 / ou); return T + SIG * NN.inv_cdf(min(max(po, 1e-4), 1 - 1e-4))
    mo = {i: mexp(*MK[i][3]['o']) for i in ii}; mc = {i: mexp(*MK[i][3]['c']) for i in ii}
    a = np.array([TOT[i] for i in ii]); m = np.array([FIN[i] for i in ii]); yy = np.array([ys[i] for i in ii])
    P(f'  ματς {len(ii)} · σ (πραγμ − κλεισιμο) {SIG:.1f} · λαθος μοντελο {np.sqrt(np.mean((a - m) ** 2)):.2f} · ανοιγμα {np.sqrt(np.mean((a - np.array([mo[i] for i in ii])) ** 2)):.2f} · '
      f'κλεισιμο {np.sqrt(np.mean((a - np.array([mc[i] for i in ii])) ** 2)):.2f} · μεση διαφορα μοντ. − κλεισ. {np.mean(m - np.array([mc[i] for i in ii])):+.2f}')
    def k2(sel, ref):
        x = np.array([FIN[i] - ref[i] for i in sel]); z = np.array([TOT[i] - ref[i] for i in sel])
        c = np.polyfit(x, z, 1); r_ = z - np.polyval(c, x); se = math.sqrt(np.sum(r_ ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2)); return c[0], c[0] / se
    for ref, lab in ((mc, 'κλεισιμο'), (mo, 'ανοιγμα')):
        b, t = k2(ii, ref); per = [k2([i for i in ii if ys[i] == Y], ref)[0] for Y in EV]
        ok = b >= .15 and t >= 2 and sum(q > 0 for q in per) >= 4
        P(f'  Κ2 vs {lab}: b {b:+.2f} (t {t:+.1f}) · ανα σεζον ' + ' '.join(f'{q:+.2f}' for q in per) + (('  ✓' if ok else '  ✗') if lab == 'κλεισιμο' else ''))
    for lab, f in (('ματς 1-3', lambda i: gno[i] <= 3), ('ματς 4+', lambda i: gno[i] > 3)):
        s = [i for i in ii if f(i)]; b, t = k2(s, mc)
        P(f'    {lab}: n {len(s)} · Κ2 vs κλεισιμο b {b:+.2f} (t {t:+.1f}) · υπολοιπο αγορας (πραγμ − κλεισ.) {np.mean([TOT[i] - mc[i] for i in s]):+.2f}')
    P('  ΤΥΦΛΑ (χωρις μοντελο — μονο η ταση της αγορας):')
    for bk, bn in ((3, 'Crown'), (8, 'Bet365')):
        for wh, wn in (('o', 'ανοιγμα'), ('c', 'κλεισιμο')):
            R = [(((MK[i][bk][wh][2] - 1) if TOT[i] < MK[i][bk][wh][0] else (0 if TOT[i] == MK[i][bk][wh][0] else -1)), int(ys[i])) for i in ii if bk in MK[i]]
            u = np.array([r[0] for r in R]); pos_ = sum(1 for Y in EV if np.mean([r[0] for r in R if r[1] == Y]) > 0)
            P(f'    τυφλο UNDER {bn} {wn}: {u.mean() * 100:+.1f}% ({len(u)}, {pos_}/5) · πραγμ − γραμμη {np.mean([TOT[i] - MK[i][bk][wh][0] for i in ii if bk in MK[i]]):+.2f}')
    def cov(mu, T):
        if abs(T - round(T)) < 1e-9:
            po = Phi((mu - T - .5) / SIG); pu = Phi((T - mu - .5) / SIG); return po, 1 - po - pu, pu
        po = Phi((mu - T) / SIG); return po, 0.0, 1 - po
    def bets(sel, book, wh, wm, thr):
        R = []
        for i in sel:
            if book not in MK[i]: continue
            T, oo, ou = MK[i][book][wh]; mk_ = mexp(T, oo, ou); mu = mk_ + wm * (FIN[i] - mk_)
            po, pq, pu = cov(mu, T); eo, eu = po * oo + pq - 1, pu * ou + pq - 1
            if max(eo, eu) < thr: continue
            ov = eo >= eu; q = (TOT[i] - T) * (1 if ov else -1); od = oo if ov else ou
            R.append(((od - 1) if q > 0 else (0 if q == 0 else -1), int(ys[i]), 'over' if ov else 'under'))
        return R
    def cell(R):
        if not R: return '—'
        u = np.array([q[0] for q in R]); pos_ = sum(1 for Y in EV if [q for q in R if q[1] == Y] and np.mean([q[0] for q in R if q[1] == Y]) > 0)
        return f'{u.mean() * 100:+.1f}% ({len(R)}, {u.sum():+.1f}u, {pos_}/5)'
    for rl, wm, thr in (('μοντελο ≥8%', 1.0, .08), ('μιξη 50/50 ≥6%', .5, .06)):
        P(f'  [{rl}]')
        for book, bn in ((3, 'Crown'), (8, 'Bet365')):
            for wh, wn in (('o', 'ανοιγμα'), ('c', 'κλεισιμο')):
                R = bets(ii, book, wh, wm, thr)
                P(f'    {bn} {wn:9s}: ολα {cell(R)} · over {cell([q for q in R if q[2] == "over"])} · under {cell([q for q in R if q[2] == "under"])}')
        for lab, f in (('ματς 1-3', lambda i: gno[i] <= 3), ('ματς 4+', lambda i: gno[i] > 3)):
            s = [i for i in ii if f(i)]
            P(f'    {lab} (ανοιγμα): Crown {cell(bets(s, 3, "o", wm, thr))} · Bet365 {cell(bets(s, 8, "o", wm, thr))}')
