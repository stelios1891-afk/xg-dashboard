"""euro_fix_threshold_timing.py — 15/10/2026 (Στελιος: «δουλεψε πανω στη διορθωση του μοντελου, με βαση το Elo και οτι αλλο πιστευεις · τεστ σε
κατωφλια — αν το μοντελο βελτιωθει πολυ, ισως δουλευουν χαμηλοτερα · τεστ σε διαφορα σκαλοπατια χρονου»).
ΔΙΟΡΘΩΣΕΙΣ (ολες οι παραμετροι απο τις ΑΛΛΕΣ 3 σεζον — LOSO — και χωριστα ανα διοργανωση):
  Μ   σημερινο
  Β   τεντωμα: λ × exp(±(bt·Δt/2 + bD·D))   (δυναμη ομαδας / διαφορα λιγκας μικραινουν· εδρα αθικτη)
  Ε   μιξη Elo: διαφορα = (1−w)·μοντελο + w·(h + k·ΔElo/100)
  ΒΕ  και τα 2 (πρωτα τεντωμα, μετα μιξη Elo)
  V   ΑΞΙΑ ΟΜΑΔΩΝ (15/10, Στελιος «δοκιμασε και αξια ομαδων»): λ × exp(±c·ln(αξια γηπ / αξια φιλ)/2) — «συνηθισμενη» αξια ενδεκαδας καθε ομαδας
      (διαμεσος 5 τελευταιων εγχωριων, γνωστη ΠΡΙΝ το ματς, euro_team_value.pkl) · και συνδυασμοι ΒV, EV, ΒΕV
  Εκτιμηση παραμετρων με βελτιστοποιηση (L-BFGS-B, πολλα σημεια εκκινησης) αντι για πλεγμα.
ΒΗΜΑ 1: ακριβεια (RPS, Δlog-lik ανα σεζον). Η ΚΑΛΥΤΕΡΗ διορθωση (χαμηλοτερο RPS με Κ1 ✓) περναει στο βημα 2 μαζι με το σημερινο.
ΒΗΜΑ 2: picks κατηγοριας Α σε ΣΚΑΛΟΠΑΤΙΑ ΧΡΟΝΟΥ (πρωτη τιμη / 168 / 72 / 48 / 24 / 12 / 6 / 1 ωρα πριν / κλεισιμο — τιμη εκεινη τη στιγμη)
  × ΚΑΤΩΦΛΙΑ edge (0 / 2 / 4 / 6 / 8 / 10 / 14%) × αγορα (φαβορι ≤−0.5 σωστα τεταρτα · αουτσαιντερ ≥+0.5 p_cover · κοντες 0/±0.25 σωστα τεταρτα)
  ✓ = Κ2 (θετικο 2 βιβλια, ≥3/4 σεζον, οι 2 νεας μορφης) + Κ3 (xG σε ισοπαλια > αυτο που ελεγε η αγορα) + Κ4 (η αγορα κινειται προς το pick ως το κλεισιμο)
ΕΠΑΝΑΛΗΨΗ: ιδιο σε Conference & Champions League — ενα ευρημα μετραει μονο αν δεν ειναι μοναχικο κελι.
"""
import sys, os
src = open('euro_tophalf_elo_test.py', encoding='utf-8').read().split("for cm, lab in (('EuropaLeague', 'EUROPA'), ('ConferenceLeague', 'CONFERENCE')):")[0]
src = src.replace("if COMP[i] not in ('EuropaLeague', 'ConferenceLeague') or LH_N[i] <= 0: continue",
                  "if COMP[i] not in ('EuropaLeague', 'ConferenceLeague', 'ChampionsLeague') or LH_N[i] <= 0: continue")
