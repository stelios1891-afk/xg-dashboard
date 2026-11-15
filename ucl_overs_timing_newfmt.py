"""ucl_overs_timing_newfmt.py — 10/10/2026 (Στελιος: «χρονισμος στα over: πως κινειται η αγορα σε οσα βγαινουν νωρις; οσα βγαινουν τις τελευταιες 8ω ειναι μετα απο κοντρα;»).
ΜΟΝΟ νεα μορφη UCL (2425-2526), OVER @4%, ζωνη 1.70-2.10, μεσος Crown/SBOBET· απο euro_totals_first.pkl (euro_totals_test, μηχανη γκολ W2 + κ).
κινηση = «συνολο αγορας» (γκολ) απο τη γραμμη/τιμες: + = η αγορα ΑΝΕΒΑΣΕ τα γκολ (προς το over μας → η τιμη μας χαλαει), − = τα κατεβασε (κοντρα)."""
import sys, numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
F = pd.read_pickle('euro_totals_first.pkl')
X = F[(F.side == 'over') & F.sea.isin(['2425', '2526'])].copy()
R = pd.read_pickle('euro_totals_first.pkl')
def c(x):
    if len(x) == 0: return '—'
    m = x.groupby('bk').pnl.agg(['mean', 'size']); ps = x.groupby('sea').pnl.mean()
    return f'{m["size"].mean():3.0f} picks {100 * m["mean"].mean():+6.1f}% (' + ' '.join(f'{s} {100 * v:+.0f}' for s, v in ps.items()) + ')'
WIN = ((72, 72, '72ω'), (60, 48, '60-48ω'), (36, 24, '36-24ω'), (18, 12, '18-12ω'), (8, 4, '8-4ω'), (2, 0, '2ω-κλεισ'))
print('OVER, Champions League νεα μορφη · ανα ωρα ΠΡΩΤΗΣ εμφανισης')
print(f'   {"βγηκε":10s} {"ROI στην εμφανιση":38s} | κινηση ΠΡΙΝ (απο πρωτη τιμη) | κινηση ΜΕΤΑ (ως κλεισιμο) | % ανεβηκαν γκολ μετα | % κοντρα συνεχισε')
for hi, lo, wl in WIN:
    y = X[(X.h <= hi) & (X.h >= lo)]
    if len(y) == 0: continue
    print(f'   {wl:10s} {c(y):38s} | {y.mv_before.mean():+.2f} | {y.mv_after.mean():+.2f} | {100 * (y.mv_after >= 0.05).mean():3.0f}% | {100 * (y.mv_after <= -0.05).mean():3.0f}%')
L = X[X.h <= 8]
print(f'\nΤΕΛΕΥΤΑΙΕΣ 8 ΩΡΕΣ: {c(L)} · μετα απο κοντρα (γκολ κατεβηκαν ≥0.05 πριν την εισοδο): {100 * (L.mv_before <= -0.05).mean():.0f}% των picks')
for lab, m in (('με κοντρα ≥0.25', L.mv_before <= -0.25), ('κοντρα 0.05-0.25', (L.mv_before <= -0.05) & (L.mv_before > -0.25)), ('χωρις κοντρα', L.mv_before > -0.05)):
    print(f'   {lab:18s} {c(L[m])} · μεση κοντρα {L[m].mv_before.mean():+.2f}')
E = X[X.h >= 48]
print(f'\nΝΩΡΙΣ (72-48ω): {c(E)} · κινηση μετα {E.mv_after.mean():+.2f} · ανεβηκαν γκολ {100 * (E.mv_after >= 0.05).mean():.0f}% / κατεβηκαν {100 * (E.mv_after <= -0.05).mean():.0f}%')
