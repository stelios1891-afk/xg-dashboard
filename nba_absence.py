# -*- coding: utf-8 -*-
"""nba_absence.py — NBA: ΚΟΣΤΟΣ ΑΠΟΥΣΙΩΝ στην προβλεψη (19/10/2026, Στελιος «περνα το live»).
Τεστ (scratchpad 19/10, LOSO 5 σεζον): absence_test.py — διορθωση περιθωριου 0.75 × Σ(αξια − (−1))·λεπτα/48 για γνωστο αποντα:
  RMSE 13.94 → 13.85 (5/5) · Οκτ-Δεκ ανοιγμα ≥8% +4.2% → +5.7% (με B2B: +5.1% → +7.1%) · κρατησαμε κατωφλι 8%.
  od_totals_test.py — συνολα: χαμενη επιθεση −0.67 (t −4.5), χαμενη αμυνα +0.97 (t +3.6)· LOSO (cO, cD) = (−0.5, +1.0).
  news_test.py / news_rule.py — ΣΚΙΩΔΗΣ κανονας συνολων: ΞΑΦΝΙΚΗ απουσια (επαιξε στον τελευταιο αγωνα) · υπολοιπο στο κλεισιμο
  = 0.18·επιθ + 1.28·αμυνα· Over αν ≥3 → +7.4% (186, 5/5) — ΜΟΝΟ καταγραφη.
ΑΠΩΝ (live) = ESPN «Out» (nba_injuries.json) · παικτης ΡΟΛΟΥ (μεσος ≥20′ στους ≤10 τελευταιους φετινους αγωνες κανονικης για ΤΗΝ ομαδα)
  · εχει παιξει ≥1 φετινο αγωνα κανονικης για την ομαδα (οπως το τεστ· οσοι λειπουν απο την αρχη τους εχει ηδη βγαλει το roster prior → οχι διπλο).
  Doubtful/Questionable: ΔΕΝ διορθωνουν (μονο το φιλτρο του nba_picks για Doubtful).
Αξιες: nba_player_values.json (nba_player_values_build.py, τοπικα, ετησια)."""
import os, json, re, unicodedata, collections, datetime as dt
ROOT = os.path.dirname(os.path.abspath(__file__))
F = lambda n: os.path.join(ROOT, n)
ABS_K, REP, REPO, REPD, MIN_ROLE = 0.75, -2.0, -0.5, -0.5, 20.0
# 20/10/2026 (Στελιος «περνα το»): ΑΝΤΙΚΑΤΑΣΤΑΤΗΣ −1 → −2 (nba_tests/t10 + t11: LOSO 5/5, RMSE 13.795→13.765, ανοιγμα ≥8% Οκτ-Δεκ +7.1→+7.4%,
# ολη +1.5→+3.1%) — καθε απων ρολου κοστιζει ~+0.5 π. (30′). Αγνωστος παικτης = αξια V_UNK −1 (οπως στα τεστ), ΟΧΙ ο αντικαταστατης.
V_UNK = -1.0
C_O, C_D = -0.5, 1.0                       # συνολα: επιθεση / αμυνα που χανεται
SH_O, SH_D, SH_THR = 0.18, 1.28, 3.0       # σκιωδης κανονας (ξαφνικες απουσιες, κλεισιμο)

def nk(s):
    s = unicodedata.normalize('NFD', str(s)); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    s = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', s); return ' '.join(re.findall(r'[a-z]+', s))

INJ_HIST = 'nba_injuries_hist.jsonl'      # 19/10 (Στελιος «κανε το 3»): ΙΣΤΟΡΙΚΟ λιστας ESPN — μονο ΑΛΛΑΓΕΣ (νεος/αλλη κατασταση/νεα ενημερωση/εφυγε)

