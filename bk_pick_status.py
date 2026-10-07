"""
bk_pick_status.py — ΠΑΡΑΚΟΛΟΥΘΗΣΗ ΚΑΤΑΣΤΑΣΗΣ PICKS ΜΠΑΣΚΕΤ (Ευρωλιγκα & EuroCup) — 1/10/2026 (Στελιος: «το Virtus–Olympiakos ηρθε
στις 5 για over 171, τωρα δεν υπαρχει αυτη η γραμμη — γιατι δεν ηρθε μηνυμα;»). Ιδια λογικη με τις εθνικες (intl_picks_ledger.track_status):
για καθε pick που ΒΓΗΚΕ (ημερολογιο *_clv_bets.jsonl, οχι paper) και δεν αρχισε το ματς:
  · ειναι ακομα pick η ΙΔΙΑ αγορα & κατευθυνση (χαντικαπ πλευρα / Over-Under) σε ΟΠΟΙΑΔΗΠΟΤΕ γραμμη;
  · ΝΑΙ → τιποτα (7/10: αλλη γραμμη στην ιδια πλευρα = ΙΔΙΟ pick, σιωπηλα — βλ. side_key/migrate_keys).
  · ΟΧΙ → «⚠ δεν ισχυει πια» (σιωπηλο, picks bot): γραμμη/αποδοση τωρα, edge τωρα, ποια αποδοση χρειαζεται για pick.
  · ξαναγινεται pick → «🔁 ΞΑΝΑ PICK».
Οχι «πινγκ-πονγκ»: νεο μηνυμα για το ιδιο pick μονο αν περασαν ≥30′ απο το προηγουμενο. Κατασταση στο *_value_state.json (κλειδι STATUS|...).
"""
import json, datetime as dt

QUIET_MIN = 30


def _dir(mkt, side, bet):
    return str(side) if mkt == 'hcap' else str(bet or '').split(' ')[0]          # 1/-1 ή Over/Under


def side_key(lg, p):
    """7/10/2026 (Στελιος: «επαιξα Βοννη −9.5 και εμφανιζεται σαν νεο στο −8.5»): ΕΝΑ pick ανα ματς & πλευρα — η γραμμη ΔΕΝ ειναι μερος του κλειδιου."""
    return f"{lg}|{p['code']}|{p['mkt']}|{_dir(p['mkt'], p.get('side'), p.get('bet'))}"


def migrate_keys(state, lg):
    """Παλια κλειδια state «LG|code|mkt|bet-ή-πλευρα|γραμμη» → «LG|code|mkt|κατευθυνση» (πρωτη εμφανιση κρατα first_seen/paper, τελευταια τιμη/γραμμη)."""
    for k in [k for k in state if k.startswith(lg + '|') and k.count('|') == 4]:
        a = k.split('|'); v = state.pop(k)
        try: v.setdefault('hcap', float(a[4]))
        except ValueError: pass
        nk = '|'.join([a[0], a[1], a[2], a[3].split(' ')[0]])
        o = state.get(nk)
        if o is None: state[nk] = v; continue
        first, last = (v, o) if v.get('first_seen', '') <= o.get('first_seen', '') else (o, v)
        state[nk] = dict(first, odds=last.get('odds'), edge=last.get('edge'), hcap=last.get('hcap'))
    return state


def same_line(prev, p):
    """Ιδια γραμμη με την τελευταια που ειδαμε; (χωρις αποθηκευμενη γραμμη → ναι)"""
    return prev.get('hcap') is None or abs(float(prev['hcap']) - float(p['hcap'])) < 1e-9


def open_bets(bets_path, now):
    """{(code, mkt, dir): πρωτη (μη paper) εγγραφη} για ματς που δεν αρχισαν."""
    out = {}
    try:
        for ln in open(bets_path, encoding='utf-8'):
            try: b = json.loads(ln)
            except Exception: continue
            if b.get('paper'): continue
            try:
                ko = dt.datetime.fromisoformat(b['when']).replace(tzinfo=dt.timezone.utc)
            except Exception:
                continue
            if ko <= now: continue
            k = (str(b['code']), b['mkt'], _dir(b['mkt'], b.get('side'), b.get('bet')))
            if k not in out or b['seen'] < out[k]['seen']: out[k] = b
    except FileNotFoundError:
        pass
    return out


