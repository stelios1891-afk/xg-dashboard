"""UFC τεστ 6: ΓΥΡΟΙ / ΚΡΙΤΕΣ (2021+) + ΣΤΙΛ (3/11, Στελιος «Γύροι + στιλ»).

Αγορές (BFO, τελευταία τιμή ανά βιβλίο = κλείσιμο, μόνο FanDuel/BetRivers/Unibet/BetWay/DraftKings/BetMGM/Caesars):
  DEC  = «πάει στους κριτές» ναι/όχι (prop 1) · O25 = Over/Under 2.5 γύρων (prop 33) · O15 = Over/Under 1.5 (prop 32)
  Πιθανότητα αγοράς = διάμεσος των βιβλίων (χωρίς περιθώριο ανά βιβλίο). Τιμή πονταρίσματος = διάμεση τιμή βιβλίων (με περιθώριο).
  Έκβαση: DEC = απόφαση κριτών · Over 2.5 = πέρασε το 2:30 του 3ου γύρου · Over 1.5 = πέρασε το 2:30 του 2ου. NC εκτός.
Μεταβλητές (μόνο προηγούμενοι αγώνες UFC, συρρίκνωση): ποσοστό τελειωμάτων υπέρ/κατά, αποφάσεων, νοκ-ντάουν
  που ρίχνει/δέχεται, χτυπήματα, takedowns, απόπειρες υποταγής, κατηγορία (λίβρες), γυναίκες, ηλικία.
Κρίση: έλεγχος τιμής (a·logit αγοράς) · εκτός δείγματος = άφησε-μία-χρονιά-έξω (2021…2026) ·
  ROI όταν μοντέλο − αγορά ≥ 5 μονάδες στη διάμεση τιμή.
ΣΤΙΛ (ορισμός από πριν): μαχητές με ≥3 αγώνες UFC· παλαιστής = πάνω 25% σε takedowns/15′, striker = κάτω 25%.
  Νικητής: παλαιστής vs striker (2008-26, άνοιγμα/κλείσιμο). Κριτές: ζεύγη στιλ vs αγορά (2021+).
"""
import html, os, sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import t3_mechanisms as t3  # noqa: E402
from t2_age_repl import side_rows, summ  # noqa: E402

DATA = Path(os.environ.get("UFC_DATA", Path(__file__).parent / "data"))
BOOKS = {"FanDuel", "BetRivers", "Unibet", "BetWay", "DraftKings", "BetMGM", "Caesars"}
MK = {"DEC": (1, "Fight goes to decision", "Fight doesn't go to decision"),
      "O25": (33, "Over 2½ rounds", "Under 2½ rounds"), "O15": (32, "Over 1½ rounds", "Under 1½ rounds")}
dec_ = lambda a: np.where(a > 0, 1 + a / 100, 1 + 100 / np.abs(a))


def props():
    b = pd.read_csv(DATA / "bfo_book_odds.csv")
    b = b[b.book.isin(BOOKS) & b.prop_type.notna()].copy()
    b["label"] = b.label.map(html.unescape)
    out = []
    for name, (pt, yes, no) in MK.items():
        x = b[b.prop_type == pt]
        y = x[x.label == yes].groupby(["matchup_id", "book"]).odds.last()
        n = x[x.label == no].groupby(["matchup_id", "book"]).odds.last()
        j = pd.concat([y.rename("y"), n.rename("n")], axis=1).dropna()
        j["dy"], j["dn"] = dec_(j.y), dec_(j.n)
        j["p"] = (1 / j.dy) / (1 / j.dy + 1 / j.dn)
        j["vig"] = 1 / j.dy + 1 / j.dn - 1
        g = j.groupby("matchup_id").agg(p=("p", "median"), dy=("dy", "median"), dn=("dn", "median"),
                                         dy_best=("dy", "max"), dn_best=("dn", "max"), vig=("vig", "median"), books=("p", "size"))
        g["mk"] = name
        out.append(g.reset_index())
    return pd.concat(out)


