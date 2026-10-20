# -*- coding: utf-8 -*-
"""nba_injrep_fetch.py — ΙΣΤΟΡΙΚΟ ΕΠΙΣΗΜΩΝ NBA INJURY REPORTS (20/10/2026, Στελιος: «αμφιβολοι στο ανοιγμα ως πιο πιθανοι εξω» +
«πως χειριζομαστε απουσιες που βγαινουν μεσα στη μερα» → χρειαζεται ΩΡΑ καθε ειδησης).
Πηγη: https://ak-static.cms.nba.com/referee/injury/Injury-Report_YYYY-MM-DD_HHAM|PM.pdf (ωριαια, 2021-22+).
Κατεβαζει ωρες 08AM..11PM ET καθε μερας κανονικης περιοδου, διαβαζει (pdfplumber), κρατα ΜΟΝΟ γραμμες (το PDF σβηνεται).
Εξοδος: nba_injrep/rows_{σεζον}.csv: rep_ts (ET, απο τον τιτλο), file_h, game_date, game_time_et, matchup, team, player, key, status, reason
  key = ονομα χωρις κενα/σημεια/Jr. (για ταιριασμα με box score). Συνεχιζει απο οπου σταματησε (nba_injrep/done_{σεζον}.txt).
Χρηση: python -I nba_injrep_fetch.py [σεζον...]   (σεζον = ετος ληξης, π.χ. 2022 = 2021-22)"""
import os, re, sys, csv, time, datetime as dt, urllib.request, concurrent.futures as cf
import pdfplumber
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(ROOT, 'nba_injrep'); TMP = os.path.join(OUT, 'pdf_tmp')
os.makedirs(TMP, exist_ok=True)
URL = 'https://ak-static.cms.nba.com/referee/injury/Injury-Report_{d}_{h}.pdf'
HOURS = ['08AM', '11AM', '01PM', '03PM', '05PM', '06PM', '07PM', '08PM', '09PM', '10PM', '11PM']   # 20/10: 11/μερα (ηταν 16) — ευγενικο ρυθμο
SEASON_DAYS = {2022: ('2021-10-19', '2022-04-10'), 2023: ('2022-10-18', '2023-04-09'), 2024: ('2023-10-24', '2024-04-14'),
               2025: ('2024-10-22', '2025-04-13'), 2026: ('2025-10-21', '2026-04-12')}
TEAMS = dict(AtlantaHawks='ATL', BostonCeltics='BOS', BrooklynNets='BRK', CharlotteHornets='CHO', ChicagoBulls='CHI', ClevelandCavaliers='CLE',
             DallasMavericks='DAL', DenverNuggets='DEN', DetroitPistons='DET', GoldenStateWarriors='GSW', HoustonRockets='HOU', IndianaPacers='IND',
             LAClippers='LAC', LosAngelesLakers='LAL', MemphisGrizzlies='MEM', MiamiHeat='MIA', MilwaukeeBucks='MIL', MinnesotaTimberwolves='MIN',
             NewOrleansPelicans='NOP', NewYorkKnicks='NYK', OklahomaCityThunder='OKC', OrlandoMagic='ORL', Philadelphia76ers='PHI', PhoenixSuns='PHO',
             PortlandTrailBlazers='POR', SacramentoKings='SAC', SanAntonioSpurs='SAS', TorontoRaptors='TOR', UtahJazz='UTA', WashingtonWizards='WAS')
TEAM_RE = re.compile('(' + '|'.join(sorted(TEAMS, key=len, reverse=True)) + ')')
ST = r'(Out|Questionable|Doubtful|Probable|Available)'
PL_RE = re.compile(r"([A-Za-zÀ-ž.'\-]+,[A-Za-zÀ-ž.'\-]+)\s+" + ST + r'\b\s*(.*)$')
GM_RE = re.compile(r'(\d\d/\d\d/\d{4})?\s*(\d\d:\d\d\s*\(ET\))?\s*([A-Z]{2,3}@[A-Z]{2,3})\s*(.*)$')   # 20/10: ωρα προαιρετικη (ματς στην ιδια ωρα)
HDR_RE = re.compile(r'Injury Report:\s*(\d\d/\d\d/\d\d)\s+(\d\d:\d\d\s*[AP]M)')
SUF = re.compile(r'(Jr\.?|Sr\.?|III|II|IV)$')

def key(raw):
    last, first = raw.split(',', 1)
    last = SUF.sub('', last)
    import unicodedata
    s = unicodedata.normalize('NFD', first + last); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    return re.sub(r'[^a-z]', '', s)

