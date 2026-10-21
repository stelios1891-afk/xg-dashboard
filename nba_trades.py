# -*- coding: utf-8 -*-
"""nba_trades.py — NBA: ΜΕΤΑΓΡΑΦΕΣ ΜΕΣΑ ΣΤΗ ΣΕΖΟΝ στην προβλεψη (20/10/2026, Στελιος «περνα το»).
Τεστ: nba_tests/t15_trades.py (5 σεζον, LOSO α 1.0 · αντικ. −2 · χωρις σβησιμο — ✓✓✓): RMSE 13.765 → 13.731 (5/5), picks ανοιγματος
ολη η σεζον +3.1 → +4.2%, Φεβ-Απρ +0.4 → +3.1% (4/5)· ματς μετα απο μεταγραφη +4.6 → +27.5μ (μεγαλες αλλαγες +1.9 → +11.9%, 5/5).
Πριν: το μοντελο αγνοουσε τις μεταγραφες (η ομαδα αλλαζε μονο σιγα σιγα απο τα αποτελεσματα) → υποτιμουσε την ενισχυμενη ομαδα ~1.7-2 π.
ΜΕΤΑΚΙΝΗΣΗ = παικτης που επαιξε ΦΕΤΟΣ (κανονικη περιοδος) για την ομαδα Α και τωρα ειναι στο ρόστερ ESPN της Β ή επαιξε για τη Β.
ΔΙΟΡΘΩΣΗ (καθε ματς, απο τη μετακινηση και μετα): κ = TRADE_K · 0.75 · (αξια + 2) · λεπτα/48 (ιδια φορμουλα με τις απουσιες)
  Β (ηρθε): +κ ΜΟΝΟ αν ειναι στο ρόστερ της και ΟΧΙ «Out» στη λιστα ESPN (τραυματιας δεν μετρα — οπως στο τεστ: «μονο οταν παιζει»)
    21/10/2026 (Στελιος «μηπως τους μετραμε μεσα και δεν παιζουν;» · «περνα»): ΚΑΙ ΜΟΝΟ αφου επαιξε το 1ο του ματς με τη Β (since) — 152/156
    αφιξεις της προθεσμιας εχασαν 1+ ματς πριν το ντεμπουτο, η ESPN δεν τους βαζει παντα «Out» (η επισημη αναφορα: «Trade Pending / Not With Team»).
  Α (εφυγε): −κ (απο τη στιγμη που φευγει· στη λιστα απουσιων της Α δεν θα ξαναεμφανιστει)
λεπτα = μ.ο. 10 τελευταιων με την Α φετος (≥5 ματς), αλλιως περσινα/ματς, αλλιως 15 (≤36) · αξια = nba_player_values (αγνωστος −1).
Μεταγραφες του καλοκαιριου ΔΕΝ μετρανε εδω (τις εχει η αφετηρια/ρόστερ). Κατασταση: build() → nba_trades.json (nba_refresh, καθε πρωι)."""
import os, json, datetime as dt, urllib.request, collections
from nba_absence import nk, ABS_K, REP, V_UNK
ROOT = os.path.dirname(os.path.abspath(__file__))
F = lambda n: os.path.join(ROOT, n)
TRADE_K = 1.0
MAX_MIN = 36.0
STATE = 'nba_trades.json'
_AB = {'BKN': 'BRK', 'CHA': 'CHO', 'GS': 'GSW', 'NO': 'NOP', 'NY': 'NYK', 'PHX': 'PHO', 'SA': 'SAS', 'UTAH': 'UTA', 'WSH': 'WAS'}
_H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0'}


def _load(n, d):
    try:
        with open(F(n), encoding='utf-8') as fh: return json.load(fh)
    except Exception: return d


