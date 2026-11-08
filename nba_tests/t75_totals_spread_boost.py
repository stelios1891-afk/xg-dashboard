# -*- coding: utf-8 -*-
"""t75_totals_spread_boost.py — ΣΥΝΟΛΑ NBA: ΧΑΝΤΙΚΑΠ ≥11 × ΜΟΝΤΕΛΟ + «BOOST» ΣΤΟ ΣΥΝΟΛΟ ΑΠΟ ΤΟ ΜΕΓΕΘΟΣ ΤΟΥ ΧΑΝΤΙΚΑΠ (24/10/2026, Στελιος «τι γινεται οταν
συμφωνει το μοντελο και οταν δεν συμφωνει, τι εξτρα boost θα μπορουσαμε να δωσουμε, πχ απο 11 ποντους +1 — πρεπει να ερευνηθει»).
ΠΑΛΙΑ ΠΕΡΙΓΡΑΦΗ t74 (βαση):
ΒΑΣΗ: nba_tests/_t35_totals.csv (Crown, ΑΝΟΙΓΜΑ, 5 σεζον 2021-26) + χαντικαπ ανοιγματος Crown (ιδιο ματς, t22 SER) + box score (G).
 Π1 «GARBAGE TIME»: |δικαιη διαφορα ανοιγματος| μεγαλη → λιγοτεροι ποντοι; ΚΑΝΟΝΑΣ under αν |διαφορα| ≥ s, s ∈ {9, 11, 13}.
 Π2 ΠΑΡΑΤΑΣΗ: |διαφορα| μικρη → περισσοτερες παρατασεις (+~20 π. η καθε μια)· η μηχανη μας ΔΕΝ το βαζει. ΚΑΝΟΝΑΣ over αν |διαφορα| ≤ c, c ∈ {1.5, 3, 4.5}.
 Π3 ΞΕΚΟΥΡΑΣΗ: μερες ξεκουρασης καθε ομαδας (απο το προηγουμενο ματς σεζον)· ομαδα ματς «ΚΑΙ ΟΙ ΔΥΟ ≥2 μερες»· κατευθυνση over/under απο τις αλλες σεζον.
 Π4 ΠΡΟΦΙΛ ΣΟΥΤ: ποσοστο τριποντων στα σουτ (φετινα ως το ματς, μεσος 2 ομαδων) − ιδιο της λιγκας· πανω 20% / κατω 20%· κατευθυνση απο τις αλλες σεζον
    (+ περιγραφικο: διασπορα του πραγματικου γυρω απο τη γραμμη ανα πεμπτημοριο).
LOSO: παραμετρος/κατευθυνση απο τις αλλες 4 σεζον με μοναδες· ελεγχος στην 5η. Αποτελεσμα στην τιμη ΑΝΟΙΓΜΑΤΟΣ.
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ (καθε παραγοντας χωριστα): LOSO picks n ≥ 150 ΚΑΙ ROI > 0 ΚΑΙ CLV > 0 ΚΑΙ θετικο σε ≥4/5 σεζον.
ΝΕΟ (t75): μ = live μοντελο συνολου (μηχανη tt + Φ3 lev − 0.5·LO + 1.0·LD, μονο Out) · σ 18 · |δ| = |δικαιη διαφορα χαντικαπ ανοιγματος|.
 Α ΠΕΡΙΓΡΑΦΙΚΟ ανα |δ|: πραγματικο − μ (μοντελο) και πραγματικο − αγορα.
 Β |δ| ≥ 11 ΧΩΡΙΣΜΕΝΟ: μοντελο ΥΠΕΡ over (μ > γραμμη) vs ΥΠΕΡ under → over %, ROI τυφλου over, υπολοιπο.
 Γ BOOST (ΠΡΟ-ΔΗΛΩΜΕΝΟ): μ' = μ + b·max(0, |δ| − 5) (γραμμικο) · μ'' = μ + k·[|δ| ≥ 11] (σκαλι)· b, k με ελαχιστα τετραγωνα στις ΑΛΛΕΣ 4 σεζον (LOSO).
   ΠΕΡΝΑ αν RMSE καλυτερο απο το μ σε ≥4/5 σεζον ΚΑΙ ROI picks (edge ≥8% στο ανοιγμα) οχι χειροτερο απο μ κατα >1.5pp.
Εξοδος: nba_tests/t75_totals_spread_boost_out.txt"""
import os, sys, io, contextlib, collections
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't22_report_timing.py'), encoding='utf-8').read().split("TAUS = (('ανοιγμα'")[0].replace("if os.environ.get('T22_AUDIT'):", "if False:")
g = {'__file__': os.path.join(SC, 't22_report_timing.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, g)
sys.stdout.reconfigure(encoding='utf-8')
np, pd = g['np'], __import__('pandas')
G, SER, SHIFT, line_at = g['G'], g['SER'], g['SHIFT'], g['line_at']
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
D = pd.read_csv(os.path.join(SC, '_t35_totals.csv'))
O = D[D.tau == 'ανοιγμα'].dropna(subset=['T', 'oo', 'ou', 'fair', 'cfair', 'tot']).copy().reset_index(drop=True)
# ---- 24/10: το i του _t35 ΔΕΝ ταιριαζει πια με το G (ιδιο προβλημα με _t29, βλ. t56) → αντιστοιχιση με (ημερα, γηπ, φιλ) + ελεγχος σκορ ----
GI = {(str(G.date.values[k])[:10], G.home.values[k], G.away.values[k]): k for k in range(len(G))}
O['i'] = [GI.get((str(d)[:10], h, a_)) for d, h, a_ in zip(O.date, O.home, O.away)]
O = O[O.i.notna()].copy(); O['i'] = O.i.astype(int)
ok_sc = np.array([abs(G.hs.values[k] + G.as_.values[k] - t) < 0.5 for k, t in zip(O.i, O.tot)])
O = O[ok_sc & np.array([k in SER for k in O.i])].reset_index(drop=True)
P_MATCH = f'αντιστοιχιση με G: {len(O)} ματς (σκορ ιδιο {100 * ok_sc.mean():.1f}%)'
# ---- χαντικαπ ανοιγματος ----
SP = []
for i in O.i.values:
    sw, tip, r21, _ = SER[int(i)]
    rows = sorted([[x[0] + SHIFT] + list(x[1:]) for x in r21 if x[0] + SHIFT <= tip + 900])
    ln = line_at(rows, rows[0][0], sw) if rows else None
    SP.append(abs(ln[3]) if ln else np.nan)
O['asp'] = SP
O['ot'] = [int(G.ot.values[int(i)] or 0) for i in O.i.values]

O['mu'] = O.tt + O.lev.fillna(0) - 0.5 * O.lo.fillna(0) + 1.0 * O.ld.fillna(0)
O['rm'] = O.tot - O.mu; O['rk'] = O.tot - O.fair
SEAS = sorted(O.sea.unique()); SIG = 18.0
from statistics import NormalDist
ND = NormalDist()
def settle(r, sd):
    x = (r['tot'] - r['T']) * sd; od = r['oo'] if sd > 0 else r['ou']
    return (od - 1) if x > 0 else (0.0 if x == 0 else -1.0)
P(f'NBA ΣΥΝΟΛΑ · ανοιγμα Crown · 5 σεζον · ματς {len(O)} · {P_MATCH}')
P('\n=== Α. ΑΝΑ |ΧΑΝΤΙΚΑΠ|: πραγματικο − ΜΟΝΤΕΛΟ μας / πραγματικο − ΑΓΟΡΑ (π., ± σφαλμα) ===')
for lo, hi in ((0, 3), (3, 5), (5, 7), (7, 9), (9, 11), (11, 13), (13, 99)):
    x = O[(O.asp >= lo) & (O.asp < hi)]
    P(f'  |δ| {lo:>2}-{hi:<2} n {len(x):4d} · − μοντελο {x.rm.mean():+5.2f} ± {x.rm.std() / np.sqrt(len(x)):.2f} · − αγορα {x.rk.mean():+5.2f} ± {x.rk.std() / np.sqrt(len(x)):.2f} · '
      'ανα σεζον (− μοντελο) ' + ' '.join(f'{s % 100}:{x[x.sea == s].rm.mean():+.1f}' for s in SEAS))
P('\n=== Β. |ΧΑΝΤΙΚΑΠ| ≥ 11: τυφλο OVER, χωρισμενο με το τι λεει το μοντελο ===')
B = O[O.asp >= 11]
for lab, m in (('ΟΛΑ', B.mu == B.mu), ('μοντελο ΥΠΕΡ over (μ > γραμμη)', B.mu > B['T']), ('μοντελο ΥΠΕΡ under (μ < γραμμη)', B.mu < B['T']),
               ('μοντελο over κατα ≥3 π.', B.mu >= B['T'] + 3), ('μοντελο under κατα ≥3 π.', B.mu <= B['T'] - 3)):
    x = B[m]; u = [settle(r, 1) for _, r in x.iterrows()]; ps = pd.Series(u, index=x.sea.values).groupby(level=0).sum()
    P(f'  {lab:32s} n {len(x):4d} · over {100 * (x.tot > x["T"]).mean():4.1f}% · ROI over {100 * np.mean(u):+6.1f}% ({sum(u):+.1f}μ, θετ {int((ps > 0).sum())}/{len(ps)}) · '
      f'πραγμ − γραμμη {(x.tot - x["T"]).mean():+5.2f} · − μοντελο {x.rm.mean():+5.2f}')
P('\n=== Γ. BOOST στο μοντελο (LOSO) ===')
f_lin = lambda d: np.maximum(0, d - 5.0); f_step = lambda d: (d >= 11).astype(float)
def picks(mu_col):
    pk = []
    for _, r in O.iterrows():
        po = 1 - ND.cdf((r['T'] + 0.0 - r[mu_col]) / SIG); eo = po * r['oo'] - 1; eu = (1 - po) * r['ou'] - 1
        sd, e = (1, eo) if eo >= eu else (-1, eu)
        if e >= 0.08: pk.append((r['sea'], settle(r, sd)))
    df = pd.DataFrame(pk, columns=['sea', 'u']); ps = df.groupby('sea').u.sum()
    return 100 * df.u.mean(), len(df), df.u.sum(), int((ps > 0).sum())
rm_s = lambda col, Y: float(np.sqrt(((O[O.sea == Y].tot - O[O.sea == Y][col]) ** 2).mean()))
base = {Y: rm_s('mu', Y) for Y in SEAS}
r0 = picks('mu'); P(f'  ΒΑΣΗ μ (live)          RMSE ' + ' '.join(f'{Y % 100}:{base[Y]:.3f}' for Y in SEAS) + f' · picks ≥8%: {r0[0]:+.1f}% ({r0[1]}, {r0[2]:+.1f}μ, {r0[3]}/5)')
for nm, f in (('γραμμικο b·(|δ|−5)+', f_lin), ('σκαλι k·[|δ|≥11]', f_step)):
    col = 'mu_' + nm[:3]; O[col] = O.mu; cf = {}
    for Y in SEAS:
        tr = O[O.sea != Y]; x = f(tr.asp.values); b = float((x * tr.rm.values).sum() / (x * x).sum()); cf[Y] = b
        m = O.sea == Y; O.loc[m, col] = O.loc[m, 'mu'] + b * f(O.loc[m, 'asp'].values)
    rs = {Y: rm_s(col, Y) for Y in SEAS}; bet = sum(rs[Y] < base[Y] - 1e-6 for Y in SEAS); r1 = picks(col)
    ok = bet >= 4 and r1[0] - r0[0] > -1.5
    P(f'  {nm:22s} συντελεστης ανα σεζον ' + ' '.join(f'{Y % 100}:{cf[Y]:+.2f}' for Y in SEAS) + ' · RMSE ' + ' '.join(f'{Y % 100}:{rs[Y]:.3f}' for Y in SEAS)
      + f' · καλυτερο {bet}/5 · picks ≥8%: {r1[0]:+.1f}% ({r1[1]}, {r1[2]:+.1f}μ, {r1[3]}/5) → {"ΠΕΡΝΑΕΙ" if ok else "ΔΕΝ ΠΕΡΝΑΕΙ"}')
x = f_lin(O.asp.values); P(f'  (για συγκριση, ιδιο γραμμικο πανω στην ΑΓΟΡΑ: b = {(x * O.rk.values).sum() / (x * x).sum():+.2f} π. ανα ποντο χαντικαπ πανω απο 5)')
open(os.path.join(SC, 't75_totals_spread_boost_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
