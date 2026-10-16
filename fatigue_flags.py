# -*- coding: utf-8 -*-
"""fatigue_flags.py — ΣΕΡΙ ΕΚΤΟΣ / ΚΟΥΡΑΣΗ: ΕΝΔΕΙΞΗ + ΣΚΙΑ (16/10/2026, Στελιος «καντο ναι»). ΔΕΝ μπαινει στο μοντελο.
Αφορμη: Ντορτμουντ/PSV/Γιουναιτεντ/Μπαρτσα με 3ο εκτος σερι στην UCL 20-21/10. Τεστ: ucl_away_streak_deep (−0.23 vs κλεισιμο, t −1.0) ·
ucl_away3_penalty_test (ποινη UCL A δ≈0.17: RMSE 3/4 αλλα picks ✗ · εγχωρια CORE7 μονο B «σερι ≥3 & ξεκουραση ≤3.5μ» περασε, n 46, δ 0.15-0.21).
1) ΕΝΔΕΙΞΗ (καρτα Value Picks + Telegram): φιλοξενουμενος που παιζει το 3ο+ συνεχομενο εκτος (εγχωρια + Ευρωπη· κυπελλα ΔΕΝ εχουμε) —
   «⚠ <ομαδα>: 3ο εκτος στη σειρα · ξεκουραση 3.1 μερες · 6.815 χλμ σε 14 μερες».
2) ΣΚΙΑ (fatigue_shadow.jsonl, ΜΙΑ εγγραφη ανα παραλλαγη/ματς/πλευρα, πρωτη φορα ≤72ω): τι θα εκανε η ποινη στα picks —
   UCL «A» (σερι ≥3, δ 0.17) · εγχωρια CORE7 «B» (σερι ≥3 ΚΑΙ ξεκουραση ≤3.5μ, δ 0.18). Ποινη = μετατοπιση υπεροχης δ υπερ γηπεδουχου
   (+δ/2 γηπ., −δ/2 φιλοξ. στα αναμενομενα γκολ — το συνολο μενει ιδιο). Κριση με πραγματικα δεδομενα (τελος σεζον / Ιανουαριος).
Ημερολογιο: data_*_2627.json / data_*_2026.json (παιγμενα εγχωρια) + match_projections_archive.json (επερχομενα CORE7) +
europe_fixtures_2627.json (Ευρωπη, και επερχομενα) + euq_fixtures.json (προκριματικα). Χλμ = αλυσιδα γηπεδων (venues.json)."""
import os, json, glob, math, datetime as dt

ROOT = os.path.dirname(os.path.abspath(__file__))
SHADOW_F = os.path.join(ROOT, 'fatigue_shadow.jsonl')
D_UCL, D_DOM = 0.17, 0.18          # δ (γκολ υπεροχης) απο ucl_away3_penalty_test (ολες οι σεζον)
STREAK_MIN, REST_MAX_DOM = 3, 3.5
ENTRY_H = 72.0
_NAT = ('AFCON', 'AFCONQ', 'AsianCup', 'CopaAmerica', 'EURO', 'EUROQ', 'Friendlies', 'GoldCup', 'WorldCup', 'Europe')
_EXTRA_LOC = {951893: (40.41, 49.87), 10217: (52.06, 4.38), 8149: (52.457, 13.568), 8463: (53.778, -1.572), 10171: (45.814, 9.072)}
_CAL = None
_LOC = None


def _utc(s):
    s = str(s or '').strip()
    if not s:
        return None
    try:
        if s[:4].isdigit():
            t = dt.datetime.fromisoformat(s.replace('Z', '+00:00')[:25])
        else:
            t = dt.datetime.strptime(s.split(', ', 1)[1].replace(' UTC', ''), '%b %d, %Y, %H:%M')
        return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)
    except Exception:
        return None


def _load(name, d):
    try:
        return json.load(open(os.path.join(ROOT, name), encoding='utf-8'))
    except Exception:
        return d


