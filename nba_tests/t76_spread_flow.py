# -*- coding: utf-8 -*-
"""t76_spread_flow.py — ΓΙΑΤΙ ΒΓΑΙΝΟΥΝ ΤΑ OVER ΣΤΑ ΑΝΙΣΑ ΜΑΤΣ; ΡΟΗ ΤΟΥ ΜΑΤΣ (ΠΕΡΙΓΡΑΦΙΚΟ, 24/10/2026, Στελιος: «τα over βγαινουν οταν το ματς παει οπως
το περιμεναμε (διαφορα 11+ για μεγαλο μερος, στην 4η μπαινουν αναπληρωματικοι) και χανονται οταν το αουτσαιντερ μενει κοντα;»).
ΠΑΛΙΑ ΠΕΡΙΓΡΑΦΗ t75 (βαση): (24/10/2026, Στελιος «τι γινεται οταν
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
t76: play-by-play ESPN (nba_pbp_full/pbp_{σεζον}.jsonl) → σκορ στο τελος της 3ης περιοδου, ποντοι 4ης, τελικη διαφορα. ΠΕΡΙΓΡΑΦΙΚΟ (χωρις κανονα).
Εξοδος: nba_tests/t76_spread_flow_out.txt"""
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

import json as _json, datetime as _dt
# ---- προσημο χαντικαπ ανοιγματος (+ = φαβορι ο γηπεδουχος) ----
SGN = []
for i in O.i.values:
    sw, tip, r21, _ = SER[int(i)]
    rows = sorted([[x[0] + SHIFT] + list(x[1:]) for x in r21 if x[0] + SHIFT <= tip + 900])
    ln = line_at(rows, rows[0][0], sw) if rows else None
    SGN.append(np.sign(ln[3]) if ln else 0.0)
O['fav_home'] = np.array(SGN) > 0
# ---- play-by-play ----
PB = {}
for s in (2022, 2023, 2024, 2025, 2026):
    fn = os.path.join(ROOT, 'nba_pbp_full', f'pbp_{s}.jsonl')
    if not os.path.exists(fn): continue
    for ln in open(fn, encoding='utf-8'):
        try: g_ = _json.loads(ln)
        except Exception: continue
        if g_.get('stype') not in (2, None): continue
        pl = [p for p in g_['plays'] if p[0] is not None and p[2] is not None and p[3] is not None]
        if not pl: continue
        q3 = [p for p in pl if p[0] <= 3]; q4 = [p for p in pl if p[0] <= 4]
        if not q3 or not q4: continue
        us = (_dt.datetime.strptime(g_['date'][:16], '%Y-%m-%dT%H:%M') - _dt.timedelta(hours=5)).date().isoformat()
        PB[(us, g_['teams']['home'], g_['teams']['away'])] = (q3[-1][2], q3[-1][3], q4[-1][2], q4[-1][3])
K = [PB.get((str(d)[:10], h, a_)) for d, h, a_ in zip(O.date, O.home, O.away)]
O['q3h'] = [k[0] if k else np.nan for k in K]; O['q3a'] = [k[1] if k else np.nan for k in K]; O['q4h'] = [k[2] if k else np.nan for k in K]; O['q4a'] = [k[3] if k else np.nan for k in K]
O = O[O.q3h.notna()].copy()
O['fm3'] = np.where(O.fav_home, O.q3h - O.q3a, O.q3a - O.q3h)                # διαφορα υπερ φαβορι μετα την 3η
O['q4pts'] = (O.q4h + O.q4a) - (O.q3h + O.q3a)                                 # ποντοι 4ης (χωρις παραταση)
O['q4rel'] = O.q4pts - O.groupby('sea').q4pts.transform('mean')
fh = np.where(O.fav_home, 1, -1); O['fmF'] = fh * (O.tot.values * 0)          # placeholder
O['fmF'] = np.where(O.fav_home, O.q4h - O.q4a, O.q4a - O.q4h)                 # διαφορα υπερ φαβορι στο τελος της 4ης
O['ov'] = (O.tot > O['T']).astype(float); O['push'] = O.tot == O['T']
def uo(x): return 100 * np.mean([(r['oo'] - 1) if r['tot'] > r['T'] else (0 if r['tot'] == r['T'] else -1) for _, r in x.iterrows()]) if len(x) else np.nan
P(f'NBA · ροη ματς · play-by-play σε {len(O)} ματς (5 σεζον) · {P_MATCH}')
P('\n=== 1. ΟΛΑ ΤΑ ΜΑΤΣ: ποντοι 4ης περιοδου ανα διαφορα μετα την 3η (σε σχεση με τον μεσο ορο της σεζον) ===')
O['am3'] = (O.q3h - O.q3a).abs()
for lo, hi in ((0, 6), (6, 11), (11, 16), (16, 21), (21, 99)):
    x = O[(O.am3 >= lo) & (O.am3 < hi)]
    P(f'  διαφορα μετα την 3η {lo:>2}-{hi:<2}: n {len(x):4d} ({100 * len(x) / len(O):4.1f}%) · ποντοι 4ης {x.q4pts.mean():5.1f} ({x.q4rel.mean():+.1f} απο τον μεσο)')
