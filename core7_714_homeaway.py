# -*- coding: utf-8 -*-
"""core7_714_homeaway.py — ΚΟΝΤΑ ΦΑΒΟΡΙ 7-14 (κανονας R): ΕΝΤΟΣ vs ΕΚΤΟΣ (10/10/2026, Στελιος: «τρεξε τη συγκριση με το τυφλο,
βρες που χανει το μοντελο στα εκτος, και γιατι διαφερει τοσο Pinnacle με Crown»). ΠΕΡΙΓΡΑΦΙΚΟ — δεν αλλαζει τιποτα live.
Ιδια δεδομενα/κανονας με core7_714_shortfav_test (2022-23…2025-26, αγων 7-14, γραμμη −0.5/−0.75, 1.70-2.10, edge ≥0%).
 1. R vs ΤΥΦΛΟ (ολα τα κοντα φαβορι ιδιας τιμης) χωριστα εντος / εκτος, ανα βιβλιο, κλεισιμο & ανοιγμα.
 2. ΕΚΤΟΣ: υπεροχη (απο τη μερια του φαβορι) μοντελο vs αγορα vs πραγματικο, συγκριση με εντος· και σε ΟΛΑ τα ματς 7-14 (εδρα μοντελου vs αγορας).
 3. PINNACLE vs CROWN: ιδια ματς στα δυο βιβλια — ποσα picks κοινα / μονο στο ενα, ROI τους, διαφορα τιμων & γραμμων.
Εξοδος: core7_714_homeaway_out.txt"""
import sys, io, contextlib
import numpy as np, pandas as pd
src = open('core7_714_shortfav_test.py', encoding='utf-8').read().split("B = pd.DataFrame(rows)")[0]
src = src.replace("pick=ev_ok(dist, side, ud, o) >= 0.0, pnl=picks.settle(r.gd, side, ud, o)))",
                  "pick=ev_ok(dist, side, ud, o) >= 0.0, pnl=picks.settle(r.gd, side, ud, o), mid=r.mid, gd=r.gd * side, o=o, L=ud,\n"
                  "                         msup=side * sup(L, oh, oa, r.xh + r.xa), mod=side * (r.xh - r.xa), edge=ev_ok(dist, side, ud, o)))")
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
g = {'__name__': 'ha'}
with contextlib.redirect_stdout(_Q()):
    exec(src, g)
sys.stdout.reconfigure(encoding='utf-8')
B = pd.DataFrame(g['rows']); W = g['W']; sup = g['sup']; SEAS = g['SEAS']
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def fm(d):
    if len(d) < 3: return f'n{len(d):4d}      —      '
    ps = d.groupby('season').pnl.mean()
    return f'n{len(d):4d} {100*d.pnl.mean():+6.1f}% {d.pnl.sum():+6.1f}u {int((ps > 0).sum())}/4'
P('=== 1. R vs ΤΥΦΛΟ, ΕΝΤΟΣ / ΕΚΤΟΣ (τυφλο = ολα τα κοντα φαβορι −0.5/−0.75 στο 1.70-2.10, ιδιο βιβλιο) ===')
for when in ('κλεισιμο', 'ανοιγμα'):
    for bk in ('Pinnacle', 'Crown', 'Bet365'):
        x = B[(B.book == bk) & (B.when == when)]
        if not len(x): continue
        for lab, m in (('ΕΝΤΟΣ', x.home), ('ΕΚΤΟΣ', ~x.home)):
            z = x[m]; r, b = z[z.pick], z
            P(f'  {when:8s} {bk:8s} {lab}: R {fm(r)} · τυφλο {fm(b)} · R−τυφλο {100*(r.pnl.mean()-b.pnl.mean()):+.1f} μ. · '
              f'οσα ΚΟΒΕΙ το μοντελο {fm(z[~z.pick])}')
P(''); P('=== 2. ΠΟΥ ΧΑΝΕΙ ΤΟ ΜΟΝΤΕΛΟ (κλεισιμο, picks R· υπεροχη γκολ απο τη μερια του φαβορι) ===')
P('  μοντελο = προβλεπομενη υπεροχη · αγορα = υπεροχη που «λεει» η γραμμη/τιμη · πραγμ = μεσο τελικο ±γκολ')
for bk in ('Pinnacle', 'Crown'):
    x = B[(B.book == bk) & (B.when == 'κλεισιμο') & B.pick]
    for lab, m in (('ΕΝΤΟΣ', x.home), ('ΕΚΤΟΣ', ~x.home)):
        z = x[m]
        P(f'  {bk:8s} {lab} n{len(z):3d}: μοντελο {z["mod"].mean():+.2f} · αγορα {z.msup.mean():+.2f} · πραγμ {z.gd.mean():+.2f} · '
          f'μοντελο−αγορα {z["mod"].mean()-z.msup.mean():+.2f} · πραγμ−αγορα {z.gd.mean()-z.msup.mean():+.2f} · μεσο edge {100*z.edge.mean():.1f}% · '
          f'νικη φαβορι {np.mean(z.gd > 0):.0%} ισοπ. {np.mean(z.gd == 0):.0%} ηττα {np.mean(z.gd < 0):.0%}')
    z = x[~x.home]
    for ln in (-0.5, -0.75):
        q = z[z.L == ln]
        if len(q): P(f'      ΕΚΤΟΣ {ln}: n{len(q)} · {100*q.pnl.mean():+.1f}% · μοντ−αγορα {q["mod"].mean()-q.msup.mean():+.2f} · πραγμ−αγορα {q.gd.mean()-q.msup.mean():+.2f}')
    P('      ΕΚΤΟΣ ανα σεζον: ' + ' · '.join(f'{s}: {100*z[z.season == s].pnl.mean():+.0f}% (n{(z.season == s).sum()})' for s in SEAS))
    P('      ΕΚΤΟΣ ανα λιγκα: ' + ' · '.join(f'{k} {100*v.pnl.mean():+.0f}% (n{len(v)})' for k, v in z.groupby('league')))
