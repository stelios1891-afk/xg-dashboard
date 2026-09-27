# -*- coding: utf-8 -*-
"""
btts_vs_over_test.py — ΕΘΝΙΚΕΣ: ειναι το BTTS-Yes σημα απλως η τσεπη OVER μεταμφιεσμενη, ή προσθετει
πληροφορια για το ΠΩΣ μοιραζονται τα γκολ; (27/9/2026)

Αντιγραφο του εθνικου σκελους του btts_test.py (ιδιο δειγμα 972 μη-νεκρα 2122-2526, ιδιος λυτης αγορας
απο closing AH + O/U, ιδια λ μοντελου Μ1/Μ2/Μ3 απο intl_model_choice_v3 με T_MODE=live, Crown & SBOBET,
ενας αριθμος = μεσος των δυο βιβλιων, * = διαφωνια προσημου).

Αναλυσεις (ολες προ-δηλωμενες, ΜΙΑ εκτελεση):
 A) Επικαλυψη: απο τα BTTS-Yes picks (edge ≥8%, υποθετικη τιμη P_mkt+5%), ποσοστο με over edge ≥8%
    του ιδιου μοντελου στη closing O/U γραμμη/τιμη του ιδιου βιβλιου (intl_pricing.over_ev, T = T_of live)·
    και ποσοστο με T_mod − T_mkt ≥ 0.2 (T_mod = λh+λa μοντελου μετα το clamp, T_mkt = λh+λa αγορας).
 B) BTTS-Yes ROI: (i) ΜΕ over edge ≥8%, (ii) ΧΩΡΙΣ (<8%), (iii) ΧΩΡΙΣ και T_mod ≤ T_mkt + 0.1.
 C) Logit: y_btts ~ logit(Pk_btts) + logit(Pm_btts) + [logit(Pm_o2.5) − logit(Pk_o2.5)]  (Poisson(λh+λa), γραμμη 2.5)
    και «split»: + Δs, s = λ_weak/(λh+λa) μοντελο − αγορα (weak = η πλευρα με το μικροτερο λ ΑΓΟΡΑΣ).

Εξοδος: btts_vs_over_test_out.txt. ΔΕΝ αγγιζει picks.py / live αρχεια.
"""
import sys, os, json, glob, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')

EDGES = (0.05, 0.08, 0.10)
MARGIN_BTTS = 0.05
KG = 15
GRID = np.arange(KG)
FACTK = np.array([math.factorial(int(k)) for k in GRID], float)
ND = 2 * KG - 1                      # gd -14..14 / total 0..28
# one-hot πινακες (K*K, ND)
_I, _J = np.meshgrid(GRID, GRID, indexing='ij')
OH_GD = np.zeros((KG * KG, ND)); OH_GD[np.arange(KG * KG), (_I - _J).ravel() + KG - 1] = 1
OH_TOT = np.zeros((KG * KG, ND)); OH_TOT[np.arange(KG * KG), (_I + _J).ravel()] = 1
DVALS = np.arange(ND) - (KG - 1)     # gd τιμες
TVALS = np.arange(ND)                # total τιμες


def parts_of(L):
    q = round(L * 4) / 4
    return [q] if abs(q * 2 - round(q * 2)) < 1e-9 else [q - 0.25, q + 0.25]


def ah_weights(lines):
    """home καλυπτει αν gd + L > 0. Επιστρεφει (wW, wL) (N, ND)."""
    N = len(lines); wW = np.zeros((N, ND)); wL = np.zeros((N, ND))
    for i, L in enumerate(lines):
        for p in parts_of(L):
            wW[i] += (DVALS + p > 1e-9); wL[i] += (DVALS + p < -1e-9)
    return wW, wL


def ou_weights(lines):
    N = len(lines); wW = np.zeros((N, ND)); wL = np.zeros((N, ND))
    for i, L in enumerate(lines):
        for p in parts_of(L):
            wW[i] += (TVALS - p > 1e-9); wL[i] += (TVALS - p < -1e-9)
    return wW, wL


def joint(lh, la):
    ph = np.exp(-lh)[:, None] * lh[:, None] ** GRID[None, :] / FACTK[None, :]
    pa = np.exp(-la)[:, None] * la[:, None] ** GRID[None, :] / FACTK[None, :]
    return (ph[:, :, None] * pa[:, None, :]).reshape(len(lh), -1)


