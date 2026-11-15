# -*- coding: utf-8 -*-
"""t9_absence_vs_market.py — ΑΠΟΥΣΙΕΣ: ΕΜΕΙΣ vs ΑΓΟΡΑ vs ΑΠΟΤΕΛΕΣΜΑ (20/10/2026, Στελιος: «αν λειψει ο Μαξει λεμε −2.3,
η αγορα μπορει να κινηθει 4 — ιστορικα ποιος ειναι πιο σωστος;»). ΠΕΡΙΓΡΑΦΙΚΟ, οχι κανονας.
Δεδομενα: news_test (5 σεζον αξιολογησης, Crown ανοιγμα/κλεισιμο, box score).
ΞΑΦΝΙΚΗ απουσια = παικτης ρολου (≥20′) που επαιξε στο προηγουμενο ματς και λειπει σημερα (η ειδηση βγαινει συνηθως μετα το ανοιγμα).
ΕΜΕΙΣ = live φορμουλα 0.75·Σ(αξια+1)·λεπτα/48 · ΑΓΟΡΑ = κινηση κλεισιμο − ανοιγμα (δικαιη γραμμη) · ΠΡΑΓΜΑΤΙΚΟ = τελικη διαφορα.
Ολα με προσημο «προς την ομαδα που χανει τον παικτη» (+ = κοστιζει σε αυτη). Εξοδος: t9_absence_vs_market_out.txt"""
import os, io, sys, contextlib
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
ns = {'__file__': os.path.join(SC, 'news_test.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()):
    exec(open(os.path.join(SC, 'news_test.py'), encoding='utf-8').read().split("def reg(y, X, m):")[0], ns)
sys.stdout.reconfigure(encoding='utf-8')
np = ns['np']; G = ns['G']; FD = ns['FD']; FLO, FLD = ns['FLO'], ns['FLD']; SEAS_G = ns['SEAS_G']; dD = ns['dD']
OPN, CLS, OPT, CLT = ns['OPN'], ns['CLS'], ns['OPT'], ns['CLT']; SER, SHIFT = ns['SER'], ns['SHIFT']
FRESH, value, REP = ns['FRESH'], ns['value'], ns['REP']; ev_m = ns['ev_m']; MG = np.asarray(ns['MG'], float); KN = ns['LOSS'][2][0]
ACT = (G.hs - G.as_).values.astype(float); TOT = (G.hs + G.as_).values.astype(float)
K, C_O, C_D = 0.75, -0.5, 1.0
# back-to-back (ιδιο με t_common) → βαση μοντελου ΧΩΡΙΣ τις ξαφνικες απουσιες
B2H = np.zeros(len(G)); B2A = np.zeros(len(G)); last = {}
for i in np.argsort(dD, kind='stable'):
    s, h_, a_, d = SEAS_G[i], G.home.values[i], G.away.values[i], dD[i]
    B2H[i] = float(last.get((s, h_)) == d - np.timedelta64(1, 'D')); B2A[i] = float(last.get((s, a_)) == d - np.timedelta64(1, 'D'))
    last[(s, h_)] = d; last[(s, a_)] = d
BASE = MG + 3.0 * (B2A - B2H) + 0.75 * KN
# μεγαλυτερος μεμονωμενος απων (σε «δικους μας» ποντους) — σταρ vs πολλοι μικροι
FMAX = np.zeros(len(G))
for i in range(len(G)):
    for side, t in ((1, G.home.values[i]), (-1, G.away.values[i])):
        for p, avg in FRESH.get((t, dD[i]), []):
            FMAX[i] = max(FMAX[i], K * (value(p, SEAS_G[i] - 1) - REP) * avg / 48)
# γραμμη & αποδοσεις κλεισιματος για καλυψη / ROI
CL_L = np.full(len(G), np.nan); CL_OH = np.full(len(G), np.nan); CL_OA = np.full(len(G), np.nan)
for i, (sw, tip, r21, _) in SER.items():
    rows = [[x[0] + SHIFT] + list(x[1:]) for x in r21]; rows = [x for x in rows if x[0] <= tip + 900]
    if not rows: continue
    x = rows[-1]; CL_L[i] = -x[1] * (-1 if sw else 1)
    CL_OH[i], CL_OA[i] = (1 + x[2], 1 + x[3]) if not sw else (1 + x[3], 1 + x[2])

out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def reg(y, X, m):
    y = y[m]; X = np.c_[np.ones(m.sum()), *[x[m] for x in X]]; c, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ c; s2 = r.var() * len(y) / (len(y) - X.shape[1]); se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X))); return c[1:], se[1:]
