"""UFC τεστ 17: μηχανή τελειωμάτων για Over/Under 2.5 και 1.5 γύρων, αγώνες 3 γύρων. Τιμές κλεισίματος 7 αμερικανικών βιβλίων 2021-26 (BFO).

Η μηχανή μαθαίνει από το αποτέλεσμα όλων των αγώνων 3 γύρων 2008+ (δεν θέλει τιμές), με στοιχεία μόνο από πριν τον αγώνα, και κάθε χρονιά Υ βλέπει μόνο <Υ.
Ομάδες (άθροισμα των δύο μαχητών): τελειώματα, νοκ ντάουν, υποταγές, χτυπήματα, πάλη, κατηγορία, ηλικία, διαφορά δυνάμεων (|logit| τιμής νικητή).
Μίξη: logit(Over) = α + β·logit(αγορά) + γ·logit(μηχανή), βάρη με όλες τις άλλες χρονιές (LOSO 2021-26) και walk-forward δίπλα (2022-26).
Ορισμένο από πριν. ΠΕΡΝΑ η αγορά αν στη μίξη LOSO: log-loss από την αγορά t ≤ −2 ΚΑΙ ROI ≥5 πόντων θετικό στη ΧΕΙΡΟΤΕΡΗ τιμή ΚΑΙ ≥4/6 χρονιές θετικές.
Μηχανισμός: bootstrap βραδιάς ≥90% ΚΑΙ placebo ≥95% ΚΑΙ επιλογή μόνο με παρελθόν ≥3/5 χρονιές. Reality Check: η καλύτερη φόρμουλα έναντι της αγοράς.
Θέλει UFC_DATA και T17_CACHE.
"""
import os

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import html
import pickle
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd

import t3_mechanisms as t3
from t2_age_repl import DATA
from t5_age_deep import LBS
from t6_rounds_style import BOOKS, MK, dec_, finish_features
from t10_own_engine import ridge
from t11_level_select import cv_fit

pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 300); pd.set_option("display.max_colwidth", 70)
lg, sig = t3.lg, t3.sig
LLf = lambda q, z: -(z * np.log(np.clip(q, 1e-6, 1 - 1e-6)) + (1 - z) * np.log(1 - np.clip(q, 1e-6, 1 - 1e-6)))
tstat = lambda d: d.mean() / (d.std() / np.sqrt(len(d)))
GROUPS = {"τελειώματα": ["S_fin_w_r", "S_fin_l_r", "S_dec_r", "S_finish_cross"], "νοκ ντάουν": ["S_kd15", "S_kd_ab15"], "υποταγές": ["S_sub15"],
          "χτυπήματα": ["S_slpm", "S_sapm"], "πάλη": ["S_td15"], "κατηγορία": ["S_lbs", "S_women"], "ηλικία": ["S_age_max"], "διαφορά δυνάμεων": ["S_gap"]}
NAMES = list(GROUPS)
ALL = [c for g in GROUPS.values() for c in g]
FULL = (1 << len(NAMES)) - 1
N_PL, N_BOOT, WORKERS = 40, 1000, 4
CACHE = os.environ.get("T17_CACHE", "t17_cache.pkl")
cols_of = lambda m: [c for i, n in enumerate(NAMES) if m >> i & 1 for c in GROUPS[n]]
label = lambda m: " + ".join(n for i, n in enumerate(NAMES) if m >> i & 1)
size = lambda m: bin(m).count("1")
YEARS = list(range(2021, 2027))
_G = {}


