# -*- coding: utf-8 -*-
"""el_box_shadow.py — ΣΚΙΑ «δικο box score» στο ΧΑΝΤΙΚΑΠ Ευρωλιγκας (23/10/2026, Στελιος «ναι» στο σχεδιο σκιας).
ΤΙ ΚΑΝΕΙ: δινει για καθε αποντα ενα ΔΕΥΤΕΡΟ κοστος απουσιας (διπλα στο PIR του live) απο τον «δικο box» δεικτη:
  15 στατιστικα box ανα 100 κατοχες στο γηπεδο × βαρη που εμαθαν απο RAPM (el_box_shadow_params.json, el_box_shadow_build.py) →
  επιθεση O / αμυνα D · φετινη τιμη μιξη με περσινη (n·φετος + K·περσι)/(n + K), n = φετινες κατοχες, K 500 ·
  κοστος = (β0 + β1·(O − D)/sd)·λεπτα/40·g(k)·βαρος (OUT 1, GTD πιθανοτητα) — ιδιοι αποντες με το live (el_absence.team_cost).
ΤΙΠΟΤΑ ΔΕΝ ΑΛΛΑΖΕΙ ΣΤΑ PICKS: το el_picks γραφει σκιωδη picks (edge ≥ 8%) στο el_box_shadow.jsonl + τις διορθωσεις ανα ματς στο
  el_box_shadow_adj.json. ΚΡΙΣΗ (προ-δηλωμενη): τελος κανονικης περιοδου, ΜΟΝΟ αγωνιστικες 11-38 — ακριβεια χαντικαπ καλυτερη απο live
  ΚΑΙ μοναδες ≥ live ΚΑΙ CLV ≥ live στα ιδια ματς → αλλαγη απο την 11η αγωνιστικη της επομενης σεζον.
ΔΕΔΟΜΕΝΑ: el_box_shadow_stats.json = ανα παιγμενο ματς, ανα παικτη [15 στατ, κατοχες στο γηπεδο, λεπτα, PIR] απο το επισημο API
  (Boxscore + PlaybyPlay· οι κατοχες απο την ανασυσταση πενταδων, ιδια με el_rapm_build.parse). update() καλειται απο el_refresh.py.
Μονο numpy/stdlib (τρεχει στο GitHub Actions)."""
import os, json, time, collections, datetime as dt, urllib.request
import numpy as np
ROOT = os.path.dirname(os.path.abspath(__file__))
F = lambda n: os.path.join(ROOT, n)
STATS, PARAMS = F('el_box_shadow_stats.json'), F('el_box_shadow_params.json')
UA = {'User-Agent': 'Mozilla/5.0'}
NF = 15
def _J(u, tries=3):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40) as r: return json.loads(r.read().decode('utf-8'))
        except Exception:
            if k == tries - 1: return None
            time.sleep(5 * (k + 1))
def _mmss(t):
    try: m, s = str(t).split(':'); return int(m) * 60 + int(s)
    except Exception: return None
_Q = ('FirstQuarter', 'SecondQuarter', 'ThirdQuarter', 'ForthQuarter', 'ExtraTime')
_BK = ('FieldGoalsMade2', 'FieldGoalsAttempted2', 'FieldGoalsMade3', 'FieldGoalsAttempted3', 'FreeThrowsMade', 'FreeThrowsAttempted', 'OffensiveRebounds',
       'DefensiveRebounds', 'Assistances', 'Steals', 'Turnovers', 'BlocksFavour', 'BlocksAgainst', 'FoulsCommited', 'FoulsReceived')
