"""UFC τεστ 10: ΔΙΚΗ ΜΗΧΑΝΗ χωρίς την τιμή της αγοράς — πόσο κοντά φτάνει;

Μοντέλο: logit(νίκη f1) = Σ b·(διαφορά f1−f2), ΧΩΡΙΣ σταθερό όρο (η πλευρά f1 δεν επηρεάζει τίποτα), ridge.
Σκάλα (ορισμένη από πριν), κάθε σκαλί προσθέτει στο προηγούμενο:
  Μ1 Glicko (walk-forward, t1_rating_preds) · Μ2 +ηλικία · Μ3 +στατιστικά (sdiff_adj, slpm, sapm, td15, tdd, ctrl_share, kd_abs15)
  Μ4 +σώμα/καριέρα UFC (άνοιγμα χεριών, ύψος, ln αγώνων, ln απουσίας, ήττες KO, σερί)
  Μ5 +έδρα (εκτός ΗΠΑ / στις ΗΠΑ) · Μ6 +Sherdog (ln αγώνων, % νικών, % τελειωμάτων) · Μ7 = Μ6 χωρίς Glicko
Κρίση: fit 2008-16 -> 2017-26, και walk-forward (κάθε χρονιά με όλες τις προηγούμενες).
Μέτρηση στους ΙΔΙΟΥΣ αγώνες: log-loss, ακρίβεια vs άνοιγμα/κλείσιμο · βάρος σε μίξη με την αγορά · ROI (τιμή με περιθώριο).
Μέτρο σύγκρισης: σημερινή φόρμουλα αγορά + ηλικία + sapm + td15.
"""
import numpy as np
import pandas as pd

import t3_mechanisms as t3
from t2_age_repl import DATA
from t8_sherdog import career_features, nat_norm

pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 200)
lg, sig, ll = t3.lg, t3.sig, t3.ll
STATS = ["sdiff_adj", "slpm", "sapm", "td15", "tdd", "ctrl_share", "kd_abs15"]
BODY = ["reach", "height", "lnexp", "lnlay", "ko_losses", "streak"]
HOME = ["home_nus", "home_us"]
SHER = ["lnpro", "winpct", "finpct"]
GRID = [0, 1, 3, 10, 30, 100, 300, 1000]


def ridge(X, w, lam):
    """Newton με ποινή, χωρίς σταθερό όρο."""
    b = np.zeros(X.shape[1]); P = lam * np.eye(len(b))
    for _ in range(40):
        q = sig(X @ b); H = (X * (q * (1 - q))[:, None]).T @ X + P + 1e-9 * np.eye(len(b))
        st = np.linalg.solve(H, X.T @ (w - q) - P @ b)
        b = b + st
        if np.abs(st).max() < 1e-7:
            break
    return b


def cv_lam(X, w, y):
    """λ από δίπλωση ανά χρονιά, μόνο μέσα στα δεδομένα εκπαίδευσης."""
    best = (9, 0)
    for lam in GRID:
        L = []
        for yy in np.unique(y):
            b = ridge(X[y != yy], w[y != yy], lam)
            p = np.clip(sig(X[y == yy] @ b), 1e-6, 1 - 1e-6)
            L.append(-(w[y == yy] * np.log(p) + (1 - w[y == yy]) * np.log(1 - p)))
        s = np.concatenate(L).mean()
        best = min(best, (s, lam))
    return best[1]


def build():
    o = t3.load()
    fi = pd.read_csv(DATA / "ufc_fighters.csv")
    dob = pd.to_datetime(fi[~fi.dup_name].set_index("fighter").dob)
    d = pd.to_datetime(o.date)
    o["a1"], o["a2"] = (d - o.f1.map(dob)).dt.days / 365.25, (d - o.f2.map(dob)).dt.days / 365.25
    g = pd.read_csv(DATA / "t1_rating_preds.csv")[["date", "event", "f1", "f2", "p_model"]].drop_duplicates(["date", "event", "f1", "f2"])
    o = o.merge(g, on=["date", "event", "f1", "f2"], how="left")
    C = career_features(o)
    for s in ("f1", "f2"):
        for c in ("pro_n", "pro_w", "pro_l", "fin_w"):
            o[f"{s}_{c}"] = [C.get((u, f), {}).get(c, np.nan) for u, f in zip(o.fight_url, o[s])]
        o[f"{s}_lnpro"] = np.log1p(o[f"{s}_pro_n"])
        o[f"{s}_winpct"] = (o[f"{s}_pro_w"] + 1) / (o[f"{s}_pro_n"] + 2)  # συρρίκνωση για λίγους αγώνες
        o[f"{s}_finpct"] = (o[f"{s}_fin_w"] + .5) / (o[f"{s}_pro_w"] + 1)
    A = pd.read_csv(DATA / "sherdog_fighters.csv").drop_duplicates("fighter").set_index("fighter")
    nat = A.nationality.map(nat_norm)
    cty = o.location.fillna("").str.split(",").str[-1].str.strip().replace({"United Kingdom": "UK"})
    n1, n2 = o.f1.map(nat), o.f2.map(nat)
    known = (n1.notna() & n2.notna()).values
    us = (cty == "USA").values
    h = ((n1 == cty).values.astype(float) - (n2 == cty).values.astype(float)) * known
    D = pd.DataFrame(index=o.index)
    D["glicko"] = lg(np.clip(o.p_model, 1e-4, 1 - 1e-4))
    D["age"] = o.a1 - o.a2
    for c in STATS + BODY + SHER:
        D[c] = (o[f"f1_{c}"] - o[f"f2_{c}"])
    D["home_nus"], D["home_us"] = h * ~us, h * us
    w = (o.f1_result == "W").astype(float).values
    keep = (D[["glicko", "age", "sapm", "td15"]].notna().all(axis=1)).values
    return o[keep].reset_index(drop=True), D[keep].reset_index(drop=True), w[keep]