def data():
    o = pd.read_csv(DATA / "ufc_fights_odds.csv")
    x = pd.read_csv(DATA / "ufc_features_causal.csv").drop(columns=["date", "event", "f1", "f2"])
    o = o.merge(x, on="fight_url").merge(finish_features(), on="fight_url")
    o = o[o.f1_result.isin(["W", "L", "D"]) & (o.date >= "2008") & (o.sched_rounds == 3)].copy()
    o["y"] = o.date.str[:4].astype(int)
    fi = pd.read_csv(DATA / "ufc_fighters.csv")
    dob = pd.to_datetime(fi[~fi.dup_name].set_index("fighter").dob)
    d = pd.to_datetime(o.date)
    a1, a2 = (d - o.f1.map(dob)).dt.days / 365.25, (d - o.f2.map(dob)).dt.days / 365.25
    lbs = o.weightclass.map(lambda s: next((v for k, v in sorted(LBS.items(), key=lambda kv: -len(kv[0])) if k in str(s)), np.nan))
    o["out_O25"] = ((o.fight_time_s > 750) | (o.method_grp == "DEC")).astype(float)
    o["out_O15"] = ((o.fight_time_s > 450) | (o.method_grp == "DEC")).astype(float)
    for c in ("fin_w_r", "fin_l_r", "dec_r", "kd15", "kd_ab15", "sub15", "slpm", "sapm", "td15"):
        o["S_" + c] = o[f"f1_{c}"] + o[f"f2_{c}"]
    o["S_finish_cross"] = o.f1_fin_w_r * o.f2_fin_l_r + o.f2_fin_w_r * o.f1_fin_l_r
    o["S_lbs"], o["S_women"] = np.log(lbs), o.women.astype(float)
    o["S_age_max"] = np.fmax(a1, a2)
    o["S_gap"] = np.abs(lg(o.f1_p_close.clip(.01, .99)))
    return o.reset_index(drop=True)


def props():
    b = pd.read_csv(DATA / "bfo_book_odds.csv", low_memory=False)
    b = b[b.book.isin(BOOKS) & b.prop_type.notna()].copy()
    b["label"] = b.label.map(html.unescape)
    out = {}
    for name in ("O25", "O15"):
        pt, yes, no = MK[name]
        x = b[b.prop_type == pt]
        j = pd.concat([x[x.label == yes].groupby(["matchup_id", "book"]).odds.last().rename("y"), x[x.label == no].groupby(["matchup_id", "book"]).odds.last().rename("n")], axis=1).dropna()
        j["dy"], j["dn"] = dec_(j.y), dec_(j.n)
        j["p"] = (1 / j.dy) / (1 / j.dy + 1 / j.dn)
        out[name] = j.groupby("matchup_id").agg(p=("p", "median"), dy=("dy", "median"), dn=("dn", "median"), dy_w=("dy", "min"), dn_w=("dn", "min"), dy_b=("dy", "max"), dn_b=("dn", "max")).reset_index()
    return out


def engine(D, cols, z, y):
    """Κάθε χρονιά 2021+ με όλες τις προηγούμενες· ποινή από επικύρωση μέσα στα δεδομένα εκπαίδευσης."""
    q = np.full(len(y), np.nan)
    for Y in YEARS:
        tr = y < Y
        V = D[cols]
        X = ((V - V[tr].mean()) / V[tr].std().replace(0, 1)).fillna(0.0).values
        X = np.c_[np.ones(len(X)), X]
        q[y == Y] = sig(X[y == Y] @ ridge(X[tr], z[tr], cv_fit(X[tr], z[tr], y[tr])))
    return q


def mix(pm, qe, z, yy, loso=True):
    """pm, qe, z, yy μόνο στους αγώνες με τιμή 2021+."""
    Zx = np.c_[np.ones(len(pm)), lg(pm), lg(np.clip(qe, 1e-4, 1 - 1e-4))]
    q = np.full(len(pm), np.nan)
    for Y in YEARS:
        tr = yy != Y if loso else yy < Y
        if tr.sum() < 100:
            continue
        q[yy == Y] = sig(Zx[yy == Y] @ t3.fit(Zx[tr], z[tr])[0])
    return q


def init(path):
    _G.update(pickle.load(open(path + ".input", "rb")))


