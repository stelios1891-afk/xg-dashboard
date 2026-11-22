"""UFC τεστ 11: επίπεδο αντιπάλων/διοργανώσεων εκτός UFC + επιλογή στοιχείων ΜΟΝΟ με παρελθόν.

Ορισμένα από πριν:
 Επίπεδο (Sherdog, αγώνες ΕΚΤΟΣ UFC πριν την ημέρα του αγώνα):
   big_w / big_l    ln νικών/ηττών σε μεγάλη διοργάνωση (λίστα BIG του τεστ 8, αμετάβλητη)
   opp_w / opp_l    ln νικών/ηττών κόντρα σε αντίπαλο που είχε ΗΔΗ αγωνιστεί στο UFC εκείνη τη μέρα του ΤΩΡΙΝΟΥ αγώνα
                    (όχι «έφτασε αργότερα στο UFC»: θα ήταν γνώση του μέλλοντος)
   dwcs             ο τελευταίος αγώνας ήταν στο Contender Series
   d_*              τα ίδια μόνο για πρωτοεμφανιζόμενο (0 για τους υπόλοιπους)
 Μέρος Β: Μ7 vs Μ7+επίπεδο (walk-forward 2017-26): log-loss, μίξη, ROI, ανά εμπειρία.
 Μέρος Γ: επιλογή μόνο με παρελθόν. Κάθε χρονιά Υ, μόνο με αγώνες < Υ:
   Σ1 αγορά + εμπρόσθια επιλογή από ΟΛΗ τη δεξαμενή (προσθήκη μόνο αν το CV log-loss πέφτει ≥0.0002, το πολύ 8)
   Σ2 μηχανή ridge με ΟΛΗ τη δεξαμενή (λ από CV) + μίξη με αγορά (βάρη από 2012..Υ−1)
   Σύγκριση: αγορά+ηλικία+sapm+td15 (φόρμουλα) και αγορά+Μ7 με το ίδιο walk-forward.
 --summary: μόνο τα βασικά (για σύγκριση με UFC_FEATURES=ufc_features_causal.csv).
"""
import sys

import numpy as np
import pandas as pd

import t3_mechanisms as t3
from t2_age_repl import DATA
from t8_sherdog import BIG
from t10_own_engine import BODY, HOME, SHER, STATS, build, ridge, roi
from ufc_build import key

pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 200)
lg, sig = t3.lg, t3.sig
LEVEL = ["big_w", "big_l", "opp_w", "opp_l", "dwcs"]
DLEVEL = ["d_" + c for c in LEVEL]
GRID = [10, 30, 100, 300, 1000]
Ls = lambda q, w: -(w * np.log(np.clip(q, 1e-6, 1 - 1e-6)) + (1 - w) * np.log(1 - np.clip(q, 1e-6, 1 - 1e-6)))


def level_features(o, D):
    F = pd.read_csv(DATA / "ufc_fights.csv")
    first_ufc = {}
    for s in ("f1", "f2"):
        for k, d in zip(F[s].map(key), pd.to_datetime(F.date)):
            if k not in first_ufc or d < first_ufc[k]:
                first_ufc[k] = d
    S = pd.read_csv(DATA / "sherdog_fights.csv")
    S["date"] = pd.to_datetime(S.date.str[:10], errors="coerce")
    S = S.dropna(subset=["date"]).sort_values(["fighter", "date"])
    ev = S.event.fillna("")
    S["ufc"] = ev.str.startswith("UFC") | ev.str.contains("Ultimate Fighting Championship")
    S["big"] = ev.str.contains(BIG, regex=True) & ~S.ufc
    S["dw"] = ev.str.contains("Contender Series")
    S["okey"] = S.opponent.fillna("").map(key)
    S["ofirst"] = S.okey.map(first_ufc)
    G = {k: v for k, v in S.groupby("fighter")}
    d = pd.to_datetime(o.date)
    out = {c: np.full(len(o), np.nan) for c in LEVEL + DLEVEL}
    for s, sg in (("f1", 1.0), ("f2", -1.0)):
        for i, (f, dd, np_) in enumerate(zip(o[s], d, o[f"{s}_n_prev"])):
            g = G.get(f)
            if g is None:
                continue
            p = g[g.date < dd - pd.Timedelta(days=1)]
            x = p[~p.ufc]
            win, los = (x.result == "win").values, (x.result == "loss").values
            known = (x.ofirst < dd).values  # ο αντίπαλος είχε ήδη αγώνα στο UFC ως τώρα
            v = dict(big_w=np.log1p((x.big.values & win).sum()), big_l=np.log1p((x.big.values & los).sum()),
                     opp_w=np.log1p((known & win).sum()), opp_l=np.log1p((known & los).sum()),
                     dwcs=float(len(p) > 0 and bool(p.dw.iloc[-1])))
            for c, val in v.items():
                out[c][i] = np.nan_to_num(out[c][i]) + sg * val
                out["d_" + c][i] = np.nan_to_num(out["d_" + c][i]) + sg * val * (np_ == 0)
    for c in out:
        D[c] = out[c]
    return D


