"""UFC: καθαρός πίνακας αγώνων (ufcstats) + ένωση με αποδόσεις BestFightOdds.

Πηγές (στο UFC_DATA, default ufc/data):
  raw/ufc_*.csv          ufcstats.com μέσω github.com/Greco1899/scrape_ufc_stats (ενημέρωση εβδομαδιαία)
                         (το ufcstats.com έχει πλέον browser-check -> δεν το χτυπάμε απευθείας)
  bfo_*.csv              από ufc/bfo_fetch.py

Έξοδος:
  ufc_fighters.csv       μαχητής: ύψος/άνοιγμα (cm), στάση, ημ. γέννησης
  ufc_fights.csv         ένας αγώνας ανά γραμμή, f1/f2: αποτέλεσμα, τρόπος, γύρος, χρόνος, σύνολα στατιστικών
  ufc_fights_odds.csv    ufc_fights + άνοιγμα/κλείσιμο ανά μαχητή (δεκαδικές) + χωρίς-περιθώριο πιθανότητες
  ufc_unmatched_bfo.csv  αγώνες BFO που δεν βρέθηκαν (για έλεγχο)

Χρήση: python ufc/ufc_build.py [--download]
"""
import argparse, os, re, unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import requests

DATA = Path(os.environ.get("UFC_DATA", Path(__file__).parent / "data"))
RAW = DATA / "raw"
GH = "https://raw.githubusercontent.com/Greco1899/scrape_ufc_stats/main/"
FILES = ["ufc_event_details", "ufc_fight_details", "ufc_fight_results", "ufc_fight_stats",
         "ufc_fighter_details", "ufc_fighter_tott"]


def download():
    RAW.mkdir(parents=True, exist_ok=True)
    for f in FILES:
        r = requests.get(GH + f + ".csv", timeout=60)
        r.raise_for_status()
        (RAW / f"{f}.csv").write_bytes(r.content)
        print(f"  {f}.csv {len(r.content) // 1024} KB")


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z ]", "", s.replace("-", " ")).split()


def key(s):
    return " ".join(norm(s))


def of(s):  # "12 of 30" -> (12, 30)
    m = re.match(r"\s*(\d+)\s+of\s+(\d+)", str(s))
    return (int(m.group(1)), int(m.group(2))) if m else (np.nan, np.nan)


def mmss(s):
    m = re.match(r"\s*(\d+):(\d+)", str(s))
    return int(m.group(1)) * 60 + int(m.group(2)) if m else np.nan


def inches(s):  # 5' 11"  /  72"
    s = str(s)
    m = re.match(r"\s*(\d+)'\s*(\d+)", s)
    if m:
        return int(m.group(1)) * 12 + int(m.group(2))
    m = re.match(r"\s*(\d+)\"", s)
    return int(m.group(1)) if m else np.nan


def build_fighters():
    t = pd.read_csv(RAW / "ufc_fighter_tott.csv")
    f = pd.DataFrame({
        "fighter": t.FIGHTER.str.strip(), "url": t.URL,
        "height_cm": t.HEIGHT.map(inches) * 2.54, "reach_cm": t.REACH.map(inches) * 2.54,
        "stance": t.STANCE, "dob": pd.to_datetime(t.DOB, errors="coerce", format="%b %d, %Y").dt.date,
    })
    f["name_key"] = f.fighter.map(key)
    f["dup_name"] = f.duplicated("name_key", keep=False)
    return f