def fair_q(W, L):
    return W / np.maximum(W + L, 1e-12)


def solve_market(ah_line, oh, oa, ou_line, oo, ou_):
    """Διανυσματικη εμφωλευμενη διχοτομηση: εξω T (O/U), μεσα s (AH). Επιστρεφει λh, λa, resid."""
    ah_line = np.asarray(ah_line, float); ou_line = np.asarray(ou_line, float)
    qh = (1 / oh) / (1 / oh + 1 / oa); qo = (1 / oo) / (1 / oo + 1 / ou_)
    aW, aL = ah_weights(ah_line); oW, oL = ou_weights(ou_line)
    N = len(qh)

    def inner(T):
        lo = -T + 0.04; hi = T - 0.04
        for _ in range(32):
            s = 0.5 * (lo + hi)
            J = joint((T + s) / 2, (T - s) / 2); pg = J @ OH_GD
            f = fair_q((pg * aW).sum(1), (pg * aL).sum(1))
            up = f < qh
            lo = np.where(up, s, lo); hi = np.where(up, hi, s)
        return 0.5 * (lo + hi)

    Tlo = np.full(N, 0.4); Thi = np.full(N, 8.0)
    for _ in range(30):
        T = 0.5 * (Tlo + Thi); s = inner(T)
        J = joint((T + s) / 2, (T - s) / 2); pt = J @ OH_TOT
        f = fair_q((pt * oW).sum(1), (pt * oL).sum(1))
        up = f < qo
        Tlo = np.where(up, T, Tlo); Thi = np.where(up, Thi, T)
    T = 0.5 * (Tlo + Thi); s = inner(T)
    lh, la = (T + s) / 2, (T - s) / 2
    J = joint(lh, la); pg = J @ OH_GD; pt = J @ OH_TOT
    r1 = fair_q((pg * aW).sum(1), (pg * aL).sum(1)) - qh
    r2 = fair_q((pt * oW).sum(1), (pt * oL).sum(1)) - qo
    return lh, la, np.maximum(np.abs(r1), np.abs(r2))


def p_btts(lh, la):
    return (1 - np.exp(-np.asarray(lh))) * (1 - np.exp(-np.asarray(la)))


# ---------------- μετρικες ----------------
EPS = 1e-4
def clipp(p): return np.clip(p, EPS, 1 - EPS)
def logit(p): p = clipp(p); return np.log(p / (1 - p))


def logreg(X, y, offset=None):
    """IRLS. X χωρις σταθερα (προστιθεται). Επιστρεφει beta, se."""
    X = np.column_stack([np.ones(len(y)), X]); b = np.zeros(X.shape[1])
    off = np.zeros(len(y)) if offset is None else offset
    for _ in range(50):
        eta = X @ b + off; p = 1 / (1 + np.exp(-eta)); w = p * (1 - p)
        H = X.T @ (X * w[:, None]); g = X.T @ (y - p)
        step = np.linalg.solve(H, g); b = b + step
        if np.max(np.abs(step)) < 1e-10:
            break
    eta = X @ b + off; p = 1 / (1 + np.exp(-eta)); w = p * (1 - p)
    cov = np.linalg.inv(X.T @ (X * w[:, None]))
    return b, np.sqrt(np.diag(cov))


def metrics(pm, pk, y):
    """Brier/logloss μοντελο vs αγορα + paired διαφορα ±SE· regression coef μοντελου."""
    pm = clipp(pm); pk = clipp(pk); y = np.asarray(y, float); n = len(y)
    bm = (pm - y) ** 2; bk = (pk - y) ** 2
    lm = -(y * np.log(pm) + (1 - y) * np.log(1 - pm)); lk = -(y * np.log(pk) + (1 - y) * np.log(1 - pk))
    db = bm - bk; dl = lm - lk
    out = dict(n=n, base=y.mean(), pm=pm.mean(), pk=pk.mean(),
               brier_m=bm.mean(), brier_k=bk.mean(), dbrier=db.mean(), dbrier_se=db.std(ddof=1) / np.sqrt(n),
               ll_m=lm.mean(), ll_k=lk.mean(), dll=dl.mean(), dll_se=dl.std(ddof=1) / np.sqrt(n))
    if n >= 30:
        b, se = logreg(np.column_stack([logit(pk), logit(pm)]), y)
        out.update(b_mkt=b[1], b_mod=b[2], t_mod=b[2] / se[2])
        d = logit(pm) - logit(pk)
        b2, se2 = logreg(d[:, None], y, offset=logit(pk))          # αγορα ως offset (συντ. 1)
        out.update(b_delta=b2[1], t_delta=b2[1] / se2[1])
    return out


