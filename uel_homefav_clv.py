# -*- coding: utf-8 -*-
"""uel_homefav_clv.py — 4/11/2026 (Στελιος: «τι clv εχουν δειξει ιστορικα τα φαβορι εντος του europa;»). ΑΚΡΙΒΩΣ τα picks του live κανονα (rule uel_home_fav,
ιδια κατασκευη με uel_full_review §4): UEL 2223-2526, FotMob+FotMob, μιξη 80% xG, γηπεδουχος δινει ≥0.5, 1.70-2.10, edge ≥4% σωστα τεταρτα, πρωτη φορα στις
36/24/18/12ω πριν. Crown & SBOBET. CLV ως το κλεισιμο: (α) γραμμη σε γκολ (+ = η γραμμη του φαβορι μεγαλωσε, υπερ μας) · (β) τιμη μας/κλεισιμο −1 οταν η γραμμη ιδια
(απλη μεθοδος Pick History) · (γ) δικαιη υπεροχη σε γκολ (γραμμη+τιμες χωρις περιθωριο, συνολο 2.9), + = προς το φαβορι · (δ) ROI στην τιμη μας vs στο κλεισιμο.
ΣΥΓΚΡΙΣΗ: τα ΑΛΛΑ φαβορι εντος του Europa (ιδια ζωνη τιμων, ιδιες ωρες, χωρις edge ≥4%) και τα φαβορι εκτος με edge ≥4%."""
import sys, io, contextlib
import numpy as np, pandas as pd
src = open('uel_full_review.py', encoding='utf-8').read()
pre = src[:src.index('# ======================= 4. ΦΑΒΟΡΙ ΕΝΤΟΣ')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass')
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
io.StringIO = _Q                      # τα εσωτερικα exec κανουν κι αυτα redirect_stdout(io.StringIO())
g = {'__name__': 'uh'}
with contextlib.redirect_stdout(_Q()):
    exec(pre, g)
sys.stdout = sys.__stdout__; sys.stdout.reconfigure(encoding='utf-8')
import pickle, picks
UEL, MIDS, SEA, GD, sdist, cover_q, edge, snap_ah = (g[k] for k in ('UEL', 'MIDS', 'SEA', 'GD', 'sdist', 'cover_q', 'edge', 'snap_ah'))
D8 = pickle.load(open('euro_blend_dump_0.8.pkl', 'rb'))
assert list(D8['MIDS']) == list(MIDS)
_c = {}
def sup(line_home, oh, oa, T=2.9):
    """Δικαιη υπεροχη γηπεδουχου απο γραμμη (γηπ., αρνητικη = δινει) + τιμες χωρις περιθωριο."""
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
rows = []
for i in UEL:
    if not D8['FM'][i]: continue
    D = sdist(D8['LH'][i], D8['LA'][i])
    for bk in ('Crown', 'SBOBET'):
        c = snap_ah(MIDS[i], bk, 0)
        if not c: continue
        Lc, ohc, oac = c
        for h in (36, 24, 18, 12):
            s = snap_ah(MIDS[i], bk, h)
            if not s: continue
            L, oh, oa = s
            for side, ln, o, oc in ((1, L, oh, ohc), (-1, -L, oa, oac)):
                if not (1.70 <= o <= 2.10) or ln > -0.5: continue
                pw, pp = cover_q(D, side, ln); e = edge(pw, pp, o)
                lnc = Lc if side == 1 else -Lc
                rows.append(dict(i=i, bk=bk, h=h, home=side == 1, side=side, sea=SEA[i], ln=ln, od=o, e=e, lnc=lnc, oc=oc, pnl=picks.settle(GD[i], side, ln, o),
                                 pnl_c=picks.settle(GD[i], side, lnc, oc), dline=ln - lnc,
                                 dprice=(o / oc - 1) if abs(ln - lnc) < .01 else np.nan,
                                 mv=side * (sup(Lc, ohc, oac) - sup(L, oh, oa))))
A = pd.DataFrame(rows)
def first(x):
    return x.sort_values('h', ascending=False).groupby(['i', 'bk', 'side']).head(1)
RULE = first(A[A.home & (A.e >= .04)])
OTHER = first(A[A.home & ~A.i.isin(RULE.i)])
AWAY = first(A[~A.home & (A.e >= .04)])
def show(z, lab):
    n = len(z) / 2
    p = z.dprice.dropna()
    print(f"{lab:46s} picks {n:5.1f} │ γραμμη: υπερ {100 * (z.dline > .01).mean():3.0f}% ιδια {100 * (z.dline.abs() <= .01).mean():3.0f}% κοντρα {100 * (z.dline < -.01).mean():3.0f}% · μεσο {z.dline.mean():+.3f} γκολ │ "
          f"ιδια γραμμη τιμη {100 * p.mean():+5.1f}% ({len(p) / 2:.0f}) │ δικαιη κινηση {z.mv.mean():+.3f} ±{z.mv.std(ddof=1) / np.sqrt(len(z) / 2):.3f} γκολ (υπερ {100 * (z.mv > 0).mean():3.0f}%) │ "
          f"ROI τιμη μας {100 * z.pnl.mean():+6.1f}% · κλεισιμο {100 * z.pnl_c.mean():+6.1f}%")
print('UEL ΦΑΒΟΡΙ ΕΝΤΟΣ — CLV ως το κλεισιμο (μεσος Crown/SBOBET, picks ανα βιβλιο). + = η αγορα ηρθε προς το φαβορι')
show(RULE, 'Ο ΚΑΝΟΝΑΣ (edge ≥4%, 12-36ω)')
for bk in ('Crown', 'SBOBET'): show(RULE[RULE.bk == bk], f'   {bk}')
for s in sorted(RULE.sea.unique()): show(RULE[RULE.sea == s], f'   σεζον {s}')
for h in (36, 24, 18, 12): show(RULE[RULE.h == h], f'   πρωτη φορα {h}ω πριν')
for lab, lo, hi in (('edge 4-10%', .04, .10), ('edge 10-20%', .10, .20), ('edge ≥20%', .20, 9)): show(RULE[(RULE.e >= lo) & (RULE.e < hi)], '   ' + lab)
for lab, m in (('γραμμη κινηθηκε ΥΠΕΡ', RULE.dline > .01), ('ιδια γραμμη', RULE.dline.abs() <= .01), ('γραμμη κινηθηκε ΚΟΝΤΡΑ', RULE.dline < -.01)): show(RULE[m], '   ' + lab)
print('--- συγκριση')
show(OTHER, 'αλλα φαβορι εντος (χωρις edge ≥4%)')
show(AWAY, 'φαβορι εκτος με edge ≥4%')
