"""euro_league_team_history.py — 14/10/2026 (Στελιος: «δεν μου αρεσει να παιρνουμε 5 σεζον και να βαζουμε το νουμερο που μας βολευει — θελω
ΙΣΤΟΡΙΚΗ αναλυση ολων των ομαδων και χωρων: ποιες χωρες υπερεκτιμαμε λογω διαφορας λιγκας και ποιανων πρωταθληματων η εγχωρια δυναμη
υπερεκτιμαται στην Ευρωπη · τα τελικα xG δεν λενε πολλα — η ομαδα που χανει πλησιαζει λογω game state»).
ΟΛΑ τα ευρωπαικα (UCL/UEL/UECL) 2223-2526, ΟΛΕΣ οι κατηγοριες, live λ (harness: w=2, γ, κ UCL). Απο τη σκοπια ΚΑΘΕ ομαδας:
  λαθος = πραγματικο − προβλεψη μοντελου (διαφορα γκολ) · + = το μοντελο ΥΠΟΤΙΜΑ τις ομαδες της λιγκας, − = ΥΠΕΡΤΙΜΑ
  ΜΕΤΡΑ: (1) ΓΚΟΛ (κυριο) · (2) xG ΜΟΝΟ ΣΕ ΙΣΟΠΑΛΙΑ (ανα 90′, οσο το σκορ ειναι ισο → χωρις game state), σχετικα με τον μεσο ολων
          · και το ιδιο λαθος για την ΑΓΟΡΑ (κλεισιμο) — αν η αγορα κανει το ιδιο λαθος, δεν ειναι εκμεταλλευσιμο
  ΑΝΑ ΛΙΓΚΑ: (α) μεσο λαθος = λαθος ΕΠΙΠΕΔΟΥ ΛΙΓΚΑΣ (η λιγκα «ανεβαινει/κατεβαινει» λαθος)
             (β) κλιση λαθους ως προς τη δυναμη της ομαδας μεσα στη λιγκα της = ΜΕΤΑΦΟΡΑ ΕΓΧΩΡΙΑΣ ΔΥΝΑΜΗΣ (− = οι κορυφαιες της λιγκας υπερτιμωνται)
  ΣΤΑΘΕΡΟΤΗΤΑ: 2223-2324 vs 2425-2526 — αν το λαθος μιας λιγκας ΕΠΙΜΕΝΕΙ, ειναι πραγματικο (μετρησιμο ανα λιγκα)· αν οχι, θορυβος.
Περιγραφικο — ΔΕΝ ρυθμιζει τιποτα.
"""
import sys, os, json, glob, pickle
NL = chr(10)
_LO = sys.stdout
src = open('uecl_full_review.py', encoding='utf-8').read().split('# ================= Α. ΒΑΘΜΟΝΟΜΗΣΗ')[0]
sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(src); sys.stdout = _LO; sys.stdout.reconfigure(encoding='utf-8')
COMPS = pickle.load(open('euro_components.pkl', 'rb'))
LG = {str(m): (a, b) for m, a, b in zip(V6['mids'], V6['lg_h'], V6['lg_a'])}
EUM = {}
for f in glob.glob('data_Europe_*.json'):
    for k, m in json.load(open(f, encoding='utf-8')).items(): EUM[str(k)] = m
def level_xg(m):
    """xG γηπ/φιλ οσο το σκορ ειναι ισο + λεπτα ισοπαλιας (απο τα σουτ: λεπτο & γκολ)."""
    hid = int(m['home']['id']); sh = sorted([s for s in (m.get('shots') or []) if s.get('xg') is not None], key=lambda s: s.get('min') or 0)
    if not sh: return None
    gh = ga = 0; xh = xa = 0.0; lvl_min = 0.0; last = 0; level = True
    for s in sh:
        t = min(s.get('min') or 0, 95)
        if level: lvl_min += max(t - last, 0)
        last = t
        if gh == ga:
            if int(s['tid']) == hid: xh += s['xg']
            else: xa += s['xg']
        if s.get('goal'):
            if int(s['tid']) == hid: gh += 1
            else: ga += 1
        level = gh == ga
    if level: lvl_min += max(93 - last, 0)
    return xh, xa, max(lvl_min, 1.0)
