"""uel_lineup_rule2.py — 14/10/2026 (Στελιος: «το ευρημα της ενδεκαδας να ξαναγινει ΧΩΡΙΣ τα picks των φαβορι 12-36ω (να μη μετραμε 2 φορες
τα ιδια) · να λαμβανει τις τιμες 1 ωρα πριν (οταν βγαινουν οι ενδεκαδες) και κλεισιματος· αν οι τιμες δεν πεφτουν πολυ με την ανακοινωση,
μπορουμε να το ακολουθησουμε»).
ΚΑΝΟΝΑΣ (ιδιος με uel_lineup_rule_test): χαντικαπ στο ΦΑΒΟΡΙ ΑΓΟΡΑΣ (γραμμη ≤−0.25, 1.70-2.10) ΜΟΝΟ οταν η ενδεκαδα του αξιζει ≥ τ της συνηθισμενης
(αξια βασικων FotMob / διαμεσος 5 τελευταιων εγχωριων ≤45 μερες). Europa League 2223-2526, Crown & SBOBET.
ΑΦΑΙΡΟΥΝΤΑΙ τα ματς οπου ο LIVE κανονας «UEL φαβορι εντος» (μιξη 80% xG, γηπ ≤−0.5, edge ≥4% σωστα τεταρτα, 1.70-2.10, εισοδος 12-36ω) θα ειχε ηδη pick
στον γηπεδουχο (ιδιο βιβλιο). Τιμες: 2ω πριν (ΠΡΙΝ τις ενδεκαδες) · 1ω πριν (≈ οταν βγαινουν) · κλεισιμο.
ΠΡΟ-ΔΗΛΩΜΕΝΑ (ιδια με πριν, στην τιμη 1ω): Κ1 LOSO (τ ∈ 0.90…1.00) εκτος δειγματος >0 ΚΑΙ θετικο στα 2 βιβλια · Κ2 ≥3/4 σεζον θετικες ΚΑΙ οι 2 νεας
μορφης · Κ3 φαβορι με rotation (<0.90) χειροτερα. + ΚΙΝΗΣΗ ΤΙΜΗΣ με την ανακοινωση (2ω → 1ω → κλεισιμο) για τα picks του κανονα.
"""
import sys, pickle
src = open('uel_lineup_rule_test.py', encoding='utf-8').read().split('\nrows = []\n')[0]
exec(src)
def implied_margin(i, L, oh, oa):
    q = (1 / oh) / (1 / oh + 1 / oa); T = LH_N[i] + LA_N[i]; lo, hi = -5.0, 5.0
    for _ in range(26):
        M = (lo + hi) / 2
        pw, pp = cover_q(sdist(max((T + M) / 2, .05), max((T - M) / 2, .05)), 1, L)
        if pw / max(1 - pp, 1e-9) < q: lo = M
        else: hi = M
    return (lo + hi) / 2
# ---------- picks του live κανονα «UEL φαβορι εντος» ----------
D8 = pickle.load(open('euro_blend_dump_0.8.pkl', 'rb')); I8 = {str(m): k for k, m in enumerate(D8['MIDS'])}
HF = set()
for i in range(len(MIDS)):
    if COMP[i] != 'EuropaLeague' or str(MIDS[i]) not in I8: continue
    k = I8[str(MIDS[i])]
    if not D8['FM'][k]: continue
    dist = sdist(D8['LH'][k], D8['LA'][k])
    for bk in ('Crown', 'SBOBET'):
        for h in (36, 24, 18, 12):
            s = snap_ah(MIDS[i], bk, h)
            if not s: continue
            L, oh, oa = s
            if L <= -0.5 and 1.70 <= oh <= 2.10 and edge(*cover_q(dist, 1, L), oh) >= .04:
                HF.add((i, bk)); break
print(f'Live κανονας «UEL φαβορι εντος» θα ειχε pick σε {len({i for i, _ in HF})} ματς (ανα βιβλιο: {len(HF)}) — ΑΦΑΙΡΟΥΝΤΑΙ')
# ---------- φαβορι αγορας με την τιμη 1ω, και οι τιμες 2ω / κλεισιμο για τα ιδια ----------
rows = []
for i in range(len(MIDS)):
    if COMP[i] != 'EuropaLeague': continue
    j = VI.get(str(MIDS[i]))
    if j is None: continue
    ko = pd.Timestamp(V6['date'][j])
    rh, ra = ratio(MIDS[i], 'h', ko), ratio(MIDS[i], 'a', ko)
    for bk in ('Crown', 'SBOBET'):
        s1 = snap_ah(MIDS[i], bk, 1)
        if not s1: continue
        L, oh, oa = s1
        if abs(L) < 0.2: continue
        side = 1 if L < 0 else -1; ln = L if side == 1 else -L; o = oh if side == 1 else oa
        if not (1.70 <= o <= 2.10): continue
        r = rh if side == 1 else ra
        if not np.isfinite(r): continue
        if side == 1 and (i, bk) in HF: continue                     # ηδη pick του live κανονα
        def at(h):
            s = snap_ah(MIDS[i], bk, h)
            if not s: return np.nan, np.nan, np.nan
            L2, a, b = s; l2 = L2 if side == 1 else -L2; o2 = a if side == 1 else b
            # «διαφορα που δικαιολογει η τιμη» (σκοπια φαβορι), για να μετρηθει η κινηση
            m2 = side * implied_margin(i, L2, a, b) if LH_N[i] > 0 else np.nan
            return picks.settle(GD[i], side, l2, o2), m2, o2
        p2, m2, o2 = at(2); p1, m1, _ = at(1); p0, m0, o0 = at(0)
        rows.append(dict(sea=SEA[i], bk=bk, ratio=r, home=side == 1, p2=p2, p1=p1, p0=p0, m2=m2, m1=m1, m0=m0, o1=o, o0=o0, ln=ln))
