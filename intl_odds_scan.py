# -*- coding: utf-8 -*-
"""intl_odds_scan.py — Αποδοσεις αγορας (TOA) για τα ματς ΕΘΝΙΚΩΝ του 🌐 International tab (25/9/2026, εντολη Στελιου).

Προτυπο: euro_odds_scan.py. Τρεχει στον scanner (GitHub Actions, scanner_tick.sh). GATING: κανει request ΜΟΝΟ αν
υπαρχει ματς Nations League με σεντρα στις επομενες HOURS_AHEAD ωρες (αλλιως 0 credits). Ενα sport (soccer_uefa_nations_league),
markets h2h+spreads+totals, bookmakers Pinnacle (πρωτο) / Matchbook (δευτερο), regions=eu → 3 credits ανα πραγματικο fetch.
AFCON προκριματικα: ΔΕΝ υπαρχει TOA key → μενουν Nowgoal (intl_dashboard_build fallback).

Fixtures: intl_projections.csv (στηλες comp/utc/home/away/hid/aid, ΜΟΝΟ comp 'NL *'). Αν λειπει → 0 credits + μηνυμα.
Εξοδος: intl_odds_latest.json {scanned_at, sport, odds:{key: {home, away, hid, aid, comp, ko, when, eid, book, h, d, a, line, oh, oa,
        ou_line, over, under, books:{pinnacle:{...}, matchbook:{...}}}}}   key = f'{hid}_{aid}_{utc[:16]}' (οπως στο csv)
        + intl_odds_hist.jsonl (μια γραμμη ανα ΑΛΛΑΓΗ, για CLV) + intl_live_odds.jsonl (in-play εως LIVE_HOURS μετα το ΚΟ).
Συμβαση spreads: TOA 'point' της ομαδας = χαντικαπ της ομαδας (θετικο = παιρνει)· κραταμε line = point ΓΗΠΕΔΟΥΧΟΥ (οπως euro).
Ταιριασμα TOA→FotMob: ALIAS_INTL + fuzzy (norm χωρις τονους) + ΚΟ ±30'.
"""
import os, sys, json, time, datetime, unicodedata, re, csv
from difflib import SequenceMatcher

sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.abspath(__file__))
FIX_F = os.path.join(ROOT, 'intl_projections.csv')
OUT_F = os.path.join(ROOT, 'intl_odds_latest.json')
HIST_F = os.path.join(ROOT, 'intl_odds_hist.jsonl')
LIVE_F = os.path.join(ROOT, 'intl_live_odds.jsonl')

SPORT = 'soccer_uefa_nations_league'     # ενεργο key (επιβεβαιωση 24/9, toa_outrights_fetch.log)
BOOKS = ('pinnacle', 'matchbook')        # σειρα προτεραιοτητας
MARKETS = 'h2h,spreads,totals'
LIVE_HOURS = 2.5     # in-play καταγραφη σε intl_live_odds.jsonl εως 2.5h μετα το ΚΟ (οπως euro)
HOURS_AHEAD = 200    # 8+ μερες μπροστα (trajectory ολου του παραθυρου εθνικων)
HOURS_BACK = 3       # κρατα και ματς που μολις αρχισαν (οπως euro — για συμμετρια gating)
KO_TOL = 1800        # ταιριασμα ΚΟ ±30'
FORCE = os.environ.get('INTL_FORCE') == '1' or os.environ.get('EURO_FORCE') == '1'   # χειροκινητο workflow παρακαμπτει το gating
PRUNE_H = 48         # ποσο κρατιουνται παλιες εγγραφες στο αρχειο
REFRESH_MIN = 45     # μακρια απο ΚΟ (>6h) φτανει ~45λεπτο refresh· <6h καθε τικ

