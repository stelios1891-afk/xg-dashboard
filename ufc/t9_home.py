"""UFC τεστ 9: ΕΛΕΓΧΟΣ του ευρήματος «έδρα» του τεστ 8 (εντόπιος εκτός ΗΠΑ ROI +7%, Αμερικανός στις ΗΠΑ −12%).
Ερώτημα: είναι έδρα, ή «οι Αμερικανοί είναι ακριβοί παντού»; Χωρίζουμε:
  Α εντόπιος μη-Αμερικανός vs Αμερικανός · Β εντόπιος vs άλλος ξένος · Γ ουδέτερη χώρα Αμερικανός vs μη-Αμερικανός · Δ στις ΗΠΑ
Λογιστική: αγορά + ηλικία + sapm + td15 + έδρα + Αμερικανός + ταξίδι. ROI και στη ΧΕΙΡΟΤΕΡΗ τιμή κλεισίματος.
Μηχανισμός: διαιτητές (ποσοστό νικών στις αποφάσεις vs τελειώματα). Ανά χρονιά, ανά εθνικότητα.
"""
import numpy as np
import pandas as pd

import t3_mechanisms as t3
from t2_age_repl import DATA, block, side_rows, summ
from t8_sherdog import TZ, nat_norm

pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30); pd.set_option("display.max_rows", 200)
lg = lambda p: np.log(p / (1 - p))


