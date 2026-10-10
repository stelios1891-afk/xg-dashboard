"""fb_value.py — Value Picks ΠΟΔΟΣΦΑΙΡΟ: picks που ΒΓΗΚΑΝ και μετα «χαθηκαν» (επεσε η αποδοση / αλλαξε η γραμμη) ΜΕΝΟΥΝ στη λιστα
ως τη σεντρα με «⚠ δεν ισχυει πια» + τωρινη γραμμη/τιμη (1/10/2026, Στελιος: «να παραμενουν, να μπορεις να αλλαξεις line & αποδοση»).
  • CORE7 (εγχωρια): clv_bets.jsonl (οχι paper) vs value_picks_latest · τωρα = τελευταια Pinnacle στο odds_history.jsonl ·
    κομπιουτερακι = calc_data.dom_calc (ιδιος τυπος με scanner, γραμμες ±0.25/±0.5 γυρω απο την ΤΩΡΙΝΗ γραμμη).
  • Ευρωπαϊκα: euro_picks_ledger.jsonl vs euro_value_latest · τωρα = euro_odds_latest (κομπιουτερακι δεν υπαρχει για τα ευρωπαϊκα).
  • Εθνικες: intl_picks_ledger.jsonl (ΣΥΝΑΙΝΕΣΗ, οχι removed) vs τωρινη συναινεση · τωρα = αγορα του ματς · κομπιουτερακι = calc_data.intl_calc.
Ιδιο κλειδι «ιδια αγορα & πλευρα»: αν ειναι ακομα pick σε αλλη γραμμη → ΔΕΝ θεωρειται χαμενο."""
import os, json, datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _jsonl(name):
    out = []
    try:
        with open(os.path.join(ROOT, name), encoding='utf-8') as fh:
            for ln in fh:
                if ln.strip():
                    try: out.append(json.loads(ln))
                    except Exception: pass
    except FileNotFoundError:
        pass
    return out


