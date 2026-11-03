"""UFC τεστ 3: όλοι οι υπόλοιποι μηχανισμοί vs αγορά (άνοιγμα / κλείσιμο).

ΜΕΡΟΣ Α — συνεχείς διαφορές μαχητή (f−αντίπαλος, τυποποιημένες), τυχαίος προσανατολισμός (seed 7):
   logit(νίκη) = a·logit(αγορά) + c + b·z   -> b, t ανά αγορά & περίοδο
ΜΕΡΟΣ Β — στρώμα στατιστικών μαζί (fit 2008-16) -> log-loss 2017-26 vs σκέτη (τεντωμένη) αγορά
ΜΕΡΟΣ Γ — δυαδικές ομάδες (πλευρά ορισμένη από πριν): νίκες vs αγορά (t), ROI με περιθώριο
ΜΕΡΟΣ Δ — τσέπες αγοράς: κίνηση γραμμής, φαβορί ανά ζώνη, γυναίκες, Fight Night vs αριθμημένα, τίτλοι
Κριτήρια: t ≥ 2, ίδιο πρόσημο 2008-16 & 2017-26, ROI θετικό στην πλειονότητα των χρονιών.
ΠΡΟΣΟΧΗ: ~35 συγκρίσεις -> ~2 «τυχαία» t≥2 αναμένονται.
"""
import os, sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from t2_age_repl import side_rows, summ  # noqa: E402

DATA = Path(os.environ.get("UFC_DATA", Path(__file__).parent / "data"))
sig = lambda z: 1 / (1 + np.exp(-z))
lg = lambda p: np.log(p / (1 - p))


def fit(X, w):
    b = np.zeros(X.shape[1]); b[0] = 1
    for _ in range(60):
        q = sig(X @ b); H = (X * (q * (1 - q))[:, None]).T @ X
        b = b + np.linalg.solve(H + 1e-9 * np.eye(len(b)), X.T @ (w - q))
    q = sig(X @ b); H = (X * (q * (1 - q))[:, None]).T @ X
    return b, np.sqrt(np.diag(np.linalg.inv(H)))


def ll(p, w):
    p = np.clip(p, 1e-6, 1 - 1e-6); return float(-np.mean(w * np.log(p) + (1 - w) * np.log(1 - p)))


def load():
    o = pd.read_csv(DATA / "ufc_fights_odds.csv")
    x = pd.read_csv(DATA / "ufc_features.csv").drop(columns=["date", "event", "f1", "f2"])
    o = o.merge(x, on="fight_url")
    o = o[o.f1_result.isin(["W", "L"]) & o.f1_p_close.notna() & o.f1_p_open.notna() & (o.date >= "2008")].copy()
    o["y"] = o.date.str[:4].astype(int)
    for s in ("f1", "f2"):
        o[f"{s}_lnexp"] = np.log1p(o[f"{s}_n_prev"])
        o[f"{s}_lnlay"] = np.log1p(o[f"{s}_layoff_d"].fillna(365))
    return o.reset_index(drop=True)


CONT = ["lnexp", "lnlay", "slpm", "sapm", "sdiff", "sdiff_adj", "td15", "tdd", "ctrl_share", "kd_abs15",
        "ko_losses", "streak", "fade", "reach", "height"]
STATS = ["sdiff_adj", "slpm", "sapm", "td15", "tdd", "ctrl_share", "kd_abs15", "fade"]


def oriented(o):
    rng = np.random.default_rng(7)
    flip = rng.random(len(o)) < 0.5
    D = pd.DataFrame({"y": o.y, "w": np.where(flip, o.f1_result == "L", o.f1_result == "W").astype(float),
                      "po": np.where(flip, 1 - o.f1_p_open, o.f1_p_open),
                      "pc": np.where(flip, 1 - o.f1_p_close, o.f1_p_close)})
    for c in CONT:
        d = o[f"f1_{c}"] - o[f"f2_{c}"]
        D[c] = np.where(flip, -d, d)
    # 5-γυρος
    D["five"] = (o.sched_rounds == 5).values
    D["fade5"] = np.where(D.five, D.fade, np.nan)
    return D


def part_a(D):
    print("\n=== Α. Κάθε μηχανισμός μόνος του, με έλεγχο τιμής (b ανά 1 τυπική απόκλιση διαφοράς) ===")
    rows = []
    for c in CONT + ["fade5"]:
        for k in ("po", "pc"):
            r = {"μηχανισμός": c, "αγορά": "άνοιγμα" if k == "po" else "κλείσιμο"}
            for per, m in (("όλα", D.y > 0), ("08-16", D.y <= 2016), ("17-26", D.y >= 2017)):
                m = m & D[c].notna()
                z = (D[c] - D[c][m].mean()) / D[c][m].std()
                X = np.c_[lg(D[k][m]), np.ones(m.sum()), z[m]]
                b, se = fit(X, D.w[m].values)
                r[f"b_{per}"], r[f"t_{per}"] = b[2], b[2] / se[2]
            r["n"] = int((D[c].notna()).sum())
            rows.append(r)
    A = pd.DataFrame(rows)
    A["✓"] = np.where((A["t_όλα"].abs() >= 2) & (np.sign(A["t_08-16"]) == np.sign(A["t_17-26"])), "✓", "")
    print(A.round(3).to_string(index=False))
    return A


