"""UFC τεστ 14: βγάζω έναν έναν τους μηχανισμούς από τη μηχανή (βάση Μ7+επίπεδο, καθαροί μέσοι, αγορά + μηχανή).

Για κάθε ομάδα: ξαναχτίζεται η μηχανή χωρίς αυτήν, walk-forward 2017-26, μίξη με άνοιγμα και με κλείσιμο.
Μέτρηση: διαφορά log-loss από τη βάση και κέρδος ανά αγώνα (μονάδες, 0 αν δεν ποντάρουμε) στα ROI ≥5 πόντων, ζευγαρωτά ανά αγώνα.
Κριτήριο από πριν: ο μηχανισμός ΜΕΝΕΙ αν η αφαίρεση χειροτερεύει το log-loss με t ≥ 2 ή ρίχνει το κέρδος με t ≤ −2,
στο άνοιγμα ή στο κλείσιμο. Αλλιώς φεύγει. Μετά: μικρή φόρμουλα μόνο με όσους έμειναν (κρίνεται στο ίδιο δείγμα, άρα αισιόδοξη).
Θέλει UFC_DATA.
"""
import os

import numpy as np
import pandas as pd

import t3_mechanisms as t3
from t10_own_engine import BODY, HOME, SHER, STATS, build, roi
from t11_level_select import DLEVEL, LEVEL, Ls, engine_wf, level_features, mix_wf

pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 200)
tstat = lambda d: d.mean() / (d.std() / np.sqrt(len(d)))
GROUPS = {"ηλικία": ["age"],
          "χτυπήματα": ["sdiff_adj", "slpm", "sapm", "kd_abs15"],
          "πάλη": ["td15", "tdd", "ctrl_share"],
          "σώμα (χέρια, ύψος)": ["reach", "height"],
          "καριέρα UFC": ["lnexp", "lnlay", "ko_losses", "streak"],
          "έδρα": HOME,
          "Sherdog (ρεκόρ πριν)": SHER,
          "επίπεδο": LEVEL + DLEVEL}
BASE = ["age"] + STATS + BODY + HOME + SHER + LEVEL + DLEVEL
assert sorted(c for g in GROUPS.values() for c in g) == sorted(BASE)
HINDSIGHT = ["age", "sdiff_adj", "sapm", "home_nus", "reach", "big_w", "big_l"]


def profit(q, o, k, w, thr=.05):
    """Κέρδος ανά αγώνα σε μονάδες· 0 όπου δεν ποντάρουμε."""
    p, d1, d2 = o[f"f1_p_{k}"].values, o[f"f1_{k}_dec"].values, o[f"f2_{k}_dec"].values
    x = np.zeros(len(q))
    a, b = (q - p >= thr), (p - q >= thr)
    x[a] = np.where(w[a] == 1, d1[a] - 1, -1.0)
    x[b] = np.where(w[b] == 0, d2[b] - 1, -1.0)
    return x


def main():
    os.environ["UFC_FEATURES"] = "ufc_features_causal.csv"
    o, D, w = build()
    D = level_features(o, D)
    y = o.y.values
    te = y >= 2017
    E = {"βάση": engine_wf(D, BASE, w, y)}
    print("βάση έτοιμη", flush=True)
    for nm, g in GROUPS.items():
        E["χωρίς " + nm] = engine_wf(D, [c for c in BASE if c not in g], w, y)
        print("χωρίς", nm, "έτοιμο", flush=True)

    M, keep = {}, {}
    for k in ("open", "close"):
        p = o[f"f1_p_{k}"].values
        M[k] = {nm: mix_wf(p, q, w, y) for nm, q in E.items()}
    for k in ("open", "close"):
        Q = M[k]
        L0, P0 = Ls(Q["βάση"][te], w[te]), profit(Q["βάση"], o, k, w)[te]
        rows = []
        for nm, q in Q.items():
            L, x, r = Ls(q[te], w[te]), profit(q, o, k, w)[te], roi(q, o, k, te, w, .05)
            r22 = roi(q, o, k, y >= 2022, w, .05)
            rows.append(dict(φόρμουλα=nm, LL=L.mean(), διαφ=(L - L0).mean(), t_LL=tstat(L - L0) if nm != "βάση" else np.nan,
                             ROI=r["ROI"], SE=r["SE"], n=r["n"], χρ=r["χρ"], μονάδες=x.sum(), δ_μον=x.sum() - P0.sum(),
                             t_κέρδος=tstat(x - P0) if nm != "βάση" else np.nan, ROI_22=r22["ROI"], n_22=r22["n"]))
            if nm != "βάση":
                keep[nm] = keep.get(nm, False) or tstat(L - L0) >= 2 or tstat(x - P0) <= -2
        print(f"\n=== Αφαίρεση, τιμή {k}, 2017-26 (διαφ θετικό = χειρότερο χωρίς αυτόν) ===")
        print(pd.DataFrame(rows).round(4).to_string(index=False))

    kept = [c for nm, g in GROUPS.items() if keep["χωρίς " + nm] for c in g]
    print("\nΜΕΝΟΥΝ με το κριτήριο:", [nm for nm in GROUPS if keep["χωρίς " + nm]])
    print("ΦΕΥΓΟΥΝ:", [nm for nm in GROUPS if not keep["χωρίς " + nm]])

    F = {"Μικρή (όσοι έμειναν)": kept, "Μικρή από τις επιλογές t11 (εκ των υστέρων)": HINDSIGHT}
    for nm, cols in F.items():
        if not cols:
            continue
        qe = engine_wf(D, cols, w, y)
        print(f"\n--- {nm}: {cols}")
        print(f"  μηχανή μόνη log-loss 2017-26: {Ls(qe[te], w[te]).mean():.4f} · βάση {Ls(E['βάση'][te], w[te]).mean():.4f}")
        for k in ("open", "close"):
            q, Q0 = mix_wf(o[f"f1_p_{k}"].values, qe, w, y), M[k]["βάση"]
            L, L0 = Ls(q[te], w[te]), Ls(Q0[te], w[te])
            x, x0 = profit(q, o, k, w)[te], profit(Q0, o, k, w)[te]
            r, r22, r0 = roi(q, o, k, te, w, .05), roi(q, o, k, y >= 2022, w, .05), roi(Q0, o, k, te, w, .05)
            print(f"  {k}: LL {L.mean():.4f} διαφ {(L - L0).mean():+.4f} t {tstat(L - L0):+.1f} · ROI {r['ROI']:+.1f} ±{r['SE']:.1f} n{r['n']} χρ {r['χρ']} "
                  f"(βάση {r0['ROI']:+.1f} n{r0['n']}) · μονάδες {x.sum():.0f} vs {x0.sum():.0f} t {tstat(x - x0):+.1f} · 2022-26 {r22['ROI']:+.1f} n{r22['n']}")


if __name__ == "__main__":
    main()
