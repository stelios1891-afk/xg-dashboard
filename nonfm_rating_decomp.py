"""nonfm_rating_decomp.py — 13/10/2026 (Στελιος: «θελω να ερευνησουμε το λαθος απο την αρχη του — τι λαθος εχουν τα ratings των ομαδων με Ben ή γκολ+Elo»).
ΑΠΟΣΥΝΘΕΣΗ της προβλεψης του ευρωπαικου μοντελου (ιδια μηχανη με euro_live_projections: GEngine + Griffis + Elo-αντικατασταση + s_v4) σε ΚΟΜΜΑΤΙΑ:
  log λ_γηπ − log λ_φιλ = t_γηπ − t_φιλ + 2·ρ·D + 2·ln(hf)
  t = att − leak = η ΔΥΝΑΜΗ ΤΗΣ ΟΜΑΔΑΣ μεσα στη λιγκα της (FotMob: σουτ/xG + γκολ · Ben: Opta xG · γκολ+Elo: 2·(a + b·Elo/100 − ρ·s_λιγκας))
  D = s(λιγκα γηπ) − s(λιγκα φιλ) = ΔΙΑΦΟΡΑ ΕΠΙΠΕΔΟΥ ΛΙΓΚΑΣ (αξιες παικτων / bridge / ClubElo χωρας)
ΕΡΩΤΗΜΑ: ποιο κομματι ειναι «φουσκωμενο»; Poisson παλινδρομηση στα ΓΚΟΛ 4 σεζον ευρωπαικων (2223-2526):
  log λ = c + β_ομαδας(πηγη)·(t/2) + β_λιγκας·(ρD) + h·εδρα   (για καθε πλευρα, με προσημο)
  β = 1 → το κομματι ειναι σωστα κλιμακωμενο · β < 1 → φουσκωμενο (π.χ. 0.6 = 40% μεγαλυτερο απ οσο αξιζει) · β > 1 → συμπιεσμενο.
  ΧΩΡΙΣΤΑ β για τη δυναμη ομαδας FotMob / Ben / γκολ+Elo, και για τη διαφορα λιγκας.
+ ΕΛΕΓΧΟΣ ΤΗΣ ΜΕΤΑΤΡΟΠΗΣ Elo: η γραμμη Elo → δυναμη (CAL) μετριεται σε ομαδες FotMob/Ben και εφαρμοζεται σε ομαδες μικρων λιγκων — ταιριαζει παντου;
Διαγνωστικο: ΔΕΝ ρυθμιζει τιποτα, δειχνει ΠΟΥ βρισκεται το λαθος.
"""
import sys, os, io
_src = open('euro_live_projections.py', encoding='utf-8').read()
_cut = _src.index('# ================================================================ ΠΕΡΣΙΝΑ ΕΥΡΩΠΑΪΚΑ -> PRIOR')
_DEV = open(os.devnull, 'w', encoding='utf-8'); _REAL = sys.stdout; sys.stdout = _DEV
exec(_src[:_cut])
sys.stdout = _REAL; sys.stdout.reconfigure(encoding='utf-8')
NL = chr(10)
# ---------- κομματια ανα ματς ----------
EUm = EUe.set_index('mid')
R = []
for r in B_ALL.itertuples():
    eh, ea = ELO_MID.get(str(r.mid), (np.nan, np.nan))
    sides = []
    for att, lk, src_, lg, el in ((r.att_h, r.leak_h, r.src_h, r.lg_h, eh), (r.att_a, r.leak_a, r.src_a, r.lg_a, ea)):
        lab = {'shots': 'FotMob', 'griffis': 'Ben', 'goals': 'γκολ+Elo'}[src_]
        if src_ == 'goals':
            try: el = float(el)
            except (TypeError, ValueError): el = np.nan
            if np.isnan(el): lab = 'γκολ (χωρις Elo)'
            else:
                u = A_CAL + B_CAL * el / 100.0 - RHO * s_v4(lg); att, lk = u, -u
        sides.append((att - lk, lab, s_v4(lg), lg, el))
    (th, sh, svh, lgh, elh), (ta, sa, sva, lga, ela) = sides
    m = EUm.loc[r.mid] if r.mid in EUm.index else None
    comp = m.comp if m is not None and not isinstance(m, pd.DataFrame) else None
    R.append(dict(mid=r.mid, sea=r.sea, comp=comp, gh=r.gh, ga=r.ga, th=th, ta=ta, sh=sh, sa=sa, D=RHO * (svh - sva), lgh=lgh, lga=lga, lXs=r.lXs, elh=elh, ela=ela))
