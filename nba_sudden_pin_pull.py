# -*- coding: utf-8 -*-
"""nba_sudden_pin_pull.py — ΑΙΦΝΙΔΙΑ OUT: ΤΙΜΕΣ PINNACLE ΣΤΙΣ ΣΤΙΓΜΕΣ ΜΕΤΑ ΤΗΝ ΕΙΔΗΣΗ (24/10/2026, Στελιος «τα συγκεκριμενα ματς, 4-5 στιγμες
μετα την ειδηση» + «οκ» για ~26.5k credits ΜΕΤΑ την ανανεωση της 1/11).
Στοχοι: nba_sudden_targets.json (απο nba_tests/t70_sudden_out.py: 723 αιφνιδια Out NBC 2021-26) → ΜΟΝΟ σεζον 2022-23…2025-26 (φωτογραφιες
TOA ανα 5′ απο 9/2022) ΚΑΙ ωρα ειδησης 08:00-02:00 Ελλαδας («ξυπνιος»).
Στιγμες ανα ειδηση (The Odds API historical, η φωτογραφια με ωρα ≤ της ζητουμενης): πριν (t0) · ≤5′ · ≤10′ · ≤15′ · κλεισιμο (τζαμπολ −1′).
Κοστος: 10 credits/φωτογραφια (spreads, pinnacle) · ~530 ειδησεις × 5 ≈ 26.5k. ΟΡΙΑ: CREDIT_BUDGET 30000 · σταματα αν τα credits < 60000.
ΔΕΝ ξεκινα πριν την 1/11/2026 (εκτος SUDDEN_FORCE=1). Συνεχιζει απο εκει που σταματησε (state).
Τρεχει στο GitHub (secret TOA_KEY, workflow nba-sudden-pin.yml). Εξοδος: nba_sudden_pin.jsonl · nba_sudden_pin_state.json."""
import os, sys, json, time, datetime as dt, urllib.request, urllib.parse
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.abspath(__file__)); F = lambda n: os.path.join(ROOT, n)
KEY = os.environ.get('TOA_KEY'); CREDIT_BUDGET, STOP_REMAINING = 30000, 60000
START = dt.datetime(2026, 11, 1, tzinfo=dt.timezone.utc)
OUT, STATE, TGT = F('nba_sudden_pin.jsonl'), F('nba_sudden_pin_state.json'), F('nba_sudden_targets.json')
MOMENTS = (('πριν', 0), ('≤5′', 5), ('≤10′', 10), ('≤15′', 15))
from nba_espn import TEAMNAME
CODE2NAME = {}
for n_, c_ in TEAMNAME.items(): CODE2NAME.setdefault(c_, n_)
def last(s): return str(s).split()[-1].lower()
spent = 0; remaining = None
def snap(ts, cache):
    global spent, remaining
    k = ts.strftime('%Y-%m-%dT%H:%M:%SZ')
    if k in cache: return cache[k]
    if spent + 10 > CREDIT_BUDGET or (remaining is not None and remaining < STOP_REMAINING):
        raise SystemExit(f'ορια credits (ξοδευτηκαν {spent}, μενουν {remaining})')
    u = 'https://api.the-odds-api.com/v4/historical/sports/basketball_nba/odds?' + urllib.parse.urlencode(
        dict(apiKey=KEY, markets='spreads', bookmakers='pinnacle', oddsFormat='decimal', date=k))
    for a in range(4):
        try:
            r = urllib.request.urlopen(u, timeout=60); d = json.loads(r.read())
            remaining = int(r.headers.get('x-requests-remaining') or 0); spent += int(r.headers.get('x-requests-last') or 10)
            break
        except Exception as e:
            print('σφαλμα', k, str(e)[:120], flush=True); snap.err = f'{k}: {str(e)[:150]}'; time.sleep(5 + 10 * a)
    else: return None
    ev = []
    for e in d.get('data', []):
        for b in e.get('bookmakers', []):
            if b.get('key') != 'pinnacle': continue
            for m in b.get('markets', []):
                if m.get('key') == 'spreads':
                    ev.append(dict(h=e['home_team'], a=e['away_team'], ct=e['commence_time'], upd=m.get('last_update') or b.get('last_update'),
                                   line=[(o['name'], o.get('point'), o.get('price')) for o in m['outcomes']]))
    cache[k] = dict(snap=d.get('timestamp'), ev=ev); return cache[k]
