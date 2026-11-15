"""UFC τεστ 15: ποιος συνδυασμός μηχανισμών; Όλες οι φόρμουλες (255) από τις 8 ομάδες του τεστ 14, αμερικανικές τιμές, 2017-26.

Ορισμένα από πριν. Βαθμός φόρμουλας = μέσος log-loss μίξης άνοιγμα και κλείσιμο (μικρότερο = καλύτερο)· μονάδες/ROI ≥5 πόντων δίπλα.
  Τ2 όλοι οι συνδυασμοί με walk-forward
  Τ3 επιλογή μόνο με παρελθόν: για κάθε Υ η φόρμουλα με τον καλύτερο βαθμό στα 2014..Υ−1, κρίση στο Υ
     (και παραλλαγή: η μικρότερη με t<1 από την πρώτη)
  Τ4 placebo: η ομάδα ανακατεμένη ανάμεσα σε αγώνες της ίδιας χρονιάς, N φορές, απέναντι στην πλήρη χωρίς την ομάδα
  Τ5 Reality Check (White): η καλύτερη από τις 254 ξεχωρίζει από τη βάση περισσότερο απ' όσο θα έφερνε η τύχη;
  Τ6 bootstrap ανά βραδιά, 1000 φορές: πιθανότητα πρώτης θέσης, μέση συνεισφορά κάθε μηχανισμού σε όλα τα ζεύγη με/χωρίς
  Τ7 CLV: στα picks ανοίγματος, τιμή μας / τιμή κλεισίματος − 1
  LOSO: οι τελικές φόρμουλες με εκπαίδευση σε όλες τις άλλες χρονιές
Κριτήριο μηχανισμού: Τ6 βελτιώνει ≥90% ΚΑΙ Τ4 πάνω από το 95% των placebo ΚΑΙ Τ3 επιλέγεται σε ≥6/10 χρονιές.
Φόρμουλα: η μικρότερη που η πρώτη δεν την κερδίζει σε ≥90% των επαναλήψεων. Τ5 p>.05: δεν υπάρχει «νικήτρια».
T15_SAFE=1: ασφαλείς τιμές. Άνοιγμα = μέση τιμή βιβλίων στο πρώτο σημείο μετά την 1η τιμή (bfo_spark σ1), κλείσιμο = μέσο εύρους
για τη μίξη και ΧΕΙΡΟΤΕΡΗ τιμή για το κέρδος· CLV = σ1 / μέσο κλεισίματος. Βγαίνουν οι αγώνες 2017-26 χωρίς σ1.
Θέλει UFC_DATA και T15_CACHE (αρχείο ενδιάμεσης αποθήκευσης, ξανατρέχει από εκεί).
"""
import os

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
os.environ["UFC_FEATURES"] = "ufc_features_causal.csv"
import itertools
import pickle
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd

import t3_mechanisms as t3
from t2_age_repl import DATA
from t10_own_engine import build, ridge, roi
from t11_level_select import Ls, cv_fit, engine_wf, level_features, mix_wf
from t14_drop_mechanisms import BASE, GROUPS, profit

pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 300)
lg, sig = t3.lg, t3.sig
NAMES = list(GROUPS)
FULL = (1 << len(NAMES)) - 1
CORE = sum(1 << NAMES.index(g) for g in ("ηλικία", "χτυπήματα", "έδρα"))
N_PL, N_BOOT, WORKERS = 40, 1000, 4
CACHE = os.environ.get("T15_CACHE", "t15_cache.pkl")
SAFE = os.environ.get("T15_SAFE") == "1"
tstat = lambda d: d.mean() / (d.std() / np.sqrt(len(d)))
label = lambda m: " + ".join(n for i, n in enumerate(NAMES) if m >> i & 1)
size = lambda m: bin(m).count("1")
cols_of = lambda m: [c for i, n in enumerate(NAMES) if m >> i & 1 for c in GROUPS[n]]
_G = {}


