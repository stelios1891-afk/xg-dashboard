"""UFC τεστ 16: στήσιμο φόρμουλας χωρίς Pinnacle. Ασφαλείς τιμές (άνοιγμα = μέση βιβλίων σ1, κλείσιμο = κέρδος στη χειρότερη τιμή), 2017-26.

Φόρμουλες: 6 μηχανισμοί (ηλικία, χτυπήματα, πάλη, σώμα, έδρα, επίπεδο) και πυρήνας 3 (ηλικία, χτυπήματα, έδρα) δίπλα.
Ορισμένα από πριν:
  2 μέσος στατιστικών: όλη η καριέρα / φθορά 2 / φθορά 4 / μέσος 3 ετών. Περνά αν ο μέσος log-loss άνοιγμα+κλείσιμο t ≤ −2 και οι μονάδες δεν πέφτουν.
  3 πρωτοεμφανιζόμενοι: ROI μέσα/έξω. Κόβουμε μόνο αν το ROI μέσα +2 SE < 0 και στις δύο τιμές.
  4 αντικαταστάτες ≤14: το ίδιο.
  5 κατώφλι: ROI, μονάδες, χρονιές για 3-12 πόντους. Ψάχνουμε περιοχή, όχι κορυφή ενός σημείου.
  6 βάρη μίξης: βάρη ανοίγματος ή κλεισίματος όταν μπαίνουμε στη μέση της διαδρομής (σ5), έναντι βαρών φτιαγμένων για το σ5.
Θέλει UFC_DATA.
"""
import os

os.environ["T15_SAFE"] = "1"
import numpy as np
import pandas as pd

import t3_mechanisms as t3
from t2_age_repl import DATA
from t10_own_engine import build
from t11_level_select import Ls, engine_wf, level_features, mix_wf
from t12_short_notice import notice
from t14_drop_mechanisms import GROUPS, profit
from t15_combos import safe_prices

pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 200)
lg, sig = t3.lg, t3.sig
tstat = lambda d: d.mean() / (d.std() / np.sqrt(len(d)))
SIX = [c for g in ("ηλικία", "χτυπήματα", "πάλη", "σώμα (χέρια, ύψος)", "έδρα", "επίπεδο") for c in GROUPS[g]]
CORE = [c for g in ("ηλικία", "χτυπήματα", "έδρα") for c in GROUPS[g]]


def load(name):
    os.environ["UFC_FEATURES"] = name
    o, D, w = build()
    D = level_features(o, D)
    return safe_prices(o, D, w)


def bets(q, p, d1, d2, w, m, thr=.05):
    a, b = m & (q - p >= thr), m & (p - q >= thr)
    x = np.zeros(len(q))
    x[a] = np.where(w[a] == 1, d1[a] - 1, -1.0)
    x[b] = np.where(w[b] == 0, d2[b] - 1, -1.0)
    return x, a | b


def line(x, on, y, m):
    v = x[m & on]
    if not len(v):
        return dict(n=0)
    by = pd.Series(x[m & on]).groupby(y[m & on]).sum()
    return dict(n=len(v), ROI=100 * v.mean(), SE=100 * v.std() / np.sqrt(len(v)), μον=v.sum(), χρ=f"{(by > 0).sum()}/{len(by)}")


