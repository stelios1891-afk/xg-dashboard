# -*- coding: utf-8 -*-
"""el_defense.py — ΑΜΥΝΤΙΚΗ ΑΞΙΑ ΠΑΙΚΤΗ για τη διορθωση απουσιων ΧΑΝΤΙΚΑΠ Ευρωλιγκας (29/10/2026, Στελιος «ναι περνα το»: «PIR + αμυνα»).
ΤΙ ΚΑΝΕΙ: για καθε παικτη δινει zΑΜΥΝΑ = −D / sd, οπου D = το αμυντικο κομματι του «συνδυασμου Σ» (ποντοι/100 κατοχες που δεχεται η ομαδα
  οταν ειναι στο γηπεδο, RAPM λ 8000 με prior το δικο μας box) — + = καλος αμυνομενος.
  φετινη τιμη: RAPM σε ολα τα τελειωμενα φετινα ματς (κομματια πενταδων απο το play-by-play) · μιξη με περσινη (n·φετος + K·περσι)/(n + K),
  n = φετινες κατοχες στο γηπεδο, K 500 (ιδιο με el_best_index_test.blend / el_pird_tests).
ΧΡΗΣΗ: el_absence.team_cost → κοστος = (B0 + B1·zPIR + B2·zΑΜΥΝΑ)·λεπτα/40·g(k) (B απο el_defense_params.json).
ΑΡΧΕΙΑ: el_defense_params.json (σταθερο, el_defense_build.py: περσινες τιμες, box συντελεστες, sd, B) · el_defense_stints.json (φετινα ματς:
  κομματια πενταδων + box ανα παικτη) · el_defense_values.json (zΑΜΥΝΑ ανα παικτη, ξαναγραφεται απο update()).
  update() καλειται καθε μερα απο el_refresh.py. ΚΑΘΕ ΝΕΑ ΣΕΖΟΝ: ξανατρεξε el_defense_build.py (περσινες τιμες = η σεζον που τελειωσε).
Μονο numpy/stdlib (τρεχει στο GitHub Actions)."""
import os, json, time, collections, datetime as dt, urllib.request
import numpy as np
ROOT = os.path.dirname(os.path.abspath(__file__))
F = lambda n: os.path.join(ROOT, n)
PARAMS, STINTS, VALUES = F('el_defense_params.json'), F('el_defense_stints.json'), F('el_defense_values.json')
UA = {'User-Agent': 'Mozilla/5.0'}
NF = 15
_BK = ('FieldGoalsMade2', 'FieldGoalsAttempted2', 'FieldGoalsMade3', 'FieldGoalsAttempted3', 'FreeThrowsMade', 'FreeThrowsAttempted', 'OffensiveRebounds',
       'DefensiveRebounds', 'Assistances', 'Steals', 'Turnovers', 'BlocksFavour', 'BlocksAgainst', 'FoulsCommited', 'FoulsReceived')
