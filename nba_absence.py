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
ABS_K, REP, REPO, REPD, MIN_ROLE = 0.75, -1.0, -0.5, -0.5, 20.0
C_O, C_D = -0.5, 1.0                       # συνολα: επιθεση / αμυνα που χανεται
SH_O, SH_D, SH_THR = 0.18, 1.28, 3.0       # σκιωδης κανονας (ξαφνικες απουσιες, κλεισιμο)

def nk(s):
    s = unicodedata.normalize('NFD', str(s)); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    s = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', s); return ' '.join(re.findall(r'[a-z]+', s))

def refresh_injuries():
    """Φρεσκια λιστα ESPN (σε καθε scan NBA)· σε σφαλμα μενει η παλια."""
    from nba_espn import get, B, TEAMNAME
    inj = get(f'{B}/injuries'); T = {}
    for t in inj.get('injuries', []):
        nm = t.get('displayName', '')
        T[nm] = dict(code=TEAMNAME.get(nm), players=[[x['athlete']['displayName'], x.get('status'), (x.get('type') or {}).get('description')] for x in t.get('injuries', [])])
    json.dump(dict(fetched=dt.datetime.now(dt.timezone.utc).isoformat(timespec='minutes'), teams=T), open(F('nba_injuries.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    return sum(len(v['players']) for v in T.values())

class Absences:
    def __init__(self):
        self.V = json.load(open(F('nba_player_values.json'), encoding='utf-8'))['values']
        GM = json.load(open(F('nba_espn_games.json'), encoding='utf-8'))
        INJ = json.load(open(F('nba_injuries.json'), encoding='utf-8'))
        self.hist = collections.defaultdict(list); self.last = {}        # (ομαδα, παικτης) → λεπτα φετος · ομαδα → παικτες τελευταιου αγωνα
        for g in sorted(GM.values(), key=lambda g: g['utc']):
            if g.get('stype') != 2 or g.get('hs') is None: continue
            for t in (g['home'], g['away']):
                pl = {nk(n): mn for _, n, mn in g['players'].get(t, [])}
                for k, mn in pl.items():
                    if mn > 0: self.hist[(t, k)].append(mn)
                self.last[t] = {k for k, mn in pl.items() if mn > 0}
        self.out = collections.defaultdict(list)
        for v in INJ.get('teams', {}).values():
            for n, stt, _ in v.get('players', []):
                if str(stt or '').strip().lower() == 'out' and v.get('code'): self.out[v['code']].append(n)

    def team(self, t):
        """Απoντες ρολου της ομαδας: [dict(name, min, v, o, d, fresh)]."""
        res = []
        for n in self.out.get(t, []):
            k = nk(n); rec = self.hist.get((t, k), [])[-10:]
            if not rec: continue                                   # δεν εχει παιξει φετος για την ομαδα → το εχει το roster prior
            mn = sum(rec) / len(rec)
            if mn < MIN_ROLE: continue
            v, o, d = self.V.get(k, [REP, REPO, REPD])
            res.append(dict(name=n, min=round(mn, 1), v=v, o=o, d=d, fresh=k in self.last.get(t, set())))
        return res

    def adjust(self, h, a):
        """(διορθωση περιθωριου γηπ, διορθωση συνολου, σκιωδες υπολοιπο, λιστες) για το ματς."""
        H, A_ = self.team(h), self.team(a)
        cost = lambda L: sum((p['v'] - REP) * p['min'] / 48 for p in L)
        dm = ABS_K * (cost(A_) - cost(H))
        LO = sum((p['o'] - REPO) * p['min'] / 48 for p in H + A_); LD = sum((p['d'] - REPD) * p['min'] / 48 for p in H + A_)
        fr = [p for p in H + A_ if p['fresh']]
        shadow = SH_O * sum((p['o'] - REPO) * p['min'] / 48 for p in fr) + SH_D * sum((p['d'] - REPD) * p['min'] / 48 for p in fr)
        return dm, C_O * LO + C_D * LD, shadow, H, A_
