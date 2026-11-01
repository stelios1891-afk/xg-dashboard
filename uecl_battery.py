"""uecl_battery.py — 12/10/2026 (Στελιος: «η αναλυση δεν ειναι οσο αναβαθμισμενη ηταν στο τσαμπιονς λιγκ — βρες τα τεστ που εγιναν εκει
και χρησιμοποιησε τα για το κονφερενς»). ΟΛΑ τα τεστ του UCL (10/10) πανω στο Conference League, 4 σεζον 2223-2526, Crown & SBOBET (μεσος).
Ροες picks (πρωτη εμφανιση ≤72ω, 1.70-2.10): ΦΑΒ Α @10 (προταση) & @4 (σημερα) · DOG Α @10 · OVER Α @8 (προταση) & @4 (σημερα) · UNDER Α @10 ·
UNDER Β @14 (σκια-προταση) · DNB / −0.25 / +0.25 Α @4.
  1. ΚΡΙΤΗΡΙΑ Κ1-Κ4 (ucl_other_lines_deep): Κ1 θετικο 2 βιβλια + ≥3/4 σεζον + οι 2 νεας μορφης · Κ2 LOSO κατωφλι → εκτος δειγματος >0 ·
     Κ3 CLV: η αγορα κινειται ΠΡΟΣ το pick μετα την εισοδο · Κ4 βαθμονομηση |P μοντελου − πραγμ| ≤ max(5 μον., |αγορα − πραγμ|)
     + ΓΕΙΤΟΝΙΚΑ κατωφλια (ucl_totals_threshold_loso): θετικο και στο −2/+2
  2. ΧΡΟΝΙΣΜΟΣ (ucl_unders_timing / ucl_nonfm_timing): ROI ανα παραθυρο εισοδου, «αν περιμενα το κλεισιμο», κινηση αγορας, αργα picks ≤2ω
  3. EDGE vs ΠΡΑΓΜΑΤΙΚΟΤΗΤΑ + ΠΟΝΤΑΡΙΣΜΑ (ucl_edge_vs_reality / ucl_over_band_test)
  4. FAIR xG (ucl_other_lines_xg): αξια με βαση τα ΤΕΛΙΚΑ xG vs πραγματικο ROI (τυχη ή παιχνιδι;)
  5. ΧΑΝΤΙΚΑΠ + ΓΚΟΛ ΣΤΟ ΙΔΙΟ ΜΑΤΣ (ucl_ah_ou_same_match)
  6. ΚΛΙΜΑΚΑ ΦΑΒΟΡΙ κ (UCL ×1.16): χρειαζεται και στο Conference; LOSO
  7. ΚΑΤΗΓΟΡΙΑ Β χαντικαπ υπερ της ομαδας ΜΕ FotMob (UCL σκια nonfm_fav_shadow) — περιγραφικο
Διαγνωστικο — τιποτα live.
"""
import sys, os, io, math
_dn = open(os.devnull, 'w', encoding='utf-8'); _so = sys.stdout; sys.stdout = _dn
exec(open('uecl_full_review.py', encoding='utf-8').read().split('# ================= Α. ΒΑΘΜΟΝΟΜΗΣΗ')[0])
sys.stdout = _so; sys.stdout.reconfigure(encoding='utf-8')
from math import lgamma
EUM = {}
for f in glob.glob('data_Europe_*.json'):
    for mid, m in json.load(open(f, encoding='utf-8')).items(): EUM[str(mid)] = m
def xg_pair(i):
    m = EUM.get(str(MIDS[i]))
    if not m or not m.get('shots'): return None
    hid, aid = int(m['home']['id']), int(m['away']['id'])
    xs = lambda t: sum(s['xg'] for s in m['shots'] if s.get('xg') is not None and int(s['tid']) == t)
    return xs(hid), xs(aid)