def current_view(b, game, pin, sig, min_edge, cover):
    """Τι λεει τωρα το μοντελο για την ιδια αγορα/κατευθυνση στη ΓΡΑΜΜΗ ΤΗΣ ΑΓΟΡΑΣ: (περιγραφη γραμμης, αποδοση, edge, απαιτουμενη αποδοση)."""
    if b['mkt'] == 'hcap':
        if pin.get('line') is None or not pin.get('oh') or not pin.get('oa'): return None
        L = float(pin['line']); m = float(game['margin'])
        pw, pp = cover(m, L, sig)
        if int(b['side']) == 1: p_, od, hc = pw, float(pin['oh']), L
        else: p_, od, hc = 1 - pw - pp, float(pin['oa']), -L
        team = b['home'] if int(b['side']) == 1 else b['away']
        lab = f"{team} {'+' if hc >= 0 else ''}{hc:g}"
    else:
        if pin.get('tl') is None or not pin.get('to') or not pin.get('tu'): return None
        T = float(pin['tl']); t = float(game['total'])
        po, pp = cover(t, -T, sig); over = str(b.get('bet', '')).startswith('Over')
        p_, od = (po, float(pin['to'])) if over else (1 - po - pp, float(pin['tu']))
        lab = f"{'Over' if over else 'Under'} {T:g}"
    e = p_ * od + pp - 1
    need = (1 + min_edge - pp) / p_ if p_ > 0 else None
    return lab, od, e, need


def track(state, picks, bets_path, games, odds, sig_of, min_edge_of, cover, lg_label, now_iso):
    """Ενημερωνει το state· επιστρεφει (drops, backs) κειμενα Telegram."""
    now = dt.datetime.fromisoformat(now_iso)
    active_now = {(str(p['code']), p['mkt'], _dir(p['mkt'], p.get('side'), p.get('bet'))) for p in picks}
    drops, backs = [], []
    for k, b in open_bets(bets_path, now).items():
        sk = 'STATUS|' + '|'.join(k)
        st = state.get(sk) or dict(active=True, when=b['when'])
        is_active = k in active_now
        last = st.get('at')
        quiet = bool(last) and (now - dt.datetime.fromisoformat(last)).total_seconds() < QUIET_MIN * 60
        if st.get('active', True) and not is_active:
            st.update(active=False, at=now_iso, when=b['when'])
            game = games.get(str(b['code'])); pin = (odds.get(str(b['code'])) or {}).get('pin') or {}
            try: me_ = min_edge_of(b['mkt'], game)          # 5/10: EuroCup συνολα — κατωφλι ανα ματς (αγων 1-6 / 7+)
            except TypeError: me_ = min_edge_of(b['mkt'])
            cv = current_view(b, game, pin, sig_of(b['mkt']), me_, cover) if game else None
            ent = f"{b.get('bet') or ((b['home'] if int(b['side']) == 1 else b['away']) + (' +' if float(b['hcap']) >= 0 else ' ') + format(float(b['hcap']), 'g'))} @{float(b['odds']):.2f}"
            txt = (f"⚠ {lg_label} · {b['home']} – {b['away']}\nμπηκε: {ent} ({_gr(b['seen'])})\n"
                   + (f"τωρα: {cv[0]} @{cv[1]:.2f} · edge {cv[2]*100:+.0f}% · για pick χρειαζεται @{cv[3]:.2f}" if cv and cv[3] else 'τωρα: χωρις τιμη στην αγορα'))
            if not quiet: drops.append(txt)
        elif not st.get('active', True) and is_active:
            st.update(active=True, at=now_iso, when=b['when'])
            p = next(p for p in picks if (str(p['code']), p['mkt'], _dir(p['mkt'], p.get('side'), p.get('bet'))) == k)
            lab = p.get('bet') or f"{(p['home'] if p['side'] == 1 else p['away'])} {'+' if p['hcap'] >= 0 else ''}{p['hcap']:g}"
            if not quiet: backs.append(f"🔁 ΞΑΝΑ PICK · {lg_label} · {b['home']} – {b['away']}\n{lab} @{p['odds']:.2f} · edge {p['edge']*100:.0f}%")
        state[sk] = st
    return drops, backs


def _gr(iso):
    t = dt.datetime.fromisoformat(iso)
    if t.tzinfo is None: t = t.replace(tzinfo=dt.timezone.utc)
    try:
        from zoneinfo import ZoneInfo; t = t.astimezone(ZoneInfo('Europe/Athens'))
    except Exception:
        t = t + dt.timedelta(hours=3)
    return f'{t:%d/%m %H:%M}'
