"""UFC τεστ 12: αντικαταστάτες ≤14 μερών μέσα στη μηχανή και στη μίξη με την αγορά.

Ορισμένα από πριν (βάση = αγορά + μηχανή Μ7+επίπεδο, καθαροί μέσοι, walk-forward 2017-26):
  Α  η μηχανή μαθαίνει σημάδι «ο f1/f2 είναι αντικαταστάτης ≤14» (ένας συντελεστής)
  Β  μίξη + S·logit(αγορά): άλλη κλίση αγοράς όταν ο αγώνας είναι ≤14 (το εύρημα του τεστ 7)
  Γ  μίξη + S·logit(μηχανή): άλλο βάρος μηχανής όταν ο αγώνας είναι ≤14
  Δ  μίξη + σημάδι αντικαταστάτη απευθείας
  Π  εικονικός έλεγχος: το Β με αντικαταστάτες 15-28 (εκεί δεν πρέπει να βγει τίποτα)
Κριτήριο: στους αγώνες ≤14 η διαφορά log-loss από τη βάση t ≤ −2, το σύνολο όχι χειρότερο,
το ROI ≥5 μονάδων όχι χειρότερο. Μέρες = γεγονός − ημ. παραπομπής Wikipedia· άγνωστες = όχι ≤14.
Θέλει UFC_FEATURES=ufc_features_causal.csv (UFC_DATA).
"""
import numpy as np
import pandas as pd

import t3_mechanisms as t3
from t2_age_repl import DATA
from t10_own_engine import BODY, HOME, SHER, STATS, build, roi
from t11_level_select import DLEVEL, LEVEL, Ls, engine_wf, level_features

pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 200)
lg, sig = t3.lg, t3.sig
PERIODS = ((2017, 2026), (2022, 2026))


def notice(o):
    """Μέρες ειδοποίησης κάθε πλευράς (NaN αν δεν είναι αντικαταστάτης ή είναι άγνωστες), και σημάδι αντικαταστάτη."""
    R = pd.read_csv(DATA / "wiki_replacements.csv")
    idx = {}
    for f, d, n in zip(R.fighter, pd.to_datetime(R.date), R.notice_days):
        for k in (-1, 0, 1):
            idx[(f, (d + pd.Timedelta(days=k)).date())] = n
    dd = pd.to_datetime(o.date).dt.date
    n1 = np.array([idx.get((f, d), np.nan) for f, d in zip(o.f1, dd)], float)
    n2 = np.array([idx.get((f, d), np.nan) for f, d in zip(o.f2, dd)], float)
    known1 = np.array([(f, d) in idx for f, d in zip(o.f1, dd)])
    known2 = np.array([(f, d) in idx for f, d in zip(o.f2, dd)])
    return n1, n2, known1, known2


def mix(X, w, y, y0=2017):
    q = np.full(len(y), np.nan)
    for Y in range(y0, 2027):
        tr = (y >= 2012) & (y < Y)
        q[y == Y] = sig(X[y == Y] @ t3.fit(X[tr], w[tr])[0])
    return q


def tstat(d):
    return d.mean() / (d.std() / np.sqrt(len(d)))


def side_roi(q, o, k, m, w, on_repl, thr=.05):
    """ROI ≥thr χωρισμένο: όταν ποντάρουμε ΤΟΝ αντικαταστάτη / τον ΑΝΤΙΠΑΛΟ του."""
    p, d1, d2 = o[f"f1_p_{k}"].values, o[f"f1_{k}_dec"].values, o[f"f2_{k}_dec"].values
    a, b = m & (q - p >= thr), m & (p - q >= thr)
    prof = np.r_[np.where(w[a] == 1, d1[a] - 1, -1.0), np.where(w[b] == 0, d2[b] - 1, -1.0)]
    rep = np.r_[on_repl[a] == 1, on_repl[b] == -1]
    out = {}
    for nm, x in (("στον αντικ.", prof[rep]), ("στον αντίπαλο", prof[~rep])):
        out[nm] = f"{100 * x.mean():+.1f} ±{100 * x.std() / np.sqrt(len(x)):.1f} (n{len(x)})" if len(x) else "-"
    return out