def _calendar():
    """{team_id: [(utc, home_id), ...]} ταξινομημενο, χωρις διπλα (ιδια μερα & ιδιο ζευγαρι)."""
    global _CAL
    if _CAL is not None:
        return _CAL
    games = {}
    def add(t, h, a):
        if t is None or h is None or a is None:
            return
        games[(t.date().isoformat(), int(h), int(a))] = t
    for f in glob.glob(os.path.join(ROOT, 'data_*_2627.json')) + glob.glob(os.path.join(ROOT, 'data_*_2026.json')):
        lg = os.path.basename(f)[5:-5].rsplit('_', 1)[0]
        if lg in _NAT or lg.startswith(('WCQ', 'NationsLeague')):
            continue
        D = _load(os.path.basename(f), {})
        for m in (D.values() if isinstance(D, dict) else D):
            try:
                add(_utc(m['date']), m['home']['id'], m['away']['id'])
            except Exception:
                pass
    for v in _load('match_projections_archive.json', {}).values():
        if isinstance(v, dict) and v.get('home_id') and v.get('away_id'):
            add(_utc(v.get('utc')), v['home_id'], v['away_id'])
    for fn in ('europe_fixtures_2627.json', 'euq_fixtures.json'):
        for k, L in _load(fn, {}).items():
            if fn == 'euq_fixtures.json' and not str(k).endswith('2627'):
                continue
            for m in L:
                add(_utc(m.get('utc')), m.get('hid'), m.get('aid'))
    cal = {}
    for (_, h, a), t in games.items():
        cal.setdefault(h, []).append((t, h)); cal.setdefault(a, []).append((t, h))
    for k in cal:
        cal[k].sort()
    _CAL = cal
    return cal


def _locs():
    global _LOC
    if _LOC is None:
        V = _load('venues.json', {})
        _LOC = {int(k): (v['lat'], v['lon']) for k, v in V.items() if v and v.get('lat')}
        for t, c in _EXTRA_LOC.items():
            _LOC.setdefault(t, c)
    return _LOC


def _km(p, q):
    if p is None or q is None:
        return 0.0
    r = math.pi / 180
    x = 0.5 - math.cos((q[0] - p[0]) * r) / 2 + math.cos(p[0] * r) * math.cos(q[0] * r) * (1 - math.cos((q[1] - p[1]) * r)) / 2
    return 12742 * math.asin(math.sqrt(max(x, 0)))


def away_state(tid, home_tid, ko):
    """Κατασταση του ΦΙΛΟΞΕΝΟΥΜΕΝΟΥ tid για ματς στο γηπεδο του home_tid την ωρα ko: σερι εκτος (μαζι με αυτο), ξεκουραση, χλμ 14 μερων."""
    try:
        tid, home_tid = int(tid), int(home_tid)
    except Exception:
        return None
    t = _utc(ko)
    if t is None:
        return None
    prev = [e for e in _calendar().get(tid, []) if e[0] < t - dt.timedelta(hours=6)]
    if not prev:
        return None
    s = 1
    for e in reversed(prev):
        if e[1] != tid:
            s += 1
        else:
            break
    rest = (t - prev[-1][0]).total_seconds() / 86400
    L = _locs(); home = L.get(tid)
    chain = [e for e in prev if (t - e[0]).total_seconds() / 86400 < 14] + [(t, home_tid)]
    k0 = len(prev) - len(chain) + 1
    start = (L.get(prev[k0 - 1][1]) if k0 - 1 >= 0 else home) if k0 - 1 >= 0 else home
    km14, here = 0.0, start
    for e in chain:
        nxt = L.get(e[1]) if e[1] is not None else home
        km14 += _km(here, nxt); here = nxt
    return dict(streak=s, rest=round(rest, 1), km14=round(km14))


def note(team, st):
    if not st or st['streak'] < STREAK_MIN:
        return None
    return (f"⚠ {team}: {st['streak']}ο εκτός στη σειρά · ξεκούραση {st['rest']:.1f} μέρες · "
            + f"{st['km14']:,.0f} χλμ σε 14 μέρες".replace(',', '.'))


def shift(xh, xa, d):
    """Ποινη: υπεροχη +d υπερ γηπεδουχου, ιδιο συνολο."""
    return max(xh + d / 2, 0.05), max(xa - d / 2, 0.05)


def _jsonl(p):
    try:
        return [json.loads(l) for l in open(p, encoding='utf-8') if l.strip()]
    except Exception:
        return []


def shadow_write(rows):
    """rows: dicts με key — γραφει μονο οσα δεν υπαρχουν ηδη (πρωτη εμφανιση)."""
    if not rows:
        return 0
    have = {r.get('key') for r in _jsonl(SHADOW_F)}
    new = [r for r in rows if r['key'] not in have]
    if new:
        with open(SHADOW_F, 'a', encoding='utf-8') as fh:
            for r in new:
                fh.write(json.dumps(r, ensure_ascii=False) + '\n')
    return len(new)
