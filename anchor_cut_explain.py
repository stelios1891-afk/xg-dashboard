# -*- coding: utf-8 -*-
"""anchor_cut_explain.py — ΤΙ ΚΟΒΕΙ / ΤΙ ΚΡΑΤΑ Η ΑΓΚΥΡΩΣΗ (21/10/2026, Στελιος «πως ακριβως αλλαζουν οι προβλεψεις; τι κοβει;»).
BCL: Bet365 3ω πριν, αγκυρωση 70% (σ 12.1, ≥6%) vs live (σ 12, ≥8%) · EC: Crown 1ω πριν, αγκυρωση 50% (σ 12.3, ≥10%) vs live (σ 11.5, ≥8%).
Ομαδες: ΜΕΝΟΥΝ (pick και στα δυο) · ΚΟΒΟΝΤΑΙ (μονο live) · ΝΕΑ (μονο αγκυρωση) — ROI + μεγεθος διαφωνιας + φαβορι/αουτσαιντερ."""
import sys, collections
MODE = sys.argv[1].upper()
src = open('anchor_timing_grid.py', encoding='utf-8').read().split("WS = (1.0, .7")[0].replace("MODE = (sys.argv[1] if len(sys.argv) > 1 else 'BCL').upper()", f"MODE = '{MODE}'")
exec(src)
bk, cp, W, TH = (('Bet365', 3, .7, .06) if MODE == 'BCL' else ('Crown', 1, .5, .10))
H = BOOKS[bk][0]; LTH = .08
def pk(i, w, sg, th):
    x = atb(H, i, cp)
    if x is None or not np.isfinite(MOD[i]): return None
    _, L, mk, o1, o2 = x; m_ = mk + w * (MOD[i] - mk)
    pw, pp, pl = cover(m_, L, sg); e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
    s, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
    return dict(side=s, L=L, od=od, e=e, gap=MOD[i] - mk, mk=mk, m=m_) if e >= th else None
G = collections.defaultdict(list)
for i in H:
    a = pk(i, 1.0, SIG_LIVE, LTH); b = pk(i, W, SIG_MIX, TH)
    if a and b: grp = 'ΜΕΝΟΥΝ' if a['side'] == b['side'] else 'ΑΛΛΑΖΕΙ ΠΛΕΥΡΑ'; p = b
    elif a: grp, p = 'ΚΟΒΟΝΤΑΙ', a
    elif b: grp, p = 'ΝΕΑ', b
    else: continue
    own = p['L'] if p['side'] == 1 else -p['L']
    G[grp].append(dict(res=settle(i, p['side'], p['L'], p['od']), gap=abs(p['gap']), fav=own < 0, s=str(SEAS[i]), e_live=(a or {}).get('e'), e_anc=(b or {}).get('e')))
def c(L):
    if not L: return '—'
    a = np.array([x['res'] for x in L]); return f'{100 * a.mean():+5.1f}% ({len(a)}, {a.sum():+.1f}μ)'
print(f'{MODE} · {bk} {cp}ω πριν · αγκυρωση {int(W * 100)}% ≥{int(TH * 100)}% vs live ≥8%')
for g in ('ΜΕΝΟΥΝ', 'ΚΟΒΟΝΤΑΙ', 'ΝΕΑ', 'ΑΛΛΑΖΕΙ ΠΛΕΥΡΑ'):
    L = G[g]
    if not L: continue
    print(f'  {g:14s} {c(L)} · μεση διαφωνια μοντελου−αγορας {np.mean([x["gap"] for x in L]):.1f} π. · φαβορι {c([x for x in L if x["fav"]])} · αουτσ. {c([x for x in L if not x["fav"]])}')
    print('       ανα διαφωνια: ' + ' · '.join(f'{lo}-{hi} π.: {c([x for x in L if lo <= x["gap"] < hi])}' for lo, hi in ((0, 3), (3, 5), (5, 8), (8, 99))))
