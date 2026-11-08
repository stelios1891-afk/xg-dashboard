"""euro_elo_blend_test.py — 15/10/2026 (Στελιος: «πως θα το διορθωνες — με το Elo καθε ομαδας; προσωπικο Elo;»).
ΛΟΓΙΚΗ: το ClubElo ειναι ΑΤΟΜΙΚΟ rating καθε ομαδας, κοινο για ολη την Ευρωπη, και χτιζεται απο αποτελεσματα ΜΕ ΑΝΑΜΕΝΟΜΕΝΟ: μια νικη κοντρα σε
αδυναμο αντιπαλο δινει ελαχιστους ποντους → η «κυριαρχια κοντρα στους αδυναμους» ΔΕΝ φουσκωνει το Elo οπως φουσκωνει το δικο μας εγχωριο rating.
Ολα τα ευρωπαικα 2223-2526 (Elo ημερας ματς απο clubelo_cache, καλυψη 92%), live λ. Τρεις εκδοχες ΔΙΑΦΟΡΑΣ γκολ (συνολο γκολ = του μοντελου):
  Μ  σημερινο μοντελο
  E  ΜΟΝΟ Elo: διαφορα = h + k·(Elo γηπ − Elo φιλ)/100   (h, k απο τις αλλες 3 σεζον)
  ME μιξη: διαφορα = (1−w)·μοντελο + w·Elo                (h, k, w απο τις αλλες 3 σεζον)
LOSO ανα σεζον, χωριστα ανα διοργανωση (UEL κυριο). ΠΡΟ-ΔΗΛΩΜΕΝΑ: Κ1 Δlog-lik γκολ > 0 σε ≥3/4 σεζον ΚΑΙ RPS καλυτερο · Κ2 η «σκαλα κυριαρχιας»
(λαθος ομαδων εκτος top-5: λιγο κυριαρχες − πολυ κυριαρχες) μικραινει. + αναφορα: αγορα κλεισιματος. Διαγνωστικο.
"""
import sys, os, json, glob, pickle
NL = chr(10)
_EO = sys.stdout
src = open('uecl_full_review.py', encoding='utf-8').read().split('# ================= Α. ΒΑΘΜΟΝΟΜΗΣΗ')[0]
sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(src); sys.stdout = _EO; sys.stdout.reconfigure(encoding='utf-8')
CP = pickle.load(open('euro_components.pkl', 'rb'))
LG = {str(m): (a, b) for m, a, b in zip(V6['mids'], V6['lg_h'], V6['lg_a'])}
TOP5 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}
rows = []
for i in range(len(MIDS)):
    if COMP[i] not in ('ChampionsLeague', 'EuropaLeague', 'ConferenceLeague') or LH_N[i] <= 0: continue
    c = CP.get(str(MIDS[i]))
    if not c or not np.isfinite(c['elh']) or not np.isfinite(c['ela']): continue
    s = snap_ah(MIDS[i], 'Crown', 0) or snap_ah(MIDS[i], 'SBOBET', 0)
    lg = LG.get(str(MIDS[i]), ('?', '?'))
    rows.append(dict(i=i, comp=COMP[i], sea=SEA[i], lh=LH_N[i], la=LA_N[i], de=(c['elh'] - c['ela']) / 100, gh=GH[i], ga=GA[i], gd=GD[i],
                     th=c['th'], ta=c['ta'], lgh=lg[0], lga=lg[1], mk=implied_margin(i, *s) if s else np.nan))
A = pd.DataFrame(rows)
print(f'Δειγμα: {len(A)} ευρωπαικα ματς με Elo και των 2 · ' + ' '.join(f'{k}:{v}' for k, v in A.comp.value_counts().items()))
HG = np.round(np.arange(0.0, 0.61, 0.05), 2); KG = np.round(np.arange(0.0, 1.21, 0.05), 2); WG = np.round(np.arange(0.0, 1.01, 0.1), 2)
def lam(x, h, k, w):
    T = x.lh.values + x.la.values; mm = x.lh.values - x.la.values; me = h + k * x.de.values
    m = (1 - w) * mm + w * me
    return np.maximum((T + m) / 2, .05), np.maximum((T - m) / 2, .05)
