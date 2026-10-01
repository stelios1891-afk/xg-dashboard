# -*- coding: utf-8 -*-
"""ec_picks.py — VALUE PICKS EuroCup + Telegram (1/10/2026, αποφαση Στελιου «περνα τη ρυθμιση live»).
Διαβαζει: ec_projections.json (ec_refresh.py) + ec_odds_latest.json (Pinnacle, ec_odds_scan.py).
Κανονας: ΜΟΝΟ ΧΑΝΤΙΚΑΠ, edge ≥ 8% (ιστορικα U2020-25 vs Crown: ανοιγμα +5.1% ολη η σεζον, πρωτα 6 ματς +13.3% — ec_carry_test).
  edge = P(μοντελο)·αποδοση + P(push) − 1 · διαφορα ~ N(margin, 11.5) · ακεραιες γραμμες: διορθωση ±0.5 (ιδιο με Ευρωλιγκα).
  Συνολα: ΟΧΙ (δεν εχουν τεσταριστει στο EuroCup). Οι κανονες alert της Ευρωλιγκας (2ωρο/κινηση) δεν εφαρμοζονται — δεν τεσταριστηκαν εδω.
Γραφει: ec_value_latest.json (dashboard) · ec_clv_bets.jsonl (ημερολογιο: καθε ΝΕΟ pick με την τιμη εισοδου) · ec_value_state.json.
Telegram (picks bot): ΜΟΝΟ νεα picks ή αλλαγη αποδοσης ≥ 0.05. Χρηση: python ec_picks.py [--no-tg]"""
import os, sys, json, datetime as dt
sys.stdout.reconfigure(encoding='utf-8')
from el_picks import cover
ROOT = os.path.dirname(os.path.abspath(__file__))
F = lambda n: os.path.join(ROOT, n)
HC_MIN, ODDS_DELTA = 0.08, 0.05

def _load(p, d):
    try: return json.load(open(p, encoding='utf-8'))
    except Exception: return d

def compute():
    proj = _load(F('ec_projections.json'), {}); odds = _load(F('ec_odds_latest.json'), {}).get('odds', {})
    sm = float(proj.get('sigma_margin', 11.5))
    games = {str(g['code']): g for g in proj.get('games', [])}
    now = dt.datetime.now(dt.timezone.utc); picks = []
    for code, o in odds.items():
        g = games.get(str(code)); pin = o.get('pin') or {}
        if not g or g.get('played'): continue
        ko = dt.datetime.fromisoformat(o['commence'].replace('Z', '+00:00'))
        if ko <= now: continue
        if pin.get('line') is None or not pin.get('oh') or not pin.get('oa'): continue
        base = dict(lg='EuroCup', home=g['home'], away=g['away'], hcode=g['hcode'], acode=g['acode'], code=g['code'], round=g['round'], group=g.get('group'),
                    when=ko.strftime('%Y-%m-%dT%H:%M'), ec=True, model=proj.get('model', '')[:60])
        L, oh, oa = float(pin['line']), float(pin['oh']), float(pin['oa']); m = float(g['margin'])
        pw, pp = cover(m, L, sm); pl = 1 - pw - pp
        for side, p_, od, hc in ((1, pw, oh, L), (-1, pl, oa, -L)):
            e = p_ * od + pp - 1
            if e >= HC_MIN:
                picks.append(dict(base, mkt='hcap', side=side, hcap=hc, odds=od, edge=round(e, 4),
                                  proj_odds=round((p_ + (1 - p_ - pp)) / p_, 2) if p_ > 0 else None, model_line=round(-m, 1), mkt_line=L))
    return picks

def key(p): return f"EC|{p['code']}|hcap|{p['side']}|{p['hcap']:g}"
def line(p, prev=None):
    t = dt.datetime.fromisoformat(p['when']).replace(tzinfo=dt.timezone.utc)
    try:
        from zoneinfo import ZoneInfo; t = t.astimezone(ZoneInfo('Europe/Athens'))
    except Exception:
        t = t + dt.timedelta(hours=3)
    tm = f"{['Δευ', 'Τρι', 'Τετ', 'Πεμ', 'Παρ', 'Σαβ', 'Κυρ'][t.weekday()]} {t:%d/%m %H:%M}"
    team = p['home'] if p['side'] == 1 else p['away']
    bet = f"{team} {'+' if p['hcap'] >= 0 else ''}{p['hcap']:g}"
    ch = f" (ηταν {prev:.2f})" if prev else ''
    return (f"🏀 EuroCup · αγων {p['round']}{' · ομιλος ' + p['group'] if p.get('group') else ''} · {tm}\n{p['home']} - {p['away']}\n"
            f"{bet} @{p['odds']:.2f}{ch} · edge {p['edge']*100:.0f}% · fair {p['proj_odds']:.2f}\n(μοντελο {p['model_line']:+.1f} · αγορα {p['mkt_line']:+.1f})")

def main(notify_tg=True):
    picks = compute()
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec='minutes')
    state = _load(F('ec_value_state.json'), {})
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
    proj_ = _load(F('ec_projections.json'), {}); sm_ = float(proj_.get('sigma_margin', 11.5))
    drops, backs = bps.track(state, picks, F('ec_clv_bets.jsonl'), {str(g['code']): g for g in proj_.get('games', [])},
                             _load(F('ec_odds_latest.json'), {}).get('odds', {}), lambda m: sm_, lambda m: HC_MIN, cover, 'EuroCup', now)
    state = {k: v for k, v in state.items() if k in cur or (v.get('when') or '9999')[:10] >= today}
    if new:
        with open(F('ec_clv_bets.jsonl'), 'a', encoding='utf-8') as fh:
            for p in new:
                fh.write(json.dumps(dict(seen=now, **{k: p[k] for k in ('lg', 'code', 'round', 'home', 'away', 'mkt', 'side', 'hcap', 'odds', 'edge', 'when')},
                                         model_line=p.get('model_line'), mkt_line=p.get('mkt_line'), model=p.get('model')), ensure_ascii=False) + '\n')
    json.dump(state, open(F('ec_value_state.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(dict(scanned_at=now, hc_min=HC_MIN, n_new=len(new), n_changed=len(changed), picks=picks),
              open(F('ec_value_latest.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if notify_tg and (new or changed):
        msg = []
        if new: msg += [f'🏀 {len(new)} ΝΕΑ value picks EuroCup', ''] + [line(p) + '\n' for p in sorted(new, key=lambda x: x['when'])]
        if changed: msg += [f'🔄 {len(changed)} ΑΛΛΑΞΑΝ odds (EuroCup)'] + [line(p, pr) for p, pr in changed]
        try:
            import notify; notify.send('\n'.join(msg))
        except Exception as e:
            print('Telegram σφαλμα:', e)
    for t in backs + drops: print(t.replace(chr(10), ' | '))
    if notify_tg and (backs or drops):
        try:
            import notify
            if backs: notify.send((chr(10) * 2).join(backs))
            if drops: notify.send('🏀 EuroCup · pick που ΔΕΝ ισχυει πια (αλλαξε γραμμη/τιμη)' + chr(10) * 2 + (chr(10) * 2).join(drops), silent=True)
        except Exception as e:
            print('Telegram σφαλμα (κατασταση):', e)
    print(f'[EC picks] {len(picks)} picks · {len(new)} νεα · {len(changed)} αλλαγες')
    for p in picks: print('  ' + line(p).replace('\n', ' | '))
    return picks

if __name__ == '__main__':
    main(notify_tg='--no-tg' not in sys.argv)
