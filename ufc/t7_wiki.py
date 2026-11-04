"""UFC τεστ 7: αντικαταστάτες με ΜΕΡΕΣ προετοιμασίας + αποτυχία ζυγίσματος (Wikipedia) vs αγορά.

Ομάδες ορισμένες ΑΠΟ ΠΡΙΝ:
  Αντικαταστάτης (πλευρά = ο αντικαταστάτης): μέρες ειδοποίησης ≤7 · 8-14 · 15-28 · >28 · άγνωστες
  Ζύγισμα (πλευρά = όποιος ΑΠΕΤΥΧΕ): μόνο κλείσιμο έχει νόημα (το ζύγισμα γίνεται την προηγούμενη μέρα)
Μέτρηση: νίκες vs πιθανότητα αγοράς χωρίς περιθώριο (t), ROI στην τιμή με περιθώριο, ανά περίοδο.
Έλεγχος: λογιστική logit(νίκη) = a·logit(αγορά) + c + b·σημάδι + g·διαφορά ηλικίας (τυχαίος προσανατολισμός).
Θέλει: ufc_fights_odds.csv, ufc_fighters.csv, wiki_replacements.csv, wiki_weightmiss.csv (UFC_DATA).
"""
import numpy as np
import pandas as pd

from t2_age_repl import DATA, block, load, side_rows
from t3_mechanisms import fit

lg = lambda p: np.log(p / (1 - p))


def flag(o, W):
    """+1 αν ο f1 είναι στη λίστα W (ίδια βραδιά ±1), −1 αν ο f2, 0 αλλιώς· και τιμή στήλης (π.χ. μέρες)."""
    d = pd.to_datetime(o.date)
    W = W.copy(); W["d"] = pd.to_datetime(W.date)
    s = np.zeros(len(o)); val = np.full(len(o), np.nan)
    idx = {}
    for i, r in W.iterrows():
        for k in (-1, 0, 1):
            idx[(r.fighter, (r.d + pd.Timedelta(days=k)).date())] = r.get("notice_days", np.nan)
    for j, (a, b, dd) in enumerate(zip(o.f1, o.f2, d.dt.date)):
        if (a, dd) in idx:
            s[j], val[j] = 1, idx[(a, dd)]
        elif (b, dd) in idx:
            s[j], val[j] = -1, idx[(b, dd)]
    return s, val


def control(o, s, name):
    rng = np.random.default_rng(7)
    flip = rng.random(len(o)) < 0.5
    m = o.a1.notna() & o.a2.notna()
    out = []
    for k in ("open", "close"):
        p = np.where(flip, 1 - o[f"f1_p_{k}"], o[f"f1_p_{k}"])
        w = np.where(flip, o.f1_result == "L", o.f1_result == "W").astype(float)
        sg = np.where(flip, -s, s)
        ag = np.where(flip, o.a2 - o.a1, o.a1 - o.a2)
        X = np.c_[lg(np.clip(p, .01, .99)), np.ones(len(o)), sg, np.nan_to_num(ag)][m.values]
        b, se = fit(X, w[m.values])
        out.append(f"{name} [{k}]: b={b[2]:+.3f} (t {b[2]/se[2]:+.1f}) · ηλικία t {b[3]/se[3]:+.1f} · n σημαδιών {int((sg[m.values] != 0).sum())}")
    return out


def main():
    o = load().reset_index(drop=True)
    R = pd.read_csv(DATA / "wiki_replacements.csv")
    W = pd.read_csv(DATA / "wiki_weightmiss.csv")
    rows = []
    s, nd = flag(o, R)
    print(f"αντικαταστάτες βρέθηκαν σε αγώνες με τιμές: {(s != 0).sum()} / {len(R)} της Wikipedia")
    grp = [("αντικ. όλοι", s != 0), ("αντικ. ≤7 μέρες", (s != 0) & (nd <= 7)),
           ("αντικ. 8-14", (s != 0) & (nd > 7) & (nd <= 14)), ("αντικ. 15-28", (s != 0) & (nd > 14) & (nd <= 28)),
           ("αντικ. >28", (s != 0) & (nd > 28)), ("αντικ. άγνωστες μέρες", (s != 0) & np.isnan(nd))]
    for name, m in grp:
        rows += block(name, side_rows(o, m, s == 1))
    # φαβορί/αουτσάιντερ αντικαταστάτης ≤14
    short = (s != 0) & (nd <= 14)
    pc_side = np.where(s == 1, o.f1_p_close, 1 - o.f1_p_close)
    rows += block("αντικ. ≤14 & φαβορί", side_rows(o, short & (pc_side >= .5), s == 1))
    rows += block("αντικ. ≤14 & αουτσάιντερ", side_rows(o, short & (pc_side < .5), s == 1))
    sw, _ = flag(o, W)
    print(f"αποτυχίες ζυγίσματος σε αγώνες με τιμές: {(sw != 0).sum()} / {len(W)}")
    rows += block("απέτυχε ζύγισμα", side_rows(o, sw != 0, sw == 1))
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    T = pd.DataFrame(rows)
    print(T.round(3).to_string(index=False))
    print()
    for line in control(o, np.where(short, s, 0), "αντικ. ≤14") + control(o, s, "αντικ. όλοι") + control(o, sw, "ζύγισμα"):
        print(line)


if __name__ == "__main__":
    main()