def part_b(D):
    print("\n=== Β. Στρώμα στατιστικών μαζί (fit 2008-16, κρίση 2017-26) ===")
    tr, te = (D.y <= 2016).values, (D.y >= 2017).values
    Z = D[STATS].copy()
    Z = (Z - Z[tr].mean()) / Z[tr].std()
    ok = Z.notna().all(axis=1).values
    for k in ("po", "pc"):
        X1 = np.c_[lg(D[k]), np.ones(len(D))]
        X2 = np.c_[X1, Z.fillna(0).values]
        b1, _ = fit(X1[tr & ok], D.w[tr & ok].values)
        b2, se2 = fit(X2[tr & ok], D.w[tr & ok].values)
        m = te & ok
        p1, p2 = sig(X1[m] @ b1), sig(X2[m] @ b2)
        w = D.w[m].values
        d = -(w * np.log(p2) + (1 - w) * np.log(1 - p2)) + (w * np.log(p1) + (1 - w) * np.log(1 - p1))
        print(f"{'άνοιγμα ' if k == 'po' else 'κλείσιμο'}: αγορά {ll(p1, w):.4f} · +στατιστικά {ll(p2, w):.4f} · "
              f"διαφορά {d.mean():+.5f} (t {d.mean() / (d.std() / np.sqrt(len(d))):.2f}) · n={m.sum()}")
        print("   βάρη:", dict(zip(STATS, (b2[2:] / se2[2:]).round(1))), "(t ανά στατιστικό, train)")


def part_c(o):
    print("\n=== Γ. Ομάδες (πλευρά ορισμένη από πριν) ===")
    rows = []

    def add(name, m1, m2):
        """m1: ο f1 είναι η πλευρά · m2: ο f2 είναι η πλευρά (αμοιβαία αποκλειστικά)."""
        m = (m1 | m2) & ~(m1 & m2)
        t = side_rows(o, m, m1)
        for per, mm in (("όλα", t.y > 0), ("08-16", t.y <= 2016), ("17-26", t.y >= 2017)):
            s = summ(t[mm].reset_index(drop=True))
            if s:
                rows.append(dict(ομάδα=name, περίοδος=per, **s))

    g = lambda c, s: o[f"{s}_{c}"]
    add("πρωτοεμφανιζόμενος vs έμπειρος (≥3)", (g("n_prev", "f1") == 0) & (g("n_prev", "f2") >= 3),
        (g("n_prev", "f2") == 0) & (g("n_prev", "f1") >= 3))
    add("μετά από ήττα με KO", (g("last_ko_loss", "f1") == 1) & (g("last_ko_loss", "f2") == 0),
        (g("last_ko_loss", "f2") == 1) & (g("last_ko_loss", "f1") == 0))
    add("«αδικημένος» στον προηγούμενο", (g("last_robbed", "f1") == 1) & (g("last_robbed", "f2") == 0),
        (g("last_robbed", "f2") == 1) & (g("last_robbed", "f1") == 0))
    add("«τυχερός» στον προηγούμενο", (g("last_lucky", "f1") == 1) & (g("last_lucky", "f2") == 0),
        (g("last_lucky", "f2") == 1) & (g("last_lucky", "f1") == 0))
    add("απουσία >1 έτους (vs ≤1)", (g("layoff_d", "f1") > 365) & (g("layoff_d", "f2") <= 365),
        (g("layoff_d", "f2") > 365) & (g("layoff_d", "f1") <= 365))
    add("ανεβαίνει κατηγορία", g("wc_move", "f1") > 0, g("wc_move", "f2") > 0)
    add("κατεβαίνει κατηγορία", g("wc_move", "f1") < 0, g("wc_move", "f2") < 0)
    add("σερί ≥2 ηττών vs αντίπαλος χωρίς σερί ηττών", (g("streak", "f1") <= -2) & (g("streak", "f2") >= 0),
        (g("streak", "f2") <= -2) & (g("streak", "f1") >= 0))
    add("σερί ≥3 νικών", (g("streak", "f1") >= 3) & (g("streak", "f2") < 3), (g("streak", "f2") >= 3) & (g("streak", "f1") < 3))
    add("southpaw vs ορθόδοξος", (g("southpaw", "f1") == 1) & (g("southpaw", "f2") == 0),
        (g("southpaw", "f2") == 1) & (g("southpaw", "f1") == 0))
    add("μακρύτερα χέρια ≥10 εκ.", (g("reach", "f1") - g("reach", "f2")) >= 10, (g("reach", "f2") - g("reach", "f1")) >= 10)
    five = o.sched_rounds == 5
    add("5 γύροι: καλύτερη αντοχή (fade +0.1)", five & ((g("fade", "f1") - g("fade", "f2")) >= .1),
        five & ((g("fade", "f2") - g("fade", "f1")) >= .1))
    return rows


