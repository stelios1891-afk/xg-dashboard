"""
red_modes.py — 5/10/2026 (Στελιος): ΦΟΡΜΟΥΛΕΣ ΔΙΟΡΘΩΣΗΣ ΚΟΚΚΙΝΩΝ στις εισοδους της μηχανης (σωστη κατευθυνση: αναιρουμε την κοκκινη,
ωστε τα ratings να δειχνουν 11 vs 11). Πηγη αριθμων: red_effect_study.py (1.029 ματς) + βιβλιογραφια.
team_adj(m, mode) → {team_id: dict(fc=πολλαπλ. για συμπιεσμενο npxG, fr=για ωμο npxG, fn=για σουτ, term=προσθετο xG)}
Τροποι:
  emp   = ΕΜΠΕΙΡΙΚΗ: σουτ ομαδας με λιγοτερους ×1.72 (2+ λιγοτεροι ×2.5) · ομαδα με περισσοτερους −0.0072 xG/λεπτο υπεροχης (σουτ αναλογικα)
  emps  = ΕΜΠΕΙΡΙΚΗ ανα σκορ τη στιγμη της 1ης κοκκινης: 10αρα μπροστα ×2.17 / −1.04 ανα 90′ · ισοπαλια ×1.72 / −0.62 · πισω ×1.45 / −0.44
  skrip = Skripnikov et al. 2025: με λιγοτερους ×1.8 (2+: ×2.5) · με περισσοτερους ×0.75 (2+: ×0.55)
  caley = Caley: με λιγοτερους ×1.4 · με περισσοτερους ÷1.4
  empa  = ΕΜΠΕΙΡΙΚΗ ΠΡΟΣΘΕΤΙΚΗ: με λιγοτερους +0.0058 xG/λεπτο (μεσος ορος απωλειας) · με περισσοτερους −0.0072 xG/λεπτο
  (προσθετο term → οι καταναλωτες προσθετουν και term/0.10 «σουτ», οπως η live)
(Η live φορμουλα — +0.0083/λεπτο ΣΤΟΝ πλεονεκτουντα — μενει στους κωδικες της· εδω μονο οι νεες.)
"""
LIVE_MODE = 'emps'      # 5/10/2026 αποφαση Στελιου («βαλε αυτη που διαλεξε το LOSO»): εμπειρικη ανα σκορ — ΑΝΤΙΚΑΘΙΣΤΑ την παλια
                        # +0.0083/λεπτο ΣΤΟΝ πλεονεκτουντα (λαθος κατευθυνση). Ακριβεια 4/4 CORE7 (LOSO 5/5), Βραζ 4/4, MLS 5/6·
                        # picks CORE7 15+ ~1 SE κατω απο την παλια (Pinnacle +73 vs +89u, Crown +83 vs +80u) — δεκτο ρητα απο τον Στελιο.

def live_adj(m):
    """{team_id: dict(fr, fc, fn, term)} με τη LIVE φορμουλα (για τους builders εισοδων)."""
    return team_adj(m, LIVE_MODE)

def ns_eff(ns, pen, red):
    """«σουτ» με το προσθετο xG της κοκκινης ως ψευδο-σουτ 0.10 (με προσημο)· ποτε κατω απο το μισο των πραγματικων."""
    return max(ns + pen + red / 0.10, 0.5 * (ns + pen))

CW = lambda x: 1.0 if x <= .2 else (.45 if x <= .4 else (.25 if x <= .5 else (.15 if x <= .7 else .05)))
EMP_ATT = 1.72; EMP_DEF = 0.0072; EMP_ATT_ADD = 0.0058
EMPS = {'ahead': (2.17, 1.04 / 90), 'level': (1.72, 0.62 / 90), 'behind': (1.45, 0.44 / 90)}

def team_adj(m, mode):
    H, A = int(m['home']['id']), int(m['away']['id'])
    reds = sorted(((r.get('min') or 0), bool(r.get('home'))) for r in (m.get('reds') or []))
    out = {H: dict(fc=1., fr=1., fn=1., term=0.), A: dict(fc=1., fr=1., fn=1., term=0.)}
    if not reds or mode in (None, 'live', 'none'):
        return out
    def diff_at(team, mn):                 # >0 = η ομαδα εχει τοσους λιγοτερους
        own = sum(1 for t, h in reds if t < mn and (h == (team == H)))
        opp = sum(1 for t, h in reds if t < mn and (h != (team == H)))
        return own - opp
    shots = [s for s in m.get('shots') or [] if s.get('xg') is not None and s.get('sit') != 'Penalty']
    # σκορ τη στιγμη της 1ης κοκκινης (για emps)
    r0, r0home = reds[0]; ten = H if r0home else A
    g = {H: 0, A: 0}
    for s in shots:
        if s.get('goal') and (s.get('min') or 0) <= r0 and s.get('tid') in g: g[s['tid']] += 1
    st = 'ahead' if g[ten] > g[H if ten == A else A] else ('level' if g[H] == g[A] else 'behind')
    for team in (H, A):
        raw = comp = n = 0.; raw2 = comp2 = n2 = 0.; post_raw_up = 0.; up_min = 0
        for s in shots:
            if s.get('tid') != team: continue
            x = s['xg']; d = diff_at(team, s.get('min') or 0); f = 1.0
            if d >= 1:                                         # παιζει με λιγοτερους
                f = {'emp': EMP_ATT if d == 1 else 2.5, 'emps': EMPS[st][0] if d == 1 else 2.5,
                     'skrip': 1.8 if d == 1 else 2.5, 'caley': 1.4}.get(mode, 1.0)
            elif d <= -1:                                      # παιζει με περισσοτερους
                f = {'skrip': 0.75 if d == -1 else 0.55, 'caley': 1 / 1.4}.get(mode, 1.0)
                post_raw_up += x
            raw += x; comp += x * CW(x); n += 1
            raw2 += x * f; comp2 += x * CW(x) * f; n2 += f
        term = 0.
        if mode == 'empa':
            dn = sum(1 for mn in range(96) if diff_at(team, mn) >= 1); up_min = sum(1 for mn in range(96) if diff_at(team, mn) <= -1)
            term = EMP_ATT_ADD * dn - min(EMP_DEF * up_min, 0.7 * post_raw_up)
        if mode in ('emp', 'emps'):
            up_min = sum(1 for mn in range(96) if diff_at(team, mn) <= -1)
            rate = EMP_DEF if mode == 'emp' else EMPS[st][1]
            term = -min(rate * up_min, 0.7 * post_raw_up)       # δεν αφαιρουμε περισσοτερο απο το 70% του xG που εβγαλε με παικτη παραπανω
        out[team] = dict(fc=comp2 / comp if comp else 1., fr=raw2 / raw if raw else 1., fn=n2 / n if n else 1., term=term)
    return out
