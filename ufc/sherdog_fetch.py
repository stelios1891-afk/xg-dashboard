"""Sherdog (robots: Allow /) -> εθνικότητα + ΠΛΗΡΕΣ επαγγελματικό ρεκόρ (και πριν το UFC) για μαχητές UFC 2007+.

Αναζήτηση fightfinder -> υποψήφιοι με ίδιο όνομα -> σελίδα μαχητή -> δεκτός μόνο αν ένας αγώνας του
στο Sherdog πέφτει ±2 μέρες από αγώνα του στο ufcstats (επιβεβαίωση ταυτότητας).
Έξοδος UFC_DATA/sherdog_fighters.csv (fighter, url, nationality, locality),
       UFC_DATA/sherdog_fights.csv   (fighter, date, result, opponent, event, method, rnd, time)
Cache: UFC_DATA/sherdog_cache/*.html.gz · 1.5″ ανά αίτημα.
"""
import gzip, os, re, sys, time
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent))
from ufc_build import key  # noqa: E402

DATA = Path(os.environ.get("UFC_DATA", Path(__file__).parent / "data"))
CACHE = DATA / "sherdog_cache"
BASE = "https://www.sherdog.com"
sess = requests.Session()
sess.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) research-script"})


def get(path):
    fn = CACHE / (re.sub(r"[^A-Za-z0-9_.-]", "_", path.strip("/"))[:180] + ".html.gz")
    if fn.exists():
        return gzip.open(fn, "rt", encoding="utf8").read()
    for a in range(4):
        try:
            r = sess.get(BASE + path, timeout=30)
            time.sleep(1.5)
            if r.status_code == 200:
                CACHE.mkdir(parents=True, exist_ok=True)
                with gzip.open(fn, "wt", encoding="utf8") as f:
                    f.write(r.text)
                return r.text
            if r.status_code == 404:
                return ""
        except requests.RequestException:
            pass
        time.sleep(10 * (a + 1))
    return None


def parse_fighter(html):
    s = BeautifulSoup(html, "html.parser")
    nat = s.select_one("[itemprop=nationality]")
    loc = s.select_one("[itemprop=addressLocality]")
    fights = []
    for t in s.find_all("table"):
        hdr = t.find("tr")
        if not hdr or "Result" not in hdr.get_text():
            continue
        # «Pro» ιστορικό = 1ος πίνακας με Result (amateur/exhibition έρχονται μετά)
        for r in t.find_all("tr")[1:]:
            c = r.find_all("td")
            if len(c) < 6:
                continue
            ev = c[2].get_text(" ", strip=True)
            m = re.search(r"(\w{3}) / (\d{2}) / (\d{4})", ev)
            d = pd.to_datetime(f"{m.group(1)} {m.group(2)} {m.group(3)}", format="%b %d %Y", errors="coerce") if m else pd.NaT
            fights.append(dict(date=d, result=c[0].get_text(strip=True).lower(), opponent=c[1].get_text(" ", strip=True),
                               event=re.sub(r"\s*\w{3} / \d{2} / \d{4}\s*$", "", ev),
                               method=re.sub(r"\s*(VIEW PLAY)?\s*$", "", c[3].get_text(" ", strip=True)),
                               rnd=c[4].get_text(strip=True), time=c[5].get_text(strip=True)))
        break
    return (nat.get_text(strip=True) if nat else None, loc.get_text(" ", strip=True) if loc else None, fights)


def main():
    F = pd.read_csv(DATA / "ufc_fights.csv")
    F = F[F.date >= "2007"]
    dates = {}
    for a, b, d in zip(F.f1, F.f2, pd.to_datetime(F.date)):
        dates.setdefault(a, []).append(d); dates.setdefault(b, []).append(d)
    names = sorted(dates)
    print(f"μαχητές: {len(names)}", flush=True)
    fr, fs, miss = [], [], []
    for i, n in enumerate(names, 1):
        html = get(f"/stats/fightfinder?SearchTxt={quote_plus(n)}")
        ok = None
        if html:
            s = BeautifulSoup(html, "html.parser")
            cands = []
            for t in s.find_all("table"):
                for r in t.find_all("tr"):
                    a = r.find("a", href=re.compile(r"^/fighter/"))
                    if a and key(a.get_text(" ", strip=True)) == key(n):
                        cands.append(a["href"])
            if not cands:  # χαλαρά: ίδιο επώνυμο + αρχικό
                for t in s.find_all("table"):
                    for r in t.find_all("tr"):
                        a = r.find("a", href=re.compile(r"^/fighter/"))
                        if a:
                            ka, kn = key(a.get_text(" ", strip=True)).split(), key(n).split()
                            if ka and kn and ka[-1] == kn[-1] and ka[0][0] == kn[0][0]:
                                cands.append(a["href"])
            for u in list(dict.fromkeys(cands))[:3]:
                ph = get(u)
                if not ph:
                    continue
                nat, loc, fights = parse_fighter(ph)
                fd = [f["date"] for f in fights if pd.notna(f["date"])]
                if any(abs((x - y).days) <= 2 for x in fd for y in dates[n]):
                    ok = (u, nat, loc, fights)
                    break
        if ok:
            u, nat, loc, fights = ok
            fr.append(dict(fighter=n, url=u, nationality=nat, locality=loc))
            for f in fights:
                fs.append(dict(fighter=n, **f))
        else:
            miss.append(n)
        if i % 100 == 0:
            print(f"  {i}/{len(names)} · βρέθηκαν {len(fr)} · όχι {len(miss)}", flush=True)
            pd.DataFrame(fr).to_csv(DATA / "sherdog_fighters.csv", index=False)
            pd.DataFrame(fs).to_csv(DATA / "sherdog_fights.csv", index=False)
    pd.DataFrame(fr).to_csv(DATA / "sherdog_fighters.csv", index=False)
    pd.DataFrame(fs).to_csv(DATA / "sherdog_fights.csv", index=False)
    pd.Series(miss, name="fighter").to_csv(DATA / "sherdog_missing.csv", index=False)
    print(f"τέλος: βρέθηκαν {len(fr)}/{len(names)} · αγώνες {len(fs)}")


if __name__ == "__main__":
    main()
