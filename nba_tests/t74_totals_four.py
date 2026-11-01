# -*- coding: utf-8 -*-
"""t74_totals_four.py — ΣΥΝΟΛΑ NBA ΣΤΟ ΑΝΟΙΓΜΑ: 4 ΝΕΟΙ ΠΑΡΑΓΟΝΤΕΣ (24/10/2026, Στελιος «τρεξε και τα 4»).
ΒΑΣΗ: nba_tests/_t35_totals.csv (Crown, ΑΝΟΙΓΜΑ, 5 σεζον 2021-26) + χαντικαπ ανοιγματος Crown (ιδιο ματς, t22 SER) + box score (G).
 Π1 «GARBAGE TIME»: |δικαιη διαφορα ανοιγματος| μεγαλη → λιγοτεροι ποντοι; ΚΑΝΟΝΑΣ under αν |διαφορα| ≥ s, s ∈ {9, 11, 13}.
 Π2 ΠΑΡΑΤΑΣΗ: |διαφορα| μικρη → περισσοτερες παρατασεις (+~20 π. η καθε μια)· η μηχανη μας ΔΕΝ το βαζει. ΚΑΝΟΝΑΣ over αν |διαφορα| ≤ c, c ∈ {1.5, 3, 4.5}.
 Π3 ΞΕΚΟΥΡΑΣΗ: μερες ξεκουρασης καθε ομαδας (απο το προηγουμενο ματς σεζον)· ομαδα ματς «ΚΑΙ ΟΙ ΔΥΟ ≥2 μερες»· κατευθυνση over/under απο τις αλλες σεζον.
 Π4 ΠΡΟΦΙΛ ΣΟΥΤ: ποσοστο τριποντων στα σουτ (φετινα ως το ματς, μεσος 2 ομαδων) − ιδιο της λιγκας· πανω 20% / κατω 20%· κατευθυνση απο τις αλλες σεζον
    (+ περιγραφικο: διασπορα του πραγματικου γυρω απο τη γραμμη ανα πεμπτημοριο).
LOSO: παραμετρος/κατευθυνση απο τις αλλες 4 σεζον με μοναδες· ελεγχος στην 5η. Αποτελεσμα στην τιμη ΑΝΟΙΓΜΑΤΟΣ.
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ (καθε παραγοντας χωριστα): LOSO picks n ≥ 150 ΚΑΙ ROI > 0 ΚΑΙ CLV > 0 ΚΑΙ θετικο σε ≥4/5 σεζον.
Εξοδος: nba_tests/t74_totals_four_out.txt"""
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
# ---- ξεκουραση & προφιλ σουτ (μονο ματς ΠΡΙΝ) ----
dD = G.date.values.astype('datetime64[D]'); SE = G.season.values
last = {}; REST = {}; acc = collections.defaultdict(lambda: [0.0, 0.0]); lg = collections.defaultdict(lambda: [0.0, 0.0]); PR3 = {}
for i in np.argsort(dD, kind='stable'):
    s, h, a, d = SE[i], G.home.values[i], G.away.values[i], dD[i]
    rh = (d - last[(s, h)]).astype(int) - 1 if (s, h) in last else np.nan; ra = (d - last[(s, a)]).astype(int) - 1 if (s, a) in last else np.nan
    REST[i] = (rh, ra)
    th, ta, L_ = acc[(s, h)], acc[(s, a)], lg[s]
    if th[1] >= 300 and ta[1] >= 300 and L_[1] > 0: PR3[i] = (th[0] / th[1] + ta[0] / ta[1]) / 2 - L_[0] / L_[1]
    last[(s, h)] = d; last[(s, a)] = d
    for t, m3, fa in ((h, G.h_3a.values[i], G.h_fga.values[i]), (a, G.a_3a.values[i], G.a_fga.values[i])):
        acc[(s, t)][0] += m3; acc[(s, t)][1] += fa; lg[s][0] += m3; lg[s][1] += fa
O['rh'] = [REST[int(i)][0] for i in O.i.values]; O['ra'] = [REST[int(i)][1] for i in O.i.values]
O['p3'] = [PR3.get(int(i), np.nan) for i in O.i.values]
O['res'] = O.tot - O.fair
SEAS = sorted(O.sea.unique())
def settle(r, sd):
    x = (r['tot'] - r['T']) * sd; od = r['oo'] if sd > 0 else r['ou']
    return (od - 1) if x > 0 else (0.0 if x == 0 else -1.0)
def summ(pk):
    if not pk: return '—', 0, 0.0, 0, 0.0
    df = pd.DataFrame(pk, columns=['sea', 'u', 'clv']); ps = df.groupby('sea').u.sum()
    return (f'{100 * df.u.mean():+6.1f}% ({len(df):4d}, {df.u.sum():+6.1f}μ, {int((ps > 0).sum())}/{df.sea.nunique()}) CLV {df.clv.mean():+.2f}π · ανα σεζον '
            + ' '.join(f'{s % 100}:{100 * df[df.sea == s].u.mean():+.0f}%' for s in sorted(df.sea.unique())), len(df), 100 * df.u.mean(), int((ps > 0).sum()), df.clv.mean())