def job(key):
    mk, kind = key[0], key[1]
    G = _G[mk]
    D, z, y, idx, pm, yy = G["D"], G["z"], G["y"], G["idx"], G["pm"], G["yy"]
    if kind == "c":
        qe = engine(D, cols_of(key[2]), z, y)
    else:
        g = GROUPS[key[2]]
        rng = np.random.default_rng(100 * NAMES.index(key[2]) + key[3] + (0 if mk == "O25" else 5000))
        D2 = D.copy()
        for Y in np.unique(y):
            i = np.where(y == Y)[0]
            D2.iloc[i, [D2.columns.get_loc(c) for c in g]] = D.iloc[rng.permutation(i)][g].values
        qe = engine(D2, ALL, z, y)
    return key, qe[idx].astype(np.float32)


def bets(q, p, dy, dn, z, thr=.05):
    a, b = q - p >= thr, p - q >= thr
    x = np.zeros(len(q))
    x[a] = np.where(z[a] == 1, dy[a] - 1, -1.0)
    x[b] = np.where(z[b] == 0, dn[b] - 1, -1.0)
    return x


def roi(x, yy):
    v = x[x != 0]
    if not len(v):
        return dict(n=0)
    by = pd.Series(x).groupby(yy).sum()
    return dict(n=len(v), ROI=round(100 * v.mean(), 1), SE=round(100 * v.std() / np.sqrt(len(v)), 1), μον=round(v.sum(), 1), χρ=f"{(by > 0).sum()}/{len(by)}")


