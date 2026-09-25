# -*- coding: utf-8 -*-
"""el_picks.py — VALUE PICKS Ευρωλιγκας + Telegram (25/9/2026, αποφαση Στελιου).
Διαβαζει: el_projections.json (μοντελο v3: χαντικαπ v1+ειδικοι · συνολο v2+παρατασεις) + el_odds_latest.json (Pinnacle, scanner).
Κανονες (ιστορικο ROI 6 σεζον, Pinnacle closing): edge ≥ 8% σε χαντικαπ ΚΑΙ σε συνολο (over/under), μονο ματς που δεν αρχισαν.
  edge = P(μοντελο)·αποδοση + P(push) − 1 · διαφορα ~ N(margin, 11.5) · συνολο ~ N(total, 16.7) · ακεραιες γραμμες: διορθωση ±0.5.
Γραφει: el_value_latest.json (dashboard, tab Value Picks) · el_clv_bets.jsonl (ημερολογιο: καθε ΝΕΟ pick με την τιμη εισοδου)
Telegram: ΜΟΝΟ νεα picks ή αλλαγη αποδοσης ≥ 0.05 (state: el_value_state.json) — οπως το ποδοσφαιρο (notify.py).
Χρηση: python el_picks.py [--no-tg]"""
import os, sys, json, math, datetime as dt
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.abspath(__file__))
F = lambda n: os.path.join(ROOT, n)
HC_MIN, TOT_MIN = 0.08, 0.08
ODDS_DELTA = 0.05
Phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))

def _load(p, d):
    try: return json.load(open(p, encoding='utf-8'))
    except Exception: return d
def _is_int(x): return abs(x - round(x)) < 1e-9
def cover(mu, L, sig):
    """P(νικη), P(push) για «mu + L > 0»."""
    if _is_int(L):
        pw = Phi((mu + L - 0.5) / sig); pl = Phi((-mu - L - 0.5) / sig); return pw, 1 - pw - pl
    return Phi((mu + L) / sig), 0.0

def compute():
    proj = _load(F('el_projections.json'), {}); odds = _load(F('el_odds_latest.json'), {}).get('odds', {})
    sm, st = float(proj.get('sigma_margin', 11.5)), float(proj.get('sigma_total', 16.7))
    games = {str(g['code']): g for g in proj.get('games', [])}
    now = dt.datetime.now(dt.timezone.utc)
    picks = []
    for code, o in odds.items():
        g = games.get(str(code)); pin = o.get('pin') or {}
        if not g or g.get('played'): continue
        ko = dt.datetime.fromisoformat(o['commence'].replace('Z', '+00:00'))
        if ko <= now: continue
        when = ko.strftime('%Y-%m-%dT%H:%M')
        base = dict(lg='Euroleague', home=g['home'], away=g['away'], hcode=g['hcode'], acode=g['acode'], code=g['code'], round=g['round'],
                    when=when, el=True, model=proj.get('model', '')[:60])
        # ---- χαντικαπ ----
        if pin.get('line') is not None and pin.get('oh') and pin.get('oa'):
            L, oh, oa = float(pin['line']), float(pin['oh']), float(pin['oa'])
            m = float(g['margin'])
            pw, pp = cover(m, L, sm); pl = 1 - pw - pp
            for side, p_, pu, od, hc in ((1, pw, pp, oh, L), (-1, pl, pp, oa, -L)):
                e = p_ * od + pu - 1
                if e >= HC_MIN:
                    picks.append(dict(base, mkt='hcap', side=side, hcap=hc, odds=od, edge=round(e, 4),
                                      proj_odds=round((p_ + (1 - p_ - pu)) / p_, 2) if p_ > 0 else None, model_line=round(-m, 1), mkt_line=L))
        # ---- συνολο ----
        if pin.get('tl') is not None and pin.get('to') and pin.get('tu'):
            T, ov, un = float(pin['tl']), float(pin['to']), float(pin['tu'])
            t = float(g['total'])
            po, pq = cover(t, -T, st); pu_ = 1 - po - pq
            for nm, p_, od in (('Over', po, ov), ('Under', pu_, un)):
                e = p_ * od + pq - 1
                if e >= TOT_MIN:
                    picks.append(dict(base, mkt='total', side=0, hcap=T, bet=f'{nm} {T:g}', odds=od, edge=round(e, 4),
                                      proj_odds=round((p_ + (1 - p_ - pq)) / p_, 2) if p_ > 0 else None, model_total=round(t, 1), mkt_line=T))
    return picks

