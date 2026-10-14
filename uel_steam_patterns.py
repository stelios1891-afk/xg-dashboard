"""uel_steam_patterns.py — 15/10/2026 (Στελιος: «ψαξε τις αποδοσεις απο το ανοιγμα μεχρι το κλεισιμο, σημειωσε αυτες με τη μεγαλυτερη πτωση και
προσπαθησε να βρεις μοτιβα»). Europa League 2223-2526, ΟΛΑ τα ματς (καθε κατηγορια), ασιατικο χαντικαπ Crown (αλλιως SBOBET), Nowgoal.
ΑΝΟΙΓΜΑ = η ΠΡΩΤΗ τιμη του βιβλιου · ΚΛΕΙΣΙΜΟ = η τελευταια πριν τη σεντρα. Κινηση = ποσα γκολ διαφορας «μετακινηθηκε» η αγορα (γραμμη + αποδοση
μετατρεπονται σε διαφορα γκολ) · η πλευρα προς την οποια ηρθε = «πλευρα που επεσε» (η αποδοση/γραμμη της ΜΙΚΡΥΝΕ).
 1) οι μεγαλυτερες πτωσεις (λιστα)
 2) ΜΟΤΙΒΑ: σε ποια ματς/πλευρες πεφτει η τιμη — εντος/εκτος, φαβορι/αουτσαιντερ στο ανοιγμα, επιπεδο λιγκας, φαση, ποσο νωρις ανοιξε, γνωμη μοντελου
 3) ΑΞΙΖΕΙ; η πλευρα που επεσε — ROI στην τιμη ΑΝΟΙΓΜΑΤΟΣ (αν την ειχες παρει νωρις) και στο ΚΛΕΙΣΙΜΟ · και η αντιθετη
 4) ΠΡΟΒΛΕΠΕΤΑΙ; ποια χαρακτηριστικα ΤΟΥ ΑΝΟΙΓΜΑΤΟΣ συνδεονται με την κινηση (ωστε να μπαινεις πριν πεσει)
Περιγραφικο.
"""
import sys, os, json, glob, pickle
NL = chr(10)
_SO = sys.stdout
src = open('uecl_full_review.py', encoding='utf-8').read().replace("CMP = 'ConferenceLeague'", "CMP = '" + os.environ.get('STEAM_COMP', 'EuropaLeague') + "'").split('# ================= Α. ΒΑΘΜΟΝΟΜΗΣΗ')[0]
sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(src); sys.stdout = _SO; sys.stdout.reconfigure(encoding='utf-8')
import euro_shadow_scan as ES
sys.stdout.reconfigure(encoding='utf-8')
TRAJ = u['TRAJ']; KO_ = u['KO']
LG = {str(m): (a, b) for m, a, b in zip(V6['mids'], V6['lg_h'], V6['lg_a'])}
CP = pickle.load(open('euro_components.pkl', 'rb'))
EUM = {}
for f in glob.glob('data_Europe_*.json'):
    for k, m in json.load(open(f, encoding='utf-8')).items(): EUM[str(k)] = m
TOP5 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}
def imp(T, L, oh, oa):
    q = (1 / oh) / (1 / oh + 1 / oa); lo, hi = -6.0, 6.0
    for _ in range(30):
        M = (lo + hi) / 2; pw, pp = ES.cover_q(ES.eu_dist(max((T + M) / 2, .05), max((T - M) / 2, .05), 0.85), 1, L)
        if pw / max(1 - pp, 1e-9) < q: lo = M
        else: hi = M
    return (lo + hi) / 2
rows = []
for i in UI:
    mid = str(MIDS[i]); ko = KO_.get(mid)
    if not ko: continue
    seq = None
    for bk in ('Crown', 'SBOBET'):
        s = TRAJ.get((mid, bk))
        if s: seq = [x for x in s if x[0] <= ko + 900]; bkn = bk
        if seq: break
    if not seq or len(seq) < 2: continue
    t0, L0, oh0, oa0 = seq[0]; t1, L1, oh1, oa1 = seq[-1]
    T = (LH_N[i] + LA_N[i]) if LH_N[i] > 0 else 2.8
    m0 = imp(T, L0, oh0, oa0); m1 = imp(T, L1, oh1, oa1)
    lg = LG.get(mid, ('?', '?')); c = CP.get(mid, {}); m = EUM.get(mid, {})
    # γνωμη μοντελου στο ανοιγμα (μονο αν υπαρχει προβλεψη)
    medge = np.nan
    if LH_N[i] > 0:
        D_ = sdist(LH_N[i], LA_N[i]); medge = (LH_N[i] - LA_N[i]) - m0
    rows.append(dict(mid=mid, i=i, sea=SEA[i], bk=bkn, home=(m.get('home') or {}).get('name', '?'), away=(m.get('away') or {}).get('name', '?'),
                     lgh=lg[0], lga=lg[1], ph=PH.get(i), cat=cat(i), h_open=(ko - t0) / 3600, L0=L0, L1=L1, oh0=oh0, oa0=oa0, oh1=oh1, oa1=oa1,
                     m0=m0, m1=m1, mv=m1 - m0, gd=GD[i], md=medge, th=c.get('th', np.nan), ta=c.get('ta', np.nan)))