def main():
    o, D, w = build()
    D = level_features(o, D)
    y = o.y.values
    n1, n2, k1, k2 = notice(o)
    s14 = (n1 <= 14).astype(float) - (n2 <= 14).astype(float)
    S14 = ((n1 <= 14) | (n2 <= 14)).astype(float)
    S15 = (((n1 > 14) & (n1 <= 28)) | ((n2 > 14) & (n2 <= 28))).astype(float) * (1 - S14)
    S7 = ((n1 <= 7) | (n2 <= 7)).astype(float)
    te = y >= 2017
    print(f"αγώνες {len(o)} · 2017-26 {te.sum()}")
    print(f"≤14: όλα {int(S14.sum())} · 2012-16 {int(S14[(y >= 2012) & (y < 2017)].sum())} · 2017-26 {int(S14[te].sum())} · "
          f"και οι 2 πλευρές ≤14: {int(((n1 <= 14) & (n2 <= 14)).sum())} · 15-28 στα 2017-26: {int(S15[te].sum())} · "
          f"αντικ. με άγνωστες μέρες: {int(((k1 & np.isnan(n1)) | (k2 & np.isnan(n2))).sum())}")

    print("\n=== ΕΛΕΓΧΟΣ γνωστών αντικαταστατών ===")
    for f, opp in (("Alexander Volkanovski", "Islam Makhachev"), ("Kamaru Usman", "Khamzat Chimaev"), ("Nate Diaz", "Conor McGregor")):
        i = o[((o.f1 == f) & (o.f2 == opp)) | ((o.f2 == f) & (o.f1 == opp))].index
        for j in i:
            print(f"  {o.date[j]} {o.f1[j]} ({n1[j]}) vs {o.f2[j]} ({n2[j]}) σημάδι f1−f2 {s14[j]:+.0f} · S {S14[j]:.0f} · "
                  f"p_άνοιγμα f1 {o.f1_p_open[j]:.2f} · νίκη f1 {w[j]:.0f}")

    base = ["age"] + STATS + BODY + HOME + SHER + LEVEL + DLEVEL
    D["r14"] = s14
    q0 = engine_wf(D, base, w, y)
    qA = engine_wf(D, base + ["r14"], w, y)
    PR = {"open": o.f1_p_open.values, "close": o.f1_p_close.values}

    print("\n=== Α. Μηχανή μόνη (χωρίς αγορά), log-loss 2017-26 ===")
    grp = (("≤7", S7), ("≤14", S14), ("15-28", S15), ("υπόλοιποι", 1 - S14 - S15))
    rows = []
    for nm, g in grp:
        m = te & (g == 1)
        dd = Ls(qA[m], w[m]) - Ls(q0[m], w[m])
        rows.append(dict(ομάδα=nm, n=int(m.sum()), μηχανή=Ls(q0[m], w[m]).mean(), με_σημάδι=Ls(qA[m], w[m]).mean(), διαφ=dd.mean(), t=tstat(dd),
                         άνοιγμα=Ls(PR["open"][m], w[m]).mean(), κλείσιμο=Ls(PR["close"][m], w[m]).mean()))
    print(pd.DataFrame(rows).round(4).to_string(index=False))

    lq0, lqA = lg(np.clip(q0, 1e-4, 1 - 1e-4)), lg(np.clip(qA, 1e-4, 1 - 1e-4))
    for k, p in PR.items():
        lp = lg(p)
        V = {"βάση": np.c_[lp, lq0], "Α σημάδι στη μηχανή": np.c_[lp, lqA], "Β κλίση αγοράς ≤14": np.c_[lp, lq0, S14 * lp],
             "Γ βάρος μηχανής ≤14": np.c_[lp, lq0, S14 * lq0], "Δ σημάδι στη μίξη": np.c_[lp, lq0, s14],
             "Π κλίση αγοράς 15-28": np.c_[lp, lq0, S15 * lp]}
        Q = {nm: mix(X, w, y) for nm, X in V.items()}
        print(f"\n=== Β. Μίξη με αγορά, τιμή {k} (διαφ = log-loss έναντι βάσης, αρνητικό = καλύτερο) ===")
        rows = []
        for a, b in PERIODS:
            per = (y >= a) & (y <= b)
            for nm, q in Q.items():
                r = dict(περίοδος=f"{a}-{b}", φόρμουλα=nm)
                for tag, m in (("όλοι", per), ("≤14", per & (S14 == 1)), ("15-28", per & (S15 == 1))):
                    dd = Ls(q[m], w[m]) - Ls(Q["βάση"][m], w[m])
                    r[f"LL_{tag}"] = Ls(q[m], w[m]).mean()
                    if nm != "βάση":
                        r[f"διαφ_{tag}"], r[f"t_{tag}"] = dd.mean(), tstat(dd)
                    x = roi(q, o, k, m, w, .05)
                    r[f"ROI5_{tag}"], r[f"SE_{tag}"], r[f"n_{tag}"], r[f"χρ_{tag}"] = x.get("ROI"), x.get("SE"), x.get("n"), x.get("χρ")
                rows.append(r)
        T = pd.DataFrame(rows).round(4)
        print(T[[c for c in T.columns if "15-28" not in c]].to_string(index=False))
        print("15-28 (εικονικός έλεγχος):")
        print(T[["περίοδος", "φόρμουλα"] + [c for c in T.columns if "15-28" in c]].to_string(index=False))

        print("συντελεστές, εκπαίδευση 2012-26 (t):")
        tr = y >= 2012
        for nm in V:
            bb, se = t3.fit(V[nm][tr], w[tr])
            print(f"  {nm}: " + " · ".join(f"{b_:+.3f} (t {b_ / s_:+.1f})" for b_, s_ in zip(bb, se)))

        print("ROI ≥5 της βάσης μέσα στους ≤14, 2017-26, ανά πλευρά που ποντάρουμε:")
        for nm in ("βάση", "Β κλίση αγοράς ≤14", "Δ σημάδι στη μίξη"):
            print(f"  {nm}: {side_roi(Q[nm], o, k, te & (S14 == 1) & (s14 != 0), w, s14)}")
        x = roi(Q["βάση"], o, k, te & (S14 == 0), w, .05)
        print(f"  βάση χωρίς καθόλου ≤14: ROI {x['ROI']:+.1f} ±{x['SE']:.1f} (n{x['n']}) · χρονιές {x['χρ']}")


if __name__ == "__main__":
    main()
