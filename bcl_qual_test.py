# -*- coding: utf-8 -*-
"""bcl_qual_test.py — BCL: ΠΩΣ ΜΕΤΡΑΝΕ ΤΑ ΠΡΟΚΡΙΜΑΤΙΚΑ (7/10/2026, Στελιος «οκ» — φετος τα προκριματικα 183 π. μεσο συνολο ανεβασαν το επιπεδο
συνολων BCL στο 172.6 → ολα τα picks συνολων over).
ΣΥΝΟΛΑ (live μηχανη: περσι .35, λ 20, φιλικα ×1, τυχη .1):
  Α 'same' = προκριματικα ιδιο επιπεδο με την κανονικη (σημερα) · Β 'own' = δικο τους επιπεδο (μετρανε μονο για τις ταση των ομαδων) · Γ 'half' = ιδιο, μισο βαρος
ΧΑΝΤΙΚΑΠ (live: 0.25·μονο BCL + 0.75·κοινη κλιμακα): προκριματικα με εδρα (σημερα) vs ΟΥΔΕΤΕΡΟ γηπεδο (μινι-τουρνουα σε μια πολη).
ΑΞΙΟΛΟΓΗΣΗ: ματς ΚΑΝΟΝΙΚΗΣ περιοδου 2021-26 · «αρχη» = 1-6 ματς (μεγαλυτερος αριθμος ματς των 2 ομαδων) · ROI picks ≥8% στο ανοιγμα (Crown, Bet365).
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση): εκδοχη ΜΠΑΙΝΕΙ αν το λαθος στην «αρχη» πεφτει σε ≥4/5 σεζον σε σχεση με τη σημερινη ΚΑΙ η υπολοιπη
κανονικη δεν χειροτερευει > 0.01 π. Εξοδος: bcl_qual_out.txt"""
import os
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import sys, json, pickle, collections
import numpy as np, pandas as pd
from statistics import NormalDist
from multiprocessing import Pool