X = pd.DataFrame(rows)
# πλευρα που επεσε (η αγορα κινηθηκε προς αυτη)
X['side'] = np.where(X.mv > 0, 1, -1); X['amv'] = X.mv.abs()
X['team'] = np.where(X.side == 1, X.home, X.away); X['opp'] = np.where(X.side == 1, X.away, X.home)
X['lg_s'] = np.where(X.side == 1, X.lgh, X.lga); X['lg_o'] = np.where(X.side == 1, X.lga, X.lgh)
X['fav_open'] = X.side * X.m0 > 0                 # η πλευρα που επεσε ηταν φαβορι στο ανοιγμα;
X['t_s'] = np.where(X.side == 1, X.th, X.ta); X['t_o'] = np.where(X.side == 1, X.ta, X.th)
def settle_side(r, side, L, oh, oa):
    return picks.settle(r.gd, side, L if side == 1 else -L, oh if side == 1 else oa)
X['p_open'] = [settle_side(r, r.side, r.L0, r.oh0, r.oa0) for r in X.itertuples()]
X['p_close'] = [settle_side(r, r.side, r.L1, r.oh1, r.oa1) for r in X.itertuples()]
X['p_open_opp'] = [settle_side(r, -r.side, r.L0, r.oh0, r.oa0) for r in X.itertuples()]
print(f'Europa League 2223-2526: {len(X)} ματς με ανοιγμα & κλεισιμο · ανοιγμα κατα μεσο ορο {X.h_open.median():.0f}ω πριν (διαμεσος) · '
      f'μεση κινηση {X.amv.mean():.2f} γκολ · κινηση ≥0.25: {100 * (X.amv >= .25).mean():.0f}% · ≥0.50: {100 * (X.amv >= .5).mean():.0f}%')
print(NL + '1) ΟΙ 30 ΜΕΓΑΛΥΤΕΡΕΣ ΚΙΝΗΣΕΙΣ (η πλευρα που «επεσε» · γραμμη/αποδοση γηπεδουχου ανοιγμα → κλεισιμο · σκορ)')
for r in X.sort_values('amv', ascending=False).head(30).itertuples():
    print(f'   {r.sea} {r.home[:20]:20s} - {r.away[:20]:20s} │ επεσε: {r.team[:20]:20s} κινηση {r.amv:.2f} │ γηπ {r.L0:+.2f} @{r.oh0:.2f} → {r.L1:+.2f} @{r.oh1:.2f} '
          f'│ ανοιξε {r.h_open:4.0f}ω πριν │ {int(r.gd):+d} │ στο ανοιγμα {r.p_open:+.2f}')
def tab(lab, groups, base=X, minn=15):
    print(f'{NL}   {lab}')
    for nm, m_ in groups:
        y = base[m_]
        if len(y) < minn: print(f'      {nm:44s} n{len(y)} (λιγα)'); continue
        big = y[y.amv >= .25]
        print(f'      {nm:44s} n{len(y):4d} · μεση κινηση {y.amv.mean():.2f} · μεγαλη (≥0.25) {100 * (y.amv >= .25).mean():3.0f}%'
              f' · πλευρα που επεσε: ROI ανοιγμα {100 * big.p_open.mean():+6.1f}% / κλεισιμο {100 * big.p_close.mean():+6.1f}% (n{len(big)})')
print(NL + '2) ΜΟΤΙΒΑ (στις μεγαλες κινησεις ≥0.25: ROI της πλευρας που επεσε, αν την επαιζες στο ΑΝΟΙΓΜΑ / στο ΚΛΕΙΣΙΜΟ)')
B = X[X.amv >= .25]
tab('ΣΥΝΟΛΙΚΑ', (('ολα τα ματς', X.amv >= 0),))
tab('ΠΟΙΑ ΠΛΕΥΡΑ ΕΠΕΣΕ', (('γηπεδουχος', X.side == 1), ('φιλοξενουμενος', X.side == -1), ('το φαβορι του ανοιγματος', X.fav_open), ('το αουτσαιντερ του ανοιγματος', ~X.fav_open)))
tab('ΛΙΓΚΑ ΤΗΣ ΠΛΕΥΡΑΣ ΠΟΥ ΕΠΕΣΕ', (('top-5 vs top-5', X.lg_s.isin(TOP5) & X.lg_o.isin(TOP5)), ('top-5 vs εκτος', X.lg_s.isin(TOP5) & ~X.lg_o.isin(TOP5)),
                                    ('εκτος vs top-5', ~X.lg_s.isin(TOP5) & X.lg_o.isin(TOP5)), ('εκτος vs εκτος', ~X.lg_s.isin(TOP5) & ~X.lg_o.isin(TOP5))))