def refresh_injuries():
    """Φρεσκια λιστα ESPN (σε καθε scan NBA)· σε σφαλμα μενει η παλια. Καθε αλλαγη σε σχεση με την προηγουμενη λιστα → INJ_HIST
    (για μελλοντικο τεστ αμφιβολων: ποτε εγινε Day-To-Day / Out, αν τελικα επαιξε). players = [ονομα, κατασταση, τυπος, ημερομηνια ESPN]."""
    from nba_espn import get, B, TEAMNAME
    inj = get(f'{B}/injuries'); T = {}; info = {}
    for t in inj.get('injuries', []):
        nm = t.get('displayName', ''); code = TEAMNAME.get(nm); pl = []
        for x in t.get('injuries', []):
            p = x['athlete']['displayName']; pl.append([p, x.get('status'), (x.get('type') or {}).get('description'), x.get('date')])
            info[(code, p)] = (x.get('status'), x.get('date'), (x.get('type') or {}).get('description'), (x.get('shortComment') or '')[:400])
        T[nm] = dict(code=code, players=pl)
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec='minutes')
    try:
        old = {}
        for v in json.load(open(F('nba_injuries.json'), encoding='utf-8')).get('teams', {}).values():
            for x in v.get('players', []): old[(v.get('code'), x[0])] = (x[1], x[3] if len(x) > 3 else None)
        ch = []
        for k, (stt, dte, typ, com) in info.items():
            o = old.get(k)
            if o is None or o[0] != stt or (o[1] is not None and o[1] != dte):
                ch.append(dict(t=now, team=k[0], player=k[1], status=stt, prev=o[0] if o else None, espn_date=dte, type=typ, comment=com))
        for k, o in old.items():
            if k not in info: ch.append(dict(t=now, team=k[0], player=k[1], status=None, prev=o[0]))   # βγηκε απο τη λιστα (επεστρεψε)
        if ch:
            with open(F(INJ_HIST), 'a', encoding='utf-8') as fh:
                for r in ch: fh.write(json.dumps(r, ensure_ascii=False) + '\n')
    except Exception as e:
        print('ιστορικο τραυματιων σφαλμα —', e)
    json.dump(dict(fetched=now, teams=T), open(F('nba_injuries.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    return sum(len(v['players']) for v in T.values())

# 22/10/2026 (Στελιος «περνα τη μιξη στο live»): ΦΕΤΙΝΗ ΑΞΙΑ απο box score (nba_tests/t59 ΠΕΡΑΣΕ: LOSO M=500 5/5, RMSE 5/5· t61: η μιξη
# ειναι η πιο ακριβης σε καθε σημειο της σεζον). αξια = (φετινα λεπτα·box + 500·περσινη)/(φετινα λεπτα + 500) — ΜΟΝΟ στο χαντικαπ (v)·
# επιθεση/αμυνα (o/d, συνολα) μενουν περσινες. box = 14 ρυθμοι ανα λεπτο, φθορα 180 μερες, μαζεμα 300′ (nba_box_value_map.json).
BOXMAP = 'nba_box_value_map.json'
def _bx_vec(st):
    def pair(k):
        try: a, b = str(st.get(k) or '0-0').split('-'); return float(a), float(b)
        except Exception: return 0.0, 0.0
    def num(k):
        try: return float(str(st.get(k) or 0).replace('+', ''))
        except Exception: return 0.0
    fgm, fga = pair('fieldGoalsMade-fieldGoalsAttempted'); m3, a3 = pair('threePointFieldGoalsMade-threePointFieldGoalsAttempted')
    ftm, fta = pair('freeThrowsMade-freeThrowsAttempted')
    return [fgm - m3, (fga - a3) - (fgm - m3), m3, a3 - m3, ftm, fta - ftm, num('offensiveRebounds'), num('defensiveRebounds'), num('assists'),
            num('steals'), num('blocks'), num('turnovers'), num('fouls'), num('plusMinus')]

class BoxValue:
    """Φετινη αξια παικτη απο τα box score κανονικης περιοδου του nba_espn_games (μονο ματς ΠΡΙΝ την ημερα του ματς)."""
    def __init__(self, GM):
        try: self.M = json.load(open(F(BOXMAP), encoding='utf-8'))
        except Exception as e: self.M = None; print('φετινη αξια: απενεργη —', e)
        self.g = collections.defaultdict(list)                           # κλειδι ονοματος → [(μερα, 14 στατιστικα, λεπτα)]
        self.ids = {}                                                    # 24/10: κλειδι ονοματος → ESPN id (για το «Β», nba_boxB)
        try:
            import nba_boxB; self.B = nba_boxB.BoxB()
        except Exception as e: self.B = None; print('φετινη αξια Β: απενεργη —', e)
        for g in GM.values():
            if g.get('stype') != 2 or g.get('hs') is None or 'pstats' not in g: continue
            day = dt.date.fromisoformat(g['date']).toordinal(); keys = g.get('pkeys') or []
            for L in g['pstats'].values():
                for _, n, vals in L:
                    self.ids[nk(n)] = str(_)
                    st = dict(zip(keys, vals))
                    try: mn = float(st.get('minutes') or 0)
                    except Exception: mn = 0.0
                    if mn > 0: self.g[nk(n)].append((day, _bx_vec(st), mn))

    def value(self, k, gdate=None):
        """(φετινη αξια σε κλιμακα nba_player_values, φετινα λεπτα) ή (None, 0)."""
        if not self.M: return None, 0.0
        d = (dt.date.fromisoformat(gdate) if gdate else dt.datetime.now(dt.timezone.utc).date()).toordinal()
        L = [x for x in self.g.get(k, []) if x[0] < d]
        if not L: return None, 0.0
        mu, cf, H, M0 = self.M['mu'], self.M['coef'], self.M['half_life_days'], self.M['prior_min']
        ss = [0.0] * len(mu); ms = 0.0; raw = 0.0
        for day, vec, mn in L:
            w = 2.0 ** (-(d - day) / H)
            for i, x in enumerate(vec): ss[i] += w * x
            ms += w * mn; raw += mn
        return cf[0] + sum(c * ((ss[i] + M0 * mu[i]) / (ms + M0) - mu[i]) for i, c in enumerate(cf[1:])), raw

    def mix(self, k, v0, gdate=None):
        """μιξη περσινης (v0) με φετινη: (αξια, φετινη ή None, φετινα λεπτα)."""
        vb, raw = self.value(k, gdate)
        if vb is None or raw <= 0: return v0, None, 0.0
        # 24/10/2026 (Στελιος «φετινο με το Β · περνα το»): φετινο κομματι = «δικο μας box» (nba_boxB, t65/t66) με M 250·
        # αν λειπει (π.χ. χωρις play-by-play/παραμετρους) → η παλια φετινη box (t59) με M 500.
        if self.B is not None and k in self.ids:
            try:
                vB = self.B.value(self.ids[k], gdate or dt.datetime.now(dt.timezone.utc).date().isoformat())
            except Exception:
                vB = None
            if vB is not None:
                MB = float(self.B.P.get('M', 250.0))
                return (raw * vB + MB * v0) / (raw + MB), vB, raw
        Mx = float(self.M.get('mix_M', 500.0))
        return (raw * vb + Mx * v0) / (raw + Mx), vb, raw

class Absences:
    def __init__(self):
        self.V = json.load(open(F('nba_player_values.json'), encoding='utf-8'))['values']
        GM = json.load(open(F('nba_espn_games.json'), encoding='utf-8'))
        INJ = json.load(open(F('nba_injuries.json'), encoding='utf-8'))
        self.BV = BoxValue(GM)
        self.hist = collections.defaultdict(list); self.last = {}        # (ομαδα, παικτης) → λεπτα φετος · ομαδα → παικτες τελευταιου αγωνα
        for g in sorted(GM.values(), key=lambda g: g['utc']):
            if g.get('stype') != 2 or g.get('hs') is None: continue
            for t in (g['home'], g['away']):
                pl = {nk(n): mn for _, n, mn in g['players'].get(t, [])}
                for k, mn in pl.items():
                    if mn > 0: self.hist[(t, k)].append(mn)
                self.last[t] = {k for k, mn in pl.items() if mn > 0}
        self.off = None                                                   # 21/10: επισημη αναφορα NBA (nba_injrep_live) — μονο με διακοπτη «official»
        try:
            import nba_injrep_live as IL
            if IL.enabled(): self.off = IL.Official(); self._prob = IL.prob; self._ck = IL.ckey
        except Exception as e: print('επισημη αναφορα: απενεργη —', e)
        self.out = collections.defaultdict(list)
        for v in INJ.get('teams', {}).values():
            for x in v.get('players', []):
                n, stt = x[0], x[1]
                if str(stt or '').strip().lower() == 'out' and v.get('code'): self.out[v['code']].append(n)

    def team(self, t, gdate=None):
        """Απoντες ρολου της ομαδας: [dict(name, min, v, o, d, fresh, w, status)] (w = πιθανοτητα απουσιας· ESPN «Out» = 1)."""
        res = []
        if self.off is not None and gdate and self.off.covers(t, gdate):       # 21/10: επισημη αναφορα → καθε κατασταση με την πιθανοτητα της
            names = {self._ck(k_): k_ for (tt, k_) in self.hist if tt == t}
            for key, (stt, why, raw) in self.off.status(t, gdate).items():
                k = names.get(key)
                if k is None: continue                                   # δεν εχει παιξει φετος για την ομαδα → το εχει το ρόστερ (nba_roster_now)
                rec = self.hist.get((t, k), [])[-10:]
                mn = sum(rec) / len(rec)
                if mn < MIN_ROLE: continue
                w = self._prob(stt, mn)
                if w <= 0: continue
                v0, o, d = self.V.get(k, [V_UNK, REPO, REPD]); v, vb, mnow = self.BV.mix(k, v0, gdate)
                res.append(dict(name=raw, min=round(mn, 1), v=v, v0=v0, vbox=vb, min_now=mnow, o=o, d=d, fresh=k in self.last.get(t, set()), w=w, status=stt))
            return res
        for n in self.out.get(t, []):
            k = nk(n); rec = self.hist.get((t, k), [])[-10:]
            if not rec: continue                                   # δεν εχει παιξει φετος για την ομαδα → το εχει το roster prior
            mn = sum(rec) / len(rec)
            if mn < MIN_ROLE: continue
            v0, o, d = self.V.get(k, [V_UNK, REPO, REPD]); v, vb, mnow = self.BV.mix(k, v0, gdate)
            res.append(dict(name=n, min=round(mn, 1), v=v, v0=v0, vbox=vb, min_now=mnow, o=o, d=d, fresh=k in self.last.get(t, set()), w=1.0, status='Out'))
        return res

    def adjust(self, h, a, gdate=None):
        """(διορθωση περιθωριου γηπ, διορθωση συνολου, σκιωδες υπολοιπο, λιστες) για το ματς (gdate = ημερα ΗΠΑ, για την επισημη αναφορα)."""
        H, A_ = self.team(h, gdate), self.team(a, gdate)
        cost = lambda L: sum(p['w'] * (p['v'] - REP) * p['min'] / 48 for p in L)
        dm = ABS_K * (cost(A_) - cost(H))
        LO = sum(p['w'] * (p['o'] - REPO) * p['min'] / 48 for p in H + A_); LD = sum(p['w'] * (p['d'] - REPD) * p['min'] / 48 for p in H + A_)
        fr = [p for p in H + A_ if p['fresh']]
        shadow = SH_O * sum(p['w'] * (p['o'] - REPO) * p['min'] / 48 for p in fr) + SH_D * sum(p['w'] * (p['d'] - REPD) * p['min'] / 48 for p in fr)
        ob = [p for p in H + A_ if p['w'] >= 1.0]                     # 21/10 (συνολα Μ2δ): χαμενη επιθ./αμυνα μονο «Out» και με πιθανοτητες
        self.last_od = (sum((p['o'] - REPO) * p['min'] / 48 for p in ob), sum((p['d'] - REPD) * p['min'] / 48 for p in ob), LO, LD)
        return dm, C_O * LO + C_D * LD, shadow, H, A_