rows = []
for i in range(len(MIDS)):
    if COMP[i] not in ('ChampionsLeague', 'EuropaLeague', 'ConferenceLeague') or LH_N[i] <= 0: continue
    mid = str(MIDS[i]); c = COMPS.get(mid); lg = LG.get(mid)
    if not c or not lg: continue
    s = snap_ah(MIDS[i], 'Crown', 0) or snap_ah(MIDS[i], 'SBOBET', 0)
    km = implied_margin(i, *s) if s else np.nan
    lx = level_xg(EUM[mid]) if mid in EUM else None
    for sg, t_own, lg_own, lg_opp in ((1, c['th'], lg[0], lg[1]), (-1, c['ta'], lg[1], lg[0])):
        rows.append(dict(mid=mid, D=sg * c['D'], t_opp=(c['ta'] if sg == 1 else c['th']), sea=SEA[i], comp=COMP[i], lg=lg_own, opp_lg=lg_opp, t=t_own, mdl=sg * (LH_N[i] - LA_N[i]), mk=sg * km, gd=sg * GD[i],
                         lvl=(sg * (lx[0] - lx[1]) * 90 / lx[2]) if lx else np.nan, w=(lx[2] / 90) if lx else 0.0))
X = pd.DataFrame(rows)
X['r'] = X.gd - X.mdl; X['rk'] = X.gd - X.mk
# xG ισοπαλιας: σχετικο λαθος (αφαιρω τη γενικη σχεση μοντελου ↔ xG ισοπαλιας με μια ευθεια σε ΟΛΑ τα δεδομενα)
ok = X.lvl.notna() & (X.w > 0.2)
b = np.polyfit(X.loc[ok, 'mdl'], X.loc[ok, 'lvl'], 1, w=X.loc[ok, 'w'])
X['rl'] = np.where(ok, X.lvl - np.polyval(b, X.mdl), np.nan)
print(f'Δειγμα: {len(X) // 2} ευρωπαικα ματς · {len(X)} πλευρες ομαδων · {X.lg.nunique()} λιγκες')
print(f'xG ισοπαλιας: μεσος χρονος σε ισο σκορ {X.w.mean() * 90:.0f}′ · σχεση με μοντελο: xG ισοπαλιας/90 = {b[1]:+.2f} + {b[0]:.2f} × διαφορα μοντελου')
TOP5 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}
se = lambda v: v.std() / np.sqrt(max(len(v), 1))
def slope(x, col):
    y = x.dropna(subset=[col])
    if len(y) < 12 or y.t.std() < 1e-6: return np.nan, np.nan
    tc = y.t - y.t.mean(); bb = np.polyfit(tc, y[col], 1); e = y[col] - np.polyval(bb, tc)
    return bb[0], np.sqrt((e ** 2).sum() / (len(y) - 2) / (tc ** 2).sum())
print(NL + '1) ΑΝΑ ΛΙΓΚΑ (≥30 πλευρες) — λαθος = πραγματικο − προβλεψη απο τη σκοπια των ομαδων της λιγκας (+ υποτιμαμε / − υπερτιμαμε)')
print(f'   {"λιγκα":26s} {"πλευρες":>7s} │ {"ΕΠΙΠΕΔΟ: γκολ":>16s} {"xG-ισοπ.":>14s} {"ΑΓΟΡΑ":>14s} │ {"ΜΕΤΑΦΟΡΑ κλιση (γκολ)":>22s} │ σταθεροτητα επιπεδου 22-24 / 24-26')
L = []
for lg, x in X.groupby('lg'):
    if len(x) < 30: continue
    bs, bse = slope(x, 'r'); e1 = x[x.sea.isin(['2223', '2324'])].r; e2 = x[x.sea.isin(['2425', '2526'])].r
    L.append(dict(lg=lg, n=len(x), r=x.r.mean(), rse=se(x.r), rl=x.rl.mean(), rlse=se(x.rl.dropna()), rk=x.rk.mean(), rkse=se(x.rk.dropna()),
                  bs=bs, bse=bse, e1=e1.mean() if len(e1) >= 10 else np.nan, e2=e2.mean() if len(e2) >= 10 else np.nan, n1=len(e1), n2=len(e2), top5=lg in TOP5))
