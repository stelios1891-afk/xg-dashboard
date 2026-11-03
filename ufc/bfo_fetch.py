"""BestFightOdds -> αποδόσεις UFC (άνοιγμα / εύρος κλεισίματος / μέση κίνηση).

Πηγή: bestfightodds.com (robots.txt: Allow /).
  1) sitemap-events.xml -> όλα τα UFC events (εκτός UFC BJJ)
  2) σελίδα event -> αγώνες (matchup id), μαχητές, ημερομηνία
     + τιμές ανά βιβλίο ΜΟΝΟ για τα σημερινά βιβλία (τα παλιά events είναι άδεια)
  3) σελίδα μαχητή -> για κάθε αγώνα: άνοιγμα, εύρος κλεισίματος (min/max βιβλίων),
     σειρά μέσης απόδοσης (sparkline, δεκαδική) -> πρώτη ≈ άνοιγμα, τελευταία ≈ μέσο κλείσιμο

Έξοδος (στο UFC_DATA, default ufc/data):
  bfo_events.csv        event_id, slug, name, date
  bfo_fights.csv        matchup_id, event_id, f1, f2 (+ urls)
  bfo_fighter_odds.csv  matchup_id, fighter, fighter_url, open, close_lo, close_hi, spark_first, spark_last, n_spark
  bfo_book_odds.csv     matchup_id, label, book, side, prop_type, odds   (μόνο σημερινά βιβλία)
Cache σελίδων: UFC_DATA/bfo_cache/*.html.gz  (ξανατρέξιμο = μόνο τα καινούρια)

Χρήση: python ufc/bfo_fetch.py [--limit N] [--refresh-recent DAYS]
"""
import argparse, csv, gzip, json, os, re, sys, time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = "https://www.bestfightodds.com"
DATA = Path(os.environ.get("UFC_DATA", Path(__file__).parent / "data"))
CACHE = DATA / "bfo_cache"
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) research-script"}
DELAY = 1.0

sess = requests.Session()
sess.headers.update(HDR)


def get(path, refresh=False):
    """Κατέβασμα με cache (gzip). path = '/events/...' ή '/fighters/...'."""
    fn = CACHE / (path.strip("/").replace("/", "__") + ".html.gz")
    if fn.exists() and not refresh:
        return gzip.open(fn, "rt", encoding="utf8").read()
    for attempt in range(4):
        try:
            r = sess.get(BASE + path, timeout=30)
            time.sleep(DELAY)
            if r.status_code == 200:
                fn.parent.mkdir(parents=True, exist_ok=True)
                with gzip.open(fn, "wt", encoding="utf8") as f:
                    f.write(r.text)
                return r.text
            print(f"  HTTP {r.status_code} {path}", flush=True)
        except requests.RequestException as e:
            print(f"  σφάλμα {path}: {e}", flush=True)
        time.sleep(5 * (attempt + 1))
    return None


def am(s):
    """American odds string -> int (ή None)."""
    s = (s or "").strip().replace("−", "-")
    m = re.match(r"^([+-]?\d+)", s)
    return int(m.group(1)) if m else None


def event_list():
    xml = sess.get(BASE + "/sitemap-events.xml", timeout=30).text
    urls = re.findall(r"<loc>https://www\.bestfightodds\.com(/events/ufc-[^<]+)</loc>", xml)
    return [u for u in urls if not u.startswith("/events/ufc-bjj")]


def parse_event(path, html):
    s = BeautifulSoup(html, "html.parser")
    eid = int(path.rsplit("-", 1)[1])
    title = s.title.get_text() if s.title else ""
    # "UFC 199 Odds: Rockhold vs. Bisping II – Jun 4, 2016 | Best Fight Odds"
    m = re.search(r"–\s*([A-Z][a-z]{2} \d{1,2}, \d{4})", title)
    date = datetime.strptime(m.group(1), "%b %d, %Y").date().isoformat() if m else ""
    name = re.split(r"\s+Odds", title)[0].strip()
    ev = dict(event_id=eid, slug=path, name=name, date=date)

    tables = [t for t in s.find_all("table", class_="odds-table")
              if "odds-table-responsive-header" not in (t.get("class") or [])]
    fights, books = [], []
    if not tables:
        return ev, fights, books
    t = tables[0]
    bookname = {th["data-b"]: th.get_text(" ", strip=True) for th in t.find("tr").find_all("th") if th.get("data-b")}
    pending = None
    for r in t.find_all("tr")[1:]:
        th = r.find("th")
        if not th:
            continue
        label = th.get_text(" ", strip=True)
        a = th.find("a", href=re.compile(r"^/fighters/"))
        if a:  # γραμμή μαχητή (έρχονται ανά δύο)
            mu = th.get("data-admin-matchup")
            if mu is None:  # χωρίς τιμές: matchup από [book,side,mu] / [side,mu] / data-mu
                for c in r.find_all(attrs={"data-li": True}):
                    mu = json.loads(c["data-li"])[-1]
                    break
                else:
                    c = r.find(attrs={"data-mu": True})
                    mu = c["data-mu"] if c else None
            if pending is None:
                pending = dict(matchup_id=int(mu) if mu else None, event_id=eid, f1=label, f1_url=a["href"])
            else:
                pending.update(f2=label, f2_url=a["href"])
                fights.append(pending)
                pending = None
        for td in r.find_all("td", attrs={"data-li": True}):
            li = json.loads(td["data-li"])
            if len(li) < 3 or str(li[0]) not in bookname:
                continue
            odds = am(td.get_text(" ", strip=True))
            if odds is None:
                continue
            books.append(dict(matchup_id=li[2], label=label, book=bookname[str(li[0])], side=li[1],
                              prop_type=li[3] if len(li) > 3 else "", odds=odds))
    return ev, fights, books


