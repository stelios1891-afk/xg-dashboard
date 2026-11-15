# -*- coding: utf-8 -*-
"""t77_boost_picks.py — ΠΡΙΝ/ΜΕΤΑ ΤΟ BOOST +k (|χαντικαπ| ≥11, k LOSO ≈ +0.9) ΣΤΑ PICKS ΤΟΥ ΜΟΝΤΕΛΟΥ ΣΥΝΟΛΩΝ (24/10/2026, Στελιος «πως αποδιδει
πριν στα χαντικαπ 10+ και πως μετα με το boost;»). Ιδια βαση/μοντελο με t75 (ανοιγμα Crown, σ 18, edge ≥8%). Περιγραφικο. Εξοδος: t77_boost_picks_out.txt"""
import os, sys
SC = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(SC, 't75_totals_spread_boost.py'), encoding='utf-8').read().split("x = f_lin(O.asp.values); P(f'  (για συγκριση")[0]
src = src.replace("out = []\ndef P(s=''): print(s, flush=True); out.append(str(s))", "out = []\ndef P(s=''): pass")
exec(src)
out2 = []
def Q(s=''): print(s, flush=True); out2.append(str(s))
def pk(col, m):
    R = []
    for _, r in O[m].iterrows():
        po = 1 - ND.cdf((r['T'] - r[col]) / SIG); eo = po * r['oo'] - 1; eu = (1 - po) * r['ou'] - 1
        sd, e = (1, eo) if eo >= eu else (-1, eu)
        if e >= 0.08: R.append((r['sea'], 'OVER' if sd > 0 else 'UNDER', settle(r, sd), r['i']))
    return pd.DataFrame(R, columns=['sea', 'side', 'u', 'i'])
def line(lab, d):
    if not len(d): return f'  {lab:24s} —'
    ps = d.groupby('sea').u.sum()
    return f"  {lab:24s} {100 * d.u.mean():+6.1f}% ({len(d):4d}, {d.u.sum():+6.1f}μ, θετ {int((ps > 0).sum())}/{d.sea.nunique()})"
for thr in (10, 11):
    m = O.asp >= thr
    a, b = pk('mu', m), pk('mu_σκα', m)
    Q(f'\n=== |χαντικαπ| ≥{thr}: {int(m.sum())} ματς · picks μοντελου συνολων (edge ≥8%, ανοιγμα Crown) ===')
    for side in ('ΟΛΑ', 'OVER', 'UNDER'):
        aa = a if side == 'ΟΛΑ' else a[a.side == side]; bb = b if side == 'ΟΛΑ' else b[b.side == side]
        Q(f'  -- {side}'); Q(line('ΠΡΙΝ (χωρις boost)', aa)); Q(line('ΜΕΤΑ (με boost)', bb))
    new = b[~b.i.isin(a.i)]; gone = a[~a.i.isin(b.i)]
    Q(line('ΝΕΑ picks απο το boost', new)); Q(line('picks που ΕΦΥΓΑΝ', gone))
a, b = pk('mu', O.asp < 10), pk('mu_σκα', O.asp < 10)
Q(f'\n=== |χαντικαπ| <10 (το boost δεν αγγιζει): ' + line('', a).strip() + ' · μετα ' + line('', b).strip())
a, b = pk('mu', O.asp == O.asp), pk('mu_σκα', O.asp == O.asp)
Q(f'=== ΟΛΑ ΤΑ ΜΑΤΣ: πριν ' + line('', a).strip() + ' · μετα ' + line('', b).strip())
open(os.path.join(SC, 't77_boost_picks_out.txt'), 'w', encoding='utf-8').write('\n'.join(out2))