def main():
    o = t3.load()
    fi = pd.read_csv(DATA / "ufc_fighters.csv")
    dob = pd.to_datetime(fi[~fi.dup_name].set_index("fighter").dob)
    d = pd.to_datetime(o.date)
    o["a1"] = (d - o.f1.map(dob)).dt.days / 365.25
    o["a2"] = (d - o.f2.map(dob)).dt.days / 365.25
    A = pd.read_csv(DATA / "sherdog_fighters.csv").drop_duplicates("fighter").set_index("fighter")
    nat = A.nationality.map(nat_norm)
    cty = o.location.fillna("").str.split(",").str[-1].str.strip().replace({"United Kingdom": "UK"})
    n1, n2 = o.f1.map(nat), o.f2.map(nat)
    known = (n1.notna() & n2.notna()).values
    h1, h2 = (n1 == cty).values, (n2 == cty).values
    u1, u2 = (n1 == "USA").values, (n2 == "USA").values
    us = (cty == "USA").values
    print("== ΕΛΕΓΧΟΣ: τυχαίοι αγώνες «εντόπιος» ==")
    x = o[known & (h1 ^ h2) & ~us].sample(6, random_state=4)
    print(x[["date", "location", "f1", "f2", "f1_result", "f1_p_close"]].assign(n1=n1[x.index], n2=n2[x.index]).to_string(index=False))
    rows = []
    # Α εντόπιος μη-Αμερικανός vs Αμερικανός (εκτός ΗΠΑ)
    a1 = known & h1 & ~us & u2; a2 = known & h2 & ~us & u1
    rows += block("Α εντόπιος vs Αμερικανός", side_rows(o, a1 | a2, a1))
    b1 = known & h1 & ~us & ~h2 & ~u2; b2 = known & h2 & ~us & ~h1 & ~u1
    rows += block("Β εντόπιος vs άλλος ξένος", side_rows(o, b1 | b2, b1))
    # Γ ουδέτερη χώρα: κανείς εντόπιος
    c1 = known & ~us & ~h1 & ~h2 & u1 & ~u2; c2 = known & ~us & ~h1 & ~h2 & u2 & ~u1
    rows += block("Γ ουδέτερη: Αμερικανός vs ξένος", side_rows(o, c1 | c2, c1))
    rows += block("Γ ουδέτερη: ο ξένος", side_rows(o, c1 | c2, c2))
    # Δ ΗΠΑ
    e1 = known & us & u1 & ~u2; e2 = known & us & u2 & ~u1
    rows += block("Δ ΗΠΑ: Αμερικανός", side_rows(o, e1 | e2, e1))
    rows += block("Δ ΗΠΑ: ο ξένος", side_rows(o, e1 | e2, e2))
    print(pd.DataFrame(rows).round(3).to_string(index=False))

    # λογιστική
    rng = np.random.default_rng(7)
    flip = rng.random(len(o)) < .5
    sg = np.where(flip, -1.0, 1.0)
    w = np.where(flip, o.f1_result == "L", o.f1_result == "W").astype(float)
    te = cty.map(TZ)
    wrap = lambda t: np.minimum((t - te).abs(), 24 - (t - te).abs())
    jet = (wrap(n1.map(TZ)) - wrap(n2.map(TZ))) / 6.0
    Dd = pd.DataFrame({"age": sg * (o.a1 - o.a2), "sapm": sg * (o.f1_sapm - o.f2_sapm), "td": sg * (o.f1_td15 - o.f2_td15),
                       "home": sg * (h1.astype(float) - h2.astype(float)), "home_nus": sg * ((h1 & ~us).astype(float) - (h2 & ~us).astype(float)),
                       "american": sg * (u1.astype(float) - u2.astype(float)), "jet": sg * jet.values})
    for k in ("open", "close"):
        Dd["m"] = lg(np.clip(np.where(flip, 1 - o[f"f1_p_{k}"], o[f"f1_p_{k}"]), .01, .99))
        for per, pm in (("όλα", o.y.values > 0), ("2008-16", o.y.values <= 2016), ("2017-26", o.y.values >= 2017)):
            u = Dd.notna().all(axis=1).values & known & pm
            for cols in (["home_nus"], ["american"], ["home_nus", "american"], ["home_nus", "american", "jet"]):
                X = np.c_[Dd.m, np.ones(len(o)), Dd.age, Dd.sapm, Dd.td, Dd[cols]][u]
                b, se = t3.fit(X, w[u])
                print(f"{k:5s} {per:7s} n={u.sum()} · " + " · ".join(f"{c} b={b[5 + i]:+.3f} (t {b[5 + i] / se[5 + i]:+.1f})" for i, c in enumerate(cols)))

    # OOS log-loss
    tr, ts = o.y.values <= 2016, o.y.values >= 2017
    res = []
    for k in ("open", "close"):
        Dd["m"] = lg(np.clip(np.where(flip, 1 - o[f"f1_p_{k}"], o[f"f1_p_{k}"]), .01, .99))
        u = Dd.notna().all(axis=1).values & known
        def oos(cols):
            X = np.c_[Dd.m, np.ones(len(o))] if not cols else np.c_[Dd.m, np.ones(len(o)), Dd[cols]]
            b, _ = t3.fit(X[u & tr], w[u & tr])
            return t3.ll(t3.sig(X[u & ts] @ b), w[u & ts])
        res.append(dict(αγορά=k, μόνο_αγορά=oos([]), ηλ_sapm_td=oos(["age", "sapm", "td"]), συν_έδρα=oos(["age", "sapm", "td", "home_nus"]),
                        συν_Αμερικανός=oos(["age", "sapm", "td", "american"]), συν_και_τα_2=oos(["age", "sapm", "td", "home_nus", "american"])))
    print("log-loss 2017-26 (fit 2008-16):"); print(pd.DataFrame(res).round(4).to_string(index=False))

    # χειρότερη τιμή κλεισίματος + ανά χρονιά
    h_all = known & (h1 ^ h2) & ~us
    t = side_rows(o, h_all, h1)
    if "f1_close_lo" in o:
        lo = np.where(h1[h_all], o.f1_close_lo[h_all], o.f2_close_lo[h_all]).astype(float)
        print(f"\nROI εντόπιου στη ΧΕΙΡΟΤΕΡΗ τιμή κλεισίματος: {100 * np.where(t.w == 1, lo - 1, -1).mean():+.1f}%")
    t["pa"] = np.where(t.w == 1, t.do - 1, -1); t["pk"] = np.where(t.w == 1, t.dc - 1, -1)
    print("\nΑνά χρονιά, εντόπιος εκτός ΗΠΑ:")
    print(t.groupby("y").agg(n=("w", "size"), νίκες=("w", "mean"), p_κλείσ=("pc", "mean"), ROI_άνοιγ=("pa", lambda s: 100 * s.mean()), ROI_κλείσ=("pk", lambda s: 100 * s.mean())).round(2).T.to_string())

    # μηχανισμός: διαιτητές
    print("\nΕντόπιος εκτός ΗΠΑ: πώς τελείωσε ο αγώνας (πλευρά εντόπιου)")
    x = o[h_all]; s = h1[h_all]
    win = np.where(s, x.f1_result == "W", x.f1_result == "L")
    pc = np.where(s, x.f1_p_close, 1 - x.f1_p_close)
    for g in ("DEC", "KO", "SUB"):
        m = (x.method_grp == g).values
        print(f"  {g}: n={m.sum()} · νίκες εντόπιου {win[m].mean():.3f} · αγορά {pc[m].mean():.3f}")
    print("  methods:", x.method_grp.value_counts().to_dict())

    # ανά εθνικότητα: πλευρά ο μαχητής, αντίπαλος άλλης εθνικότητας
    rows = []
    for c in ("USA", "Brazil", "Russia", "Canada", "UK", "Australia", "Mexico", "Poland", "Japan", "Sweden", "France", "China"):
        m1 = known & (n1 == c).values & (n2 != c).values; m2 = known & (n2 == c).values & (n1 != c).values
        nh = ~(h1 | h2) | us if c != "USA" else np.ones(len(o), bool)
        for lab, mm in ((f"{c} εκτός έδρας", (m1 | m2) & ((m1 & ~h1) | (m2 & ~h2))),):
            s = summ(side_rows(o, mm, m1))
            if s:
                rows.append(dict(ομάδα=lab, **s))
    print(pd.DataFrame(rows).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
