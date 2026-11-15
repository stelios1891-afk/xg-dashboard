"""Wikipedia (επίσημο API) -> αντικαταστάτες με μέρες προετοιμασίας + αποτυχίες στο ζύγισμα, ανά event UFC.

1) «List of UFC events» -> τίτλος σελίδας + ημερομηνία κάθε event
2) wikitext κάθε event (cache gz) -> ενότητα Background, προτάσεις:
   - «replaced by [[X]]» / «stepped in» -> αντικαταστάτης X· είδηση = |date= των παραπομπών της πρότασης
     -> notice_days = ημ. event − ημ. είδησης
   - «weighed in at … over» / «missed weight» -> μαχητές της κάρτας ΠΡΙΝ από τη φράση
   Δεχόμαστε μόνο ονόματα που ταιριάζουν με μαχητή της κάρτας (ufcstats) -> όχι λάθος σύνδεσμοι (τίτλοι κ.λπ.).
Έξοδος UFC_DATA/wiki_replacements.csv, wiki_weightmiss.csv. Περιεχόμενο Wikipedia: CC BY-SA.
"""
import gzip, json, os, re, sys, time
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent))
from ufc_build import key  # noqa: E402

DATA = Path(os.environ.get("UFC_DATA", Path(__file__).parent / "data"))
CACHE = DATA / "wiki_cache"
API = "https://en.wikipedia.org/w/api.php"
HDR = {"User-Agent": "BettingModelResearch/1.0 (personal research; contact via github stelios1891-afk)"}
MON = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def wikitext(title):
    fn = CACHE / (re.sub(r"[^A-Za-z0-9_.-]", "_", title)[:150] + ".json.gz")
    if fn.exists():
        return json.load(gzip.open(fn, "rt", encoding="utf8"))
    for a in range(4):
        try:
            r = requests.get(API, params=dict(action="parse", page=title, prop="wikitext", format="json",
                                              formatversion=2, redirects=1), headers=HDR, timeout=30)
            time.sleep(1.0)
            if r.status_code == 200:
                t = r.json().get("parse", {}).get("wikitext", "")
                CACHE.mkdir(parents=True, exist_ok=True)
                json.dump(t, gzip.open(fn, "wt", encoding="utf8"))
                return t
        except requests.RequestException:
            pass
        time.sleep(5 * (a + 1))
    return ""


def event_list():
    t = wikitext("List of UFC events")
    out = []
    for row in t.split("\n|-"):  # γραμμή πίνακα: 1ος σύνδεσμος = event, 1ο {{dts}} = ημερομηνία
        row = re.sub(r"<ref.*?</ref>|<ref[^>]*/>", "", row, flags=re.S)
        lk = re.search(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]", row)
        m = re.search(r"\{\{dts\|(\d{4})\|(\w+)\|(\d{1,2})", row)
        if not lk or not m or lk.start() > m.start():
            continue
        title, (y, mo, d) = lk.group(1), m.groups()
        mon = int(mo) if mo.isdigit() else MON.get(mo[:3])
        if mon:
            out.append((title.strip(), pd.Timestamp(int(y), mon, int(d))))
    return out


def ref_date(s):
    m = re.search(r"\|\s*date\s*=\s*([^|}]+)", s)
    if not m:
        return None
    d = pd.to_datetime(m.group(1).strip(), errors="coerce")
    return None if pd.isna(d) else d