XG = {i: xg_pair(i) for i in UI}
# ---------------- ροες ----------------
rows = []
for i in UI:
    c = cat(i); D = sdist(LH_N[i], LA_N[i]); fmh = SRCC[i] != 'FF' and (V6['src_h'][VI[str(MIDS[i])]] == 'shots')
    td = ES.tot_dist(OH[i], OA[i], DRAW_SCALE); tot = GH[i] + GA[i]
    for bk in ('Crown', 'SBOBET'):
        for h in HS:
            s = snap_ah(MIDS[i], bk, h)
            if s and c in ('A', 'B'):
                L, oh, oa = s; km = implied_margin(i, L, oh, oa)
                for side, ln, o, oo in ((1, L, oh, oa), (-1, -L, oa, oh)):
                    if not (1.70 <= o <= 2.10): continue
                    if c == 'B':
                        if not ((side == 1) == fmh and ln <= -0.5): continue        # μονο η ομαδα ΜΕ FotMob ως φαβορι
                        kind = 'Β φαβ FotMob'
                    elif abs(ln) < .01: kind = 'DNB'
                    elif ln <= -0.5: kind = 'φαβορι'
                    elif ln >= 0.5: kind = 'αουτσαιντερ'
                    elif ln < 0: kind = '−0.25'
                    else: kind = '+0.25'
                    pw, pp = cover_q(D, side, ln) if kind != 'αουτσαιντερ' else picks.p_cover(D, side, ln)
                    rows.append(dict(i=i, bk=bk, h=h, grp='AH', kind=kind, side=side, ln=ln, sea=SEA[i], ph=PH[i], e=edge(pw, pp, o), od=o,
                                     pm=pw / max(1 - pp, 1e-9), pk=(1 / o) / (1 / o + 1 / oo), mk=side * km, pnl=picks.settle(GD[i], side, ln, o)))
            so = snap_ou(MIDS[i], bk, h)
            if so:
                L, o, un = so; po, pu = ES.p_over(td, L); mt_ = mtot(L, o, un)
                for side, od, oo, pw, pl in (('over', o, un, po, pu), ('under', un, o, pu, po)):
                    if not (1.70 <= od <= 2.10): continue
                    kind = {'A': side, 'B': side + ' Β', 'G': side + ' Γ'}[c]
                    rows.append(dict(i=i, bk=bk, h=h, grp='OU', kind=kind, side=side, ln=L, sea=SEA[i], ph=PH[i], e=pw * (od - 1) * (1 - picks.MARGIN) - pl,
                                     od=od, pm=pw / max(pw + pl, 1e-9), pk=(1 / od) / (1 / od + 1 / oo), mk=(1 if side == 'over' else -1) * mt_,
                                     pnl=settle(tot, L, od, side == 'over')))
R = pd.DataFrame(rows)
CL = R[R.h == 0].set_index(['i', 'bk', 'kind', 'side'])
STREAMS = [('ΦΑΒ Α @10 (προταση)', 'φαβορι', .10), ('ΦΑΒ Α @4 (σημερα)', 'φαβορι', .04), ('DOG Α @10 (σημερα)', 'αουτσαιντερ', .10),
           ('OVER Α @8 (προταση)', 'over', .08), ('OVER Α @4 (σημερα)', 'over', .04), ('UNDER Α @10', 'under', .10),
           ('UNDER Β @14 (σκια)', 'under Β', .14), ('DNB Α @4', 'DNB', .04), ('−0.25 Α @4', '−0.25', .04), ('+0.25 Α @4', '+0.25', .04),
           ('Β φαβ FotMob @10', 'Β φαβ FotMob', .10)]
def stream(kind, th):
    X = R[R.kind == kind]; keys = ['i', 'bk', 'side'] if X.grp.iloc[0] == 'AH' else ['i', 'bk']
    F = X[X.e >= th].sort_values('h', ascending=False).groupby(keys).head(1).copy()
    cl = [CL.pnl.get((r.i, r.bk, r.kind, r.side), np.nan) if isinstance(CL.pnl.get((r.i, r.bk, r.kind, r.side), np.nan), float) else np.nan for r in F.itertuples()]
    F['pc'] = cl
    F['mc'] = [CL.mk.get((r.i, r.bk, r.kind, r.side), np.nan) for r in F.itertuples()]
    F['clv'] = F.mc - F.mk
    return X, F, keys
