# -*- coding: utf-8 -*-
"""nba_board.py — NBA: ΒΑΣΗ ΠΑΙΚΤΩΝ ανα ομαδα + «ΤΙ ΓΙΝΕΤΑΙ ΑΝ ΛΕΙΨΕΙ» + κινηση αγορας (20/10/2026, Στελιος:
«βαση δεδομενων παικτων ανα ομαδα … σε αμφιβολους/questionable να εχω πριν βγει η ειδηση την εικονα» ·
«οταν προκυπτει νεο pick να εμφανιζεται η κινηση της αγορας και η λιστα των παικτων»).
ΜΟΝΟ ΕΝΔΕΙΞΗ — δεν αλλαζει ουτε το μοντελο ουτε τα picks. Ιδιοι αριθμοι με το live (nba_absence):
  χαντικαπ: ο παικτης κοστιζει στην ομαδα 0.75 × (αξια − (−1)) × λεπτα/48 ποντους
  συνολο:   −0.5 × (επιθ. αξια + 0.5) × λεπτα/48 + 1.0 × (αμυντ. αξια + 0.5) × λεπτα/48
Λεπτα = μεσος στους ≤10 τελευταιους φετινους αγωνες κανονικης για την ομαδα· αν δεν εχει παιξει φετος → περσινα λεπτα/αγωνα.
«Ηδη στο μοντελο» = Out που μετρα ηδη η προβλεψη (παικτης ρολου ≥20′ που επαιξε φετος, ή εκτος αφετηριας ροστερ)."""
import os, json, collections, datetime as dt
from statistics import NormalDist
from nba_absence import nk, ABS_K, REP, REPO, REPD, MIN_ROLE, C_O, C_D
ROOT = os.path.dirname(os.path.abspath(__file__))
F = lambda n: os.path.join(ROOT, n)
MOVE_INJ = 1.5            # κινηση δικαιης γραμμης (ποντοι) απο το ανοιγμα → στο pick μπαινει και η λιστα απουσιων
MIN_SHOW = 8.0            # στη βαση: παικτες με ≥8′ (ή στη λιστα τραυματιων)
ST_GR = {'out': 'ΕΚΤΟΣ', 'day-to-day': 'αμφίβολος (DTD)', 'questionable': 'αμφίβολος (Q)', 'doubtful': 'μάλλον εκτός (D)', 'probable': 'πιθανόν παίζει'}


def _load(n, d):
    try:
        with open(F(n), encoding='utf-8') as fh: return json.load(fh)
    except Exception: return d


def _cover(mu, L, sig):
    from el_picks import cover
    return cover(mu, L, sig)


def gr_status(s):
    return ST_GR.get(str(s or '').strip().lower(), str(s or ''))


def impact(v, o, d, mn):
    """(ποντοι χαντικαπ που χανει η ομαδα, αλλαγη συνολου) αν λειψει ο παικτης."""
    return ABS_K * (v - REP) * mn / 48, C_O * (o - REPO) * mn / 48 + C_D * (d - REPD) * mn / 48


def players():
    """{κωδικος: [dict(name, min, msrc, gp, v, o, d, imp_m, imp_t, status, itype, idate, in_model)]} ταξινομημενα κατα επιδραση."""
    V = _load('nba_player_values.json', {}).get('values', {})
    BASE = _load('nba_roster_base.json', {}).get('players', {})
    RL = _load('nba_roster_live.json', {}); ROST = RL.get('roster', {})
    GM = _load('nba_espn_games.json', {}); INJ = _load('nba_injuries.json', {})
    hist = collections.defaultdict(list); names = {}
    for g in sorted(GM.values(), key=lambda g: g['utc']):
        if g.get('stype') != 2 or g.get('hs') is None: continue
        for t in (g['home'], g['away']):
            for _, n, mn in g['players'].get(t, []):
                if mn > 0: hist[(t, nk(n))].append(mn); names[(t, nk(n))] = n
    inj = {}
    for v in INJ.get('teams', {}).values():
        for x in v.get('players', []):
            if v.get('code'): inj[(v['code'], nk(x[0]))] = (x[0], x[1], x[2] if len(x) > 2 else None, x[3] if len(x) > 3 else None)
    teams = set(ROST) | {t for t, _ in hist} | {t for t, _ in inj}
    out = {}
    for t in teams:
        cand = {}
        for n in ROST.get(t, []): cand[nk(n)] = n
        for (tt, k), n in names.items():
            if tt == t: cand[k] = n
        for (tt, k), x in inj.items():
            if tt == t: cand.setdefault(k, x[0])
        rows = []
        for k, n in cand.items():
            rec = hist.get((t, k), [])[-10:]
            if rec: mn, src = sum(rec) / len(rec), 'φετος'
            else:
                b = BASE.get(k); mn, src = (float(b[1]), 'περσι') if b and b[1] else (0.0, '—')
            v, o, d = V.get(k, [REP, REPO, REPD])
            im, it = impact(v, o, d, mn)
            ij = inj.get((t, k)); stt = ij[1] if ij else None
            played = bool(hist.get((t, k)))
            in_model = bool(ij) and str(stt).lower() == 'out' and ((played and mn >= MIN_ROLE) or (not played and n not in ROST.get(t, [])))
            if mn < MIN_SHOW and not ij: continue
            rows.append(dict(name=n, min=round(mn, 1), msrc=src, gp=len(hist.get((t, k), [])), v=round(v, 2), o=round(o, 2), d=round(d, 2),
                             imp_m=round(im, 2), imp_t=round(it, 2), status=stt, itype=ij[2] if ij else None, idate=ij[3] if ij else None, in_model=in_model))
        out[t] = sorted(rows, key=lambda r: -r['imp_m'])
    return out