def roi_table(pm, pk, y):
    """ΥΠΟΘΕΤΙΚΟ: τιμες BTTS Yes/No = P_mkt με 5% margin αναλογικα. Flat 1u."""
    pm = np.asarray(pm); pk = np.asarray(pk); y = np.asarray(y)
    oy = 1 / (pk * (1 + MARGIN_BTTS)); on = 1 / ((1 - pk) * (1 + MARGIN_BTTS))
    ey = pm * oy - 1; en = (1 - pm) * on - 1
    res = {}
    for thr in EDGES:
        by = (ey >= thr) & (ey >= en); bn = (en >= thr) & (en > ey)
        pnl = np.concatenate([np.where(y[by] == 1, oy[by] - 1, -1.0), np.where(y[bn] == 0, on[bn] - 1, -1.0)])
        res[thr] = (len(pnl), pnl.mean() if len(pnl) else np.nan,
                    pnl.std(ddof=1) / np.sqrt(len(pnl)) if len(pnl) > 1 else np.nan, int(by.sum()), int(bn.sum()))
    py = np.where(y == 1, oy - 1, -1.0); pn = np.where(y == 0, on - 1, -1.0)
    res['allY'] = (len(py), py.mean(), py.std(ddof=1) / np.sqrt(len(py)), len(py), 0)
    res['allN'] = (len(pn), pn.mean(), pn.std(ddof=1) / np.sqrt(len(pn)), 0, len(pn))
    return res


def calib_delta(pm, pk, y, nb=5):
    pm = np.asarray(pm); pk = np.asarray(pk); y = np.asarray(y, float)
    d = pm - pk; qs = np.quantile(d, np.linspace(0, 1, nb + 1)); rows = []
    for i in range(nb):
        m = (d >= qs[i]) & (d <= qs[i + 1]) if i == nb - 1 else (d >= qs[i]) & (d < qs[i + 1])
        rows.append((int(m.sum()), d[m].mean(), pm[m].mean(), pk[m].mean(), y[m].mean(), (y[m] - pk[m]).mean()))
    return rows


def calib_dec(p, y, nb=10):
    p = np.asarray(p); y = np.asarray(y, float); qs = np.quantile(p, np.linspace(0, 1, nb + 1)); rows = []
    for i in range(nb):
        m = (p >= qs[i]) & (p <= qs[i + 1]) if i == nb - 1 else (p >= qs[i]) & (p < qs[i + 1])
        rows.append((int(m.sum()), p[m].mean(), y[m].mean()))
    return rows



# =====================================================================================
from intl_pricing import over_ev

print('BTTS vs OVER — ΕΘΝΙΚΕΣ: προσθετει το BTTS πληροφορια περα απο την τσεπη over;')
print('=' * 100)
print("""ΠΡΟ-ΔΗΛΩΜΕΝΑ ΚΡΙΤΗΡΙΑ (γραφτηκαν ΠΡΙΝ τα αποτελεσματα, ΜΙΑ εκτελεση):
  Το BTTS προσθετει πληροφορια περα απο τα overs για ενα μοντελο ΑΝ:
   (1) ο συντελεστης του logit(P_mod_btts) στο C (με ελεγχο για τη διαφωνια συνολου γκολ) μενει > 0 με t ≥ 2 pooled, ΚΑΙ
   (2) B(ii) ROI BTTS-Yes ΧΩΡΙΣ over edge ≥8% ειναι θετικο pooled ΚΑΙ σε ≥3/5 σεζον.
  (μεσος Crown/SBOBET). Συνολικη ετυμηγορια κριτηριων: ισχυουν και τα δυο για ≥2 απο τα 3 μοντελα.
  Η «split» εκδοχη του C τυπωνεται ως πληροφορια (δεν μπαινει στο κριτηριο).
""")