def roi(q, o, k, m, w, thr):
    """Πόνταρε όποια πλευρά έχει q − p_αγοράς ≥ thr, στην τιμή με περιθώριο."""
    p, d1, d2 = o[f"f1_p_{k}"].values, o[f"f1_{k}_dec"].values, o[f"f2_{k}_dec"].values
    a = m & (q - p >= thr); b = m & ((1 - q) - (1 - p) >= thr)
    prof = np.r_[np.where(w[a] == 1, d1[a] - 1, -1.0), np.where(w[b] == 0, d2[b] - 1, -1.0)]
    yr = np.r_[o.y.values[a], o.y.values[b]]
    fav = np.r_[p[a] >= .5, (1 - p[b]) >= .5]
    if not len(prof):
        return dict(n=0)
    by = pd.Series(prof).groupby(yr).mean()
    return dict(n=len(prof), ROI=100 * prof.mean(), SE=100 * prof.std() / np.sqrt(len(prof)), χρ=f"{(by > 0).sum()}/{len(by)}",
                φαβ_n=int(fav.sum()), φαβ=100 * prof[fav].mean() if fav.any() else np.nan,
                αουτσ=100 * prof[~fav].mean() if (~fav).any() else np.nan)


def main():
    o, D, w = build()
    y = o.y.values
    tr, te = y <= 2016, y >= 2017
    print(f"αγώνες {len(o)} · 2008-16 {tr.sum()} · 2017-26 {te.sum()}")
    print("κάλυψη: ", {c: round(float(D[c].notna().mean()), 3) for c in ("reach", "height", "lnpro")})
    # τυποποίηση ΜΟΝΟ με τυπική απόκλιση εκπαίδευσης· λείπει -> διαφορά 0
    sd = D[tr].std().replace(0, 1)
    Z = (D / sd).fillna(0.0)
    LAD = [("Μ1 Glicko", ["glicko"]), ("Μ2 +ηλικία", ["glicko", "age"]), ("Μ3 +στατιστικά", ["glicko", "age"] + STATS),
           ("Μ4 +σώμα/καριέρα", ["glicko", "age"] + STATS + BODY), ("Μ5 +έδρα", ["glicko", "age"] + STATS + BODY + HOME),
           ("Μ6 +Sherdog", ["glicko", "age"] + STATS + BODY + HOME + SHER), ("Μ7 χωρίς Glicko", ["age"] + STATS + BODY + HOME + SHER)]

    po, pc = o.f1_p_open.values, o.f1_p_close.values
    print(f"\nΑΓΟΡΑ 2017-26: άνοιγμα log-loss {ll(po[te], w[te]):.4f} ακρίβεια {((po[te] > .5) == w[te]).mean():.3f} · "
          f"κλείσιμο {ll(pc[te], w[te]):.4f} ακρίβεια {((pc[te] > .5) == w[te]).mean():.3f}")
    print("(ακρίβεια: προσοχή, ο f1 είναι συνήθως ο νικητής -> δεν επηρεάζει το μοντέλο χωρίς σταθερό όρο, μετράει συμμετρικά)")

    # Φόρμουλα σύγκρισης
    Xf = lambda k: np.c_[lg(o[f"f1_p_{k}"]), D[["age", "sapm", "td15"]].values]
    q_form = {k: sig(Xf(k) @ ridge(Xf(k)[tr], w[tr], 0)) for k in ("open", "close")}

    rows, preds, betas = [], {}, {}
    for name, cols in LAD:
        X = Z[cols].values
        lam = cv_lam(X[tr], w[tr], y[tr])
        b = ridge(X[tr], w[tr], lam)
        q = sig(X @ b)
        # walk-forward
        qw = np.full(len(o), np.nan)
        for yy in range(2017, 2027):
            qw[y == yy] = sig(X[y == yy] @ ridge(X[y < yy], w[y < yy], lam))
        preds[name], betas[name] = (q, qw), dict(zip(cols, b))
        r = dict(μηχανή=name, λ=lam, LL=ll(q[te], w[te]), ακρίβεια=((q[te] > .5) == w[te]).mean(), LL_wf=ll(qw[te], w[te]),
                 ακρίβ_wf=((qw[te] > .5) == w[te]).mean())
        r["−άνοιγμα"] = r["LL_wf"] - ll(po[te], w[te])
        r["−κλείσιμο"] = r["LL_wf"] - ll(pc[te], w[te])
        for k, p in (("άν", po), ("κλ", pc)):
            pq = np.clip(qw[te], 1e-6, 1 - 1e-6); pm = np.clip(p[te], 1e-6, 1 - 1e-6); ww = w[te]
            dl = -(ww * np.log(pq) + (1 - ww) * np.log(1 - pq)) + (ww * np.log(pm) + (1 - ww) * np.log(1 - pm))
            r[f"χρ<{k}"] = f"{(pd.Series(dl).groupby(y[te]).mean() < 0).sum()}/10"
        rows.append(r)
    print("\n=== Α. Σκάλα χωρίς αγορά: log-loss 2017-26 (LL = fit 08-16, wf = κάθε χρονιά με τις προηγούμενες) ===")
    print(pd.DataFrame(rows).round(4).to_string(index=False))

    print("\n=== Β. Βάρη καλύτερης μηχανής Μ6 (fit 08-16, ανά 1 τυπική απόκλιση) ===")
    print(pd.Series(betas["Μ6 +Sherdog"]).round(3).to_string())
    print("βάρη Μ7:"); print(pd.Series(betas["Μ7 χωρίς Glicko"]).round(3).to_string())

    print("\n=== Γ. Μίξη με την αγορά: logit = a·αγορά + b·μηχανή (walk-forward προβλέψεις) ===")
    print("βάρη/t: όλο το 2017-26 · LL/διαφ: βάρη από 2017-21, κρίση 2022-26 (η μηχανή δεν έχει δει τους αγώνες)")
    a, c = (y >= 2017) & (y <= 2021), y >= 2022
    mix_rows = []
    for name, (q, qw) in preds.items():
        lq = lg(np.clip(qw, 1e-4, 1 - 1e-4))
        for k, p in (("άνοιγμα", po), ("κλείσιμο", pc)):
            X = np.c_[lg(p), lq]; X0 = lg(p)[:, None]
            b, se = t3.fit(X[a], w[a]); b0, _ = t3.fit(X0[a], w[a])
            bAll, seAll = t3.fit(X[te], w[te])
            q1, q0 = sig(X[c] @ b), sig(X0[c] @ b0); ww = w[c]
            dl = -(ww * np.log(q1) + (1 - ww) * np.log(1 - q1)) + (ww * np.log(q0) + (1 - ww) * np.log(1 - q0))
            mix_rows.append(dict(μηχανή=name, αγορά=k, βάρος_αγοράς=bAll[0], βάρος_μηχανής=bAll[1], t=bAll[1] / seAll[1],
                                 LL_αγορά=ll(q0, ww), LL_μίξη=ll(q1, ww), διαφ=dl.mean(), t_διαφ=dl.mean() / (dl.std() / np.sqrt(len(dl)))))
    print(pd.DataFrame(mix_rows).round(4).to_string(index=False))

    print("\n=== Δ. ROI 2017-26: πόνταρε όταν μηχανή (wf) − αγορά ≥ όριο, τιμή με περιθώριο ===")
    R = []
    for name, (q, qw) in preds.items():
        if name not in ("Μ1 Glicko", "Μ3 +στατιστικά", "Μ6 +Sherdog", "Μ7 χωρίς Glicko"):
            continue
        for k, kk in (("open", "άνοιγμα"), ("close", "κλείσιμο")):
            for thr in (.03, .05, .08, .12):
                R.append(dict(μηχανή=name, τιμή=kk, όριο=thr, **roi(qw, o, k, te, w, thr)))
    for k, kk in (("open", "άνοιγμα"), ("close", "κλείσιμο")):
        for thr in (.03, .05, .08, .12):
            R.append(dict(μηχανή="φόρμουλα αγορά+η+s+t", τιμή=kk, όριο=thr, **roi(q_form[k], o, k, te, w, thr)))
    print(pd.DataFrame(R).round(2).to_string(index=False))

    print("\n=== ΣΤ. 2022-26, ίδιοι αγώνες: φόρμουλες με αγορά (βάρη ΜΟΝΟ από πριν το 2022), ROI στην τιμή με περιθώριο ===")
    S = []
    FX = {"ηλικία+sapm+td15": ["age", "sapm", "td15"], "ηλικία+td15+έδρα": ["age", "td15", "home_nus"]}
    for k, kk, p in (("open", "άνοιγμα", po), ("close", "κλείσιμο", pc)):
        ww = w[c]
        cand = {}
        for nm, cols in FX.items():
            X = np.c_[lg(p), D[cols].values]
            cand["αγορά+" + nm] = sig(X @ ridge(X[y <= 2021], w[y <= 2021], 0))
        for nm in ("Μ3 +στατιστικά", "Μ7 χωρίς Glicko"):
            X = np.c_[lg(p), lg(np.clip(preds[nm][1], 1e-4, 1 - 1e-4))]
            q = np.full(len(o), np.nan)
            q[c] = sig(X[c] @ t3.fit(X[a], w[a])[0])
            cand["αγορά+" + nm] = q
        X0 = lg(p)[:, None]
        q0 = sig(X0[c] @ t3.fit(X0[y <= 2021], w[y <= 2021])[0])
        l0 = -(ww * np.log(q0) + (1 - ww) * np.log(1 - q0))
        for nm, q in cand.items():
            l1 = -(ww * np.log(q[c]) + (1 - ww) * np.log(1 - q[c]))
            r = dict(τιμή=kk, φόρμουλα=nm, LL=l1.mean(), διαφ_αγορά=(l1 - l0).mean(), t=(l1 - l0).mean() / ((l1 - l0).std() / np.sqrt(len(l1))))
            for thr in (.03, .05, .08):
                x = roi(q, o, k, c, w, thr)
                r[f"n≥{int(thr*100)}"], r[f"ROI≥{int(thr*100)}"], r[f"χρ≥{int(thr*100)}"] = x.get("n"), x.get("ROI"), x.get("χρ")
            S.append(r)
    print(pd.DataFrame(S).round(4).to_string(index=False))

    print("\n=== Ε. ΕΛΕΓΧΟΣ: γνωστοί αγώνες (Μ6 walk-forward, από την πλευρά f1) ===")
    _, qw = preds["Μ6 +Sherdog"]
    show = [("Ilia Topuria", "Alexander Volkanovski"), ("Sean Strickland", "Israel Adesanya"), ("Leon Edwards", "Kamaru Usman"),
            ("Islam Makhachev", "Alexander Volkanovski"), ("Merab Dvalishvili", "Sean O'Malley"), ("Alex Pereira", "Jiri Prochazka"),
            ("Tom Aspinall", "Curtis Blaydes"), ("Max Holloway", "Justin Gaethje")]
    for a1, b1 in show:
        x = o[((o.f1 == a1) & (o.f2 == b1)) | ((o.f1 == b1) & (o.f2 == a1))]
        x = x[x.y >= 2017]
        for i in x.index:
            print(f"  {o.date[i]} {o.f1[i]} vs {o.f2[i]}: μηχανή {qw[i]:.3f} · άνοιγμα {po[i]:.3f} · κλείσιμο {pc[i]:.3f} · f1 {o.f1_result[i]} · "
                  f"Δηλικίας {D.age[i]:+.1f}")
    print("\nμεγαλύτερες διαφωνίες με το κλείσιμο 2022-26:")
    gap = np.where(y >= 2022, qw - pc, 0)
    for i in np.argsort(-np.abs(gap))[:12]:
        print(f"  {o.date[i]} {o.f1[i]} vs {o.f2[i]}: μηχανή {qw[i]:.3f} · κλείσιμο {pc[i]:.3f} · f1 {o.f1_result[i]} · n_prev {o.f1_n_prev[i]:.0f}/{o.f2_n_prev[i]:.0f}")
    print("\nβαθμονόμηση Μ6 wf 2017-26 (φαβορί της μηχανής):")
    pf = np.maximum(qw[te], 1 - qw[te]); wf = np.where(qw[te] >= .5, w[te], 1 - w[te])
    print(pd.DataFrame({"p": pf, "w": wf, "b": pd.cut(pf, [.5, .6, .7, .8, 1])}).groupby("b", observed=True)
          .agg(n=("w", "size"), πρόβλεψη=("p", "mean"), κέρδισε=("w", "mean")).round(3).to_string())
    print("\nΕΛΕΓΧΟΣ διαρροής: Μ6 με ανακατεμένο αποτέλεσμα στο fit -> πρέπει log-loss ~0.693+")
    rng = np.random.default_rng(1)
    X = Z[LAD[5][1]].values
    print(round(ll(sig(X[te] @ ridge(X[tr], rng.permutation(w[tr]), 100)), w[te]), 4))


if __name__ == "__main__":
    main()
