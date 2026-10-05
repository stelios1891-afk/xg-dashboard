"""
coach_flags.py — 5/10/2026 (Στελιος «ναι»): ΑΛΛΑΓΗ ΠΡΟΠΟΝΗΤΗ στα LIVE εγχωρια (CORE7). Ιδια λογικη με manager_study.py / manager_picks_test.py.
1. Τραβαει τον προπονητη καθε ΤΕΛΕΙΩΜΕΝΟΥ φετινου ματς (FotMob matchDetails → lineup.coach) → managers_2627.json (μονο τα νεα· resumable).
2. Χρονολογιο ανα ομαδα (περσι + φετος): προπονητης, γκολ, npxG. ΚΑΘΑΡΙΣΜΑ: «σεκανς» ≤2 ματς αναμεσα στον ΙΔΙΟ προπονητη = ο βοηθος
   στον παγκο (τιμωρια/ασθενεια) → αγνοειται. Μεταβατικος = σεκανς ≤4 ματς αναμεσα σε ΔΙΑΦΟΡΕΤΙΚΟΥΣ.
3. Για καθε ομαδα: τελευταια αλλαγη ΜΕΣΑ στη φετινη σεζον → ποσα ματς εχουν παιχτει απο τοτε, μεταβατικος ή μονιμος, και ΤΥΠΟΣ του σεριου
   πριν την αλλαγη (8 ματς): τυχη = μεσος (διαφορα γκολ − διαφορα npxG) → «ατυχη» ≤ −0.35 · «τυχερη» ≥ +0.20 · αλλιως «κακη και στα δυο».
   + καλοκαιρινη αλλαγη (αλλος προπονητης στο 1ο φετινο απο το τελευταιο περσινο).
4. → coach_flags.json (το διαβαζουν ο scanner — φιλτρο — και το dashboard — καρτες).
ΦΙΛΤΡΟ (manager_picks_test 5/10, περασε προ-δηλωση): ΟΧΙ pick αουτσαιντερ 15η+ ΥΠΕΡ ομαδας στα 1-8 πρωτα ματς μετα απο αλλαγη μεσα στη σεζον,
αν πριν την αλλαγη ηταν «κακη και στα δυο». Τα κομμενα γραφονται στο coach_filter_log.jsonl (για ελεγχο σε μια σεζον).
Χρηση: python coach_flags.py          (fetch + build)   ·   python coach_flags.py --no-fetch
"""
import os, sys, json, gzip, time, urllib.request, datetime as dt
ROOT = os.path.dirname(os.path.abspath(__file__))
CUR, PREV = '2627', '2526'
LG = ['EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'PrimeiraLiga', 'Eredivisie']
MG_CUR = os.path.join(ROOT, 'managers_2627.json'); MG_ALL = os.path.join(ROOT, 'managers_all.json')
OUT = os.path.join(ROOT, 'coach_flags.json'); LOG = os.path.join(ROOT, 'coach_filter_log.jsonl')
HDR = {'User-Agent': 'Mozilla/5.0', 'Accept': '*/*', 'Referer': 'https://www.fotmob.com/'}
LUCK_UNLUCKY, LUCK_LUCKY, WINDOW, FILTER_MIN_MD = -0.35, 0.20, 8, 15

def _load(p, default):
    try: return json.load(open(p, encoding='utf-8'))
    except Exception: return default

def fetch_coaches():
    cache = _load(MG_CUR, {}); new = 0
    for lg in LG:
        d = _load(os.path.join(ROOT, f'data_{lg}_{CUR}.json'), {})
        for mid, m in d.items():
            if m.get('hs') is None or (mid in cache and cache[mid]): continue
            for i in range(3):
                try:
                    raw = urllib.request.urlopen(urllib.request.Request(f'https://www.fotmob.com/api/data/matchDetails?matchId={mid}', headers=HDR), timeout=25).read()
                    if raw[:2] == b'\x1f\x8b': raw = gzip.decompress(raw)
                    lu = json.loads(raw).get('content', {}).get('lineup') or {}
                    out = {}
                    for side, k in (('homeTeam', 'h'), ('awayTeam', 'a')):
                        c = (lu.get(side) or {}).get('coach') or {}
                        if isinstance(c, dict) and c.get('id'): out[k] = [c['id'], c.get('name')]
                    cache[mid] = out or None; new += 1; break
                except Exception:
                    time.sleep(1 + i)
            time.sleep(0.25)
    json.dump(cache, open(MG_CUR, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'προπονητες: {new} νεα ματς · συνολο {len(cache)}')

def timelines():
    mg = dict(_load(MG_ALL, {})); mg.update(_load(MG_CUR, {}))
    T = {}
    for lg in LG:
        for sea in (PREV, CUR):
            d = _load(os.path.join(ROOT, f'data_{lg}_{sea}.json'), {})
            for mid, m in d.items():
                if m.get('hs') is None: continue
                H, A = int(m['home']['id']), int(m['away']['id']); c = mg.get(str(mid)) or {}
                x = {t: sum((s.get('xg') or 0) for s in (m.get('shots') or []) if s.get('tid') == t and s.get('sit') != 'Penalty') for t in (H, A)}
                when = dt.datetime.strptime(m['date'].replace(' UTC', ''), '%a, %b %d, %Y, %H:%M')
                for t, o, gf, ga, cc, nm in ((H, A, m['hs'], m['as'], c.get('h'), m['home']['name']), (A, H, m['as'], m['hs'], c.get('a'), m['away']['name'])):
                    T.setdefault(t, []).append(dict(date=when, sea=sea, lg=lg, mid=str(mid), name=nm, coach=(cc or [None])[0], coach_nm=(cc or [None, None])[1],
                                                    gd=gf - ga, xgd=x[t] - x[o]))
    for t in T: T[t].sort(key=lambda r: r['date'])
    return T

def runs_of(g):
    co = [r['coach'] for r in g]
    for i in range(1, len(co)):                       # ffill/bfill αγνωστου
        if co[i] is None: co[i] = co[i - 1]
    for i in range(len(co) - 2, -1, -1):
        if co[i] is None: co[i] = co[i + 1]
    runs = []
    for i, c in enumerate(co):
        if runs and runs[-1][0] == c: runs[-1][2] += 1
        else: runs.append([c, i, 1])
    changed = True
    while changed:
        changed = False
        for j in range(1, len(runs) - 1):
            if runs[j][2] <= 2 and runs[j - 1][0] == runs[j + 1][0]:
                runs[j - 1][2] += runs[j][2] + runs[j + 1][2]; del runs[j:j + 2]; changed = True; break
    return runs

def build():
    T = timelines(); teams = {}
    nm_of = lambda g, idx: next((r['coach_nm'] for r in g[idx:] if r['coach_nm']), None)
    for t, g in T.items():
        cur_idx = [i for i, r in enumerate(g) if r['sea'] == CUR]
        if not cur_idx: continue
        runs = runs_of(g); info = dict(name=g[-1]['name'], lg=g[-1]['lg'], coach=nm_of(g, len(g) - 1) or g[-1]['coach_nm'], played=len(cur_idx))
        # καλοκαιρινη αλλαγη
        prv = [i for i, r in enumerate(g) if r['sea'] == PREV]
        if prv:
            run_at = lambda i: next(rr[0] for rr in runs if rr[1] <= i < rr[1] + rr[2])
            info['summer_new'] = run_at(prv[-1]) != run_at(cur_idx[0])
        # τελευταια αλλαγη μεσα στη φετινη σεζον
        ev = None
        for j in range(1, len(runs)):
            prv_r, cur_r = runs[j - 1], runs[j]
            if prv_r[2] <= 4 and j >= 2 and runs[j - 2][0] != cur_r[0]: continue
            k = cur_r[1]
            if g[k]['sea'] != CUR or g[k - 1]['sea'] != CUR: continue
            ev = (j, k)
        if ev:
            j, k = ev; cur_r = runs[j]
            ongoing = j == len(runs) - 1
            caretaker = (cur_r[2] <= 4 and not ongoing)
            pre = g[max(0, k - WINDOW):k]
            luck = sum(r['gd'] - r['xgd'] for r in pre) / len(pre)
            typ = 'unlucky' if luck <= LUCK_UNLUCKY else ('lucky' if luck >= LUCK_LUCKY else 'bad_both')
            since = len(g) - k                                    # ματς που εχουν παιχτει μετα την αλλαγη
            info.update(change=dict(date=g[k]['date'].strftime('%Y-%m-%d'), old=nm_of(g, max(0, k - 1)) if False else next((r['coach_nm'] for r in reversed(g[:k]) if r['coach_nm']), None),
                                    first=g[k]['coach_nm'], caretaker_first=caretaker, perm=nm_of(g, runs[j + 1][1]) if caretaker else g[k]['coach_nm'],
                                    played_since=since, next_match_no=since + 1, pre_luck=round(luck, 3), pre_gd=round(sum(r['gd'] for r in pre) / len(pre), 2),
                                    pre_xgd=round(sum(r['xgd'] for r in pre) / len(pre), 2), type=typ))
        teams[str(t)] = info
    json.dump(dict(updated=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC'), season=CUR, teams=teams), open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    n_ch = sum(1 for v in teams.values() if v.get('change')); n_act = sum(1 for v in teams.values() if v.get('change') and v['change']['next_match_no'] <= WINDOW)
    print(f'coach_flags.json: {len(teams)} ομαδες · αλλαγες μεσα στη σεζον: {n_ch} · ενεργες (επομενο ματς ≤{WINDOW}): {n_act}')
    return teams

_CACHE = None
def load():
    global _CACHE
    if _CACHE is None: _CACHE = _load(OUT, {}).get('teams', {})
    return _CACHE

TYP_GR = {'bad_both': 'κακη και στα δυο (αποτελεσματα & data)', 'unlucky': 'ατυχη (αποτελεσματα χειροτερα απο τα data)', 'lucky': 'τυχερη (αποτελεσματα καλυτερα απο τα data)'}
def filter_reason(team_id, md):
    """λογος κοψιματος pick ΥΠΕΡ της ομαδας (μονο αουτσαιντερ 15η+) ή None."""
    if md is None or md < FILTER_MIN_MD: return None
    c = (load().get(str(team_id)) or {}).get('change')
    if not c or c['next_match_no'] > WINDOW or c['type'] != 'bad_both': return None
    return f"νεος προπονητης ({c['perm'] or c['first']}, απο {c['date']}) · {c['next_match_no']}ο ματς μετα την αλλαγη · πριν: κακη και στα δυο (τυχη {c['pre_luck']:+.2f})"

def notes(team_id):
    """κειμενα για καρτες/alerts: αλλαγη στα 1-8 ματς (με τυπο) ή καλοκαιρινη."""
    v = load().get(str(team_id)) or {}; out = []
    c = v.get('change')
    if c and c['next_match_no'] <= WINDOW:
        who = c['perm'] or c['first']
        ct = f" (πρωτα μεταβατικος {c['first']})" if c.get('caretaker_first') and c['first'] != who else ''
        out.append(f"{v.get('name')}: νεος προπονητης {who}{ct} απο {c['date']} — {c['next_match_no']}ο ματς · πριν: {TYP_GR[c['type']]}")
    elif v.get('summer_new') and (v.get('played') or 0) < 8:
        out.append(f"{v.get('name')}: νεος προπονητης απο το καλοκαιρι ({v.get('coach')})")
    return out

def log_cut(rec):
    """καταγραφη κομμενου pick (μια φορα ανα ματς/πλευρα/γραμμη)."""
    key = f"{rec.get('home')}|{rec.get('away')}|{rec.get('when')}|{rec.get('side')}|{rec.get('hcap')}"
    seen = set()
    if os.path.exists(LOG):
        for ln in open(LOG, encoding='utf-8'):
            try: seen.add(json.loads(ln).get('key'))
            except Exception: pass
    if key in seen: return
    with open(LOG, 'a', encoding='utf-8') as fh:
        fh.write(json.dumps(dict(rec, key=key, logged=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M')), ensure_ascii=False) + chr(10))

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if '--no-fetch' not in sys.argv: fetch_coaches()
    tm = build()
    for t, v in tm.items():
        c = v.get('change')
        if c and c['next_match_no'] <= WINDOW:
            print(f"  [{v['lg']}] {v['name']}: {c['first']}{' → ' + c['perm'] if c['caretaker_first'] else ''} απο {c['date']} · επομενο = {c['next_match_no']}ο · {c['type']} (τυχη {c['pre_luck']:+.2f})")
