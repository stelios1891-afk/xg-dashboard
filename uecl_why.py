"""uecl_why.py — 12/10/2026 (Στελιος: «τι χαλαει τα under της Α; τι δεν μας αφηνει να παιξουμε χαντικαπ ή γκολ στη Β; υποτιμαμε/υπερτιμαμε
συστηματικα τις ομαδες χωρις FotMob;»). Conference League 4 σεζον, κλεισιμο Crown (αλλιως SBOBET) για την αγορα.
  1) UNDER Α: γκολ των ματς Α (πραγμ/μοντελο/αγορα) ανα σεζον/φαση + τι εγινε στα ιδια τα under picks
  2) Β: πλευρα ΜΕ FotMob vs ΧΩΡΙΣ — γκολ/xG/μοντελο/αγορα ανα σεζον και ανα πηγη · διαφορα απο σκοπια FotMob · θορυβος (|μοντ−αγορα|, b)
  3) ΔΟΚΙΜΗ: γκολ της πλευρας ΜΕ FotMob ×c στα ματς Β (c LOSO απο τις αλλες 3 σεζον) → προβλεψη + picks χαντικαπ (φαβ FotMob / dog χωρις) και συνολων
"""
import sys, os
_src = open('uecl_battery.py', encoding='utf-8').read().split('# ================= 1 =================')[0]
_DEV = open(os.devnull, 'w', encoding='utf-8'); _REAL = sys.stdout; sys.stdout = _DEV
exec(_src)
sys.stdout = _REAL; sys.stdout.reconfigure(encoding='utf-8')
NL = chr(10)
LABS = {'shots': 'FotMob', 'griffis': 'Ben', 'goals': 'γκολ+Elo'}
FMH = {i: V6['src_h'][VI[str(MIDS[i])]] == 'shots' for i in UI}
SRCN = {i: (V6['src_a'][VI[str(MIDS[i])]] if FMH[i] else V6['src_h'][VI[str(MIDS[i])]]) for i in UI}
rows = []
for i in UI:
    s = snap_ah(MIDS[i], 'Crown', 0) or snap_ah(MIDS[i], 'SBOBET', 0); so = snap_ou(MIDS[i], 'Crown', 0) or snap_ou(MIDS[i], 'SBOBET', 0)
    if not s or not so or LH_N[i] <= 0: continue
    km = implied_margin(i, *s); kt = mtot(*so); x = XG.get(i) or (np.nan, np.nan)
    rows.append(dict(i=i, sea=SEA[i], ph=PH[i], cat=cat(i), gh=GH[i], ga=GA[i], lh=LH_N[i], la=LA_N[i], oh=OH[i], oa=OA[i], xh=x[0], xa=x[1],
                     kh=(kt + km) / 2, ka=(kt - km) / 2, fmh=FMH[i], srcn=SRCN[i]))
M = pd.DataFrame(rows)
se = lambda a: a.std() / max(np.sqrt(len(a)), 1)
# ===== 1 =====
print('1. UNDER ΚΑΤΗΓΟΡΙΑΣ Α — ποσα γκολ μπαινουν στα ματς Α (πραγματικα / xG / μοντελο / αγορα)')
A_ = M[M.cat == 'A'].copy(); A_['t'] = A_.gh + A_.ga; A_['mt'] = A_.oh + A_.oa; A_['kt'] = A_.kh + A_.ka; A_['xt'] = A_.xh + A_.xa
print(f'   ΟΛΑ n{len(A_)}: πραγμ {A_.t.mean():.2f} · xG {A_.xt.mean():.2f} · μοντελο {A_.mt.mean():.2f} · αγορα {A_.kt.mean():.2f} · πραγμ−μοντ {(A_.t - A_.mt).mean():+.2f}±{se(A_.t - A_.mt):.2f}')
for k, x in A_.groupby('sea'): print(f'      {k}: n{len(x):3d} πραγμ {x.t.mean():.2f} · xG {x.xt.mean():.2f} · μοντ {x.mt.mean():.2f} · αγορα {x.kt.mean():.2f}')
for k, x in A_.groupby('ph'): print(f'      φαση {k}: n{len(x):3d} πραγμ {x.t.mean():.2f} · xG {x.xt.mean():.2f} · μοντ {x.mt.mean():.2f} · αγορα {x.kt.mean():.2f}')
q = pd.qcut(A_.mt - A_.kt, 3, labels=['μοντ ΧΑΜΗΛΟΤΕΡΑ απο αγορα', 'σχεδον ιδια', 'μοντ ΨΗΛΟΤΕΡΑ απο αγορα'])
for k, x in A_.groupby(q, observed=True):
    print(f'      {k:26s} n{len(x):3d} · πραγμ {x.t.mean():.2f} · xG {x.xt.mean():.2f} · μοντ {x.mt.mean():.2f} · αγορα {x.kt.mean():.2f}')