def build_fights():
    ev = pd.read_csv(RAW / "ufc_event_details.csv")
    ev["EVENT"] = ev.EVENT.str.strip()
    ev["date"] = pd.to_datetime(ev.DATE, format="%B %d, %Y").dt.date
    r = pd.read_csv(RAW / "ufc_fight_results.csv")
    for c in ["EVENT", "BOUT", "OUTCOME", "WEIGHTCLASS", "METHOD", "TIME FORMAT", "REFEREE", "DETAILS"]:
        r[c] = r[c].astype(str).str.strip()
    sp = r.BOUT.str.split(r"\s+vs\.\s+", n=1, expand=True, regex=True)
    out = pd.DataFrame({
        "fight_url": r.URL, "event": r.EVENT, "f1": sp[0].str.strip(), "f2": sp[1].str.strip(),
        "f1_result": r.OUTCOME.str.split("/").str[0],
        "weightclass": r.WEIGHTCLASS.str.replace(r"^UFC |\s*(Title )?Bout$", "", regex=True),
        "title_fight": r.WEIGHTCLASS.str.contains("Title") & ~r.WEIGHTCLASS.str.contains("Tournament"),
        "interim_title": r.WEIGHTCLASS.str.contains("Interim"),"women": r.WEIGHTCLASS.str.contains("Women"),
        "method": r.METHOD, "end_round": pd.to_numeric(r.ROUND, errors="coerce"),
        "end_time_s": r.TIME.map(mmss), "time_format": r["TIME FORMAT"],
        "sched_rounds": r["TIME FORMAT"].str.extract(r"^(\d+) Rnd", expand=False).astype(float),
        "referee": r.REFEREE, "details": r.DETAILS,
    })
    out = out.merge(ev[["EVENT", "date", "LOCATION"]].rename(columns={"EVENT": "event", "LOCATION": "location"}),
                    on="event", how="left")
    # συνολικός χρόνος αγώνα (5λεπτοι γύροι στα σύγχρονα format)
    out["fight_time_s"] = (out.end_round - 1) * 300 + out.end_time_s
    out["method_grp"] = np.select(
        [out.method.str.startswith("Decision"), out.method.str.contains("KO|TKO"),
         out.method.str.startswith("Submission")], ["DEC", "KO", "SUB"], "OTHER")

    # στατιστικά ανά μαχητή ανά αγώνα (άθροισμα γύρων)
    s = pd.read_csv(RAW / "ufc_fight_stats.csv").dropna(subset=["FIGHTER"])
    s["EVENT"] = s.EVENT.str.strip(); s["BOUT"] = s.BOUT.str.strip(); s["FIGHTER"] = s.FIGHTER.str.strip()
    cols = {"SIG.STR.": "sig", "TOTAL STR.": "tot", "TD": "td", "HEAD": "head", "BODY": "body", "LEG": "leg",
            "DISTANCE": "dist", "CLINCH": "clinch", "GROUND": "ground"}
    for c, n in cols.items():
        x = s[c].map(of)
        s[n] = x.str[0]; s[n + "_att"] = x.str[1]
    s["kd"] = pd.to_numeric(s.KD, errors="coerce")
    s["subatt"] = pd.to_numeric(s["SUB.ATT"], errors="coerce")
    s["rev"] = pd.to_numeric(s["REV."], errors="coerce")
    s["ctrl_s"] = s.CTRL.map(mmss)
    num = [c for c in s.columns if c in cols.values() or c.endswith("_att")] + ["kd", "subatt", "rev", "ctrl_s"]
    tot = s.groupby(["EVENT", "BOUT", "FIGHTER"])[num].sum(min_count=1).reset_index()
    tot["n_rounds_stats"] = s.groupby(["EVENT", "BOUT", "FIGHTER"]).size().values

    out["bout"] = r.BOUT
    for side in ("f1", "f2"):
        m = tot.rename(columns={"EVENT": "event", "BOUT": "bout", "FIGHTER": side})
        m = m.rename(columns={c: f"{side}_{c}" for c in num + ["n_rounds_stats"]})
        out = out.merge(m, on=["event", "bout", side], how="left")
    # μετονομασμένα events («UFC Fight Night» -> «Noche UFC») εμφανίζονται διπλά χωρίς ημερομηνία
    out = out.dropna(subset=["date"]).drop_duplicates("fight_url")
    return out.drop(columns="bout").sort_values(["date", "event"]).reset_index(drop=True)


def am2dec(a):
    a = pd.to_numeric(a, errors="coerce")
    return pd.Series(np.where(a > 0, 1 + a / 100, 1 + 100 / a.abs()), index=a.index)