def key(p): return f"EL|{p['code']}|{p['mkt']}|{p.get('bet') or p['side']}|{p['hcap']:g}"
def line(p, prev=None):
    t = dt.datetime.fromisoformat(p['when']).replace(tzinfo=dt.timezone.utc)
    try:
        from zoneinfo import ZoneInfo; t = t.astimezone(ZoneInfo('Europe/Athens'))
    except Exception:
        t = t + dt.timedelta(hours=3)
    tm = f"{['Δευ', 'Τρι', 'Τετ', 'Πεμ', 'Παρ', 'Σαβ', 'Κυρ'][t.weekday()]} {t:%d/%m %H:%M}"
    if p['mkt'] == 'hcap':
        team = p['home'] if p['side'] == 1 else p['away']
        bet = f"{team} {'+' if p['hcap'] >= 0 else ''}{p['hcap']:g}"
        why = f"μοντελο {p['model_line']:+.1f} · αγορα {p['mkt_line']:+.1f}"
    else:
        bet = p['bet']; why = f"μοντελο {p['model_total']:.1f} · αγορα {p['mkt_line']:g}"
    ch = f" (ηταν {prev:.2f})" if prev else ''
    return f"🏀 Euroleague · αγων {p['round']} · {tm}\n{p['home']} - {p['away']}\n{bet} @{p['odds']:.2f}{ch} · edge {p['edge']*100:.0f}% · fair {p['proj_odds']:.2f}\n({why})"

def main(notify_tg=True):
    picks = compute()
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec='minutes')
    state = _load(F('el_value_state.json'), {})
    new, changed, cur = [], [], set()
    for p in picks:
        k = key(p); cur.add(k); prev = state.get(k)
        if prev is None:
            new.append(p); state[k] = dict(odds=p['odds'], edge=p['edge'], when=p['when'], first_seen=now)
        elif abs(p['odds'] - prev.get('odds', p['odds'])) >= ODDS_DELTA:
            changed.append((p, prev.get('odds'))); state[k].update(odds=p['odds'], edge=p['edge'])
    today = now[:10]
    state = {k: v for k, v in state.items() if k in cur or (v.get('when') or '9999')[:10] >= today}
    if new:
        with open(F('el_clv_bets.jsonl'), 'a', encoding='utf-8') as fh:
            for p in new:
                fh.write(json.dumps(dict(seen=now, **{k: p[k] for k in ('lg', 'code', 'round', 'home', 'away', 'mkt', 'side', 'hcap', 'odds', 'edge', 'when')},
                                         bet=p.get('bet'), model_line=p.get('model_line'), model_total=p.get('model_total'), mkt_line=p.get('mkt_line'),
                                         model=p.get('model')), ensure_ascii=False) + '\n')
    json.dump(state, open(F('el_value_state.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(dict(scanned_at=now, hc_min=HC_MIN, tot_min=TOT_MIN, n_new=len(new), n_changed=len(changed), picks=picks),
              open(F('el_value_latest.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if notify_tg and (new or changed):
        msg = []
        if new: msg += [f'🏀 {len(new)} ΝΕΑ value picks Ευρωλιγκας', ''] + [line(p) + '\n' for p in sorted(new, key=lambda x: x['when'])]
        if changed: msg += [f'🔄 {len(changed)} ΑΛΛΑΞΑΝ odds'] + [line(p, pr) for p, pr in changed]
        try:
            import notify; notify.send('\n'.join(msg))
        except Exception as e:
            print('Telegram σφαλμα:', e)
    print(f'[EL picks] {len(picks)} picks · {len(new)} νεα · {len(changed)} αλλαγες')
    for p in picks: print('  ' + line(p).replace('\n', ' | '))
    return picks

if __name__ == '__main__':
    main(notify_tg='--no-tg' not in sys.argv)