def sentences(text, whole=False):
    """Background (ή όλη η σελίδα) -> λίστα (καθαρό κείμενο, [ημερομηνίες παραπομπών], [(όνομα συνδέσμου, θέση)])."""
    m = re.search(r"==\s*Background\s*==(.*?)(\n==[^=]|$)", text, re.S)
    if whole:
        b = text
    elif not m:
        return []
    else:
        b = m.group(1)
    named = {}
    for rm in re.finditer(r'<ref name\s*=\s*"?([^">/]+)"?\s*>(.*?)</ref>', b, re.S):
        named[rm.group(1).strip()] = ref_date(rm.group(2))

    def rep(mm):
        s = mm.group(0)
        nm = re.match(r'<ref name\s*=\s*"?([^">/]+)"?\s*/>', s)
        d = named.get(nm.group(1).strip()) if nm else ref_date(s)
        return f" §{d.date() if d is not None else ''}§ "
    b = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", rep, b, flags=re.S)
    b = re.sub(r"\{\{[^{}]*\}\}", "", b)
    b = re.sub(r"\{\{[^{}]*\}\}", "", b)
    # παραπομπές ΜΕΤΑ την τελεία ανήκουν στην ίδια πρόταση -> μεταφορά πριν την τελεία
    b = re.sub(r"\.\s*((?:§[^§]*§\s*)+)", r" \1. ", b)
    out = []
    # σπάσιμο σε προτάσεις: τελεία ακολουθούμενη από κενό/§ και κεφαλαίο
    for s in re.split(r"(?<=\.)\s+(?=[A-Z\[§])|\n+", b):
        dates = [pd.Timestamp(x) for x in re.findall(r"§(\d{4}-\d{2}-\d{2})§", s)]
        links = []
        clean = ""
        pos = 0
        for lm in re.finditer(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", s):
            clean += re.sub(r"§[^§]*§", "", s[pos:lm.start()])
            disp = (lm.group(2) or lm.group(1)).strip()
            links.append((disp, lm.group(1).strip(), len(clean)))
            clean += disp
            pos = lm.end()
        clean += re.sub(r"§[^§]*§", "", s[pos:])
        if clean.strip():
            out.append((clean, dates, links))
    return out


def same(a, b):
    ta, tb = key(a).split(), key(b).split()
    return bool(ta and tb) and (ta == tb or (ta[-1] == tb[-1] and ta[0][0] == tb[0][0]))


def main():
    F = pd.read_csv(DATA / "ufc_fights.csv")
    F["d"] = pd.to_datetime(F.date)
    evs = event_list()
    print(f"events στη λίστα Wikipedia: {len(evs)}", flush=True)
    reps, wms = [], []
    for i, (title, d) in enumerate(evs, 1):
        card = F[(F.d - d).abs() <= pd.Timedelta(days=1)]
        names = list(card.f1) + list(card.f2)
        if not names:
            continue
        txt = wikitext(title)

        def match(link):
            for n in names:
                if same(link[0], n) or same(link[1], n):
                    return n
            return None
        for clean, dates, links in sentences(txt):
            low = clean.lower()
            AFTER = ("replaced by", "replacement by", "was replaced")  # αντικαταστάτης = 1ος μαχητής ΜΕΤΑ
            BEFORE = ("as the replacement", "as a replacement", "as his replacement", "as her replacement",
                      "stepped in", "will replace", "would replace", "agreed to replace", "short notice")  # = τελευταίος ΠΡΙΝ
            for kw in AFTER + BEFORE:
                k = low.find(kw)
                if k < 0:
                    continue
                after = [match(l) for l in links if l[2] >= k]
                before = [match(l) for l in links if l[2] < k]
                cand = [x for x in after if x][:1] if kw in AFTER else [x for x in before if x][-1:]
                if cand:
                    nd = max(dates) if dates else None
                    reps.append(dict(event=title, date=d.date(), fighter=cand[0], news_date=nd.date() if nd is not None else None,
                                     notice_days=(d - nd).days if nd is not None else None, text=clean[:300]))
                break
        # ζύγισμα: ΟΛΗ η σελίδα (συχνά σε σημειώσεις εκτός Background)· λίστα «A, B και C missed weight» -> όλοι
        for clean, dates, links in sentences(txt, whole=True):
            low = clean.lower()
            if not ("weigh" in low and ("over" in low or "missed" in low) and ("pound" in low or "lb" in low)):
                continue
            for km in re.finditer(r"weighed|missed weight|missed the", low):
                prev = [(l, match(l)) for l in links if l[2] < km.start() and km.start() - l[2] <= 60]
                prev = [x for x in prev if x[1]]
                if not prev:
                    continue
                wms.append(dict(event=title, date=d.date(), fighter=prev[-1][1], text=clean[:300]))
                if "missed weight" in low[km.start():km.start() + 14]:  # λίστα ονομάτων κολλητά πριν
                    seg = [x for x in links if x[2] < km.start() and match(x)]
                    for l in reversed(seg[:-1]):
                        gap = clean[l[2] + len(l[0]):seg[seg.index(l) + 1][2]]
                        if re.fullmatch(r"\s*(,|,? and|and)\s*", gap):
                            wms.append(dict(event=title, date=d.date(), fighter=match(l), text=clean[:300]))
                        else:
                            break
        if i % 100 == 0:
            print(f"  {i}/{len(evs)} · αντικαταστάτες {len(reps)} · ζύγισμα {len(wms)}", flush=True)
    R = pd.DataFrame(reps).drop_duplicates(["date", "fighter"])
    W = pd.DataFrame(wms).drop_duplicates(["date", "fighter"])
    R.to_csv(DATA / "wiki_replacements.csv", index=False)
    W.to_csv(DATA / "wiki_weightmiss.csv", index=False)
    print(f"wiki_replacements.csv: {len(R)} (με μέρες: {R.notice_days.notna().sum()}) · wiki_weightmiss.csv: {len(W)}")


if __name__ == "__main__":
    main()
