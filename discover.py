"""
discover.py  -  ΒΗΜΑ 1 του pipeline: ανακαλυψη νεων finished ματς.

Χτυπαει το FotMob leagues endpoint για καθε λιγκα, βρισκει τα ματς που εχουν
τελειωσει (status.finished) και ενημερωνει το match_index.json, ΧΩΡΙΣ να χαλαει
οσα υπαρχουν ηδη (append-only, dedup).

Χρηση:
    python discover.py 2627                 # top-5, σεζον 2026/27
    python discover.py 2627 EPL LaLiga      # μονο συγκεκριμενες λιγκες
    python discover.py 2627 --all           # top-5 + δευτερευοντα
    python discover.py 2526 --dry           # ΔΟΚΙΜΗ: δειχνει τι θα εκανε, χωρις εγγραφη

Το match_index.json εχει τη μορφη: { "EPL_2526": ["4813374", ...], ... }
"""
import urllib.request, json, gzip, time, sys, os

# Ωστε να τυπωνονται ελληνικα στο Windows console (default cp1252)
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

# ---- ρυθμισεις ----
LEAGUES = {   # ονομα -> FotMob league id
    'EPL': 47, 'LaLiga': 87, 'SerieA': 55, 'Bundesliga': 54, 'Ligue1': 53,
    'Bundesliga2': 146, 'Eredivisie': 57, 'PrimeiraLiga': 61, 'GreeceSL': 135,
    'Belgium': 40, 'ScottishPrem': 64, 'MLS': 130,
}
CORE = ['EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1']          # τα σιγουρα top-5
SECONDARY = ['Bundesliga2', 'Eredivisie', 'PrimeiraLiga', 'GreeceSL', 'Belgium', 'MLS']

INDEX_PATH = 'match_index.json'

hdr = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                     '(KHTML, like Gecko) Chrome/120 Safari/537.36',
       'Accept': '*/*', 'Referer': 'https://www.fotmob.com/'}


def get(url, tries=3):
    for i in range(tries):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers=hdr), timeout=25).read()
            if raw[:2] == b'\x1f\x8b':
                raw = gzip.decompress(raw)
            return raw
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(1.5 * (i + 1))


def season_url(code):
    """'2627' -> '2026%2F2027' (μορφη που θελει το FotMob leagues endpoint)."""
    if len(code) != 4 or not code.isdigit():
        raise ValueError(f"Λαθος κωδικος σεζον: {code!r} (περιμενα π.χ. 2627)")
    a = 2000 + int(code[:2])
    b = 2000 + int(code[2:])
    return f'{a}%2F{b}'


def discover_league(name, code):
    """Επιστρεφει (finished_ids, total_matches, sample_desc) για μια λιγκα-σεζον."""
    lid = LEAGUES[name]
    url = f'https://www.fotmob.com/api/data/leagues?id={lid}&season={season_url(code)}'
    d = json.loads(get(url))
    am = d.get('fixtures', {}).get('allMatches', [])
    finished = []
    latest = None  # (utcTime, "Home v Away sc") του πιο προσφατου finished, για επιβεβαιωση
    for m in am:
        st = m.get('status', {})
        if st.get('finished') and not st.get('cancelled') and not st.get('awarded'):
            finished.append(str(m['id']))
            ut = st.get('utcTime', '')
            desc = f"{m['home']['name']} {st.get('scoreStr','?')} {m['away']['name']}  ({ut[:10]})"
            if latest is None or ut > latest[0]:
                latest = (ut, desc)
    return finished, len(am), (latest[1] if latest else '-')


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    code = args[0]
    flags = [a for a in args[1:] if a.startswith('--')]
    names = [a for a in args[1:] if not a.startswith('--')]
    dry = '--dry' in flags
    if '--all' in flags:
        names = CORE + SECONDARY
    elif not names:
        names = CORE

    idx = {}
    if os.path.exists(INDEX_PATH):
        idx = json.load(open(INDEX_PATH, encoding='utf-8'))

    print(f"{'DRY-RUN ' if dry else ''}discover  σεζον={code}  λιγκες={','.join(names)}\n")
    print(f"{'League':14s} {'FotMob':>7s} {'finished':>9s} {'στο index':>10s} {'ΝΕΑ':>5s}   τελευταιο finished")
    print('-' * 100)

    changed = False
    total_new = 0
    for name in names:
        key = f'{name}_{code}'
        try:
            finished, total, latest = discover_league(name, code)
        except Exception as e:
            print(f"{name:14s}  ΣΦΑΛΜΑ: {type(e).__name__} {str(e)[:60]}")
            continue
        existing = idx.get(key, [])
        existing_set = set(map(str, existing))
        new_ids = [i for i in finished if i not in existing_set]
        # append-only merge, διατηρωντας σειρα: παλια + νεα (dedup)
        merged = list(existing) + [i for i in new_ids]
        if new_ids and not dry:
            idx[key] = merged
            changed = True
        total_new += len(new_ids)
        print(f"{name:14s} {total:>7d} {len(finished):>9d} {len(existing):>10d} {len(new_ids):>5d}   {latest}")
        time.sleep(0.3)

    print('-' * 100)
    print(f"Συνολικα νεα finished ματς: {total_new}")
    if dry:
        print("(DRY-RUN: δεν γραφτηκε τιποτα στο match_index.json)")
    elif changed:
        json.dump(idx, open(INDEX_PATH, 'w', encoding='utf-8'))
        print(f"Ενημερωθηκε το {INDEX_PATH}.")
    else:
        print("Καμια αλλαγη - το index ειναι ηδη ενημερωμενο.")


if __name__ == '__main__':
    main()
