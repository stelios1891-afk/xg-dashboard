# -*- coding: utf-8 -*-
"""nba_odds_scan.py — NBA: τιμες Pinnacle (league 487, 0 credits) + ΠΡΟΒΛΕΨΗ για καθε ματς (6/10/2026, Στελιος «φτιαξε τη μηχανη»).
Τρεχει στον scanner (το πολυ 1 / 10'). Προβλεψη απο nba_state.json (nba_refresh.py):
  διαφορα = κατοχες × (επιθ_γηπ + αμυνα_φιλ + εδρα/2 − επιθ_φιλ − αμυνα_γηπ − εδρα/2)/100 + 3 × (B2B φιλ − B2B γηπ)
  συνολο  = κατοχες × (2μ + επιθ + αμυνες)/100 + Φ3 (επιπεδο τελευταιων 150 ματς)
Back-to-back: η ομαδα επαιξε την προηγουμενη μερα (ESPN) ή εχει ματς Pinnacle την προηγουμενη μερα.
Εξοδος (ιδια μορφη με EuroCup/BCL): nba_projections.json · nba_odds_latest.json · nba_odds_hist.jsonl. --results: μονο σκορ (ESPN)."""
import os, sys, json, math, datetime
try: sys.stdout.reconfigure(encoding='utf-8')
except Exception: pass
import el_odds_scan as E
from nba_espn import TEAMNAME, us_date
ROOT = os.path.dirname(os.path.abspath(__file__))
F = lambda n: os.path.join(ROOT, n)
WINDOW_H, GAP_MIN, LEAGUE = int(os.environ.get('NBA_WINDOW_H', 48)), 10, 487
FORCE = os.environ.get('NBA_FORCE') == '1'
Phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))
def code_of(name):
    if name in TEAMNAME: return TEAMNAME[name]
    low = (name or '').lower()
    for k, v in TEAMNAME.items():
        if k.split()[-1].lower() in low: return v
    return None
def predict(st, h, a, b2h, b2a):
    E1, E2 = st['h_eng'], st['t_eng']
    if h not in E1['O'] or a not in E1['O']: return None
    hb = st['h'] / 2
    eh = E1['mu'] + E1['O'][h] + E1['D'][a] + hb; ea = E1['mu'] + E1['O'][a] + E1['D'][h] - hb; poss = E1['pm'] + E1['P'][h] + E1['P'][a]
    m = poss * (eh - ea) / 100 + st['b2b_k'] * (b2a - b2h)
    th = E2['mu'] + E2['O'][h] + E2['D'][a]; ta = E2['mu'] + E2['O'][a] + E2['D'][h]; pt = E2['pm'] + E2['P'][h] + E2['P'][a]
    t = pt * (th + ta) / 100 + st.get('res_t', 0.0)
    return m, t
