# -*- coding: utf-8 -*-
"""bcl_picks.py — VALUE PICKS Basketball Champions League + Telegram (6/10/2026, Στελιος «BCL σημερα»). Αντιγραφο του ec_picks.py
(ιδια λογικη/ημερολογιο/κατασταση/μηνυματα «δεν ισχυει πια») με αρχεια bcl_* — ΧΑΝΤΙΚΑΠ + ΣΥΝΟΛΑ (6/10 βραδυ: μοντελο μονο του ≥8%, bcl_totals_luck_test).
Κανονας και σ: απο bcl_engine_test (βλ. HC_MIN και sigma_margin στο bcl_projections.json)."""
import os, sys, json, datetime as dt
sys.stdout.reconfigure(encoding='utf-8')
from el_picks import cover
ROOT = os.path.dirname(os.path.abspath(__file__))
F = lambda n: os.path.join(ROOT, n)
HC_MIN, ODDS_DELTA = 0.08, 0.05
PAPER = False       # 6/10 Στελιος: «βαλτα στο dashboard οπως Euroleague/EuroCup, alerts, picks — το βλεπουμε στην πραξη» (backtest ≥8% Crown −0.4% / B365 +1.8%)
TOT_MIN, TOT_W = 0.08, 1.0          # 6/10 ΣΥΝΟΛΑ BCL: μοντελο ΜΟΝΟ ΤΟΥ, edge ≥8% (bcl_totals_luck_test LOSO: Crown ανοιγμα +7.1% 4/5, Bet365 +11.5% 4/5, Κ2 .41 t 2.8)
TOT_MIN_LATE, TOT_W_LATE = 0.08, 1.0   # (ιδιο ολη τη σεζον — η μιξη 50/50 δεν ηταν καλυτερη)
TOT_EARLY_GNO = 5
# ec_totals_bias_test / ec_totals_thr_test (Crown ανοιγμα U2020-25, αγων 7+): μιξη ≥6% −1.1% (125) · μοντελο μονο ≥6% +10.3% (339, 4/6)·
#   LOSO κατωφλιου ≤6% σε 6/6 · ζωνη 6-8% +27% (40), CLV +0.62, bootstrap P .96. ΠΡΟΣΟΧΗ: βαθμονομηση φτωχη (edge 15%+ → +2.2%).

def tot_rule(game):
    """(βαρος μοντελου, κατωφλι edge) για τα συνολα του ματς."""
    return (TOT_W, TOT_MIN) if int((game or {}).get('gno') or 0) <= TOT_EARLY_GNO else (TOT_W_LATE, TOT_MIN_LATE)

def tot_mix(game, pin, st):
    """Αναμενομενο συνολο για τα picks (αγων 1-6: μιξη 50/50 με την αγορα · 7+: μοντελο μονο του)· None αν λειπουν τιμες."""
    if not game or game.get('total') is None or game.get('total_src') != 'μοντελο' or pin.get('tl') is None or not pin.get('to') or not pin.get('tu'): return None
    from statistics import NormalDist
    T, ov, un = float(pin['tl']), float(pin['to']), float(pin['tu'])
    po = (1 / ov) / (1 / ov + 1 / un); mk = T + st * NormalDist().inv_cdf(min(max(po, 1e-4), 1 - 1e-4))
    return mk + tot_rule(game)[0] * (float(game['total']) - mk), mk

def _load(p, d):
    try: return json.load(open(p, encoding='utf-8'))
    except Exception: return d