_Q = ('FirstQuarter', 'SecondQuarter', 'ThirdQuarter', 'ForthQuarter', 'ExtraTime')
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
def parse(b, p):
    """Boxscore + PlaybyPlay → (H, A, κομματια [(πεντα γηπ, πεντα φιλ, ποντοι γηπ, φιλ, κατοχες γηπ, φιλ, δευτ.)], box {pid: [15 στατ, κατοχες στο γηπεδο, λεπτα, PIR]})
    — ιδια λογικη με el_rapm_build.parse + el_index_build_test (κατοχες = ΠΣ + 0.44·βολες − επιθ.ριμπ + λαθη· στο γηπεδο = (γηπ + φιλ)/2)."""
    H, A = (p.get('CodeTeamA') or '').strip(), (p.get('CodeTeamB') or '').strip()
    box = {}; on = {H: set(), A: set()}
    for st in b.get('Stats') or []:
        for x in st.get('PlayersStats') or []:
            pid = x['Player_ID'].strip(); tm = x['Team'].strip()
            box[pid] = dict(team=tm, sec=_mmss(x.get('Minutes')) or 0, val=x.get('Valuation') or 0, **{k: x.get(k) or 0 for k in _BK})
            if x.get('IsStarter') and tm in on: on[tm].add(pid)
    stints = []
    cur = dict(pts={H: 0, A: 0}, fga={H: 0, A: 0}, fta={H: 0, A: 0}, orb={H: 0, A: 0}, to={H: 0, A: 0}, sec=0)
    def close():
        nonlocal cur
        if cur['sec'] > 0 or any(cur['pts'].values()):
            if len(on[H]) == 5 and len(on[A]) == 5:
                poss = {t: cur['fga'][t] + 0.44 * cur['fta'][t] - cur['orb'][t] + cur['to'][t] for t in (H, A)}
                stints.append((tuple(sorted(on[H])), tuple(sorted(on[A])), cur['pts'][H], cur['pts'][A], poss[H], poss[A], cur['sec']))
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
    pon = collections.Counter()
    for h5, a5, ph, pa, qh, qa, sec in stints:
        for q in h5 + a5: pon[q] += (qh + qa) / 2
    vec = {}
    for pid, v in box.items():
        if pon.get(pid, 0) <= 0: continue
        vec[pid] = [v['FieldGoalsMade2'], v['FieldGoalsAttempted2'] - v['FieldGoalsMade2'], v['FieldGoalsMade3'], v['FieldGoalsAttempted3'] - v['FieldGoalsMade3'],
                    v['FreeThrowsMade'], v['FreeThrowsAttempted'] - v['FreeThrowsMade'], v['OffensiveRebounds'], v['DefensiveRebounds'], v['Assistances'],
                    v['Steals'], v['Turnovers'], v['BlocksFavour'], v['BlocksAgainst'], v['FoulsCommited'], v['FoulsReceived'], pon[pid], v['sec'] / 60, v['val']]
    return H, A, [list(map(list, s[:2])) + list(s[2:]) for s in stints], vec
def rapm(games, lam, prior):
    """games: λιστα {st, ...}. prior: {pid: (O, D)}. → {pid: (O, D)} — ridge με prior (ιδιο με el_index_build_test.rapm, numpy αντι scipy)."""
    off, dff, hm, y, w = [], [], [], [], []
    for g in games:
        for h5, a5, ph, pa, qh, qa, sec in g['st']:
            for o, d_, pts, poss, ih in ((h5, a5, ph, qh, 1), (a5, h5, pa, qa, 0)):
                if poss <= 0: continue
                off.append(o); dff.append(d_); hm.append(ih); y.append(100 * pts / poss); w.append(poss)
    if not y: return {}
    y, w, hm = np.array(y), np.array(w), np.array(hm)
    mu = np.average(y, weights=w)
    pl = sorted({q for r in off + dff for q in r}); n = len(pl); loc = {q: i for i, q in enumerate(pl)}; m = 2 * n + 1
    lo = np.array([[loc[q] for q in r] for r in off]); ld = np.array([[loc[q] for q in r] for r in dff]) + n
    cols = np.c_[lo, ld, np.where(hm > 0, 2 * n, -1)]                       # −1 = κενο (φιλοξ χωρις εδρα)
    valid = cols >= 0
    ii = np.repeat(cols[:, :, None], cols.shape[1], 2); jj = np.repeat(cols[:, None, :], cols.shape[1], 1)
    vv = (valid[:, :, None] & valid[:, None, :])
    wt = np.broadcast_to(w[:, None, None], ii.shape)
    A = np.bincount((ii[vv] * m + jj[vv]), weights=wt[vv], minlength=m * m).reshape(m, m)
    bvec = np.bincount(cols[valid], weights=np.broadcast_to((w * (y - mu))[:, None], cols.shape)[valid], minlength=m)
    p0 = np.zeros(m)
    for i, q in enumerate(pl): p0[i], p0[n + i] = prior.get(q, (0.0, 0.0))
    bvec = bvec - A @ p0
    beta = p0 + np.linalg.solve(A + lam * np.eye(m), bvec)
    return {q: (float(beta[i]), float(beta[n + i])) for i, q in enumerate(pl)}