def init(path):
    _G.update(pickle.load(open(path + ".input", "rb")))


def job(key):
    """key: ("c", μάσκα) ή ("p", όνομα ομάδας, επανάληψη). Επιστρέφει τις μίξεις άνοιγμα/κλείσιμο από το 2014."""
    D, w, y = _G["D"], _G["w"], _G["y"]
    if key[0] == "c":
        q = engine_wf(D, cols_of(key[1]), w, y)
    else:
        g = GROUPS[key[1]]
        rng = np.random.default_rng(1000 * NAMES.index(key[1]) + key[2])
        D2 = D.copy()
        for Y in np.unique(y):
            i = np.where(y == Y)[0]
            D2.iloc[i, [D2.columns.get_loc(c) for c in g]] = D.iloc[rng.permutation(i)][g].values
        q = engine_wf(D2, BASE, w, y)
    return key, mix_wf(_G["po"], q, w, y, 2014).astype(np.float32), mix_wf(_G["pc"], q, w, y, 2014).astype(np.float32)


def clv(q, o):
    """CLV ανά αγώνα σε μονάδες για τα picks ανοίγματος ≥5 πόντων· 0 όπου δεν ποντάρουμε."""
    p = o.f1_p_open.values
    x = np.zeros(len(q))
    a, b = q - p >= .05, p - q >= .05
    c1, c2 = (o.f1_close_mid, o.f2_close_mid) if SAFE else (o.f1_close_dec, o.f2_close_dec)
    x[a] = (o.f1_open_dec.values / c1.values - 1)[a]
    x[b] = (o.f2_open_dec.values / c2.values - 1)[b]
    return x


def safe_prices(o, D, w):
    """Αντικαθιστά τις τιμές με τις ασφαλείς και βγάζει τους αγώνες 2017-26 χωρίς σ1 (πριν το 2017 μένει η 1η τιμή, μόνο για εκπαίδευση)."""
    o = o.reset_index(drop=True).copy()
    sp = pd.read_csv(DATA / "bfo_spark.csv")
    sp = sp[sp.n == 10].drop_duplicates(["matchup_id", "fighter_url"])
    X = pd.read_csv(DATA / "bfo_fighter_odds.csv").drop_duplicates(["matchup_id", "fighter_url"])
    dec = lambda a: np.where(a > 0, 1 + a / 100, 1 + 100 / np.abs(a))
    s1, wc = {}, {}
    for s in ("1", "2"):
        u = f"f{s}_bfo_url"
        s1[s] = o[["matchup_id", u]].merge(sp[["matchup_id", "fighter_url", "s1"]].rename(columns={"fighter_url": u}), on=["matchup_id", u], how="left").s1.values
        m = o[["matchup_id", u]].merge(X[["matchup_id", "fighter_url", "close_lo", "close_hi"]].rename(columns={"fighter_url": u}), on=["matchup_id", u], how="left")
        wc[s] = np.fmin(dec(pd.to_numeric(m.close_lo, errors="coerce").values), dec(pd.to_numeric(m.close_hi, errors="coerce").values))
    has = np.isfinite(s1["1"]) & np.isfinite(s1["2"])
    p = (1 / s1["1"]) / (1 / s1["1"] + 1 / s1["2"])
    o["f1_close_mid"], o["f2_close_mid"] = o.f1_close_dec, o.f2_close_dec
    o["f1_p_open"] = np.where(has, p, o.f1_p_open)
    o["f1_open_dec"], o["f2_open_dec"] = np.where(has, s1["1"], o.f1_open_dec), np.where(has, s1["2"], o.f2_open_dec)
    o["f1_close_dec"] = np.where(np.isfinite(wc["1"]), wc["1"], o.f1_close_dec)
    o["f2_close_dec"] = np.where(np.isfinite(wc["2"]), wc["2"], o.f2_close_dec)
    keep = has | (o.y.values < 2017)
    print(f"ασφαλείς τιμές: βγαίνουν {(~keep).sum()} αγώνες 2017-26 χωρίς σ1", flush=True)
    return o[keep].reset_index(drop=True), D.reset_index(drop=True)[keep].reset_index(drop=True), w[keep]


