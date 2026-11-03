"""BFO: πλήρης σειρά τιμών (sparkline) ανά μαχητή-αγώνα από τις σελίδες μαχητών στο cache.

Η σειρά είναι ~10 σημεία από το άνοιγμα (σημείο 0 = ακριβώς το «Open») ως το κλείσιμο, δεκαδικές.
Έξοδος UFC_DATA/bfo_spark.csv: matchup_id, fighter_url, s0..s9 (n_spark<10 -> τα τελευταία κενά)
"""
import gzip, os, re, json
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

DATA = Path(os.environ.get("UFC_DATA", Path(__file__).parent / "data"))


def main():
    rows = []
    for fn in sorted((DATA / "bfo_cache").glob("fighters__*.html.gz")):
        url = "/" + fn.name[:-len(".html.gz")].replace("__", "/")
        s = BeautifulSoup(gzip.open(fn, "rt", encoding="utf8").read(), "html.parser")
        for td in s.select("td.chart-cell[data-sparkline]"):
            mu = json.loads(td["data-li"])[0]
            v = [float(x) for x in td["data-sparkline"].split(",") if x.strip()]
            rows.append(dict(matchup_id=mu, fighter_url=url, n=len(v), **{f"s{i}": x for i, x in enumerate(v[:10])}))
    df = pd.DataFrame(rows).drop_duplicates(["matchup_id", "fighter_url"])
    df.to_csv(DATA / "bfo_spark.csv", index=False)
    print(f"bfo_spark.csv: {len(df)} σειρές")


if __name__ == "__main__":
    main()