def design(D, cols, y, Y):
    """Τυποποίηση μόνο με αγώνες < Υ· λείπει -> 0."""
    sd = D.loc[y < Y, cols].std().replace(0, 1)
    return (D[cols] / sd).fillna(0.0).values


def cv_fit(X, w, y, grid=GRID):
    blocks = (y - y.min()) // 3
    best = (9, grid[0])
    for lam in grid:
        L = []
        for b in np.unique(blocks):
            m = blocks == b
            L.append(Ls(sig(X[m] @ ridge(X[~m], w[~m], lam)), w[m]))
        best = min(best, (np.concatenate(L).mean(), lam))
    return best[1]


def engine_wf(D, cols, w, y, y0=2012):
    q = np.full(len(y), np.nan)
    for Y in range(y0, 2027):
        X = design(D, cols, y, Y)
        tr = y < Y
        q[y == Y] = sig(X[y == Y] @ ridge(X[tr], w[tr], cv_fit(X[tr], w[tr], y[tr])))
    return q


def mix_wf(p, qe, w, y, y0=2017):
    X = np.c_[lg(p), lg(np.clip(qe, 1e-4, 1 - 1e-4))]
    q = np.full(len(y), np.nan)
    for Y in range(y0, 2027):
        tr = (y >= 2012) & (y < Y)
        q[y == Y] = sig(X[y == Y] @ t3.fit(X[tr], w[tr])[0])
    return q


def formula_wf(p, F, w, y, y0=2017):
    X = np.c_[lg(p), F]
    q = np.full(len(y), np.nan)
    for Y in range(y0, 2027):
        q[y == Y] = sig(X[y == Y] @ ridge(X[y < Y], w[y < Y], 0))
    return q


def forward_wf(p, D, pool, w, y, y0=2017):
    lp = lg(p)
    q, chosen = np.full(len(y), np.nan), {}
    for Y in range(y0, 2027):
        Z = design(D, pool, y, Y)
        tr = y < Y
        Ztr, wt, yt, lpt = Z[tr], w[tr], y[tr], lp[tr]
        blocks = (yt - yt.min()) // 3

        def cv(idx):
            X = np.c_[lpt, Ztr[:, idx]] if idx else lpt[:, None]
            L = []
            for b in np.unique(blocks):
                m = blocks == b
                L.append(Ls(sig(X[m] @ ridge(X[~m], wt[~m], 1)), wt[m]))
            return np.concatenate(L).mean()
        sel, cur = [], cv([])
        while len(sel) < 8:
            sc = [(cv(sel + [j]), j) for j in range(len(pool)) if j not in sel]
            s, j = min(sc)
            if cur - s < .0002:
                break
            sel.append(j); cur = s
        X = np.c_[lp, Z[:, sel]] if sel else lp[:, None]
        q[y == Y] = sig(X[y == Y] @ ridge(X[tr], w[tr], 1))
        chosen[Y] = [pool[j] for j in sel]
        print(f"  {Y}: {chosen[Y]}", flush=True)
    return q, chosen


def report(name, q, o, w, y, k, p, per=((2017, 2026), (2022, 2026))):
    rows = []
    for a, b in per:
        m = (y >= a) & (y <= b)
        X0 = lg(p)[:, None]
        q0 = np.full(len(y), np.nan)
        for Y in range(a, b + 1):
            q0[y == Y] = sig(X0[y == Y] @ t3.fit(X0[y < Y], w[y < Y])[0])
        d = Ls(q[m], w[m]) - Ls(q0[m], w[m])
        by = pd.Series(d).groupby(y[m]).mean()
        r = dict(φόρμουλα=name, τιμή=k, περίοδος=f"{a}-{b}", n=int(m.sum()), LL=Ls(q[m], w[m]).mean(), διαφ=d.mean(),
                 t=d.mean() / (d.std() / np.sqrt(len(d))), χρ=f"{(by < 0).sum()}/{len(by)}")
        for thr in (.03, .05, .08):
            x = roi(q, o, k, m, w, thr)
            pc = int(thr * 100)
            r[f"n{pc}"], r[f"ROI{pc}"], r[f"SE{pc}"], r[f"χρ{pc}"] = x.get("n"), x.get("ROI"), x.get("SE"), x.get("χρ")
        rows.append(r)
    return rows


