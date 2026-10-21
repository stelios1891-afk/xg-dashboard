# -*- coding: utf-8 -*-
"""xi_formula.py — 21/10/2026: Η ΦΟΡΜΟΥΛΑ ΕΝΔΕΚΑΔΑΣ (ερευνα απουσιων 20-21/10) ως βιβλιοθηκη για την καταγραφη/σκια (lineup_window.py).
  Δ ομαδας = ενδεκαδα − ΣΥΝΗΘΙΣΜΕΝΗ (11 με τα περισσοτερα λεπτα στα 10 τελευταια ματς πρωταθληματος: 1 τερματοφυλακας + 10)
  ΧΑΝΤΙΚΑΠ: διορθωση υπεροχης γηπ. = G_V·(ΔV_γ − ΔV_φ) + G_T·(ΔT_γ − ΔT_φ)
     V = μεσος ln(αξιας) των 11 · T = εμπιστοσυνη προπονητη (μεριδιο λεπτων οταν ειναι στην αποστολη, 10 ματς)
  ΣΥΝΟΛΑ: διορθωση συνολου = Σ_k B_k·(Δk_γ + Δk_φ), k = VO, VD (αξια επιθ./αμυνας) · TO, TD (εμπιστοσυνη επιθ./αμυνας) · XGI (αθροισμα xG+xA/90)
  Συντελεστες απο 2223-2526 (xi_pred2627: πραγματικη 11αδα vs συνηθισμενη, LOSO-σταθεροι). Πηγες ΜΟΝΟ αρχεια του repo:
  squads_2627.json (+core7_squads.json αν υπαρχει τοπικα) · player_matches(_2627).json (θεσεις, αξιες) · player_xgi.jsonl (xG/xA ανα παικτη)."""
import os, json, math, collections, datetime as dt
ROOT = os.path.dirname(os.path.abspath(__file__))
G_V, G_T = 0.024, 0.875
B = dict(VO=-0.015, VD=-0.031, TO=0.240, TD=-0.051, XGI=0.136)
_STATE = None


def _j(name, default=None):
    p = os.path.join(ROOT, name)
    if not os.path.exists(p): return default
    with open(p, encoding='utf-8') as f: return json.load(f)


def state():
    """Φορτωνει ιστορικο λεπτων ανα ομαδα (πρωταθλημα), θεσεις, αξιες, ρυθμους xGI. Μια φορα ανα εκτελεση."""
    global _STATE
    if _STATE is not None: return _STATE
    SQ = dict(_j('core7_squads.json', {}) or {}); SQ.update(_j('squads_2627.json', {}) or {})
    PM = dict(_j('player_matches.json', {}) or {}); PM.update(_j('player_matches_2627.json', {}) or {})
    DATES = {}
    for name in os.listdir(ROOT):
        if name.startswith('data_') and name.endswith('.json') and any(lg in name for lg in ('EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'Eredivisie', 'PrimeiraLiga')):
            try:
                for k, v in (_j(name, {}) or {}).items():
                    try: DATES[str(k)] = dt.datetime.strptime(v['date'], '%a, %b %d, %Y, %H:%M UTC')
                    except Exception: pass
            except Exception: pass
    order = sorted([k for k in SQ if k in DATES], key=lambda k: DATES[k])
    team_hist = collections.defaultdict(list)
    for k in order:
        for fs in ('h', 'a'):
            s = SQ[k].get(fs)
            if s and s.get('t') is not None: team_hist[int(s['t'])].append({str(p): mn for p, mn in s['p'].items()})
    pos, val = {}, {}
    for k in sorted(PM, key=lambda k: DATES.get(k, dt.datetime(2000, 1, 1))):
        for fs in ('h', 'a'):
            for e in ((PM.get(k) or {}).get(fs) or {}).get('p', []) or []:
                pos[str(e[0])] = e[3] if e[3] in (0, 1, 2, 3) else 2
                if len(e) > 2 and e[2]: val[str(e[0])] = e[2]
    st, acc = {}, collections.defaultdict(lambda: [0.0, 0.0])
    xrows = []
    p = os.path.join(ROOT, 'player_xgi.jsonl')
    if os.path.exists(p):
        with open(p, encoding='utf-8') as f:
            for l in f:
                try: r = json.loads(l); xrows.append((DATES.get(r['mid'], dt.datetime(2000, 1, 1)), r['p']))
                except Exception: pass
    xrows.sort(key=lambda x: x[0])
    for _, rows in xrows:
        for pid, (mn, xg, xa) in rows.items():
            if mn and mn > 0:
                s = st.get(pid, [0.0, 0.0]); st[pid] = [s[0] * 0.95 + xg + xa, s[1] * 0.95 + mn / 90.0]
                a = acc[pos.get(pid, 2)]; a[0] += xg + xa; a[1] += mn / 90.0
    mu = {k: v[0] / v[1] for k, v in acc.items() if v[1] > 0}
    _STATE = dict(team_hist=team_hist, pos=pos, val=val, xgi=st, mu=mu)
    return _STATE


def team_delta(tid, xi, xi_values=None):
    """Δ της ενδεκαδας xi (λιστα FotMob ids) vs τη συνηθισμενη της ομαδας tid. xi_values: {pid: αξια} απο τη σημερινη ενδεκαδα (FotMob)."""
    S = state(); hist = S['team_hist'].get(int(tid), [])[-10:]
    if len(hist) < 4 or not xi or len(xi) < 9: return None
    xi = [str(p) for p in xi]; vals = dict(S['val']); vals.update({str(k): v for k, v in (xi_values or {}).items() if v})
    mins = collections.Counter()
    for h in hist:
        for p, mn in h.items(): mins[p] += mn
    pool = [p for p, mn in mins.most_common() if mn > 0]
    usual = [p for p in pool if S['pos'].get(p, 2) == 0][:1] + [p for p in pool if S['pos'].get(p, 2) != 0][:10]
    def trust(p):
        ins = [h[p] for h in hist if p in h]; return sum(ins) / (90.0 * len(ins)) if ins else 0.3
    def lv(p):
        v = vals.get(p); return math.log(v) if v else None
    def xgi(p):
        s = S['xgi'].get(p); m = S['mu'].get(S['pos'].get(p, 2), 0.25); return (s[0] + 5 * m) / (s[1] + 5) if s else m
    def mean(xs):
        xs = [x for x in xs if x is not None]; return sum(xs) / len(xs) if xs else None
    def feats(x):
        vs = [lv(p) for p in x]; o = [p for p in x if S['pos'].get(p, 2) in (2, 3)]; d = [p for p in x if S['pos'].get(p, 2) in (0, 1)]
        return dict(V=mean(vs), T=mean([trust(p) for p in x]), XGI=sum(xgi(p) for p in x),
                    TO=mean([trust(p) for p in o]), TD=mean([trust(p) for p in d]),
                    VO=mean([lv(p) for p in o]), VD=mean([lv(p) for p in d]))
    F, G = feats(usual), feats(xi)
    out = {k: (G[k] - F[k]) if (G[k] is not None and F[k] is not None) else 0.0 for k in F}
    out['out_of_usual'] = [p for p in usual if p not in xi]; out['n_changes'] = len(out['out_of_usual'])
    return out


def adjust(dh, da):
    """(διορθωση υπεροχης γηπεδουχου, διορθωση συνολου) σε γκολ — None αν λειπει η μια ομαδα."""
    if dh is None or da is None: return None, None
    gd = G_V * (dh['V'] - da['V']) + G_T * (dh['T'] - da['T'])
    tot = sum(B[k] * (dh[k] + da[k]) for k in B)
    return gd, tot