def parse(path):
    rows = []; rep = None; gd = gt = mu = tm = None
    with pdfplumber.open(path) as pdf:
        for pg in pdf.pages:
            for ln in (pg.extract_text() or '').split('\n'):
                ln = ln.strip()
                m = HDR_RE.search(ln)
                if m: rep = f'{m.group(1)} {m.group(2)}'; continue
                m = GM_RE.match(ln)
                if m:
                    if m.group(1): gd = m.group(1)
                    if m.group(2): gt = m.group(2).replace(' ', '')
                    mu, ln, tm = m.group(3), m.group(4), None
                m = TEAM_RE.match(ln)
                if m: tm = TEAMS[m.group(1)]; ln = ln[m.end():].strip()
                m = PL_RE.search(ln)
                if m and tm:
                    rows.append([rep, gd, gt, mu, tm, m.group(1), key(m.group(1)), m.group(2), m.group(3)[:60]])
    return rows

CANARY = 'https://ak-static.cms.nba.com/referee/injury/Injury-Report_2024-01-15_05PM.pdf'
def blocked():
    try:
        urllib.request.urlopen(urllib.request.Request(CANARY, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30); return False
    except Exception:
        return True

def fetch_one(d, h):
    p = os.path.join(TMP, f'{d}_{h}.pdf')
    # 21/10: απο ~22/12/2025 το NBA αλλαξε ονομα αρχειου: 05PM → 05_00PM (αναφορες ανα 15′). Δοκιμαζει πρωτα τη μορφη που ισχυει την ημερα.
    alt = h[:2] + '_00' + h[2:]
    forms = [alt, h] if d >= '2025-12-21' else [h, alt]
    for k_, hh in enumerate(forms):
        u = URL.format(d=d, h=hh)
        try:
            urllib.request.urlopen(urllib.request.Request(u, method='HEAD', headers={'User-Agent': 'Mozilla/5.0'}), timeout=30); break
        except urllib.error.HTTPError as e:
            if e.code not in (403, 404) or k_ == len(forms) - 1: u = URL.format(d=d, h=forms[0])
        except Exception:
            u = URL.format(d=d, h=forms[0]); break
    for att in range(3):
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=40)
            open(p, 'wb').write(r.read()); break
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                return d, h, ('BLOCK' if blocked() else None)   # 20/10: ο CDN δινει 403 ΚΑΙ για «δεν υπαρχει» ΚΑΙ οταν μας μπλοκαρει
            time.sleep(2 + 3 * att)
        except Exception:
            time.sleep(2 + 3 * att)
    else:
        return d, h, 'ERR'
    try: rows = parse(p)
    except Exception as e: rows = 'ERR'
    try: os.remove(p)
    except Exception: pass
    return d, h, rows

def run(season):
    a, b = SEASON_DAYS[season]; d0 = dt.date.fromisoformat(a); d1 = dt.date.fromisoformat(b)
    done_f = os.path.join(OUT, f'done_{season}.txt'); done = set(open(done_f).read().split()) if os.path.exists(done_f) else set()
    jobs = []; d = d0
    while d <= d1:
        for h in HOURS:
            if f'{d}_{h}' not in done: jobs.append((str(d), h))
        d += dt.timedelta(days=1)
    print(f'{season}: {len(jobs)} αναφορες να κατεβουν ({len(done)} ηδη)', flush=True)
    csv_f = os.path.join(OUT, f'rows_{season}.csv'); new = not os.path.exists(csv_f)
    n = 0; waits = 0
    with open(csv_f, 'a', newline='', encoding='utf-8') as fh, open(done_f, 'a') as dfh:
        w = csv.writer(fh)
        if new: w.writerow(['rep_ts', 'game_date', 'game_time_et', 'matchup', 'team', 'player', 'key', 'status', 'reason', 'file_d', 'file_h'])
        for d_, h_ in jobs:
            while True:
                _, _, rows = fetch_one(d_, h_)
                if rows != 'BLOCK': break
                waits += 1; fh.flush(); dfh.flush()
                print(f'  ΜΠΛΟΚ απο τον server ({d_} {h_}) — αναμονη 15′ (#{waits})', flush=True)
                if waits > 12: print('  σταματαω — ξανατρεξε αργοτερα (συνεχιζει απο εδω)', flush=True); return
                time.sleep(900)
            n += 1
            if rows != 'ERR':
                for r in (rows or []): w.writerow(r + [d_, h_])
                dfh.write(f'{d_}_{h_}\n')
            if n % 100 == 0: fh.flush(); dfh.flush(); print(f'  {season}: {n}/{len(jobs)}', flush=True)
            time.sleep(1.5)
    print(f'{season}: ΤΕΛΟΣ', flush=True)

if __name__ == '__main__':
    if sys.argv[1:2] == ['--test']:
        for r in parse(sys.argv[2])[:12]: print(r)
        print('γραμμες:', len(parse(sys.argv[2]))); sys.exit()
    for s in [int(x) for x in sys.argv[1:]] or sorted(SEASON_DAYS):
        run(s)