LOWINFO_N = 4      # 7/10 Στελιος: ομαδα χωρις ιστορικο στη μηχανη → picks σε καταγραφη ως να παιξει 4 ματς BCL (bcl_state.json lowinfo)
# 27/10/2026 (Στελιος «οκ περνα και τα 2»· bcl_late_picks_test.py, Nowgoal Crown/Bet365 2021-26) — ΚΑΤΑΓΡΑΦΗ, ΟΧΙ ΠΑΙΧΝΙΔΙ (paper):
#  1 ΧΑΝΤΙΚΑΠ που ΔΕΝ ηταν pick στην ΠΡΩΤΗ γραμμη Pinnacle (bcl_pin_hist.jsonl· τωρινο μοντελο, πρωτη γραμμη/τιμες) → paper='late1st'
#    (αργα χαντικαπ Crown −3.7% 129 2/5 · Bet365 +0.6% 108 3/5, CLV −0.54 · ανοιγμα +3.4/+6.5% · ιδιο μοτιβο NBA & Euroleague).
#  2 ΣΥΝΟΛΑ που ΔΕΝ ηταν pick στην πρωτη γραμμη ΚΑΙ η αγορα (δικαιο συνολο) κινηθηκε ≥2π ΚΟΝΤΡΑ απο την πρωτη τιμη → paper='move2'
#    (κοντρα ≥2 Crown −23.3% 27 1/5 · Bet365 −5.8% 53· κοντρα 1-2π +19.2% / +40.5% → οριο 2, οχι 1.5 οπως EL). Τα υπολοιπα αργα συνολα μενουν picks (+5.0%, 4/5).
#  Η αποφαση παιρνεται ΜΙΑ φορα, στη γεννηση του pick (bcl_value_state paper/note) — δεν αλλαζει αν αλλαξει μετα το μοντελο.
LATE_KINDS, MOVE_TOT = ('late1st', 'move2'), 2.0
def _first_rows():
    """{(code, 'sp'|'tot'): πρωτη εγγραφη Pinnacle του ματς} απο το bcl_pin_hist.jsonl."""
    H = {}
    try:
        for ln in open(F('bcl_pin_hist.jsonl'), encoding='utf-8'):
            try: r = json.loads(ln)
            except Exception: continue
            for k_ in ('sp', 'tot'):
                v = r.get(k_) or {}
                if v.get('line') is None or not v.get('oh' if k_ == 'sp' else 'oo') or not v.get('oa' if k_ == 'sp' else 'ou'): continue
                kk = (f"pin{r.get('id')}", k_)
                if kk not in H or str(r.get('t', '')) < str(H[kk].get('_t', '')): H[kk] = dict(v, _t=r.get('t'))
    except Exception:
        pass
    return H
