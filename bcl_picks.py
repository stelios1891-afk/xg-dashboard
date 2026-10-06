# -*- coding: utf-8 -*-
"""bcl_picks.py — VALUE PICKS Basketball Champions League + Telegram (6/10/2026, Στελιος «BCL σημερα»). Αντιγραφο του ec_picks.py
(ιδια λογικη/ημερολογιο/κατασταση/μηνυματα «δεν ισχυει πια») με αρχεια bcl_* — ΜΟΝΟ ΧΑΝΤΙΚΑΠ (τα συνολα BCL δεν εχουν τεσταριστει).
Κανονας και σ: απο bcl_engine_test (βλ. HC_MIN και sigma_margin στο bcl_projections.json)."""
import os, sys, json, datetime as dt
sys.stdout.reconfigure(encoding='utf-8')
from el_picks import cover
ROOT = os.path.dirname(os.path.abspath(__file__))
F = lambda n: os.path.join(ROOT, n)
HC_MIN, ODDS_DELTA = 0.08, 0.05
PAPER = True        # 6/10: ΜΟΝΟ ΚΑΤΑΓΡΑΦΗ (χωρις Telegram) μεχρι αποφαση Στελιου — bcl_engine_test: μοντελο 0.9 π. πισω απο την αγορα, Κ2 ≈ 0
TOT_MIN, TOT_W = 0.06, 0.5          # 5/10: συνολα αγων 1-6 — edge ≥6% με μιξη 50/50
TOT_MIN_LATE, TOT_W_LATE = 0.06, 1.0   # 5/10 (Στελιος «μιξη ως την 7η, μετα το μοντελο μονο του»): αγων 7+ μοντελο ΜΟΝΟ ΤΟΥ, edge ≥6%
TOT_EARLY_GNO = 5                    # gno = ματς που εχει ηδη παιξει (max των 2)· 0-5 = αγων 1-6
# ec_totals_bias_test / ec_totals_thr_test (Crown ανοιγμα U2020-25, αγων 7+): μιξη ≥6% −1.1% (125) · μοντελο μονο ≥6% +10.3% (339, 4/6)·
#   LOSO κατωφλιου ≤6% σε 6/6 · ζωνη 6-8% +27% (40), CLV +0.62, bootstrap P .96. ΠΡΟΣΟΧΗ: βαθμονομηση φτωχη (edge 15%+ → +2.2%).

def tot_rule(game):
    """(βαρος μοντελου, κατωφλι edge) για τα συνολα του ματς."""
    return (TOT_W, TOT_MIN) if int((game or {}).get('gno') or 0) <= TOT_EARLY_GNO else (TOT_W_LATE, TOT_MIN_LATE)

def tot_mix(game, pin, st):
    """Αναμενομενο συνολο για τα picks (αγων 1-6: μιξη 50/50 με την αγορα · 7+: μοντελο μονο του)· None αν λειπουν τιμες."""
    if not game or game.get('total') is None or pin.get('tl') is None or not pin.get('to') or not pin.get('tu'): return None
    from statistics import NormalDist
    T, ov, un = float(pin['tl']), float(pin['to']), float(pin['tu'])
    po = (1 / ov) / (1 / ov + 1 / un); mk = T + st * NormalDist().inv_cdf(min(max(po, 1e-4), 1 - 1e-4))
    return mk + tot_rule(game)[0] * (float(game['total']) - mk), mk

def _load(p, d):
    try: return json.load(open(p, encoding='utf-8'))
    except Exception: return d

def compute():
    proj = _load(F('bcl_projections.json'), {}); odds = _load(F('bcl_odds_latest.json'), {}).get('odds', {})
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
        L, oh, oa = float(pin['line']), float(pin['oh']), float(pin['oa']); m = float(g['margin'])
        pw, pp = cover(m, L, sm); pl = 1 - pw - pp
        for side, p_, od, hc in ((1, pw, oh, L), (-1, pl, oa, -L)):
            e = p_ * od + pp - 1
            if e >= HC_MIN:
                picks.append(dict(base, mkt='hcap', side=side, hcap=hc, odds=od, edge=round(e, 4),
                                  proj_odds=round((p_ + (1 - p_ - pp)) / p_, 2) if p_ > 0 else None, model_line=round(-m, 1), mkt_line=L))
    return picks

def key(p): return f"BCL|{p['code']}|{p['mkt']}|{p.get('bet') or p['side']}|{p['hcap']:g}"
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
    new, changed, cur = [], [], set()
    for p in picks:
        k = key(p); cur.add(k); prev = state.get(k)
        if prev is None:
            new.append(p); state[k] = dict(odds=p['odds'], edge=p['edge'], when=p['when'], first_seen=now)
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
                                         bet=p.get('bet'), paper=PAPER, model_line=p.get('model_line'), model_total=p.get('model_total'), mix_total=p.get('mix_total'),
                                         mkt_total=p.get('mkt_total'), mkt_line=p.get('mkt_line'), model=p.get('model')), ensure_ascii=False) + '\n')
    json.dump(state, open(F('bcl_value_state.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(dict(scanned_at=now, hc_min=HC_MIN, tot_min=TOT_MIN, tot_w=TOT_W, n_new=len(new), n_changed=len(changed), picks=picks),
              open(F('bcl_value_latest.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
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