def finish_features():
    F = pd.read_csv(DATA / "ufc_fights.csv")
    F["d"] = pd.to_datetime(F.date)
    rows = []
    for me, op in (("f1", "f2"), ("f2", "f1")):
        won = F.f1_result == ("W" if me == "f1" else "L")
        lost = F.f1_result == ("L" if me == "f1" else "W")
        rows.append(pd.DataFrame({
            "fid": F.index, "d": F.d, "fighter": F[me],
            "fin_w": (won & F.method_grp.isin(["KO", "SUB"])).astype(float),
            "fin_l": (lost & F.method_grp.isin(["KO", "SUB"])).astype(float),
            "dec": (F.method_grp == "DEC").astype(float),
            "kd": F[f"{me}_kd"].fillna(0), "kd_ab": F[f"{op}_kd"].fillna(0), "sub": F[f"{me}_subatt"].fillna(0),
            "t": F.fight_time_s.fillna(0)}))
    L = pd.concat(rows).sort_values(["d", "fid"], kind="stable").reset_index(drop=True)
    g = L.groupby("fighter", sort=False)
    prev = lambda c: g[c].cumsum() - L[c]
    n = g.cumcount()
    K = 3.0
    for c in ("fin_w", "fin_l", "dec"):
        L[c + "_r"] = (prev(c) + L[c].mean() * K) / (n + K)
    T = prev("t")
    for c in ("kd", "kd_ab", "sub"):
        mu = L[c].sum() / L.t.sum()
        L[c + "15"] = 900 * (prev(c) + mu * 900) / (T + 900)
    feats = ["fin_w_r", "fin_l_r", "dec_r", "kd15", "kd_ab15", "sub15"]
    E = F[["fight_url"]].copy()
    for me in ("f1", "f2"):
        sub = L.merge(F[[me]].rename(columns={me: "fighter"}).reset_index().rename(columns={"index": "fid"}), on=["fid", "fighter"])
        E = E.join(sub.drop_duplicates("fid").set_index("fid")[feats].add_prefix(me + "_"))
    return E


def build():
    o = pd.read_csv(DATA / "ufc_fights_odds.csv")
    x = pd.read_csv(DATA / "ufc_features.csv").drop(columns=["date", "event", "f1", "f2"])
    o = o.merge(x, on="fight_url").merge(finish_features(), on="fight_url")
    o = o[o.f1_result.isin(["W", "L", "D"])].copy()
    o["y"] = o.date.str[:4].astype(int)
    fi = pd.read_csv(DATA / "ufc_fighters.csv"); dob = pd.to_datetime(fi[~fi.dup_name].set_index("fighter").dob)
    d = pd.to_datetime(o.date)
    o["a1"] = (d - o.f1.map(dob)).dt.days / 365.25; o["a2"] = (d - o.f2.map(dob)).dt.days / 365.25
    from t5_age_deep import LBS
    o["lbs"] = o.weightclass.map(lambda s: next((v for k, v in sorted(LBS.items(), key=lambda kv: -len(kv[0])) if k in str(s)), np.nan))
    o["out_DEC"] = (o.method_grp == "DEC").astype(float)
    o["out_O25"] = ((o.fight_time_s > 750) | (o.method_grp == "DEC")).astype(float)
    o["out_O15"] = ((o.fight_time_s > 450) | (o.method_grp == "DEC")).astype(float)
    # συμμετρικές μεταβλητές αγώνα (άθροισμα των δύο)
    S = {}
    for c in ("fin_w_r", "fin_l_r", "dec_r", "kd15", "kd_ab15", "sub15", "slpm", "sapm", "td15"):
        S[c] = o[f"f1_{c}"] + o[f"f2_{c}"]
    S["finish_cross"] = o.f1_fin_w_r * o.f2_fin_l_r + o.f2_fin_w_r * o.f1_fin_l_r  # «ρίχνει» × «πέφτει»
    S["lbs"] = np.log(o.lbs)
    S["women"] = o.women.astype(float)
    S["age_max"] = np.fmax(o.a1, o.a2)
    for k, v in S.items():
        o["S_" + k] = v
    return o


SFEATS = ["S_fin_w_r", "S_fin_l_r", "S_dec_r", "S_finish_cross", "S_kd15", "S_kd_ab15", "S_sub15", "S_slpm", "S_sapm",
          "S_td15", "S_lbs", "S_women", "S_age_max"]