# εδρα σε ολα τα ματς 7-14 (Pinnacle κλεισιμο): μοντελο vs αγορα vs πραγμ
w = W[W.L.notna()].copy()
w['msup'] = [sup(L, oh, oa, xh + xa) for L, oh, oa, xh, xa in zip(w.L, w.ah, w.aa, w.xh, w.xa)]
P(''); P(f'  ΟΛΑ τα ματς 7-14 (n{len(w)}), υπεροχη γηπεδουχου: μοντελο {(w.xh - w.xa).mean():+.3f} · αγορα (Pinnacle) {w.msup.mean():+.3f} · πραγμ {w.gd.mean():+.3f}  '
  f'→ το μοντελο δινει στον γηπεδουχο {(w.xh - w.xa).mean() - w.msup.mean():+.3f} γκολ σε σχεση με την αγορα')
P('     ανα σεζον (μοντελο − αγορα / πραγμ − αγορα): ' + ' · '.join(f'{s}: {(q.xh - q.xa).mean() - q.msup.mean():+.2f} / {q.gd.mean() - q.msup.mean():+.2f}' for s, q in w.groupby('season')))
P(''); P('=== 3. PINNACLE vs CROWN (κλεισιμο) ===')
pc = B[(B.when == 'κλεισιμο') & B.book.isin(['Pinnacle', 'Crown'])]
both = set(pc[pc.book == 'Pinnacle'].mid) & set(pc[pc.book == 'Crown'].mid)
P(f'  κοντα φαβορι στο 1.70-2.10: Pinnacle {pc[pc.book == "Pinnacle"].mid.nunique()} ματς · Crown {pc[pc.book == "Crown"].mid.nunique()} · ΚΟΙΝΑ {len(both)}')
pk = pc[pc.pick]
sp, sc = set(pk[pk.book == 'Pinnacle'].mid), set(pk[pk.book == 'Crown'].mid)
for lab, ids in (('pick ΚΑΙ στα δυο', sp & sc), ('pick ΜΟΝΟ Pinnacle', sp - sc), ('pick ΜΟΝΟ Crown', sc - sp)):
    a = pk[(pk.book == 'Pinnacle') & pk.mid.isin(ids)]; c = pk[(pk.book == 'Crown') & pk.mid.isin(ids)]
    P(f'  {lab:20s} {len(ids):3d} ματς · Pinnacle {fm(a)} · Crown {fm(c)}')
    if lab.startswith('pick ΜΟΝΟ'):
        other = 'Crown' if 'Pinnacle' in lab else 'Pinnacle'
        o_ = pc[(pc.book == other) & pc.mid.isin(ids)]
        P(f'      στο {other} τα ιδια ματς: υπαρχουν ως κοντο φαβορι {o_.mid.nunique()} (εκει χωρις pick: edge μ.ο. {100*o_.edge.mean() if len(o_) else 0:+.1f}%) · '
          f'λειπουν {len(ids) - o_.mid.nunique()} (αλλη γραμμη/τιμη εκτος 1.70-2.10)')
cm = pk[pk.mid.isin(sp & sc)]
pv = cm.pivot_table(index='mid', columns='book', values=['o', 'L', 'pnl'], aggfunc='first').dropna()
if len(pv):
    P(f'  ΚΟΙΝΑ picks: τιμη Crown − Pinnacle μ.ο. {(pv["o"]["Crown"] - pv["o"]["Pinnacle"]).mean():+.3f} · ιδια γραμμη {np.mean(pv["L"]["Crown"] == pv["L"]["Pinnacle"]):.0%} · '
      f'ROI Pinnacle {100*pv["pnl"]["Pinnacle"].mean():+.1f}% vs Crown {100*pv["pnl"]["Crown"].mean():+.1f}%')
for bk in ('Pinnacle', 'Crown'):
    z = pk[pk.book == bk]
    P(f'  {bk:8s} picks: εντος {z.home.mean():.0%} · μεση τιμη {z.o.mean():.3f} · −0.75 {np.mean(z.L == -0.75):.0%} · μεσο edge {100*z.edge.mean():.1f}% · '
      f'πραγμ−αγορα {z.gd.mean() - z.msup.mean():+.2f}')
open('core7_714_homeaway_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