tab('ΦΑΣΗ / ΣΕΖΟΝ', (('φαση λιγκας/ομιλων', X.ph == 'league'), ('νοκ-αουτ', X.ph == 'KO')) + tuple((f'σεζον {s}', X.sea == s) for s in sorted(X.sea.unique())))
tab('ΠΟΣΟ ΝΩΡΙΣ ΑΝΟΙΞΕ', (('≤24ω πριν', X.h_open <= 24), ('24-72ω', (X.h_open > 24) & (X.h_open <= 72)), ('72-168ω', (X.h_open > 72) & (X.h_open <= 168)), ('>168ω', X.h_open > 168)))
tab('ΓΡΑΜΜΗ ΑΝΟΙΓΜΑΤΟΣ (σκοπια γηπεδουχου)', (('γηπ φαβορι ≥1.25', X.L0 <= -1.25), ('γηπ φαβορι 0.5-1', (X.L0 <= -.5) & (X.L0 > -1.25)), ('κοντα (−0.25…+0.25)', X.L0.abs() <= .25),
                                               ('φιλ φαβορι 0.5-1', (X.L0 >= .5) & (X.L0 < 1.25)), ('φιλ φαβορι ≥1.25', X.L0 >= 1.25)))
tab('ΚΑΤΗΓΟΡΙΑ (FotMob)', (('Α', X.cat == 'A'), ('Β', X.cat == 'B'), ('Γ', X.cat == 'G')))
tab('ΠΛΕΥΡΑ ΠΟΥ ΕΠΕΣΕ = ΠΟΛΥ ΚΥΡΙΑΡΧΗ ΕΚΤΟΣ TOP-5;', (('ναι (t ≥0.9)', ~X.lg_s.isin(TOP5) & (X.t_s >= .9)), ('ο ΑΝΤΙΠΑΛΟΣ ειναι πολυ κυριαρχη εκτος top-5', ~X.lg_o.isin(TOP5) & (X.t_o >= .9))))
print(NL + '3) ΑΞΙΖΕΙ; ROI ανα μεγεθος κινησης — πλευρα που επεσε (ανοιγμα / κλεισιμο) και η ΑΝΤΙΘΕΤΗ στο ανοιγμα')
for lo, hi in ((0, .1), (.1, .25), (.25, .5), (.5, 9)):
    y = X[(X.amv >= lo) & (X.amv < hi)]
    print(f'   κινηση {lo:.2f}-{hi if hi < 9 else "+":>4}: n{len(y):4d} · πλευρα που επεσε: ανοιγμα {100 * y.p_open.mean():+6.1f}% · κλεισιμο {100 * y.p_close.mean():+6.1f}% │ '
          f'αντιθετη στο ανοιγμα {100 * y.p_open_opp.mean():+6.1f}%')
print(NL + '4) ΠΡΟΒΛΕΠΕΤΑΙ ΑΠΟ ΤΟ ΑΝΟΙΓΜΑ; συσχετιση με την κινηση (σκοπια γηπεδουχου, + = προς γηπεδουχο)')
H = X.copy(); H['top5h'] = H.lgh.isin(TOP5).astype(float); H['top5a'] = H.lga.isin(TOP5).astype(float)
H['domh'] = (~H.lgh.isin(TOP5) & (H.th >= .9)).astype(float); H['doma'] = (~H.lga.isin(TOP5) & (H.ta >= .9)).astype(float)
for col, nm in (('md', 'ΜΟΝΤΕΛΟ − αγορα ανοιγματος (γνωμη μοντελου)'), ('m0', 'διαφορα ανοιγματος (ποσο φαβορι ο γηπ)'), ('h_open', 'ωρες πριν ανοιξε'),
                ('top5h', 'γηπεδουχος top-5'), ('top5a', 'φιλοξενουμενος top-5'), ('domh', 'γηπ πολυ κυριαρχη εκτος top-5'), ('doma', 'φιλ πολυ κυριαρχη εκτος top-5')):
    z = H[[col, 'mv']].dropna()
    if len(z) < 30: continue
    r = np.corrcoef(z[col], z.mv)[0, 1]; b = np.polyfit(z[col], z.mv, 1)[0]
    print(f'   {nm:46s} n{len(z):4d} · συσχετιση {r:+.2f} (t {r * np.sqrt(len(z) - 2) / np.sqrt(1 - r * r):+.1f}) · κλιση {b:+.3f}')
y = H.dropna(subset=['md'])
for lo, hi, l in ((-9, -.3, 'μοντελο ≤ −0.3 (βλεπει φιλοξενουμενο)'), (-.3, .3, 'κοντα'), (.3, 9, 'μοντελο ≥ +0.3 (βλεπει γηπεδουχο)')):
    z = y[(y.md >= lo) & (y.md < hi)]
    print(f'      {l:40s} n{len(z):4d} · μεση κινηση προς γηπεδουχο {z.mv.mean():+.3f} · κινηση ≥0.25 προς την πλευρα του μοντελου '
          f'{100 * ((np.sign(z.md) * z.mv) >= .25).mean():.0f}% · κοντρα {100 * ((np.sign(z.md) * z.mv) <= -.25).mean():.0f}%')
X.to_pickle('uel_steam_rows.pkl' if os.environ.get('STEAM_COMP', 'EuropaLeague') == 'EuropaLeague' else f"steam_rows_{os.environ['STEAM_COMP']}.pkl")