PICKED = ["S_dec_r", "S_finish_cross", "S_kd15", "S_lbs", "S_women"]  # μικρό μοντέλο (ορισμένο από πριν)


def rounds_tests(o, P):
    print("=== Α. Αγορά γύρων/κριτών: πόσο σωστή είναι μόνη της; (κλείσιμο, διάμεσος βιβλίων) ===")
    res = {}
    for mk in MK:
        p = P[P.mk == mk].merge(o, on="matchup_id")
        p = p[p.sched_rounds == 3] if mk != "DEC" else p
        w = p[f"out_{mk}"].values
        bins = pd.cut(p.p, [0, .3, .4, .5, .6, .7, 1])
        cal = p.assign(w=w, b=bins).groupby("b", observed=True).agg(n=("w", "size"), p=("p", "mean"), έγινε=("w", "mean"))
        print(f"\n{mk}: n={len(p)} · αγορά λέει {p.p.mean():.3f} · έγινε {w.mean():.3f} · περιθώριο {p.vig.mean():.3f} · βιβλία/αγώνα {p.books.median():.0f}")
        print(cal.round(3).to_string())
        res[mk] = p.reset_index(drop=True)
    print("\n=== Β. Κάθε μεταβλητή μόνη με έλεγχο τιμής (b ανά 1 τυπ. απόκλιση, όλα τα χρόνια 2021+) ===")
    for mk, p in res.items():
        w = p[f"out_{mk}"].values
        parts = []
        for c in SFEATS:
            m = p[c].notna().values
            z = (p[c] - p[c][m].mean()) / p[c][m].std()
            b, se = t3.fit(np.c_[t3.lg(p.p.clip(.02, .98))[m], np.ones(m.sum()), z[m]], w[m])
            parts.append(f"{c[2:]} {b[2]:+.2f}({b[2] / se[2]:+.1f})")
        print(f"{mk}: " + " · ".join(parts))
    print("\n=== Γ. Εκτός δείγματος (άφησε-μία-χρονιά-έξω), μικρό μοντέλο " + ",".join(c[2:] for c in PICKED) + " ===")
    for mk, p in res.items():
        p = p.dropna(subset=PICKED).reset_index(drop=True)
        w = p[f"out_{mk}"].values
        lgp = t3.lg(p.p.clip(.02, .98)).values
        gains, picks = [], []
        for yy in sorted(p.y.unique()):
            tr, te = (p.y != yy).values, (p.y == yy).values
            Z = (p[PICKED] - p[PICKED][tr].mean()) / p[PICKED][tr].std()
            X0 = np.c_[lgp, np.ones(len(p))]; X = np.c_[X0, Z.values]
            b0, _ = t3.fit(X0[tr], w[tr]); b, _ = t3.fit(X[tr], w[tr])
            q0, q = t3.sig(X0[te] @ b0), t3.sig(X[te] @ b)
            ww = w[te]
            dl = -(ww * np.log(q) + (1 - ww) * np.log(1 - q)) + (ww * np.log(q0) + (1 - ww) * np.log(1 - q0))
            gains.append((yy, dl.mean(), len(dl)))
            pk = p.p.values[te]
            dy, dn = p.dy.values[te], p.dn.values[te]
            yes = q - pk >= .05; no = (1 - q) - (1 - pk) >= .05
            for sel, side, price in ((yes, 1, dy), (no, 0, dn)):
                for i in np.where(sel)[0]:
                    picks.append(dict(y=yy, side="ΝΑΙ/Over" if side else "ΟΧΙ/Under",
                                      prof=(price[i] - 1) if ww[i] == side else -1.0))
        G = pd.DataFrame(gains, columns=["y", "gain", "n"])
        PK = pd.DataFrame(picks)
        tot = np.average(G.gain, weights=G.n)
        print(f"{mk}: κέρδος log-loss {tot:+.5f} · χρονιές καλύτερο {(G.gain < 0).sum()}/{len(G)} · "
              f"πονταρίσματα {len(PK)} ROI {100 * PK.prof.mean():+.1f}% ±{100 * PK.prof.std() / np.sqrt(max(len(PK), 1)):.1f}"
              if len(PK) else f"{mk}: κέρδος {tot:+.5f}")
        if len(PK):
            print("   ανά πλευρά:", PK.groupby("side").prof.agg(["size", "mean"]).assign(mean=lambda s: (100 * s["mean"]).round(1)).to_dict("index"),
                  "· ανά χρονιά ROI%:", (100 * PK.groupby("y").prof.mean()).round(1).to_dict())
    return res