def values(P_, games):
    """→ {pid: dict(D μιξη, zd, n φετινες κατοχες)} για ολους οσους εχουν φετινη ή περσινη τιμη."""
    agg = {}
    for g in games:
        for pid, v in g['p'].items():
            agg[pid] = agg.get(pid, 0) + np.array(v, float)
    cf, kbox = P_['coef'], P_['KBOX']; lg = np.array(cf['lg']); bO, bD = np.array(cf['bO']), np.array(cf['bD'])
    BX = {}
    for pid, v in agg.items():
        if v[15] <= 0: continue
        rate = 100 * (v[:NF] + kbox * lg) / (v[15] + kbox)
        BX[pid] = (float(bO[0] + rate @ bO[1:]), float(bD[0] + rate @ bD[1:]))
    cur = rapm(games, P_['LAM'], BX) if games else {}
    out = {}
    for pid in set(cur) | set(P_['prev']):
        c = cur.get(pid); pv = P_['prev'].get(pid)
        n = float(agg[pid][15]) if (c is not None and pid in agg) else 0.0
        cc = np.array(c) if c is not None else np.zeros(2); pp = np.array(pv, float) if pv is not None else np.zeros(2)
        O, D = (n * cc + P_['K'] * pp) / (n + P_['K'])
        out[pid] = dict(D=round(float(D), 4), zd=round(-float(D) / P_['sdD'], 4), n=round(n, 1), prev=pv is not None)
    return out
def update(season=None, local_dir=None, sleep=1.0):
    """Κατεβαζει box + PBP οσων ΤΕΛΕΙΩΜΕΝΩΝ φετινων ματς λειπουν (>3ω μετα το τζαμπολ) και ξαναγραφει el_defense_values.json. → (νεα ματς, συνολο)."""
    P_ = json.load(open(PARAMS, encoding='utf-8')); season = season or P_['season']
    S = json.load(open(STINTS, encoding='utf-8')) if os.path.exists(STINTS) else {}
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
        try: H, A, st, vec = parse(b, p)
        except Exception as e: print('el_defense: σφαλμα', key, e); continue
        if not st or not vec: continue
        S[key] = dict(utc=x['utcDate'], H=H, A=A, st=st, p=vec); new += 1
    if new: json.dump(S, open(STINTS, 'w', encoding='utf-8'), separators=(',', ':'))
    V = values(P_, [v for k, v in S.items() if k.startswith(season + '_')])
    json.dump(dict(updated=now.isoformat(timespec='seconds'), season=season, games=sum(1 for k in S if k.startswith(season + '_')), players=V),
              open(VALUES, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    _C.clear()
    return new, len(S)
_C = {}
def params():
    if 'P' not in _C:
        try: _C['P'] = json.load(open(PARAMS, encoding='utf-8'))
        except Exception: _C['P'] = None
    return _C['P']
def zd(pid):
    """zΑΜΥΝΑ του παικτη (+ = καλος αμυνομενος) ή None αν δεν υπαρχει τιμη (ουτε φετος ουτε περσι)."""
    if 'V' not in _C:
        try: _C['V'] = json.load(open(VALUES, encoding='utf-8'))['players']
        except Exception: _C['V'] = {}
    v = _C['V'].get(str(pid).strip())
    return None if v is None else v['zd']

if __name__ == '__main__':
    import sys; sys.stdout.reconfigure(encoding='utf-8')
    n, tot = update(local_dir=sys.argv[1] if len(sys.argv) > 1 else None)
    V = json.load(open(VALUES, encoding='utf-8'))
    print(f'el_defense: +{n} ματς · συνολο {tot} · παικτες με τιμη {len(V["players"])}')
