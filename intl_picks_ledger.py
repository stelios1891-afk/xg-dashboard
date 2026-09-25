"""
intl_picks_ledger.py — LEDGER ΚΑΝΟΝΙΚΩΝ PICKS ΕΘΝΙΚΩΝ (25/9/2026, αποφαση Στελιου). Τρεχει σε καθε τικ του scanner (μετα το intl_dashboard_build).

Ροες:
  ΣΥΝΑΙΝΕΣΗ = το κανονικο pick (≥2 απο 3 μοντελα, handicap + over) — αυτο που παιζεται.
  Μ1 / Μ2 / Μ3 = καθε μοντελο χωριστα (χαρτινα, για να συνεχισει η συγκριση των μοντελων σε πραγματικα ματς).
Καταγραφη: ΠΡΩΤΗ εμφανιση μεσα στις 72 ωρες πριν τη σεντρα (ωρα, γραμμη, τιμη, βιβλιο, edge). Picks που πρωτοεμφανιζονται στις
  2 τελευταιες ωρες μπαινουν κανονικα, με σημειωση («μπηκε <1 ωρα πριν» / «~1-2 ωρες πριν»).
Εκκαθαριση: μετα τη σεντρα + 2.5 ωρες, με αποτελεσμα FotMob (NL A-D, AFCONQ)· AH με picks.settle, over με intl_pricing.settle_over.
Αρχειο: intl_picks_ledger.jsonl (μια γραμμη ανα pick· ξαναγραφεται ολοκληρο μονο οταν αλλαζει κατι).
"""
import os, sys, json, gzip, time, datetime as dt, urllib.request
sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import picks, intl_pricing, intl_consensus as ic

ROOT = os.path.dirname(os.path.abspath(__file__))
DASH_F = os.path.join(ROOT, 'intl_projections_dashboard.json')
LEDGER_F = os.path.join(ROOT, 'intl_picks_ledger.jsonl')
WINDOW_H = 72
SETTLE_AFTER_H = 2.5
FOTMOB = {'NL A': 9806, 'NL B': 9807, 'NL C': 9808, 'NL D': 9809, 'AFCONQ': 10608}
SEASON = '2026%2F2027'
HDR = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36',
       'Accept': '*/*', 'Referer': 'https://www.fotmob.com/'}


def load_ledger():
    rows = []
    if os.path.exists(LEDGER_F):
        for ln in open(LEDGER_F, encoding='utf-8'):
            if ln.strip():
                rows.append(json.loads(ln))
    return rows


def pick_key(comp, m, stream, p):
    return f"{comp}|{m['home']}|{m['away']}|{m['utc']}|{stream}|{p['mkt']}|{p['side']}"


def new_entries(dash, known, now):
    """Καθαρη λογικη (testable): νεες εγγραφες για picks που εμφανιζονται τωρα μεσα στο παραθυρο και δεν εχουν καταγραφει."""
    out = []
    for c in dash.get('comps', []):
        comp = c['comp']
        for m in c['matches']:
            try:
                ko = dt.datetime.fromisoformat(m['utc']).replace(tzinfo=dt.timezone.utc)
            except Exception:
                continue
            hours = (ko - now).total_seconds() / 3600
            if hours <= 0 or hours > WINDOW_H:
                continue
            streams = [('ΣΥΝΑΙΝΕΣΗ', ic.consensus(m['picks']))] + list(ic.model_picks(m['picks']).items())
            for stream, ps in streams:
                for p in ps:
                    k = pick_key(comp, m, stream, p)
                    if k in known:
                        continue
                    known.add(k)
                    out.append(dict(key=k, stream=stream, comp=comp, home=m['home'], away=m['away'], hid=m.get('hid'), aid=m.get('aid'),
                                    ko=m['utc'], first_seen=now.strftime('%Y-%m-%d %H:%M'), hours_before=round(hours, 1),
                                    mkt=p['mkt'], role=p['role'], side=p['side'], line=p['line'], odds=p['odds'], book=p['book'],
                                    edge=p['edge'], models=p.get('models', stream), label=ic.label(p, m['home'], m['away']),
                                    late=ic.late_note(hours), market_ts=(m.get('market') or {}).get('ts')))
    return out


def settle_row(r, hs, as_):
    gd = hs - as_
    if r['mkt'] == 'OVER':
        return intl_pricing.settle_over(hs + as_, r['line'], r['odds'])
    return picks.settle(gd, 1 if r['side'] == 1 else -1, r['line'], r['odds'])


def fetch_results(comps):
    """{(comp, home, away): (hs, as)} τελειωμενα ματς FotMob της σεζον 2026/27 (μονο οσα comps χρειαζονται)."""
    res = {}
    for comp in comps:
        lid = FOTMOB.get(comp)
        if not lid:
            continue
        try:
            raw = urllib.request.urlopen(urllib.request.Request(f'https://www.fotmob.com/api/data/leagues?id={lid}&season={SEASON}', headers=HDR),
                                         timeout=25).read()
            raw = gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw
            for mm in json.loads(raw).get('fixtures', {}).get('allMatches', []):
                st = mm.get('status', {})
                if st.get('finished') and not st.get('cancelled') and st.get('scoreStr'):
                    h, a = [int(x) for x in st['scoreStr'].replace(' ', '').split('-')[:2]]
                    res[(comp, mm['home']['name'], mm['away']['name'])] = (h, a)
        except Exception as e:
            print(f'  αποτελεσματα {comp}: σφαλμα {str(e)[:60]}', flush=True)
        time.sleep(0.3)
    return res


def main():
    now = dt.datetime.now(dt.timezone.utc)
    try:
        dash = json.load(open(DASH_F, encoding='utf-8'))
    except Exception:
        print('χωρις intl_projections_dashboard.json — τιποτα'); return
    rows = load_ledger(); known = {r['key'] for r in rows}
    add = new_entries(dash, known, now)
    changed = bool(add)
    rows += add
    # εκκαθαριση
    due = [r for r in rows if r.get('result') is None and
           (now - dt.datetime.fromisoformat(r['ko']).replace(tzinfo=dt.timezone.utc)).total_seconds() / 3600 >= SETTLE_AFTER_H]
    if due:
        res = fetch_results(sorted({r['comp'] for r in due}))
        for r in due:
            sc = res.get((r['comp'], r['home'], r['away']))
            if sc:
                r['result'] = f'{sc[0]}-{sc[1]}'; r['pnl'] = round(settle_row(r, *sc), 4); changed = True
    if changed:
        with open(LEDGER_F, 'w', encoding='utf-8') as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + '\n')
    cons = [r for r in rows if r['stream'] == 'ΣΥΝΑΙΝΕΣΗ']; st_ = [r for r in cons if r.get('pnl') is not None]
    print(f'intl ledger: +{len(add)} νεες ({sum(1 for r in add if r["stream"] == "ΣΥΝΑΙΝΕΣΗ")} συναινεσης) · εκκαθαρισμενα συναινεσης {len(st_)}'
          + (f' · ROI {sum(r["pnl"] for r in st_) / len(st_) * 100:+.1f}%' if st_ else '') + f' · συνολο εγγραφων {len(rows)}')


if __name__ == '__main__':
    main()
