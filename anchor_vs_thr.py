# -*- coding: utf-8 -*-
"""anchor_vs_thr.py — ΑΓΚΥΡΩΣΗ ή ΑΠΛΑ ΨΗΛΟΤΕΡΟ ΚΑΤΩΦΛΙ; (21/10/2026, Στελιος). Live (w 1, σ live) με κατωφλι 8…30% vs αγκυρωση, ιδια στιγμη/βιβλιο,
και ποσα ιδια picks διαλεγουν (επικαλυψη)."""
import sys, collections
MODE = sys.argv[1].upper()
src = open('anchor_timing_grid.py', encoding='utf-8').read().split("WS = (1.0, .7")[0].replace("MODE = (sys.argv[1] if len(sys.argv) > 1 else 'BCL').upper()", f"MODE = '{MODE}'")
exec(src)
bk, cp, W, TH = (('Bet365', 3, .7, .06) if MODE == 'BCL' else ('Crown', 1, .5, .10))
H = BOOKS[bk][0]
def picks(w, sg, th):
    out = {}
    for i in H:
        x = atb(H, i, cp)
        if x is None or not np.isfinite(MOD[i]): continue
        _, L, mk, o1, o2 = x; m_ = mk + w * (MOD[i] - mk); pw, pp, pl = cover(m_, L, sg); e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
        s, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
        if e >= th: out[i] = (settle(i, s, L, od), str(SEAS[i]), s)
    return out
def c(d):
    a = np.array([v[0] for v in d.values()]); ps = collections.defaultdict(float)
    for v in d.values(): ps[v[1]] += v[0]
    return f'{100 * a.mean():+5.1f}% ({len(a):3d}, {a.sum():+6.1f}μ, {sum(x > 0 for x in ps.values())}/{len(ps)})'
A = picks(W, SIG_MIX, TH)
print(f'{MODE} · {bk} {cp}ω πριν · ΑΓΚΥΡΩΣΗ {int(W * 100)}% ≥{int(TH * 100)}%: {c(A)}')
for th in (.08, .10, .12, .15, .18, .20, .25, .30):
    Lv = picks(1.0, SIG_LIVE, th); both = set(Lv) & set(A)
    print(f'  live ≥{int(th * 100):2d}%: {c(Lv)} · κοινα με αγκυρωση {len(both)} ({100 * len(both) / max(len(A), 1):.0f}% της αγκυρωσης)')
