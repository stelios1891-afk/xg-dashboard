# -*- coding: utf-8 -*-
"""el_absence.py — EUROLEAGUE: ΚΟΣΤΟΣ ΑΠΟΥΣΙΩΝ στην προβλεψη χαντικαπ (9/10/2026, Στελιος «να περασουν τα λεπτα»).
Τεστ: el_player_absence_value.py («μονο λεπτα», γ .5): LOSO 4/5 · picks ≥8% ανοιγμα +6.9% (575) → +9.4% (589, 5/5) · el_absence_scorer_test.
ΥΠΟΛΟΓΙΣΜΟΣ για καθε ομαδα:
  1. ΑΠΟΝΤΕΣ = παικτες με OUT στη RotoWire (EuroLeague daily lineups)· οι GTD (αμφιβολοι) ΔΕΝ μετρανε, μονο σημειωνονται.
  2. Μετραει μονο αν ειναι ΤΑΚΤΙΚΟΣ: επαιξε σε ≥3 απο τα 10 τελευταια φετινα ματς Ευρωλιγκας της ομαδας.
  3. Λεπτα = μεσος ορος των 10 τελευταιων ματς Ευρωλιγκας που επαιξε (φετος + περσι/παλιοτερα, el_player_min_prev.json)· ≥10′.
  4. k = ποσα συνεχομενα ματς της ομαδας λειπει (μαζι με το σημερινο): k 1-3 → πληρες· 4-10 → μισο· >10 → 0 (το μοντελο το εχει «μαθει» απο τα αποτελεσματα).
  5. ΚΟΣΤΟΣ = 0.922 × λεπτα/40 × (1 / 0.5 / 0) ποντοι.  Προβλεψη γηπ. = μοντελο + κοστος φιλοξ − κοστος γηπ.
Δεδομενα φετινα: el_box.json (ph/pa = [id, ονομα, λεπτα] ανα ματς — backfill() τα συμπληρωνει απο το επισημο API)."""
import os, re, json, html, time, unicodedata, datetime as dt, urllib.request
ROOT = os.path.dirname(os.path.abspath(__file__))
F = lambda n: os.path.join(ROOT, n)
COEF, G_LONG, MIN_MIN = 0.922, 0.5, 10.0
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36'}

def _tok(s):
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode().lower()
    return [w for w in re.split(r'[^a-z0-9]+', s) if w]

def fetch_rotowire():
    """→ [{visit, home, inj: {'visit': [(ονομα, κατασταση)], 'home': [...]}}] (κενη λιστα αν αποτυχει)"""
    try:
        req = urllib.request.Request('https://www.rotowire.com/euro/daily-lineups.php', headers=UA)
        s = urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'ignore')
    except Exception as e:
        print('RotoWire σφαλμα:', e); return []
    games = []
    parts = s.split('class="lineup__matchup"')[1:]
    for part in parts:
        names = re.findall(r'lineup__mteam is-(visit|home)[^>]*>\s*([^<]+?)\s*</a>', part)
        nm = {k: v.strip() for k, v in names}
        inj = {'visit': [], 'home': []}
        for side in ('visit', 'home'):
            m = re.search(r'<ul class="lineup__list is-' + side + r'">(.*?)</ul>', part, re.S)
            if not m or 'INJURIES' not in m.group(1): continue
            seg = m.group(1).split('INJURIES', 1)[1]
            for title, status in re.findall(r'<a title="([^"]+)"[^>]*>[^<]*</a>\s*<span class="lineup__inj">([^<]+)</span>', seg):
                inj[side].append((html.unescape(title), status.strip()))
        if 'visit' in nm and 'home' in nm: games.append(dict(visit=nm['visit'], home=nm['home'], inj=inj))
    return games

def backfill(B, season, J, sched):
    """Συμπληρωνει ph/pa (λεπτα παικτων) στα φετινα ματς του el_box.json που δεν τα εχουν. J = συναρτηση GET json."""
    n = 0
    for x in sched:
        k = f"{season}_{x['code']}"
        if not x.get('played') or k not in B or 'err' in B[k] or 'ph' in B[k]: continue
        b = J(f"https://live.euroleague.net/api/Boxscore?gamecode={x['code']}&seasoncode={season}")
        if not b or not b.get('Stats'): continue
        for side, t in (('ph', b['Stats'][0]), ('pa', b['Stats'][1])):
            L = []
            for p in (t.get('PlayersStats') or []):
                try: mm, ss = str(p.get('Minutes')).split(':'); mn = int(mm) + int(ss) / 60
                except Exception: mn = 0.0
                if mn > 0: L.append([str(p.get('Player_ID', '')).strip(), p.get('Player'), round(mn, 1)])
            B[k][side] = L
        n += 1
    return n

