"""calc_data.py — 28/9/2026 (Στελιος): «κομπιουτερακι» στις καρτες Value Picks.
Βαζεις την τιμη που βρισκεις ΤΩΡΑ (και γραμμη) → edge ανα μοντελο. Το edge ειναι ΓΡΑΜΜΙΚΟ στην τιμη:
edge(o) = a·o + b (ιδιοι τυποι με τον scanner: τεταρτα, κουρεμα MARGIN, βαθια φαβορι, Σχεδιο Β), οποτε στελνουμε στη σελιδα
μονο (a, b) ανα μοντελο & γραμμη και το JS υπολογιζει αμεσα. Ελαχιστη τιμη για οριο thr = (thr − b) / a.
"""
import picks
import intl_pricing as ip

STEPS = (-0.5, -0.25, 0.0, 0.25, 0.5)        # γραμμες γυρω απο τη γραμμη του pick


def _lin(ev):
    """(a, b) με ev(o) = a·o + b — ακριβες, αφου ολοι οι τυποι ειναι γραμμικοι στην τιμη."""
    e2, e3 = ev(2.0), ev(3.0)
    a = e3 - e2
    return [round(a, 6), round(e2 - 2 * a, 6)]


def _fmt(line, over):
    return f"{line:g}" if over else f"{'+' if line > 0 else ''}{line:g}"


def intl_calc(m, x):
    """Εθνικες: 3 μοντελα (Μ1 H, Μ2 A, Μ3 AV)· συναινεση = ≥2 με edge ≥ οριο (AH 10% με κουρεμα 3%, over 8%)."""
    over = x['mkt'] == 'OVER'
    side = 1 if x['side'] == 1 else -1
    models, lines = [], []
    vers = [(lab, (m.get('versions') or {}).get(v)) for lab, v in (('Μ1', 'H'), ('Μ2', 'A'), ('Μ3', 'AV'))]
    vers = [(lab, V) for lab, V in vers if V and V.get('xg_h') is not None]
    if not vers:
        return None
    for st in STEPS:
        ln = round(float(x['line']) + st, 2)
        if over and ln < 0.5:
            continue
        row = []
        for lab, V in vers:
            if over:
                row.append(_lin(lambda o, T=V['T'], L=ln: ip.over_ev(T, L, o)))
            else:
                dist = picks.gd_dist(max(V['xg_h'], .05), max(V['xg_a'], .05))
                dd = (picks.gd_dist(max(V['xg_h_D'], .05), max(V['xg_a_D'], .05))
                      if V.get('xg_h_D') is not None and V.get('xg_a_D') is not None else None)
                dx = ip.dist_for(dist, dd, ln)
                row.append(_lin(lambda o, dx=dx, L=ln: ip.ah_ev(dx, side, L, o, picks.MARGIN)))
        lines.append({'l': ln, 'lab': _fmt(ln, over), 'c': row})
    models = [lab for lab, _ in vers]
    return {'models': models, 'need': 2, 'thr': 0.08 if over else 0.10, 'lines': lines,
            'def': next(i for i, L in enumerate(lines) if abs(L['l'] - float(x['line'])) < 1e-9),
            'rng': None if over else [1.70, 2.10], 'minabs': None if over else 0.5, 'price': x.get('odds')}


def dom_calc(p):
    """Εγχωρια (CORE7): ενα μοντελο, ιδιος τυπος με scan_value (p_cover στη γραμμη, κουρεμα MARGIN), οριο 10%, τιμη 1.70-2.10."""
    if p.get('mxh') is None or p.get('mxa') is None:
        return None
    dist = picks.gd_dist(p['mxh'], p['mxa'])
    side = 1 if p['side'] == 1 else -1
    lines = []
    for st in STEPS:
        ln = round(float(p['hcap']) + st, 2)
        def ev(o, L=ln):
            pw, pp = picks.p_cover(dist, side, L)
            return pw * (o - 1) * (1 - picks.MARGIN) - (1 - pw - pp)
        lines.append({'l': ln, 'lab': _fmt(ln, False), 'c': [_lin(ev)]})
    return {'models': ['Μοντελο'], 'need': 1, 'thr': 0.10, 'lines': lines, 'def': 2, 'rng': [1.70, 2.10], 'minabs': None,
            'price': p.get('odds')}


def single_calc(p, thr):
    """Ευρωλιγκα (γραμμες .5, χωρις push/κουρεμα): μονο η γραμμη του pick· p = (1+edge)/τιμη → edge(o) = p·o − 1."""
    try:
        pr = (1 + float(p['edge'])) / float(p['odds'])
    except Exception:
        return None
    lab = p.get('bet') or f"{'+' if p['hcap'] > 0 else ''}{p['hcap']:g}"
    return {'models': ['Μοντελο'], 'need': 1, 'thr': thr, 'lines': [{'l': p['hcap'], 'lab': lab, 'c': [[round(pr, 6), -1.0]]}],
            'def': 0, 'rng': None, 'minabs': None, 'price': p.get('odds')}