def compute():
    proj = _load(F('bcl_projections.json'), {}); odds = _load(F('bcl_odds_latest.json'), {}).get('odds', {})
    FR = _first_rows()
    low = _load(F('bcl_state.json'), {}).get('lowinfo', {})
    sm, st = float(proj.get('sigma_margin', 11.5)), float(proj.get('sigma_total', 16.7))
    games = {str(g['code']): g for g in proj.get('games', [])}
    now = dt.datetime.now(dt.timezone.utc); picks = []
    for code, o in odds.items():
        g = games.get(str(code)); pin = o.get('pin') or {}
        if not g or g.get('played'): continue
        ko = dt.datetime.fromisoformat(o['commence'].replace('Z', '+00:00'))
        if ko <= now: continue
        if pin.get('line') is None or not pin.get('oh') or not pin.get('oa'): continue
        base = dict(lg='BCL', paper=PAPER, home=g['home'], away=g['away'], hcode=g['hcode'], acode=g['acode'], code=g['code'], round=g['round'], group=g.get('group'),
                    when=ko.strftime('%Y-%m-%dT%H:%M'), bcl=True, model=proj.get('model', '')[:60])
        lw = [(nm_, low[c_]) for c_, nm_ in ((g['hcode'], g['home']), (g['acode'], g['away'])) if c_ in low and low[c_] < LOWINFO_N]
        if lw:
            base.update(paper='lowinfo', late_kind='λιγα δεδομενα', mkt_note='⚠ λίγα δεδομένα: ' + ' · '.join(f'{n_} χωρίς ιστορικό στη μηχανή, {k_} ματς BCL φέτος' for n_, k_ in lw)
                        + f' — καταγραφή ως το {LOWINFO_N}ο ματς')
        L, oh, oa = float(pin['line']), float(pin['oh']), float(pin['oa']); m = float(g['margin'])
        pw, pp = cover(m, L, sm); pl = 1 - pw - pp
        f_sp = FR.get((str(code), 'sp'))
        for side, p_, od, hc in ((1, pw, oh, L), (-1, pl, oa, -L)):
            e = p_ * od + pp - 1
            if e >= HC_MIN:
                late = {}
                if f_sp and base.get('paper') != 'lowinfo':               # 27/10 κανονας 1: πρωτη γραμμη
                    L0 = float(f_sp['line']); pw0, pp0 = cover(m, L0, sm); pl0 = 1 - pw0 - pp0
                    od0 = float(f_sp['oh'] if side == 1 else f_sp['oa']); e0 = (pw0 if side == 1 else pl0) * od0 + pp0 - 1
                    if e0 < HC_MIN:
                        late = dict(paper='late1st', late_kind='αργο χαντικαπ',
                                    mkt_note=f"⚠ αργό χάντικαπ: στην πρώτη γραμμή ({(L0 if side == 1 else -L0):+g} @{od0:.2f}) edge {e0 * 100:.0f}% — καταγραφή (ιστορικά αργά χάντικαπ BCL ≈0%)")
                picks.append(dict(base, mkt='hcap', side=side, hcap=hc, odds=od, edge=round(e, 4),
                                  proj_odds=round((p_ + (1 - p_ - pp)) / p_, 2) if p_ > 0 else None, model_line=round(-m, 1), mkt_line=L, **late))
        # ---- συνολο (6/10): μοντελο μονο του ≥8% ----
        tm = tot_mix(g, pin, st)
        if tm:
            mu, mk = tm; T = float(pin['tl'])
            po, pq = cover(mu, -T, st); pu = 1 - po - pq
            f_t = FR.get((str(code), 'tot'))
            for nm, p_, od in (('Over', po, float(pin['to'])), ('Under', pu, float(pin['tu']))):
                e = p_ * od + pq - 1
                if e >= tot_rule(g)[1]:
                    late = {}
                    if f_t and base.get('paper') != 'lowinfo':             # 27/10 κανονας 2: αργο ΚΑΙ κινηση ≥2π κοντρα
                        from statistics import NormalDist
                        T0, oo0, ou0 = float(f_t['line']), float(f_t['oo']), float(f_t['ou'])
                        po0, pq0 = cover(mu, -T0, st); e0 = (po0 * oo0 if nm == 'Over' else (1 - po0 - pq0) * ou0) + pq0 - 1
                        q0 = (1 / oo0) / (1 / oo0 + 1 / ou0); mk0 = T0 + st * NormalDist().inv_cdf(min(max(q0, 1e-4), 1 - 1e-4))
                        mv = (mk0 - mk) if nm == 'Over' else (mk - mk0)      # + = η αγορα πηγε ΚΟΝΤΡΑ μας
                        if e0 < tot_rule(g)[1] and mv >= MOVE_TOT:
                            late = dict(paper='move2', late_kind='κοντρα κινηση', move_open=round(-mv, 2),
                                        mkt_note=f"⚠ σύνολο μετά από κίνηση {mv:.1f} π. κόντρα (αγορά {mk0:.1f} → {mk:.1f}) — καταγραφή (ιστορικά −23%/−6%)")
                    picks.append(dict(base, mkt='total', side=0, hcap=T, bet=f'{nm} {T:g}', odds=od, edge=round(e, 4),
                                      proj_odds=round((p_ + (1 - p_ - pq)) / p_, 2) if p_ > 0 else None, model_total=round(float(g['total']), 1),
                                      mix_total=round(mu, 1), mkt_total=round(mk, 1), mkt_line=T, gno=g.get('gno'), **late))
    return picks

