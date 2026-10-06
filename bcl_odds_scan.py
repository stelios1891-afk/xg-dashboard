# -*- coding: utf-8 -*-
"""bcl_odds_scan.py — Basketball Champions League: τιμες Pinnacle (league 197844, 0 credits) + ΠΡΟΒΛΕΨΗ για καθε ματς (6/10/2026).
Τρεχει στον scanner (καθε τικ, το πολυ 1 / 10'). Ταιριασμα ονοματων Pinnacle → κωδικος Flashscore (bcl_state.json, ομαδες BCL φετος πρωτα).
Προβλεψη διαφορας γηπ = (1 − A)·Μ1 + A·Μ2 (bcl_refresh.py). Ιδια μορφη αρχειων με EuroCup (ec_*), ωστε picks/dashboard να δουλευουν ιδια.
Εξοδος: bcl_projections.json (ματς + προβλεψη) · bcl_odds_latest.json · bcl_odds_hist.jsonl (διαδρομη τιμων)."""
import os, sys, json, re, unicodedata, datetime
try: sys.stdout.reconfigure(encoding='utf-8')
except Exception: pass
import el_odds_scan as E
ROOT = os.path.dirname(os.path.abspath(__file__))
F = lambda n: os.path.join(ROOT, n)
WINDOW_H, GAP_MIN, LEAGUE = 48, 10, 197844
FORCE = os.environ.get('BCL_FORCE') == '1'
STOP = {'basket', 'basketball', 'bc', 'bk', 'kk', 'club', 'cb', 'sc', 'fc', 'kc', 'bbc', 'telekom', 'the'}
def toks(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    return {w for w in re.split(r'[^a-z0-9]+', s) if len(w) >= 3 and w not in STOP}
def match_team(name, st):
    tn = toks(name); best = (0, None)
    pool = [(t, st['names'].get(t, [])) for t in st['bcl_teams']] + [(t, v) for t, v in st['names'].items() if t not in st['bcl_teams']]
    for k, (t, nms) in enumerate(pool):
        for nm in nms:
            tt = toks(nm)
            if not tt or not tn: continue
            sc = len(tn & tt) / min(len(tn), len(tt)) + (0.05 if k < len(st['bcl_teams']) else 0)
            if sc > best[0]: best = (sc, t)
    return best[1] if best[0] >= 0.5 else None
def predict(st, h, a):
    m2 = st['m2']; r = m2['r']
    p2 = (r[h] - r[a] + m2['h']) if h in r and a in r else None
    m1 = st.get('m1') or {}
    p1 = None
    if h in m1.get('O', {}) and a in m1.get('O', {}):
        p1 = m1['pace'] * (m1['h'] + m1['O'][h] + m1['D'][a] - m1['O'][a] - m1['D'][h]) / 100
    if p1 is None and p2 is None: return None, None, None
    if p1 is None: return p2, p1, p2
    if p2 is None: return p1, p1, p2
    return (1 - st['A']) * p1 + st['A'] * p2, p1, p2
def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    try: st = json.load(open(F('bcl_state.json'), encoding='utf-8'))
    except Exception as e: print('BCL: bcl_state.json λειπει —', e); return
    try: old = json.load(open(F('bcl_odds_latest.json'), encoding='utf-8'))
    except Exception: old = {}
    try: age = (now - E._pdt(old['scanned_at'])).total_seconds() / 60
    except Exception: age = 1e9
    if age < GAP_MIN and not FORCE: print(f'BCL: τελευταιο scan πριν {age:.0f}λ — skip'); return
    import pin_api
    try: data = pin_api.toa_like(LEAGUE, include_alt=True)
    except pin_api.PinError as e: print('BCL: Pinnacle σφαλμα', e); return
    try: P = json.load(open(F('bcl_projections.json'), encoding='utf-8'))
    except Exception: P = {}
    games = {str(g['code']): g for g in P.get('games', [])}
    nomatch = []
    for g in data:
        try: ko = E._pdt(g['commence_time'])
        except Exception: continue
        code = str(g.get('id'))
        if ko <= now or (ko - now).total_seconds() > WINDOW_H * 3600:
            continue
        h, a = match_team(g['home_team'], st), match_team(g['away_team'], st)
        if not h or not a: nomatch.append(f"{g['home_team']} - {g['away_team']}"); continue
        mg, p1, p2 = predict(st, h, a)
        if mg is None: nomatch.append(f"{g['home_team']} - {g['away_team']} (χωρις rating)"); continue
        games[code] = dict(code=code, round=None, group=None, utc=ko.isoformat().replace('+00:00', 'Z'), home=g['home_team'], away=g['away_team'], hcode=h, acode=a,
                           margin=round(mg, 2), m_bcl=None if p1 is None else round(p1, 2), m_common=None if p2 is None else round(p2, 2), played=False)
    # ματς που ξεκινησαν → played (κρατιουνται 2 μερες για το Pick History)
    # ματς που ξεκινησαν → played· σκορ απο Flashscore (fs_bk_games, ανανεωνεται στο bcl_refresh) για το Pick History
    res = {}
    try:
        for e in json.load(open(F('fs_bk_games.json'), encoding='utf-8')).get(f"BCL_{st['season']}", []):
            if e.get('hs') not in (None, '') and e.get('ts'): res.setdefault((e['hid'], e['aid']), []).append((e['ts'], int(e['hs']), int(e['as_'])))
    except Exception: pass
    for k, g in list(games.items()):
        ko = E._pdt(g['utc'])
        if ko <= now: g['played'] = True
        if g['played'] and g.get('hs') is None:
            for ts, hs, as_ in res.get((g['hcode'], g['acode']), []):
                if abs(ts - ko.timestamp()) <= 36 * 3600: g['hs'], g['as_'] = hs, as_
    json.dump(dict(generated=now.isoformat(timespec='minutes'), season=st['season'], comp='BCL', model=st.get('model'), sigma_margin=st.get('sigma', 12.5),
                   games=sorted(games.values(), key=lambda g: g['utc'])), open(F('bcl_projections.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    up = [dict(code=g['code'], round=None, utc=E._pdt(g['utc']), hcode=g['hcode'], acode=g['acode'], home=g['home'], away=g['away']) for g in games.values() if not g['played']]
    odds, hist_rows, unmatched, nmatch = E.build_records(list(data), up, now, old.get('odds', {}))
    json.dump(dict(scanned_at=now.isoformat()[:16], season=st['season'], src='pinnacle', n_games=nmatch, unmatched=unmatched[:20], odds=odds),
              open(F('bcl_odds_latest.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    if hist_rows:
        with open(F('bcl_odds_hist.jsonl'), 'a', encoding='utf-8') as hf:
            for row in hist_rows: hf.write(json.dumps(row, ensure_ascii=False) + chr(10))
    print(f'BCL: Pinnacle {len(data)} ματς · με προβλεψη {len(up)} · τιμες {nmatch}' + (f' · ΧΩΡΙΣ ταιριασμα: {"; ".join(nomatch[:6])}' if nomatch else ''))
if __name__ == '__main__':
    main()
