"""UFC τεστ 4: ρεαλισμός ανοίγματος — πόσο αντέχει το πλεονέκτημα (ηλικία + sapm + td15) κατά μήκος της γραμμής.

Σειρά BFO (bfo_spark.csv): 10 σημεία, σ0 = άνοιγμα (1 βιβλίο), ... σ9 ≈ κλείσιμο. Ο χρόνος ανάμεσα στα σημεία ΔΕΝ είναι γνωστός.
Για κάθε σημείο k: fit 2008-16 logit(νίκη)=a·logit(p_k)+c+ηλικία+sapm+td15 -> 2017-26:
  κέρδος log-loss vs σκέτη (τεντωμένη) p_k · ROI πονταρίσματος όταν μοντέλο − p_k ≥ 3/5/8 μονάδες, στην τιμή σ_k (με περιθώριο)
  + τυφλός κανόνας: νεότερος με διαφορά ≥8 ετών στην τιμή σ_k.
"""
import os, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
import t3_mechanisms as t3

DATA = Path(os.environ.get("UFC_DATA", Path(__file__).parent / "data"))


def main():
    o = t3.load()
    fi = pd.read_csv(DATA / "ufc_fighters.csv"); dob = pd.to_datetime(fi[~fi.dup_name].set_index("fighter").dob)
    d = pd.to_datetime(o.date)
    o["a1"] = (d - o.f1.map(dob)).dt.days / 365.25; o["a2"] = (d - o.f2.map(dob)).dt.days / 365.25
    sp = pd.read_csv(DATA / "bfo_spark.csv")
    sp = sp[sp.n == 10]
    o["u1"], o["u2"] = o.f1_bfo_url, o.f2_bfo_url  # αντιστοίχιση από ufc_build (όχι ονόματα)
    S = [f"s{i}" for i in range(10)]
    o = o.merge(sp[["matchup_id", "fighter_url"] + S].rename(columns={"fighter_url": "u1", **{s: s + "_1" for s in S}}), on=["matchup_id", "u1"])
    o = o.merge(sp[["matchup_id", "fighter_url"] + S].rename(columns={"fighter_url": "u2", **{s: s + "_2" for s in S}}), on=["matchup_id", "u2"])
    # έλεγχος: σ0 = άνοιγμα, σ9 ≈ κλείσιμο
    print(f"αγώνες με πλήρη σειρά και για τους 2: {len(o)}")
    print(f"σ0 = άνοιγμα (±0.01): {(abs(o.s0_1 - o.f1_open_dec) < .01).mean():.3f} · "
          f"σ9 vs μέσο κλεισίματος: διάμεση |διαφορά| {np.median(abs(o.s9_1 - o.f1_close_dec)):.3f}")
    rng = np.random.default_rng(7); flip = rng.random(len(o)) < .5; sg = np.where(flip, -1, 1)
    w = np.where(flip, o.f1_result == "L", o.f1_result == "W").astype(float)
    F = pd.DataFrame({"age": sg * (o.a1 - o.a2), "sapm": sg * (o.f1_sapm - o.f2_sapm), "td15": sg * (o.f1_td15 - o.f2_td15)})
    y = o.y.values; tr, te = y <= 2016, y >= 2017
    ok = F.notna().all(axis=1).values
    Z = ((F - F[tr].mean()) / F[tr].std()).fillna(0).values
    rows = []
    for k in range(10):
        d1, d2 = o[f"s{k}_1"].values, o[f"s{k}_2"].values
        dme, dop = np.where(flip, d2, d1), np.where(flip, d1, d2)  # τιμή «δικής μας» πλευράς / αντιπάλου
        p = (1 / dme) / (1 / dme + 1 / dop)
        X0 = np.c_[t3.lg(p), np.ones(len(p))]; X = np.c_[X0, Z]
        b0, _ = t3.fit(X0[tr & ok], w[tr & ok]); b, _ = t3.fit(X[tr & ok], w[tr & ok])
        m = te & ok
        q0, q = t3.sig(X0[m] @ b0), t3.sig(X[m] @ b)
        ww = w[m]
        dl = -(ww * np.log(q) + (1 - ww) * np.log(1 - q)) + (ww * np.log(q0) + (1 - ww) * np.log(1 - q0))
        r = dict(σημείο=k, n=int(m.sum()), περιθώριο=np.mean(1 / d1 + 1 / d2) - 1,
                 κέρδος_ll=dl.mean(), t_ll=dl.mean() / (dl.std() / np.sqrt(len(dl))))
        pm, pk, dm, do_ = q, p[m], dme[m], dop[m]
        for thr in (.03, .05, .08):
            a = pm - pk >= thr; bsel = (1 - pm) - (1 - pk) >= thr
            prof = np.r_[np.where(ww[a] == 1, dm[a] - 1, -1), np.where(ww[bsel] == 0, do_[bsel] - 1, -1)]
            r[f"ROI≥{int(thr*100)}%"] = 100 * prof.mean() if len(prof) else np.nan
            r[f"n≥{int(thr*100)}"] = len(prof)
        # τυφλός κανόνας ηλικίας ≥8
        gap = (o.a1 - o.a2).values[m]; yo1 = gap <= -8; yo2 = gap >= 8
        d1m, d2m = d1[m], d2[m]; w1 = (o.f1_result == "W").values[m]
        prof = np.r_[np.where(w1[yo1], d1m[yo1] - 1, -1), np.where(~w1[yo2], d2m[yo2] - 1, -1)]
        r["νεότερος≥8 ROI%"] = 100 * prof.mean(); r["n_νεότ"] = len(prof)
        rows.append(r)
    T = pd.DataFrame(rows)
    pd.set_option("display.width", 250)
    print("\n2017-26 (εκτός δείγματος). σημείο 0 = άνοιγμα (1 βιβλίο) … 9 ≈ κλείσιμο")
    print(T.round(4).to_string(index=False))
    T.to_csv(DATA / "t4_open_realism.csv", index=False)


if __name__ == "__main__":
    main()