def roi(x): return x.groupby('bk').pnl.mean().mean() if len(x) else np.nan
NL = chr(10)
# ================= 1 =================
print('1. ΚΡΙΤΗΡΙΑ ανα ροη (Κ1 βιβλια/σεζον · Κ2 LOSO · Κ3 CLV · Κ4 βαθμονομηση · Γ γειτονικα κατωφλια ±2)')
SF = {}
for lab, kind, th in STREAMS:
    X, F, keys = stream(kind, th); SF[lab] = F
    if len(F) == 0: print(f'   {lab}: —'); continue
    m = F.groupby('bk').pnl.mean(); ps = F.groupby('sea').pnl.mean(); pn = ps[ps.index.isin(NEW)]
    k1 = bool((m > 0).all()) and (ps > 0).sum() >= 3 and len(pn) == 2 and bool((pn > 0).all())
    outs, allx = loso(X, (0, .02, .04, .06, .08, .10, .12, .14, .16), tuple(keys)); k2 = len(allx) > 0 and roi(allx) > 0
    cv = F.clv.dropna(); k3 = len(cv) > 5 and cv.mean() > 0
    act = (F.pnl > 0).mean(); k4 = abs(F.pm.mean() - act) <= max(.05, abs(F.pk.mean() - act))
    nb = [roi(X[X.e >= t].sort_values('h', ascending=False).groupby(keys).head(1)) for t in (max(th - .02, 0), th + .02)]
    kg = all(v > 0 for v in nb)
    print(f'   {lab:22s} {cc(F)}')
    print(f'      Κ1 {"✓" if k1 else "✗"} · Κ2 {"✓" if k2 else "✗"} (LOSO {" ".join(f"{h[2:]}:{int(t * 100)}" for h, t, _ in outs)} → {100 * roi(allx):+.1f}%) · '
          f'Κ3 {"✓" if k3 else "✗"} (CLV {cv.mean():+.3f} γκολ, υπερ {100 * (cv > 0).mean():.0f}% / κοντρα {100 * (cv < 0).mean():.0f}%) · '
          f'Κ4 {"✓" if k4 else "✗"} (κερδος: μοντ {100 * F.pm.mean():.0f}% αγορα {100 * F.pk.mean():.0f}% πραγμ {100 * act:.0f}%) · '
          f'γειτονικα {"✓" if kg else "✗"} ({" / ".join(f"{100 * v:+.0f}%" for v in nb)}) · ΣΥΝΟΛΟ {sum([k1, k2, k3, k4, kg])}/5')
# ================= 2 =================
print(NL + '2. ΧΡΟΝΙΣΜΟΣ — ROI ανα ωρα πρωτης εμφανισης · «αν περιμενα το κλεισιμο» · κινηση αγορας μετα την εισοδο (+ = προς εμας)')
for lab, kind, th in STREAMS[:7]:
    F = SF[lab]
    if len(F) == 0: continue
    cells = []
    for hi, lo, wl in ((72, 48, '72-48ω'), (36, 18, '36-18ω'), (12, 6, '12-6ω'), (4, 0, '≤4ω')):
        y = F[(F.h <= hi) & (F.h >= lo)]
        if len(y): cells.append(f'{wl}: {len(y) / 2:.0f}/{100 * roi(y):+.0f}% CLV {y.clv.mean():+.2f}')
    print(f'   {lab:22s} ' + ' · '.join(cells) + f' · ΣΤΗΝ ΕΙΣΟΔΟ {100 * roi(F):+.1f}% vs ΑΝ ΠΕΡΙΜΕΝΑ ΤΟ ΚΛΕΙΣΙΜΟ {100 * F.dropna(subset=["pc"]).groupby("bk").pc.mean().mean():+.1f}%')
# ================= 3 =================
print(NL + '3. ΔΗΛΩΜΕΝΟ EDGE → ΠΡΑΓΜΑΤΙΚΟ ROI (κλιση 1 = καθε +1% edge δινει +1% · 0 = το edge δεν λεει τιποτα)')
def ols1(x, y):
    b = np.polyfit(x, y, 1); e = y - np.polyval(b, x); return b[0], np.sqrt((e ** 2).sum() / (len(x) - 2) / ((x - x.mean()) ** 2).sum())