def game_vectors(b, p):
    """Boxscore + PlaybyPlay (επισημο API) → {pid: [15 στατ, κατοχες στο γηπεδο, λεπτα, PIR]} — ιδια λογικη με el_rapm_build.parse +
    el_index_build_test (κατοχες = ΠΣ + 0.44·βολες − επιθ.ριμπ + λαθη ανα κομματι 5+5, στο γηπεδο = (δικες + αντιπαλου)/2)."""
    H, A = (p.get('CodeTeamA') or '').strip(), (p.get('CodeTeamB') or '').strip()
    box = {}; on = {H: set(), A: set()}
    for st in b.get('Stats') or []:
        for x in st.get('PlayersStats') or []:
            pid = x['Player_ID'].strip(); tm = x['Team'].strip()
            box[pid] = dict(team=tm, sec=_mmss(x.get('Minutes')) or 0, val=x.get('Valuation') or 0, **{k: x.get(k) or 0 for k in _BK})
            if x.get('IsStarter') and tm in on: on[tm].add(pid)
    pon = collections.Counter()
    cur = dict(pts={H: 0, A: 0}, fga={H: 0, A: 0}, fta={H: 0, A: 0}, orb={H: 0, A: 0}, to={H: 0, A: 0}, sec=0)
    def close():
        nonlocal cur
        if (cur['sec'] > 0 or any(cur['pts'].values())) and len(on[H]) == 5 and len(on[A]) == 5:
            q = {t: cur['fga'][t] + 0.44 * cur['fta'][t] - cur['orb'][t] + cur['to'][t] for t in (H, A)}
            for pid in on[H] | on[A]: pon[pid] += (q[H] + q[A]) / 2
        cur = dict(pts={H: 0, A: 0}, fga={H: 0, A: 0}, fta={H: 0, A: 0}, orb={H: 0, A: 0}, to={H: 0, A: 0}, sec=0)
    for qi, k in enumerate(_Q):
        plays = p.get(k) or []
        if not plays: continue
        prev = 600 if qi < 4 else 300
        for x in plays:
            t = _mmss(x.get('MARKERTIME') or '')
            if t is not None and prev - t > 0: cur['sec'] += prev - t; prev = t
            pt, tm, pid = x.get('PLAYTYPE'), (x.get('CODETEAM') or '').strip(), (x.get('PLAYER_ID') or '').strip()
            if tm not in on: continue
            if pt in ('IN', 'OUT'):
                close(); (on[tm].add if pt == 'IN' else on[tm].discard)(pid); continue
            if pt == '2FGM': cur['pts'][tm] += 2; cur['fga'][tm] += 1
            elif pt == '3FGM': cur['pts'][tm] += 3; cur['fga'][tm] += 1
            elif pt in ('2FGA', '3FGA'): cur['fga'][tm] += 1
            elif pt == 'FTM': cur['pts'][tm] += 1; cur['fta'][tm] += 1
            elif pt == 'FTA': cur['fta'][tm] += 1
            elif pt == 'O': cur['orb'][tm] += 1
            elif pt == 'TO': cur['to'][tm] += 1
        if prev > 0: cur['sec'] += prev
        close()
    out = {}
    for pid, v in box.items():
        if pon.get(pid, 0) <= 0: continue
        out[pid] = [v['FieldGoalsMade2'], v['FieldGoalsAttempted2'] - v['FieldGoalsMade2'], v['FieldGoalsMade3'], v['FieldGoalsAttempted3'] - v['FieldGoalsMade3'],
                    v['FreeThrowsMade'], v['FreeThrowsAttempted'] - v['FreeThrowsMade'], v['OffensiveRebounds'], v['DefensiveRebounds'], v['Assistances'],
                    v['Steals'], v['Turnovers'], v['BlocksFavour'], v['BlocksAgainst'], v['FoulsCommited'], v['FoulsReceived'],
                    round(pon[pid], 3), round(v['sec'] / 60, 2), v['val']]
    return out
