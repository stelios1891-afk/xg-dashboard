"""euro_stretch_home_source.py — 14/10/2026 (Στελιος: «απο που προερχεται το τεντωμα των ομαδων; ειναι η εγχωρια ποιοτητα που μεταφερεται
με μεγαλυτερα gaps; και απο που προερχεται το λαθος της εδρας; ελεγξε και τα 2»).
Ιδια αποσυνθεση με nonfm_rating_decomp §3 (Poisson με OFFSET = log της ΤΕΛΙΚΗΣ live προβλεψης, κατηγορια Α), ΤΩΡΑ:
  (α) στοχος ΚΑΙ γκολ ΚΑΙ xG (το xG λεει αν ειναι παιχνιδι ή φινιρισμα)
  (β) + μεταβλητη ΕΔΡΑΣ μεσα στο ιδιο μοντελο: 0 = η εδρα του μοντελου (hf, ιδια για ολους) σωστη · + = η εδρα αξιζει περισσοτερο
  → ετσι το τεντωμα (δυναμη ομαδας / διαφορα λιγκας) και η εδρα μετριουνται ΧΩΡΙΣΤΑ (η αποσυνθεση a + b·διαφορα τα ανακατευε:
    η διαφορα του μοντελου ΠΕΡΙΕΧΕΙ και την εδρα, οποτε το «b» συμπιεζε και την εδρα).
  (γ) ΕΔΡΑ αναλυτικα: φαση (λιγκα / νοκ-αουτ), επιπεδο λιγκας γηπεδουχου, σεζον.
"""
import sys, os, glob, json
_MYOUT = sys.stdout; sys.stdout = open(os.devnull, 'w', encoding='utf-8')
exec(open('nonfm_rating_decomp.py', encoding='utf-8').read().split('# ---------- 4. ROTATION')[0])
sys.stdout = _MYOUT; sys.stdout.reconfigure(encoding='utf-8')
NL = chr(10)
XG = {}; PH = {}
for f in glob.glob('data_Europe_*.json'):
    for k, m in json.load(open(f, encoding='utf-8')).items():
        sh = m.get('shots') or []
        if not sh: continue
        hid = int(m['home']['id'])
        XG[str(k)] = (sum(s['xg'] for s in sh if s.get('xg') is not None and int(s['tid']) == hid),
                      sum(s['xg'] for s in sh if s.get('xg') is not None and int(s['tid']) != hid))
PHS = {str(m): p for m, p in zip(_V['mids'], _V['phase'])}
A = R2[(R2.cat == 'Α') & R2.mid.isin(XG)].copy()
A['xh'] = [XG[m][0] for m in A.mid]; A['xa'] = [XG[m][1] for m in A.mid]; A['ph'] = [PHS.get(m) for m in A.mid]
TOP5 = TOP
sv = {lg: s_v4(lg) for lg in set(A.lgh) | set(A.lga)}
mid_cut = np.median([sv[lg] for lg in sv if lg not in TOP5])
tier = lambda lg: 'top5' if lg in TOP5 else ('μεσαια' if sv[lg] >= mid_cut else 'μικρη')
A['tier_h'] = [tier(l) for l in A.lgh]
def design4(df, target):
    rows = []; ys = []; offs = []
    for r in df.itertuples():
        yh, ya = (r.gh, r.ga) if target == 'γκολ' else (r.xh, r.xa)
        for y, lam, t_own, t_opp, sgn in ((yh, r.lh, r.th, r.ta, 1), (ya, r.la, r.ta, r.th, -1)):
            rows.append({'t': (t_own - t_opp) / 2, 'D': sgn * r.D, 'home': sgn / 2}); ys.append(y); offs.append(np.log(lam))
    return pd.DataFrame(rows), np.array(ys, float), np.array(offs)
def run(df, target):
    X, y, off = design4(df, target); return poisson(X, y, off)
print('ΚΑΤΗΓΟΡΙΑ Α — ποσο ΑΚΟΜΑ λαθος εχει η τελικη live προβλεψη (Poisson, offset = live λ)')
print('   δυναμη ομαδας: 0 = σωστη · −0.40 = 40% φουσκωμενη (τεντωμα) │ διαφορα λιγκας: ιδιο │ εδρα: 0 = σωστη · +0.10 ≈ ο γηπεδουχος αξιζει ~10% περισσοτερα γκολ')
for cm, lab in (('EuropaLeague', 'EUROPA'), ('ConferenceLeague', 'CONFERENCE'), ('ChampionsLeague', 'CHAMPIONS')):
    x = A[A.comp == cm]
    for tg in ('xG', 'γκολ'):
        r = run(x, tg)
        print(f'   {lab:11s} n{len(x):4d} στοχος {tg:4s} · ΔΥΝΑΜΗ ΟΜΑΔΑΣ {r["t"][0]:+.2f}±{r["t"][1]:.2f} · ΔΙΑΦΟΡΑ ΛΙΓΚΑΣ {r["D"][0]:+.2f}±{r["D"][1]:.2f} · '
              f'ΕΔΡΑ {r["home"][0]:+.2f}±{r["home"][1]:.2f}')
print(NL + f'ΕΔΡΑ του μοντελου: hf = {HF_LIVE:.3f} (γηπεδουχος ×{HF_LIVE:.3f}, φιλοξενουμενος ÷{HF_LIVE:.3f}) — ΙΔΙΑ για ολες τις διοργανωσεις/φασεις/ομαδες,')
print('   μετρημενη ως √(ολα τα xG γηπεδουχων / ολα τα xG φιλοξενουμενων) σε ΟΛΑ τα ευρωπαικα 2122-2526 (με προκριματικα).')
print('   ΠΡΑΓΜΑΤΙΚΗ εδρα (ωμη, ιδιος τυπος) ανα διοργανωση/φαση — κατηγορια Α:')
for cm in ('EuropaLeague', 'ConferenceLeague', 'ChampionsLeague'):
    for ph in ('league', 'KO'):
        y = A[(A.comp == cm) & (A.ph == ph)]
        if len(y) < 30: continue
        print(f'      {cm:17s} {ph:7s} n{len(y):4d} · ωμη εδρα xG √(γηπ/φιλ) {np.sqrt(y.xh.sum() / y.xa.sum()):.3f} · γκολ {np.sqrt(y.gh.sum() / y.ga.sum()):.3f}')
print(NL + 'ΕΔΡΑ αναλυτικα (στοχος xG, με τη δυναμη ομαδας & λιγκας στο ιδιο μοντελο) — Europa + Conference')
U = A[A.comp.isin(['EuropaLeague', 'ConferenceLeague'])]
for lab, m_ in (('φαση λιγκας/ομιλων', U.ph == 'league'), ('νοκ-αουτ', U.ph == 'KO'), ('γηπεδουχος top-5', U.tier_h == 'top5'),
                ('γηπεδουχος μεσαιας λιγκας', U.tier_h == 'μεσαια'), ('γηπεδουχος μικρης λιγκας', U.tier_h == 'μικρη')) + tuple(
                (f'σεζον {s}', U.sea == s) for s in ('2223', '2324', '2425', '2526')):
    y = U[m_]
    if len(y) < 40: print(f'   {lab:28s} n{len(y)} (λιγα)'); continue
    r = run(y, 'xG')
    print(f'   {lab:28s} n{len(y):4d} · ΕΔΡΑ {r["home"][0]:+.2f}±{r["home"][1]:.2f} · δυναμη ομαδας {r["t"][0]:+.2f}±{r["t"][1]:.2f}')
