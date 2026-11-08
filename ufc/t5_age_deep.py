"""UFC τεστ 5: τι μετράει πραγματικά η ηλικία; (3/11, Στελιος «ναι, τρεξτα»)

Τ1 «παλιά στατιστικά»: sapm/td15 με βάρος προσφάτων (μισή ζωή H=1 ή 2 έτη) αντί για ίσο βάρος καριέρας.
    Αν η ηλικία αδυνατίζει με τα φρέσκα στατιστικά -> η ηλικία διόρθωνε μπαγιάτικα νούμερα.
Τ2 καμπύλη ηλικίας: πάνω-από-32 (max(0,ηλ−32)) και κάτω-από-25 (max(0,25−ηλ)) ανά κατηγορία βάρους
    (ελαφριές ≤145 + γυναίκες · μεσαίες 155-185 · βαριές 205+).
Τ3 φήμη: νίκες UFC, αγώνες τίτλου, main events πριν. Μένει η ηλικία με έλεγχο φήμης;
    + «διάσημος μεγάλος» (≥1 τίτλος ή ≥3 main events) vs «άγνωστος μεγάλος».
Όλα: έλεγχος τιμής (a·logit αγοράς), τυχαίος προσανατολισμός (seed 7), fit 2008-16 / κρίση 2017-26.
"""
import os, sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import t3_mechanisms as t3  # noqa: E402
from t2_age_repl import side_rows, summ  # noqa: E402

DATA = Path(os.environ.get("UFC_DATA", Path(__file__).parent / "data"))
T0 = 900.0
LBS = {"Strawweight": 115, "Flyweight": 125, "Bantamweight": 135, "Featherweight": 145, "Lightweight": 155,
       "Welterweight": 170, "Middleweight": 185, "Light Heavyweight": 205, "Heavyweight": 265}


def extra_features():
    F = pd.read_csv(DATA / "ufc_fights.csv")
    F["d"] = pd.to_datetime(F.date)
    F["pos"] = F.groupby("event", sort=False).cumcount() + 1  # 1 = main event (σειρά ufcstats)
    rows = []
    for me, op in (("f1", "f2"), ("f2", "f1")):
        rows.append(pd.DataFrame({
            "fid": F.index, "d": F.d, "fighter": F[me], "pos": F.pos, "title": F.title_fight.astype(int),
            "win": (F.f1_result == ("W" if me == "f1" else "L")).astype(int),
            "t": F.fight_time_s, "sig_ab": F[f"{op}_sig"], "td": F[f"{me}_td"]}))
    L = pd.concat(rows).sort_values(["d", "fid"], kind="stable").reset_index(drop=True)
    ok = L.t.notna() & (L.t > 0) & L.sig_ab.notna()
    mu_ab = L.sig_ab[ok].sum() / L.t[ok].sum()
    mu_td = L.td[ok].sum() / L.t[ok].sum()
    out = {}
    st = {}
    for r in L.itertuples():
        s = st.get(r.fighter)
        feat = {}
        if s is None:
            s = dict(wins=0, title=0, main=0, last=r.d, **{f"{k}{h}": 0.0 for h in (1, 2) for k in ("ab", "td", "t")})
        dd = (r.d - s["last"]).days
        for h in (1, 2):
            dec = 0.5 ** (dd / (365.0 * h))
            for k in ("ab", "td", "t"):
                s[f"{k}{h}"] *= dec
            feat[f"sapm_r{h}"] = 60 * (s[f"ab{h}"] + mu_ab * T0) / (s[f"t{h}"] + T0)
            feat[f"td15_r{h}"] = 900 * (s[f"td{h}"] + mu_td * T0) / (s[f"t{h}"] + T0)
        feat.update(wins_prev=s["wins"], title_prev=s["title"], main_prev=s["main"])
        out[(r.fid, r.fighter)] = feat
        if ok[r.Index]:
            for h in (1, 2):
                s[f"ab{h}"] += r.sig_ab; s[f"td{h}"] += 0 if pd.isna(r.td) else r.td; s[f"t{h}"] += r.t
        s["wins"] += r.win; s["title"] += r.title; s["main"] += int(r.pos == 1); s["last"] = r.d
        st[r.fighter] = s
    E = F[["fight_url", "f1", "f2"]].copy()
    for me in ("f1", "f2"):
        X = pd.DataFrame([out.get((i, n), {}) for i, n in zip(F.index, F[me])])
        E = E.join(X.add_prefix(me + "_"))
    E["lbs"] = F.weightclass.map(lambda s: next((v for k, v in sorted(LBS.items(), key=lambda kv: -len(kv[0])) if k in str(s)), np.nan))
    E["women"] = F.women
    return E.drop(columns=["f1", "f2"])