def update(season=None, local_dir=None, sleep=1.0):
    """Κατεβαζει box + PBP οσων ΤΕΛΕΙΩΜΕΝΩΝ ματς λειπουν απο το el_box_shadow_stats.json (ματς >3ω μετα το τζαμπολ)."""
    P_ = json.load(open(PARAMS, encoding='utf-8')); season = season or P_['season']
    S = json.load(open(STATS, encoding='utf-8')) if os.path.exists(STATS) else {}
    g = _J(f'https://api-live.euroleague.net/v2/competitions/E/seasons/{season}/games')
    now = dt.datetime.now(dt.timezone.utc); new = 0
    for x in (g or {}).get('data', []):
        if not x.get('played') or not x.get('utcDate'): continue
        ko = dt.datetime.fromisoformat(x['utcDate'].replace('Z', '+00:00'))
        if (now - ko).total_seconds() < 3 * 3600: continue
        key = f"{season}_{x['gameCode']}"
        if key in S: continue
        fn = os.path.join(local_dir, f'{key}.json') if local_dir else None
        if fn and os.path.exists(fn):
            d = json.load(open(fn, encoding='utf-8')); b, p = d['box'], d['pbp']
        else:
            b = _J(f"https://live.euroleague.net/api/Boxscore?gamecode={x['gameCode']}&seasoncode={season}"); time.sleep(sleep)
            p = _J(f"https://live.euroleague.net/api/PlaybyPlay?gamecode={x['gameCode']}&seasoncode={season}"); time.sleep(sleep)
            if not b or not p: continue
        try: vec = game_vectors(b, p)
        except Exception as e: print('el_box_shadow: σφαλμα', key, e); continue
        if not vec: continue
        S[key] = dict(utc=x['utcDate'], p=vec); new += 1
    if new: json.dump(S, open(STATS, 'w', encoding='utf-8'), separators=(',', ':'))
    return new, len(S)
_CACHE = {}
def _load():
    if 'P' not in _CACHE:
        _CACHE['P'] = json.load(open(PARAMS, encoding='utf-8'))
        _CACHE['S'] = json.load(open(STATS, encoding='utf-8')) if os.path.exists(STATS) else {}
    return _CACHE['P'], _CACHE['S']
def _boxval(v, cf, kbox):
    rate = 100 * (v[:NF] + kbox * np.array(cf['lg'])) / (v[15] + kbox)
    bO, bD = np.array(cf['bO']), np.array(cf['bD'])
    return float(bO[0] + rate @ bO[1:]), float(bD[0] + rate @ bD[1:])
def value(pid, before_utc):
    """→ καθαρη τιμη (O − D, ποντοι/100 κατοχες) ή None αν δεν υπαρχει τιποτα (ουτε φετος ουτε περσι)."""
    P_, S = _load(); pid = str(pid).strip()
    k = (pid, str(before_utc))
    if k in _CACHE: return _CACHE[k]
    acc = None
    for g in S.values():
        if g['utc'] >= str(before_utc).replace('+00:00', 'Z') or pid not in g['p']: continue
        v = np.array(g['p'][pid], float); acc = v if acc is None else acc + v
    pv = P_['prev'].get(pid)
    if acc is None and pv is None: res = None
    else:
        n = float(acc[15]) if acc is not None else 0.0
        c = np.array(_boxval(acc, P_['coef'], P_['KBOX'])) if acc is not None else np.zeros(2)
        p_ = np.array(pv, float) if pv is not None else np.zeros(2)
        O, D = (n * c + P_['K'] * p_) / (n + P_['K']); res = float(O - D)
    _CACHE[k] = res
    return res
def cost(pid, before_utc, avg_min, g):
    """κοστος απουσιας (ποντοι διαφορας) με τον δικο box δεικτη, πριν απο το βαρος GTD."""
    P_, _ = _load(); v = value(pid, before_utc)
    return (P_['b0'] + P_['b1'] * (v / P_['sd'] if v is not None else 0.0)) * avg_min / 40 * g

if __name__ == '__main__':
    import sys; sys.stdout.reconfigure(encoding='utf-8')
    n, tot = update(local_dir=sys.argv[1] if len(sys.argv) > 1 else None)
    print(f'el_box_shadow_stats.json: +{n} ματς · συνολο {tot}')