def loso(D, cols, w, y, p):
    """Κάθε χρονιά ≥2012 με μηχανή και μίξη εκπαιδευμένες σε όλες τις άλλες."""
    qe = np.full(len(y), np.nan)
    for Y in range(2012, 2027):
        tr = y != Y
        sd = D.loc[tr, cols].std().replace(0, 1)
        X = (D[cols] / sd).fillna(0.0).values
        qe[y == Y] = sig(X[y == Y] @ ridge(X[tr], w[tr], cv_fit(X[tr], w[tr], y[tr])))
    Z = np.c_[lg(p), lg(np.clip(qe, 1e-4, 1 - 1e-4))]
    q = np.full(len(y), np.nan)
    for Y in range(2017, 2027):
        tr = (y >= 2012) & (y != Y)
        q[y == Y] = sig(Z[y == Y] @ t3.fit(Z[tr], w[tr])[0])
    return q


def main():
    o, D, w = build()
    D = level_features(o, D)
    if SAFE:
        o, D, w = safe_prices(o, D, w)
    y = o.y.values
    te = y >= 2017
    po, pc = o.f1_p_open.values, o.f1_p_close.values
    pickle.dump(dict(D=D[BASE], w=w, y=y, po=po, pc=pc), open(CACHE + ".input", "wb"))
    R = pickle.load(open(CACHE, "rb")) if os.path.exists(CACHE) else {}
    todo = [("c", m) for m in range(1, FULL + 1)] + [("p", n, i) for n in NAMES for i in range(N_PL)]
    todo = [k for k in todo if k not in R]
    print(f"αγώνες {len(o)} · 2017-26 {te.sum()} · υπόλοιπες μηχανές {len(todo)}", flush=True)
    if todo:
        with ProcessPoolExecutor(WORKERS, initializer=init, initargs=(CACHE,)) as ex:
            fs = [ex.submit(job, k) for k in todo]
            for n, f in enumerate(as_completed(fs), 1):
                k, a, b = f.result()
                R[k] = (a, b)
                if n % 25 == 0 or n == len(todo):
                    pickle.dump(R, open(CACHE, "wb"))
                    print(f"  {n}/{len(todo)}", flush=True)

    # --- πίνακες ανά αγώνα, 2017-26
    K = list(range(1, FULL + 1))
    Qo = np.array([R[("c", m)][0] for m in K], float)
    Qc = np.array([R[("c", m)][1] for m in K], float)
    idx = {m: i for i, m in enumerate(K)}
    ou = o[te].reset_index(drop=True)
    LLo = np.array([Ls(q[te], w[te]) for q in Qo])
    LLc = np.array([Ls(q[te], w[te]) for q in Qc])
    S = (LLo + LLc) / 2
    Uo = np.array([profit(q, o, "open", w)[te] for q in Qo])
    Uc = np.array([profit(q, o, "close", w)[te] for q in Qc])
    C = np.array([clv(q[te], ou) for q in Qo])
    r = roi(Qo[idx[FULL]], o, "open", te, w, .05)
    r2 = roi(Qc[idx[FULL]], o, "close", te, w, .05)
    print(f"\nΕΛΕΓΧΟΣ βάσης (πρώτη τιμή +12.9 n1951 · +7.1 n870· ασφαλείς περίπου +9.4 n1648 · +4.8 n870): {r['ROI']:+.1f} n{r['n']} · {r2['ROI']:+.1f} n{r2['n']}", flush=True)

    # --- Τ6 bootstrap ανά βραδιά
    ev, _ = pd.factorize(ou.date)
    E = ev.max() + 1
    nE = np.bincount(ev, minlength=E).astype(float)
    per_ev = lambda A: np.array([np.bincount(ev, a, minlength=E) for a in A])  # K × E
    aS, aUo, aUc, aC = per_ev(S), per_ev(Uo), per_ev(Uc), per_ev(C)
    rng = np.random.default_rng(15)
    W = rng.multinomial(E, np.ones(E) / E, N_BOOT).astype(float)  # B × E
    den = W @ nE
    bS = (W @ aS.T) / den[:, None]  # B × K
    sc = len(ev) / den[:, None]  # μονάδες στην κλίμακα του πλήρους δείγματος
    bUo, bUc, bC = (W @ aUo.T) * sc, (W @ aUc.T) * sc, (W @ aC.T) * sc
    s0 = S.mean(1)
    P1 = np.bincount(bS.argmin(1), minlength=len(K)) / N_BOOT
    best = K[int(s0.argmin())]
    Pb = (bS - bS[:, [idx[best]]] > 0).mean(0)  # πόσο συχνά η πρώτη κερδίζει την κ
    elig = [m for m in K if Pb[idx[m]] < .90]
    small = min(elig, key=lambda m: (size(m), s0[idx[m]]))
    T = pd.DataFrame(dict(φόρμουλα=[label(m) for m in K], μηχ=[size(m) for m in K], βαθμός=s0, LL_op=LLo.mean(1), LL_cl=LLc.mean(1),
                          μον_op=Uo.sum(1), μον_cl=Uc.sum(1), n_op=(Uo != 0).sum(1), n_cl=(Uc != 0).sum(1), CLV_μον=C.sum(1),
                          CLV_μέσο=C.sum(1) / (C != 0).sum(1).clip(1) * 100, Π_πρώτη=P1, Π_χάνει_από_1η=Pb))
    T.to_csv(DATA / ("t15_combos_safe.csv" if SAFE else "t15_combos.csv"), index=False)
    print("\n=== Τ2 κορυφή με βαθμό log-loss (15 πρώτες) ===")
    print(T.sort_values("βαθμός").head(15).round(4).to_string(index=False))
    print("\n=== κορυφή με μονάδες άνοιγμα (10) ===")
    print(T.sort_values("μον_op", ascending=False).head(10).round(4).to_string(index=False))
    print("\n=== κορυφή με μονάδες κλείσιμο (10) ===")
    print(T.sort_values("μον_cl", ascending=False).head(10).round(4).to_string(index=False))
    print(f"\nφόρμουλες που η πρώτη ΔΕΝ κερδίζει σε ≥90%: {len(elig)}/{len(K)} · η πρώτη κέρδισε ως πρώτη σε {P1[idx[best]]:.1%} των επαναλήψεων")
    print(f"ΠΡΩΤΗ: {label(best)}\nΜΙΚΡΟΤΕΡΗ ΕΝΤΟΣ ΘΟΡΥΒΟΥ: {label(small)}")

    # --- Τ5 Reality Check
    print("\n=== Τ5 Reality Check: η καλύτερη των υπολοίπων ξεχωρίζει από τη φόρμουλα-μέτρο; ===")
    rc = []
    for bn, b in (("πλήρης", FULL), ("3 μηχανισμοί", CORE)):
        for mn, boot, real, sgn in (("log-loss", bS, s0, -1), ("μον. άνοιγμα", bUo, Uo.sum(1), 1), ("μον. κλείσιμο", bUc, Uc.sum(1), 1)):
            j = idx[b]
            keep = np.arange(len(K)) != j
            d = sgn * (real - real[j])[keep]
            db = sgn * (boot - boot[:, [j]])[:, keep]
            V, Vb = d.max(), (db - d).max(1)
            rc.append(dict(μέτρο_απέναντι=bn, κριτήριο=mn, καλύτερη_διαφορά=V, p=(Vb >= V).mean(), καλύτερη=label(K[np.delete(np.arange(len(K)), j)[d.argmax()]])))
    print(pd.DataFrame(rc).round(4).to_string(index=False))

    # --- Τ3 επιλογή μόνο με παρελθόν
    print("\n=== Τ3 επιλογή μόνο με παρελθόν ===")
    S_all = (np.array([Ls(q, w) for q in Qo]) + np.array([Ls(q, w) for q in Qc])) / 2
    sel, sel2 = {}, {}
    for Y in range(2017, 2027):
        h = (y >= 2014) & (y < Y)
        sh = S_all[:, h]
        i = int(sh.mean(1).argmin())
        sel[Y] = K[i]
        t = (sh - sh[i]).mean(1) / ((sh - sh[i]).std(1).clip(1e-9) / np.sqrt(h.sum()))
        sel2[Y] = min([K[j] for j in np.where(t < 1)[0]], key=lambda m: (size(m), sh[idx[m]].mean()))
        print(f"  {Y}: πρώτη [{label(sel[Y])}] · μικρότερη [{label(sel2[Y])}]")
    rows = []
    pick = lambda Q, s: np.concatenate([Q[idx[s[Y]]][y == Y] for Y in range(2017, 2027)])
    order = np.concatenate([np.where(y == Y)[0] for Y in range(2017, 2027)])
    for nm, s in (("επιλογή: πρώτη", sel), ("επιλογή: μικρότερη", sel2), ("πάντα πλήρης", {Y: FULL for Y in sel}), ("πάντα 3 μηχανισμοί", {Y: CORE for Y in sel})):
        qo, qc = np.full(len(y), np.nan), np.full(len(y), np.nan)
        qo[order], qc[order] = pick(Qo, s), pick(Qc, s)
        a, b = roi(qo, o, "open", te, w, .05), roi(qc, o, "close", te, w, .05)
        rows.append(dict(φόρμουλα=nm, LL_op=Ls(qo[te], w[te]).mean(), ROI_op=a["ROI"], SE_op=a["SE"], n_op=a["n"], μον_op=profit(qo, o, "open", w)[te].sum(),
                         LL_cl=Ls(qc[te], w[te]).mean(), ROI_cl=b["ROI"], SE_cl=b["SE"], n_cl=b["n"], μον_cl=profit(qc, o, "close", w)[te].sum()))
    print(pd.DataFrame(rows).round(4).to_string(index=False))

    # --- Τ4 placebo
    print(f"\n=== Τ4 placebo ({N_PL} ανακατέματα ανά ομάδα): κέρδος σε σχέση με την πλήρη χωρίς την ομάδα ===")
    pl = {}
    for n in NAMES:
        wo = FULL ^ (1 << NAMES.index(n))
        s_wo, uo_wo, uc_wo = s0[idx[wo]], Uo[idx[wo]].sum(), Uc[idx[wo]].sum()
        D_s, D_o, D_c = [], [], []
        for i in range(N_PL):
            a, b = R[("p", n, i)]
            a, b = np.asarray(a, float), np.asarray(b, float)
            D_s.append(s_wo - ((Ls(a[te], w[te]) + Ls(b[te], w[te])) / 2).mean())
            D_o.append(profit(a, o, "open", w)[te].sum() - uo_wo)
            D_c.append(profit(b, o, "close", w)[te].sum() - uc_wo)
        D_s, D_o, D_c = np.array(D_s), np.array(D_o), np.array(D_c)
        rs, ro, rc_ = s_wo - s0[idx[FULL]], Uo[idx[FULL]].sum() - uo_wo, Uc[idx[FULL]].sum() - uc_wo
        pl[n] = (D_s < rs).mean()
        print(f"  {n}: log-loss αληθινό {rs:+.5f} · placebo 95% {np.quantile(D_s, .95):+.5f} · μεγαλύτερο {D_s.max():+.5f} · κάτω από αληθινό {pl[n]:.0%}"
              f" | μον. άνοιγμα {ro:+.0f} vs placebo 95% {np.quantile(D_o, .95):+.0f} ({(D_o < ro).mean():.0%})"
              f" | μον. κλείσιμο {rc_:+.0f} vs placebo 95% {np.quantile(D_c, .95):+.0f} ({(D_c < rc_).mean():.0%})")

    # --- Τ6 μηχανισμοί + τελικός πίνακας
    print("\n=== Μηχανισμοί: μέση συνεισφορά σε όλα τα ζεύγη με/χωρίς (Τ6), placebo (Τ4), επιλογή (Τ3), CLV (Τ7) ===")
    rows = []
    for g, n in enumerate(NAMES):
        pairs = [(idx[m], idx[m ^ (1 << g)]) for m in K if m >> g & 1 and m ^ (1 << g)]
        A, B = [p[0] for p in pairs], [p[1] for p in pairs]
        ms, bs = (s0[A] - s0[B]).mean(), (bS[:, A] - bS[:, B]).mean(1)
        mo, bo = (Uo[A].sum(1) - Uo[B].sum(1)).mean(), (bUo[:, A] - bUo[:, B]).mean(1)
        mc, bc = (Uc[A].sum(1) - Uc[B].sum(1)).mean(), (bUc[:, A] - bUc[:, B]).mean(1)
        mC, bcl = (C[A].sum(1) - C[B].sum(1)).mean(), (bC[:, A] - bC[:, B]).mean(1)
        yrs = sum(sel[Y] >> g & 1 for Y in sel)
        ok = (bs < 0).mean() >= .9 and pl[n] >= .95 and yrs >= 6
        rows.append(dict(μηχανισμός=n, δ_βαθμός=ms, Π_βελτ=(bs < 0).mean(), placebo=pl[n], χρονιές_Τ3=yrs, δ_μον_op=mo, Π_op=(bo > 0).mean(), δ_μον_cl=mc, Π_cl=(bc > 0).mean(),
                         δ_CLV=mC, Π_CLV=(bcl > 0).mean(), ΠΕΡΝΑ=ok))
    print(pd.DataFrame(rows).round(4).to_string(index=False))

    # --- LOSO + ανά χρονιά για τις τελικές
    print("\n=== LOSO και ανά χρονιά, τελικές φόρμουλες ===")
    fin = {"πλήρης": FULL, "3 μηχανισμοί": CORE, "πρώτη": best, "μικρότερη": small}
    for nm, m in fin.items():
        cols = cols_of(m)
        qo, qc = loso(D, cols, w, y, po), loso(D, cols, w, y, pc)
        a, b = roi(qo, o, "open", te, w, .05), roi(qc, o, "close", te, w, .05)
        yo = pd.Series(Uo[idx[m]]).groupby(ou.date.str[:4]).sum()
        yc = pd.Series(Uc[idx[m]]).groupby(ou.date.str[:4]).sum()
        print(f"  {nm} [{label(m)}]\n    LOSO άνοιγμα LL {Ls(qo[te], w[te]).mean():.4f} ROI {a['ROI']:+.1f} ±{a['SE']:.1f} n{a['n']} χρ {a['χρ']} · κλείσιμο LL {Ls(qc[te], w[te]).mean():.4f} ROI {b['ROI']:+.1f} ±{b['SE']:.1f} n{b['n']} χρ {b['χρ']}"
              f"\n    walk-forward μονάδες ανά χρονιά, άνοιγμα {yo.round(0).astype(int).to_dict()} · χωρίς την καλύτερη {yo.sum() - yo.max():.0f}"
              f"\n    κλείσιμο {yc.round(0).astype(int).to_dict()} · χωρίς την καλύτερη {yc.sum() - yc.max():.0f}"
              f"\n    CLV picks ανοίγματος: μέσος {C[idx[m]].sum() / max((C[idx[m]] != 0).sum(), 1) * 100:+.2f}% · σύνολο {C[idx[m]].sum():.0f} μον.")


if __name__ == "__main__":
    main()
