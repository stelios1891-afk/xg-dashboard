"""UFC τεστ 8: Sherdog (ρεκόρ πριν το UFC, εθνικότητα) + επανέλεγχος αγώνων ≤14 μερών.

Ομάδες ορισμένες ΑΠΟ ΠΡΙΝ:
 Δ Πρωτοεμφανιζόμενος vs έμπειρος (πλευρά = ο πρωτοεμφανιζόμενος): όλοι · αήττητος (≥5 αγώνες) · ≥15 αγώνες · ≤6 αγώνες ·
   τελευταίος αγώνας σε DWCS · σε μεγάλη διοργάνωση · σερί ≥5 · νίκες με τελείωμα ≥70% · απουσία ≥12 μήνες
 Ε Έδρα (πλευρά = ο εντόπιος, ο αντίπαλος όχι): εκτός ΗΠΑ / ανά χώρα / ΗΠΑ
   Ταξίδι (πλευρά = αυτός που ΔΕΝ ταξίδεψε): αντίπαλος ≥6 ώρες διαφορά & δικός του ≤2 · ≥9 ώρες
   ΠΡΟΣΟΧΗ: εθνικότητα ≠ τόπος προπόνησης (πολλοί Βραζιλιάνοι ζουν στις ΗΠΑ).
 Σ Σύνολο αγώνων: διαφορά ln(αγώνες), χρόνια καριέρας, λεπτά καριέρας, % νικών, ήττες με KO καριέρας.
   Αδυνατίζει η ηλικία; (a·logit αγοράς + b·ηλικία + g·δείκτης). OOS fit 2008-16 / κρίση 2017-26.
 Ρ ≤14 μέρες: έξτρα κλίση αγοράς με έλεγχο ηλικία+sapm+td15, ανά περίοδο, δόση-απόκριση, και πρωτοεμφανιζόμενοι.
Κριτήρια: t ≥ 2, ίδιο πρόσημο 2008-16 & 2017-26, ROI (με περιθώριο) θετικό. ~35 συγκρίσεις -> ~2 τυχαία t≥2.
"""
import re
import sys

import numpy as np
import pandas as pd

import t3_mechanisms as t3
from t2_age_repl import DATA, block, side_rows
from t7_wiki import flag

pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
lg = lambda p: np.log(p / (1 - p))
BIG = r"^(Bellator|Professional Fighters League|PFL|ONE|Strikeforce|WEC|Pride|PRIDE|WSOF|World Series of Fighting|RIZIN|Rizin|KSW|ACA|M-1|Invicta|DREAM|Dream|CWFC|Cage Warriors|Affliction|Oktagon|Titan FC|LFA)"
TZ = {"United States": -6, "USA": -6, "Brazil": -3, "Canada": -5, "UK": 0, "Russia": 3, "Australia": 10, "Japan": 9, "Mexico": -6,
      "Poland": 1, "France": 1, "Sweden": 1, "Ireland": 0, "Peru": -5, "Germany": 1, "South Korea": 9, "New Zealand": 12,
      "Argentina": -3, "Kazakhstan": 5, "Netherlands": 1, "Georgia": 4, "Serbia": 1, "Ukraine": 2, "Italy": 1, "Spain": 1,
      "Venezuela": -4, "Denmark": 1, "Croatia": 1, "Finland": 2, "South Africa": 2, "Philippines": 8, "Czech Republic": 1,
      "Colombia": -5, "Romania": 2, "Kyrgyzstan": 6, "Belgium": 1, "Lithuania": 2, "China": 8, "Cuba": -5, "Turkey": 3,
      "Ecuador": -5, "Austria": 1, "Mongolia": 8, "Uzbekistan": 5, "Guam": 10, "Norway": 1, "Azerbaijan": 4, "Tajikistan": 5,
      "Morocco": 1, "Portugal": 0, "Armenia": 4, "Bulgaria": 2, "Hungary": 1, "Chile": -4, "Moldova": 2, "Nigeria": 1, "Iran": 3,
      "United Arab Emirates": 4, "Singapore": 8, "Saudi Arabia": 3, "Qatar": 3, "Uruguay": -3}
