"""2ο πέρασμα Sherdog για όσους έλειψαν: η αναζήτηση έχει σελίδες (Jon Jones = σελ. 2) -> περνάμε έως 6 σελίδες + παραλλαγή ονόματος.
Ίδια επιβεβαίωση ταυτότητας (αγώνας ±2 μέρες από ufcstats). Προσθέτει στα sherdog_fighters/fights.csv, ξαναγράφει sherdog_missing.csv."""
import re
from urllib.parse import quote_plus

import pandas as pd
from bs4 import BeautifulSoup

from sherdog_fetch import DATA, get, parse_fighter
from ufc_build import key

A = pd.read_csv(DATA / "sherdog_fighters.csv")
S = pd.read_csv(DATA / "sherdog_fights.csv")
M = pd.read_csv(DATA / "sherdog_missing.csv").fighter.tolist()
F = pd.read_csv(DATA / "ufc_fights.csv"); F = F[F.date >= "2007"]
dates = {}
for a, b, d in zip(F.f1, F.f2, pd.to_datetime(F.date)):
    dates.setdefault(a, []).append(d); dates.setdefault(b, []).append(d)
SKIP = {"junior", "jr", "de", "da", "dos", "do"}


def cands(n):
    kn = [t for t in key(n).split() if t not in SKIP]
    out, q = [], [n]
    if len(kn) >= 2:
        q.append(f"{kn[0]} {kn[-1]}")
    for term in dict.fromkeys(q):
        for pg in range(1, 7):
            h = get(f"/stats/fightfinder?SearchTxt={quote_plus(term)}&page={pg}")
            if not h:
                break
            s = BeautifulSoup(h, "html.parser")
            for a in s.select("table a[href^='/fighter/']"):
                ka = [t for t in key(a.get_text(" ", strip=True)).split() if t not in SKIP]
                if ka and kn and ka[-1] == kn[-1] and ka[0][0] == kn[0][0]:
                    out.append(a["href"])
            if not s.find("a", href=re.compile(f"page={pg + 1}")):
                break
    return list(dict.fromkeys(out))[:8]


fr, fs, miss = [], [], []
for i, n in enumerate(M, 1):
    ok = None
    for u in cands(n):
        ph = get(u)
        if not ph:
            continue
        nat, loc, fights = parse_fighter(ph)
        if any(pd.notna(f["date"]) and abs((f["date"] - y).days) <= 2 for f in fights for y in dates.get(n, [])):
            ok = (u, nat, loc, fights); break
    if ok:
        fr.append(dict(fighter=n, url=ok[0], nationality=ok[1], locality=ok[2]))
        fs += [dict(fighter=n, **f) for f in ok[3]]
    else:
        miss.append(n)
    if i % 20 == 0:
        print(f"{i}/{len(M)} · βρέθηκαν {len(fr)}", flush=True)
pd.concat([A, pd.DataFrame(fr)]).to_csv(DATA / "sherdog_fighters.csv", index=False)
pd.concat([S, pd.DataFrame(fs)]).to_csv(DATA / "sherdog_fights.csv", index=False)
pd.Series(miss, name="fighter").to_csv(DATA / "sherdog_missing.csv", index=False)
print(f"τέλος: +{len(fr)} · μένουν {len(miss)}", miss[:30])
