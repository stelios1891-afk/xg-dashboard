"""
intl_pick_status.py — ΚΑΤΑΣΤΑΣΗ ενος καταγεγραμμενου pick εθνικων (συναινεση) τωρα (26/9/2026, εντολη Στελιου).

Ενα pick μπαινει στο ημερολογιο με την πρωτη εμφανιση· μετα η τιμη μπορει να πεσει (π.χ. Φινλανδια −2.5 1.99 → 1.91) και η συναινεση
να σπασει, και αργοτερα να ξαναγυρισει. Εδω: ειναι ακομα pick; αν οχι, τι edge δινει καθε μοντελο στην τωρινη τιμη και ποια τιμη
χρειαζεται για να ξαναγινει (η 2η μικροτερη «τιμη για edge 10%» — over: 8% — γιατι θελουμε 2 απο 3 μοντελα).
Χρησιμοποιειται απο το intl_picks_ledger.py (Telegram «επεσε» / «ξανα pick») και το dashboard (καρτες 🌐).
"""
VERS = (('H', 'Μ1'), ('A', 'Μ2'), ('AV', 'Μ3'))
ZONE_HI = 2.10          # AH picks μονο σε 1.70-2.10


def market_src(m):
    mk = m.get('market') or {}
    src = mk.get('source')
    if src and mk.get(src):
        return src, mk[src]
    for lab in ('pinnacle', 'matchbook', 'bovada', 'crown', 'sbobet'):
        if mk.get(lab):
            return lab, mk[lab]
    return '', {}


def status(row, m):
    """row = εγγραφη ledger (mkt, side 1/2/0, line) · m = ματς του intl_projections_dashboard.json.
    -> dict(active, cur_line, cur_odds, book, edges{Μ1: %}, need) ή None αν δεν υπαρχει αγορα."""
    for c in m.get('consensus') or []:
        if c['mkt'] == row['mkt'] and c['side'] == row['side']:
            return dict(active=True, cur_line=c['line'], cur_odds=c['odds'], book=c.get('book'),
                        edges={k: round(v * 100) for k, v in (c.get('edges') or {}).items()}, need=None, models=c.get('models'))
    src, b = market_src(m)
    if not b:
        return None
    E = m.get('edges') or {}
    edges, needs = {}, []
    if row['mkt'] == 'OVER':
        if b.get('ou_line') is None:
            return None
        line, odds = b['ou_line'], b.get('over')
        for v, lab in VERS:
            r = (E.get(v) or {}).get(src) or {}
            if r.get('over') is not None:
                edges[lab] = round(r['over'])
            if r.get('need_over'):
                needs.append(r['need_over'])
    else:
        if b.get('ah_line') is None:
            return None
        home = row['side'] == 1
        line = b['ah_line'] if home else -b['ah_line']
        odds = b.get('oh') if home else b.get('oa')
        for v, lab in VERS:
            r = (E.get(v) or {}).get(src) or {}
            e = r.get('ah_home' if home else 'ah_away')
            if e is not None:
                edges[lab] = round(e)
            nd = r.get('need_h' if home else 'need_a')
            if nd and nd <= ZONE_HI:
                needs.append(nd)
    needs.sort()
    return dict(active=False, cur_line=line, cur_odds=odds, book=src, edges=edges, need=(needs[1] if len(needs) >= 2 else None), models=None)


def describe(row, st, home, away):
    """κειμενο για Telegram/dashboard: «Φινλανδια −2.5: τωρα 1.91 (Bovada) · Μ1 +17 / Μ2 +1 / Μ3 +7 · ξανα pick απο ≥1.96»."""
    if row['mkt'] == 'OVER':
        what = f"Over {st['cur_line']:g}"
    else:
        what = f"{home if row['side'] == 1 else away} {st['cur_line']:+g}"
    eds = ' / '.join(f'{k} {v:+d}%' for k, v in st['edges'].items())
    s = f"{what}: τωρα {st['cur_odds']:.2f} ({str(st['book']).capitalize()})"
    if eds:
        s += f' · {eds}'
    if not st['active']:
        s += (f" · ξανα pick απο ≥{st['need']:.2f}" if st.get('need') else ' · δεν ξαναγινεται pick σε αυτη τη γραμμη (λιγοτερα απο 2 μοντελα)')
    return s