UK = {"England", "Scotland", "Wales", "Northern Ireland", "United Kingdom"}


def nat_norm(x):
    if pd.isna(x):
        return None
    return "UK" if x in UK else ("USA" if x == "United States" else x)


def career_features(o):
    S = pd.read_csv(DATA / "sherdog_fights.csv")
    S["date"] = pd.to_datetime(S.date.str[:10], errors="coerce")
    S = S.dropna(subset=["date"]).sort_values(["fighter", "date"])
    S["ev0"] = S.event.fillna("")
    S["fin"] = S.method.fillna("").str.contains(r"KO|TKO|Submission", regex=True)
    S["ko"] = S.method.fillna("").str.contains(r"KO", regex=True)
    rnd = pd.to_numeric(S.rnd, errors="coerce").fillna(1)
    tt = S.time.fillna("").str.extract(r"(\d+):(\d+)").astype(float)
    S["mins"] = (rnd - 1) * 5 + tt[0].fillna(5) + tt[1].fillna(0) / 60
    G = {k: v for k, v in S.groupby("fighter")}
    rows = {}
    for side in ("f1", "f2"):
        for fid, f, d in zip(o.fight_url, o[side], pd.to_datetime(o.date)):
            g = G.get(f)
            if g is None:
                continue
            p = g[g.date < d - pd.Timedelta(days=1)]
            if not len(p):
                rows[(fid, f)] = dict(pro_n=0, pro_w=0, pro_l=0, fin_w=0, ko_l=0, streak=0, years=0.0, mins=0.0, lay=np.nan, last_ev="")
                continue
            res = p.result.values
            st = 0
            for r in res[::-1]:
                if r != "win":
                    break
                st += 1
            w = res == "win"; lo = res == "loss"
            rows[(fid, f)] = dict(pro_n=len(p), pro_w=int(w.sum()), pro_l=int(lo.sum()), fin_w=int((w & p.fin.values).sum()),
                                  ko_l=int((lo & p.ko.values).sum()), streak=st, years=(d - p.date.iloc[0]).days / 365.25,
                                  mins=float(p.mins.sum()), lay=(d - p.date.iloc[-1]).days, last_ev=p.ev0.iloc[-1])
    return rows


