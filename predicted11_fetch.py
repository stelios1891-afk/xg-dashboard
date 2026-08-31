# -*- coding: utf-8 -*-
"""
predicted11_fetch.py — Συλλεκτης projected lineups απο predicted11.com (LaLiga + Premier).

Ανα ματς: 2x11 προβλεπομενοι παικτες (ονομα + site id + συντεταγμενες) -> ταιριασμα
με τα δικα μας ρόστερ (lineup_lab.json) -> προσθηκη στο projected_lineups.jsonl με
χρονοσημανση. Ξανατρεξιμο = νεο snapshot (κραταμε ολα τα στιγμιοτυπα — η εξελιξη
της προβλεψης ειναι απο μονη της πληροφορια).
"""
import sys, os, json, re, gzip, time, datetime, unicodedata, urllib.request
sys.stdout.reconfigure(encoding='utf-8')

LEAGUES = {'laliga': 'LaLiga', 'premier-league': 'EPL'}
OUT = 'projected_lineups.jsonl'
HDR = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36',
       'Accept': 'text/html,*/*', 'Accept-Encoding': 'gzip'}


def get(u):
    r = urllib.request.urlopen(urllib.request.Request(u, headers=HDR), timeout=25)
    d = r.read()
    if d[:2] == b'\x1f\x8b':
        d = gzip.decompress(d)
    return d.decode('utf-8', 'replace')


def norm(s):
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    return set(re.findall(r'[a-z]{2,}', s))


LAB = json.load(open('lineup_lab.json', encoding='utf-8'))


def team_lookup(lg, name_tokens):
    """Βρες tid της ομαδας στη βαση μας με token overlap."""
    best, bs = None, 0.0
    for tid, t in LAB['teams'].items():
        if t['lg'] != lg:
            continue
        tt = norm(t['name'])
        ov = len(name_tokens & tt)
        if ov and (ov + 0.01 * len(tt & name_tokens)) > bs:
            best, bs = tid, ov + 0.01 * len(tt & name_tokens)
    return best


def player_lookup(tid, site_name):
    """Ταιριασε ονομα του site με παικτη του ροστερ μας (μεσα στην ομαδα)."""
    if not tid:
        return None
    toks = norm(site_name)
    best, bs = None, 0
    for p in LAB['teams'][tid]['players']:
        ov = len(toks & norm(p['nm']))
        if ov > bs:
            best, bs = p['id'], ov
    return best if bs >= 1 else None


def discover(slug):
    """Ολα τα links ματς της λιγκας (απο league page + απο μια σελιδα ματς)."""
    urls = set()
    for page in (f'https://www.predicted11.com/es/{slug}',):
        try:
            h = get(page)
            urls |= set(re.findall(rf'https://www\.predicted11\.com/es/{slug}/partido/[a-z0-9-]+', h))
            urls |= {f'https://www.predicted11.com{u}' for u in
                     re.findall(rf'href="(/es/{slug}/partido/[a-z0-9-]+)"', h)}
        except Exception as e:
            print(f'  {slug}: discovery σφαλμα {type(e).__name__}', flush=True)
    if urls:  # απο μια σελιδα ματς παρε ολη την αγωνιστικη
        try:
            h = get(sorted(urls)[0])
            urls |= set(re.findall(rf'https://www\.predicted11\.com/es/{slug}/partido/[a-z0-9-]+', h))
        except Exception:
            pass
    return sorted(urls)


def parse_match(url, lg):
    h = get(url)
    # kickoff
    mko = re.search(r'Fecha: (\d{4}-\d{2}-\d{2}) a las (\d{2}:\d{2})', h)
    ko = f'{mko.group(1)}T{mko.group(2)}' if mko else None
    # ονοματα ομαδων απο τον τιτλο: "del Betis vs Real Madrid"
    mt = re.search(r'probables del (.+?) vs (.+?) para', h)
    home_nm, away_nm = (mt.group(1), mt.group(2)) if mt else (None, None)
    # 22 player blocks με τη σειρα: 11 γηπεδουχος, 11 φιλοξενουμενη
    blocks = re.findall(r'player-on-field player-appear[^>]*data-id="(\d+)".*?alt="([^"]+)"', h, re.S)
    if len(blocks) < 22:
        return None
    def best_team(bl, hint_tokens):
        """Διαλεξε ομαδα της λιγκας με το ΡΟΣΤΕΡ που ταιριαζει τους περισσοτερους απο τους 11."""
        best, bs = None, -1
        for tid, t in LAB['teams'].items():
            if t['lg'] != lg:
                continue
            hits = sum(1 for _, nm in bl if player_lookup(tid, nm))
            score = hits + 0.5 * len(hint_tokens & norm(t['name']))
            if score > bs:
                best, bs = tid, score
        return best

    tid_h = best_team(blocks[:11], norm(home_nm or ''))
    tid_a = best_team(blocks[11:22], norm(away_nm or ''))

    def side(bl, tid):
        out = []
        for sid, nm in bl:
            out.append(dict(nm=nm.strip(), site_id=sid, pid=player_lookup(tid, nm)))
        return out
    return dict(ts=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='minutes'),
                src='predicted11', lg=lg, url=url, ko=ko,
                home=home_nm, away=away_nm, home_tid=tid_h, away_tid=tid_a,
                xi_home=side(blocks[:11], tid_h), xi_away=side(blocks[11:22], tid_a))


if __name__ == '__main__':
    n = 0
    with open(OUT, 'a', encoding='utf-8') as fh:
        for slug, lg in LEAGUES.items():
            urls = discover(slug)
            print(f'{lg}: {len(urls)} ματς', flush=True)
            for u in urls:
                try:
                    rec = parse_match(u, lg)
                except Exception as e:
                    print(f'  {u.rsplit("/",1)[-1]}: {type(e).__name__}', flush=True)
                    continue
                if rec:
                    fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
                    ok_h = sum(1 for p in rec['xi_home'] if p['pid'])
                    ok_a = sum(1 for p in rec['xi_away'] if p['pid'])
                    print(f'  {rec.get("home")} - {rec.get("away")}: ταιριασμα {ok_h}/11 + {ok_a}/11', flush=True)
                    n += 1
                time.sleep(0.8)
    print(f'ΤΕΛΟΣ: {n} projected lineups αποθηκευτηκαν')
