"""euro_remote_teams.py — 16/10/2026 (Στελιος: «ομαδες που ταξιδευουν μακρια, π.χ. Καραμπαγκ, Σαμπαχ, Μποντο, Καιρατ — δεν επηρεαζονται;»).
Πανω στις γραμμες ομαδας-ματς του ucl_away_streak_deep (UCL+UEL+UECL 2122-2526, Crown/SBOBET κλεισιμο). «Απομακρυσμενη» ομαδα = εδρα
ανατολικα του 40° μηκους (Αζερμπαιτζαν, Καζακσταν, Αρμενια, Γεωργια…) ή βορεια του 64° (Bodø, Tromsø…).
(1) ταξιδι φιλοξενουμενου απο την εδρα του (χλμ): <1000 / 1000-2000 / 2000-3000 / ≥3000 · (2) απομακρυσμενη ΕΝΤΟΣ (ο αντιπαλος ταξιδεψε μακρια)
· (3) απομακρυσμενη ΕΚΤΟΣ. Μετρα vs αγορα κλεισιματος: διαφορα, γκολ που βαζει / τρωει, συνολο, τυφλο χαντικαπ υπερ ομαδας, ανα σεζον."""
import sys, os
_s = open('ucl_away_streak_deep.py', encoding='utf-8').read(); _s = _s[:_s.index("SEAS = ['2122'")]
_TO = sys.stdout; sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(_s); sys.stdout = _TO
sys.stdout.reconfigure(encoding='utf-8')
SEAS = ['2122', '2223', '2324', '2425', '2526']
E['sf'] = (E.rt + E.rc) / 2; E['sa'] = (E.rt - E.rc) / 2
E['tid'] = [G[m]['h'] if s == 1 else G[m]['a'] for m, s in zip(E.mid, E.s)]
E['oid'] = [G[m]['a'] if s == 1 else G[m]['h'] for m, s in zip(E.mid, E.s)]
def remote(t):
    c = LOC.get(t)
    return bool(c and (c[1] >= 40 or c[0] >= 64))
E['rem'] = [remote(t) for t in E.tid]; E['orem'] = [remote(t) for t in E.oid]
NM = {}
for m, x in G.items():
    pass
def ms(v):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    return f'{v.mean():+.2f}±{v.std() / np.sqrt(max(len(v), 1)):.2f}' if len(v) > 2 else '—'
def line(lab, y):
    print(f'   {lab:40s} {len(y):4d} │ {ms(y.rc):>11s} │ {ms(y.sf):>11s} │ {ms(y.sa):>11s} │ {ms(y.rt):>11s} │ {100 * y.roi.mean():+6.1f}% │ ' +
          ' '.join(f'{s[2:]}:{y[y.sea == s].rc.mean():+.2f}' for s in SEAS if (y.sea == s).sum() >= 3))
hdr = f'   {"":40s} {"n":>4s} │ {"διαφορα−αγ":>11s} │ {"βαζει−αγ":>11s} │ {"τρωει−αγ":>11s} │ {"συνολο−αγ":>11s} │ {"τυφλο AH":>7s} │ ανα σεζον (διαφορα)'
print('ΕΥΡΩΠΗ (UCL+UEL+UECL) 2122-2526 · ομαδα-ματς · + = καλυτερα / περισσοτερα γκολ απ οσα περιμενε η αγορα στο κλεισιμο')
print(f'\n(1) ΦΙΛΟΞΕΝΟΥΜΕΝΟΣ ανα αποσταση ταξιδιου απο την εδρα του'); print(hdr)
A = E[E.s == -1]
for lo, hi in ((0, 1000), (1000, 2000), (2000, 3000), (3000, 99999)):
    line(f'ταξιδι {lo}-{hi if hi < 99999 else "+"} χλμ', A[(A.trip >= lo) & (A.trip < hi)])
print(f'\n(2)-(3) ΑΠΟΜΑΚΡΥΣΜΕΝΕΣ ΟΜΑΔΕΣ (εδρα ανατολικα 40° ή βορεια 64°)'); print(hdr)
line('απομακρυσμενη ΕΝΤΟΣ (αντιπαλος ταξιδεψε)', E[(E.s == 1) & E.rem & ~E.orem])
line('απομακρυσμενη ΕΚΤΟΣ (ταξιδευει η ιδια)', E[(E.s == -1) & E.rem & ~E.orem])
line('ο ΑΝΤΙΠΑΛΟΣ της απομακρυσμενης στην εδρα της', E[(E.s == -1) & E.orem & ~E.rem])
for cm in ('ChampionsLeague', 'EuropaLeague', 'ConferenceLeague'):
    line(f'   {cm[:10]}: απομακρυσμενη ΕΝΤΟΣ', E[(E.comp == cm) & (E.s == 1) & E.rem & ~E.orem])
    line(f'   {cm[:10]}: απομακρυσμενη ΕΚΤΟΣ', E[(E.comp == cm) & (E.s == -1) & E.rem & ~E.orem])
# ποιες ομαδες
from collections import Counter
nm = {}
for f in glob.glob('data_Europe_*.json'):
    for k, m in json.load(open(f, encoding='utf-8')).items():
        nm[int(m['home']['id'])] = m['home']['name']; nm[int(m['away']['id'])] = m['away']['name']
c = Counter(nm.get(int(t), t) for t in E[E.rem].tid)
print('\n   απομακρυσμενες ομαδες στο δειγμα (ομαδα-ματς): ' + ', '.join(f'{k} {v}' for k, v in c.most_common()))