R = pd.DataFrame(R)
R = R[~R.sh.str.contains('χωρις') & ~R.sa.str.contains('χωρις')].reset_index(drop=True)
R['cat'] = np.where((R.sh == 'FotMob') & (R.sa == 'FotMob'), 'Α', np.where((R.sh == 'FotMob') | (R.sa == 'FotMob'), 'Β', 'Γ'))
print(f'Ευρωπαικα ματς 2223-2526 με πληρη κομματια: {len(R)} · κατηγοριες ' + ' '.join(f'{k}:{v}' for k, v in R.cat.value_counts().items()))
print(f'Μετατροπη Elo (CAL): δυναμη = {A_CAL:+.3f} + {B_CAL:.4f}·Elo/100 (μετρημενη σε {len(xs)} πλευρες FotMob/Ben)')
# ---------- Poisson παλινδρομηση ----------
SRC = ['FotMob', 'Ben', 'γκολ+Elo']
def design(df):
    rows = []; ys = []; offs = []
    for r in df.itertuples():
        for y, t_own, s_own, t_opp, s_opp, sgnD, home in ((r.gh, r.th, r.sh, r.ta, r.sa, 1, 1), (r.ga, r.ta, r.sa, r.th, r.sh, -1, 0)):
            x = {f't_{s}': 0.0 for s in SRC}
            x[f't_{s_own}'] += t_own / 2; x[f't_{s_opp}'] -= t_opp / 2
            x['D'] = sgnD * r.D; x['home'] = home
            rows.append(x); ys.append(y); offs.append(r.lXs)
    X = pd.DataFrame(rows); return X, np.array(ys, float), np.array(offs)
def poisson(X, y, off, ridge=1e-6):
    cols = [c for c in X.columns if X[c].abs().sum() > 0]
    A = np.column_stack([np.ones(len(X))] + [X[c].values for c in cols]); th = np.zeros(A.shape[1]); th[0] = np.log(y.mean() + 1e-9) - off.mean()
    for _ in range(60):
        eta = off + A @ th; lam = np.exp(np.clip(eta, -10, 5)); W = lam
        H = A.T @ (A * W[:, None]) + ridge * np.eye(A.shape[1]); g = A.T @ (y - lam)
        step = np.linalg.solve(H, g); th += step
        if np.abs(step).max() < 1e-9: break
    cov = np.linalg.inv(A.T @ (A * np.exp(off + A @ th)[:, None]))
    return {c: (th[j + 1], np.sqrt(cov[j + 1, j + 1])) for j, c in enumerate(cols)}
def show(df, lab):
    if len(df) < 60: print(f'   {lab}: n{len(df)} (λιγα)'); return
    X, y, off = design(df); res = poisson(X, y, off)
    cells = []
    for k, nm in (('t_FotMob', 'δυναμη FotMob'), ('t_Ben', 'δυναμη Ben'), ('t_γκολ+Elo', 'δυναμη γκολ+Elo'), ('D', 'διαφορα ΛΙΓΚΑΣ')):
        if k in res: b, s = res[k]; cells.append(f'{nm} {b:.2f}±{s:.2f}')
    print(f'   {lab:34s} n{len(df):4d} · ' + ' · '.join(cells))
print(NL + '1. ΠΟΣΟ «ΑΞΙΖΕΙ» ΚΑΘΕ ΚΟΜΜΑΤΙ ΤΗΣ ΠΡΟΒΛΕΨΗΣ (β: 1 = σωστο · <1 = φουσκωμενο · >1 = συμπιεσμενο)')
show(R, 'ΟΛΑ τα ευρωπαικα')
for c in ('Α', 'Β', 'Γ'): show(R[R.cat == c], f'κατηγορια {c}')
for cm in ('ChampionsLeague', 'EuropaLeague', 'ConferenceLeague'):
    show(R[R.comp == cm], f'{cm}')
    show(R[(R.comp == cm) & (R.cat != 'Α')], f'   {cm} μονο Β+Γ')