def ll(x, lh, la): return float(np.sum(x.gh.values * np.log(lh) - lh + x.ga.values * np.log(la) - la))
def fit(x, ver):
    best, bp = -1e18, (0, 0, 0)
    for h in (HG if ver != 'M' else [0]):
        for k in (KG if ver != 'M' else [0]):
            for w in ({'M': [0.0], 'E': [1.0], 'ME': WG}[ver]):
                v = ll(x, *lam(x, h, k, w))
                if v > best: best, bp = v, (h, k, w)
    return bp
def rps(lh, la, gd):
    out = []
    for a, b, g in zip(lh, la, gd):
        D = sdist(a, b); p1 = sum(p for kk, p in D.items() if kk > 0); px = D.get(0, 0)
        out.append(((p1 - (g > 0)) ** 2 + (p1 + px - (g >= 0)) ** 2) / 2)
    return np.array(out)
for cm, lab in (('EuropaLeague', 'EUROPA'), ('ConferenceLeague', 'CONFERENCE'), ('ChampionsLeague', 'CHAMPIONS')):
    x = A[A.comp == cm].reset_index(drop=True); seas = sorted(x.sea.unique())
    P = {v: (np.zeros(len(x)), np.zeros(len(x))) for v in ('M', 'E', 'ME')}; PAR = {v: {} for v in P}
    for v in P:
        for s in seas:
            tr = x[x.sea != s]; te = x.sea == s; p = fit(tr, v); PAR[v][s] = p
            a, b = lam(x[te], *p); P[v][0][te.values] = a; P[v][1][te.values] = b
    R = {v: rps(*P[v], x.gd.values) for v in P}
    ok = x.mk.notna()
    Tm = x.lh + x.la; mkh = np.maximum((Tm + x.mk) / 2, .05); mka = np.maximum((Tm - x.mk) / 2, .05)
    rmk = rps(mkh[ok].values, mka[ok].values, x.gd[ok].values)
    print(f'{NL}===== {lab}: {len(x)} ματς')
    print('   παραμετροι (αλλες 3 σεζον): ' + ' · '.join(f'{s[2:]}: Elo k {PAR["ME"][s][1]:.2f} εδρα {PAR["ME"][s][0]:.2f} βαρος Elo w {PAR["ME"][s][2]:.1f}' for s in seas))
    for v, nm in (('M', 'σημερινο μοντελο'), ('E', 'ΜΟΝΟ Elo'), ('ME', 'μιξη μοντελο+Elo')):
        d = {s: ll(x[x.sea == s], P[v][0][(x.sea == s).values], P[v][1][(x.sea == s).values]) - ll(x[x.sea == s], P['M'][0][(x.sea == s).values], P['M'][1][(x.sea == s).values]) for s in seas}
        npos = sum(t > 0 for t in d.values())
        k1 = v != 'M' and npos >= 3 and R[v].mean() < R['M'].mean()
        # σκαλα κυριαρχιας: ομαδες εκτος top-5
        sides = []
        for k_, r in x.iterrows():
            m_ = P[v][0][k_] - P[v][1][k_]
            for sg, t, lg in ((1, r.th, r.lgh), (-1, r.ta, r.lga)):
                if lg not in TOP5: sides.append((t, sg * (r.gd - m_)))
        S = pd.DataFrame(sides, columns=['t', 'e'])
        lo = S[S.t < .3].e.mean(); hi = S[S.t >= .9].e.mean()
        print(f'   {nm:18s} RPS {R[v].mean():.4f} · Δlog-lik ' + ' '.join(f'{s[2:]}:{t:+.1f}' for s, t in d.items()) +
              f'{" · Κ1 " + ("✓" if k1 else "✗") if v != "M" else ""} │ σκαλα κυριαρχιας: λιγο κυριαρχες {lo:+.2f} / πολυ κυριαρχες {hi:+.2f} → ευρος {lo - hi:.2f}')
    print(f'   (αγορα κλεισιματος RPS {rmk.mean():.4f} στα {ok.sum()} ματς με τιμη · μοντελο εκει {R["M"][ok.values].mean():.4f} · μιξη {R["ME"][ok.values].mean():.4f})')