exec(src)
NL = chr(10)
TRAJ = u['TRAJ']; KO_ = u['KO']
A['D'] = [CP[str(MIDS[int(i)])]['D'] for i in A.i]
A['dt'] = A.th - A.ta
import pickle as _pkv
class _R: pass
def minimize(f, x0, method=None, bounds=None, iters=400):
    """απλο Nelder-Mead με ορια (δεν υπαρχει scipy στο laptop)."""
    lo = np.array([b[0] for b in bounds]); hi = np.array([b[1] for b in bounds]); n = len(x0)
    clip = lambda v: np.minimum(np.maximum(v, lo), hi)
    P = [clip(np.array(x0, float))] + [clip(np.array(x0, float) + np.eye(n)[j] * 0.15 * (hi[j] - lo[j])) for j in range(n)]
    F = [f(v) for v in P]
    for _ in range(iters):
        o = np.argsort(F); P = [P[j] for j in o]; F = [F[j] for j in o]
        if abs(F[-1] - F[0]) < 1e-7: break
        c = np.mean(P[:-1], axis=0); xr = clip(c + (c - P[-1])); fr = f(xr)
        if fr < F[0]:
            xe = clip(c + 2 * (c - P[-1])); fe = f(xe)
            P[-1], F[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < F[-2]: P[-1], F[-1] = xr, fr
        else:
            xc = clip(c + 0.5 * (P[-1] - c)); fc = f(xc)
            if fc < F[-1]: P[-1], F[-1] = xc, fc
            else:
                P = [P[0]] + [clip(P[0] + 0.5 * (v - P[0])) for v in P[1:]]; F = [F[0]] + [f(v) for v in P[1:]]
    r = _R(); j = int(np.argmin(F)); r.x = P[j]; r.fun = F[j]; return r
TV = _pkv.load(open('euro_team_value.pkl', 'rb'))
A['lv_'] = [np.log(TV[str(MIDS[int(i)])][0] / TV[str(MIDS[int(i)])][1]) if str(MIDS[int(i)]) in TV else 0.0 for i in A.i]
print(f'αξια ομαδων: καλυψη {100 * np.mean([str(MIDS[int(i)]) in TV for i in A.i]):.0f}% των ματς (οπου λειπει: χωρις διορθωση αξιας)')
COMP_ONLY = os.environ.get('FIX_COMPS', 'EuropaLeague,ConferenceLeague,ChampionsLeague').split(',')
def lamV(x, p):
    bt, bD, w, h, k, c = p
    z = bt * x.dt.values / 2 + bD * x.D.values + c * x.lv_.values / 2
    lh = x.lh.values * np.exp(z); la = x.la.values * np.exp(-z)
    if w > 0:
        T = lh + la; m = (1 - w) * (lh - la) + w * (h + k * x.de.values)
        lh = np.maximum((T + m) / 2, .05); la = np.maximum((T - m) / 2, .05)
    return lh, la
BND = {'bt': (-1.2, 0.5), 'bD': (-1.2, 0.6), 'w': (0.0, 1.0), 'h': (0.0, 0.8), 'k': (0.0, 1.5), 'c': (-0.3, 1.0)}
NAMES = ('bt', 'bD', 'w', 'h', 'k', 'c')
def fitV(x, ver):
    act = [n for n, on in (('bt', 'B' in ver), ('bD', 'B' in ver), ('w', 'E' in ver), ('h', 'E' in ver), ('k', 'E' in ver), ('c', 'V' in ver)) if on]
    if not act: return (0, 0, 0, 0, 0, 0)
    def full(v):
        d = dict(zip(act, v)); return tuple(d.get(n, 0.0) for n in NAMES)
    f = lambda v: -ll(x, *lamV(x, full(v)))
    best = None
    starts = [[0.0 if n not in ('w', 'k') else 0.3 for n in act], [(-0.4 if n in ('bt', 'bD') else (0.5 if n in ('w', 'k', 'h') else 0.3)) for n in act]]
    for st in starts:
        r = minimize(f, st, method='L-BFGS-B', bounds=[BND[n] for n in act])
        if best is None or r.fun < best.fun: best = r
    return full(best.x)
def snapT(mid, bk, h):
    ko = KO_.get(mid); seq = TRAJ.get((mid, bk))
    if not ko or not seq: return None
    if h == 'open': return seq[0][1:] if seq[0][0] <= ko else None
    cut = ko - h * 3600 if h else ko + 900
    prev = [r for r in seq if r[0] <= cut]
    return prev[-1][1:] if prev else None
WINS = ['open', 168, 72, 48, 24, 12, 6, 1, 0]
WLAB = {'open': 'πρωτη τιμη', 168: '168ω', 72: '72ω', 48: '48ω', 24: '24ω', 12: '12ω', 6: '6ω', 1: '1ω', 0: 'κλεισιμο'}
THS = (0.0, 0.02, 0.04, 0.06, 0.08, 0.10, 0.14)
KINDS = (('ΦΑΒΟΡΙ (≤−0.5)', lambda ln: ln <= -0.5, 'q'), ('ΑΟΥΤΣΑΙΝΤΕΡ (≥+0.5)', lambda ln: ln >= 0.5, 'p'), ('ΚΟΝΤΕΣ (0, ±0.25)', lambda ln: abs(ln) <= 0.25, 'q'))
for cm in COMP_ONLY:
    x = A[A.comp == cm].reset_index(drop=True); seas = sorted(x.sea.unique())
    print(f'{NL}{"=" * 110}{NL}{cm}: {len(x)} ματς με Elo (ολες οι κατηγοριες για την εκτιμηση)')
    LV = {}; PAR = {}
    for ver in ('M', 'B', 'E', 'V', 'BE', 'BV', 'EV', 'BEV'):
        lh = np.zeros(len(x)); la = np.zeros(len(x)); PAR[ver] = {}
        for s in seas:
            te = (x.sea == s).values; p = fitV(x[~te], ver) if ver != 'M' else (0, 0, 0, 0, 0, 0); PAR[ver][s] = p
            a, b = lamV(x[te], p); lh[te] = a; la[te] = b
        LV[ver] = (lh, la)
    R = {v: rps(*LV[v], x.gd.values) for v in LV}
    print('ΒΗΜΑ 1 — ΑΚΡΙΒΕΙΑ (εκτος δειγματος)')
    best = None
    for ver, nm in (('M', 'σημερινο'), ('B', 'τεντωμα'), ('E', 'μιξη Elo'), ('V', 'αξια ομαδων'), ('BE', 'τεντωμα+Elo'), ('BV', 'τεντωμα+αξια'), ('EV', 'Elo+αξια'), ('BEV', 'ολα μαζι')):
        d = {s: ll(x[x.sea == s], LV[ver][0][(x.sea == s).values], LV[ver][1][(x.sea == s).values]) -
                ll(x[x.sea == s], LV['M'][0][(x.sea == s).values], LV['M'][1][(x.sea == s).values]) for s in seas}
        npos = sum(t > 0 for t in d.values()); k1 = ver != 'M' and npos >= 3 and R[ver].mean() < R['M'].mean()
        pars = ' · '.join(f'{s[2:]}: bt {PAR[ver][s][0]:+.2f} bD {PAR[ver][s][1]:+.2f} w {PAR[ver][s][2]:.2f} c {PAR[ver][s][5]:+.2f}' for s in seas) if ver != 'M' else ''
        print(f'   {nm:14s} RPS {R[ver].mean():.4f} · Δlog-lik ' + ' '.join(f'{s[2:]}:{t:+.1f}' for s, t in d.items()) +
              (f' · Κ1 {"✓" if k1 else "✗"}' if ver != 'M' else '') + f'   [{pars}]')
        if k1 and (best is None or R[ver].mean() < R[best].mean()): best = ver
    mk_all = []
    for r in x.itertuples():
        s = snapT(str(MIDS[int(r.i)]), 'Crown', 0) or snapT(str(MIDS[int(r.i)]), 'SBOBET', 0)
        mk_all.append(implied_margin(int(r.i), *s) if s else np.nan)
    mk_all = np.array(mk_all); lv_ok = np.isfinite(x.lvl.values) & (x.lw.values > 0.2); okc = lv_ok & np.isfinite(mk_all)
    print(f'   (αγορα κλεισιματος RPS {rps(np.maximum((x.lh + x.la + mk_all) / 2, .05)[okc], np.maximum((x.lh + x.la - mk_all) / 2, .05)[okc], x.gd.values[okc]).mean():.4f} στα ιδια ματς με τιμη)')
    cal = np.polyfit(mk_all[okc], x.lvl.values[okc], 1, w=x.lw.values[okc])
    VERS2 = ['M'] + ([best] if best else [])
    print(f'ΒΗΜΑ 2 — PICKS κατηγοριας Α ανα ΣΚΑΛΟΠΑΤΙ ΧΡΟΝΟΥ × ΚΑΤΩΦΛΙ · εκδοχες: σημερινο' + (f' + {best}' if best else ' (καμια διορθωση δεν περασε Κ1)'))
    xa_ = x[x.cat == 'A']
    # προυπολογισμος στιγμιοτυπων
    SNP = {}
    for k_ in xa_.index:
        mid = str(MIDS[int(x.loc[k_, 'i'])])
        for bk in ('Crown', 'SBOBET'):
            for w in WINS: SNP[(k_, bk, w)] = snapT(mid, bk, w)
    for ver in VERS2:
        rows = []
        for k_ in xa_.index:
            r = x.loc[k_]; i = int(r.i); D_ = sdist(LV[ver][0][k_], LV[ver][1][k_])
            for bk in ('Crown', 'SBOBET'):
                sc = SNP[(k_, bk, 0)]; mcl = implied_margin(i, *sc) if sc else np.nan
                for w in WINS:
                    s = SNP[(k_, bk, w)]
                    if not s: continue
                    L, oh, oa = s
                    for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                        if not (1.70 <= o <= 2.10): continue
                        for kn, cond, how in KINDS:
                            if not cond(ln): continue
                            f = cover_q if how == 'q' else picks.p_cover
                            e = edge(*f(D_, side, ln), o)
                            if e < 0: continue
                            me = implied_margin(i, L, oh, oa)
                            rows.append(dict(w=w, kind=kn, e=e, sea=r.sea, bk=bk, pnl=picks.settle(GD[i], side, ln, o),
                                             lv=side * (r.lvl - (cal[0] * me + cal[1])) if lv_ok[k_] else np.nan, lw=r.lw,
                                             clv=side * (mcl - me) if np.isfinite(mcl) and w != 0 else np.nan))
        Pk = pd.DataFrame(rows)
        print(f'{NL}   ---- {cm} · {"ΣΗΜΕΡΙΝΟ" if ver == "M" else "ΔΙΟΡΘΩΜΕΝΟ (" + ver + ")"} ---- κελι = ROI% (picks ανα βιβλιο) · ✓ = Κ2+Κ3+Κ4')
        for kn, *_ in KINDS:
            print(f'      {kn}')
            print(f'      {"":12s}' + ''.join(f'{"≥" + str(int(t * 100)) + "%":>15s}' for t in THS))
            for w in WINS:
                cells = []
                for t in THS:
                    y = Pk[(Pk.w == w) & (Pk.kind == kn) & (Pk.e >= t)]
                    if len(y) < 16: cells.append(f'{"·":>15s}'); continue
                    mb = y.groupby('bk').pnl.mean(); n = y.groupby('bk').size().mean(); ps = y.groupby('sea').pnl.mean(); pn = ps[ps.index.isin(NEW)]
                    k2 = bool((mb > 0).all()) and (ps > 0).sum() >= 3 and len(pn) == 2 and bool((pn > 0).all())
                    yy = y.dropna(subset=['lv']); k3 = len(yy) > 0 and np.average(yy.lv, weights=yy.lw) > 0
                    k4 = (w == 0) or (y.clv.mean() > 0)
                    cells.append(f'{100 * mb.mean():+6.1f} ({n:3.0f}){"✓" if (k2 and k3 and k4) else " "}'.rjust(15))
                print(f'      {WLAB[w]:12s}' + ''.join(cells))
