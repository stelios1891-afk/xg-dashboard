"""UFC τεστ 1: σκέτη βαθμολογία μαχητή (Glicko-1) vs άνοιγμα/κλείσιμο BestFightOdds.

Walk-forward: κάθε αγώνας προβλέπεται ΜΟΝΟ με αγώνες πριν από αυτόν (ζέσταμα 1994-2007).
Παράμετροι (πλέγμα) ρυθμίζονται στο 2008-2016, κρίση στο 2017-2026 (εκτός δείγματος).
  RD0      αβεβαιότητα νέου μαχητή
  C        αύξηση αβεβαιότητας ανά 365 μέρες απουσίας
  DEBUT    αρχική βαθμολογία πρωτοεμφανιζόμενου (1500 + DEBUT)
  FIN      πολλαπλασιαστής ενημέρωσης για KO/υποταγή (απόφαση = 1)
  SPLIT    πολλαπλασιαστής για διχασμένη/πλειοψηφίας απόφαση
Μετά: μία κλίμακα s (p = σ(s·logit)) από το 2008-16.

Χρήση: python ufc/t1_rating.py   (UFC_DATA όπως στα άλλα)
"""
import itertools, math, os
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(os.environ.get("UFC_DATA", Path(__file__).parent / "data"))
Q = math.log(10) / 400


def g(rd):
    return 1 / math.sqrt(1 + 3 * Q * Q * rd * rd / math.pi ** 2)


def run(F, RD0, C, DEBUT, FIN, SPLIT):
    """Επιστρέφει x = λογάριθμος-λόγος (logit) πρόβλεψης για τον f1, πριν τον αγώνα."""
    R, RD, LAST = {}, {}, {}
    out = np.full(len(F), np.nan)
    for i, (d, a, b, res, mg) in enumerate(F):
        for p in (a, b):
            if p not in R:
                R[p], RD[p] = 1500.0 + DEBUT, RD0
            else:
                t = (d - LAST[p]) / 365.0
                RD[p] = min(math.sqrt(RD[p] ** 2 + C * C * t), RD0)
        ra, rb, sa, sb = R[a], R[b], RD[a], RD[b]
        out[i] = Q * g(math.sqrt(sa * sa + sb * sb)) * (ra - rb)  # logit της πιθανότητας f1
        LAST[a] = LAST[b] = d
        if res is None:  # NC: μόνο ενημέρωση χρόνου
            continue
        m = FIN if mg == "FIN" else SPLIT if mg == "SPLIT" else 1.0
        new = {}
        for p, r_p, s_p, r_o, s_o, s in ((a, ra, sa, rb, sb, res), (b, rb, sb, ra, sa, 1 - res)):
            gr = g(s_o)
            E = 1 / (1 + 10 ** (-gr * (r_p - r_o) / 400))
            den = 1 / s_p ** 2 + Q * Q * gr * gr * E * (1 - E)
            new[p] = (r_p + m * Q / den * gr * (s - E), max(math.sqrt(1 / den), 30.0))
        for p, (r, rd) in new.items():
            R[p], RD[p] = r, rd
    run.state = (R, RD)
    return out


def ll(p, w):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-np.mean(w * np.log(p) + (1 - w) * np.log(1 - p)))


def sig(x):
    return 1 / (1 + np.exp(-x))


