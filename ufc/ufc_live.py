"""UFC πρόβα χωρίς χρήματα: τι θα έπαιζε η φόρμουλα στις βραδιές που δεν έχουν κριθεί ακόμα. Κανένα Telegram, κανένα στοίχημα.

Φόρμουλα (Στέλιος 6/11, προσωρινή ως τα τεστ Pinnacle): 6 μηχανισμοί, όλη η καριέρα, κατώφλι 5 πόντοι, όχι αγώνες με πρωτοεμφανιζόμενο.
Βάρη μίξης από τις ασφαλείς τιμές: «νωρίς» ως 6 ώρες πριν τον αγώνα, «κλείσιμο» μετά (το όριο των 6 ωρών είναι υπόθεση, όχι τεστ).
Τιμές: ufc_pin_log.jsonl (καταγραφή Pinnacle στο GitHub). Στοιχεία μαχητών: ο ίδιος κώδικας με τα τεστ, με τους αγώνες που έρχονται
προστιθέμενους σε αντίγραφο του ufc_fights, άρα μετρούν μόνο όσα έγιναν πριν. Τοποθεσίες: ufc/live_events.csv (χειροκίνητα).
Έξοδος UFC_DATA: ufc_live_board.csv (όλοι οι αγώνες που δεν έχουν κριθεί, τελευταία τιμή) · ufc_live_ledger.csv (1η φορά που βγήκε pick, ποτέ δεν ξαναγράφεται).

Χρήση: python ufc/ufc_live.py [--refresh] [--check]
  --refresh  ΠΡΩΤΑ γράφει τα picks, μετά κατεβάζει τα νέα αποτελέσματα ufcstats και τους νέους μαχητές Sherdog
  --check    συγκρίνει τα στοιχεία αυτής της ροής με των τεστ σε παλιά βραδιά και σταματά
"""
import difflib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from t16_setup import SIX, load  # noqa: E402  (ορίζει ασφαλείς τιμές)
import t3_mechanisms as t3  # noqa: E402
from t2_age_repl import DATA  # noqa: E402
from t8_sherdog import nat_norm  # noqa: E402
from t10_own_engine import ridge  # noqa: E402
from t11_level_select import cv_fit, engine_wf, level_features  # noqa: E402
from ufc_build import key  # noqa: E402

pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 300); pd.set_option("display.max_colwidth", 40)
lg, sig = t3.lg, t3.sig
LOG_URL = "https://raw.githubusercontent.com/stelios1891-afk/xg-dashboard/main/ufc_pin_log.jsonl"
THR, CLOSE_H = .05, 6
BOARD, LEDGER = DATA / "ufc_live_board.csv", DATA / "ufc_live_ledger.csv"
dec = lambda a: 1 + a / 100 if a > 0 else 1 + 100 / abs(a)


def pin_rows():
    r = requests.get(LOG_URL, timeout=30)
    r.raise_for_status()
    R = pd.DataFrame([json.loads(x) for x in r.text.splitlines() if x.strip()])
    R = R[(R.type == "moneyline") & (R.key == "s;0;m") & R.f_home.notna() & R.home.notna() & R.away.notna()].copy()
    if "special" in R:
        R = R[R.special.isna()]
    R["t"], R["st"] = pd.to_datetime(R.ts, utc=True), pd.to_datetime(R.start, utc=True)
    R["d1"], R["d2"] = R.home.map(dec), R.away.map(dec)
    R["p"] = (1 / R.d1) / (1 / R.d1 + 1 / R.d2)
    return R.sort_values("t")