def finish(games, st, now):
    """Σκορ (ESPN) + εβδομαδα + ratings → nba_projections.json."""
    try: GM = json.load(open(F('nba_espn_games.json'), encoding='utf-8'))
    except Exception: GM = {}
    res = {}
    for g in GM.values():
        if g['stype'] == 2: res.setdefault((g['home'], g['away']), []).append((g['date'], g['hs'], g['as_']))
    for g in games.values():
        ko = E._pdt(g['utc'])
        if ko <= now: g['played'] = True
        if g['played'] and g.get('hs') is None:
            d0 = us_date(g['utc'])
            for d, hs, as_ in res.get((g['hcode'], g['acode']), []):
                if abs((datetime.date.fromisoformat(d) - datetime.date.fromisoformat(d0)).days) <= 1: g['hs'], g['as_'] = hs, as_
    wk = sorted({E._pdt(g['utc']).date().isocalendar()[:2] for g in games.values()})
    for g in games.values(): g['round'] = wk.index(E._pdt(g['utc']).date().isocalendar()[:2]) + 1
    E1 = st['h_eng']; nm = {v: k for k, v in TEAMNAME.items()}
    ratings = [dict(code=t, name=nm.get(t, t), net=round(E1['O'][t] - E1['D'][t], 2), O=round(E1['O'][t], 2), D=round(E1['D'][t], 2), pace=round(E1['P'][t], 2),
                    games=st['gp'].get(t, 0)) for t in E1['O']]
    json.dump(dict(generated=now.isoformat(timespec='minutes'), season=st['season'], comp='NBA', model=st.get('model'), sigma_margin=st['sig_m'], sigma_total=st['sig_t'],
                   res_t=st.get('res_t'), games=sorted(games.values(), key=lambda g: g['utc']), ratings=ratings),
              open(F('nba_projections.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    try: st = json.load(open(F('nba_state.json'), encoding='utf-8'))
    except Exception as e: print('NBA: nba_state.json λειπει —', e); return
    try: old = json.load(open(F('nba_odds_latest.json'), encoding='utf-8'))
    except Exception: old = {}
    try: age = (now - E._pdt(old['scanned_at'])).total_seconds() / 60
    except Exception: age = 1e9
    if age < GAP_MIN and not FORCE: print(f'NBA: τελευταιο scan πριν {age:.0f}λ — skip'); return
    import pin_api
    try: data = pin_api.toa_like(LEAGUE, include_alt=True)
    except pin_api.PinError as e: print('NBA: Pinnacle σφαλμα', e); return
    try: P = json.load(open(F('nba_projections.json'), encoding='utf-8'))
    except Exception: P = {}
    games = {str(g['code']): g for g in P.get('games', [])}
    # ημερες ματς καθε ομαδας (ESPN παιγμενα + Pinnacle προγραμμα) για το back-to-back
    days = {}
    for t, d in st.get('last', {}).items(): days.setdefault(t, set()).add(d)
    for g in data:
        try: d = us_date(g['commence_time'])
        except Exception: continue
        for nmx in (g['home_team'], g['away_team']):
            c = code_of(nmx)
            if c: days.setdefault(c, set()).add(d)
    nomatch = []
    for g in data:
        try: ko = E._pdt(g['commence_time'])
        except Exception: continue
        code = str(g.get('id'))
        if ko <= now or (ko - now).total_seconds() > WINDOW_H * 3600: continue
        h, a = code_of(g['home_team']), code_of(g['away_team'])
        if not h or not a: nomatch.append(f"{g['home_team']} - {g['away_team']}"); continue
        d = us_date(g['commence_time']); yd = (datetime.date.fromisoformat(d) - datetime.timedelta(days=1)).isoformat()
        b2h, b2a = int(yd in days.get(h, ())), int(yd in days.get(a, ()))
        pr = predict(st, h, a, b2h, b2a)
        if pr is None: nomatch.append(f"{g['home_team']} - {g['away_team']} (χωρις rating)"); continue
        m, T = pr
        games[code] = dict(code=code, round=None, phase='RS', group=None, utc=ko.isoformat().replace('+00:00', 'Z'), home=g['home_team'], away=g['away_team'], hcode=h, acode=a,
                           margin=round(m, 2), total=round(T, 1), total_src='μοντελο', pts_h=round((T + m) / 2, 1), pts_a=round((T - m) / 2, 1),
                           p_home=round(Phi(m / st['sig_m']), 3), played=False, version='nba1', venue='', b2b_h=b2h, b2b_a=b2a,
                           gno=max(st['gp'].get(h, 0), st['gp'].get(a, 0)), gp_h=st['gp'].get(h, 0), gp_a=st['gp'].get(a, 0))
    finish(games, st, now)
    up = [dict(code=g['code'], round=None, utc=E._pdt(g['utc']), hcode=g['hcode'], acode=g['acode'], home=g['home'], away=g['away']) for g in games.values() if not g['played']]
    odds, hist_rows, unmatched, nmatch = E.build_records(list(data), up, now, old.get('odds', {}))
    json.dump(dict(scanned_at=now.isoformat()[:16], season=st['season'], src='pinnacle', n_games=nmatch, unmatched=unmatched[:20], odds=odds),
              open(F('nba_odds_latest.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    if hist_rows:
        with open(F('nba_odds_hist.jsonl'), 'a', encoding='utf-8') as hf:
            for row in hist_rows: hf.write(json.dumps(row, ensure_ascii=False) + chr(10))
    print(f'NBA: Pinnacle {len(data)} ματς · με προβλεψη {len(up)} · τιμες {nmatch}' + (f' · ΧΩΡΙΣ ταιριασμα: {"; ".join(nomatch[:6])}' if nomatch else ''))
def results_only():
    now = datetime.datetime.now(datetime.timezone.utc)
    st = json.load(open(F('nba_state.json'), encoding='utf-8')); P = json.load(open(F('nba_projections.json'), encoding='utf-8'))
    finish({str(g['code']): g for g in P.get('games', [])}, st, now); print('NBA: σκορ ενημερωθηκαν')
def _status(ok, msg):
    try: json.dump(dict(t=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='minutes'), ok=ok, msg=str(msg)[:300]), open(F('nba_scan_status.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    except Exception: pass
if __name__ == '__main__':
    import io, contextlib, traceback
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            results_only() if '--results' in sys.argv else main()
        print(buf.getvalue(), end=''); _status(True, (buf.getvalue().strip().splitlines() or [''])[-1])   # 7/10: κατασταση για διαγνωση στο GitHub
    except Exception as e:
        print(buf.getvalue(), end=''); traceback.print_exc(); _status(False, f'{type(e).__name__}: {e}'); raise