def main():
    o, D, w = build()
    y = o.y.values
    print(f"αγώνες {len(o)}")
    D = level_features(o, D)
    print("κάλυψη επιπέδου:", round(float(D.big_w.notna().mean()), 3))
    M7 = ["age"] + STATS + BODY + HOME + SHER
    F = D[["age", "sapm", "td15"]].values
    PR = {"open": o.f1_p_open.values, "close": o.f1_p_close.values}
    q7 = engine_wf(D, M7, w, y)
    R = []
    for k, p in PR.items():
        R += report("αγορά+ηλικία+sapm+td15", formula_wf(p, F, w, y), o, w, y, k, p)
        R += report("αγορά+Μ7", mix_wf(p, q7, w, y), o, w, y, k, p)
    if "--summary" in sys.argv:
        print(pd.DataFrame(R).round(4).to_string(index=False))
        return

    print("\n=== Α. ΕΛΕΓΧΟΣ γνωστών (τιμές επιπέδου: διαφορά f1−f2, από ln) ===")
    for a, b in (("Holly Holm", "Kayla Harrison"), ("Neil Magny", "Yaroslav Amosov"), ("Lerone Murphy", "Aaron Pico"),
                 ("Nathaniel Wood", "Losene Keita"), ("Preston Parsons", "Jacobe Smith")):
        for i in o[(o.f1 == a) & (o.f2 == b)].index:
            print(f"  {o.date[i]} {a} vs {b}: " + " ".join(f"{c}={D[c][i]:+.2f}" for c in LEVEL))

    qL = engine_wf(D, M7 + LEVEL + DLEVEL, w, y)
    mn = np.minimum(o.f1_n_prev, o.f2_n_prev).values; mx = np.maximum(o.f1_n_prev, o.f2_n_prev).values
    te = y >= 2017
    print("\n=== Β. Μ7 vs Μ7+επίπεδο, 2017-26 ===")
    rows = []
    for nm, m in (("όλοι", np.ones(len(y), bool)), ("και οι 2 πρωτοεμφ.", (mn == 0) & (mx == 0)), ("1 πρωτοεμφ.", (mn == 0) & (mx > 0)),
                  ("κανένας πρωτοεμφ.", mn > 0)):
        m = m & te
        r = dict(ομάδα=nm, n=int(m.sum()), Μ7=Ls(q7[m], w[m]).mean(), Μ7_επίπεδο=Ls(qL[m], w[m]).mean(),
                 άνοιγμα=Ls(PR["open"][m], w[m]).mean(), κλείσιμο=Ls(PR["close"][m], w[m]).mean())
        dd = Ls(qL[m], w[m]) - Ls(q7[m], w[m])
        r["διαφ"], r["t"] = dd.mean(), dd.mean() / (dd.std() / np.sqrt(len(dd)))
        for k, p in PR.items():
            a7, aL = mix_wf(p, q7, w, y), mix_wf(p, qL, w, y)
            dm = Ls(aL[m], w[m]) - Ls(a7[m], w[m])
            r[f"μίξη_{k[:2]}"] = dm.mean(); r[f"t_{k[:2]}"] = dm.mean() / (dm.std() / np.sqrt(len(dm)))
            for tag, qq in (("Μ7", a7), ("επ", aL)):
                x = roi(qq, o, k, m, w, .05)
                r[f"{tag}_n_{k[:2]}"], r[f"{tag}_ROI_{k[:2]}"] = x.get("n"), x.get("ROI")
        rows.append(r)
    print(pd.DataFrame(rows).round(4).to_string(index=False))
    Z = design(D, M7 + LEVEL + DLEVEL, y, 2027)
    b = ridge(Z, w, cv_fit(Z, w, y))
    print("βάρη 2008-26 (ανά 1 τυπική απόκλιση):")
    print(pd.Series(dict(zip(M7 + LEVEL + DLEVEL, b))).round(3).to_string())

    print("\n=== Γ. Επιλογή ΜΟΝΟ με παρελθόν ===")
    pool = ["glicko"] + M7 + LEVEL + DLEVEL
    qE = engine_wf(D, pool, w, y)
    for k, p in PR.items():
        print(f"Σ1 στοιχεία ανά χρονιά, αγορά {k}:")
        qs, ch = forward_wf(p, D, pool, w, y)
        cnt = pd.Series([c for v in ch.values() for c in v]).value_counts()
        print("  πόσες χρονιές από 10:", cnt.to_dict())
        R += report("Σ1 αγορά+επιλογή", qs, o, w, y, k, p)
        R += report("Σ2 αγορά+μηχανή όλης δεξαμενής", mix_wf(p, qE, w, y), o, w, y, k, p)
    print(pd.DataFrame(R).round(4).sort_values(["τιμή", "περίοδος"], kind="stable").to_string(index=False))


if __name__ == "__main__":
    main()