def parse_fighter(path, html):
    s = BeautifulSoup(html, "html.parser")
    t = s.find("table", class_="team-stats-table")
    out = []
    if not t:
        return out
    cur_mu = None
    for r in t.find_all("tr"):
        th = r.find("th", class_="oppcell")
        if not th:
            continue
        a = th.find("a", href=re.compile(r"^/fighters/"))
        tds = r.find_all("td", class_="moneyline")
        chart = r.find("td", class_="chart-cell")
        if "main-row" in (r.get("class") or []):
            cur_mu = None
            li = chart.get("data-li") if chart else None
            if not li:
                sp = r.find(attrs={"data-li": True})
                li = sp.get("data-li") if sp else None
            if li:
                cur_mu = json.loads(li)[0]
        spark = [float(x) for x in (chart.get("data-sparkline") or "").split(",") if x.strip()] if chart else []
        vals = [am(td.get_text(" ", strip=True)) for td in tds] + [None] * 3
        ev = th.find("a", href=re.compile(r"^/events/"))
        out.append(dict(matchup_id=cur_mu, fighter=a.get_text(" ", strip=True) if a else "",
                        fighter_url=a["href"] if a else "", open=vals[0], close_lo=vals[1], close_hi=vals[2],
                        spark_first=spark[0] if spark else None, spark_last=spark[-1] if spark else None,
                        n_spark=len(spark), event_slug=ev["href"] if ev else "", src_page=path))
    return out


def write(name, rows, cols):
    with open(DATA / name, "w", newline="", encoding="utf8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  -> {name}: {len(rows)} γραμμές", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="μόνο τα πρώτα N events (δοκιμή)")
    ap.add_argument("--refresh-recent", type=int, default=14,
                    help="ξανακατέβασε events/μαχητές των τελευταίων N ημερών (ανανέωση τιμών)")
    a = ap.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)

    evs = event_list()
    print(f"UFC events στο sitemap: {len(evs)}", flush=True)
    if a.limit:
        evs = evs[:a.limit]
    recent = (datetime.now() - timedelta(days=a.refresh_recent)).date().isoformat()

    events, fights, books = [], [], []
    fresh_fighters = set()
    for i, p in enumerate(evs, 1):
        html = get(p)
        if html is None:
            continue
        ev, fs, bs = parse_event(p, html)
        if ev["date"] >= recent:  # πρόσφατο/μελλοντικό -> ξανά για φρέσκες τιμές
            ev, fs, bs = parse_event(p, get(p, refresh=True) or html)
            for f in fs:
                fresh_fighters.update([f["f1_url"], f.get("f2_url")])
        events.append(ev); fights.extend(fs); books.extend(bs)
        if i % 50 == 0:
            print(f"events {i}/{len(evs)}  αγώνες {len(fights)}", flush=True)

    urls = sorted({u for f in fights for u in (f["f1_url"], f.get("f2_url")) if u})
    print(f"μαχητές προς κατέβασμα: {len(urls)}", flush=True)
    frows = []
    for i, u in enumerate(urls, 1):
        html = get(u, refresh=u in fresh_fighters)
        if html:
            frows.extend(parse_fighter(u, html))
        if i % 200 == 0:
            print(f"μαχητές {i}/{len(urls)}", flush=True)

    ufc_mu = {f["matchup_id"] for f in fights}
    seen, odds = set(), []
    # η σειρά μέσης απόδοσης υπάρχει μόνο στη σελίδα του ίδιου του μαχητή -> αυτή πρώτη
    frows.sort(key=lambda r: -r["n_spark"])
    for r in frows:  # κράτα μόνο UFC αγώνες, μία φορά ανά (αγώνας, μαχητής)
        k = (r["matchup_id"], r["fighter_url"])
        if r["matchup_id"] in ufc_mu and k not in seen:
            seen.add(k); odds.append(r)

    write("bfo_events.csv", events, ["event_id", "slug", "name", "date"])
    write("bfo_fights.csv", fights, ["matchup_id", "event_id", "f1", "f2", "f1_url", "f2_url"])
    write("bfo_fighter_odds.csv", odds, ["matchup_id", "fighter", "fighter_url", "open", "close_lo",
                                          "close_hi", "spark_first", "spark_last", "n_spark", "event_slug"])
    write("bfo_book_odds.csv", books, ["matchup_id", "label", "book", "side", "prop_type", "odds"])


if __name__ == "__main__":
    main()