def run_rule(name, cands):
    """cands: [(ετικετα, συναρτηση γραμμη → κατευθυνση ή 0 (με γνωστη κατευθυνση), ή None για «κατευθυνση απο αλλες σεζον»)]"""
    sel = {}
    for Y in SEAS:
        oth = O[O.sea != Y]; best = None
        for lab, f, fixed in cands:
            m = oth.apply(lambda r: f(r), axis=1).astype(bool)
            if m.sum() < 30: continue
            sd = fixed if fixed else (1 if oth[m].res.mean() > 0 else -1)
            u = sum(settle(r, sd) for _, r in oth[m].iterrows())
            if best is None or u > best[0]: best = (u, lab, f, sd)
        sel[Y] = best
    pk = []
    for Y in SEAS:
        _, lab, f, sd = sel[Y]; x = O[O.sea == Y]; m = x.apply(lambda r: f(r), axis=1).astype(bool)
        pk += [(Y, settle(r, sd), sd * (r['cfair'] - r['fair'])) for _, r in x[m].iterrows()]
    txt, n, roi, pos, clv = summ(pk)
    P(f'  LOSO επιλογες: ' + ' · '.join(f'{Y % 100}: {sel[Y][1]} → {"over" if sel[Y][3] > 0 else "under"}' for Y in SEAS))
    P(f'  LOSO: {txt}')
    ok = n >= 150 and roi > 0 and clv > 0 and pos >= 4
    P(f'  ΚΡΙΤΗΡΙΟ ({name}): n {n} (≥150) · ROI {roi:+.1f}% · CLV {clv:+.2f} · θετικες {pos}/5 → {"ΠΕΡΝΑΕΙ" if ok else "ΔΕΝ ΠΕΡΝΑΕΙ"}')
P(f'NBA ΣΥΝΟΛΑ ΣΤΟ ΑΝΟΙΓΜΑ (Crown) · 5 σεζον · ματς {len(O)} · με χαντικαπ ανοιγματος {int(O.asp.notna().sum())} · {P_MATCH}')
P('\n=== ΠΕΡΙΓΡΑΦΙΚΟ: |δικαιη διαφορα ανοιγματος| → παρατασεις και πραγματικο − γραμμη συνολου (π.) ===')
for lo, hi in ((0, 1.5), (1.5, 3), (3, 4.5), (4.5, 7), (7, 9), (9, 11), (11, 13), (13, 99)):
    x = O[(O.asp >= lo) & (O.asp < hi)]
    if not len(x): continue
    P(f'  |διαφορα| {lo:>4}-{hi:<4} n {len(x):4d} · παραταση {100 * (x.ot > 0).mean():4.1f}% · πραγμ − ανοιγμα {x.res.mean():+5.2f} ± {x.res.std() / np.sqrt(len(x)):.2f} · '
      f'χωρις τα ματς με παραταση {x[x.ot == 0].res.mean():+5.2f} · κινηση αγορας ως κλεισιμο {(x.cfair - x.fair).mean():+.2f}')
P('\n=== Π1 «GARBAGE TIME»: under αν |διαφορα| ≥ s ===')
run_rule('Π1', [(f'|δ|≥{s}', (lambda r, s=s: r['asp'] >= s), -1) for s in (9, 11, 13)])
P('\n=== Π2 ΠΑΡΑΤΑΣΗ: over αν |διαφορα| ≤ c ===')
run_rule('Π2', [(f'|δ|≤{c}', (lambda r, c=c: r['asp'] <= c), 1) for c in (1.5, 3, 4.5)])
P('\n=== Π3 ΞΕΚΟΥΡΑΣΗ (μερες απο το προηγουμενο ματς) ===')
for lab, m in (('και οι δυο 0 (B2B)', (O.rh == 0) & (O.ra == 0)), ('ενας 0', ((O.rh == 0) ^ (O.ra == 0))), ('και οι δυο 1', (O.rh == 1) & (O.ra == 1)),
               ('και οι δυο ≥2', (O.rh >= 2) & (O.ra >= 2)), ('ενας ≥2, αλλος 1', ((O.rh >= 2) & (O.ra == 1)) | ((O.ra >= 2) & (O.rh == 1)))):
    x = O[m]; P(f'  {lab:20s} n {len(x):4d} · πραγμ − ανοιγμα {x.res.mean():+5.2f} ± {x.res.std() / np.sqrt(max(len(x), 1)):.2f} · ανα σεζον ' + ' '.join(f'{s % 100}:{x[x.sea == s].res.mean():+.1f}' for s in SEAS))
run_rule('Π3', [('και οι δυο ≥2', (lambda r: r['rh'] >= 2 and r['ra'] >= 2), None), ('και οι δυο ≥3', (lambda r: r['rh'] >= 3 and r['ra'] >= 3), None)])
P('\n=== Π4 ΠΡΟΦΙΛ ΣΟΥΤ (ποσοστο τριποντων στα σουτ, 2 ομαδες − λιγκα) ===')
q = O.p3.quantile([.2, .4, .6, .8]).values
for k, (lo, hi) in enumerate(zip([-9] + list(q), list(q) + [9])):
    x = O[(O.p3 >= lo) & (O.p3 < hi)]
    P(f'  πεμπτημοριο {k + 1} ({lo:+.3f}..{hi:+.3f}) n {len(x):4d} · πραγμ − ανοιγμα {x.res.mean():+5.2f} ± {x.res.std() / np.sqrt(len(x)):.2f} · διασπορα (τυπ. αποκλιση) {x.res.std():.1f} · '
      f'over {100 * (x.tot > x["T"]).mean():.1f}%')
run_rule('Π4', [('πανω 20%', (lambda r: r['p3'] >= q[3]), None), ('κατω 20%', (lambda r: r['p3'] <= q[0]), None)])
open(os.path.join(SC, 't74_totals_four_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