def build():
    o = t3.load()
    o = o.merge(extra_features(), on="fight_url", suffixes=("", "_x"))
    fi = pd.read_csv(DATA / "ufc_fighters.csv"); dob = pd.to_datetime(fi[~fi.dup_name].set_index("fighter").dob)
    d = pd.to_datetime(o.date)
    o["a1"] = (d - o.f1.map(dob)).dt.days / 365.25; o["a2"] = (d - o.f2.map(dob)).dt.days / 365.25
    rng = np.random.default_rng(7); flip = rng.random(len(o)) < .5; sg = np.where(flip, -1, 1)
    D = pd.DataFrame({"y": o.y.values, "w": np.where(flip, o.f1_result == "L", o.f1_result == "W").astype(float),
                      "po": np.where(flip, 1 - o.f1_p_open, o.f1_p_open), "pc": np.where(flip, 1 - o.f1_p_close, o.f1_p_close)})
    diff = lambda c: sg * (o[f"f1_{c}"] - o[f"f2_{c}"]).values
    D["age"] = sg * (o.a1 - o.a2).values
    D["over32"] = sg * (np.maximum(0, o.a1 - 32) - np.maximum(0, o.a2 - 32)).values
    D["under25"] = sg * (np.maximum(0, 25 - o.a1) - np.maximum(0, 25 - o.a2)).values
    for c in ("sapm", "td15", "sapm_r1", "td15_r1", "sapm_r2", "td15_r2"):
        D[c] = diff(c)
    for c in ("wins_prev", "title_prev", "main_prev"):
        D[c] = sg * (np.log1p(o[f"f1_{c}"]) - np.log1p(o[f"f2_{c}"])).values
    D["cls"] = np.where(o.women | (o.lbs <= 145), "ελαφριές+γυναίκες", np.where(o.lbs >= 205, "βαριές 205+", "μεσαίες 155-185"))
    D.loc[o.lbs.isna() & ~o.women.astype(bool), "cls"] = "άγνωστη"
    return o, D


def coef(D, k, cols, m):
    m = m & D[cols].notna().all(axis=1)
    Z = D.loc[m, cols] / D.loc[m, cols].std()
    X = np.c_[t3.lg(D[k][m]), np.ones(m.sum()), Z.values]
    b, se = t3.fit(X, D.w[m].values)
    return {c: (b[2 + i], b[2 + i] / se[2 + i]) for i, c in enumerate(cols)}, int(m.sum())


def oos(D, k, cols):
    tr, te = (D.y <= 2016).values, (D.y >= 2017).values
    allc = ["age", "sapm", "td15", "sapm_r1", "td15_r1", "sapm_r2", "td15_r2", "over32", "under25"]
    ok = D[allc].notna().all(axis=1).values
    base = np.c_[t3.lg(D[k]), np.ones(len(D))]
    b0, _ = t3.fit(base[tr & ok], D.w[tr & ok].values)
    m = te & ok; w = D.w[m].values; p0 = t3.sig(base[m] @ b0)
    Z = D[cols]; Z = ((Z - Z[tr].mean()) / Z[tr].std()).fillna(0).values
    X = np.c_[base, Z]; b, _ = t3.fit(X[tr & ok], D.w[tr & ok].values); p = t3.sig(X[m] @ b)
    dl = -(w * np.log(p) + (1 - w) * np.log(1 - p)) + (w * np.log(p0) + (1 - w) * np.log(1 - p0))
    yr = pd.Series(dl).groupby(D.y[m].values).mean()
    return dl.mean(), dl.mean() / (dl.std() / np.sqrt(len(dl))), int((yr < 0).sum())


def fmt(r):
    return " · ".join(f"{c} {b:+.3f} (t {t:+.1f})" for c, (b, t) in r.items())