def match_odds(fights):
    ev = pd.read_csv(DATA / "bfo_events.csv")
    bf = pd.read_csv(DATA / "bfo_fights.csv").merge(ev[["event_id", "date", "name"]], on="event_id")
    od = pd.read_csv(DATA / "bfo_fighter_odds.csv")
    od["open_dec"] = am2dec(od.open)
    # κλείσιμο = μέσο του εύρους (σε πιθανότητα) - το εύρος είναι min/max όλων των βιβλίων
    p_lo, p_hi = 1 / am2dec(od.close_lo), 1 / am2dec(od.close_hi)
    od["close_dec"] = 2 / (p_lo + p_hi)
    od["close_spread_pp"] = (p_lo - p_hi).abs() * 100
    od["fkey"] = od.fighter.map(key)

    bf["date"] = pd.to_datetime(bf.date).dt.date
    fights = fights.copy()
    fights["k1"], fights["k2"] = fights.f1.map(key), fights.f2.map(key)
    bf["k1"], bf["k2"] = bf.f1.map(key), bf.f2.map(key)

    def last(k):
        return k.split()[-1] if k else ""

    # ευρετήριο ufcstats ανά ημερομηνία (±1 μέρα: ώρες/ζώνες)
    by_date = {}
    for i, row in fights.iterrows():
        by_date.setdefault(row.date, []).append(i)

    def same(a, b):  # ίδιο πρόσωπο: ίδιο πλήρες ή ίδιο επώνυμο + ίδιο αρχικό
        if a == b:
            return True
        ta, tb = a.split(), b.split()
        return bool(ta and tb) and ta[-1] == tb[-1] and ta[0][0] == tb[0][0]

    links, unmatched = [], []
    for _, b in bf.iterrows():
        if pd.isna(b.date):
            continue
        hit = None
        for d in (b.date, b.date - pd.Timedelta(days=1), b.date + pd.Timedelta(days=1)):
            for i in by_date.get(d, []):
                f = fights.loc[i]
                if same(b.k1, f.k1) and same(b.k2, f.k2):
                    hit = (i, False)
                elif same(b.k1, f.k2) and same(b.k2, f.k1):
                    hit = (i, True)
                if hit:
                    break
            if hit is None:  # χαλαρό: τουλάχιστον ένας ίδιος + επώνυμο του άλλου
                for i in by_date.get(d, []):
                    f = fights.loc[i]
                    for swap, (x1, x2) in ((False, (f.k1, f.k2)), (True, (f.k2, f.k1))):
                        if (same(b.k1, x1) and last(b.k2) == last(x2)) or (same(b.k2, x2) and last(b.k1) == last(x1)) \
                                or (same(b.k1, x1) and same(b.k2.split()[0] + " " + last(b.k2), x2)):
                            hit = (i, swap)
                            break
                    if hit:
                        break
            if hit:
                break
        if hit is None:
            unmatched.append(b)
        else:
            links.append(dict(idx=hit[0], swap=hit[1], matchup_id=b.matchup_id, bfo_f1=b.f1_url, bfo_f2=b.f2_url))

    L = pd.DataFrame(links, columns=["idx", "swap", "matchup_id", "bfo_f1", "bfo_f2"]).drop_duplicates("idx")
    res = fights.copy()
    res["matchup_id"] = np.nan
    res.loc[L.idx, "matchup_id"] = L.matchup_id.values
    odk = od.drop_duplicates(["matchup_id", "fighter_url"]).set_index(["matchup_id", "fighter_url"])
    cols = ["open_dec", "close_dec", "close_spread_pp", "spark_first", "spark_last"]
    for c in cols:
        res[f"f1_{c}"] = np.nan; res[f"f2_{c}"] = np.nan
    for l in L.itertuples():
        u1, u2 = (l.bfo_f2, l.bfo_f1) if l.swap else (l.bfo_f1, l.bfo_f2)
        for side, u in (("f1", u1), ("f2", u2)):
            if (l.matchup_id, u) in odk.index:
                v = odk.loc[(l.matchup_id, u)]
                for c in cols:
                    res.at[l.idx, f"{side}_{c}"] = v[c]
    for t in ("open", "close"):
        p1, p2 = 1 / res[f"f1_{t}_dec"], 1 / res[f"f2_{t}_dec"]
        res[f"{t}_overround"] = p1 + p2
        res[f"f1_p_{t}"] = p1 / (p1 + p2)  # χωρίς περιθώριο (αναλογικά)
    pd.DataFrame(unmatched).to_csv(DATA / "ufc_unmatched_bfo.csv", index=False)
    return res.drop(columns=["k1", "k2"]), len(unmatched)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true", help="ξανακατέβασε τα ufcstats CSV από GitHub")
    a = ap.parse_args()
    if a.download:
        download()
    fighters = build_fighters()
    fighters.to_csv(DATA / "ufc_fighters.csv", index=False)
    print(f"ufc_fighters.csv: {len(fighters)} (ίδιο όνομα σε >1: {fighters.dup_name.sum()})")
    fights = build_fights()
    fights.to_csv(DATA / "ufc_fights.csv", index=False)
    print(f"ufc_fights.csv: {len(fights)} αγώνες, {fights.date.min()} -> {fights.date.max()}")
    if (DATA / "bfo_fighter_odds.csv").exists():
        res, n_un = match_odds(fights)
        res.to_csv(DATA / "ufc_fights_odds.csv", index=False)
        has = res.f1_close_dec.notna() & res.f2_close_dec.notna()
        print(f"ufc_fights_odds.csv: με κλείσιμο {has.sum()}/{len(res)} · BFO χωρίς αντιστοίχιση {n_un}")


if __name__ == "__main__":
    main()