B = pd.DataFrame(rows)
def cc(x, col):
    x = x.dropna(subset=[col])
    if len(x) < 6: return '   —'
    m = x.groupby('bk')[col].mean(); n = x.groupby('bk').size().mean(); ps = x.groupby('sea')[col].mean()
    return f'{n:4.0f} picks {100 * m.mean():+6.1f}% [C {100 * m.get("Crown", np.nan):+.0f}/S {100 * m.get("SBOBET", np.nan):+.0f}] (' + ' '.join(f'{s[2:]} {100 * v:+.0f}' for s, v in ps.items()) + ')'
TAUS = (0.90, 0.93, 0.95, 0.97, 1.00)
print(NL + 'EUROPA LEAGUE — φαβορι αγορας ≤−0.25, 1.70-2.10, ΧΩΡΙΣ τα picks του κανονα «φαβορι εντος 12-36ω»')
print(f'   {"ενδεκαδα":16s} {"τιμη 2ω πριν (πριν την ενδεκαδα)":44s} {"τιμη 1ω πριν (ανακοινωση)":44s} κλεισιμο')
for tau in TAUS:
    x = B[B.ratio >= tau]
    print(f'   ≥{tau:.2f}           {cc(x, "p2"):44s} {cc(x, "p1"):44s} {cc(x, "p0")}')
x = B[B.ratio < 0.90]; print(f'   <0.90 rotation   {cc(x, "p2"):44s} {cc(x, "p1"):44s} {cc(x, "p0")}')
print(f'   ολα τα φαβορι    {cc(B, "p2"):44s} {cc(B, "p1"):44s} {cc(B, "p0")}')
# LOSO στην τιμη 1ω
outs = []
for hold in SEAS:
    tr = B[B.sea != hold].dropna(subset=['p1'])
    sc = {t: tr[tr.ratio >= t].groupby('bk').p1.mean().mean() for t in TAUS}
    t = max(sc, key=lambda k: sc[k]); outs.append((hold, t, B[(B.sea == hold) & (B.ratio >= t)]))
X = pd.concat([o[2] for o in outs]).dropna(subset=['p1'])
m = X.groupby('bk').p1.mean(); ps = X.groupby('sea').p1.mean(); pn = ps[ps.index.isin(NEW)]
k1 = m.mean() > 0 and bool((m > 0).all()); k2 = (ps > 0).sum() >= 3 and len(pn) == 2 and bool((pn > 0).all())
t_best = max(set(t for _, t, _ in outs), key=lambda t: sum(1 for _, tt, _ in outs if tt == t))
rot = B[B.ratio < 0.90].dropna(subset=['p1']).groupby('bk').p1.mean().mean(); full = B[B.ratio >= t_best].dropna(subset=['p1']).groupby('bk').p1.mean().mean()
k3 = rot < full
print(NL + 'LOSO (τιμη 1ω): ' + ' '.join(f'{h[2:]}:τ={t:.2f}' for h, t, _ in outs) + f' → εκτος δειγματος {cc(X, "p1")}')
print(f'ΚΡΙΤΗΡΙΑ: Κ1 {"✓" if k1 else "✗"} · Κ2 {"✓" if k2 else "✗"} · Κ3 (rotation {100 * rot:+.1f}% < πληρης {100 * full:+.1f}%) {"✓" if k3 else "✗"} → {"ΠΕΡΝΑ" if k1 and k2 and k3 else "ΔΕΝ ΠΕΡΝΑ"}')
# ΚΙΝΗΣΗ με την ανακοινωση
y = B[B.ratio >= t_best].dropna(subset=['m2', 'm1', 'm0'])
print(NL + f'ΚΙΝΗΣΗ ΤΙΜΗΣ στα φαβορι με ενδεκαδα ≥{t_best:.2f} (διαφορα που δικαιολογει η τιμη · + = η αγορα ΑΝΕΒΑΣΕ το φαβορι = χειροτερη τιμη για εμας)')
print(f'   2ω → 1ω: {(y.m1 - y.m2).mean():+.3f} γκολ · 1ω → κλεισιμο: {(y.m0 - y.m1).mean():+.3f} · συνολο 2ω → κλεισιμο: {(y.m0 - y.m2).mean():+.3f} '
      f'· η τιμη ανεβηκε (χειροτερα) στο {100 * ((y.m0 - y.m2) > .02).mean():.0f}% · ιδια {100 * ((y.m0 - y.m2).abs() <= .02).mean():.0f}% · επεσε {100 * ((y.m0 - y.m2) < -.02).mean():.0f}%')
z = B[B.ratio < 0.90].dropna(subset=['m2', 'm0'])
print(f'   (για συγκριση, φαβορι με ROTATION: 2ω → κλεισιμο {(z.m0 - z.m2).mean():+.3f} γκολ)')
print(f'   εντος / εκτος (τιμη 1ω, ενδεκαδα ≥{t_best:.2f}): εντος {cc(B[(B.ratio >= t_best) & B.home], "p1")} · εκτος {cc(B[(B.ratio >= t_best) & ~B.home], "p1")}')