L = pd.DataFrame(L).sort_values('r')
for r in L.itertuples():
    flag = ' ◄' if abs(r.r) > 2 * r.rse else ''
    print(f'   {r.lg[:26]:26s} {r.n:7d} │ {r.r:+6.2f} ±{r.rse:.2f}{flag:2s} {r.rl:+6.2f} ±{r.rlse:.2f} {r.rk:+6.2f} ±{r.rkse:.2f} │ {r.bs:+8.2f} ±{r.bse:.2f}       │ '
          f'{r.e1:+.2f} (n{r.n1}) / {r.e2:+.2f} (n{r.n2})')
v = L.dropna(subset=['e1', 'e2']); wts = 1 / (1 / v.n1 + 1 / v.n2)
cw = np.cov(v.e1, v.e2, aweights=wts)[0, 1] / np.sqrt(np.cov(v.e1, v.e1, aweights=wts)[0, 1] * np.cov(v.e2, v.e2, aweights=wts)[0, 1])
print(f'{NL}   ΣΤΑΘΕΡΟΤΗΤΑ λαθους επιπεδου λιγκας απο 2223-2324 σε 2425-2526: συσχετιση {cw:+.2f} ({len(v)} λιγκες) — κοντα στο 0 = θορυβος, θετικη = πραγματικο')
print(NL + '2) ΜΕΤΑΦΟΡΑ ΕΓΧΩΡΙΑΣ ΔΥΝΑΜΗΣ — κλιση λαθους (γκολ) ως προς τη δυναμη της ομαδας μεσα στη λιγκα της (0 = μεταφερεται σωστα · − = οι κορυφαιες υπερτιμωνται)')
for lab, m_ in (('ΟΛΕΣ', X.lg.notna()), ('top-5', X.lg.isin(TOP5)), ('εκτος top-5', ~X.lg.isin(TOP5))):
    for cm in (None, 'ChampionsLeague', 'EuropaLeague', 'ConferenceLeague'):
        x = X[m_] if cm is None else X[m_ & (X.comp == cm)]
        bg, sg_ = slope(x, 'r'); bl, sl_ = slope(x, 'rl'); bk, sk_ = slope(x, 'rk')
        print(f'   {lab:12s} {(cm or "ολες")[:16]:16s} n{len(x):5d} · μοντελο: γκολ {bg:+.2f}±{sg_:.2f} · xG-ισοπ. {bl:+.2f}±{sl_:.2f} │ ΑΓΟΡΑ γκολ {bk:+.2f}±{sk_:.2f}')
# σταθεροτητα κλισης ανα λιγκα
s1 = {lg: slope(x[x.sea.isin(['2223', '2324'])], 'r')[0] for lg, x in X.groupby('lg') if len(x) >= 40}
s2 = {lg: slope(x[x.sea.isin(['2425', '2526'])], 'r')[0] for lg, x in X.groupby('lg') if len(x) >= 40}
kk = [k for k in s1 if np.isfinite(s1[k]) and np.isfinite(s2.get(k, np.nan))]
print(f'   ΣΤΑΘΕΡΟΤΗΤΑ κλισης ανα λιγκα (2223-2324 vs 2425-2526, {len(kk)} λιγκες): συσχετιση {np.corrcoef([s1[k] for k in kk], [s2[k] for k in kk])[0, 1]:+.2f}'
      f' · μεση κλιση {np.mean([s1[k] for k in kk]):+.2f} → {np.mean([s2[k] for k in kk]):+.2f}')
X.to_pickle('euro_league_team_history_rows.pkl')