# ---------- 2. Μετατροπη Elo ----------
print(NL + '2. Η ΜΕΤΑΤΡΟΠΗ Elo → ΔΥΝΑΜΗ: σε ομαδες ΜΕ δικα τους δεδομενα (FotMob/Ben), δυναμη πραγματικη (μηχανη) vs αυτη που θα εδινε το Elo')
C = []
for r in B_ALL.itertuples():
    eh, ea = ELO_MID.get(str(r.mid), (np.nan, np.nan))
    for src_, lg, at, lk, el in ((r.src_h, r.lg_h, r.att_h, r.leak_h, eh), (r.src_a, r.lg_a, r.att_a, r.leak_a, ea)):
        try: el = float(el)
        except (TypeError, ValueError): continue
        if src_ == 'goals' or np.isnan(el) or lg not in POFF: continue
        C.append(dict(src=src_, lg=lg, el=el, y=RHO * s_player(lg) + 0.5 * (at - lk)))
C = pd.DataFrame(C).drop_duplicates(['lg', 'el', 'y']); C['pred'] = A_CAL + B_CAL * C.el / 100
TOP = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}
C['grp'] = np.where(C.lg.isin(TOP), 'top-5', np.where(C.src == 'griffis', 'Ben λιγκες', 'αλλες FotMob λιγκες'))
print(f'   συνολο n{len(C)} · R² {np.corrcoef(C.el, C.y)[0, 1] ** 2:.2f} · κλιση συνολικη {B_CAL:.3f} ανα 100 Elo')
for g, x in C.groupby('grp'):
    if len(x) < 20: continue
    b = np.polyfit(x.el / 100, x.y, 1)[0]
    print(f'   {g:22s} n{len(x):4d} · κλιση εντος ομαδας {b:.3f} (vs {B_CAL:.3f}) · μεσο λαθος (πραγμ − Elo) {(x.y - x.pred).mean():+.3f}')
q = pd.qcut(C.el, 5)
print('   ανα επιπεδο Elo (ολες): ' + ' · '.join(f'{int(k.left)}-{int(k.right)}: λαθος {(x.y - x.pred).mean():+.3f} (n{len(x)})' for k, x in C.groupby(q, observed=True)))
R.to_pickle('nonfm_rating_decomp_rows.pkl')
# ---------- 3. ΤΙ ΜΕΝΕΙ ΣΤΗΝ ΤΕΛΙΚΗ (LIVE) ΠΡΟΒΛΕΨΗ ----------
# Η τελικη προβλεψη (euro_v6_preds: + περσινα ευρωπαικα στο prior, γ λιγκας, κ UCL) εχει επιπλεον στρωματα. Poisson με OFFSET = log τελικης
# προβλεψης και τα ιδια κομματια ως επιπλεον μεταβλητες: συντελεστης 0 = η τελικη προβλεψη τα εχει σωστα · αρνητικος = ΑΚΟΜΑ φουσκωμενο.
import pickle as _pk
_V = _pk.load(open('euro_v6_preds.pkl', 'rb')); LV = {str(m): (a, b) for m, a, b in zip(_V['mids'], _V['lh'], _V['la'])}
R['mid'] = R.mid.astype(str); R2 = R[R.mid.isin(LV)].copy()
R2['lh'] = [LV[m][0] for m in R2.mid]; R2['la'] = [LV[m][1] for m in R2.mid]; R2 = R2[(R2.lh > 0) & (R2.la > 0)]
def design2(df):
    rows = []; ys = []; offs = []
    for r in df.itertuples():
        for y, lam, t_own, s_own, t_opp, s_opp, sgnD in ((r.gh, r.lh, r.th, r.sh, r.ta, r.sa, 1), (r.ga, r.la, r.ta, r.sa, r.th, r.sh, -1)):
            x = {f't_{s}': 0.0 for s in SRC}
            x[f't_{s_own}'] += t_own / 2; x[f't_{s_opp}'] -= t_opp / 2; x['D'] = sgnD * r.D
            rows.append(x); ys.append(y); offs.append(np.log(lam))
    return pd.DataFrame(rows), np.array(ys, float), np.array(offs)
