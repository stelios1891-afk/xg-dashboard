# -*- coding: utf-8 -*-
"""nba_board.py — NBA: ΒΑΣΗ ΠΑΙΚΤΩΝ ανα ομαδα + «ΤΙ ΓΙΝΕΤΑΙ ΑΝ ΛΕΙΨΕΙ» + κινηση αγορας (20/10/2026, Στελιος:
«βαση δεδομενων παικτων ανα ομαδα … σε αμφιβολους/questionable να εχω πριν βγει η ειδηση την εικονα» ·
«οταν προκυπτει νεο pick να εμφανιζεται η κινηση της αγορας και η λιστα των παικτων»).
ΜΟΝΟ ΕΝΔΕΙΞΗ — δεν αλλαζει ουτε το μοντελο ουτε τα picks. Ιδιοι αριθμοι με το live (nba_absence):
  χαντικαπ: ο παικτης κοστιζει στην ομαδα 0.75 × (αξια − (−2)) × λεπτα/48 ποντους (αντικαταστατης −2 απο 20/10· ηταν −1)
  συνολο:   −0.5 × (επιθ. αξια + 0.5) × λεπτα/48 + 1.0 × (αμυντ. αξια + 0.5) × λεπτα/48
Λεπτα = μεσος στους ≤10 τελευταιους φετινους αγωνες κανονικης για την ομαδα· αν δεν εχει παιξει φετος → περσινα λεπτα/αγωνα.
«Ηδη στο μοντελο» = Out που μετρα ηδη η προβλεψη (παικτης ρολου ≥20′ που επαιξε φετος, ή εκτος αφετηριας ροστερ)."""
import os, json, collections, datetime as dt
from statistics import NormalDist
from nba_absence import nk, ABS_K, REP, REPO, REPD, MIN_ROLE, C_O, C_D, V_UNK
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
    # 20/10 (Στελιος «να δειχνει αυτο που μετραει πραγματικα το μοντελο»): οσοι ΔΕΝ εχουν παιξει φετος μετρανε μεσω ΑΦΕΤΗΡΙΑΣ (ροστερ),
    # οχι με τη φορμουλα απουσιας: διαφορα αξιας ροστερ με/χωρις αυτον (nba_live_roster: βαρη λεπτα/ματς, αγνωστοι −1 με 15′),
    # × βαρος αφετηριας που μενει ≈ 8/(8 + φετινα ματς ομαδας). Συνολα: η αφετηρια δεν αγγιζει τα συνολα → 0.
    gpt = collections.Counter()
    for g in GM.values():
        if g.get('stype') == 2 and g.get('hs') is not None: gpt[g['home']] += 1; gpt[g['away']] += 1
    def tv(ns_):
        vals = [BASE.get(nk(x), [-1.0, 15.0, 0.0])[:2] for x in ns_]
        if not vals: return 0.0
        w = [x[1] or 15.0 for x in vals]; tot = sum(w)
        return sum(5 * wi / tot * x[0] for wi, x in zip(w, vals))
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
            v, o, d = V.get(k, [V_UNK, REPO, REPD])
            im, it = impact(v, o, d, mn)
            ij = inj.get((t, k)); stt = ij[1] if ij else None
            played = bool(hist.get((t, k)))
            R = ROST.get(t, [])
            if played:
                how = 'απουσια' if mn >= MIN_ROLE else 'κατω απο 20′'
                if mn < MIN_ROLE: im, it = 0.0, 0.0                       # το live δεν μετρα απουσιες παικτων <20′
            else:
                how = 'αφετηρια'
                inR = n in R
                d_ = (tv(R) - tv([x for x in R if x != n])) if inR else (tv(R + [n]) - tv(R))
                im, it = max(d_, 0.0) * 8 / (8 + gpt.get(t, 0)), 0.0
            in_model = bool(ij) and str(stt).lower() == 'out' and ((played and mn >= MIN_ROLE) or (not played and n not in R))
            if mn < MIN_SHOW and not ij: continue
            rows.append(dict(name=n, min=round(mn, 1), msrc=src, gp=len(hist.get((t, k), [])), v=round(v, 2), o=round(o, 2), d=round(d, 2),
                             imp_m=round(im, 2), imp_t=round(it, 2), how=how, status=stt, itype=ij[2] if ij else None, idate=ij[3] if ij else None, in_model=in_model))
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
            L.append(f"  • {r['name']} — {gr_status(r['status'])} · {r['min']:.0f}′ ({r['msrc']}) · χαντικαπ {-r['imp_m']:+.1f} π.{' (αφετηρια)' if r.get('how') == 'αφετηρια' else ''}, συνολο {r['imp_t']:+.1f}"
                     + (' · ✓ ηδη στο μοντελο' if r['in_model'] else ''))
    return '\n'.join(L)


def _probs(m, tot, pin, sm, st):
    """Πιθανοτητες & δικαιες αποδοσεις μοντελου σε ΟΛΕΣ τις αγορες της τωρινης γραμμης Pinnacle (νικη, χαντικαπ, συνολο)."""
    N = NormalDist()
    ph = N.cdf(m / sm); r = dict(margin=m, total=tot, p_h=ph, p_a=1 - ph)
    if pin.get('line') is not None:
        L = float(pin['line']); pw, pp = _cover(m, L, sm); r.update(line=L, c_h=pw, c_a=1 - pw - pp, c_p=pp)
    if pin.get('tl') is not None:
        tl = float(pin['tl']); po, pp = _cover(tot, -tl, st); r.update(tl=tl, o=po, u=1 - po - pp, t_p=pp)
    return r


def whatif(g, pin, off_h, off_a, P, sm, st):
    """off_h / off_a = ονοματα που ΔΕΝ παιζουν (μαζι με οσους ειναι ηδη Out στο μοντελο). Παικτης που αφαιρεθηκε απο το Out
    → ξαναμπαινει (επιστροφη). → (πριν, μετα) με πιθανοτητες ολων των αγορων + dm/dt."""
    dm = dt_ = 0.0
    for code, off, sg in ((g['hcode'], set(off_h), -1), (g['acode'], set(off_a), 1)):
        for r in P.get(code, []):
            if r['name'] in off and not r['in_model']:
                dm += sg * r['imp_m']; dt_ += r['imp_t']
            elif r['name'] not in off and r['in_model']:
                dm -= sg * r['imp_m']; dt_ -= r['imp_t']
    m0, t0 = float(g['margin']), float(g['total'])
    return _probs(m0, t0, pin, sm, st), dict(_probs(m0 + dm, t0 + dt_, pin, sm, st), dm=dm, dt=dt_)


if __name__ == '__main__':
    import sys; sys.stdout.reconfigure(encoding='utf-8')
    P = players()
    for t in sorted(P)[:3]:
        print(t); [print('  ', r) for r in P[t][:6]]
    print(inj_text('CHO', 'BRK', 'Charlotte Hornets', 'Brooklyn Nets', P))