m0 = ev_m & np.isfinite(OPN) & np.isfinite(CLS)
sg = -np.sign(FD)                                  # +1 = ο γηπεδουχος ειναι η «υγιης» πλευρα
OURS = K * np.abs(FD)                              # εμεις: ποντοι που χανει η ομαδα με τις απουσιες (καθαρο, γηπ − φιλ)
MOVE = sg * (CLS - OPN)                            # αγορα: ποσο πηγε ΚΟΝΤΡΑ στην ομαδα με την απουσια
REAL_O = sg * (ACT - OPN)                          # πραγματικο vs ανοιγμα
LEFT = sg * (ACT - CLS)                            # πραγματικο vs κλεισιμο (+ = η αγορα ΥΠΟτιμησε την απουσια)
SEAS = sorted(set(SEAS_G[m0]))
P('NBA · ΑΠΟΥΣΙΕΣ: ΕΜΕΙΣ vs ΑΓΟΡΑ vs ΑΠΟΤΕΛΕΣΜΑ · 5 σεζον, Crown, ξαφνικες απουσιες ρολου (≥20′, επαιξε στο προηγουμενο ματς)')
P(f'σεζον {SEAS} · αγωνες {m0.sum()} · με ξαφνικη απουσια ≥0.5 π. (δικοι μας) {(m0 & (OURS >= .5)).sum()}')
P('ολοι οι ποντοι «προς την ομαδα που χανει τον παικτη»: + = της κοστιζει')

P(''); P('=== 1. ΠΟΣΟ ΚΟΣΤΙΖΕΙ 1 «δικος μας» ποντος απουσιας (παλινδρομηση, με ελεγχο γνωστων απουσιων) ===')
P('    1.00 = ακριβως οσο λεμε εμεις · >1 = κοστιζει ΠΕΡΙΣΣΟΤΕΡΟ απο οσο λεμε')
Y = {'ΠΡΑΓΜΑΤΙΚΟ (αποτελεσμα − βαση μοντελου)': ACT - BASE, 'ΑΓΟΡΑ κλεισιμο (− βαση μοντελου)': CLS - BASE,
     'ΑΓΟΡΑ ανοιγμα (− βαση μοντελου)': OPN - BASE, 'κινηση αγορας (κλεισ − ανοιγμα)': CLS - OPN, 'μενει στο κλεισιμο (αποτελ − κλεισ)': ACT - CLS}
for lab, y in Y.items():
    c, se = reg(y, [K * FD, KN], m0); ps = []
    for s in SEAS:
        cs, _ = reg(y, [K * FD, KN], m0 & (SEAS_G == s)); ps.append(-cs[0])
    P(f'  {lab:42s} {-c[0]:5.2f} ± {se[0]:.2f}  · ανα σεζον: ' + ' '.join(f'{x:4.2f}' for x in ps))