def style_tests(o, res):
    print("\n=== Δ. ΣΤΙΛ ===")
    exp = (o.f1_n_prev >= 3) & (o.f2_n_prev >= 3)
    td = pd.concat([o.f1_td15[o.f1_n_prev >= 3], o.f2_td15[o.f2_n_prev >= 3]])
    lo, hi = td.quantile(.25), td.quantile(.75)
    print(f"όρια: striker td15 ≤ {lo:.2f} · παλαιστής td15 ≥ {hi:.2f} (takedowns ανά 15′)")
    sty = lambda s: np.where(o[f"{s}_td15"] >= hi, "Π", np.where(o[f"{s}_td15"] <= lo, "S", "-"))
    o["st1"], o["st2"] = sty("f1"), sty("f2")
    m = exp & o.f1_p_close.notna() & o.f1_result.isin(["W", "L"]) & (o.y >= 2008)
    oo = o[m].copy()
    gs = ((oo.st1 == "Π") & (oo.st2 == "S")) | ((oo.st1 == "S") & (oo.st2 == "Π"))
    t = side_rows(oo, gs, oo.st1 == "Π")
    rows = []
    for per, pm in (("όλα", t.y > 0), ("08-16", t.y <= 2016), ("17-26", t.y >= 2017)):
        rows.append(dict(ομάδα="παλαιστής vs striker → παλαιστής", περίοδος=per, **summ(t[pm].reset_index(drop=True))))
    # και ανά «ποιος είναι φαβορί»
    for lab, fm in (("παλαιστής φαβορί", None), ("παλαιστής αουτσάιντερ", None)):
        pass
    T = pd.DataFrame(rows)
    pd.set_option("display.width", 250)
    print(T[["ομάδα", "περίοδος", "n", "νίκες", "p_άνοιγ", "t_άνοιγ", "ROI_άνοιγ%", "χρ+_άνοιγ", "p_κλείσ", "t_κλείσ",
             "ROI_κλείσ%", "χρ+_κλείσ"]].round(3).to_string(index=False))
    # κριτές ανά ζεύγος στιλ (2021+)
    p = res["DEC"].merge(o[["matchup_id", "st1", "st2"]], on="matchup_id")
    p = p[(p.f1_n_prev >= 3) & (p.f2_n_prev >= 3)]
    pair = np.where((p.st1 == "Π") & (p.st2 == "Π"), "Π-Π", np.where((p.st1 == "S") & (p.st2 == "S"), "S-S",
                    np.where(((p.st1 == "Π") & (p.st2 == "S")) | ((p.st1 == "S") & (p.st2 == "Π")), "Π-S", "λοιπά")))
    p = p.assign(pair=pair, w=p.out_DEC)
    print("\nΚριτές ανά ζεύγος στιλ (2021+, κλείσιμο): αγορά λέει vs έγινε")
    for k, g in p.groupby("pair"):
        se = np.sqrt((g.p * (1 - g.p)).sum()) / len(g)
        roi_y = np.where(g.w == 1, g.dy - 1, -1).mean(); roi_n = np.where(g.w == 0, g.dn - 1, -1).mean()
        print(f"  {k:6} n={len(g):4} αγορά {g.p.mean():.3f} έγινε {g.w.mean():.3f} t {(g.w - g.p).mean() / se:+.2f} · ROI ΝΑΙ {100 * roi_y:+.1f}% / ΟΧΙ {100 * roi_n:+.1f}%")


def main():
    o = build()
    P = props()
    res = rounds_tests(o, P)
    style_tests(o, res)


if __name__ == "__main__":
    main()