# TOA ονομα -> ονομα FotMob (intl_projections.csv). Προσθηκες οποτε δουμε unmatched στην εξοδο.
ALIAS_INTL = {'Türkiye': 'Turkiye', 'Turkey': 'Turkiye', 'Turkiye': 'Turkiye',
              'Czech Republic': 'Czechia', 'Czechia': 'Czechia',
              'Bosnia and Herzegovina': 'Bosnia and Herzegovina', 'Bosnia': 'Bosnia and Herzegovina', 'Bosnia-Herzegovina': 'Bosnia and Herzegovina',
              'Republic of Ireland': 'Ireland', 'Ireland': 'Ireland', 'Ireland Republic': 'Ireland',
              'North Macedonia': 'North Macedonia', 'Macedonia': 'North Macedonia', 'FYR Macedonia': 'North Macedonia',
              'Faroe Islands': 'Faroe Islands', 'Faroes': 'Faroe Islands',
              'Kosovo': 'Kosovo', 'Northern Ireland': 'Northern Ireland', 'Moldova': 'Moldova', 'Republic of Moldova': 'Moldova',
              'Holland': 'Netherlands', 'Netherlands': 'Netherlands', 'Great Britain': 'England',
              'Georgia': 'Georgia', 'Belarus': 'Belarus', 'Luxembourg': 'Luxembourg', 'Liechtenstein': 'Liechtenstein',
              'San Marino': 'San Marino', 'Gibraltar': 'Gibraltar', 'Andorra': 'Andorra', 'Malta': 'Malta',
              'Cyprus': 'Cyprus', 'Kazakhstan': 'Kazakhstan', 'Azerbaijan': 'Azerbaijan', 'Armenia': 'Armenia',
              'Iceland': 'Iceland', 'Estonia': 'Estonia', 'Latvia': 'Latvia', 'Lithuania': 'Lithuania'}


def _key():
    k = os.environ.get('TOA_KEY')
    if not k:
        raise RuntimeError('TOA_KEY δεν βρεθηκε στο environment.')
    return k


def norm(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'\b(republic|of|the|islands|and)\b', ' ', s)
    return re.sub(r'[^a-z ]', '', s).strip()


def sim(a, b):
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    r = SequenceMatcher(None, na, nb).ratio()
    ta, tb = set(na.split()), set(nb.split())
    tok = len(ta & tb) / max(len(ta | tb), 1)
    return max(r, tok)


def alias(nm):
    """TOA ονομα -> FotMob ονομα (ALIAS_INTL, μετα χωρις τονους)."""
    if nm in ALIAS_INTL:
        return ALIAS_INTL[nm]
    plain = unicodedata.normalize('NFKD', str(nm)).encode('ascii', 'ignore').decode()
    return ALIAS_INTL.get(plain, nm)


def _pdt(s):
    s = str(s)
    if len(s) == 16:                      # 'YYYY-MM-DDTHH:MM' -> UTC
        s += ':00+00:00'
    d = datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))
    return d.replace(tzinfo=datetime.timezone.utc) if d.tzinfo is None else d


def _book(g, bk):
    """Ολες οι κυριες γραμμες ΕΝΟΣ book: {h,d,a,line,oh,oa,ou_line,over,under} (μονο οσα υπαρχουν) ή None.
    line = point του ΓΗΠΕΔΟΥΧΟΥ (χαντικαπ γηπεδουχου, θετικο = παιρνει) — ιδια συμβαση με euro_odds_scan._spread."""
    ht, at = g.get('home_team'), g.get('away_team')
    rec = {}
    for b in g.get('bookmakers', []):
        if b.get('key') != bk:
            continue
        for m in b.get('markets', []):
            key = m.get('key')
            if key == 'h2h':
                h = d = a = None
                for o in m.get('outcomes', []):
                    nm = o.get('name')
                    if nm == ht:
                        h = o.get('price')
                    elif nm == at:
                        a = o.get('price')
                    elif nm and str(nm).lower() == 'draw':
                        d = o.get('price')
                if h and d and a:
                    rec.update(h=round(float(h), 2), d=round(float(d), 2), a=round(float(a), 2))
            elif key == 'spreads':
                hp = ho = ao = None
                for o in m.get('outcomes', []):
                    if o.get('name') == ht:
                        hp = o.get('point'); ho = o.get('price')
                    elif o.get('name') == at:
                        ao = o.get('price')
                if hp is not None and ho and ao:
                    rec.update(line=float(hp), oh=round(float(ho), 2), oa=round(float(ao), 2))
            elif key == 'totals':
                tl = to = tu = None
                for o in m.get('outcomes', []):
                    nm = str(o.get('name', '')).lower()
                    if nm == 'over':
                        tl = o.get('point'); to = o.get('price')
                    elif nm == 'under':
                        tu = o.get('price')
                if tl is not None and to and tu:
                    rec.update(ou_line=float(tl), over=round(float(to), 2), under=round(float(tu), 2))
    return rec or None


FIELDS = ('h', 'd', 'a', 'line', 'oh', 'oa', 'ou_line', 'over', 'under')