P(''); P('=== 2. ΑΝΑ ΜΕΓΕΘΟΣ ΑΠΟΥΣΙΑΣ (μεσοι οροι, ποντοι) ===')
P(f'  {"εμεις λεμε":14s} {"n":>5s} {"εμεις":>6s} {"κινηση αγ.":>10s} {"ανοιγμα→":>9s} {"πραγμ. vs ανοιγμα":>17s} {"πραγμ. vs κλεισ.":>16s}')
for lo, hi in ((0.5, 1), (1, 2), (2, 3), (3, 4.5), (4.5, 99)):
    m = m0 & (OURS >= lo) & (OURS < hi)
    P(f'  {f"{lo:g}-{hi:g}" if hi < 99 else f"≥{lo:g}":14s} {m.sum():5d} {OURS[m].mean():6.2f} {MOVE[m].mean():10.2f} {"":9s} {REAL_O[m].mean():17.2f} {LEFT[m].mean():+16.2f}')
P('  (πραγμ. vs ανοιγμα = ολο το κοστος που φανηκε στο γηπεδο σε σχεση με τη γραμμη ανοιγματος· αν η ειδηση ηταν ηδη γνωστη στο ανοιγμα, ειναι μικροτερο)')

P(''); P('=== 3. ΣΤΑΡ vs ΠΟΛΛΟΙ ΜΙΚΡΟΙ (ιδιο συνολικο μεγεθος 1.5-4 π.) ===')
for lab, mm in (('ενας σταρ (≥1.5 π. ο ιδιος)', FMAX >= 1.5), ('χωρις σταρ (κανενας ≥1.5)', FMAX < 1.5)):
    m = m0 & (OURS >= 1.5) & (OURS < 4) & mm
    if m.sum() < 20: P(f'  {lab:32s} n {m.sum()} (λιγα)'); continue
    c, se = reg(REAL_O, [OURS], m)
    P(f'  {lab:32s} n {m.sum():4d} · εμεις {OURS[m].mean():.2f} · κινηση αγορας {MOVE[m].mean():.2f} · πραγμ. vs ανοιγμα {REAL_O[m].mean():.2f} · '
      f'πραγμ. vs κλεισιμο {LEFT[m].mean():+.2f}')

P(''); P('=== 4. ΤΟ ΒΑΣΙΚΟ ΕΡΩΤΗΜΑ: η αγορα κινηθηκε ΠΕΡΙΣΣΟΤΕΡΟ / ΛΙΓΟΤΕΡΟ απο οσο λεμε εμεις — ποιος ειχε δικιο; ===')
P('  (μονο αγωνες με ξαφνικη απουσια ≥1 π. δικοι μας · «διαφορα» = κινηση αγορας − δικη μας εκτιμηση)')
P('  καλυψη/ROI = παιζεις την ομαδα ΜΕ την απουσια στο κλεισιμο (Crown) — >50% / + = η αγορα το υπερτιμησε')
mb = m0 & (OURS >= 1) & np.isfinite(CL_L)
D = MOVE - OURS
def cover_absent(m):
    """καλυψη & ROI παιζοντας την ομαδα με την απουσια (sg=+1 → φιλοξενουμενος) στο κλεισιμο"""
    res = []; seas = []
    for i in np.where(m)[0]:
        if sg[i] > 0:  x = -(ACT[i] + CL_L[i]); od = CL_OA[i]    # φιλοξενουμενος με απουσια: καλυπτει αν ACT + L < 0
        else:          x = ACT[i] + CL_L[i]; od = CL_OH[i]
        res.append(0.0 if x == 0 else (od - 1 if x > 0 else -1.0)); seas.append(SEAS_G[i])
    res = np.array(res); seas = np.array(seas)
    pos = sum(1 for s in set(seas) if res[seas == s].mean() > 0)
    return (res > 0).sum() / max((res != 0).sum(), 1), res.mean(), pos, len(set(seas))