def main():
    o = t3.load()
    fi = pd.read_csv(DATA / "ufc_fighters.csv")
    dob = pd.to_datetime(fi[~fi.dup_name].set_index("fighter").dob)
    d = pd.to_datetime(o.date)
    o["a1"] = (d - o.f1.map(dob)).dt.days / 365.25
    o["a2"] = (d - o.f2.map(dob)).dt.days / 365.25
    C = career_features(o)
    for side in ("f1", "f2"):
        for c in ("pro_n", "pro_w", "pro_l", "fin_w", "ko_l", "streak", "years", "mins", "lay", "last_ev"):
            o[f"{side}_{c}"] = [C.get((u, f), {}).get(c, np.nan if c != "last_ev" else "") for u, f in zip(o.fight_url, o[side])]

    print("== ΕΛΕΓΧΟΣ γνωστών (ρεκόρ ΠΡΙΝ το ντεμπούτο UFC) ==")
    for f in ("Conor McGregor", "Khabib Nurmagomedov", "Israel Adesanya", "Ilia Topuria", "Jon Jones"):
        for s in ("f1", "f2"):
            x = o[(o[s] == f) & (o[f"{s}_n_prev"] == 0)]
            if len(x):
                r = x.iloc[0]
                print(f"  {f} {r.date}: {r[f'{s}_pro_w']}-{r[f'{s}_pro_l']} · σερί {r[f'{s}_streak']} · τελευταίος: {r[f'{s}_last_ev']}")
    rows = []

    # Δ πρωτοεμφανιζόμενοι
    has1 = o.f1_pro_n.notna() & (o.f1_n_prev == 0) & (o.f2_n_prev >= 1)
    has2 = o.f2_pro_n.notna() & (o.f2_n_prev == 0) & (o.f1_n_prev >= 1)
    any_d = has1 | has2
    print(f"\nαγώνες πρωτοεμφ. vs έμπειρος με ρεκόρ: {any_d.sum()}")
    get = lambda c: np.where(has1, o[f"f1_{c}"], o[f"f2_{c}"])
    pn, pw, pl, fw, st, ly = (get(c) for c in ("pro_n", "pro_w", "pro_l", "fin_w", "streak", "lay"))
    ev = pd.Series(np.where(has1, o.f1_last_ev, o.f2_last_ev), index=o.index).fillna("")
    ly = ly.astype(float)
    grp = [("Δ όλοι", np.ones(len(o), bool)), ("Δ αήττητος ≥5", (pl.astype(float) == 0) & (pn.astype(float) >= 5)),
           ("Δ ≥15 αγώνες", pn.astype(float) >= 15), ("Δ ≤6 αγώνες", pn.astype(float) <= 6),
           ("Δ DWCS", ev.str.contains("Contender Series").values), ("Δ μεγάλη διοργ.", ev.str.contains(BIG, regex=True).values),
           ("Δ σερί ≥5", st.astype(float) >= 5), ("Δ τελειώματα ≥70%", (fw.astype(float) / np.maximum(pw.astype(float), 1) >= .7) & (pw.astype(float) >= 3)),
           ("Δ απουσία ≥12μ", ly >= 365)]
    for name, m in grp:
        rows += block(name, side_rows(o, any_d.values & m, has1.values))
    print(pd.DataFrame(rows).round(3).to_string(index=False))

    # Ε έδρα + ταξίδι
    rows = []
    A = pd.read_csv(DATA / "sherdog_fighters.csv").drop_duplicates("fighter").set_index("fighter")
    nat = A.nationality.map(nat_norm)
    cty = o.location.fillna("").str.split(",").str[-1].str.strip().replace({"United Kingdom": "UK"})
    n1, n2 = o.f1.map(nat), o.f2.map(nat)
    h1 = (n1 == cty) & n2.notna() & (n2 != cty)
    h2 = (n2 == cty) & n1.notna() & (n1 != cty)
    home = (h1 | h2).values
    print(f"\nεθνικότητα γνωστή και στους 2: {(n1.notna() & n2.notna()).sum()}/{len(o)} · εντόπιος vs ξένος: {home.sum()}")
    us = (cty == "USA").values
    rows += block("Ε εντόπιος εκτός ΗΠΑ", side_rows(o, home & ~us, h1.values))
    rows += block("Ε Αμερικανός στις ΗΠΑ", side_rows(o, home & us, h1.values))
    for c in ("Brazil", "Canada", "UK", "Mexico", "Australia"):
        rows += block(f"Ε εντόπιος {c}", side_rows(o, home & (cty == c).values, h1.values))
    t1, t2, te = n1.map(TZ), n2.map(TZ), cty.map(TZ)
    wrap = lambda x: np.minimum((x - te).abs(), 24 - (x - te).abs())
    j1, j2 = wrap(t1), wrap(t2)
    print(f"ταξίδι: γνωστή ζώνη και στους 2 + χώρα αγώνα: {(j1.notna() & j2.notna()).sum()}")
    for gap in (6, 9):
        a = (j2 >= gap) & (j1 <= 2); b = (j1 >= gap) & (j2 <= 2)
        rows += block(f"Τ αντίπαλος ταξίδεψε ≥{gap}ω", side_rows(o, (a | b).values, a.values))
        rows += block(f"Τ ≥{gap}ω, αγώνας στις ΗΠΑ", side_rows(o, (a | b).values & us, a.values))
        rows += block(f"Τ ≥{gap}ω, αγώνας εκτός ΗΠΑ", side_rows(o, (a | b).values & ~us, a.values))
    print(pd.DataFrame(rows).round(3).to_string(index=False))

    # Σ σύνολο αγώνων vs ηλικία
    rng = np.random.default_rng(7)
    flip = rng.random(len(o)) < 0.5
    sg = np.where(flip, -1.0, 1.0)
    w = np.where(flip, o.f1_result == "L", o.f1_result == "W").astype(float)
    Dd = {}
    Dd["age"] = sg * (o.a1 - o.a2)
    Dd["lnpro"] = sg * (np.log1p(o.f1_pro_n) - np.log1p(o.f2_pro_n))
    Dd["years"] = sg * (o.f1_years - o.f2_years)
    Dd["lnmins"] = sg * (np.log1p(o.f1_mins) - np.log1p(o.f2_mins))
    Dd["winpct"] = sg * (o.f1_pro_w / o.f1_pro_n.clip(lower=1) - o.f2_pro_w / o.f2_pro_n.clip(lower=1))
    Dd["ko_l"] = sg * (o.f1_ko_l - o.f2_ko_l)
    Dd["sapm"] = sg * (o.f1_sapm - o.f2_sapm)
    Dd["td15"] = sg * (o.f1_td15 - o.f2_td15)
    D = pd.DataFrame(Dd)
    D["pk_open"] = lg(np.clip(np.where(flip, 1 - o.f1_p_open, o.f1_p_open), .01, .99))
    D["pk_close"] = lg(np.clip(np.where(flip, 1 - o.f1_p_close, o.f1_p_close), .01, .99))
    D["w"] = w; D["y"] = o.y.values
    ok = D[list(Dd)].notna().all(axis=1) & (o.f1_pro_n > 0) & (o.f2_pro_n > 0)
    D = D[ok].reset_index(drop=True)
    print(f"\n== Σ: σύνολο αγώνων vs ηλικία (n={len(D)}) · b ανά τυπική απόκλιση της διαφοράς ==")
    Z = {c: D[c] / D[c].std() for c in Dd}
    res = []
    for k in ("open", "close"):
        base = [D[f"pk_{k}"].values, np.ones(len(D))]
        X = np.c_[base[0], base[1], Z["age"]]; b, se = t3.fit(X, D.w.values)
        res.append(dict(αγορά=k, δείκτης="σκέτη ηλικία", b_age=b[2], t_age=b[2] / se[2]))
        for c in ("lnpro", "years", "lnmins", "winpct", "ko_l"):
            X = np.c_[base[0], base[1], Z[c]]; b0, se0 = t3.fit(X, D.w.values)
            X = np.c_[base[0], base[1], Z["age"], Z[c]]; b, se = t3.fit(X, D.w.values)
            res.append(dict(αγορά=k, δείκτης=c, b_μόνος=b0[2], t_μόνος=b0[2] / se0[2], b_age=b[2], t_age=b[2] / se[2], b_δείκτη=b[3], t_δείκτη=b[3] / se[3]))
    print(pd.DataFrame(res).round(3).to_string(index=False))
    tr, te_ = D.y <= 2016, D.y >= 2017
    res = []
    for k in ("open", "close"):
        def oos(cols):
            X = np.c_[D[f"pk_{k}"].values, np.ones(len(D))] + 0
            for c in cols:
                X = np.c_[X, D[c].values]
            b, _ = t3.fit(X[tr.values], D.w.values[tr.values])
            return t3.ll(t3.sig(X[te_.values] @ b), D.w.values[te_.values])
        res.append(dict(αγορά=k, μόνο_αγορά=oos([]), ηλικία=oos(["age"]), ηλ_sapm_td=oos(["age", "sapm", "td15"]),
                        συν_lnpro=oos(["age", "sapm", "td15", "lnpro"]), συν_years=oos(["age", "sapm", "td15", "years"]),
                        συν_mins=oos(["age", "sapm", "td15", "lnmins"]), συν_winpct=oos(["age", "sapm", "td15", "winpct"]),
                        συν_ko=oos(["age", "sapm", "td15", "ko_l"])))
    print("log-loss 2017-26 (fit 2008-16):"); print(pd.DataFrame(res).round(4).to_string(index=False))
    # κανόνας ηλικίας ≥8 χρόνια, σπάσιμο: ο μεγάλος έχει πολλά ή λίγα χιλιόμετρα
    rows = []
    f1y = o.a1 < o.a2
    gap = (o.a1 - o.a2).abs() >= 8
    oldmins = np.where(f1y, o.f2_mins, o.f1_mins).astype(float)
    med = np.nanmedian(oldmins[gap.values])
    rows += block(f"νεότερος ≥8χρ · ο μεγάλος >{med:.0f} λεπτά", side_rows(o, gap.values & (oldmins > med), f1y.values))
    rows += block(f"νεότερος ≥8χρ · ο μεγάλος ≤{med:.0f} λεπτά", side_rows(o, gap.values & (oldmins <= med), f1y.values))
    print(pd.DataFrame(rows).round(3).to_string(index=False))

    # Ρ ≤14 μέρες
    print("\n== Ρ: αγώνες αντικαταστάτη: έξτρα κλίση αγοράς (το φαβορί κερδίζει περισσότερο απ' όσο λέει η τιμή) ==")
    R = pd.read_csv(DATA / "wiki_replacements.csv")
    s, nd = flag(o, R)
    isrepl = s != 0
    D2 = pd.DataFrame({"o": lg(np.clip(np.where(flip, 1 - o.f1_p_open, o.f1_p_open), .01, .99)),
                       "c": lg(np.clip(np.where(flip, 1 - o.f1_p_close, o.f1_p_close), .01, .99)),
                       "age": sg * (o.a1 - o.a2), "sapm": sg * (o.f1_sapm - o.f2_sapm), "td": sg * (o.f1_td15 - o.f2_td15),
                       "w": w, "y": o.y.values, "deb": ((o.f1_n_prev == 0) | (o.f2_n_prev == 0)).values})
    ok2 = D2.notna().all(axis=1).values
    res = []
    for k in ("o", "c"):
        for lbl, m in (("≤7", isrepl & (nd <= 7)), ("8-14", isrepl & (nd > 7) & (nd <= 14)), ("≤14", isrepl & (nd <= 14)),
                       ("15-28", isrepl & (nd > 14) & (nd <= 28)), (">28", isrepl & (nd > 28))):
            for per, pm in (("όλα", np.ones(len(o), bool)), ("2008-16", o.y.values <= 2016), ("2017-26", o.y.values >= 2017)):
                u = ok2 & pm
                X = np.c_[D2[k], np.ones(len(o)), D2.age, D2.sapm, D2.td, D2[k] * m, D2[k] * D2.deb][u]
                b, se = t3.fit(X, D2.w.values[u])
                res.append(dict(αγορά="άνοιγμα" if k == "o" else "κλείσιμο", ομάδα=lbl, περίοδος=per, n=int((m & u).sum()),
                                κλίση_βάση=b[0], έξτρα=b[5], t=b[5] / se[5], έξτρα_πρωτοεμφ=b[6], t_πρωτ=b[6] / se[6]))
    print(pd.DataFrame(res).round(3).to_string(index=False))
    fav = lambda k: o[f"f1_p_{k}"] >= .5
    rows = []
    short = isrepl & (nd <= 14)
    rows += block("φαβορί ανοίγματος, αγώνας ≤14", side_rows(o, short, fav("open").values))
    rows += block("φαβορί ανοίγματος, όλοι οι άλλοι", side_rows(o, ~short, fav("open").values))
    print(pd.DataFrame(rows).round(3).to_string(index=False))


if __name__ == "__main__":
    sys.exit(main())
