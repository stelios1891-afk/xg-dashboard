"""
red_effect_study.py — 5/10/2026 (Στελιος): ΤΙ ΚΑΝΕΙ ΠΡΑΓΜΑΤΙΚΑ Η ΚΟΚΚΙΝΗ στο xG — ΕΠΙΘΕΣΗ και ΑΜΥΝΑ της ομαδας με 10 ΧΩΡΙΣΤΑ,
και αν η αμυνα εξαρταται απο το ποσο δυνατος ειναι ο αντιπαλος (υποθεση Στελιου: «η ομαδα με 10 πεθαινει επιθετικα, αλλα δεν
τρωει απαραιτητα πολλα xG αν ο αντιπαλος δεν μπορει να τη βομβαρδισει»).
Μεθοδος (για ΚΑΘΕ ματς με ΜΙΑ κοκκινη στο λεπτο m, 5 ≤ m ≤ 85):
  αναμενομενο xG της καθε ομαδας στο διαστημα μετα την κοκκινη = (προ-αγωνα προβλεψη λ, χωρις γνωση κοκκινης) × k_λιγκας × (μεριδιο xG που
  πεφτει κανονικα στα λεπτα m..τελος — μετρημενο σε ματς ΧΩΡΙΣ κοκκινη). Μετα: λογος ΠΡΑΓΜΑΤΙΚΟ / ΑΝΑΜΕΝΟΜΕΝΟ.
  Ιδιο και για το διαστημα ΠΡΙΝ την κοκκινη (ελεγχος: πρεπει να ειναι ~1) και για τα σουτ (η μηχανη μας = σουτ × xG/σουτ).
xG = χωρις πεναλτι (τα πεναλτι χωριστα). Λ: CORE7 core7_mech_preds_cur_0.75_6_13.csv (2223-2526), Βραζιλια/MLS southam_preds.csv.
"""
import json, glob, sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
C7 = ['EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'PrimeiraLiga', 'Eredivisie']
LAM = {}
P = pd.read_csv('core7_mech_preds_cur_0.75_6_13.csv', dtype={'mid': str})
for r in P.itertuples(): LAM[r.mid] = (r.xg_h, r.xg_a)
Q = pd.read_csv('southam_preds.csv', dtype={'mid': str})
for r in Q.itertuples(): LAM[r.mid] = (r.lh_base, r.la_base)
files = [(lg, f) for lg in C7 for f in glob.glob(f'data_{lg}_*.json') if any(s in f for s in ('2223', '2324', '2425', '2526'))]
files += [('Brazil', f'data_Brazil_{y}.json') for y in (2023, 2024, 2025, 2026)] + [('MLS', f'data_MLS_{y}.json') for y in (2021, 2022, 2023, 2024, 2025, 2026)]
GRP = lambda lg: 'CORE7' if lg in C7 else lg
rows = []; prof = {}
for lg, f in files:
    for mid, m in json.load(open(f, encoding='utf-8')).items():
        mid = str(mid)
        if mid not in LAM or m.get('hs') is None or not m.get('shots'): continue
        H, A = m['home']['id'], m['away']['id']
        if not ({s.get('tid') for s in m['shots']} >= {H, A}): continue
        reds = m.get('reds') or []
        sh = [(s['tid'], s['xg'] or 0, min(int(s.get('min') or 0), 95), s.get('sit') == 'Penalty', bool(s.get('goal'))) for s in m['shots'] if s.get('xg') is not None]
        if not reds:                                    # προφιλ χρονου: μεριδιο npxG ανα λεπτο (ματς χωρις κοκκινη)
            p = prof.setdefault(GRP(lg), np.zeros(96))
            for t, x, mn, pen, g in sh:
                if not pen: p[mn] += x
            rows.append(dict(grp=GRP(lg), mid=mid, red=False, lh=LAM[mid][0], la=LAM[mid][1],
                             xh=sum(x for t, x, mn, pen, g in sh if t == H and not pen), xa=sum(x for t, x, mn, pen, g in sh if t == A and not pen)))
            continue
        if len(reds) != 1: continue
        rm = int(reds[0].get('min') or 0)
        if not (5 <= rm <= 85): continue
        ten_home = bool(reds[0].get('home'))
        T10, T11 = (H, A) if ten_home else (A, H)
        l10, l11 = (LAM[mid][0], LAM[mid][1]) if ten_home else (LAM[mid][1], LAM[mid][0])
        def agg(team, post):
            s = [(x, g) for t, x, mn, pen, g in sh if t == team and not pen and ((mn > rm) if post else (mn <= rm))]
            return sum(x for x, g in s), len(s), sum(g for x, g in s)
        gl = lambda team: sum(1 for t, x, mn, pen, g in sh if t == team and g and mn <= rm)
        sc10, sc11 = gl(T10), gl(T11)
        a10, n10, g10 = agg(T10, True); a11, n11, g11 = agg(T11, True)
        b10, m10, _ = agg(T10, False); b11, m11, _ = agg(T11, False)
        rows.append(dict(grp=GRP(lg), mid=mid, red=True, rm=rm, ten_home=ten_home, l10=l10, l11=l11,
                         post10=a10, post11=a11, sh10=n10, sh11=n11, g10=g10, g11=g11, pre10=b10, pre11=b11, psh10=m10, psh11=m11,
                         state='10 μπροστα' if sc10 > sc11 else ('ισοπαλια' if sc10 == sc11 else '10 πισω')))
R = pd.DataFrame(rows)
# κ λιγκας: πραγματικο npxG / λ (ματς χωρις κοκκινη) · μεριδιο χρονου
K = {g: (d.xh.sum() + d.xa.sum()) / (d.lh.sum() + d.la.sum()) for g, d in R[~R.red].groupby('grp')}
CUM = {g: np.cumsum(p) / p.sum() for g, p in prof.items()}
# σουτ: αναλογια σουτ/xG ανα ομαδα δεν εχουμε απο λ — αναμενομενα σουτ = κ_σ × λ (απο ματς χωρις κοκκινη)
X = R[R.red].copy()
X['rm'] = X.rm.astype(int); X['post_share'] = [1 - CUM[g][rm] for g, rm in zip(X.grp, X.rm)]; X['pre_share'] = 1 - X.post_share
X['k'] = X.grp.map(K)
for t in ('10', '11'):
    X[f'e_post{t}'] = X[f'l{t}'] * X.k * X.post_share; X[f'e_pre{t}'] = X[f'l{t}'] * X.k * X.pre_share
X.to_csv('red_effect_rows.csv', index=False)

def ratio(d, a, e):
    r = d[a].sum() / d[e].sum()
    # bootstrap SE (ματς)
    rng = np.random.default_rng(0); idx = np.arange(len(d)); bs = []
    for _ in range(300):
        s = rng.choice(idx, len(idx)); bs.append(d[a].values[s].sum() / d[e].values[s].sum())
    return r, np.std(bs)
def line(d, lab):
    if len(d) < 25: return f'  {lab:34s} n{len(d):4d}'
    a, sa = ratio(d, 'post10', 'e_post10'); b, sb = ratio(d, 'post11', 'e_post11')
    pa, _ = ratio(d, 'pre10', 'e_pre10'); pb, _ = ratio(d, 'pre11', 'e_pre11')
    return (f'  {lab:34s} n{len(d):4d} | ΜΕΤΑ: επιθεση 10 ×{a:.2f} (±{sa:.2f}) · xG που ΔΕΧΕΤΑΙ ο 10 ×{b:.2f} (±{sb:.2f})'
            f' | ΠΡΙΝ: ×{pa:.2f} / ×{pb:.2f}')
print('ΛΟΓΟΣ πραγματικο/αναμενομενο npxG ΜΕΤΑ την κοκκινη (1.00 = σαν να μην εγινε τιποτα) · ΠΡΙΝ = ελεγχος/επιλογη')
print(f'κ λιγκας (npxG/λ, ματς χωρις κοκκινη): ' + ', '.join(f'{g} {k:.3f}' for g, k in K.items()))
for g in ('ΟΛΑ', 'CORE7', 'Brazil', 'MLS'):
    d = X if g == 'ΟΛΑ' else X[X.grp == g]
    print(line(d, f'[{g}]'))
print('\nΑΝΑ ΔΥΝΑΜΗ ΑΝΤΙΠΑΛΟΥ (προβλεπομενο xG της ομαδας με 11, ολο το ματς) — ΟΛΑ')
for lo, hi in ((0, 1.0), (1.0, 1.3), (1.3, 1.6), (1.6, 2.0), (2.0, 9)):
    print(line(X[(X.l11 * X.k >= lo) & (X.l11 * X.k < hi)], f'αντιπαλος xG {lo}-{hi if hi < 9 else "∞"}'))
print('\nΑΝΑ ΔΥΝΑΜΗ της ομαδας με 10 (προβλεπομενο xG της)')
for lo, hi in ((0, 1.0), (1.0, 1.3), (1.3, 1.6), (1.6, 9)):
    print(line(X[(X.l10 * X.k >= lo) & (X.l10 * X.k < hi)], f'10αρα xG {lo}-{hi if hi < 9 else "∞"}'))
print('\nΑΝΑ ΛΕΠΤΟ ΚΟΚΚΙΝΗΣ')
for lo, hi in ((5, 30), (30, 50), (50, 70), (70, 86)):
    print(line(X[(X.rm >= lo) & (X.rm < hi)], f'λεπτο {lo}-{hi - 1}'))
print('\nΑΝΑ ΣΚΟΡ τη στιγμη της κοκκινης')
for s in ('10 μπροστα', 'ισοπαλια', '10 πισω'):
    print(line(X[X.state == s], s))
print('\nΑΝΑ ΕΔΡΑ της ομαδας με 10')
for h, lab in ((True, '10αρα γηπεδουχος'), (False, '10αρα φιλοξενουμενος')):
    print(line(X[X.ten_home == h], lab))
print('\nΣΥΝΔΥΑΣΜΟΣ: κοκκινη πριν το 60′ × δυναμη αντιπαλου (εκει μετραει περισσοτερο)')
for lo, hi in ((0, 1.3), (1.3, 1.7), (1.7, 9)):
    print(line(X[(X.rm < 60) & (X.l11 * X.k >= lo) & (X.l11 * X.k < hi)], f'πριν 60′, αντιπαλος {lo}-{hi if hi < 9 else "∞"}'))
# ΓΚΟΛ μετα (ελεγχος με γκολ)
print(f"\nΓΚΟΛ μετα την κοκκινη (ελεγχος): 10αρα {X.g10.sum()} γκολ σε αναμενομενα xG {X.e_post10.sum():.0f} · 11αρα {X.g11.sum()} σε {X.e_post11.sum():.0f}")
# ΑΝΑ ΛΕΠΤΟ (ρυθμος): λογος ανα λεπτο υπεροχης → προσθετικη μορφη
mins = (95 - X.rm).sum()
print(f"ΠΡΟΣΘΕΤΙΚΑ ανα λεπτο αριθμ. υπεροχης: 10αρα επιθεση {(X.post10.sum() - X.e_post10.sum()) / mins:+.4f} xG/λεπτο · xG που δεχεται ο 10 {(X.post11.sum() - X.e_post11.sum()) / mins:+.4f} xG/λεπτο")