def load_fixtures(path=FIX_F):
    """intl_projections.csv -> λιστα fixtures NL: dict(key, comp, ko, home, away, hid, aid). [] αν λειπει."""
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding='utf-8', newline='') as fh:
        for r in csv.DictReader(fh):
            if not str(r.get('comp', '')).startswith('NL'):
                continue
            try:
                ko = _pdt(r['utc'][:16])
                hid, aid = int(float(r['hid'])), int(float(r['aid']))
            except Exception:
                continue
            out.append(dict(key=f"{hid}_{aid}_{r['utc'][:16]}", comp=r['comp'], ko=ko,
                            home=r['home'], away=r['away'], hid=hid, aid=aid))
    return out


def _match(g, cands):
    ht, at = alias(g.get('home_team')), alias(g.get('away_team'))
    best = None; bs = 0.0
    for f in cands:
        s = sim(ht, f['home']) + sim(at, f['away'])
        if s > bs:
            bs, best = s, f
    return best, bs


def process(games, upc, livefx, old, now):
    """ΚΑΘΑΡΗ λογικη (testable χωρις δικτυο): TOA events -> (odds, hist_rows, live_rows, unmatched).
    upc/livefx = λιστες fixtures, old = προηγουμενο odds dict (prune ηδη), now = aware UTC."""
    odds = dict(old); hist_rows = []; live_rows = []; unmatched = []
    for g in games:
        try:
            gko = _pdt(g.get('commence_time'))
        except Exception:
            continue
        # --- LIVE ματς: καταγραφη σε χωριστο append-only αρχειο, ΟΧΙ στο κυριο ---
        lcands = [f for f in livefx if abs((f['ko'] - gko).total_seconds()) <= KO_TOL]
        lbest, lbs = _match(g, lcands)
        if lbest is not None and lbs >= 1.1:
            for bk in BOOKS:
                b = _book(g, bk)
                if b:
                    lr = dict(t=now.isoformat()[:16], key=lbest['key'], book=bk,
                              min_ko=round((now - lbest['ko']).total_seconds() / 60))
                    lr.update(b); live_rows.append(lr)
            continue
        cands = [f for f in upc if abs((f['ko'] - gko).total_seconds()) <= KO_TOL]
        best, bs = _match(g, cands)
        if best is None or bs < 1.1:      # ~0.55 μεσος ορος ανα πλευρα
            if cands:                     # TOA event εκτος παραθυρου μας = οχι πραγματικο mismatch
                unmatched.append(f"{g.get('home_team')} vs {g.get('away_team')} ({bs:.2f})")
            continue
        books = {bk: _book(g, bk) for bk in BOOKS}
        books = {k: v for k, v in books.items() if v}
        if not books:
            continue
        old_rec = odds.get(best['key']) or {}
        rec = dict(home=best['home'], away=best['away'], hid=best['hid'], aid=best['aid'], comp=best['comp'],
                   ko=best['ko'].isoformat()[:16], when=now.isoformat()[:16], eid=g.get('id'), sport=SPORT,
                   toa_home=g.get('home_team'), toa_away=g.get('away_team'))
        # κορυφαια γραμμη = Pinnacle αν εχει, αλλιως Matchbook (ανα πεδιο: αν ο Pinnacle δεν εχει π.χ. totals, το παιρνει απο Matchbook)
        prim = next(bk for bk in BOOKS if bk in books)
        rec['book'] = prim
        for fld in FIELDS:
            for bk in BOOKS:
                if bk in books and books[bk].get(fld) is not None:
                    rec[fld] = books[bk][fld]; break
        rec['books'] = books
        sig = lambda r: tuple(r.get(x) for x in FIELDS)
        if sig(rec) != sig(old_rec):
            row = dict(t=now.isoformat()[:16], key=best['key'], comp=best['comp'], ko=rec['ko'], book=prim)
            row.update({x: rec[x] for x in FIELDS if rec.get(x) is not None})
            hist_rows.append(row)
        odds[best['key']] = rec
    return odds, hist_rows, live_rows, unmatched