def part_d(o, rows):
    print("\n=== Δ. Τσέπες αγοράς ===")
    lgc, lgo = lg(o.f1_p_close), lg(o.f1_p_open)
    rng = np.random.default_rng(7); flip = rng.random(len(o)) < .5
    w = np.where(flip, o.f1_result == "L", o.f1_result == "W").astype(float)
    s = np.where(flip, -1, 1)
    for per, m in (("όλα", o.y > 0), ("08-16", o.y <= 2016), ("17-26", o.y >= 2017)):
        X = np.c_[s * lgc, np.ones(len(o)), s * (lgc - lgo)][m.values]
        b, se = fit(X, w[m.values])
        print(f"κίνηση γραμμής πέρα από το κλείσιμο ({per}): b={b[2]:+.3f} t={b[2] / se[2]:.2f}  (b>0: η κίνηση συνεχίζει)")

    def add(name, m1, m2):
        m = (m1 | m2) & ~(m1 & m2)
        t = side_rows(o, m, m1)
        for per, mm in (("όλα", t.y > 0), ("08-16", t.y <= 2016), ("17-26", t.y >= 2017)):
            ss = summ(t[mm].reset_index(drop=True))
            if ss:
                rows.append(dict(ομάδα=name, περίοδος=per, **ss))

    mv = o.f1_p_close - o.f1_p_open
    add("κίνηση υπέρ (≥5 μον.) — στο κλείσιμο", mv >= .05, mv <= -.05)
    fav1 = o.f1_p_close >= .5
    for lo, hi in ((.5, .6), (.6, .7), (.7, .8), (.8, 1)):
        add(f"φαβορί κλεισίματος {int(lo * 100)}-{int(hi * 100)}%", fav1 & o.f1_p_close.between(lo, hi, "left"),
            ~fav1 & (1 - o.f1_p_close).between(lo, hi, "left"))
    women = o.women.astype(bool)
    add("φαβορί · γυναίκες", women & fav1, women & ~fav1)
    add("φαβορί · άνδρες", ~women & fav1, ~women & ~fav1)
    ppv = o.event.str.match(r"^UFC \d+")
    add("φαβορί · αριθμημένα (PPV)", ppv & fav1, ppv & ~fav1)
    add("φαβορί · Fight Night/λοιπά", ~ppv & fav1, ~ppv & ~fav1)
    add("αουτσάιντερ · Fight Night/λοιπά", ~ppv & ~fav1, ~ppv & fav1)
    tf = o.title_fight.astype(bool)
    add("φαβορί · αγώνες τίτλου", tf & fav1, tf & ~fav1)


def main():
    o = load()
    D = oriented(o)
    A = part_a(D)
    part_b(D)
    rows = part_c(o)
    part_d(o, rows)
    T = pd.DataFrame(rows)
    T["✓"] = ""
    for name, g in T.groupby("ομάδα", sort=False):
        a, p1, p2 = (g[g.περίοδος == p] for p in ("όλα", "08-16", "17-26"))
        for k in ("άνοιγ", "κλείσ"):
            if len(a) and len(p1) and len(p2) and abs(a[f"t_{k}"].iloc[0]) >= 2 and \
                    np.sign(p1[f"t_{k}"].iloc[0]) == np.sign(p2[f"t_{k}"].iloc[0]):
                yrs = a[f"χρ+_{k}"].iloc[0].split("/")
                if (a[f"ROI_{k}%"].iloc[0] > 0) == (int(yrs[0]) > int(yrs[1]) / 2):
                    T.loc[a.index, "✓"] += k[:3] + " "
    cols = ["ομάδα", "περίοδος", "n", "νίκες", "p_άνοιγ", "t_άνοιγ", "ROI_άνοιγ%", "χρ+_άνοιγ",
            "p_κλείσ", "t_κλείσ", "ROI_κλείσ%", "χρ+_κλείσ", "✓"]
    print(T[cols].round(3).to_string(index=False))
    A.to_csv(DATA / "t3_part_a.csv", index=False)
    T.to_csv(DATA / "t3_groups.csv", index=False)


if __name__ == "__main__":
    main()
