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
    if '1Χ2' in str(row.get('book', '')):        # 2/10: pick ΝΙΚΗΣ (= −0.5 απο το 1Χ2) → κρινεται στην ΤΙΜΗ 1Χ2, οχι στη γραμμη χαντικαπ
        return _status_x12(row, m, src, b)
    E = m.get('edges') or {}
    edges, needs, raw = {}, [], {}
    if row['mkt'] == 'OVER':
        if b.get('ou_line') is None:
            return None
        line, odds = b['ou_line'], b.get('over')
        for v, lab in VERS:
            r = (E.get(v) or {}).get(src) or {}
            if r.get('over') is not None:
                edges[lab] = round(r['over']); raw[lab] = r['over']
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
                edges[lab] = round(e); raw[lab] = e
            nd = r.get('need_h' if home else 'need_a')
            if nd:      # 1/10: χωρις ανω οριο — για pick που ηδη σταλθηκε, καλυτερη τιμη ειναι παντα δεκτη
                needs.append(nd)
    needs.sort()
    # 1/10/2026 (Στελιος, Ολλανδια −0.5 @2.09 → 2.15): pick που ΣΤΑΛΘΗΚΕ δεν «πεφτει» επειδη η τιμη εγινε ΚΑΛΥΤΕΡΗ (πανω απο το 2.10).
    # Ενεργο αν η γραμμη ειναι ιδια ή καλυτερη για εμας ΚΑΙ ≥2 μοντελα δινουν ακομα το κατωφλι (AH 10% · over 8%) — χωρις ανω οριο τιμης.
    thr = 8 if row['mkt'] == 'OVER' else 10
    same_or_better = (line <= row['line'] + 1e-9) if row['mkt'] == 'OVER' else (line >= row['line'] - 1e-9)
    if same_or_better and sum(1 for v in raw.values() if v >= thr - 1e-9) >= 2:   # ακριβη (οχι στρογγυλεμενα) edges
        return dict(active=True, cur_line=line, cur_odds=odds, book=src, edges=edges, need=None, models=None, above_cap=True)
    return dict(active=False, cur_line=line, cur_odds=odds, book=src, edges=edges, need=(needs[1] if len(needs) >= 2 else None), models=None)


def _status_x12(row, m, src, b):
    """Ενεργο αν ≥2 μοντελα δινουν edge ≥10% στη ΝΙΚΗ με την τωρινη τιμη 1Χ2 — ΧΩΡΙΣ ανω οριο (σταλμενο pick: καλυτερη τιμη = δεκτη)."""
    import picks, intl_pricing as ip
    home = row['side'] == 1
    odds = b.get('o1') if home else b.get('o2')
    if not odds:
        return None
    edges, raw, needs = {}, {}, []
    for v, lab in VERS:
        V = (m.get('versions') or {}).get(v)
        if not V or V.get('xg_h') is None:
            continue
        dist = picks.gd_dist(max(V['xg_h'], .05), max(V['xg_a'], .05))
        e = ip.ah_ev(dist, 1 if home else -1, -0.5, odds, picks.MARGIN)
        raw[lab] = 100 * e; edges[lab] = round(100 * e)
        pw = sum(q for k, q in dist.items() if (k > 0 if home else k < 0))
        if pw > 0:
            needs.append(1 + (1.10 - pw) / (pw * (1 - picks.MARGIN)))
    needs.sort()
    act = odds >= 1.70 and sum(1 for x in raw.values() if x >= 10 - 1e-9) >= 2
    return dict(active=act, cur_line=-0.5, cur_odds=odds, book=src, edges=edges,
                need=None if act else (needs[1] if len(needs) >= 2 else None), models=None, x12=True)


def describe(row, st, home, away):
    """κειμενο για Telegram/dashboard: «Φινλανδια −2.5: τωρα 1.91 (Bovada) · Μ1 +17 / Μ2 +1 / Μ3 +7 · ξανα pick απο ≥1.96»."""
    if row['mkt'] == 'OVER':
        what = f"Over {st['cur_line']:g}"
    elif st.get('x12'):
        what = f"{home if row['side'] == 1 else away} νικη (1Χ2)"
    else:
        what = f"{home if row['side'] == 1 else away} {st['cur_line']:+g}"
    eds = ' / '.join(f'{k} {v:+d}%' for k, v in st['edges'].items())
    s = f"{what}: τωρα {st['cur_odds']:.2f} ({str(st['book']).capitalize()})"
    if eds:
        s += f' · {eds}'
    if not st['active']:
        s += (f" · ξανα pick απο ≥{st['need']:.2f}" if st.get('need') else ' · δεν ξαναγινεται pick σε αυτη τη γραμμη (λιγοτερα απο 2 μοντελα)')
    return s