def find(t, sv):
    if not sv: return None
    tip = dt.datetime.fromisoformat(t['tip']); hn, an = CODE2NAME.get(t['home'], t['home']), CODE2NAME.get(t['away'], t['away'])
    for e in sv['ev']:
        ct = dt.datetime.fromisoformat(e['ct'].replace('Z', '+00:00'))
        if abs((ct - tip).total_seconds()) <= 5400 and last(e['h']) == last(hn) and last(e['a']) == last(an):
            hl = next((o for o in e['line'] if last(o[0]) == last(hn)), None); al = next((o for o in e['line'] if last(o[0]) == last(an)), None)
            return dict(snap=sv['snap'], upd=e.get('upd'), line_home=hl[1] if hl else None, odds_home=hl[2] if hl else None, odds_away=al[2] if al else None)
    return None
def targets():
    T = json.load(open(TGT, encoding='utf-8'))
    return [t for t in T if t['S'] >= 2023 and (t['gr_hour'] >= 8 or t['gr_hour'] < 2)]
def main():
    try: st = json.load(open(STATE, encoding='utf-8'))
    except Exception: st = {}
    now = dt.datetime.now(dt.timezone.utc)
    if now < START and os.environ.get('SUDDEN_FORCE') != '1':
        print(f'περιμενει την ανανεωση credits της 1/11 (τωρα {now:%d/%m %H:%M} UTC) — 0 credits'); return
    if not KEY:
        json.dump(dict(st, last_error='TOA_KEY λειπει'), open(STATE, 'w', encoding='utf-8')); print('TOA_KEY λειπει'); return
    cache = {}; done = set(st.get('done', [])); T = targets()
    print(f'στοχοι {len(T)} · ηδη {len(done)}', flush=True)
    try:
        for t in T:
            key = f"{t['t0']}|{t['home']}|{t['away']}|{t['lost']}"
            if key in done: continue
            t0 = dt.datetime.fromisoformat(t['t0']); tip = dt.datetime.fromisoformat(t['tip'])
            rec = dict(t, pin={})
            for lab, mins in MOMENTS:
                ts = t0 + dt.timedelta(minutes=mins)
                if ts >= tip - dt.timedelta(minutes=1): continue
                rec['pin'][lab] = find(t, snap(ts, cache))
            rec['pin']['κλεισιμο'] = find(t, snap(tip - dt.timedelta(minutes=1), cache))
            with open(OUT, 'a', encoding='utf-8') as fh: fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
            done.add(key)
            if len(done) % 20 == 0: print(f'{len(done)}/{len(T)} · ξοδευτηκαν {spent} · μενουν {remaining}', flush=True)
        st['last_error'] = None; print('ΟΛΟΙ ΟΙ ΣΤΟΧΟΙ ΕΤΟΙΜΟΙ', flush=True)
    except BaseException as e:
        st['last_error'] = f'{type(e).__name__}: {e}'[:400]; print('ΣΤΑΣΗ:', st['last_error'], flush=True)
    finally:
        if getattr(snap, 'err', None): st['last_req_error'] = snap.err
        json.dump(dict(done=sorted(done), n_targets=len(T), spent_total=int(st.get('spent_total', 0)) + spent, remaining=remaining,
                       last_error=st.get('last_error'), last_req_error=st.get('last_req_error'),
                       t=dt.datetime.now(dt.timezone.utc).isoformat(timespec='minutes')), open(STATE, 'w', encoding='utf-8'), ensure_ascii=False)
        print(f'ΤΕΛΟΣ · credits αυτο το τρεξιμο {spent} · μενουν {remaining}', flush=True)
if __name__ == '__main__':
    main()