for lab, kind, th in (('UNDER Α @10', 'under', .10), ('OVER Α @8', 'over', .08)):
    X = R[R.kind == kind]; F = X[X.e >= th].sort_values('h', ascending=False).groupby(['i', 'bk']).head(1)
    y = A_[A_.i.isin(F.i)]
    print(f'   στα ματς με {lab} (n{len(y)}): πραγμ {y.t.mean():.2f} · xG {y.xt.mean():.2f} · μοντ {y.mt.mean():.2f} · αγορα {y.kt.mean():.2f}')
# ===== 2 =====
print(NL + '2. ΚΑΤΗΓΟΡΙΑ Β — γκολ που ΒΑΖΕΙ η ομαδα ΜΕ FotMob και η ομαδα ΧΩΡΙΣ (πραγμ / xG / μοντελο / αγορα)')
B_ = M[M.cat == 'B'].copy()
for a_, h_, a2 in (('fg', 'gh', 'ga'), ('fl', 'lh', 'la'), ('fx', 'xh', 'xa'), ('fk', 'kh', 'ka')):
    B_[a_] = np.where(B_.fmh, B_[h_], B_[a2]); B_['n' + a_[1]] = np.where(B_.fmh, B_[a2], B_[h_])
def bl(x, lab):
    return (f'   {lab:30s} n{len(x):3d} · ΜΕ FotMob {x.fg.mean():.2f} / xG {x.fx.mean():.2f} / μοντ {x.fl.mean():.2f} / αγορα {x.fk.mean():.2f} · '
            f'ΧΩΡΙΣ {x.ng.mean():.2f} / xG {x.nx.mean():.2f} / μοντ {x.nl.mean():.2f} / αγορα {x.nk.mean():.2f}')
print(bl(B_, 'ΟΛΑ'))
for k, x in B_.groupby('sea'): print(bl(x, f'   σεζον {k}'))
for k, x in B_.groupby('srcn'): print(bl(x, f'   ομαδα χωρις = {LABS.get(k, k)}'))
for k, x in B_.groupby(np.where(B_.fmh, 'η ΜΕ FotMob εντος', 'η ΜΕ FotMob εκτος')): print(bl(x, f'   {k}'))
for k, x in B_.groupby(np.where(B_.fl > B_.nl, 'η ΜΕ FotMob φαβορι', 'η ΜΕ FotMob αουτσαιντερ')): print(bl(x, f'   {k}'))
print(f'   ΔΙΑΦΟΡΑ (σκοπια ομαδας ΜΕ FotMob): πραγμ {(B_.fg - B_.ng).mean():+.2f} · xG {(B_.fx - B_.nx).mean():+.2f} · μοντελο {(B_.fl - B_.nl).mean():+.2f} · αγορα {(B_.fk - B_.nk).mean():+.2f}')
print(f'   ΘΟΡΥΒΟΣ: μεση |μοντελο − αγορα| στη διαφορα: Α {np.abs((A_.lh - A_.la) - (A_.kh - A_.ka)).mean():.2f} · Β {np.abs((B_.lh - B_.la) - (B_.kh - B_.ka)).mean():.2f}')
def ols(y, x0, x1):
    X = np.column_stack([np.ones(len(y)), x0, x1]); b, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ b; cov = np.linalg.inv(X.T @ X) * (e @ e / max(len(y) - 3, 1)); return b[2], b[2] / np.sqrt(cov[2, 2])
