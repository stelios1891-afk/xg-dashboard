# -*- coding: utf-8 -*-
"""nba_boxB.py — NBA ΦΕΤΙΝΗ ΑΞΙΑ ΠΑΙΚΤΗ «Β» = δικο μας box (24/10/2026, Στελιος «περσινο DARKO + LEBRON οπως ειναι, φετινο με το Β · περνα το»).
Τεστ: nba_tests/t65_bet.py (χαντικαπ 2023-26, επισημες αναφορες στο ανοιγμα): +152.5 vs +120.1μ, RMSE 3/4, κλιση 1.00 · t66 τυχη (καλυτερος
απο 3) 0.078 / ανα εβδομαδα 0.093 (< 0.10) · θετικο 4/4 σεζον. Συνολα: ΑΜΕΤΑΒΛΗΤΑ (o/d περσινα).
ΤΙ ΥΠΟΛΟΓΙΖΕΙ: για παικτη (ESPN id) πριν απο μια μερα: 13 στατιστικα ανα 100 κατοχες στο γηπεδο (μαζεμα 150 κατοχες προς τον μεσο) +
  λεπτα/ματς + % βασικος, απο τα φετινα ματς ΠΡΙΝ τη μερα + περσινα × w_prev → επιθεση O / αμυνα D (βαρη απο RAPM) → καθαρο O + D →
  κλιμακα live αξιας (a + c·καθαρο). Οι κατοχες στο γηπεδο απο ανασυσταση πενταδων του φετινου play-by-play (nba_pbp_full/2027, ιδια
  λογικη με nba_tests/t65_lineups.parse_game). Παραμετροι: nba_boxB_params.json (nba_tests/t67_boxB_params_build.py, τοπικα, ετησια).
ΧΡΗΣΗ: nba_absence.BoxValue.mix → v = (φετινα λεπτα·v_B + 250·v_περσι)/(φετινα λεπτα + 250)· χωρις v_B → η παλια φετινη box (t59).
Μονο numpy/stdlib."""
import os, json, glob, collections, datetime as dt
import numpy as np
ROOT = os.path.dirname(os.path.abspath(__file__))
F = lambda n: os.path.join(ROOT, n)
SKIP = ('Technical', 'Ejection', 'Timeout', 'Challenge', 'Review', 'Delay', 'End Period', 'End Game', 'Too Many', 'No Violation', 'No Foul')
def _is_to(t): return ('Turnover' in t and t != 'No Turnover') or t in ('Traveling', 'Offensive Charge')
def _ft_last(t):
    if not t.startswith('Free Throw') or 'Technical' in t: return None
    try:
        a, b = t.rsplit(' ', 3)[-3], t.rsplit(' ', 1)[-1]; return int(a) == int(b)
    except Exception: return True
def _mins(v):
    try: return float(v)
    except Exception: return 0.0