def _load(name, d):
    try:
        with open(os.path.join(ROOT, name), encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:
        return d


def _ko(s):
    s = str(s).replace(' ', 'T').replace('Z', '')[:16]
    return dt.datetime.fromisoformat(s).replace(tzinfo=dt.timezone.utc)


def _now_tag(lab, od, a_b, thr):
    """(περιγραφη, τιμη, [a, b]) → dict για την ετικετα «τωρα» (edge = a·τιμη + b· χρειαζεται = (thr − b)/a)."""
    if od is None or a_b is None:
        return dict(lab=lab, odds=od, edge=None, need=None) if lab else None
    a, b = a_b
    return dict(lab=lab, odds=od, edge=a * od + b, need=((thr - b) / a) if a > 0 else None)


def core7_gone(active):
    """active: τα τωρινα εγχωρια picks (καρτες). → καρτες «⚠ δεν ισχυει πια»."""
    import calc_data
    now = dt.datetime.now(dt.timezone.utc)
    act = {(p['lg'], p['home'], p['away'], p['side']) for p in active}
    first = {}
    for b in _jsonl('clv_bets.jsonl'):
        if b.get('paper'):
            continue
        try: ko = _ko(b['ko'])
        except Exception: continue
        if ko <= now: continue
        k = (b['lg'], b['home'], b['away'], b['side'])
        if k not in first or b['seen'] < first[k]['seen']: first[k] = b
    if not first:
        return []
    last = {}
    for r in _jsonl('odds_history.jsonl'):
        if r.get('pin') and not r.get('inplay'):
            k = (r.get('lg'), r.get('home'), r.get('away'))
            if k not in last or r['t'] > last[k]['t']: last[k] = r
    out = []
    for k, b in first.items():
        if k in act:
            continue
        side = int(b['side']); r = last.get(k[:3]) or {}
        pin = r.get('pin')
        cen = (pin[0] if side == 1 else -pin[0]) if pin else float(b['hcap'])
        price = (pin[1] if side == 1 else pin[2]) if pin else float(b['odds'])
        role = 'fav' if float(b['hcap']) <= -0.5 else None
        q = dict(lg=b['lg'], home=b['home'], away=b['away'], home_id=b.get('hid'), away_id=b.get('aid'), side=side, hcap=float(b['hcap']),
                 odds=float(b['odds']), edge=float(b.get('edge') or 0), proj_odds=None, when=str(b['ko'])[:16], gone=True, role=role,
                 mxh=b.get('mxh'), mxa=b.get('mxa'), stake_final=0.0)
        try:
            c = calc_data.dom_calc(dict(mxh=b.get('mxh'), mxa=b.get('mxa'), side=side, hcap=cen, role=role, odds=price))
        except Exception:
            c = None
        q['calc'] = c
        team = b['home'] if side == 1 else b['away']
        lab = f"{team} {'+' if cen >= 0 else ''}{cen:g}" if pin else None
        q['gone_now'] = _now_tag(lab, price if pin else None, c['lines'][c['def']]['c'][0] if c else None, 0.10)
        out.append(q)
    return out


def euro_gone(active):
    now = dt.datetime.now(dt.timezone.utc)
    act = {(p['lg'], p['home'], p['away'], 0 if str(p.get('bet') or '').startswith(('Over', 'Under')) else p['side']) for p in active}
    odds = _load('euro_odds_latest.json', {}).get('odds', {})
    out = []
    for b in _jsonl('euro_picks_ledger.jsonl'):
        try: ko = _ko(b['ko'])
        except Exception: continue
        if ko <= now or b.get('no_play'):
            continue
        over = b.get('mkt') in ('OVER', 'UNDER')     # 10/10: + under UCL (συνολο)
        un = b.get('mkt') == 'UNDER'
        side = 0 if over else int(b['side'])
        if (b['comp'], b['home'], b['away'], side) in act:
            continue
        r = odds.get(str(b.get('mid'))) or {}
        if over:
            lab = f"{'Under' if un else 'Over'} {r['tl']:g}" if r.get('tl') is not None else None; od = r.get('tu' if un else 'to')
        else:
            L = r.get('line')
            lab = (f"{b['home'] if side == 1 else b['away']} {'+' if (L if side == 1 else -L) >= 0 else ''}{(L if side == 1 else -L):g}"
                   if L is not None else None)
            od = r.get('oh') if side == 1 else r.get('oa')
        q = dict(lg=b['comp'], home=b['home'], away=b['away'], home_id=b.get('hid'), away_id=b.get('aid'), side=side,
                 hcap=float(b['line']), odds=float(b['odds']), edge=float(b.get('edge') or 0), proj_odds=None,
                 when=str(b['ko'])[:16], eu=True, gone=True, gone_now=_now_tag(lab, od, None, 0.0))
        if over:
            q['bet'] = f"{'Under' if un else 'Over'} {float(b['line']):g}"
        out.append(q)
    return out


def intl_gone(active):
    import calc_data
    now = dt.datetime.now(dt.timezone.utc)
    act = {(p['lg'], p['home'], p['away'], p['side']) for p in active}
    d = _load('intl_projections_dashboard.json', {})
    M = {(c['comp'], m['home'], m['away'], m['utc']): m for c in d.get('comps', []) for m in c.get('matches', [])}
    first = {}
    for r in _jsonl('intl_picks_ledger.jsonl'):
        if r.get('stream') != 'ΣΥΝΑΙΝΕΣΗ' or r.get('removed'):
            continue
        try: ko = _ko(r['ko'])
        except Exception: continue
        if ko <= now or (ko - now).total_seconds() > 72 * 3600:
            continue
        side = 0 if r['mkt'] == 'OVER' else (1 if r['side'] == 1 else -1)
        k = (r['comp'], r['home'], r['away'], side)
        if k not in first or str(r.get('first_seen')) < str(first[k].get('first_seen')): first[k] = r
    out = []
    for k, r in first.items():
        if k in act:
            continue
        m = M.get((r['comp'], r['home'], r['away'], r['ko']))
        if not m:
            continue
        mk = (m.get('market') or {}); pm = mk.get(mk.get('source') or 'pinnacle') or mk.get('pinnacle') or {}
        side = k[3]; over = side == 0
        if over:
            cen = pm.get('ou_line'); od = pm.get('over')
        else:
            L = pm.get('ah_line'); cen = (L if side == 1 else -L) if L is not None else None
            od = pm.get('oh') if side == 1 else pm.get('oa')
        x = dict(mkt=r['mkt'], side=r['side'], line=cen if cen is not None else r['line'], odds=od or r['odds'])
        try:
            c = calc_data.intl_calc(m, x)
        except Exception:
            c = None
        q = dict(lg=r['comp'], home=r['home'], away=r['away'], home_id=r.get('hid'), away_id=r.get('aid'), side=side, hcap=float(r['line']),
                 odds=float(r['odds']), edge=float(r.get('edge') or 0), proj_odds=None, when=str(r['ko']).replace(' ', 'T'), intl=True,
                 models=r.get('models'), gone=True, calc=c)
        if over:
            q['bet'] = f"Over {float(r['line']):g}"
        if cen is not None and od:
            lab = f"Over {cen:g}" if over else f"{r['home'] if side == 1 else r['away']} {'+' if cen >= 0 else ''}{cen:g}"
            q['gone_now'] = dict(lab=lab, odds=od, edge=None, need=None)
        out.append(q)
    return out