def fair_margin(L, oh, oa, sig):
    """Δικαιη αναμενομενη διαφορα γηπεδουχου απο γραμμη+αποδοσεις (χωρις περιθωριο, κανονικη σ)."""
    try:
        ph = (1 / oh) / (1 / oh + 1 / oa); return sig * NormalDist().inv_cdf(ph) - float(L)
    except Exception: return None


def move_note(p, f0, pin, sig):
    """«κινηση: Hornets +1 @1.95 → −3.5 @1.91 · δικαιη 2.9 π. ΚΟΝΤΡΑ/ΥΠΕΡ» για την πλευρα του pick (+ ποντοι κινησης για το κατωφλι)."""
    s = int(p['side']); team = p['home'] if s == 1 else p['away']
    L0, Lc = float(f0['line']) * s, float(pin['line']) * s
    o0 = f0['oh'] if s == 1 else f0['oa']; oc = pin['oh'] if s == 1 else pin['oa']
    m0 = fair_margin(f0['line'], f0['oh'], f0['oa'], sig); mc = fair_margin(pin['line'], pin['oh'], pin['oa'], sig)
    mv = None if m0 is None or mc is None else round((mc - m0) * s, 1)     # + = η αγορα πηγε ΥΠΕΡ της πλευρας μας
    txt = f"ανοιγμα {team} {L0:+g} @{float(o0):.2f} → τωρα {Lc:+g} @{float(oc):.2f}"
    if mv is not None:
        txt += (f" · αγορα {abs(mv):.1f} π. " + ('ΥΠΕΡ μας' if mv > 0 else 'ΚΟΝΤΡΑ μας')) if abs(mv) >= .3 else ' · ουσιαστικα ιδια'
    return txt, mv


def inj_text(hcode, acode, home, away, P=None):
    """Λιστα ESPN και των 2 ομαδων (μονο οσοι ειναι στη λιστα) με λεπτα & ποσο κοστιζουν· ✓ = ηδη μεσα στην προβλεψη."""
    P = P if P is not None else players(); L = []
    for c, nm in ((hcode, home), (acode, away)):
        rs = [r for r in P.get(c, []) if r['status']]
        if not rs: L.append(f"{nm}: καμια απουσια στη λιστα"); continue
        L.append(f"{nm}:")
        for r in rs:
            L.append(f"  • {r['name']} — {gr_status(r['status'])} · {r['min']:.0f}′ ({r['msrc']}) · χαντικαπ {-r['imp_m']:+.1f} π., συνολο {r['imp_t']:+.1f}"
                     + (' · ✓ ηδη στο μοντελο' if r['in_model'] else ''))
    return '\n'.join(L)


def whatif(g, pin, out_h, out_a, P, sm, st):
    """Νεα προβλεψη αν λειψουν επιπλεον οι out_h / out_a (ονοματα, οσοι ΔΕΝ ειναι ηδη στο μοντελο) + edge στην τωρινη γραμμη Pinnacle."""
    H = {r['name']: r for r in P.get(g['hcode'], [])}; A = {r['name']: r for r in P.get(g['acode'], [])}
    xh = [H[n] for n in out_h if n in H and not H[n]['in_model']]; xa = [A[n] for n in out_a if n in A and not A[n]['in_model']]
    dm = -sum(r['imp_m'] for r in xh) + sum(r['imp_m'] for r in xa); dt_ = sum(r['imp_t'] for r in xh + xa)
    m = float(g['margin']) + dm; tot = float(g['total']) + dt_
    res = dict(margin=round(m, 2), total=round(tot, 1), dm=round(dm, 2), dt=round(dt_, 2))
    if pin.get('line') is not None and pin.get('oh') and pin.get('oa'):
        L = float(pin['line']); pw, pp = _cover(m, L, sm)
        res.update(line=L, e_h=pw * float(pin['oh']) + pp - 1, e_a=(1 - pw - pp) * float(pin['oa']) + pp - 1)
    if pin.get('tl') is not None and pin.get('to') and pin.get('tu'):
        tl = float(pin['tl']); po, pp = _cover(tot, -tl, st)
        res.update(tl=tl, e_o=po * float(pin['to']) + pp - 1, e_u=(1 - po - pp) * float(pin['tu']) + pp - 1)
    return res


if __name__ == '__main__':
    import sys; sys.stdout.reconfigure(encoding='utf-8')
    P = players()
    for t in sorted(P)[:3]:
        print(t); [print('  ', r) for r in P[t][:6]]
    print(inj_text('CHO', 'BRK', 'Charlotte Hornets', 'Brooklyn Nets', P))