def _team_games(B, season, code):
    g = [v for k, v in B.items() if k.startswith(season + '_') and 'ph' in v and code in (v.get('hcode'), v.get('acode'))]
    g.sort(key=lambda v: v['utc'])
    return [(v['utc'], {p[0]: p[2] for p in (v['ph'] if v['hcode'] == code else v['pa'])}, {p[0]: p[1] for p in (v['ph'] if v['hcode'] == code else v['pa'])}) for v in g]

def _match(name, roster):
    """RotoWire «Mike James» → id στο ρόστερ {id: «JAMES, MIKE»}"""
    t = _tok(name)
    if not t: return None
    best = None
    for pid, nm in roster.items():
        u = _tok(nm)
        if not u: continue
        if t[-1] in u and (len(t) == 1 or any(w[0] == t[0][0] for w in u if w != t[-1])):
            if best is None: best = pid
            else: return None                                          # διφορουμενο
    return best

def team_cost(B, season, code, out_names, before_utc, prev):
    """→ (κοστος, [λεπτομερειες])"""
    tg = [x for x in _team_games(B, season, code) if x[0] < before_utc]
    if not tg: return 0.0, []
    roster = {}
    for _, _, nm in tg: roster.update(nm)
    last10 = tg[-10:]; played = {pid: sum(1 for _, mn, _ in last10 if mn.get(pid, 0) > 0) for pid in roster}
    cost, det = 0.0, []
    for name in out_names:
        pid = _match(name, roster)
        if not pid: det.append(f'{name}: δεν επαιξε φετος'); continue
        if played.get(pid, 0) < 3: det.append(f'{name}: οχι τακτικος ({played.get(pid, 0)}/10)'); continue
        mins = list((prev.get(pid) or {}).get('mins', [])) + [mn[pid] for _, mn, _ in tg if mn.get(pid, 0) > 0]
        avg = sum(mins[-10:]) / len(mins[-10:]) if mins else 0.0
        if avg < MIN_MIN: det.append(f'{name}: {avg:.0f}′ (<10)'); continue
        k = 1
        for _, mn, _ in reversed(tg):
            if mn.get(pid, 0) > 0: break
            k += 1
        g = 1.0 if k <= 3 else (G_LONG if k <= 10 else 0.0)
        c = COEF * avg / 40 * g; cost += c
        det.append(f'{name} {avg:.0f}′ ×{g:g} → {c:.2f}')
    return round(cost, 2), det

def adjustments(games, B=None):
    """games: λιστα ματς el_projections (home, away, hcode, acode, utc). → {code: dict(adj, cost_h, cost_a, note)}"""
    B = B if B is not None else json.load(open(F('el_box.json'), encoding='utf-8'))
    try: prev = json.load(open(F('el_player_min_prev.json'), encoding='utf-8'))['players']
    except Exception: prev = {}
    rw = fetch_rotowire()
    if not rw: return {}
    season = max((k.split('_')[0] for k in B if k.startswith('E')), default=None)
    res = {}
    now = dt.datetime.now(dt.timezone.utc)
    for g in games:
        if g.get('played'): continue
        try: ko = dt.datetime.fromisoformat(str(g['utc']).replace('Z', '+00:00'))
        except Exception: continue
        if not (now - dt.timedelta(hours=3) <= ko <= now + dt.timedelta(hours=60)): continue     # μονο η τρεχουσα αγωνιστικη (η RotoWire δειχνει μονο αυτη)
        best = None
        for r in rw:
            if set(_tok(r['home'])) & set(_tok(g['home'])) and set(_tok(r['visit'])) & set(_tok(g['away'])): best = r; break
        if not best: continue
        out_h = [n for n, s in best['inj']['home'] if s.upper() == 'OUT']; out_a = [n for n, s in best['inj']['visit'] if s.upper() == 'OUT']
        gtd = [n for side in ('home', 'visit') for n, s in best['inj'][side] if s.upper() != 'OUT']
        ch, dh = team_cost(B, season, g['hcode'], out_h, g['utc'], prev)
        ca, da = team_cost(B, season, g['acode'], out_a, g['utc'], prev)
        parts = []
        if dh: parts.append(f"{g['home']}: " + ', '.join(dh))
        if da: parts.append(f"{g['away']}: " + ', '.join(da))
        if gtd: parts.append('αμφιβολοι (δεν μετρανε): ' + ', '.join(gtd))
        res[str(g['code'])] = dict(adj=round(ca - ch, 2), cost_h=ch, cost_a=ca, note=' · '.join(parts))
    return res

if __name__ == '__main__':
    import sys; sys.stdout.reconfigure(encoding='utf-8')
    P = json.load(open(F('el_projections.json'), encoding='utf-8'))
    for c, v in adjustments(P['games']).items():
        g = next(x for x in P['games'] if str(x['code']) == c)
        print(f"{g['home']} - {g['away']}: μοντελο {g['margin']:+.1f} → {g['margin'] + v['adj']:+.1f} (γηπ −{v['cost_h']}, φιλ −{v['cost_a']}) · {v['note']}")