def show2(df, lab):
    if len(df) < 60: print(f'   {lab}: n{len(df)} (λιγα)'); return
    X, y, off = design2(df); res = poisson(X, y, off)
    print(f'   {lab:34s} n{len(df):4d} · ' + ' · '.join(f'{nm} {res[k][0]:+.2f}±{res[k][1]:.2f}' for k, nm in
          (('t_FotMob', 'δυναμη FotMob'), ('t_Ben', 'δυναμη Ben'), ('t_γκολ+Elo', 'δυναμη γκολ+Elo'), ('D', 'διαφορα ΛΙΓΚΑΣ')) if k in res))
print(NL + '3. ΣΤΗΝ ΤΕΛΙΚΗ (LIVE) ΠΡΟΒΛΕΨΗ: ποσο ΑΚΟΜΑ «φουσκωνει» καθε κομματι (0 = σωστο · −0.40 = 40% φουσκωμενο · + = συμπιεσμενο)')
show2(R2, 'ΟΛΑ')
for c in ('Α', 'Β'): show2(R2[R2.cat == c], f'κατηγορια {c}')
for cm in ('ChampionsLeague', 'EuropaLeague', 'ConferenceLeague'):
    show2(R2[R2.comp == cm], cm)
    for c in ('Α', 'Β'): show2(R2[(R2.comp == cm) & (R2.cat == c)], f'   {cm} {c}')
# ---------- 4. ROTATION; (νεα μορφη, ενδεκαδες FotMob) ----------
# Αν η «δυναμη ομαδας» αξιζει λιγοτερο στο UEL/UECL επειδη οι δυνατες ομαδες ξεκουραζουν παικτες, τοτε οταν η ομαδα παιζει με ΠΛΗΡΗ ενδεκαδα
# το κομματι πρεπει να ειναι σωστο (≈0) και το φουσκωμα να βρισκεται στα ματς με rotation.
EUM = {}
for f in glob.glob('data_Europe_*.json'):
    for mid_, m_ in json.load(open(f, encoding='utf-8')).items(): EUM[str(mid_)] = m_
RT = pd.read_pickle('euro_rotation_rows.pkl'); RT['day'] = pd.to_datetime(RT.ko).dt.strftime('%Y-%m-%d'); RT = RT.drop_duplicates(['team', 'day'])
ROT = {(r.team, r.day): bool(r.rot) for r in RT.itertuples()}
def rot_of(mid, side):
    m = EUM.get(str(mid))
    if not m: return None
    d = datetime.strptime(m['date'], '%a, %b %d, %Y, %H:%M UTC').strftime('%Y-%m-%d')
    return ROT.get((m[side]['name'], d))
R3 = R2[R2.sea.isin(['2425', '2526'])].copy()
R3['rh'] = [rot_of(m, 'home') for m in R3.mid]; R3['ra'] = [rot_of(m, 'away') for m in R3.mid]
R3 = R3[R3.rh.notna() | R3.ra.notna()]
def design3(df):
    rows = []; ys = []; offs = []
    for r in df.itertuples():
        for y, lam, t_own, r_own, t_opp, r_opp, sgnD in ((r.gh, r.lh, r.th, r.rh, r.ta, r.ra, 1), (r.ga, r.la, r.ta, r.ra, r.th, r.rh, -1)):
            x = {k: 0.0 for k in ('own_full', 'own_rot', 'own_unk', 'opp_full', 'opp_rot', 'opp_unk')}
            x['own_' + ('unk' if r_own is None else ('rot' if r_own else 'full'))] += t_own / 2
            x['opp_' + ('unk' if r_opp is None else ('rot' if r_opp else 'full'))] -= t_opp / 2
            x['D'] = sgnD * r.D
            rows.append(x); ys.append(y); offs.append(np.log(lam))
    return pd.DataFrame(rows), np.array(ys, float), np.array(offs)
