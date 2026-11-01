"""uel_late_over_xi.py — 14/10/2026 (Στελιος: «αν περιμενουμε και το κλεισιμο, γιατι να μην προσθεσουμε και την ποιοτητα ενδεκαδας;»).
Βαση = ο κανονας που περασε (uel_late_over_test): over UEL κατηγορια Α, edge ≥8% μεσα στις τελευταιες 12ω. ΕΔΩ: περιμενουμε τις ενδεκαδες
(~1ω πριν) και παιζουμε ΣΤΟ ΚΛΕΙΣΙΜΟ μονο αν περνα φιλτρο ενδεκαδας. ΚΑΜΙΑ νεα αναζητηση κατωφλιου (μενει 8%).
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΥΡΙΟ ΦΙΛΤΡΟ: ενδεκαδα ΦΑΒΟΡΙ ≥1.00 (ιδιο με το ευρημα ενδεκαδας). Δευτερευοντα (πληροφορια): φαβορι ≥0.90 · και οι 2 ≥0.90 ·
και τιμη κλεισιματος να εχει ακομα edge ≥8%. Κριτηρια Κ2-Κ4 (2 βιβλια, ≥3/4 σεζον, νεα μορφη) + να ΒΕΛΤΙΩΝΕΙ τις μοναδες ή το ROI
χωρις να χανει σεζον, και τα picks που ΚΟΒΕΙ να ειναι χειροτερα. + ιδιο φιλτρο στο Conference (επαναληψη, κατηγορια Α, edge ≥ −2% ως live).
"""
import sys, pickle
src = open('uel_late_over_test.py', encoding='utf-8').read().split("for win in ('≤12ω'")[0]
exec(src)
XR = pickle.load(open('uel_xi_ratios.pkl', 'rb'))
CLe = CL.e
def add(F):
    F = F.copy(); m = [XR.get(str(MIDS[k]), (np.nan, np.nan, 0)) for k in F.i]
    F['rf'] = [(a if f == 1 else b) if f else np.nan for a, b, f in m]
    F['rmin'] = [min(a, b) for a, b, f in m]
    F['pc'] = [CL.pnl.get((r.i, r.bk), np.nan) for r in F.itertuples()]
    F['ec'] = [CLe.get((r.i, r.bk), np.nan) for r in F.itertuples()]
    return F
def show(lab, x, col='pc'):
    x = x.dropna(subset=[col])
    if len(x) < 6: print(f'   {lab:44s} (λιγα)'); return
    y = x.assign(pnl=x[col]); k2, k3, k4 = crit(y)
    print(f'   {lab:44s} {cc(y)}  Κ2{ck(k2)} Κ3{ck(k3)} Κ4{ck(k4)}')
for lab_c, comp_ok in (('EUROPA LEAGUE (κυριο)', lambda i: COMP[i] == 'EuropaLeague'),):
    F = add(stream('≤12ω', .08))
    print(f'===== {lab_c}: over κατηγορια Α, edge ≥8% στις τελευταιες 12ω — αποτελεσμα ΣΤΗΝ ΤΙΜΗ ΚΛΕΙΣΙΜΑΤΟΣ')
    print(f'   γνωστη ενδεκαδα φαβορι: {F.rf.notna().mean() * 100:.0f}% των picks')
    show('ΟΛΑ (χωρις φιλτρο) — στην εισοδο', F, 'pnl')
    show('ΟΛΑ (χωρις φιλτρο) — στο κλεισιμο', F)
    print('   --- με φιλτρο ενδεκαδας (παιζεται στο κλεισιμο):')
    show('★ φαβορι ≥1.00 (ΚΥΡΙΟ)', F[F.rf >= 1.0])
    show('   κοβονται: φαβορι <1.00', F[F.rf < 1.0])
    show('   αγνωστη ενδεκαδα φαβορι', F[F.rf.isna()])
    show('φαβορι ≥0.90', F[F.rf >= 0.9])
    show('   κοβονται: φαβορι <0.90', F[F.rf < 0.9])
    show('και οι 2 ≥0.90', F[F.rmin >= 0.9])
    show('   κοβονται: καποια <0.90', F[F.rmin < 0.9])
    show('φαβορι ≥1.00 ΚΑΙ edge κλεισιματος ≥8%', F[(F.rf >= 1.0) & (F.ec >= .08)])
    show('edge κλεισιματος ≥8% (χωρις ενδεκαδα)', F[F.ec >= .08])
    print('   ανα ποσοστο ενδεκαδας φαβορι (κλεισιμο):')
    for lo, hi, l in ((0, .9, '<0.90'), (.9, 1.0, '0.90-1.00'), (1.0, 1.15, '1.00-1.15'), (1.15, 9, '≥1.15')):
        show(f'      {l}', F[(F.rf >= lo) & (F.rf < hi)])
