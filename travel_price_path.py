"""travel_price_path.py — 17/10/2026 (Στελιος: «στο μοτιβο 1 περα απο ROI παρακολουθησε την πορεια των τιμων — παιζεται το under και η κοντρα
της ομαδας που ειχε ευρωπαικο;»). ΜΟΤΙΒΟ 1 = Ευρωπη → πρωταθλημα (1.5-6μ), χωρις ευρωπαικο ≤7 μερες μετα· ομαδες Δυτ./Κεντρ. Ευρωπης.
Πορεια (Crown, αλλιως Bet365 · ματς με γραμμες AH/OU = κυριως CORE7): ΑΝΟΙΓΜΑ → ΛΗΞΗ ΤΟΥ ΕΥΡΩΠΑΙΚΟΥ (+2ω) → ΚΛΕΙΣΙΜΟ.
  κινηση συνολου (− = προς UNDER) · κινηση υπεροχης της ομαδας της Ευρωπης (− = ΚΟΝΤΡΑ της) · % ματς με κινηση ≥0.10 προς under / κοντρα ·
  ROI στο ΑΝΟΙΓΜΑ vs στο ΚΛΕΙΣΙΜΟ για under και κοντρα. + Pinnacle 1Χ2 ανοιγμα→κλεισιμο (αντιστροφη) για τα ματς χωρις AH/OU."""
import sys, json, os
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import x12_implied as X12
B = pd.read_pickle('travel_fatigue_B.pkl')
B = B[(B.kind == 'dom')].copy()
import os
PAT = os.environ.get('PAT', '1')
B = B[(B.eu_after > 7) | B.eu_after.isna()] if PAT == '1' else B[B.eu_after <= 5]
X = {}
for l in open('nowgoal_1x2.jsonl', encoding='utf-8'):
    r = json.loads(l)
    if r.get('open') and r.get('close') and min(r['open'] + r['close']) > 1: X[str(r['mid'])] = r
def mv1x2(row):
    r = X.get(str(row.mid))
    if not r: return (np.nan, np.nan)
    h0, a0 = X12.lam_from_1x2(*r['open']); h1, a1 = X12.lam_from_1x2(*r['close'])
    return ((h1 + a1) - (h0 + a0), row.s2 * ((h1 - a1) - (h0 - a0)))
mm = [mv1x2(r) if not np.isfinite(r.mvT_all if 'mvT_all' in B else np.nan) else (np.nan, np.nan) for r in B.itertuples()]
B['x_mvT'] = [m[0] for m in mm]; B['x_mvM'] = [m[1] for m in mm]
def ms(v):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    return f'{v.mean():+.3f}±{v.std() / np.sqrt(max(len(v), 1)):.3f}' if len(v) > 4 else '    —'
def sh(v, sign):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    return f'{100 * np.mean(sign * v >= 0.10):3.0f}%/{100 * np.mean(sign * v <= -0.10):3.0f}%' if len(v) > 4 else '   —   '
def pc(v):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    return f'{100 * v.mean():+6.1f}%' if len(v) >= 5 else '   —  '
TR = (('ευρωπαικο ΕΝΤΟΣ [ελεγχος]', lambda y: y.prev_home), ('εκτος <1.500 χλμ', lambda y: ~y.prev_home & (y.trip < 1500)),
      ('εκτος 1.500-2.500', lambda y: ~y.prev_home & (y.trip >= 1500) & (y.trip < 2500)), ('εκτος ≥2.500', lambda y: ~y.prev_home & (y.trip >= 2500)))
print(('ΜΟΤΙΒΟ 1 — ' if PAT == '1' else 'ΜΟΤΙΒΟ 2 (Ευρωπη → πρωταθλημα → Ευρωπη ≤5μ) — ') + 'ΠΟΡΕΙΑ ΤΙΜΩΝ στο ματς πρωταθληματος μετα απο ευρωπαικο (γκολ αγορας · − συνολο = προς under · − υπεροχη = κοντρα στην ομαδα της Ευρωπης)')
for where, m in (('ΠΡΩΤΑΘΛΗΜΑ ΕΝΤΟΣ', True), ('ΠΡΩΤΑΘΛΗΜΑ ΕΚΤΟΣ', False)):
    y0 = B[B.nhome == m]
    print(f'\n  — {where} — (Crown/Bet365 με γραμμες)')
    print(f'   {"ευρωπαικο πριν":26s} {"n":>4s} │ {"ΣΥΝΟΛΟ ανοιγ→κλεισ":>18s} {"πριν το ευρ.":>13s} {"μετα το ευρ.":>13s} {"προς under/over ≥.1":>19s} │ '
          f'{"ΥΠΕΡΟΧΗ ανοιγ→κλεισ":>19s} {"μετα το ευρ.":>13s} {"κοντρα/υπερ ≥.1":>15s} │ {"UNDER ανοιγ/κλεισ":>17s} {"ΚΟΝΤΡΑ ανοιγ/κλεισ":>18s}')
    for tl, f in TR:
        y = y0[f(y0) & np.isfinite(y0.mvT_all)]
        print(f'   {tl:26s} {len(y):4d} │ {ms(y.mvT_all):>18s} {ms(y.mvT_pre):>13s} {ms(y.mvT_post):>13s} {sh(y.mvT_all, -1):>19s} │ '
              f'{ms(y.mvM_all):>19s} {ms(y.mvM_post):>13s} {sh(y.mvM_all, -1):>15s} │ {pc(y.und_open):>8s}/{pc(y.und):>8s} {pc(y.opp_open):>8s}/{pc(y.roi_opp):>8s}')
    z0 = y0[~np.isfinite(y0.mvT_all) & np.isfinite(y0.x_mvT)]
    print(f'   … Pinnacle 1Χ2 (αλλες λιγκες, ανοιγμα→κλεισιμο):')
    for tl, f in TR:
        z = z0[f(z0)]
        print(f'   {tl:26s} {len(z):4d} │ συνολο {ms(z.x_mvT):>14s} · προς under/over ≥.1 {sh(z.x_mvT, -1)} │ υπεροχη {ms(z.x_mvM):>14s} · κοντρα/υπερ ≥.1 {sh(z.x_mvM, -1)}')