def match_names(names, fi, F):
    """Όνομα Pinnacle -> όνομα ufcstats. Ακριβές κλειδί, αλλιώς ίδιες λέξεις, αλλιώς πολύ κοντινό (σημειώνεται).
    Πρώτα το όνομα των αγώνων: 23 μαχητές γράφονται αλλιώς στον πίνακα μαχητών (Waldo Cortes-Acosta / Waldo Cortes Acosta) και θα έβγαιναν πρωτοεμφανιζόμενοι."""
    by = {k: f for k, f in zip(fi.name_key, fi.fighter)}
    by.update({key(f): f for f in pd.unique(F[["f1", "f2"]].values.ravel())})
    tok = {" ".join(sorted(k.split())): f for k, f in by.items()}
    out = {}
    for n in names:
        k = key(n)
        if k in by:
            out[n] = (by[k], "")
        elif " ".join(sorted(k.split())) in tok:
            out[n] = (tok[" ".join(sorted(k.split()))], "")
        else:
            c = difflib.get_close_matches(k, by, 1, .88)
            out[n] = (by[c[0]], "κοντινό όνομα") if c else (n, "άγνωστο όνομα")
    return out


def features_with(F, up):
    """Ο ίδιος κώδικας των τεστ, σε αντίγραφο με τους αγώνες που έρχονται (χωρίς στατιστικά)."""
    W = Path(tempfile.mkdtemp(prefix="ufc_live_"))
    try:
        (W / "raw").mkdir()
        shutil.copy(DATA / "raw" / "ufc_fight_stats.csv", W / "raw")
        shutil.copy(DATA / "ufc_fighters.csv", W)
        pd.concat([F, up], ignore_index=True).to_csv(W / "ufc_fights.csv", index=False)
        env = {**os.environ, "UFC_DATA": str(W), "PYTHONIOENCODING": "utf8"}
        subprocess.run([sys.executable, "-W", "ignore", str(HERE / "ufc_features.py"), "--causal"], check=True, env=env, stdout=subprocess.DEVNULL)
        return pd.read_csv(W / "ufc_features_causal.csv")
    finally:
        shutil.rmtree(W, ignore_errors=True)


def diff_table(x):
    """Διαφορές f1−f2 της φόρμουλας, όπως στο t10_own_engine.build (χωρίς τα στοιχεία που δεν χρησιμοποιεί)."""
    fi = pd.read_csv(DATA / "ufc_fighters.csv")
    dob = pd.to_datetime(fi[~fi.dup_name].set_index("fighter").dob)
    dobk = pd.to_datetime(fi[~fi.dup_name].set_index("name_key").dob)
    born = lambda c: x[c].map(dob).fillna(x[c].map(key).map(dobk))  # ίδιος μαχητής με άλλη γραφή στον πίνακα μαχητών
    d = pd.to_datetime(x.date)
    A = pd.read_csv(DATA / "sherdog_fighters.csv").drop_duplicates("fighter").set_index("fighter")
    nat = A.nationality.map(nat_norm)
    cty = x.location.fillna("").str.split(",").str[-1].str.strip().replace({"United Kingdom": "UK"})
    n1, n2 = x.f1.map(nat), x.f2.map(nat)
    known = (n1.notna() & n2.notna()).values
    us = (cty == "USA").values
    h = ((n1 == cty).values.astype(float) - (n2 == cty).values.astype(float)) * known
    D = pd.DataFrame(index=x.index)
    D["age"] = (d - born("f1")).dt.days / 365.25 - (d - born("f2")).dt.days / 365.25
    for s in ("f1", "f2"):
        x[f"{s}_lnexp"] = np.log1p(x[f"{s}_n_prev"])
        x[f"{s}_lnlay"] = np.log1p(x[f"{s}_layoff_d"].fillna(365))
    for c in SIX:
        if c in ("age", "home_nus", "home_us") or c.startswith(("big_", "opp_", "dwcs", "d_")):
            continue
        D[c] = x[f"f1_{c}"] - x[f"f2_{c}"]
    D["home_nus"], D["home_us"] = h * ~us, h * us
    return level_features(x, D), known