def main():
    o, D = build()
    allm = D.y > 0
    print("=== Τ1. «Παλιά στατιστικά»: ηλικία με στατιστικά καριέρας vs με βάρος προσφάτων ===")
    print("(συντελεστές ανά 1 τυπική απόκλιση, 2008-26, έλεγχος τιμής)")
    for k, nm in (("po", "άνοιγμα"), ("pc", "κλείσιμο")):
        for lab, cols in (("καριέρα", ["age", "sapm", "td15"]), ("πρόσφατα H=1y", ["age", "sapm_r1", "td15_r1"]),
                          ("πρόσφατα H=2y", ["age", "sapm_r2", "td15_r2"])):
            r, n = coef(D, k, cols, allm); print(f"  {nm:8} {lab:14} {fmt(r)}")
    print("\n  εκτός δείγματος (fit 08-16 -> 17-26), κέρδος log-loss vs αγορά (αρνητικό = καλύτερο):")
    for k, nm in (("po", "άνοιγμα"), ("pc", "κλείσιμο")):
        for lab, cols in (("ηλικία μόνο", ["age"]), ("ηλικία+καριέρα", ["age", "sapm", "td15"]),
                          ("ηλικία+πρόσφατα 1y", ["age", "sapm_r1", "td15_r1"]), ("ηλικία+πρόσφατα 2y", ["age", "sapm_r2", "td15_r2"]),
                          ("ΧΩΡΙΣ ηλικία, πρόσφατα 1y", ["sapm_r1", "td15_r1"]), ("ΧΩΡΙΣ ηλικία, καριέρα", ["sapm", "td15"])):
            g, t, yrs = oos(D, k, cols); print(f"  {nm:8} {lab:26} {g:+.5f} (t {t:+.2f}) χρονιές {yrs}/10")

    print("\n=== Τ2. Καμπύλη ηλικίας ανά κατηγορία (πάνω-από-32 & κάτω-από-25, ανά 1 τυπ. απόκλιση) ===")
    for k, nm in (("po", "άνοιγμα"), ("pc", "κλείσιμο")):
        for cls in ("ελαφριές+γυναίκες", "μεσαίες 155-185", "βαριές 205+"):
            parts = []
            for per, pm in (("08-16", D.y <= 2016), ("17-26", D.y >= 2017)):
                r, n = coef(D, k, ["over32", "under25"], pm & (D.cls == cls))
                parts.append(f"{per} n={n}: {fmt(r)}")
            print(f"  {nm:8} {cls:18} " + " | ".join(parts))
    print("\n  εκτός δείγματος: γραμμική ηλικία vs καμπύλη")
    for k, nm in (("po", "άνοιγμα"), ("pc", "κλείσιμο")):
        for lab, cols in (("γραμμική", ["age"]), ("καμπύλη 32/25", ["over32", "under25"]), ("και τα δύο", ["age", "over32", "under25"])):
            g, t, yrs = oos(D, k, cols); print(f"  {nm:8} {lab:14} {g:+.5f} (t {t:+.2f}) χρονιές {yrs}/10")

    print("\n=== Τ3. Ηλικία vs φήμη (νίκες UFC, τίτλοι, main events — log, ανά 1 τυπ. απόκλιση) ===")
    for k, nm in (("po", "άνοιγμα"), ("pc", "κλείσιμο")):
        r, _ = coef(D, k, ["age"], allm); print(f"  {nm:8} μόνο ηλικία          {fmt(r)}")
        r, _ = coef(D, k, ["age", "wins_prev", "title_prev", "main_prev"], allm); print(f"  {nm:8} ηλικία + φήμη        {fmt(r)}")
        r, _ = coef(D, k, ["wins_prev", "title_prev", "main_prev"], allm); print(f"  {nm:8} μόνο φήμη            {fmt(r)}")
    # διάσημος vs άγνωστος μεγάλος (διαφορά ≥5 ετών), πόνταρισμα στον νεότερο
    old_is1 = o.a1 > o.a2
    gap = (o.a1 - o.a2).abs()
    fam = lambda s: (o[f"{s}_title_prev"] >= 1) | (o[f"{s}_main_prev"] >= 3)
    old_famous = np.where(old_is1, fam("f1"), fam("f2"))
    rows = []
    for lab, m in (("μεγάλος ΔΙΑΣΗΜΟΣ", old_famous), ("μεγάλος άγνωστος", ~old_famous)):
        mm = (gap >= 5) & pd.Series(m, index=o.index) & o.a1.notna() & o.a2.notna()
        t = side_rows(o, mm, ~old_is1)
        for per, pm in (("όλα", t.y > 0), ("08-16", t.y <= 2016), ("17-26", t.y >= 2017)):
            rows.append(dict(ομάδα=f"νεότερος (≥5 έτη) vs {lab}", περίοδος=per, **summ(t[pm].reset_index(drop=True))))
    T = pd.DataFrame(rows)
    pd.set_option("display.width", 250)
    print(T[["ομάδα", "περίοδος", "n", "νίκες", "p_άνοιγ", "t_άνοιγ", "ROI_άνοιγ%", "χρ+_άνοιγ", "p_κλείσ", "t_κλείσ",
             "ROI_κλείσ%", "χρ+_κλείσ"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