def _stints(g):
    """αντιγραφο του nba_tests/t65_lineups.parse_game (μονο τα κομματια): [h5, a5, sec, pts_h, pts_a, fga_h, fta_h, oreb_h, tov_h, fga_a, ...]"""
    box = g['box']; tid = g['team_ids']; home, away = g['teams']['home'], g['teams']['away']
    team_of = {p: v[0] for p, v in box.items()}
    side_of_tid = {k: (0 if c == home else 1) for k, c in tid.items()}
    def side(p): t = team_of.get(p); return None if t is None else (0 if t == home else (1 if t == away else None))
    starters = [[p for p, v in box.items() if v[2] and side(p) == s] for s in (0, 1)]
    bmin = {p: _mins(v[4].get('minutes')) for p, v in box.items()}
    byper = collections.OrderedDict()
    for p in g['plays']:
        if p[0] is None: continue
        byper.setdefault(p[0], []).append(p)
    stints = []; prev_end = [set(starters[0]), set(starters[1])]; lh, la = 0, 0
    for per, pl in byper.items():
        L0 = 720.0 if per <= 4 else 300.0
        if per == 1: cur = [set(starters[0]), set(starters[1])]
        else:
            seen = {}; cur = [set(), set()]
            for p in pl:
                t = p[5] or ''
                if t == 'Substitution':
                    if len(p[4]) != 2: continue
                    pin, pout = p[4]
                    if pin not in seen: seen[pin] = 'in'
                    if pout not in seen: seen[pout] = 'start'
                    continue
                if any(w in t for w in SKIP): continue
                for q in p[4]:
                    if q not in seen: seen[q] = 'start'
            for q, how in seen.items():
                s = side(q)
                if how == 'start' and s is not None: cur[s].add(q)
            for s in (0, 1):
                if len(cur[s]) < 5:
                    for q in sorted(prev_end[s] - set(seen), key=lambda x: -bmin.get(x, 0)):
                        if len(cur[s]) >= 5: break
                        cur[s].add(q)
                if len(cur[s]) < 5:
                    for q in sorted([x for x in box if side(x) == s and x not in seen and x not in cur[s]], key=lambda x: -bmin.get(x, 0)):
                        if len(cur[s]) >= 5: break
                        cur[s].add(q)
        t_prev = L0
        def new_seg():
            stints.append([tuple(sorted(cur[0])), tuple(sorted(cur[1])), 0.0] + [0.0] * 10); return len(stints) - 1
        seg = new_seg(); foul_seg, foul_clk = None, None; last_ft_nonlast = False
        for p in pl:
            clk = p[1] if p[1] is not None else t_prev
            if t_prev - clk > 0: stints[seg][2] += t_prev - clk; t_prev = clk
            t = p[5] or ''; hs, as_ = p[2], p[3]; tgt = seg
            if t.startswith('Free Throw') and foul_seg is not None and foul_clk == clk: tgt = foul_seg
            if hs is not None and as_ is not None:
                dh, da = hs - lh, as_ - la
                if dh or da: stints[tgt][3] += dh; stints[tgt][4] += da; lh, la = hs, as_
            sd = side_of_tid.get(p[9]) if p[9] is not None else None
            if t == 'Substitution':
                if len(p[4]) != 2: continue
                pin, pout = p[4]; s = side(pin) if side(pin) is not None else side(pout)
                if s is None: continue
                cur[s].discard(pout); cur[s].add(pin)
                if stints[seg][2] == 0 and stints[seg][3] == 0 and stints[seg][4] == 0 and sum(stints[seg][5:]) == 0:
                    stints[seg][0], stints[seg][1] = tuple(sorted(cur[0])), tuple(sorted(cur[1]))
                else: seg = new_seg()
                continue
            if sd is None: continue
            o = 5 if sd == 0 else 9
            if 'Foul' in t and 'Turnover' not in t: foul_seg, foul_clk = seg, clk
            if p[7] and not t.startswith('Free Throw'): stints[tgt][o] += 1; last_ft_nonlast = False
            elif t.startswith('Free Throw'):
                fl = _ft_last(t)
                if fl is not None: stints[tgt][o + 1] += 1; last_ft_nonlast = (fl is False)
            elif t == 'Offensive Rebound':
                if not (not p[4] and last_ft_nonlast): stints[tgt][o + 2] += 1
            elif _is_to(t): stints[tgt][o + 3] += 1
        if t_prev > 0: stints[seg][2] += t_prev
        prev_end = [set(cur[0]), set(cur[1])]
    out = []
    for st in stints:
        if st[2] <= 0 and st[3] == 0 and st[4] == 0 and sum(st[5:]) == 0: continue
        if out and out[-1][0] == st[0] and out[-1][1] == st[1]:
            for j in range(2, 13): out[-1][j] += st[j]
        else: out.append(list(st))
    return out
def _mk(v):
    try: a, b = str(v).split('-'); return float(a), float(b)
    except Exception: return 0.0, 0.0
def _fl(v):
    try: return float(v)
    except Exception: return 0.0
def _et_ord(iso):
    return (dt.datetime.strptime(iso[:16], '%Y-%m-%dT%H:%M') - dt.timedelta(hours=5)).date().toordinal()