def check(o, D):
    """Στην τελευταία κριμένη βραδιά με τιμές, τα στοιχεία αυτής της ροής πρέπει να είναι ίδια με των τεστ."""
    last = o[o.date == o.date.max()]
    x = last[["fight_url", "date", "f1", "f2", "location"]].merge(pd.read_csv(DATA / "ufc_features_causal.csv").drop(columns=["date", "event", "f1", "f2"]), on="fight_url").reset_index(drop=True)
    E, _ = diff_table(x)
    a, b = D.loc[last.index, SIX].values, E[SIX].values
    gap = np.nanmax(np.abs(a - b), axis=0)
    print(f"έλεγχος σε {len(last)} αγώνες της {o.date.max()}: μεγαλύτερη διαφορά ανά στοιχείο {np.nanmax(gap):.2e}" + (" ✓" if np.nanmax(gap) < 1e-6 else " ✗"))
    if np.nanmax(gap) >= 1e-6:
        print(pd.Series(gap, index=SIX)[gap >= 1e-6])


def weights(o, D, w, y):
    """Βάρη μίξης με προβλέψεις μηχανής που δεν έχουν δει τον αγώνα (όπως στα τεστ)."""
    qe = np.clip(engine_wf(D, SIX, w, y), 1e-4, 1 - 1e-4)
    tr = y >= 2012
    return {k: t3.fit(np.c_[lg(o[f"f1_p_{p}"].values), lg(qe)][tr], w[tr])[0] for k, p in (("νωρίς", "open"), ("κλείσιμο", "close"))}