BK = [(.04, .08), (.08, .12), (.12, .16), (.16, .22), (.22, 9)]
for lab in ('ΦΑΒ Α @4 (σημερα)', 'DOG Α @10 (σημερα)', 'OVER Α @4 (σημερα)', 'UNDER Β @14 (σκια)'):
    x = SF[lab]
    if len(x) < 10: continue
    b, se_ = ols1(x.e.values, x.pnl.values)
    cells = [f'{int(lo * 100)}-{int(hi * 100) if hi < 9 else "+"}%: {len(y) / 2:.0f}/{100 * roi(y):+.0f}%' for lo, hi in BK for y in [x[(x.e >= lo) & (x.e < hi)]] if len(y)]
    print(f'   {lab:22s} μεσο edge {100 * x.e.mean():4.1f}% → πραγμ {100 * roi(x):+5.1f}% · κλιση {b:+.2f} (t {b / se_:+.1f}) · ' + ' · '.join(cells))
ALL = pd.concat([SF[l] for l in ('ΦΑΒ Α @10 (προταση)', 'DOG Α @10 (σημερα)', 'OVER Α @8 (προταση)')])
ALL['ko'] = [KO.get(MIDS[i]) for i in ALL.i]
def dd(p):
    c = np.cumsum(p); return float((np.maximum.accumulate(np.r_[0, c])[1:] - c).max())
print('   ΠΟΝΤΑΡΙΣΜΑ στο σετ της προτασης (φαβ @10 + dog @10 + over @8), ιδιο συνολικο ποσο:')
res = {}
for bk, x in ALL.groupby('bk'):
    x = x.sort_values('ko'); k = (x.e / (x.od - 1)).clip(lower=0).values
    for n, s in (('σταθερο', np.ones(len(x))), ('αναλογο edge', x.e.values), ('Kelly', k), ('Kelly κομμενο 2×', np.minimum(k, 2 * k.mean()))):
        s = s / s.mean(); p = s * x.pnl.values; r = res.setdefault(n, [[], [], {}])
        r[0].append(p.sum()); r[1].append(dd(p))
        for se2 in x.sea.unique():
            mm = (x.sea == se2).values; r[2].setdefault(se2, []).append(p[mm].sum() / s[mm].sum())
for n, r in res.items():
    print(f'      {n:18s} μοναδες {np.mean(r[0]):+6.1f} · χειροτερη βουτια {np.mean(r[1]):4.1f}μ · ανα σεζον ' + ' '.join(f'{s[2:]} {100 * np.mean(v):+.0f}' for s, v in sorted(r[2].items())))
# ================= 4 =================
print(NL + '4. FAIR xG — αξια με βαση τα ΤΕΛΙΚΑ xG (τιμη / fair − 1) vs πραγματικο ROI · κοντα = το κερδισαν οι ομαδες, πολυ χαμηλοτερη = τυχη')
KS = np.arange(25)
def pois(l): return np.array([math.exp(-l) * l ** k / math.factorial(k) for k in range(25)])
def xval(r):
    x = XG.get(r.i)
    if not x: return np.nan
    if r.grp == 'AH':
        d = picks.gd_dist(max(x[0], .05), max(x[1], .05)); pw, pp = picks.p_cover(d, r.side, r.ln)
    else:
        pt = pois(max(x[0] + x[1], .05)); parts = [r.ln] if (r.ln * 4) % 2 == 0 else [r.ln - .25, r.ln + .25]; pw = pp = 0
        for L in parts:
            pw += pt[(KS > L + .01) if r.side == 'over' else (KS < L - .01)].sum() / len(parts); pp += pt[np.abs(KS - L) < .01].sum() / len(parts)
    return r.od / ((1 - pp) / max(pw, 1e-9)) - 1
for lab, _, _ in STREAMS:
    F = SF[lab]
    if len(F) < 6: continue
    v = np.array([xval(r) for r in F.itertuples()]); F = F.assign(xv=v)
    print(f'   {lab:22s} {len(F) / 2:4.0f} picks · ROI πραγματικο {100 * roi(F):+6.1f}% · ΑΞΙΑ xG {100 * F.groupby("bk").xv.mean().mean():+6.1f}% · '
          f'ανα σεζον αξια xG ' + ' '.join(f'{s[2:]} {100 * y.xv.mean():+.0f}' for s, y in F.groupby('sea')))
