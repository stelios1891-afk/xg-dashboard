# -*- coding: utf-8 -*-
"""nba_pin_open_hist.py — ΠΟΤΕ ΑΝΟΙΓΕ Η PINNACLE ΣΤΟ NBA (σεζον 2025-26) — The Odds API HISTORICAL (21/10/2026, Στελιος «τραβα περισσοτερα
ματς στην αρχη της σεζον … και 20-30 ματς ανα τακτα διαστηματα μεσα στη σεζον»).
Στοχοι: ΟΛΑ τα ματς κανονικης 21-26/10/2025 + 4 ματς σε καθε μια απο 8 ημερες μεσα στη σεζον (Νοε-Απρ).
Για καθε ματς: δυαδικη αναζητηση της ΠΡΩΤΗΣ «φωτογραφιας» TOA (ανα 5′) οπου η Pinnacle εχει χαντικαπ για το ματς, στο [τζαμπολ − 120ω, τζαμπολ − 1ω],
ακριβεια ~15′. Οι φωτογραφιες κρατιουνται (μια φωτογραφια δινει ΟΛΑ τα ματς NBA) → μοιραζονται μεταξυ ματς.
Κοστος: 10 credits/φωτογραφια (spreads, pinnacle). Ορια: CREDIT_BUDGET 9000 · σταματα αν τα credits του λογαριασμου < 30000.
Τρεχει στο GitHub (secret TOA_KEY, workflow nba-pin-open.yml). Εξοδος: nba_pin_open_hist.jsonl (+ nba_pin_open_state.json για συνεχεια)."""
import os, sys, json, time, datetime as dt, urllib.request, urllib.parse
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.abspath(__file__)); F = lambda n: os.path.join(ROOT, n)
KEY = os.environ.get('TOA_KEY'); CREDIT_BUDGET, STOP_REMAINING = 9000, 30000
OUT, STATE = F('nba_pin_open_hist.jsonl'), F('nba_pin_open_state.json')
DAYS_ALL = ['2025-10-21', '2025-10-22', '2025-10-23', '2025-10-24', '2025-10-25', '2025-10-26']
DAYS_4 = ['2025-11-10', '2025-12-01', '2025-12-22', '2026-01-12', '2026-02-02', '2026-02-24', '2026-03-16', '2026-04-06']
def last(s): return str(s).split()[-1].lower()
def targets():
    if os.path.exists(F('nba_pin_open_targets.json')):                 # στο GitHub: ετοιμη λιστα (το sched του Nowgoal δεν ειναι στο repo)
        T = json.load(open(F('nba_pin_open_targets.json'), encoding='utf-8'))
        for g in T: g['tip'] = dt.datetime.fromisoformat(g['tip'])
        return T
    S = json.load(open(F('nowgoal_nba/sched_25-26.json'), encoding='utf-8')); T = []
    for g in S:
        if g.get('kind') != 1: continue
        tip = dt.datetime.strptime(g['bj'], '%Y-%m-%d %H:%M').replace(tzinfo=dt.timezone.utc) - dt.timedelta(hours=8)
        us = (tip - dt.timedelta(hours=5)).date().isoformat(); g['tip'] = tip; g['us'] = us
    by = {}
    for g in S:
        if g.get('kind') == 1: by.setdefault(g['us'], []).append(g)
    for d in DAYS_ALL: T += sorted(by.get(d, []), key=lambda g: g['tip'])
    for d in DAYS_4: T += sorted(by.get(d, []), key=lambda g: g['tip'])[:4]
    return T
spent = 0; remaining = None
def snap(ts, cache):
    global spent, remaining
    k = ts.strftime('%Y-%m-%dT%H:%M:00Z')
    if k in cache: return cache[k]
    if spent + 10 > CREDIT_BUDGET or (remaining is not None and remaining < STOP_REMAINING): raise SystemExit(f'ορια credits (ξοδευτηκαν {spent}, μενουν {remaining})')
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
        has = any(m.get('key') == 'spreads' for b in e.get('bookmakers', []) if b.get('key') == 'pinnacle' for m in b.get('markets', []))
        if has:
            sp = next(m for b in e['bookmakers'] if b['key'] == 'pinnacle' for m in b['markets'] if m['key'] == 'spreads')
            ev.append(dict(h=e['home_team'], a=e['away_team'], ct=e['commence_time'], line=[(o['name'], o.get('point'), o.get('price')) for o in sp['outcomes']]))
    cache[k] = dict(snap=d.get('timestamp'), ev=ev); return cache[k]
def present(g, sv):
    if not sv: return None
    for e in sv['ev']:
        ct = dt.datetime.fromisoformat(e['ct'].replace('Z', '+00:00'))
        if abs((ct - g['tip']).total_seconds()) <= 5400 and last(e['h']) == last(g['home']) and last(e['a']) == last(g['away']): return e
    return None
def main():
    try: st = json.load(open(STATE, encoding='utf-8'))
    except Exception: st = {}
    if not KEY:
        json.dump(dict(st, last_error='TOA_KEY λειπει'), open(STATE, 'w', encoding='utf-8')); print('TOA_KEY λειπει'); return
    cache = st.get('cache', {}); done = set(st.get('done', []))
    try:
        for g in targets():
            key = f"{g['ngid']}"
            if key in done: continue
            hi = g['tip'] - dt.timedelta(hours=1); lo = g['tip'] - dt.timedelta(hours=120)
            e_hi = present(g, snap(hi, cache))
            rec = dict(ngid=g['ngid'], us=g['us'], tip=g['tip'].isoformat(), home=g['home'], away=g['away'])
            if not e_hi: rec.update(first=None, note='δεν βρεθηκε 1ω πριν')
            elif present(g, snap(lo, cache)): rec.update(first=lo.isoformat(), hours=120.0, note='ηδη 120ω πριν')
            else:
                while (hi - lo) > dt.timedelta(minutes=15):
                    mid = lo + (hi - lo) / 2; mid = mid.replace(minute=(mid.minute // 5) * 5, second=0, microsecond=0)
                    if mid <= lo or mid >= hi: break
                    if present(g, snap(mid, cache)): hi = mid
                    else: lo = mid
                e = present(g, snap(hi, cache))
                rec.update(first=hi.isoformat(), hours=round((g['tip'] - hi).total_seconds() / 3600, 2), first_line=e['line'] if e else None)
            with open(OUT, 'a', encoding='utf-8') as fh: fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
            if getattr(snap, 'err', None): st['last_error'] = 'τελευταιο σφαλμα αιτηματος: ' + snap.err
            done.add(key); print(f"{g['us']} {g['home']} – {g['away']}: πρωτη Pinnacle {rec.get('hours')}ω πριν · ξοδευτηκαν {spent} · μενουν {remaining}", flush=True)
    except BaseException as e:                                         # 21/10: το μηνυμα γραφεται στο state (τα logs του GitHub δεν φαινονται απο εδω)
        st['last_error'] = f'{type(e).__name__}: {e}'[:400]; print('ΣΤΑΣΗ:', st['last_error'], flush=True)
    finally:
        json.dump(dict(cache={k: v for k, v in list(cache.items())[-400:]}, done=sorted(done), spent=spent, remaining=remaining,
                       last_error=st.get('last_error'), t=dt.datetime.now(dt.timezone.utc).isoformat(timespec='minutes')), open(STATE, 'w', encoding='utf-8'))
        print(f'ΤΕΛΟΣ · credits {spent} · μενουν {remaining}', flush=True)
if __name__ == '__main__':
    main()