def main():
    o = data()
    P = props()
    inp = {}
    for mk in P:
        j = o[["matchup_id", "y"]].reset_index().merge(P[mk], on="matchup_id")
        j = j[j.y >= 2021].drop_duplicates("index")
        idx = j["index"].values
        inp[mk] = dict(D=o[ALL], z=o[f"out_{mk}"].values, y=o.y.values, idx=idx, pm=j.p.clip(.02, .98).values, yy=j.y.values)
    pickle.dump(inp, open(CACHE + ".input", "wb"))
    R = pickle.load(open(CACHE, "rb")) if os.path.exists(CACHE) else {}
    todo = [(mk, "c", m) for mk in P for m in range(1, FULL + 1)] + [(mk, "p", n, i) for mk in P for n in NAMES for i in range(N_PL)]
    todo = [k for k in todo if k not in R]
    print(f"αγώνες 3 γύρων 2008+ {len(o)} · υπόλοιπες μηχανές {len(todo)}", flush=True)
    if todo:
        with ProcessPoolExecutor(WORKERS, initializer=init, initargs=(CACHE,)) as ex:
            fs = [ex.submit(job, k) for k in todo]
            for n, f in enumerate(as_completed(fs), 1):
                k, q = f.result()
                R[k] = q
                if n % 100 == 0 or n == len(todo):
                    pickle.dump(R, open(CACHE, "wb"))
                    print(f"  {n}/{len(todo)}", flush=True)

    print("\nΕΛΕΓΧΟΣ αποτελέσματος (2:30 του 3ου = 750″):")
    for _, r in o[(o.y == 2025)].sample(4, random_state=3).iterrows():
        print(f"  {r.date} {r.f1} - {r.f2}: {r.method_grp} γύρος {r.end_round} {r.end_time_s}″ · χρόνος {r.fight_time_s} · Over 2.5 {r.out_O25:.0f} · Over 1.5 {r.out_O15:.0f}")

    K = list(range(1, FULL + 1))
    for mk in P:
        G = inp[mk]
        j = o[["matchup_id", "date", "y"]].iloc[G["idx"]].reset_index(drop=True).merge(P[mk], on="matchup_id", how="left")
        z, yy, pm = G["z"][G["idx"]], G["yy"], G["pm"]
        Qe = {m: np.asarray(R[(mk, "c", m)], float) for m in K}
        print(f"\n\n================ {mk}: {len(z)} αγώνες 2021-26 · Over έγινε {z.mean():.3f} · αγορά {pm.mean():.3f} · περιθώριο διάμεσο {np.median(1 / j.dy + 1 / j.dn - 1):.3f} ================")
        L0 = LLf(pm, z)
        Zb = np.c_[np.ones(len(z)), lg(pm)]
        qb = np.full(len(z), np.nan)
        for Y in YEARS:
            qb[yy == Y] = sig(Zb[yy == Y] @ t3.fit(Zb[yy != Y], z[yy != Y])[0])
        print(f"αγορά: log-loss {L0.mean():.4f} · αγορά διορθωμένη (LOSO) {LLf(qb, z).mean():.4f} t {tstat(LLf(qb, z) - L0):+.2f} · ROI τυφλό Over διάμεση {roi(np.where(z == 1, j.dy.values - 1, -1.0), yy)}")
        Ql = {m: mix(pm, Qe[m], z, yy) for m in K}
        Qw = {m: mix(pm, Qe[m], z, yy, False) for m in K}
        LL = np.array([LLf(Ql[m], z) for m in K])
        s0 = LL.mean(1)
        rows = []
        for m in K:
            xw = bets(Ql[m], pm, j.dy_w.values, j.dn_w.values, z)
            rows.append(dict(φόρμουλα=label(m), μηχ=size(m), LL=s0[m - 1], διαφ=(LL[m - 1] - L0).mean(), t=tstat(LL[m - 1] - L0), **roi(xw, yy)))
        T = pd.DataFrame(rows).sort_values("LL")
        T.to_csv(DATA / f"t17_combos_{mk}.csv", index=False)
        print("\n--- μίξη LOSO, ROI ≥5 πόντων στη ΧΕΙΡΟΤΕΡΗ τιμή, 15 πρώτες με log-loss ---")
        print(T.head(15).round(4).to_string(index=False))
        print(f"πληρούν το κριτήριο αγοράς (t ≤ −2, ROI>0, ≥4/6): {((T.t <= -2) & (T.ROI > 0) & (T.χρ.fillna("0").str[0].astype(int) >= 4)).sum()} από {len(T)}")

        for nm, m in (("ΠΛΗΡΗΣ", FULL), ("ΠΡΩΤΗ", K[int(s0.argmin())])):
            print(f"\n--- {nm}: {label(m)} ---")
            print(f"  μηχανή μόνη log-loss {LLf(Qe[m], z).mean():.4f} (αγορά {L0.mean():.4f}) · βάρη LOSO όλα: {np.round(t3.fit(np.c_[np.ones(len(z)), lg(pm), lg(np.clip(Qe[m], 1e-4, 1 - 1e-4))], z)[0], 3)}")
            for thr in (.03, .05, .08):
                print(f"  κατώφλι {int(thr * 100)}: χειρότερη {roi(bets(Ql[m], pm, j.dy_w.values, j.dn_w.values, z, thr), yy)} · διάμεση {roi(bets(Ql[m], pm, j.dy.values, j.dn.values, z, thr), yy)} · καλύτερη {roi(bets(Ql[m], pm, j.dy_b.values, j.dn_b.values, z, thr), yy)}")
            w5 = yy >= 2022
            xw = bets(Qw[m][w5], pm[w5], j.dy_w.values[w5], j.dn_w.values[w5], z[w5])
            print(f"  walk-forward 2022-26: LL {LLf(Qw[m][w5], z[w5]).mean():.4f} vs αγορά {L0[w5].mean():.4f} t {tstat(LLf(Qw[m][w5], z[w5]) - L0[w5]):+.2f} · ROI χειρότερη {roi(xw, yy[w5])}")

        # bootstrap ανά βραδιά + Reality Check έναντι αγοράς
        ev, _ = pd.factorize(j.date)
        E = ev.max() + 1
        nE = np.bincount(ev, minlength=E).astype(float)
        aL = np.array([np.bincount(ev, a, minlength=E) for a in LL])
        a0 = np.bincount(ev, L0, minlength=E)
        Wt = np.random.default_rng(17).multinomial(E, np.ones(E) / E, N_BOOT).astype(float)
        den = Wt @ nE
        bL = (Wt @ aL.T) / den[:, None]
        b0 = (Wt @ a0) / den
        d = L0.mean() - s0
        V, Vb = d.max(), ((b0[:, None] - bL) - d).max(1)
        print(f"\nReality Check: καλύτερη φόρμουλα έναντι αγοράς {V:+.5f} log-loss · p {(Vb >= V).mean():.3f} (χρειάζεται <0.05)")
        print(f"η πρώτη βγήκε πρώτη στο {(bL.argmin(1) == s0.argmin()).mean():.1%} των επαναλήψεων · η πλήρης νικά την αγορά στο {(bL[:, FULL - 1] < b0).mean():.1%}")

        # επιλογή μόνο με παρελθόν
        sel = {}
        for Y in YEARS[1:]:
            h = yy < Y
            if Y == YEARS[1]:  # μόνο μία χρονιά ιστορικού: χωρίς LOSO
                sc = [LLf(sig(Zm @ t3.fit(Zm, z[h])[0]), z[h]).mean() for Zm in (np.c_[np.ones(h.sum()), lg(pm[h]), lg(np.clip(Qe[m][h], 1e-4, 1 - 1e-4))] for m in K)]
            else:
                sc = [LLf(mix(pm[h], Qe[m][h], z[h], yy[h]), z[h]).mean() for m in K]
            sel[Y] = K[int(np.nanargmin(sc))]
            print(f"  επιλογή {Y}: {label(sel[Y])}")
        qs = np.full(len(z), np.nan)
        for Y, m in sel.items():
            qs[yy == Y] = Qw[m][yy == Y]
        w5 = yy >= 2022
        print(f"  επιλογή με παρελθόν 2022-26: LL {LLf(qs[w5], z[w5]).mean():.4f} vs αγορά {L0[w5].mean():.4f} t {tstat(LLf(qs[w5], z[w5]) - L0[w5]):+.2f} · ROI χειρότερη {roi(bets(qs[w5], pm[w5], j.dy_w.values[w5], j.dn_w.values[w5], z[w5]), yy[w5])}")

        # μηχανισμοί
        print("\n--- μηχανισμοί: μέση συνεισφορά, bootstrap, placebo, επιλογή ---")
        rows = []
        for g, n in enumerate(NAMES):
            pr = [(idx_ - 1, (idx_ ^ (1 << g)) - 1) for idx_ in K if idx_ >> g & 1 and idx_ ^ (1 << g)]
            A, B = [a for a, _ in pr], [b for _, b in pr]
            ms, bs = (s0[A] - s0[B]).mean(), (bL[:, A] - bL[:, B]).mean(1)
            wo = FULL ^ (1 << g)
            real = s0[wo - 1] - s0[FULL - 1]
            pl = np.array([s0[wo - 1] - LLf(mix(pm, np.asarray(R[(mk, "p", n, i)], float), z, yy), z).mean() for i in range(N_PL)])
            yrs = sum(sel[Y] >> g & 1 for Y in sel)
            rows.append(dict(μηχανισμός=n, δ_LL=round(ms, 5), Π_βελτ=(bs < 0).mean(), αληθινό=round(real, 5), placebo95=round(np.quantile(pl, .95), 5), πάνω_από_placebo=(pl < real).mean(), χρονιές=yrs,
                             ΠΕΡΝΑ=bool((bs < 0).mean() >= .9 and (pl < real).mean() >= .95 and yrs >= 3)))
        print(pd.DataFrame(rows).round(4).to_string(index=False))


if __name__ == "__main__":
    main()