B = O[O.asp >= 11].copy()
B['flow'] = np.select([B.fm3 >= 11, B.fm3 >= 1], ['φαβορι +11 ή περισσοτερο', 'φαβορι +1 εως +10'], 'αουτσαιντερ μπροστα/ισοπαλια')
P(f'\n=== 2. ΧΑΝΤΙΚΑΠ ≥11 ({len(B)} ματς): ΡΟΗ ΜΕΤΑ ΤΗΝ 3η → over (γραμμη ανοιγματος) ===')
for lab in ('φαβορι +11 ή περισσοτερο', 'φαβορι +1 εως +10', 'αουτσαιντερ μπροστα/ισοπαλια'):
    x = B[B.flow == lab]
    P(f'  {lab:28s} n {len(x):4d} ({100 * len(x) / len(B):4.1f}%) · over {100 * x.ov.mean():4.1f}% · ROI over {uo(x):+6.1f}% · ποντοι 4ης {x.q4rel.mean():+.1f} απο μεσο · '
      f'συνολο − γραμμη {(x.tot - x["T"]).mean():+5.1f}')
for mlab, mm in (('ΜΟΝΤΕΛΟ ΥΠΕΡ over', B.mu > B['T']), ('ΜΟΝΤΕΛΟ ΥΠΕΡ under', B.mu < B['T'])):
    P(f'  -- {mlab} ({int(mm.sum())} ματς):')
    for lab in ('φαβορι +11 ή περισσοτερο', 'φαβορι +1 εως +10', 'αουτσαιντερ μπροστα/ισοπαλια'):
        x = B[mm & (B.flow == lab)]
        P(f'     {lab:28s} n {len(x):4d} ({100 * len(x) / max(1, mm.sum()):4.1f}%) · over {100 * x.ov.mean():4.1f}% · ποντοι 4ης {x.q4rel.mean():+.1f} · συνολο − γραμμη {(x.tot - x["T"]).mean():+5.1f}')
P('\n=== 3. ΧΑΝΤΙΚΑΠ ≥11: ΤΕΛΙΚΗ ΔΙΑΦΟΡΑ (κανονικος χρονος) → over ===')
for lab, m in (('φαβορι κερδισε με ≥11', B.fmF >= 11), ('φαβορι κερδισε με 1-10', (B.fmF >= 1) & (B.fmF < 11)), ('αουτσαιντερ κερδισε/ισοπαλια', B.fmF <= 0)):
    x = B[m]
    P(f'  {lab:28s} n {len(x):4d} ({100 * len(x) / len(B):4.1f}%) · over {100 * x.ov.mean():4.1f}% · ποντοι 4ης {x.q4rel.mean():+.1f} · συνολο − γραμμη {(x.tot - x["T"]).mean():+5.1f}')
P('\n=== 4. ΣΥΓΚΡΙΣΗ: ΧΑΝΤΙΚΑΠ <11, φαβορι +11 μετα την 3η (το ματς «ανοιξε» απροσδοκητα) ===')
C = O[(O.asp < 11)]
x = C[C.fm3 >= 11]; y = C[C.fm3 < 11]
P(f'  ανοιξε ≥11: n {len(x)} · over {100 * x.ov.mean():.1f}% · ποντοι 4ης {x.q4rel.mean():+.1f} · συνολο − γραμμη {(x.tot - x["T"]).mean():+.1f}  |  δεν ανοιξε: n {len(y)} · over {100 * y.ov.mean():.1f}% · ποντοι 4ης {y.q4rel.mean():+.1f}')
open(os.path.join(SC, 't76_spread_flow_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