print(NL + '4. ROTATION (νεα μορφη): ποσο φουσκωνει η «δυναμη ομαδας» στην τελικη προβλεψη, ανα ενδεκαδα (0 = σωστο)')
print('   «δικη» = η δυναμη της ομαδας στα γκολ που ΒΑΖΕΙ · «αντιπαλου» = η δυναμη του αντιπαλου στα γκολ που ΤΡΩΕΙ η ομαδα')
for lab, m_ in (('UEL + UECL', R3.comp.isin(['EuropaLeague', 'ConferenceLeague'])), ('UCL', R3.comp == 'ChampionsLeague')):
    df = R3[m_]; X, y, off = design3(df); res = poisson(X, y, off)
    nrot = int((df.rh == True).sum() + (df.ra == True).sum()); nfull = int((df.rh == False).sum() + (df.ra == False).sum())
    print(f'   {lab:12s} n{len(df)} ματς (πλευρες: rotation {nrot} · πληρης {nfull}) · ' + ' · '.join(
        f'{nm} {res[k][0]:+.2f}±{res[k][1]:.2f}' for k, nm in (('own_full', 'δικη, ΠΛΗΡΗΣ'), ('own_rot', 'δικη, ROTATION'),
                                                               ('opp_full', 'αντιπαλου ΠΛΗΡΗΣ'), ('opp_rot', 'αντιπαλου ROTATION')) if k in res))
# ---------- 5. «ΜΕΓΑΛΟ ΨΑΡΙ ΣΕ ΜΙΚΡΗ ΛΙΜΝΗ»; φουσκωμα της δυναμης ομαδας ανα επιπεδο λιγκας ----------
TOP5 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}
sv = {lg: s_v4(lg) for lg in set(R2.lgh) | set(R2.lga)}
mid_cut = np.median([sv[lg] for lg in sv if lg not in TOP5])
def tier(lg): return 'top5' if lg in TOP5 else ('mid' if sv[lg] >= mid_cut else 'small')
def design5(df):
    rows = []; ys = []; offs = []
    for r in df.itertuples():
        for y, lam, t_own, l_own, t_opp, l_opp, sgnD in ((r.gh, r.lh, r.th, r.lgh, r.ta, r.lga, 1), (r.ga, r.la, r.ta, r.lga, r.th, r.lgh, -1)):
            x = {f'{a}_{b}': 0.0 for a in ('own', 'opp') for b in ('top5', 'mid', 'small')}
            x[f'own_{tier(l_own)}'] += t_own / 2; x[f'opp_{tier(l_opp)}'] -= t_opp / 2; x['D'] = sgnD * r.D
            rows.append(x); ys.append(y); offs.append(np.log(lam))
    return pd.DataFrame(rows), np.array(ys, float), np.array(offs)
print(NL + f'5. ΦΟΥΣΚΩΜΑ «ΔΥΝΑΜΗΣ ΟΜΑΔΑΣ» ανα ΕΠΙΠΕΔΟ ΛΙΓΚΑΣ της ομαδας (τελικη προβλεψη, 0 = σωστο) · top-5 / μεσαιες / μικρες λιγκες')
print('   μεσαιες: ' + ', '.join(sorted(lg for lg in sv if tier(lg) == 'mid')))
print('   μικρες:  ' + ', '.join(sorted(lg for lg in sv if tier(lg) == 'small')))
for lab, m_ in (('UEL + UECL', R2.comp.isin(['EuropaLeague', 'ConferenceLeague'])), ('UCL', R2.comp == 'ChampionsLeague'), ('ΟΛΑ', R2.comp.notna())):
    X, y, off = design5(R2[m_]); res = poisson(X, y, off)
    print(f'   {lab:12s} · ' + ' · '.join(f'{nm} {res[k][0]:+.2f}±{res[k][1]:.2f}' for k, nm in
          (('own_top5', 'δικη top-5'), ('own_mid', 'δικη μεσαιας'), ('own_small', 'δικη μικρης'),
           ('opp_top5', 'αντιπ. top-5'), ('opp_mid', 'αντιπ. μεσαιας'), ('opp_small', 'αντιπ. μικρης')) if k in res))
# εξαπλωση της δυναμης ομαδας μεσα σε καθε επιπεδο (ποσο «απλωμενες» ειναι οι βαθμολογιες)
T_ = pd.concat([R2[['th', 'lgh']].rename(columns={'th': 't', 'lgh': 'lg'}), R2[['ta', 'lga']].rename(columns={'ta': 't', 'lga': 'lg'})])
T_['tier'] = T_.lg.map(tier)
print('   ευρος «δυναμης ομαδας» (τυπικη αποκλιση των t των ομαδων που παιζουν Ευρωπη): ' + ' · '.join(f'{k} {x.t.std():.2f} (μεσος {x.t.mean():+.2f})' for k, x in T_.groupby('tier')))
