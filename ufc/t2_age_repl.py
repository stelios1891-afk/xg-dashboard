"""UFC τεστ 2: ηλικία + αντικαταστάτες vs αγορά (άνοιγμα / κλείσιμο).

Ομάδες ορισμένες ΑΠΟ ΠΡΙΝ (εγκρίθηκαν 3/11):
  Ηλικία, πλευρά = ο ΝΕΟΤΕΡΟΣ:  μεγαλύτερος ≥35 · ≥38 · διαφορά ≥5 · ≥8 έτη
  Αντικαταστάτης Α (ακυρωμένος αγώνας ίδιας βραδιάς, 2020+): πλευρά = ο αντικαταστάτης
  Αργή κράτηση Β (early_days ≥30, 2007-23): πλευρά = το φαβορί του κλεισίματος
Μέτρηση: νίκες vs πιθανότητα αγοράς χωρίς περιθώριο (t), ROI τυφλού πονταρίσματος
στην τιμή ΜΕ περιθώριο (άνοιγμα = 1η τιμή BFO, κλείσιμο = μέσο εύρους), ανά περίοδο/χρονιά.
Θέλει: ufc_fights_odds.csv, ufc_fighters.csv, bfo_fights_repl.csv (UFC_DATA).
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(os.environ.get("UFC_DATA", Path(__file__).parent / "data"))


def load():
    o = pd.read_csv(DATA / "ufc_fights_odds.csv")
    o = o[o.f1_result.isin(["W", "L"]) & o.f1_p_close.notna() & o.f1_p_open.notna() & (o.date >= "2008")].copy()
    o["y"] = o.date.str[:4].astype(int)
    fi = pd.read_csv(DATA / "ufc_fighters.csv")
    dob = pd.to_datetime(fi[~fi.dup_name].set_index("fighter").dob)
    d = pd.to_datetime(o.date)
    o["a1"] = (d - o.f1.map(dob)).dt.days / 365.25
    o["a2"] = (d - o.f2.map(dob)).dt.days / 365.25
    r = pd.read_csv(DATA / "bfo_fights_repl.csv")[["matchup_id", "repl", "early_days", "f1_url", "f2_url", "f1"]]
    r = r.rename(columns={"f1": "bfo_f1"})
    o = o.merge(r, on="matchup_id", how="left")
    return o


def side_rows(o, mask, is_f1):
    """Μετατρέπει σε γραμμές «στόχου»: νίκη, p άνοιγμα/κλείσιμο, τιμές."""
    x = o[mask]
    s = is_f1[mask]
    w = np.where(s, x.f1_result == "W", x.f1_result == "L").astype(float)
    po = np.where(s, x.f1_p_open, 1 - x.f1_p_open)
    pc = np.where(s, x.f1_p_close, 1 - x.f1_p_close)
    do = np.where(s, x.f1_open_dec, x.f2_open_dec)
    dc = np.where(s, x.f1_close_dec, x.f2_close_dec)
    return pd.DataFrame(dict(y=x.y.values, w=w, po=po, pc=pc, do=do, dc=dc))


def summ(t):
    n = len(t)
    if n == 0:
        return {}
    out = dict(n=n, νίκες=t.w.mean())
    for k, p, dec in (("άνοιγ", "po", "do"), ("κλείσ", "pc", "dc")):
        diff = t.w - t[p]
        se = np.sqrt((t[p] * (1 - t[p])).sum()) / n
        prof = np.where(t.w == 1, t[dec] - 1, -1.0)
        out[f"p_{k}"] = t[p].mean()
        out[f"t_{k}"] = diff.mean() / se
        out[f"ROI_{k}%"] = 100 * prof.mean()
        out[f"SE_{k}"] = 100 * prof.std() / np.sqrt(n)
        yr = pd.Series(prof).groupby(t.y.values).mean()
        out[f"χρ+_{k}"] = f"{(yr > 0).sum()}/{len(yr)}"
    return out


def block(name, t):
    rows = []
    for per, m in (("όλα", t.y > 0), ("2008-16", t.y <= 2016), ("2017-26", t.y >= 2017)):
        s = summ(t[m])
        if s:
            rows.append(dict(ομάδα=name, περίοδος=per, **s))
    return rows


def main():
    o = load()
    rows = []
    has_age = o.a1.notna() & o.a2.notna()
    f1_younger = o.a1 < o.a2
    old = np.fmax(o.a1, o.a2)
    gap = (o.a1 - o.a2).abs()
    for name, m in (("μεγαλύτερος ≥35", has_age & (old >= 35) & (gap > 0)),
                    ("μεγαλύτερος ≥38", has_age & (old >= 38) & (gap > 0)),
                    ("διαφορά ≥5 ετών", has_age & (gap >= 5)),
                    ("διαφορά ≥8 ετών", has_age & (gap >= 8))):
        rows += block(f"νεότερος · {name}", side_rows(o, m, f1_younger))

    # Α: αντικαταστάτης (repl είναι σε όρους BFO f1/f2 -> μετάφραση στο ufcstats f1)
    # (αντιστοίχιση μέσω url από το ufc_build, όχι μέσω ονομάτων)
    ra = o.repl.isin(["f1", "f2"])
    repl_url = np.where(o.repl == "f1", o.f1_url, o.f2_url)
    f1_is_repl = pd.Series(repl_url == o.f1_bfo_url, index=o.index)
    rows += block("αντικαταστάτης (Α, 2020+)", side_rows(o, ra, f1_is_repl))

    # Β: αργή κράτηση -> φαβορί κλεισίματος
    late = o.early_days >= 30
    f1_fav = o.f1_p_close >= 0.5
    rows += block("φαβορί · αργή κράτηση (Β)", side_rows(o, late, f1_fav))
    rows += block("φαβορί · κανονική κράτηση (σύγκριση)", side_rows(o, o.early_days < 30, f1_fav))

    T = pd.DataFrame(rows)
    pd.set_option("display.width", 250)
    cols = ["ομάδα", "περίοδος", "n", "νίκες", "p_άνοιγ", "t_άνοιγ", "ROI_άνοιγ%", "SE_άνοιγ", "χρ+_άνοιγ",
            "p_κλείσ", "t_κλείσ", "ROI_κλείσ%", "SE_κλείσ", "χρ+_κλείσ"]
    print(T[cols].round(3).to_string(index=False))
    T.to_csv(DATA / "t2_age_repl.csv", index=False)


if __name__ == "__main__":
    main()