print('[B] ΕΘΝΙΚΕΣ — χτισιμο (intl_model_choice_v3, ιδιο με btts_test) ...', flush=True)
src = open('intl_model_choice_v3.py', encoding='utf-8').read()
G = {'__name__': 'btts'}
import io, contextlib
class _Buf(io.StringIO):
    def reconfigure(self, *a, **k): pass
_buf = _Buf()
with contextlib.redirect_stdout(_buf):
    exec(src[:src.index('bets = []')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass'), G)
D, MODELS, T_of, A_GOAL = (G[k] for k in ('D', 'MODELS', 'T_of', 'A_GOAL'))
MI = pd.read_csv('intl_matches.csv', dtype={'mid': str})
KO = {m: pd.Timestamp(d).tz_localize('UTC').timestamp() for m, d in zip(MI.mid, MI.date)}


def hk(v):
    v = float(v); return v + 1 if v < 1.5 else v


def line_of(s):
    s = str(s)
    if '/' in s:
        a, b = s.split('/'); return (float(a) + float(b)) / 2
    return float(s)


def ok_row(x):
    return x[1] in ('', None) and not x[7] and x[4] not in (None, '') and x[5] not in (None, '', '0') and x[6] not in (None, '', '0')


ROWS = {}
for f in glob.glob('nowgoal_intl_odds/*.jsonl'):
    for ln in open(f, encoding='utf-8'):
        r = json.loads(ln)
        if r.get('cid') not in (3, 31):
            continue
        mid = str(r['mid']); k = KO.get(mid)
        if k is None:
            continue
        rc = {'ah': [], 'ou': []}
        for x in (r.get('ah') or []):
            if ok_row(x) and x[0] < k:
                try: rc['ah'].append(((k - x[0]) / 3600, -line_of(x[4]), hk(x[5]), hk(x[6])))
                except Exception: pass
        for x in (r.get('ou') or []):
            if ok_row(x) and x[0] < k:
                try: rc['ou'].append(((k - x[0]) / 3600, line_of(x[4]), hk(x[5]), hk(x[6])))
                except Exception: pass
        rc['ah'].sort(key=lambda z: -z[0]); rc['ou'].sort(key=lambda z: -z[0])
        ROWS[(mid, r['cid'])] = rc

NSEAS = sorted(D.season.unique())
Dn = D[~D.dead].copy()
Dn['hg'] = ((Dn.tot + Dn.gd) / 2).round().astype(int); Dn['ag'] = ((Dn.tot - Dn.gd) / 2).round().astype(int)
Dn['y'] = ((Dn.hg > 0) & (Dn.ag > 0)).astype(int)
for m in MODELS:
    T = np.array([T_of(getattr(r, f'd_{m}'), r) for r in Dn.itertuples()])
    s_ = A_GOAL * Dn[f'd_{m}'].values
    lhm = np.maximum((T + s_) / 2, .15); lam = np.maximum((T - s_) / 2, .15)
    Dn[f'pm_{m}'] = p_btts(lhm, lam)
    Dn[f'T_{m}'] = T; Dn[f'lh_{m}'] = lhm; Dn[f'la_{m}'] = lam
print(f'  αγωνιστικα (μη νεκρα) με diff: {len(Dn)} · σεζον {NSEAS}')


def p_over25(lsum):
    lsum = np.asarray(lsum, float)
    return 1 - np.exp(-lsum) * (1 + lsum + lsum ** 2 / 2)


BOOKS = ((3, 'Crown'), (31, 'SBOBET'))
BK = {}
for cid, bname in BOOKS:
    rows = []
    for r in Dn.itertuples():
        rc = ROWS.get((str(r.mid), cid))
        if not rc or not rc['ah'] or not rc['ou']:
            continue
        a = rc['ah'][-1]; u = rc['ou'][-1]
        rows.append((r.Index, a[1], a[2], a[3], u[1], u[2], u[3]))
    X = pd.DataFrame(rows, columns=['ix', 'ah', 'oh', 'oa', 'oul', 'oo', 'ou']).set_index('ix')
    X = X[(X.oh > 1) & (X.oa > 1) & (X.oo > 1) & (X.ou > 1)]
    lh, la, resid = solve_market(X.ah.values, X.oh.values, X.oa.values, X.oul.values, X.oo.values, X.ou.values)
    X['pk'] = p_btts(lh, la); X['resid'] = resid; X['lsum'] = lh + la; X['lh_k'] = lh; X['la_k'] = la
    nb = int((resid > 0.005).sum()); X = X[X.resid <= 0.005]
    B = Dn.loc[X.index].join(X[['pk', 'lsum', 'lh_k', 'la_k', 'oul', 'oo']])
    B['pko'] = p_over25(B.lsum)
    weak_home = B.lh_k < B.la_k
    B['sk'] = np.where(weak_home, B.lh_k, B.la_k) / B.lsum
    for m in MODELS:
        B[f'oe_{m}'] = [over_ev(T, L, o) for T, L, o in zip(B[f'T_{m}'], B.oul, B.oo)]
        B[f'Tm_{m}'] = B[f'lh_{m}'] + B[f'la_{m}']
        B[f'pmo_{m}'] = p_over25(B[f'Tm_{m}'])
        B[f'sm_{m}'] = np.where(weak_home, B[f'lh_{m}'], B[f'la_{m}']) / B[f'Tm_{m}']
    BK[bname] = B
    print(f'  {bname}: ματς με closing AH+O/U {len(X) + nb} · αντιστροφη ✗ {nb} · τελικο {len(B)} · '
          f'μεσο λ_m {B.lsum.mean():.3f} vs actual {B.tot.mean():.3f}')


def avg2(a, b):
    return (a + b) / 2


def flag(a, b):
    return '*' if (np.sign(a) != np.sign(b) and a != 0 and b != 0) else ' '


def sub(bname, s):
    return BK[bname] if s == 'POOLED' else BK[bname][BK[bname].season == s]


def yes_mask(d, m, thr=0.08):
    pm = d[f'pm_{m}'].values; pk = d.pk.values
    oy = 1 / (pk * (1 + MARGIN_BTTS)); on = 1 / ((1 - pk) * (1 + MARGIN_BTTS))
    ey = pm * oy - 1; en = (1 - pm) * on - 1
    return (ey >= thr) & (ey >= en), oy


def roi(pnl):
    n = len(pnl)
    if n == 0:
        return 0, np.nan, np.nan
    return n, pnl.mean(), (pnl.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan)



# ---------------- 27/9 ΣΥΝΑΙΝΕΣΗ (αιτημα Στελιου): BTTS Yes οταν ≥2 απο τα 3 μοντελα το δινουν (edge ≥8%) ----------------
print(chr(10) + '=' * 100)
print('ΣΥΝΑΙΝΕΣΗ ≥2/3 — BTTS Yes (edge ≥8%, υποθετικη τιμη = P_mkt + 5%) · μεσος Crown/SBOBET (* = διαφωνια προσημου)')
SEAS_ = sorted(set(BK['Crown'].season))
def cons_rows(d, split):
    ys = [yes_mask(d, m)[0] for m in MODELS]; oy = yes_mask(d, MODELS[0])[1]
    cy = (np.sum(ys, axis=0) >= 2)
    co = (np.sum([d[f'oe_{m}'].values >= 0.08 for m in MODELS], axis=0) >= 2)
    sel = cy if split == 'ολα' else (cy & co if split == 'με over (≥2 μοντελα)' else cy & ~co)
    pnl = np.where(d.y.values[sel] == 1, oy[sel] - 1, -1.0)
    return roi(pnl)
for split in ('ολα', 'με over (≥2 μοντελα)', 'ΧΩΡΙΣ over'):
    cells = []
    for s_ in SEAS_ + ['POOLED']:
        c = cons_rows(sub('Crown', s_), split); b = cons_rows(sub('SBOBET', s_), split)
        if c[0] and b[0]:
            cells.append(f"{(c[0] + b[0]) / 2:4.0f} {avg2(c[1], b[1]) * 100:+6.1f}±{avg2(c[2] if np.isfinite(c[2]) else 0, b[2] if np.isfinite(b[2]) else 0) * 100:4.1f}{flag(c[1], b[1])}")
        else:
            cells.append('   —')
    print(f"  {split:>22s} | " + ' | '.join(f'{x:>17s}' for x in cells) + f"   ({' / '.join(SEAS_)} / POOLED)")
