# -*- coding: utf-8 -*-
"""uel_homefav_clv_live.py — 4/11/2026 (Στελιος: «μιλαω μονο για τα εντος φαβορι που παιζουμε, αυτα μου δειχνεις;»). ΕΛΕΓΧΟΣ ΠΙΣΤΟΤΗΤΑΣ του uel_homefav_clv:
ΜΟΝΟ τα picks του κανονα, με τη ΜΗΧΑΝΗ ΠΟΥ ΠΑΙΖΕΙ ΣΗΜΕΡΑ: μιξη 80% xG + φετινα ευρωπαικα (Μ8, βαρος 0.5, LOSO συντελεστες — harness uel_homefav_inseason),
και αποτελεσμα στο 90′ (data_Europe_* μετα το euro_regulation 19/10· χωρις παραταση/πεναλτι). Γηπεδουχος δινει ≥0.5, 1.70-2.10, FotMob+FotMob, σωστα τεταρτα,
edge ≥4%, πρωτη φορα στις 36/24/18/12ω. Crown & SBOBET (μεσος). CLV ως το κλεισιμο: γραμμη σε γκολ · τιμη στην ιδια γραμμη · δικαιη κινηση (+ = προς το φαβορι)."""
import sys, io, json, glob, contextlib
import numpy as np, pandas as pd
src = open('uel_homefav_inseason.py', encoding='utf-8').read()
pre = src[:src.index('rows = []\nfor i, mid in enumerate(MIDS):')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass')
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
io.StringIO = _Q
g = {'__name__': 'ul'}
with contextlib.redirect_stdout(_Q()):
    exec(pre, g)
sys.stdout = sys.__stdout__; sys.stdout.reconfigure(encoding='utf-8')
import picks
MIDS, SEA, GD, U, D8, INS, snap, sdist, cover_q, edge = (g[k] for k in ('MIDS', 'SEA', 'GD', 'U', 'D8', 'INS', 'snap', 'sdist', 'cover_q', 'edge'))
R90 = {}
for f in glob.glob('data_Europe_*.json'):
    for k, m in json.load(open(f, encoding='utf-8')).items():
        if m.get('hs') is not None and m.get('as') is not None:
            R90[str(k)] = m['hs'] - m['as']
_c = {}
def sup(line_home, oh, oa, T=2.9):
    key = (line_home, oh, oa)
    if key in _c: return _c[key]
    q = (1 / oh) / (1 / oh + 1 / oa); lo, hi = -5.0, 5.0
    parts = [line_home] if (line_home * 4) % 2 == 0 else [line_home - .25, line_home + .25]
    for _ in range(30):
        s = (lo + hi) / 2; d = picks.gd_dist(max((T + s) / 2, .05), max((T - s) / 2, .05))
        c = [picks.p_cover(d, 1, L) for L in parts]; pe = sum(a for a, _ in c) / max(sum(1 - b for _, b in c), 1e-9)
        lo, hi = (s, hi) if pe < q else (lo, s)
    _c[key] = (lo + hi) / 2
    return _c[key]
rows = []; n_diff = 0
for i, mid in enumerate(MIDS):
    if not U[i] or not D8['FM'][i]: continue
    D = sdist(INS[0][i], INS[1][i])
    gd0 = float(GD[i]); gd = float(R90.get(str(mid), gd0))
    for bk in ('Crown', 'SBOBET'):
        c = snap(mid, bk, 0)
        if not c: continue
        Lc, ohc, oac = c
        for h in (36, 24, 18, 12):
            s = snap(mid, bk, h)
            if not s: continue
            L, oh, oa = s
            ln, o, oc, lnc = L, oh, ohc, Lc                      # γηπεδουχος
            if not (1.70 <= o <= 2.10) or ln > -0.5: continue
            pw, pp = cover_q(D, 1, ln); e = edge(pw, pp, o)
            if e < .04: continue
            rows.append(dict(i=i, mid=str(mid), bk=bk, h=h, sea=SEA[i], e=e, ln=ln, od=o, lnc=lnc, oc=oc, gd=gd, gd0=gd0,
                             pnl=picks.settle(gd, 1, ln, o), pnl0=picks.settle(gd0, 1, ln, o), pnl_c=picks.settle(gd, 1, lnc, oc), dline=ln - lnc,
                             dprice=(o / oc - 1) if abs(ln - lnc) < .01 else np.nan, mv=sup(Lc, ohc, oac) - sup(L, oh, oa)))
A = pd.DataFrame(rows)
R = A.sort_values('h', ascending=False).groupby(['i', 'bk']).head(1)
def show(z, lab):
    n = len(z) / max(z.bk.nunique(), 1); p = z.dprice.dropna()
    print(f"{lab:30s} picks {n:5.1f} │ γραμμη υπερ {100 * (z.dline > .01).mean():3.0f}% ιδια {100 * (z.dline.abs() <= .01).mean():3.0f}% κοντρα {100 * (z.dline < -.01).mean():3.0f}% · μεσο {z.dline.mean():+.3f} │ "
          f"ιδια γραμμη τιμη {100 * p.mean():+5.1f}% │ δικαιη κινηση {z.mv.mean():+.3f} ±{z.mv.std(ddof=1) / np.sqrt(max(n, 1)):.3f} γκολ (υπερ {100 * (z.mv > 0).mean():3.0f}%) │ ROI {100 * z.pnl.mean():+6.1f}% · {z.pnl.sum() / z.bk.nunique():+5.1f}μ · στο κλεισιμο {100 * z.pnl_c.mean():+6.1f}%")
print('UEL ΦΑΒΟΡΙ ΕΝΤΟΣ = ΜΟΝΟ τα picks του κανονα · μηχανη σημερα (80% xG + Μ8) · αποτελεσμα 90′ · μεσος Crown/SBOBET')
show(R, 'Ο ΚΑΝΟΝΑΣ')
for bk in ('Crown', 'SBOBET'): show(R[R.bk == bk], '  ' + bk)
for s in sorted(R.sea.unique()): show(R[R.sea == s], '  σεζον ' + s)
for lab, lo, hi in (('edge 4-10%', .04, .10), ('edge 10-20%', .10, .20), ('edge ≥20%', .20, 9)): show(R[(R.e >= lo) & (R.e < hi)], '  ' + lab)
d = R[R.gd != R.gd0]
print(f"ελεγχος 90′: picks με διαφορετικο αποτελεσμα vs παλιο αρχειο {len(d)} (μοναδικα ματς {d.mid.nunique()}) · ROI με παλιο {100 * R.pnl0.mean():+.1f}% → με 90′ {100 * R.pnl.mean():+.1f}%")
miss = [m for m in R.mid.unique() if m not in {str(k) for k in R90}]
print(f"ματς χωρις data_Europe (μενει το παλιο αποτελεσμα): {len(miss)} απο {R.mid.nunique()}")
