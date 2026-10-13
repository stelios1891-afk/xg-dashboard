"""team_strength_domestic_check.py — 13/10/2026 (Στελιος: «αν στο πρωταθλημα ειναι +0.5 xGD/90 και στην Ευρωπη +0.15, δεν ειναι λογικο; τα ματς
ειναι πιο δυσκολα»). ΙΔΙΟ τεστ με nonfm_rating_decomp §1 (ωμη μηχανη, Poisson στα γκολ, β της «δυναμης ομαδας» t = att − leak, 1 = σωστο)
αλλα σε ΕΓΧΩΡΙΑ ματς (ιδιες λιγκες, 2223-2526, κατασταση ΠΡΙΝ το ματς). Αν εγχωρια β ≈ 1 και στην Ευρωπη ≈ 0.45 → το φουσκωμα ειναι ΕΥΡΩΠΑΪΚΟ,
οχι «θορυβος της βαθμολογιας» (ο θορυβος θα φαινοταν ΚΑΙ εγχωρια).
"""
import sys, os, random
_src = open('euro_live_projections.py', encoding='utf-8').read()
_cut = _src.index('# ================================================================ ΠΕΡΣΙΝΑ ΕΥΡΩΠΑΪΚΑ -> PRIOR')
_DEV = open(os.devnull, 'w', encoding='utf-8'); _REAL = sys.stdout; sys.stdout = _DEV
exec(_src[:_cut])
sys.stdout = _REAL; sys.stdout.reconfigure(encoding='utf-8')
random.seed(7)
EU_LGS = set(B_ALL.lg_h) | set(B_ALL.lg_a)
rows = []
for (lg, sea), hh in eng.H.items():
    if lg not in EU_LGS or sea not in ('2223', '2324', '2425', '2526') or (lg, sea) in eng.GOAL_ONLY: continue
    p = f'data_{lg}_{sea}.json'
    if not os.path.exists(p): continue
    d = json.load(open(p, encoding='utf-8')); ms = [m for m in d.values() if m.get('hs') is not None]
    random.shuffle(ms)
    for m in ms[:150]:
        dt_ = kodt(m['date'])
        if dt_ is None: continue
        hid, aid = int(m['home']['id']), int(m['away']['id'])
        sh, sa = eng.side_state(hid, dt_), eng.side_state(aid, dt_)
        if sh is None or sa is None or sh['lg'] != lg or sa['lg'] != lg: continue
        ah, lh, SLh, XLh, srh = side_terms(eng, sh, dt_, GKEYS); aa, la, SLa, XLa, sra = side_terms(eng, sa, dt_, GKEYS)
        lXs = math.log(((SLh * SLa) ** 0.5) * ((XLh * XLa) ** 0.5))
        rows.append(dict(lg=lg, src={'shots': 'FotMob', 'griffis': 'Ben'}.get(srh, srh), gh=m['hs'], ga=m['as'], th=ah - lh, ta=aa - la, lXs=lXs))
D = pd.DataFrame(rows)
def beta(df):
    y = np.r_[df.gh.values, df.ga.values].astype(float); off = np.r_[df.lXs.values, df.lXs.values]
    t = np.r_[(df.th - df.ta).values / 2, (df.ta - df.th).values / 2]; home = np.r_[np.ones(len(df)), np.zeros(len(df))]
    A = np.column_stack([np.ones(len(y)), t, home]); th = np.zeros(3)
    for _ in range(50):
        lam = np.exp(off + A @ th); H = A.T @ (A * lam[:, None]); step = np.linalg.solve(H, A.T @ (y - lam)); th += step
        if np.abs(step).max() < 1e-10: break
    se = np.sqrt(np.linalg.inv(A.T @ (A * np.exp(off + A @ th)[:, None]))[1, 1]); return th[1], se
TOP5 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}
print(f'ΕΓΧΩΡΙΑ ματς (ιδιες λιγκες με τα ευρωπαικα, 2223-2526, ως 150 ανα λιγκα-σεζον): {len(D)}')
print('β «δυναμης ομαδας» (1 = σωστο · <1 = φουσκωμενη):')
for lab, m_ in (('ΟΛΑ', D.lg.notna()), ('λιγκες FotMob', D.src == 'FotMob'), ('λιγκες Ben', D.src == 'Ben'), ('top-5', D.lg.isin(TOP5)),
                ('αλλες FotMob λιγκες', (D.src == 'FotMob') & ~D.lg.isin(TOP5))):
    b, s = beta(D[m_]); print(f'   {lab:22s} n{m_.sum():5d} · β {b:.2f} ± {s:.2f}')
print('ΣΥΓΚΡΙΣΗ (ιδια ωμη μηχανη, ευρωπαικα — nonfm_rating_decomp §1): ΟΛΑ FotMob 0.72 · Ben 0.45 · UCL 0.94 · UEL 0.45 · UECL 0.45')