for lab, x in (('Α', A_), ('Β', B_)):
    y = (x.gh - x.ga).values; km_ = (x.kh - x.ka).values; mm = (x.lh - x.la).values
    b, t = ols(y, km_, mm - km_); bx, tx = ols((x.xh - x.xa).values, km_, mm - km_)
    print(f'   πληροφορια περα απο αγορα (b) στη διαφορα, {lab}: γκολ {b:+.2f} (t {t:+.1f}) · xG {bx:+.2f} (t {tx:+.1f})')
# ===== 3 =====
print(NL + '3. ΔΟΚΙΜΗ: γκολ της ομαδας ΜΕ FotMob ×c στα ματς Β (c απο τις αλλες 3 σεζον) — προβλεψη και picks')
IB = [i for i in UI if cat(i) == 'B' and LH_N[i] > 0]
def ll(idx, c):
    s = 0.0
    for i in idx:
        a, b = LH_N[i], LA_N[i]
        if FMH[i]: a *= c
        else: b *= c
        s += GH[i] * math.log(a) - a + GA[i] * math.log(b) - b
    return s
GRID = np.round(np.arange(0.70, 1.11, 0.02), 2); CS = {}
for s_ in SEAS:
    tr = [i for i in IB if SEA[i] != s_]; te = [i for i in IB if SEA[i] == s_]
    c = GRID[np.argmax([ll(tr, g) for g in GRID])]; CS[s_] = c
    print(f'   τεστ {s_}: c = {c:.2f} · Δlog-lik {ll(te, c) - ll(te, 1.0):+.2f} (n{len(te)})')
print(f'   c με ολες: {GRID[np.argmax([ll(IB, g) for g in GRID])]:.2f}')
def picks_B(cmap):
    out = []
    for i in IB:
        c = cmap.get(SEA[i], 1.0); a, b = LH_N[i], LA_N[i]; oa_, ob_ = OH[i], OA[i]
        if FMH[i]: a *= c; oa_ *= c
        else: b *= c; ob_ *= c
        D = sdist(a, b); td = ES.tot_dist(oa_, ob_, DRAW_SCALE); fs = 1 if FMH[i] else -1
        for bk in ('Crown', 'SBOBET'):
            got = set()
            for h in HS:
                s = snap_ah(MIDS[i], bk, h)
                if s:
                    L, oh, oa = s
                    for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                        if not (1.70 <= o <= 2.10) or side in got: continue
                        if side == fs and ln <= -0.5: pw, pp = cover_q(D, side, ln); k = 'φαβ ΜΕ FotMob'
                        elif side != fs and ln >= 0.5: pw, pp = picks.p_cover(D, side, ln); k = 'dog ΧΩΡΙΣ FotMob'
                        else: continue
                        if edge(pw, pp, o) >= .10: got.add(side); out.append(dict(bk=bk, sea=SEA[i], k=k, pnl=picks.settle(GD[i], side, ln, o)))
                so = snap_ou(MIDS[i], bk, h)
                if so and 'ou' not in got:
                    L, o, un = so; po, pu = ES.p_over(td, L)
                    for nm, od, p, q_, th in (('over', o, po, pu, .08), ('under', un, pu, po, .14)):
                        if 1.70 <= od <= 2.10 and p * (od - 1) * (1 - picks.MARGIN) - q_ >= th:
                            got.add('ou'); out.append(dict(bk=bk, sea=SEA[i], k=nm, pnl=settle(GH[i] + GA[i], L, od, nm == 'over'))); break
    return pd.DataFrame(out)
P0 = picks_B({}); P1 = picks_B(CS)
for k in ('φαβ ΜΕ FotMob', 'dog ΧΩΡΙΣ FotMob', 'over', 'under'):
    print(f'   {k:18s} σημερα {cc(P0[P0.k == k])}')
    print(f'   {"":18s} με c   {cc(P1[P1.k == k])}')