def game_rows(g):
    """compact ματς (nba_pbp_full) → {ESPN id: [ημερα ΗΠΑ (ordinal), κατοχες στο γηπεδο, λεπτα, βασικος, 13 στατ]} — ιδιο με t65 pgbox"""
    poss = collections.Counter()
    for st in _stints(g):
        ph = st[5] + 0.44 * st[6] - st[7] + st[8]; pa = st[9] + 0.44 * st[10] - st[11] + st[12]; pav = max((ph + pa) / 2, 0.0)
        for q in st[0] + st[1]: poss[q] += pav
    d = _et_ord(g['date']); res = {}
    for p, v in g['box'].items():
        if v[3]: continue
        stt = v[4]; mn = _mins(stt.get('minutes'))
        if mn <= 0: continue
        fgm, fga = _mk(stt.get('fieldGoalsMade-fieldGoalsAttempted', '0-0')); tpm, tpa = _mk(stt.get('threePointFieldGoalsMade-threePointFieldGoalsAttempted', '0-0'))
        ftm, fta = _mk(stt.get('freeThrowsMade-freeThrowsAttempted', '0-0'))
        res[p] = [d, poss.get(p, 0.0), mn, 1.0 if v[2] else 0.0, fgm - tpm, (fga - tpa) - (fgm - tpm), tpm, tpa - tpm, ftm, fta - ftm,
                  _fl(stt.get('offensiveRebounds')), _fl(stt.get('defensiveRebounds')), _fl(stt.get('assists')), _fl(stt.get('steals')),
                  _fl(stt.get('blocks')), _fl(stt.get('turnovers')), _fl(stt.get('fouls'))]
    return res
class BoxB:
    def __init__(self, params=None, pbp_glob=None):
        self.P = params or json.load(open(F('nba_boxB_params.json'), encoding='utf-8'))
        self.rows = collections.defaultdict(list)
        pat = pbp_glob or F(os.path.join('nba_pbp_full', str(self.P['season']), '*.jsonl'))
        seen = set()
        for fn in sorted(glob.glob(pat)):
            for ln in open(fn, encoding='utf-8'):
                try: g = json.loads(ln)
                except Exception: continue
                if g.get('stype') not in (2, None) or g.get('id') in seen: continue
                seen.add(g.get('id'))
                try:
                    for p, r in game_rows(g).items(): self.rows[str(p)].append(r)
                except Exception: continue
        self.cO, self.cD, self.mu = np.array(self.P['cO']), np.array(self.P['cD']), np.array(self.P['mu'])
        self._c = {}
    def raw(self, pid, before_ord):
        """(καθαρο O + D σε ποντους/100 κατοχες, O, D) ή None — ιδιο με t65 prior_vec / box_feats."""
        pid = str(pid); k = (pid, before_ord)
        if k in self._c: return self._c[k]
        acc = np.zeros(17)                                               # poss, min, st, f0..f12, g
        for r in self.rows.get(pid, []):
            if r[0] < before_ord: acc[:16] += np.array(r[1:], float); acc[16] += 1
        pv = self.P['prev'].get(pid)
        if pv is not None: acc += self.P['wp'] * np.array(pv, float)
        if acc[1] <= 0: self._c[k] = None; return None
        P0, mu = self.P['P0'], self.mu
        rate = (acc[3:16] * 100 + P0 * mu) / (acc[0] + P0) - mu
        mpg = (acc[1] + 3 * 12.0) / (acc[16] + 3) - 24.0; stp = acc[2] / (acc[16] + 3) - 0.5
        Z = np.r_[1.0, rate, mpg, stp]; O = float(Z @ self.cO); D = float(Z @ self.cD)
        self._c[k] = (O + D, O, D); return self._c[k]
    def value(self, pid, gdate):
        """φετινη αξια «Β» σε κλιμακα live (a + c·καθαρο) ή None · gdate = ημερα ΗΠΑ 'YYYY-MM-DD' (μονο ματς ΠΡΙΝ)."""
        r = self.raw(pid, dt.date.fromisoformat(str(gdate)[:10]).toordinal())
        return None if r is None else self.P['a'] + self.P['c'] * r[0]
