"""euro_dominance_steps.py — 9/10/2026 (Στελιος: «πως ακριβως δημιουργουνται οι διαφορες στα ανισα ματς; μηπως τις πειραξαμε επιτηδες;»).
Αποσυνθεση της προβλεπομενης υπεροχης (οπτικη φαβορι της ΤΕΛΙΚΗΣ προβλεψης) σε βηματα της αλυσιδας:
  Β0 εγχωρια ratings μονο (ουδετερο γηπεδο, χωρις διαφορα λιγκας) → Β1 + εδρα → Β2 + διαφορα λιγκας (γεφυρες παικτων)
  → Β3 + ξεφουσκωμα γ (10/9) → Β4 + κ UCL (11/9) = σημερινη προβλεψη.
Συγκριση με αγορα (Crown κλεισιμο) και πραγματικα γκολ/xG. Επισης: ποιο βημα «φερνει» τα ακραια λ (π.χ. 4.27)."""
import sys, io, json, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
g = {'__name__': 'ds'}
with contextlib.redirect_stdout(io.StringIO()):
    exec(open('euro_dominance_explain.py', encoding='utf-8').read().split("BK = ((0, .3")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1), g)
G = g['G']; o = g['g']
MIDS, SEA, COMP, GD, CROWN, XG, msup = g['MIDS'], g['SEA'], g['COMP'], g['GD'], g['CROWN'], g['XG'], g['msup']
RAW = o['predict_arm'](o['rate_base'])
LHr, LAr = RAW
D = G['D_ARR']; HFV = G['HFV']; RHO = G['RHO']; C = G['C_ARR']; KS = G['KSCOPE']; KAP = G['UCL_FAV_SCALE']
S0 = (LHr / HFV / np.exp(RHO * D), LAr * HFV * np.exp(RHO * D))
S1 = (LHr / np.exp(RHO * D), LAr * np.exp(RHO * D))
S2 = (LHr, LAr)
S3 = (np.maximum(LHr - C / 2, .05), np.maximum(LAr + C / 2, .05))
fh3 = S3[0] >= S3[1]
S4 = (np.where(KS & fh3, S3[0] * KAP, S3[0]), np.where(KS & ~fh3, S3[1] * KAP, S3[1]))
assert np.allclose(S4[0], o['BASE'][0]) and np.allclose(S4[1], o['BASE'][1]), 'ανακατασκευη ≠ σημερινη προβλεψη'
STEPS = [('Β0 εγχωρια', S0), ('+εδρα', S1), ('+λιγκα', S2), ('+γ', S3), ('+κ', S4)]
TOP7 = o['TOP7']; LGH, LGA = G['LGH'], G['LGA']
rows = []
for i, mid in enumerate(MIDS):
    if mid not in XG: continue
    sg = 1 if S4[0][i] >= S4[1][i] else -1
    r = dict(i=i, comp=COMP[i], home=sg == 1, sea=SEA[i], gd=GD[i] * sg, xd=(XG[mid][0] - XG[mid][1]) * sg,
             mkt=(msup(*CROWN[mid], S4[0][i] + S4[1][i]) * sg if mid in CROWN else np.nan),
             fav7=(LGH[i] if sg == 1 else LGA[i]) in TOP7, dog7=(LGA[i] if sg == 1 else LGH[i]) in TOP7,
             fav=XG[mid][2] if sg == 1 else XG[mid][3], dog=XG[mid][3] if sg == 1 else XG[mid][2])
    for lab, (a, b) in STEPS:
        r[lab] = (a[i] - b[i]) * sg; r[lab + '_f'] = a[i] if sg == 1 else b[i]
    rows.append(r)
X = pd.DataFrame(rows); X['fin'] = X['+κ']
BK = ((0, .3, 'ισορροπημενο'), (.3, .7, 'μικρο φαβ'), (.7, 1.2, 'φαβορι'), (1.2, 1.8, 'μεγαλο φαβ'), (1.8, 9, 'τεραστιο φαβ'))
def tab(Z, title):
    print(f'\n{title}')
    print(f'   {"":14s} {"n":>4s} | ' + ' '.join(f'{l:>10s}' for l, _ in STEPS) + f' | {"ΑΓΟΡΑ":>6s} {"ΓΚΟΛ":>6s} {"xG":>6s}')
    for lo, hi, lab in BK:
        z = Z[(Z.fin >= lo) & (Z.fin < hi)]
        if len(z) < 15: continue
        print(f'   {lab:14s} {len(z):4d} | ' + ' '.join(f'{z[l].mean():+10.2f}' for l, _ in STEPS) + f' | {z.mkt.mean():+6.2f} {z.gd.mean():+6.2f} {z.xd.mean():+6.2f}')
tab(X, 'ΟΛΑ — υπεροχη φαβορι μετα απο καθε βημα')
tab(X[X.home], 'ΦΑΒΟΡΙ ΕΝΤΟΣ'); tab(X[~X.home], 'ΦΑΒΟΡΙ ΕΚΤΟΣ')
tab(X[X.comp == 'ChampionsLeague'], 'UCL'); tab(X[X.comp != 'ChampionsLeague'], 'UEL+UECL')
tab(X[X.fav7 & ~X.dog7], 'CORE7 φαβ vs αλλη λιγκα'); tab(X[X.fav7 & X.dog7], 'CORE7 vs CORE7'); tab(X[~X.fav7 & ~X.dog7], 'καμια CORE7')
print('\nΠΑΡΑΔΕΙΓΜΑΤΑ — λ φαβορι μετα απο καθε βημα (υπεροχη)')
for nm in (('Barcelona', 'København'), ('Inter', 'Bodø'), ('Crystal Palace', 'KuPS'), ('Aston Villa', 'Salzburg'), ('Arsenal', 'Kairat'), ('Bologna', 'Brann')):
    z = X[X.fav.str.contains(nm[0], na=False) & X.dog.str.contains(nm[1], na=False) & (X.sea == '2526')]
    for r in z.itertuples():
        rr = r._asdict()
        print(f'   {r.fav[:16]} – {r.dog[:14]}: ' + ' → '.join(f'{l} {rr[l.replace(" ", "_").replace("+", "_").replace("Β0_εγχωρια", "Β0_εγχωρια")] if False else X.loc[r.Index, l]:+.2f}' for l, _ in STEPS)
              + f' · αγορα {r.mkt:+.2f} · σκορ διαφ {r.gd:+d} · xG {r.xd:+.2f}')
print('\nΣΥΝΕΙΣΦΟΡΑ καθε βηματος στην υπερβολη (τεραστια φαβ ≥1.8, ματς με αγορα): μεση αλλαγη υπεροχης ανα βημα')
z = X[(X.fin >= 1.8) & X.mkt.notna()]
prev = None
for l, _ in STEPS:
    print(f'   {l:12s} υπεροχη {z[l].mean():+.2f}' + (f' (βημα {z[l].mean() - z[prev].mean():+.2f})' if prev else '') + f' · vs αγορα {z[l].mean() - z.mkt.mean():+.2f} · vs γκολ {z[l].mean() - z.gd.mean():+.2f}')
    prev = l