def espn_rosters():
    """{ομαδα: {espn_id: ονομα}} απο το ESPN (ιδια πηγη με nba_live_roster)."""
    g = lambda u: json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=_H), timeout=40).read())
    out = {}
    for tm in g('https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams')['sports'][0]['leagues'][0]['teams']:
        tm = tm['team']; ab = _AB.get(tm['abbreviation'], tm['abbreviation'])
        out[ab] = {str(a['id']): a['displayName'] for a in g(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{tm['id']}/roster").get('athletes', [])}
    return out


def detect(GM, R, BASE, V, now):
    """Μετακινησεις φετος: λιστα dict(pid, name, from, to, since, min, v, on_roster)."""
    hist = collections.defaultdict(list)                     # pid → [(utc, team, name, min)]
    for g in sorted(GM.values(), key=lambda g: g['utc']):
        if g.get('stype') != 2 or g.get('hs') is None: continue
        for t in (g['home'], g['away']):
            for pid, name, mn in g['players'].get(t, []):
                if mn > 0: hist[str(pid)].append((g['utc'], t, name, mn))
    where = {pid: t for t, d in (R or {}).items() for pid in d}
    moves = []
    for pid, seq in hist.items():
        name = seq[-1][2]
        chain = []                                           # (απο, προς, ημερομηνια) απο τα box scores
        for (u0, t0, _, _), (u1, t1, _, _) in zip(seq, seq[1:]):
            if t1 != t0: chain.append((t0, t1, u1[:10]))
        last_t = seq[-1][1]
        if R and pid in where and where[pid] != last_t:      # στο ρόστερ αλλης ομαδας χωρις να εχει παιξει ακομα εκει
            chain.append((last_t, where[pid], None))
        for a, b, since in chain:
            old = [mn for u, t, _, mn in seq if t == a][-10:]
            if len(old) >= 5: mins = sum(old) / len(old)
            else:
                bb = BASE.get(nk(name)); mins = float(bb[1]) if bb and bb[1] else 15.0
            moves.append(dict(pid=pid, name=name, frm=a, to=b, since=since, min=round(min(mins, MAX_MIN), 1),
                              v=round(V.get(nk(name), [V_UNK])[0], 2), on_roster=(where.get(pid) == b) if R else True))
    return moves


def build(save=True):
    GM = _load('nba_espn_games.json', {}); V = _load('nba_player_values.json', {}).get('values', {})
    BASE = _load('nba_roster_base.json', {}).get('players', {})
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec='minutes')
    try: R = espn_rosters()
    except Exception as e:
        print('μεταγραφες: ρόστερ ESPN σφαλμα —', e); R = {}
    old = _load(STATE, {}); first = {f"{m['pid']}|{m['frm']}|{m['to']}": m.get('first_seen') for m in old.get('moves', [])}
    moves = detect(GM, R, BASE, V, now)
    for m in moves: m['first_seen'] = first.get(f"{m['pid']}|{m['frm']}|{m['to']}") or now
    if save:
        json.dump(dict(updated=now, season=_load('nba_roster_live.json', {}).get('season'), rosters_ok=bool(R), moves=moves),
                  open(F(STATE), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return moves


def _out_set():
    S = set()
    for v in _load('nba_injuries.json', {}).get('teams', {}).values():
        for x in v.get('players', []):
            if v.get('code') and str(x[1] or '').strip().lower() == 'out': S.add((v['code'], nk(x[0])))
    return S


def cost(m):
    return TRADE_K * ABS_K * (m['v'] - REP) * m['min'] / 48


def adjust(h, a, moves=None, out=None):
    """(διορθωση περιθωριου γηπεδουχου, λεπτομερειες) για το ματς h - a."""
    moves = moves if moves is not None else _load(STATE, {}).get('moves', [])
    out = out if out is not None else _out_set()
    dm = 0.0; det = []
    for m in moves:
        c = cost(m)
        for team, sg in ((h, 1), (a, -1)):
            if m['to'] == team and m.get('since') and m.get('on_roster', True) and (team, nk(m['name'])) not in out:   # 21/10: μονο αφου επαιξε
                dm += sg * c; det.append([team, m['name'], round(c, 2)])
            if m['frm'] == team:
                dm -= sg * c; det.append([team, m['name'], round(-c, 2)])
    return dm, det


if __name__ == '__main__':
    import sys; sys.stdout.reconfigure(encoding='utf-8')
    mv = build(save='--dry' not in sys.argv)
    print(f'μεταγραφες φετος: {len(mv)}')
    for m in mv[:20]: print(f"  {m['name']}: {m['frm']} → {m['to']} ({m['since'] or 'στο ρόστερ'}) · {m['min']}′ · αξια {m['v']:+.2f} · κ {cost(m):.2f}")