def key(p):                                   # 7/10: ΕΝΑ pick ανα ματς & πλευρα (η γραμμη εκτος κλειδιου)
    import bk_pick_status as _b; return _b.side_key('BCL', p)
def line(p, prev=None):
    t = dt.datetime.fromisoformat(p['when']).replace(tzinfo=dt.timezone.utc)
    try:
        from zoneinfo import ZoneInfo; t = t.astimezone(ZoneInfo('Europe/Athens'))
    except Exception:
        t = t + dt.timedelta(hours=3)
    tm = f"{['Δευ', 'Τρι', 'Τετ', 'Πεμ', 'Παρ', 'Σαβ', 'Κυρ'][t.weekday()]} {t:%d/%m %H:%M}"
    if p['mkt'] == 'total':
        bet = p['bet']; why = f"μοντελο {p['model_total']:.1f} · αγορα {p['mkt_total']:.1f}" + (f" · μιξη {p['mix_total']:.1f}" if abs(p['mix_total'] - p['model_total']) > .05 else '')
    else:
        team = p['home'] if p['side'] == 1 else p['away']
        bet = f"{team} {'+' if p['hcap'] >= 0 else ''}{p['hcap']:g}"; why = f"μοντελο {p['model_line']:+.1f} · αγορα {p['mkt_line']:+.1f}"
    ch = f" (ηταν {prev:.2f})" if prev else ''
    return (f"🏀 Champions League (FIBA) · {tm}\n{p['home']} - {p['away']}\n"
            f"{bet} @{p['odds']:.2f}{ch} · edge {p['edge']*100:.0f}% · fair {p['proj_odds']:.2f}\n({why})")