def main():
    o, D, w = load("ufc_features_causal.csv")
    y = o.y.values
    if "--check" in sys.argv:
        return check(o, D)
    B = weights(o, D, w, y)
    print("βάρη (αγορά, μηχανή): " + " · ".join(f"{k} {b[0]:.3f}, {b[1]:.3f}" for k, b in B.items()))
    sd = D[SIX].std().replace(0, 1)
    X = (D[SIX] / sd).fillna(0.0).values
    beta = ridge(X, w, cv_fit(X, w, y))

    F = pd.read_csv(DATA / "ufc_fights.csv")
    R = pin_rows()
    R["evd"] = (R.st - pd.Timedelta(hours=10)).dt.strftime("%Y-%m-%d")
    R = R[R.evd > F.date.max()]
    if R.empty:
        return print("καμία βραδιά που να μην έχει κριθεί στην καταγραφή")
    fi = pd.read_csv(DATA / "ufc_fighters.csv")
    M = match_names(pd.unique(R[["f_home", "f_away"]].values.ravel()), fi, F)
    ev = pd.read_csv(HERE / "live_events.csv")
    locs = {d: l for d, l in zip(ev.date, ev.location)}
    near = lambda d: next((locs[k] for k in (d, str((pd.Timestamp(d) + timedelta(days=1)).date()), str((pd.Timestamp(d) - timedelta(days=1)).date())) if k in locs), None)
    lastrow = R.groupby("mid").tail(1).reset_index(drop=True)
    up = pd.DataFrame({"fight_url": "live:" + lastrow.mid.astype(str), "event": "live", "date": lastrow.evd, "location": lastrow.evd.map(near),
                       "f1": lastrow.f_home.map(lambda n: M[n][0]), "f2": lastrow.f_away.map(lambda n: M[n][0])})
    x = features_with(F, up)
    x = x[x.fight_url.str.startswith("live:")].merge(up[["fight_url", "location"]], on="fight_url").reset_index(drop=True)
    E, known = diff_table(x)
    q = sig((E[SIX] / sd).fillna(0.0).values @ beta)

    now = datetime.now(timezone.utc)
    board, new = [], []
    old = pd.read_csv(LEDGER) if LEDGER.exists() else pd.DataFrame(columns=["mid", "πλευρά"])
    seen = set(zip(old.mid, old["πλευρά"]))
    for i, u in enumerate(x.itertuples()):
        mid = int(u.fight_url.split(":")[1])
        h = R[R.mid == mid]
        deb = bool(u.f1_n_prev == 0 or u.f2_n_prev == 0)
        flags = [t for t in (M[h.f_home.iloc[-1]][1], M[h.f_away.iloc[-1]][1]) if t]
        if deb:
            flags.append("πρωτοεμφανιζόμενος")
        if not known[i]:
            flags.append("λείπει εθνικότητα")
        if not isinstance(u.location, str):
            flags.append("λείπει τοποθεσία")
        if not np.isfinite(E.age.iloc[i]):
            flags.append("λείπει ηλικία")
        # ο αγώνας κόβεται αν ο μαχητής δεν αναγνωρίστηκε με βεβαιότητα ή είναι πρωτοεμφανιζόμενος· τα κενά στοιχεία μετρούν ως 0 όπως στα τεστ
        out = deb or any(t.endswith("όνομα") for t in flags)
        mix = []
        for r in h.itertuples():
            b = B["κλείσιμο"] if (r.st - r.t) <= pd.Timedelta(hours=CLOSE_H) else B["νωρίς"]
            m = sig(b[0] * lg(r.p) + b[1] * lg(np.clip(q[i], 1e-4, 1 - 1e-4)))
            mix.append(m)
            if not out and abs(m - r.p) >= THR:
                side = "f1" if m > r.p else "f2"
                if (mid, side) not in seen:
                    seen.add((mid, side))
                    new.append(dict(mid=mid, πλευρά=side, γράφτηκε=now.strftime("%Y-%m-%dT%H:%MZ"), ώρα_τιμής=r.ts, έναρξη=r.start, pick=u.f1 if side == "f1" else u.f2, αντίπαλος=u.f2 if side == "f1" else u.f1,
                                    απόδοση=round(r.d1 if side == "f1" else r.d2, 3), όριο=r.limit, αγορά=round(r.p if side == "f1" else 1 - r.p, 4), μίξη=round(m if side == "f1" else 1 - m, 4),
                                    μηχανή=round(q[i] if side == "f1" else 1 - q[i], 4), ώρες_πριν=round((r.st - r.t).total_seconds() / 3600, 1)))
        L, m = h.iloc[-1], mix[-1]
        board.append(dict(βραδιά=u.date, έναρξη=L.start[:16], f1=u.f1, f2=u.f2, απ1=round(L.d1, 3), απ2=round(L.d2, 3), όριο=L.limit, αγορά_f1=round(L.p, 3), μηχανή_f1=round(q[i], 3), μίξη_f1=round(m, 3), διαφορά=round(m - L.p, 3),
                          pick=("" if out or abs(m - L.p) < THR else u.f1 if m > L.p else u.f2), σημειώσεις=" · ".join(flags), n1=int(u.f1_n_prev), n2=int(u.f2_n_prev), τιμές=len(h)))
    T = pd.DataFrame(board).sort_values(["βραδιά", "έναρξη"])
    T.to_csv(BOARD, index=False)
    print(T.drop(columns=["απ1", "απ2", "έναρξη"]).to_string(index=False))
    if new:
        pd.concat([old, pd.DataFrame(new)], ignore_index=True).to_csv(LEDGER, index=False)
    print(f"\nαγώνες {len(T)} · pick τώρα {(T.pick != '').sum()} · νέες εγγραφές στο ημερολόγιο {len(new)} · πρωτοεμφανιζόμενοι/κομμένοι {T['σημειώσεις'].str.contains('πρωτοεμφ|όνομα').sum()}")

    if "--refresh" in sys.argv:
        env = {**os.environ, "PYTHONIOENCODING": "utf8"}
        for a in (["ufc_build.py", "--download"], ["ufc_features.py", "--causal"], ["sherdog_fetch.py"]):
            subprocess.run([sys.executable, "-W", "ignore", str(HERE / a[0]), *a[1:]], check=True, env=env)


if __name__ == "__main__":
    main()