def main():
    o, D, w = load("ufc_features_causal.csv")
    y = o.y.values
    te = y >= 2017
    po, pc = o.f1_p_open.values, o.f1_p_close.values
    P = {"open": (po, o.f1_open_dec.values, o.f2_open_dec.values), "close": (pc, o.f1_close_dec.values, o.f2_close_dec.values)}
    E = {"6": engine_wf(D, SIX, w, y), "3": engine_wf(D, CORE, w, y)}
    Q = {(f, k): mix_wf(P[k][0], E[f], w, y) for f in E for k in P}

    print("=== 2. Μέσος στατιστικών (log-loss μέσος ανοίγματος και κλεισίματος, διαφορά από όλη την καριέρα) ===")
    S0 = (Ls(Q[("6", "open")][te], w[te]) + Ls(Q[("6", "close")][te], w[te])) / 2
    X0 = {k: profit(Q[("6", k)], o, k, w)[te] for k in P}
    rows = [dict(μέσος="όλη η καριέρα", LL=S0.mean(), μον_op=X0["open"].sum(), n_op=(X0["open"] != 0).sum(), μον_cl=X0["close"].sum(), n_cl=(X0["close"] != 0).sum())]
    for nm, f in (("φθορά 2 ετών", "ufc_features_decay2.csv"), ("φθορά 4 ετών", "ufc_features_decay4.csv"), ("μέσος 3 ετών", "ufc_features_recent3.csv")):
        o2, D2, w2 = load(f)
        assert (o2.fight_url.values == o.fight_url.values).all() and (w2 == w).all()
        e = engine_wf(D2, SIX, w, y)
        qo, qc = mix_wf(po, e, w, y), mix_wf(pc, e, w, y)
        s = (Ls(qo[te], w[te]) + Ls(qc[te], w[te])) / 2
        xo, xc = profit(qo, o, "open", w)[te], profit(qc, o, "close", w)[te]
        rows.append(dict(μέσος=nm, LL=s.mean(), διαφ=(s - S0).mean(), t=tstat(s - S0), μον_op=xo.sum(), n_op=(xo != 0).sum(), t_op=tstat(xo - X0["open"]),
                         μον_cl=xc.sum(), n_cl=(xc != 0).sum(), t_cl=tstat(xc - X0["close"])))
    print(pd.DataFrame(rows).round(4).to_string(index=False))

    n1, n2, *_ = notice(o)
    deb = (o.f1_n_prev.values == 0) | (o.f2_n_prev.values == 0)
    rep = (n1 <= 14) | (n2 <= 14)
    print("\n=== 3-4. Ομάδες αγώνων, κατώφλι 5 πόντοι ===")
    rows = []
    for f in E:
        for k in P:
            x, on = bets(Q[(f, k)], *P[k], w, te)
            for nm, g in (("όλοι", np.ones(len(y), bool)), ("με πρωτοεμφ.", deb), ("χωρίς πρωτοεμφ.", ~deb), ("με αντικ. ≤14", rep), ("χωρίς αντικ. ≤14", ~rep), ("χωρίς και τα δύο", ~deb & ~rep)):
                rows.append(dict(φόρμουλα=f, τιμή=k, ομάδα=nm, **line(x, on, y, g & te)))
    print(pd.DataFrame(rows).round(2).to_string(index=False))

    print("\n=== 5. Κατώφλι ===")
    rows = []
    for k in P:
        for thr in (.03, .04, .05, .06, .07, .08, .10, .12):
            for f in E:
                x, on = bets(Q[(f, k)], *P[k], w, te, thr)
                rows.append(dict(τιμή=k, κατώφλι=int(thr * 100), φόρμουλα=f, **line(x, on, y, te), ROI_22=line(x, on, y, y >= 2022).get("ROI")))
    print(pd.DataFrame(rows).round(2).to_string(index=False))

    print("\n=== 6. Βάρη μίξης στη μέση της διαδρομής (σ5) ===")
    sp = pd.read_csv(DATA / "bfo_spark.csv")
    sp = sp[sp.n == 10].drop_duplicates(["matchup_id", "fighter_url"])
    d = {}
    for s in ("1", "2"):
        u = f"f{s}_bfo_url"
        d[s] = o[["matchup_id", u]].merge(sp[["matchup_id", "fighter_url", "s5"]].rename(columns={"fighter_url": u}), on=["matchup_id", u], how="left").s5.values
    p5 = (1 / d["1"]) / (1 / d["1"] + 1 / d["2"])
    has = np.isfinite(p5)
    p5f = np.where(has, p5, po)
    for f in E:
        Z5 = np.c_[lg(p5f), lg(np.clip(E[f], 1e-4, 1 - 1e-4))]
        qs = {"βάρη σ5": mix_wf(p5f, E[f], w, y)}
        for nm, pk in (("βάρη ανοίγματος", po), ("βάρη κλεισίματος", pc)):
            Zk = np.c_[lg(pk), lg(np.clip(E[f], 1e-4, 1 - 1e-4))]
            q = np.full(len(y), np.nan)
            for Y in range(2017, 2027):
                tr = (y >= 2012) & (y < Y)
                q[y == Y] = sig(Z5[y == Y] @ t3.fit(Zk[tr], w[tr])[0])
            qs[nm] = q
        m = te & has
        for nm, q in qs.items():
            x, on = bets(q, p5, d["1"], d["2"], w, m)
            print(f"  {f}: {nm}: LL {Ls(q[m], w[m]).mean():.4f} · {line(x, on, y, m)}")
        tr = y >= 2012
        for nm, pk in (("άνοιγμα σ1", po), ("σ5", p5f), ("κλείσιμο", pc)):
            b, se = t3.fit(np.c_[lg(pk), lg(np.clip(E[f], 1e-4, 1 - 1e-4))][tr], w[tr])
            print(f"     βάρη {nm} 2012-26: αγορά {b[0]:+.3f} (t {b[0] / se[0]:+.1f}) · μηχανή {b[1]:+.3f} (t {b[1] / se[1]:+.1f})")


if __name__ == "__main__":
    main()
