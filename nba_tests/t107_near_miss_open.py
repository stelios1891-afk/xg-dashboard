# -*- coding: utf-8 -*-
"""t107_near_miss_open.py — «ΣΧΕΔΟΝ PICKS» ΤΟΥ ΑΝΟΙΓΜΑΤΟΣ ΣΤΑ ΧΑΝΤΙΚΑΠ (26/10/2026, Στελιος για Μπακς +4.5: «δεν μιλαμε για πικ που
προεκυψε αργα, στην ουσια προεκυψε στο ανοιγμα» — 7.92% στην 1η γραμμη, 8.88% τωρα, ιδια γραμμη +4.5, κινηση μονο τιμης).
Πλαισιο t101/t22 (live αντιγραφο + επισημη αναφορα της στιγμης, Crown 5 σεζον, κατωφλι 8% · Ιαν-Φεβ 12%).
(α) ΑΡΓΑ picks που ΚΟΒΕΙ ο κανονας (Β1+Β2 του t101), ανα ζωνη «ποσο κοντα ηταν το τωρινο μοντελο στην 1η γραμμη» (er = edge τωρινου
    μοντελου στην ΠΡΩΤΗ γραμμη, οπως ο live κανονας): κατωφλι−1% … κατωφλι (= Μπακς) · −2…−1% · −4…−2% · πιο κατω. Αποτελεσμα στην τιμη της στιγμης.
(β) ΣΥΓΚΡΙΣΗ: ολα τα «σχεδον picks» του ανοιγματος (edge ανοιγματος κατωφλι−1% … κατωφλι), παιγμενα ΣΤΟ ΑΝΟΙΓΜΑ, οτι κι αν εγινε μετα
    · και τα κανονικα picks ανοιγματος (≥ κατωφλι) για μετρο.
ΚΡΙΤΗΡΙΟ (ιδιο με t101): μια ζωνη θεωρειται «σαν κανονικα picks» ΜΟΝΟ αν θετικη σε ≥4/5 σεζον ΚΑΙ CLV > 0 ΚΑΙ n ≥ 80. ΠΕΡΙΓΡΑΦΙΚΟ — δεν αλλαζει τιποτα.
Εξοδος: t107_near_miss_open_out.txt"""
import os, sys, io, contextlib
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't101_late_picks_absences.py'), encoding='utf-8').read().split("X = pd.DataFrame(recs); out = []")[0]
g = {'__file__': os.path.join(SC, 't101_late_picks_absences.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, g)
sys.stdout.reconfigure(encoding='utf-8')
np, pd = g['np'], g['pd']
SER, SHIFT, G, dD, SEAS_G, EV, VNO, ACT = (g[k] for k in ('SER', 'SHIFT', 'G', 'dD', 'SEAS_G', 'EV', 'VNO', 'ACT'))
abs_cost, W, line_at, edges, REP_SEASONS = g['abs_cost'], g['W'], g['line_at'], g['edges'], g['REP_SEASONS']
X = pd.DataFrame(g['recs']); X['thr'] = np.where(X.mon.isin([1, 2]), .12, .08); X['gap'] = X.er - X.thr
# (β) ανοιγμα
op = []
for i, (sw, tip, r21, _) in SER.items():
    s = int(SEAS_G[i])
    if s not in EV or s not in REP_SEASONS or not np.isfinite(VNO[i]): continue
    rows = [[x[0] + SHIFT] + list(x[1:]) for x in r21]; rows = [x for x in rows if x[0] <= tip + 900]
    if not rows: continue
    mon = int(G.date.dt.month.values[i]); thr = .12 if mon in (1, 2) else .08
    h, a, d = G.home.values[i], G.away.values[i], dD[i]; t0 = rows[0][0]
    close = line_at(rows, tip, sw); ln0 = line_at(rows, t0, sw)
    m0 = VNO[i] - abs_cost(h, d, s, t0, W)[0] + abs_cost(a, d, s, t0, W)[0]
    E0, (oh, oa), _ = edges(m0, ln0)
    for sd in (1, -1):
        od = oh if sd == 1 else oa; x = (ACT[i] + ln0[0]) * sd
        op.append(dict(i=i, sea=s, mon=mon, gap=E0[sd] - thr, res=(od - 1) if x > 0 else (0.0 if x == 0 else -1.0), clv=sd * (close[3] - ln0[3])))
O = pd.DataFrame(op)
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def cell(d):
    if not len(d): return '—'
    ps = d.groupby('sea').res.sum(); pos = int((ps > 0).sum()); ok = pos >= 4 and d.clv.mean() > 0 and len(d) >= 80
    return f'{100 * d.res.mean():+6.1f}% ({len(d):4d} picks, {d.res.sum():+6.1f}μ, θετ {pos}/{d.sea.nunique()}) · CLV {d.clv.mean():+.2f}π' + (' ✓' if ok else '')
BANDS = (('κατωφλι−1% … κατωφλι (Μπακς 7.92%)', -.01, 0), ('−2% … −1%', -.02, -.01), ('−4% … −2%', -.04, -.02), ('πιο κατω απο −4%', -9, -.04))
P('t107 · ΧΑΝΤΙΚΑΠ NBA · «σχεδον picks» του ανοιγματος · Crown · 5 σεζον · κατωφλι 8% (Ιαν-Φεβ 12%)')
P('κελι = ROI (picks, μοναδες, θετικες σεζον) · CLV = κινηση γραμμης ως το κλεισιμο προς εμας (ποντοι) · ✓ = ≥4/5 & CLV>0 & n≥80')
B = X[X.grp != 'Α']
P('\n(α) ΑΡΓΑ picks που ΚΟΒΕΙ ο κανονας, ανα «ποσο κοντα ηταν το τωρινο μοντελο στην 1η γραμμη» (τιμη της στιγμης):')
for nm, lo, hi in BANDS:
    d = B[(B.gap >= lo) & (B.gap < hi)]
    P(f'  {nm:38s} ολα {cell(d)}')
    P(f'  {"":38s}   Β1 μονο τιμη {cell(d[d.grp == "Β1"])} · Β2 τιμη+απουσιες {cell(d[d.grp == "Β2"])}')
P(f'  ΟΛΑ Β (ελεγχος = t101): {cell(B)}')
P('\n(β) ΠΑΙΓΜΕΝΑ ΣΤΟ ΑΝΟΙΓΜΑ (τιμη ανοιγματος, οτι κι αν εγινε μετα), ανα edge ανοιγματος:')
P(f'  κανονικα picks (≥ κατωφλι)              {cell(O[O.gap >= 0])}')
for nm, lo, hi in BANDS[:3]:
    P(f'  {nm:38s} {cell(O[(O.gap >= lo) & (O.gap < hi)])}')
d = B[(B.gap >= -.01) & (B.gap < 0)]
P('\nανα σεζον (α) ζωνη −1…0: ' + ' · '.join(f'{s}: {d[d.sea == s].res.sum():+.1f}μ ({(d.sea == s).sum()})' for s in sorted(X.sea.unique())))
dd = O[(O.gap >= -.01) & (O.gap < 0)]
P('ανα σεζον (β) ζωνη −1…0: ' + ' · '.join(f'{s}: {dd[dd.sea == s].res.sum():+.1f}μ ({(dd.sea == s).sum()})' for s in sorted(O.sea.unique())))
P('\nελεγχος (2 παραδειγματα (α) ζωνη −1…0):')
for _, r in d.head(2).iterrows():
    j = int(r.i); P(f'   {G.home.values[j]}-{G.away.values[j]} {str(dD[j])[:10]} · {r.tau} · {r.grp} · edge τοτε {100*r.e:.1f}% · τωρινο στην 1η {100*r.er:.1f}% (κατωφλι {100*r.thr:.0f}%) · αποτ {r.res:+.2f}')
open(os.path.join(SC, 't107_near_miss_open_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