def write_out(now, odds, rem=None, unmatched=(), note=None, hist_rows=(), live_rows=()):
    d = dict(scanned_at=now.isoformat()[:16], sport=SPORT, odds=odds, credits_remaining=rem, unmatched=list(unmatched)[:20])
    if note:
        d['note'] = note
    json.dump(d, open(OUT_F, 'w', encoding='utf-8'), ensure_ascii=False)
    if hist_rows:
        with open(HIST_F, 'a', encoding='utf-8') as hf:
            for row in hist_rows:
                hf.write(json.dumps(row, ensure_ascii=False) + '\n')
    if live_rows:
        with open(LIVE_F, 'a', encoding='utf-8') as lf:
            for lr in live_rows:
                lf.write(json.dumps(lr, ensure_ascii=False) + '\n')


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    if now < datetime.datetime(2026, 10, 6, tzinfo=datetime.timezone.utc) and not os.environ.get('EURO_FORCE'):
        print('ΠΑΥΣΗ TOA ως 6/10 (διακοπη εθνικων, Στελιος 24/9) — 0 credits'); return
    fixtures = load_fixtures()
    if not fixtures:
        print('χωρις intl_projections.csv (ή χωρις ματς NL) — τιποτα να κανω, 0 credits')
        return
    old = {}; last = None
    try:
        _o = json.load(open(OUT_F, encoding='utf-8'))
        old = _o.get('odds', {}); last = _o.get('scanned_at')
    except Exception:
        pass
    upc = []; livefx = []
    for f in fixtures:
        dt_s = (f['ko'] - now).total_seconds()
        # ΜΟΝΟ ματς που ΔΕΝ εχουν σεντραρει μπαινουν στο κυριο αρχειο: μετα το ΚΟ η εγγραφη
        # παγωνει στην τελευταια προ-ΚΟ τιμη (= το «κλεισιμο» μας).
        if 0 <= dt_s <= HOURS_AHEAD * 3600:
            upc.append(f)
        elif -LIVE_HOURS * 3600 <= dt_s < 0:
            livefx.append(f)
    # prune παλιες εγγραφες
    odds = {k: v for k, v in old.items()
            if v.get('ko') and (now - _pdt(v['ko'])).total_seconds() < PRUNE_H * 3600}
    if not upc and not livefx:
        print('κανενα ματς εθνικων στο παραθυρο — 0 credits')
        if odds != old or not os.path.exists(OUT_F):     # γραψε μονο αν αλλαξε κατι (αλλιως commit καθε τικ)
            write_out(now, odds, note='no upcoming')
        return
    # gating συχνοτητας: μακρια απο σεντρα φτανει ~45λεπτο refresh· μεσα στο 6ωρο προ ΚΟ καθε scan (κλεισιμο γραμμων)
    try:
        age_min = (now - _pdt(last)).total_seconds() / 60
    except Exception:
        age_min = 1e9
    nearest_h = min([(f['ko'] - now).total_seconds() / 3600 for f in upc] or [1e9])
    if age_min < REFRESH_MIN and nearest_h > 6 and not livefx and not FORCE:
        print(f'φρεσκο αρχειο ({age_min:.0f}λ) και κοντινοτερο ΚΟ σε {nearest_h:.1f}h — skip (0 credits)')
        return
    if not os.environ.get('TOA_KEY'):
        print('TOA_KEY δεν υπαρχει (τοπικο τρεξιμο;) — δεν γινεται fetch, το αρχειο μενει ως εχει')
        return
    import requests
    r = requests.get(f'https://api.the-odds-api.com/v4/sports/{SPORT}/odds',
                     params=dict(apiKey=_key(), regions='eu', markets=MARKETS,
                                 bookmakers=','.join(BOOKS), oddsFormat='decimal'),
                     timeout=45)
    rem = r.headers.get('x-requests-remaining')
    if r.status_code != 200:
        print(f'TOA {r.status_code} — skip ({r.text[:120]})')
        return
    games = r.json()
    odds, hist_rows, live_rows, unmatched = process(games, upc, livefx, odds, now)
    write_out(now, odds, rem=rem, unmatched=unmatched, hist_rows=hist_rows, live_rows=live_rows)
    nmatch = sum(1 for v in odds.values() if v.get('when') == now.isoformat()[:16])
    print(f'ματς στο παραθυρο: {len(upc)} · TOA events {len(games)} · ταιριασαν {nmatch} · hist +{len(hist_rows)} · '
          f'live +{len(live_rows)} · unmatched {len(unmatched)} · credits left {rem}')
    if unmatched:
        print('  unmatched:', '; '.join(unmatched[:8]))
    time.sleep(0.2)


if __name__ == '__main__':
    main()