for lab, lo, hi in (('αγορα ΠΟΛΥ ΛΙΓΟΤΕΡΟ (≤ −1.5)', -99, -1.5), ('αγορα λιγοτερο (−1.5…−0.5)', -1.5, -0.5), ('περιπου ιδια (±0.5)', -0.5, 0.5),
                    ('αγορα περισσοτερο (+0.5…+1.5)', 0.5, 1.5), ('αγορα ΠΟΛΥ ΠΕΡΙΣΣΟΤΕΡΟ (+1.5…+3)', 1.5, 3), ('αγορα ΤΕΡΑΣΤΙΑ (≥ +3)', 3, 99)):
    m = mb & (D >= lo) & (D < hi)
    if m.sum() < 15: P(f'  {lab:34s} n {m.sum()} (λιγα)'); continue
    cv, roi, pos, ns_ = cover_absent(m)
    rm_c = np.sqrt(np.mean((ACT[m] - CLS[m]) ** 2)); rm_o = np.sqrt(np.mean((ACT[m] - (OPN[m] - sg[m] * OURS[m])) ** 2))
    P(f'  {lab:34s} n {m.sum():4d} · εμεις {OURS[m].mean():.1f} · αγορα {MOVE[m].mean():+.1f} · πραγμ. vs ανοιγμα {REAL_O[m].mean():+.1f} · '
      f'πραγμ. vs κλεισ {LEFT[m].mean():+.2f} · καλυψη ομαδας-με-απουσια {100 * cv:.1f}% ROI {100 * roi:+.1f}% ({pos}/{ns_})')
    P(f'  {"":34s}        λαθος (RMSE): κλεισιμο αγορας {rm_c:.2f} · ανοιγμα + δικη μας διορθωση {rm_o:.2f}')

P(''); P('=== 5. ΠΟΙΟΝ ΝΑ ΕΜΠΙΣΤΕΥΤΟΥΜΕ: πραγμ. − ανοιγμα = α·(κινηση αγορας) + β·(δικη μας εκτιμηση) ===')
P('  α = 1, β = 0 → η αγορα τα λεει ολα σωστα · β > 0 → η δικη μας εκτιμηση προσθετει πληροφορια που η αγορα δεν εβαλε')
for lab, mm in (('ολες οι ξαφνικες ≥1 π.', mb), ('η αγορα κινηθηκε ≥1 π. προς την απουσια', mb & (MOVE >= 1)),
                ('η αγορα κινηθηκε ΠΕΡΙΣΣΟΤΕΡΟ απο εμας (+1.5)', mb & (D >= 1.5))):
    c, se = reg(REAL_O, [MOVE, OURS], mm); ps = []
    for s in SEAS:
        if (mm & (SEAS_G == s)).sum() > 30:
            cs, _ = reg(REAL_O, [MOVE, OURS], mm & (SEAS_G == s)); ps.append(f'{cs[0]:.2f}/{cs[1]:.2f}')
    P(f'  {lab:46s} n {mm.sum():4d} · α {c[0]:.2f} ± {se[0]:.2f} · β {c[1]:.2f} ± {se[1]:.2f} · ανα σεζον α/β: {" ".join(ps)}')

P(''); P('=== 6. ΣΥΝΟΛΑ: ιδια λογικη (εμεις = −0.5·επιθεση + 1.0·αμυνα που χανεται) ===')
mt = ev_m & np.isfinite(OPT) & np.isfinite(CLT)
OT = C_O * FLO + C_D * FLD; MVT = CLT - OPT
for lab, y in (('πραγματικο − ανοιγμα', TOT - OPT), ('κινηση αγορας', MVT), ('πραγματικο − κλεισιμο', TOT - CLT)):
    c, se = reg(y, [OT], mt)
    P(f'  {lab:24s} ανα «δικο μας» ποντο: {c[0]:5.2f} ± {se[0]:.2f}')
mt2 = mt & (np.abs(OT) >= 1)
c, se = reg(TOT - OPT, [MVT, OT], mt2)
P(f'  ποιον να εμπιστευτουμε (|εμεις| ≥1, n {mt2.sum()}): α (αγορα) {c[0]:.2f} ± {se[0]:.2f} · β (εμεις) {c[1]:.2f} ± {se[1]:.2f}')
open(os.path.join(SC, 't9_absence_vs_market_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