def main(notify_tg=True):
    picks = compute()
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec='minutes')
    state = _load(F('bcl_value_state.json'), {})
    import bk_pick_status as _b; _b.migrate_keys(state, 'BCL')
    new, changed, cur = [], [], set()
    for p in picks:
        k = key(p); cur.add(k); prev = state.get(k)
        if prev is not None:                                   # 27/10: καταγραφη αργων = αποφαση της γεννησης (σταθερη)
            if prev.get('paper') in LATE_KINDS: p.update(paper=prev['paper'], late_kind=prev.get('late_kind'), mkt_note=prev.get('note'))
            elif p.get('paper') in LATE_KINDS:
                p['paper'] = False; p.pop('late_kind', None); p.pop('mkt_note', None); p.pop('move_open', None)
        if prev is None:
            new.append(p); state[k] = dict(odds=p['odds'], edge=p['edge'], when=p['when'], first_seen=now, hcap=p['hcap'])
            if p.get('paper') in LATE_KINDS: state[k].update(paper=p['paper'], late_kind=p.get('late_kind'), note=p.get('mkt_note'))
        elif not _b.same_line(prev, p):                 # 7/10: ιδια πλευρα, αλλη γραμμη → ΙΔΙΟ pick, σιωπηλα (οχι νεο/ημερολογιο/Telegram)
            state[k].update(hcap=p['hcap'], odds=p['odds'], edge=p['edge'])
        elif abs(p['odds'] - prev.get('odds', p['odds'])) >= ODDS_DELTA:
            changed.append((p, prev.get('odds'))); state[k].update(odds=p['odds'], edge=p['edge'])
    for p in picks:
        st0 = state.get(key(p), {})
        try:
            p['hrs_birth'] = round((dt.datetime.fromisoformat(p['when']).replace(tzinfo=dt.timezone.utc)
                                    - dt.datetime.fromisoformat(st0.get('first_seen', now))).total_seconds() / 3600, 1)
        except Exception:
            p['hrs_birth'] = None
    today = now[:10]
    # 1/10/2026: pick που ΔΕΝ ισχυει πια → μηνυμα· ξαναγινεται → «ΞΑΝΑ PICK» (bk_pick_status, ιδιο με Ευρωλιγκα/εθνικες)
    import bk_pick_status as bps
    proj_ = _load(F('bcl_projections.json'), {}); sm_, st_ = float(proj_.get('sigma_margin', 11.5)), float(proj_.get('sigma_total', 16.7))
    odds_ = _load(F('bcl_odds_latest.json'), {}).get('odds', {})
    games_ = {str(g['code']): g for g in proj_.get('games', [])}
    for c_, g_ in list(games_.items()):                  # συνολα: ο ελεγχος «ισχυει ακομα;» με την ιδια μιξη 50/50
        tm_ = tot_mix(g_, (odds_.get(c_) or {}).get('pin') or {}, st_)
        if tm_: games_[c_] = dict(g_, total=tm_[0])
    drops, backs = bps.track(state, picks, F('bcl_clv_bets.jsonl'), games_, odds_,
                             lambda m: sm_ if m == 'hcap' else st_, lambda m, g=None: HC_MIN if m == 'hcap' else tot_rule(g)[1], cover, 'BCL', now)
    state = {k: v for k, v in state.items() if k in cur or (v.get('when') or '9999')[:10] >= today}
    if new:
        with open(F('bcl_clv_bets.jsonl'), 'a', encoding='utf-8') as fh:
            for p in new:
                fh.write(json.dumps(dict(seen=now, **{k: p[k] for k in ('lg', 'code', 'round', 'home', 'away', 'mkt', 'side', 'hcap', 'odds', 'edge', 'when')},
                                         bet=p.get('bet'), paper=p.get('paper') or PAPER, model_line=p.get('model_line'), model_total=p.get('model_total'), mix_total=p.get('mix_total'),
                                         mkt_total=p.get('mkt_total'), mkt_line=p.get('mkt_line'), model=p.get('model'),
                                         **({'late_kind': p.get('late_kind'), 'move_open': p.get('move_open'), 'paper_note': p.get('mkt_note')} if p.get('paper') in LATE_KINDS else {})), ensure_ascii=False) + '\n')
    json.dump(state, open(F('bcl_value_state.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(dict(scanned_at=now, hc_min=HC_MIN, tot_min=TOT_MIN, tot_w=TOT_W, n_new=len(new), n_changed=len(changed), picks=picks),
              open(F('bcl_value_latest.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    new = [p for p in new if not p.get('paper')]; changed = [(p, pr) for p, pr in changed if not p.get('paper')]     # 7/10: καταγραφη («λιγα δεδομενα») οχι Telegram
    if notify_tg and not PAPER and (new or changed):
        msg = []
        if new: msg += [f'🏀 {len(new)} ΝΕΑ value picks BCL', ''] + [line(p) + '\n' for p in sorted(new, key=lambda x: x['when'])]
        if changed: msg += [f'🔄 {len(changed)} ΑΛΛΑΞΑΝ odds (BCL)'] + [line(p, pr) for p, pr in changed]
        try:
            import notify; notify.send('\n'.join(msg))
        except Exception as e:
            print('Telegram σφαλμα:', e)
    for t in backs + drops: print(t.replace(chr(10), ' | '))
    if notify_tg and not PAPER and (backs or drops):
        try:
            import notify
            if backs: notify.send((chr(10) * 2).join(backs))
            if drops: notify.send('🏀 BCL · pick που ΔΕΝ ισχυει πια (αλλαξε γραμμη/τιμη)' + chr(10) * 2 + (chr(10) * 2).join(drops), silent=True)
        except Exception as e:
            print('Telegram σφαλμα (κατασταση):', e)
    print(f'[BCL picks] {len(picks)} picks · {len(new)} νεα · {len(changed)} αλλαγες')
    for p in picks: print('  ' + line(p).replace('\n', ' | '))
    return picks

if __name__ == '__main__':
    main(notify_tg='--no-tg' not in sys.argv)
