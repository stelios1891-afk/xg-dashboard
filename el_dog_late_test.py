# -*- coding: utf-8 -*-
"""el_dog_late_test.py — ΕΥΡΩΛΙΓΚΑ: ΑΟΥΤΣΑΪΝΤΕΡ ΠΟΥ ΠΡΩΤΟΒΓΑΙΝΟΥΝ ΑΡΓΑ = ΚΑΤΑΓΡΑΦΗ; (17/10/2026, Στελιος «αν το backtest εδειξε οτι τα
αουτσαιντερ αργα πρεπει να κοβονται, γιατι τα εχουμε;»). Περιγραφικο ευρημα (el_fav_dog_timing): dogs 2-6ω −6.8% (52, 2/5).
Ιδια προσομοιωση με el_fav_dog_timing (live μηχανη h_new, Crown, E2021-25, πρωτο alert ≥8%, τελευταιο 2ωρο ηδη καταγραφη στο live).
ΚΑΝΟΝΑΣ (ΠΡΟ-ΔΗΛΩΜΕΝΟΣ, ΠΡΙΝ την εκτελεση): ΑΟΥΤΣΑΪΝΤΕΡ που πρωτοεμφανιζεται < Χ ωρες πριν (οχι στο ανοιγμα) = ΚΑΤΑΓΡΑΦΗ. ΚΥΡΙΟ Χ = 6.
ΠΕΡΝΑ αν ΟΛΑ (ιδια με el_over_late_test): (1) κομμενα ROI < 0 ΚΑΙ χειροτερα απο οσα μενουν, στην τιμη του alert ΚΑΙ στο κλεισιμο ·
(2) χειροτερα σε ≥3/5 σεζον (σεζον με ≥3 κομμενα) · (3) ιδια φορα με Χ = 4 και Χ = 8 · (4) μοναδες αουτσαιντερ με τον κανονα ≥ χωρις.
Εξοδος: el_dog_late_test_out.txt"""
import sys, io, contextlib
import pandas as pd
class _B(io.StringIO):
    def reconfigure(self, **k): pass
ns = {'__name__': 'x'}
src = open('el_fav_dog_timing.py', encoding='utf-8').read(); src = src[:src.index('X = pd.DataFrame(rows)') + len('X = pd.DataFrame(rows)')]
with contextlib.redirect_stdout(_B()): exec(src, ns)
sys.stdout.reconfigure(encoding='utf-8')
X = ns['X']; dg = X[X.role == 'ΑΟΥΤΣΑΪΝΤΕΡ']; SE = sorted(dg.sea.unique())
out = []
def P(s=''): print(s); out.append(str(s))
def cell(d, col='pa'):
    if not len(d): return '—'
    ps = d.groupby('sea')[col].mean()
    return f'{100*d[col].mean():+6.1f}% ({len(d)}, {d[col].sum():+6.1f}μ, {int((ps > 0).sum())}/{d.sea.nunique()})'
P(f'ΑΟΥΤΣΑΪΝΤΕΡ (κανονικα σημερα): alert {cell(dg)} · κλεισιμο {cell(dg, "pc")}')
for lo, hi in ((12, 99), (6, 12), (4, 6), (2, 4)):
    d = dg[(dg.hrs >= lo) & (dg.hrs < hi)]
    P(f'  {lo:2d}-{hi if hi < 99 else "+"}ω: {cell(d)} | κλεισ. {cell(d, "pc")}')
res = {}
for Xh in (4, 6, 8):
    cut = dg[(dg.hrs < Xh) & ~dg.at_open]; keep = dg.drop(cut.index)
    ys = [s for s in SE if (cut.sea == s).sum() >= 3]
    worse = sum(1 for s in ys if cut[cut.sea == s].pa.mean() < keep[keep.sea == s].pa.mean())
    res[Xh] = dict(ca=cut.pa.mean(), cc=cut.pc.mean(), ka=keep.pa.mean(), kc=keep.pc.mean(), w=worse, ny=len(ys), u0=dg.pa.sum(), u1=keep.pa.sum())
    P(f'  Χ={Xh}: κοβει {cell(cut)} · κλεισ. {cell(cut, "pc")} | μενουν {cell(keep)} · κλεισ. {cell(keep, "pc")} | χειροτερα {worse}/{len(ys)} σεζον · μοναδες {dg.pa.sum():+.1f} → {keep.pa.sum():+.1f}')
r = res[6]
c1 = r['ca'] < 0 and r['cc'] < 0 and r['ca'] < r['ka'] and r['cc'] < r['kc']; c2 = r['w'] >= 3
c3 = all(res[x]['ca'] < res[x]['ka'] for x in (4, 8)); c4 = r['u1'] >= r['u0']
P(f'ΚΡΙΣΗ (Χ=6): (1) {"✓" if c1 else "✗"} · (2) {r["w"]}/{r["ny"]} {"✓" if c2 else "✗"} · (3) {"✓" if c3 else "✗"} · (4) {"✓" if c4 else "✗"} → {"ΠΕΡΝΑ" if c1 and c2 and c3 and c4 else "ΔΕΝ ΠΕΡΝΑ"}')
open('el_dog_late_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
