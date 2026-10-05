"""bk_value.py — Value Picks μπασκετ (Ευρωλιγκα & EuroCup) για το dashboard (1/10/2026, Στελιος).
  • Τα picks που ΒΓΗΚΑΝ και μετα «χαθηκαν» (επεσε η αποδοση / αλλαξε η γραμμη) ΜΕΝΟΥΝ στη λιστα ως το τζαμπολ με «⚠ δεν ισχυει πια»
    (τωρινη γραμμη/αποδοση/edge Pinnacle) — γιατι μια εναλλακτικη γραμμη ή αλλο book του broker μπορει ακομα να περνα το οριο.
  • Κομπιουτερακι με ΕΠΙΛΟΓΗ ΓΡΑΜΜΗΣ: ±0.5 / ±1 / ±1.5 γυρω απο τη γραμμη (π.χ. Over 172.5 → 172 / 171.5 …) + τιμη → edge αμεσα.
    edge(τιμη) = P(νικη)·τιμη + P(push) − 1 με το ΙΔΙΟ μοντελο του scanner (διαφορα ~ N(margin, σ), συνολο ~ N(total, σ), push στις ακεραιες).
Πηγες: {el,ec}_value_latest.json (ενεργα picks) · {el,ec}_clv_bets.jsonl (οσα βγηκαν) · {el,ec}_projections.json · {el,ec}_odds_latest.json."""
import os, json, datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STEPS = (-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5)
THR = 0.08


def _load(name, d):
    try:
        with open(os.path.join(ROOT, name), encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:
        return d


def _cover(mu, L, sig):
    from el_picks import cover
    return cover(mu, L, sig)


def bk_calc(game, mkt, side, over, center, price, sm, st, team=None, thr=THR):
    """Γραμμες γυρω απο το center (γραμμη ΤΗΣ ΠΛΕΥΡΑΣ μας για χαντικαπ · γραμμη συνολου για over/under)· (a, b) με edge = a·τιμη + b."""
    lines = []
    for d in STEPS:
        L = round(float(center) + d, 1)
        if mkt == 'hcap':
            mt = float(game['margin']) if side == 1 else -float(game['margin'])
            pw, pp = _cover(mt, L, sm)
            lab = f"{team} {'+' if L >= 0 else ''}{L:g}"
        else:
            po, pp = _cover(float(game['total']), -L, st)
            pw = po if over else 1 - po - pp
            lab = f"{'Over' if over else 'Under'} {L:g}"
        lines.append({'l': L, 'lab': lab, 'c': [[round(pw, 6), round(pp - 1, 6)]]})
    return {'models': ['Μοντελο'], 'need': 1, 'thr': thr, 'lines': lines, 'def': STEPS.index(0.0), 'rng': None, 'minabs': None, 'price': price}


def rows(prefix, lg):
    """→ (λιστα καρτων, ωρα σαρωσης). prefix 'el' / 'ec'."""
    import bk_pick_status as bs
    lat = _load(f'{prefix}_value_latest.json', {})
    proj = _load(f'{prefix}_projections.json', {})
    odds = _load(f'{prefix}_odds_latest.json', {}).get('odds', {})
    games = {str(g['code']): g for g in proj.get('games', [])}
    sm, st = float(proj.get('sigma_margin', 11.5)), float(proj.get('sigma_total', 16.7))
    tthr = lambda g_: THR
    if prefix == 'ec':                     # 5/10: EuroCup συνολα = αγων 1-6 μιξη 50/50, 7+ μοντελο μονο του, edge ≥6% (ec_picks.tot_rule)
        try:
            from ec_picks import tot_mix, tot_rule
            tthr = lambda g_: tot_rule(g_)[1]
            for c_, g_ in list(games.items()):
                tm_ = tot_mix(g_, (odds.get(c_) or {}).get('pin') or {}, st)
                if tm_: games[c_] = dict(g_, total=tm_[0])
        except Exception:
            pass
    out, active = [], set()
    for p in lat.get('picks', []):
        q = dict(lg=lg, home=p['home'], away=p['away'], side=p['side'], hcap=p['hcap'], odds=p['odds'], edge=p['edge'],
                 proj_odds=p.get('proj_odds'), when=p['when'], el=True, mkt=p.get('mkt'), mkt_note=p.get('mkt_note'), drift=p.get('drift'),
                 old_agree=p.get('old_agree'), total_base=p.get('total_base'),
                 paper_late=bool(p.get('paper')), late_kind=p.get('late_kind'), travel=p.get('travel'), coach_notes=p.get('coach_notes'))
        if p.get('bet'):
            q['bet'] = p['bet']
        active.add((str(p['code']), p.get('mkt'), bs._dir(p.get('mkt'), p.get('side'), p.get('bet'))))
        g = games.get(str(p['code']))
        try:
            over = str(p.get('bet', '')).startswith('Over')
            team = p['home'] if p['side'] == 1 else p['away']
            q['calc'] = bk_calc(g, p['mkt'], p['side'], over, p['hcap'], p['odds'], sm, st, team, THR if p['mkt'] == 'hcap' else tthr(g)) if g else None
        except Exception:
            q['calc'] = None
        out.append(q)
    # ---- οσα βγηκαν και ΔΕΝ ειναι πια pick (ματς που δεν αρχισε) ----
    now = dt.datetime.now(dt.timezone.utc)
    for k, b in bs.open_bets(os.path.join(ROOT, f'{prefix}_clv_bets.jsonl'), now).items():
        if k in active:
            continue
        g = games.get(str(b['code']))
        if not g or g.get('played'):
            continue
        pin = (odds.get(str(b['code'])) or {}).get('pin') or {}
        over = str(b.get('bet') or '').startswith('Over')
        side = int(b['side']) if b['mkt'] == 'hcap' else 0
        team = b['home'] if side == 1 else b['away']
        q = dict(lg=lg, home=b['home'], away=b['away'], side=side, hcap=float(b['hcap']), odds=float(b['odds']), edge=float(b.get('edge') or 0),
                 proj_odds=None, when=b['when'], el=True, mkt=b['mkt'], gone=True)
        if b.get('bet'):
            q['bet'] = b['bet']
        try:
            cv = bs.current_view(b, g, pin, sm if b['mkt'] == 'hcap' else st, THR if b['mkt'] == 'hcap' else tthr(g), _cover)
        except Exception:
            cv = None
        q['gone_now'] = cv and dict(lab=cv[0], odds=cv[1], edge=cv[2], need=cv[3])
        # κομπιουτερακι: κεντρο = η ΤΩΡΙΝΗ γραμμη της αγορας (αν υπαρχει), αλλιως η γραμμη που μπηκαμε
        if b['mkt'] == 'hcap':
            cen = (float(pin['line']) if side == 1 else -float(pin['line'])) if pin.get('line') is not None else float(b['hcap'])
            pr = (pin.get('oh') if side == 1 else pin.get('oa')) or b['odds']
        else:
            cen = float(pin['tl']) if pin.get('tl') is not None else float(b['hcap'])
            pr = (pin.get('to') if over else pin.get('tu')) or b['odds']
        try:
            q['calc'] = bk_calc(g, b['mkt'], side, over, cen, float(pr), sm, st, team, THR if b['mkt'] == 'hcap' else tthr(g))
        except Exception:
            q['calc'] = None
        out.append(q)
    return out, lat.get('scanned_at')
