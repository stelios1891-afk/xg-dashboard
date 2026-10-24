# -*- coding: utf-8 -*-
"""nba_rw_lineups.py — ΚΑΤΑΣΤΑΣΕΙΣ ΠΑΙΚΤΩΝ ΑΠΟ ΤΗ ΣΕΛΙΔΑ ΠΕΝΤΑΔΩΝ ΤΟΥ ROTOWIRE (24/10/2026, Στελιος «ναι ετσι μετρα το»).
Γιατι: ομαδες στο 2ο ματς back-to-back δηλωνουν στην επισημη αναφορα μονο ως τις 13:00 τοπικη ωρα της ημερας του ματς· ως τοτε ειχαμε
μονο ESPN, οπου «Day-To-Day» = παιζει (π.χ. 24/10 VanVleet: ESPN DTD, RotoWire Out). Το RotoWire γραφει Out/Doubt/Ques/Prob πολυ νωριτερα.
Πηγη: rotowire.com/basketball/nba-lineups.php (σημερα) + ?date=tomorrow (δωρεαν, ενα αιτημα η καθε σελιδα).
ΚΡΑΤΑΜΕ ΤΟ ΣΗΜΑ (Out/Doubt/Ques/Prob/OFS/GTD/Susp) → καταστασεις της επισημης αναφορας και ΙΔΙΕΣ πιθανοτητες (nba_injrep_live.PROB).
Το ποσοστο «θα παιξει» του RotoWire (τελεια 0/25/50/75/100) αποθηκευεται μονο για πληροφορια — εχει αντιφασεις με το σημα (Adams Doubt/100%).
Σειρα πηγων (nba_injrep_live.Official): επισημη αναφορα (οταν η ομαδα εχει δηλωσει) → RotoWire → ESPN.
Εξοδος: nba_rw_lineups.json (τελευταιο) + nba_rw_lineups_hist.jsonl (καθε αλλαγη, για ελεγχο)."""
import os, re, json, html, datetime as dt, urllib.request
ROOT = os.path.dirname(os.path.abspath(__file__))
F = lambda n: os.path.join(ROOT, n)
STATE, HIST = 'nba_rw_lineups.json', 'nba_rw_lineups_hist.jsonl'
PAGES = ('https://www.rotowire.com/basketball/nba-lineups.php', 'https://www.rotowire.com/basketball/nba-lineups.php?date=tomorrow')
_H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0'}
TEAM = {'CHA': 'CHO', 'BKN': 'BRK', 'PHX': 'PHO', 'NY': 'NYK', 'GS': 'GSW', 'SA': 'SAS', 'NO': 'NOP', 'UTAH': 'UTA', 'WSH': 'WAS'}
TAG = {'out': 'Out', 'ofs': 'Out', 'susp': 'Out', 'doubt': 'Doubtful', 'ques': 'Questionable', 'gtd': 'Questionable', 'prob': 'Probable'}
MONTHS = {m: i + 1 for i, m in enumerate(('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'))}


def _load(n, d):
    try:
        with open(F(n), encoding='utf-8') as fh: return json.load(fh)
    except Exception: return d