def _job(a):
    import bcl_common as B
    rows = B.load(pre=True)
    if a[0] == 't': return a, B.run_tot(rows, .35, 20.0, kf=1.0, wo=1.0, tmap=B.luck_totals(.1), qmode=a[1])
    return a, B.run(rows, 1.3, 1.5, 9999.0, 25.0, kf=0.5, wo=1.5, qual_neutral=a[1])

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    out = []
    def P(s=''): print(s, flush=True); out.append(str(s))
    jobs = [('t', 'same'), ('t', 'own'), ('t', 'half'), ('h', False), ('h', True)]
    with Pool(len(jobs)) as pool: R = dict(pool.map(_job, jobs))
    D = pickle.load(open('bcl_engine_preds_live.pkl', 'rb')); ids, ys = D['id'], D['y']
    pos = {i: k for k, i in enumerate(ids)}
    def arr(pr):
        v = np.full(len(ids), np.nan)
        for mid, (p, y) in pr.items():
            if mid in pos: v[pos[mid]] = p
        return v
    M2 = {k[1]: arr(v) for k, v in R.items() if k[0] == 'h'}
    M1 = (D['FIN'] - .75 * M2[False]) / .25
    H = {k: .25 * M1 + .75 * v for k, v in M2.items()}
    T = {k[1]: arr(v) for k, v in R.items() if k[0] == 't'}
    FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
    E = {e['id']: e for k, L in FG.items() if k.startswith('BCL_') for e in L if e.get('hs') not in (None, '')}
    q = np.array([bool(i in E and 'Qualif' in (E[i].get('stage') or '')) for i in ids])
    act = np.array([(int(E[i]['hs']) - int(E[i]['as_'])) if i in E else np.nan for i in ids], float)
    tot = np.array([(int(E[i]['hs']) + int(E[i]['as_'])) if i in E else np.nan for i in ids], float)
    gn = np.zeros(len(ids), int); cnt = collections.Counter()
    for k in sorted(range(len(ids)), key=lambda k: E[ids[k]]['ts'] if ids[k] in E else 0):
        i = ids[k]
        if i not in E or q[k]: continue
        a_, b_ = (ys[k], E[i]['hid']), (ys[k], E[i]['aid']); cnt[a_] += 1; cnt[b_] += 1; gn[k] = max(cnt[a_], cnt[b_])
    EV = [2021, 2022, 2023, 2024, 2025]; ev = np.isin(ys, EV) & ~q
    early = ev & (gn >= 1) & (gn <= 6); late = ev & (gn > 6)
    def rm(v, tgt, m): m = m & np.isfinite(v) & np.isfinite(tgt); return float(np.sqrt(np.mean((tgt - v)[m] ** 2)))
    def bias(v, tgt, m): m = m & np.isfinite(v) & np.isfinite(tgt); return float(np.mean((tgt - v)[m]))
    P('μεσο συνολο προκριματικων vs κανονικης: ' + ' · '.join(f'{Y}: {np.nanmean(tot[(ys == Y) & q]):.1f} / {np.nanmean(tot[(ys == Y) & ~q]):.1f}' for Y in (2020, 2021, 2022, 2023, 2024, 2025)))
    # αγορα
    ND = NormalDist(); Phi = ND.cdf
    MKH = pickle.load(open('bcl_mk.pkl', 'rb'))
    ROWS = collections.defaultdict(dict)
    for ln in open('nowgoal_bcl/odds.jsonl', encoding='utf-8'):
        r = json.loads(ln)
        if r['t'] == 23 and r['cid'] in (3, 8): ROWS[r['ngid']][r['cid']] = sorted([x for x in r['rows'] if x[4] == 2 and x[1] is not None and x[2] and x[3]], key=lambda x: x[0])
    idx = collections.defaultdict(list)
    for k, i in enumerate(ids):
        if i in E: idx[(int(E[i]['hs']), int(E[i]['as_']))].append(k)
    MKT = {}
    for f in sorted(os.listdir('nowgoal_bcl')):
        if not f.startswith('sched_'): continue
        for g in json.load(open('nowgoal_bcl/' + f, encoding='utf-8')):
            if g.get('hs') is None or g['ngid'] not in ROWS: continue
            tip = (pd.Timestamp(g['bj']) - pd.Timedelta(hours=8)).timestamp(); hit = None
            for key in ((g['hs'], g['as_']), (g['as_'], g['hs'])):
                for k in idx.get(key, []):
                    if abs(E[ids[k]]['ts'] - tip) <= 26 * 3600: hit = k; break
                if hit is not None: break
            if hit is not None: MKT[ids[hit]] = {cid: (float(R_[0][1]), 1 + R_[0][2], 1 + R_[0][3]) for cid, R_ in ROWS[g['ngid']].items() if R_}
    def cover(m_, L, s):
        if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
        pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
    def roi(kind, v, msk, book):
        U = collections.defaultdict(list); nov = 0
        for k, i in enumerate(ids):
            if not msk[k] or not np.isfinite(v[k]): continue
            if kind == 'h':
                mk = (MKH.get(i) or {}).get(book)
                if not mk: continue
                L, _, o1, o2 = mk['o']; pw, pp, pl = cover(v[k], L, 12.0); x = act[k] + L
            else:
                mk = (MKT.get(i) or {}).get(book)
                if not mk: continue
                L, o1, o2 = mk; pw, pp, pl = cover(v[k], -L, 17.3); x = tot[k] - L
            e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1; s_, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
            if e < .08: continue
            nov += s_ == 1; qq = x * s_; U[int(ys[k])].append((od - 1) if qq > 0 else (0 if qq == 0 else -1))
        u = [z for v_ in U.values() for z in v_]
        extra = f', over {nov}' if kind == 't' else ''
        return f'{np.mean(u)*100:+.1f}% ({len(u)}{extra}, {sum(u):+.1f}u, θετ {sum(1 for Y in EV if U.get(Y) and np.mean(U[Y]) > 0)}/{sum(1 for Y in EV if U.get(Y))})' if u else '—'
    for kind, V, tgt, base, nm in (('t', T, tot, 'same', 'ΣΥΝΟΛΑ'), ('h', H, act, False, 'ΧΑΝΤΙΚΑΠ')):
        P(''); P(f'################ {nm} ################')
        for k, v in V.items():
            P(f'  {str(k):6s} αρχη (1-6): λαθος {rm(v, tgt, early):.3f} · μεροληψια (πραγμ − μοντ) {bias(v, tgt, early):+.2f} · υπολοιπη: {rm(v, tgt, late):.3f}' +
              (f' · προκριματικα: {rm(v, tgt, np.isin(ys, EV) & q):.3f}' if kind == 'h' else ''))
            for book, bn in ((3, 'Crown'), (8, 'Bet365')):
                P(f'         ROI ≥8% {bn}: αρχη {roi(kind, v, early, book)} · ολη η κανονικη {roi(kind, v, ev, book)}')
        for k, v in V.items():
            if k == base: continue
            d = [rm(v, tgt, early & (ys == Y)) - rm(V[base], tgt, early & (ys == Y)) for Y in EV]
            dl = rm(v, tgt, late) - rm(V[base], tgt, late)
            ok = sum(x < 0 for x in d) >= 4 and dl <= .01
            P(f'  ΚΡΙΣΗ {k} vs σημερα: αρχη ανα σεζον ' + ' '.join(f'{x:+.2f}' for x in d) + f' → {sum(x < 0 for x in d)}/5 · υπολοιπη {dl:+.3f}' + ('  <- ΜΠΑΙΝΕΙ' if ok else '  <- ✗'))
    open('bcl_qual_out.txt', 'w', encoding='utf-8').write('\n'.join(out))

if __name__ == '__main__':
    main()
