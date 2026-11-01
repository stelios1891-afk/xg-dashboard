"""euro_long_trip_next.py — 16/10/2026 (Στελιος: «ποσο επηρεαζει ενα μακρινο ταξιδι μια ομαδα, στο ιδιο το ματς και στο ΕΠΟΜΕΝΟ — π.χ. εξω στη
Bodø και μετα εξω στο πρωταθλημα· ισως ακομα και εντος, η πτηση 6-12 ωρες πηγαινε-ελα ειναι κουραστικη»).
Ημερολογιο/αγορα: ucl_away_streak_deep (UCL+UEL+UECL 2122-2526, εγχωρια CORE7 2223-2526 με Crown κλεισιμο). Αποσταση = χλμ απο την εδρα της
ομαδας ως το ευρωπαικο γηπεδο (ευθεια· ~800 χλμ ≈ 1ω πτησης, 3000 χλμ ≈ 4ω, 5000 ≈ 6-7ω).
(Α) ΙΔΙΟ ΜΑΤΣ: ο φιλοξενουμενος στην Ευρωπη ανα αποσταση. (Β) ΕΠΟΜΕΝΟ ΕΓΧΩΡΙΟ (≤5 μερες μετα): ανα αποσταση του ευρωπαικου ταξιδιου, χωριστα
αν το επομενο ειναι ΕΝΤΟΣ ή ΕΚΤΟΣ. Μετρα vs αγορα κλεισιματος: διαφορα, γκολ που βαζει / τρωει, συνολο, τυφλο AH, + vs μοντελο & xG."""
import sys, os
_s = open('ucl_away_streak_deep.py', encoding='utf-8').read(); _s = _s[:_s.index("DD = pd.DataFrame(drows)") + len("DD = pd.DataFrame(drows)")]
_o = "prev_away=pe[3],"
assert _s.count(_o) == 1
_s = _s.replace(_o, "prev_away=pe[3], ptrip=(km(LOC.get(t), LOC.get(pe[2])) if pe[3] else 0.0), pcomp=pk['lg'],", 1)
_TO = sys.stdout; sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(_s); sys.stdout = _TO
sys.stdout.reconfigure(encoding='utf-8')
SEAS = ['2122', '2223', '2324', '2425', '2526']
for Z in (E, DD):
    Z['sf'] = (Z.rt + Z.rc) / 2; Z['sa'] = (Z.rt - Z.rc) / 2
def ms(v):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    return f'{v.mean():+.2f}±{v.std() / np.sqrt(max(len(v), 1)):.2f}' if len(v) > 2 else '   —'
def line(lab, y):
    ss = [s for s in SEAS if (y.sea == s).sum() >= 4]
    print(f'   {lab:34s} {len(y):4d} │ {ms(y.rc):>11s} │ {ms(y.sf):>11s} │ {ms(y.sa):>11s} │ {ms(y.rt):>11s} │ {100 * y.roi.mean():+6.1f}% │ {ms(y.rm):>11s} {ms(y.rx):>11s} │ ' +
          ' '.join(f'{s[2:]}:{y[y.sea == s].rc.mean():+.2f}' for s in ss))
hdr = f'   {"":34s} {"n":>4s} │ {"διαφορα−αγ":>11s} │ {"βαζει−αγ":>11s} │ {"τρωει−αγ":>11s} │ {"συνολο−αγ":>11s} │ {"τυφλο AH":>7s} │ {"−μοντελο":>11s} {"xG−μοντ":>11s} │ ανα σεζον (διαφορα)'
B = ((0, 1500, '<1.500 χλμ (≤2ω πτηση)'), (1500, 2500, '1.500-2.500 (2-3ω)'), (2500, 3500, '2.500-3.500 (3-4.5ω)'), (3500, 99999, '≥3.500 (4.5ω+)'))
print('(Α) ΙΔΙΟ ΜΑΤΣ — φιλοξενουμενος στην Ευρωπη (UCL+UEL+UECL 2122-2526) · + = καλυτερα / περισσοτερα γκολ απ οσα περιμενε η αγορα')
print(hdr)
A = E[E.s == -1]
for lo, hi, lab in B: line(lab, A[(A.trip >= lo) & (A.trip < hi)])
print('\n(Β) ΕΠΟΜΕΝΟ ΕΓΧΩΡΙΟ ματς (CORE7, ≤5 μερες μετα το ευρωπαικο) — ανα ταξιδι του ευρωπαικου ματς')
print(hdr)
N = DD[DD.prev_eu]
for where, m in (('ΕΝΤΟΣ', N.s == 1), ('ΕΚΤΟΣ', N.s == -1), ('ολα', N.s != 0)):
    print(f'  — επομενο ματς {where} —')
    y = N[m]
    line('ευρωπαικο ηταν ΕΝΤΟΣ (χωρις ταξιδι)', y[~y.prev_away.astype(bool)])
    for lo, hi, lab in B:
        line('ευρωπαικο εκτος ' + lab, y[y.prev_away.astype(bool) & (y.ptrip >= lo) & (y.ptrip < hi)])
y = N[N.prev_away.astype(bool) & (N.ptrip >= 2500)]
print(f'\n   μακρινα (≥2.500) ταξιδια πριν απο εγχωριο: ' + ', '.join(f'{c}: {int((y.pcomp == c).sum())}' for c in ('ChampionsLeague', 'EuropaLeague', 'ConferenceLeague')))