def main():
    o = pd.read_csv(DATA / "ufc_fights_odds.csv")
    o["d"] = pd.to_datetime(o.date)
    o = o.sort_values(["d", "event"], kind="stable").reset_index(drop=True)
    res = o.f1_result.map({"W": 1.0, "L": 0.0, "D": 0.5})
    dec_split = o.method.str.contains("Split|Majority", na=False)
    mg = np.where(o.method_grp.isin(["KO", "SUB"]), "FIN", np.where(dec_split, "SPLIT", "DEC"))
    F = [(d.toordinal(), a, b, (None if pd.isna(r) else r), m)
         for d, a, b, r, m in zip(o.d, o.f1, o.f2, res, mg)]

    y = o.d.dt.year
    ev = (o.f1_result.isin(["W", "L"]) & o.f1_p_close.notna() & o.f1_p_open.notna() & (y >= 2008)).values
    w = (o.f1_result == "W").astype(float).values
    tr, te = ev & (y <= 2016).values, ev & (y >= 2017).values

    grid = dict(RD0=[275, 350, 450], C=[60, 100, 150, 220], DEBUT=[-75, -150], FIN=[0.8, 1.0, 1.3], SPLIT=[0.25, 0.5, 1.0])
    rows = []
    for vals in itertools.product(*grid.values()):
        P = dict(zip(grid, vals))
        x = run(F, **P)
        # καλύτερη κλίμακα στο train
        best = min((ll(sig(s * x[tr]), w[tr]), s) for s in np.arange(0.2, 1.51, 0.05))
        rows.append({**P, "ll_tr": best[0], "s": best[1], "x": x})
        print(P, round(best[0], 4), round(best[1], 2), flush=True)
    G = pd.DataFrame(rows).sort_values("ll_tr")
    print("\nΚΑΛΥΤΕΡΑ 8 (train 2008-16):")
    print(G.drop(columns="x").head(8).round(4).to_string(index=False))
    b = G.iloc[0]
    p = sig(b.s * b.x)
    o["p_model"] = p

    print(f"\nΕπιλογή: {dict((k, b[k]) for k in grid)}  κλίμακα {b.s:.2f}")
    print("\nlog-loss (μικρότερο = καλύτερο), ίδιοι αγώνες:")
    tab = []
    for name, m in [("2008-16 (ρύθμιση)", tr), ("2017-26 (εκτός δείγματος)", te)] + \
                   [(str(yy), ev & (y == yy).values) for yy in range(2008, 2027)]:
        tab.append(dict(περίοδος=name, n=int(m.sum()), μοντέλο=ll(p[m], w[m]),
                        άνοιγμα=ll(o.f1_p_open.values[m], w[m]), κλείσιμο=ll(o.f1_p_close.values[m], w[m])))
    T = pd.DataFrame(tab)
    T["μοντ−άνοιγ"] = T.μοντέλο - T.άνοιγμα
    T["μοντ−κλείσ"] = T.μοντέλο - T.κλείσιμο
    print(T.round(4).to_string(index=False))
    yrs = T.iloc[2:]
    print(f"\nχρονιές όπου μοντέλο < άνοιγμα: {(yrs['μοντ−άνοιγ'] < 0).sum()}/{len(yrs)} · "
          f"< κλείσιμο: {(yrs['μοντ−κλείσ'] < 0).sum()}/{len(yrs)}")

    # βαθμονόμηση από πλευρά φαβορί του μοντέλου (εκτός δείγματος)
    m = te
    pf = np.maximum(p[m], 1 - p[m]); wf = np.where(p[m] >= .5, w[m], 1 - w[m])
    cal = pd.DataFrame({"p": pf, "w": wf, "b": pd.cut(pf, [.5, .6, .7, .8, .9, 1])})
    print("\nβαθμονόμηση 2017-26 (φαβορί του μοντέλου):")
    print(cal.groupby("b", observed=True).agg(n=("w", "size"), p=("p", "mean"), κέρδισε=("w", "mean")).round(3).to_string())

    # προσθέτει πληροφορία στην αγορά; logit(p) = a·logit(αγορά) + b·logit(μοντέλο), fit 2008-16, κρίση 2017-26
    lg = lambda q: np.log(q / (1 - q))
    for mk in ("f1_p_open", "f1_p_close"):
        X = np.c_[lg(o[mk].values), lg(np.clip(p, 1e-4, 1 - 1e-4))]
        bb = np.array([1.0, 0.0])
        for _ in range(50):  # Newton
            z = X[tr] @ bb; q = sig(z); H = (X[tr] * (q * (1 - q))[:, None]).T @ X[tr]
            bb = bb + np.linalg.solve(H, X[tr].T @ (w[tr] - q))
        print(f"\nαγορά={mk[5:]}: βάρος αγοράς {bb[0]:.3f}, βάρος μοντέλου {bb[1]:.3f} · "
              f"2017-26 log-loss μίξη {ll(sig(X[te] @ bb), w[te]):.4f} vs σκέτη αγορά {ll(o[mk].values[te], w[te]):.4f}")

    o[["date", "event", "f1", "f2", "f1_result", "method", "p_model", "f1_p_open", "f1_p_close"]].to_csv(
        DATA / "t1_rating_preds.csv", index=False)


if __name__ == "__main__":
    main()