# ================= 5 =================
print(NL + '5. ΧΑΝΤΙΚΑΠ + ΓΚΟΛ ΣΤΟ ΙΔΙΟ ΜΑΤΣ (σετ προτασης: φαβ @10, dog @10, over @8)')
ah = pd.concat([SF['ΦΑΒ Α @10 (προταση)'].assign(r='φαβ'), SF['DOG Α @10 (σημερα)'].assign(r='dog')])
ou = SF['OVER Α @8 (προταση)']
J = ah.merge(ou[['i', 'bk', 'pnl']], on=['i', 'bk'], suffixes=('_ah', '_ou'))
print(f'   ματς με χαντικαπ: {ah.groupby("bk").size().mean():.0f} · με over: {len(ou) / 2:.0f} · ΚΑΙ ΤΑ ΔΥΟ: {len(J) / 2:.0f}')
for r_, x in J.groupby('r'):
    both = ((x.pnl_ah > 0) & (x.pnl_ou > 0)).mean(); none = ((x.pnl_ah < 0) & (x.pnl_ou < 0)).mean()
    cor = np.corrcoef(x.pnl_ah, x.pnl_ou)[0, 1] if len(x) > 3 else np.nan
    print(f'   {r_}+over: {len(x) / 2:.0f} ζευγη · κερδιζουν και τα 2 {100 * both:.0f}% · χανουν και τα 2 {100 * none:.0f}% · συσχετιση {cor:+.2f} · '
          f'ROI χαντικαπ {100 * x.pnl_ah.mean():+.0f}% / over {100 * x.pnl_ou.mean():+.0f}%')
# ================= 6 =================
print(NL + '6. ΚΛΙΜΑΚΑ ΦΑΒΟΡΙ κ (στο UCL ×1.16): γκολ του φαβορι (μοντελου) ×κ, κ απο τις αλλες 3 σεζον → log-lik στη σεζον-τεστ, κατηγορια Α')
IA = [i for i in UI if cat(i) == 'A' and LH_N[i] > 0]
def llk(idx, k):
    s = 0.0
    for i in idx:
        a, b = LH_N[i], LA_N[i]
        if a >= b: a *= k
        else: b *= k
        s += GH[i] * math.log(a) - a + GA[i] * math.log(b) - b - lgamma(GH[i] + 1) - lgamma(GA[i] + 1)
    return s
GRID = np.round(np.arange(0.90, 1.31, 0.02), 2); ok = 0
for s_ in SEAS:
    tr = [i for i in IA if SEA[i] != s_]; te = [i for i in IA if SEA[i] == s_]
    k = GRID[np.argmax([llk(tr, g) for g in GRID])]; d = llk(te, k) - llk(te, 1.0); ok += d > 0
    print(f'   τεστ {s_}: κ = {k:.2f} · Δlog-lik {d:+.2f} (n{len(te)})')
print(f'   κ με ολες: {GRID[np.argmax([llk(IA, g) for g in GRID])]:.2f} · νεα μορφη μονο: {GRID[np.argmax([llk([i for i in IA if SEA[i] in NEW], g) for g in GRID])]:.2f} · '
      f'καλυτερο εκτος δειγματος {ok}/4')
fav = []
for i in IA:
    a, b = LH_N[i], LA_N[i]; fh = a >= b
    fav.append((GH[i] if fh else GA[i], a if fh else b))
fav = np.array(fav); print(f'   γκολ φαβορι: πραγμ {fav[:, 0].mean():.2f} vs μοντελο {fav[:, 1].mean():.2f} ({100 * fav[:, 0].sum() / fav[:, 1].sum():.0f}%)')
# ================= 7 =================
print(NL + '7. ΚΑΤΗΓΟΡΙΑ Β — χαντικαπ ΥΠΕΡ της ομαδας ΜΕ FotMob οταν ειναι φαβορι (στο UCL: σκια, 27 picks +6.1%)')
F = SF['Β φαβ FotMob @10']
print(f'   @10: {cc(F)} · νεα μορφη {cc(F[F.sea.isin(NEW)])}')
X = R[R.kind == 'Β φαβ FotMob']
print('   κατωφλια: ' + ' · '.join(f'≥{int(t * 100)}% {cc(X[X.e >= t].sort_values("h", ascending=False).groupby(["i", "bk", "side"]).head(1))[:26]}' for t in (0, .04, .10, .16)))