def parse(s):
    """HTML σελιδας → (ημερα ΗΠΑ 'YYYY-MM-DD' ή None, [dict(away, home, time, players=[[ομαδα, ονομα, σημα, κατασταση, ποσοστο]])])"""
    m = re.search(r'(' + '|'.join(MONTHS) + r') (\d{1,2}), (20\d\d)', s)
    gd = dt.date(int(m.group(3)), MONTHS[m.group(1)], int(m.group(2))).isoformat() if m else None
    games = []
    for b in s.split('class="lineup is-nba')[1:]:
        ab = re.findall(r'class="lineup__abbr">([A-Z]+)<', b)
        if len(ab) < 2: continue
        away, home = (TEAM.get(x, x) for x in ab[:2])
        tm = re.search(r'lineup__time">([^<]+)<', b)
        parts = b.split('<ul class="lineup__list is-home">')
        seen, P = set(), []
        for team, ul in zip((away, home), parts[:2]):
            for x in re.finditer(r'is-pct-play-(\d+)[^"]*"\s+title="[^"]*">.*?<a title="([^"]+)"[^>]*>.*?</a>\s*(?:<span class="lineup__inj">([^<]+)</span>)?', ul, re.S):
                pct, nm, tag = int(x.group(1)), html.unescape(x.group(2)), (x.group(3) or '').strip()
                stt = TAG.get(tag.lower())
                if not stt or (team, nm) in seen: continue
                seen.add((team, nm)); P.append([team, nm, tag, stt, pct])
        games.append(dict(away=away, home=home, time=tm.group(1).strip() if tm else None, players=P))
    return gd, games


def refresh(now=None):
    """Κατεβαζει σημερα + αυριο → nba_rw_lineups.json. Σε σφαλμα κραταει το παλιο (με το παλιο fetched → γινεται «παλιο» μονο του)."""
    now = now or dt.datetime.now(dt.timezone.utc)
    S = _load(STATE, {}); pages, errs = [], []
    for u in PAGES:
        try:
            s = urllib.request.urlopen(urllib.request.Request(u, headers=_H), timeout=30).read().decode('utf-8', 'ignore')
            gd, games = parse(s)
            if gd and games: pages.append(dict(date=gd, games=games))
        except Exception as e: errs.append(f'{type(e).__name__}: {str(e)[:120]}')
    if not pages:
        S['error'] = '; '.join(errs) or 'κενη σελιδα'; S['checked'] = now.isoformat(timespec='minutes')
        json.dump(S, open(F(STATE), 'w', encoding='utf-8'), ensure_ascii=False)
        return f"σφαλμα — κραταω την παλια ({S.get('fetched', '—')}): {S['error']}"
    old = json.dumps(S.get('pages'), sort_keys=True, ensure_ascii=False)
    S = dict(fetched=now.isoformat(timespec='minutes'), checked=now.isoformat(timespec='minutes'), pages=pages)
    json.dump(S, open(F(STATE), 'w', encoding='utf-8'), ensure_ascii=False)
    if json.dumps(pages, sort_keys=True, ensure_ascii=False) != old:
        with open(F(HIST), 'a', encoding='utf-8') as fh: fh.write(json.dumps(S, ensure_ascii=False) + '\n')
    n = sum(len(g['players']) for p in pages for g in p['games'])
    return ' · '.join(f"{p['date']}: {len(p['games'])} ματς" for p in pages) + f' · {n} παικτες με σημα'


def age_min(now=None):
    S = _load(STATE, {})
    if not S.get('fetched'): return None
    now = now or dt.datetime.now(dt.timezone.utc)
    return (now - dt.datetime.fromisoformat(S['fetched'])).total_seconds() / 60


def by_team(now=None, stale_min=180):
    """{(ομαδα, ημερα ΗΠΑ): {ονομα: (κατασταση, σημα, ποσοστο)}} για ΟΛΕΣ τις ομαδες που εχουν ματς στη σελιδα (και χωρις τραυματιες)
    — κενο αν το αρχειο ειναι παλιο (> stale_min)."""
    a = age_min(now)
    if a is None or a > stale_min: return {}
    out = {}
    for p in _load(STATE, {}).get('pages', []):
        for g in p['games']:
            for t in (g['away'], g['home']): out.setdefault((t, p['date']), {})
            for team, nm, tag, stt, pct in g['players']: out[(team, p['date'])][nm] = (stt, tag, pct)
    return out


if __name__ == '__main__':
    import sys; sys.stdout.reconfigure(encoding='utf-8')
    print(refresh())
    for (t, d), v in sorted(by_team().items()):
        print(d, t, {k: x[1] for k, x in v.items()})
