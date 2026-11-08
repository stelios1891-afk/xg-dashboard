# -*- coding: utf-8 -*-
"""nba_ratings_due.py — NBA: ΔΥΝΑΜΕΙΣ ΟΜΑΔΩΝ ΑΜΕΣΩΣ ΜΕΤΑ ΤΑ ΜΑΤΣ (29/10/2026, Στελιος «περνα και τα 2»).
Προβλημα: οι δυναμεις (nba_state.json) ανανεωνονταν μονο με το πρωινο nba_refresh (euro-refresh, ~08:30 Ελλαδας) → απο το τελος των
βραδινων ματς ως τοτε ο scanner εβγαζε picks με δυναμεις ΧΩΡΙΣ το χθεσινο ματς (Πελικανς–Κινγκς Over 237.5: +11% → −12% μετα την ανανεωση).
Τρεχει σε καθε τικ του scanner, ΜΕΤΑ το bk_results_due (που φερνει τα σκορ ESPN) και ΠΡΙΝ το nba_odds_scan:
  αν υπαρχει τελειωμενο ματς κανονικης περιοδου (nba_espn_games.json) με ημερα ΜΕΤΑ την τελευταια μερα των δυναμεων καποιας ομαδας →
  nba_refresh.py --no-fetch (~25″, χωρις Telegram) και αμεσως νεες προβλεψεις (nba_odds_scan.py με NBA_FORCE=1).
  Το πολυ 1 φορα / 20′· ιδια «υπογραφη» (ομαδες-ημερες) το πολυ 3 φορες (να μη γυριζει σε κυκλο αν κατι δεν περναει).
Το «φρενο» (nba_picks.stale_filter) κραταει τα picks αυτων των ματς ως τοτε. State: nba_ratings_due_state.json"""
import os, sys, json, subprocess, datetime as dt
try: sys.stdout.reconfigure(encoding='utf-8')
except Exception: pass
ROOT = os.path.dirname(os.path.abspath(__file__))
F = lambda n: os.path.join(ROOT, n)
ST_F, GAP_MIN, MAX_TRY = F('nba_ratings_due_state.json'), 20, 3

def _load(p, d):
    try: return json.load(open(p, encoding='utf-8'))
    except Exception: return d

def missing():
    """[(ομαδα, ημερα ΗΠΑ)] τελειωμενων ματς κανονικης περιοδου που ΔΕΝ ειναι ακομα στις δυναμεις"""
    last = _load(F('nba_state.json'), {}).get('last', {})
    out = set()
    for g in _load(F('nba_espn_games.json'), {}).values():
        if g.get('stype') != 2 or g.get('hs') is None: continue
        for t in (g.get('home'), g.get('away')):
            if t and g['date'] > str(last.get(t, '')): out.add((t, g['date']))
    return sorted(out)

def main():
    now = dt.datetime.now(dt.timezone.utc)
    if not os.path.exists(F('nba_state.json')): print('NBA δυναμεις: nba_state.json λειπει — τιποτα'); return
    M = missing()
    if not M: print('NBA δυναμεις: ενημερες'); return
    sig = ' '.join(f'{t}:{d}' for t, d in M); st = _load(ST_F, {})
    last = st.get('t')
    if last and (now - dt.datetime.fromisoformat(last)).total_seconds() < GAP_MIN * 60:
        print(f'NBA δυναμεις: λειπουν {len(M)} ({sig[:80]}) · τελευταια προσπαθεια πριν <{GAP_MIN}′ — skip'); return
    n = st.get('n', 0) + 1 if st.get('sig') == sig else 1
    if n > MAX_TRY:
        print(f'NBA δυναμεις: λειπουν {len(M)} αλλα η ιδια ενημερωση απετυχε {MAX_TRY} φορες — περιμενω το πρωινο nba_refresh'); return
    json.dump(dict(t=now.isoformat(timespec='minutes'), sig=sig, n=n), open(ST_F, 'w', encoding='utf-8'))
    print(f'NBA δυναμεις: λειπουν {len(M)} ({sig[:120]}) → nba_refresh.py --no-fetch', flush=True)
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    r = subprocess.run([sys.executable, 'nba_refresh.py', '--no-fetch'], cwd=ROOT, env=env, timeout=600, capture_output=True, text=True, encoding='utf-8', errors='replace')
    print('  nba_refresh: exit', r.returncode, '·', ((r.stdout or '').strip().splitlines() or [''])[-1][:160])
    if r.returncode != 0: print((r.stderr or '')[-600:]); return
    left = missing()
    print(f'  μετα: λειπουν {len(left)}' + (f' ({" ".join(f"{t}:{d}" for t, d in left)[:120]})' if left else ' ✓'))
    r2 = subprocess.run([sys.executable, 'nba_odds_scan.py'], cwd=ROOT, env=dict(env, NBA_FORCE='1'), timeout=600, capture_output=True, text=True, encoding='utf-8', errors='replace')
    print('  nba_odds_scan (νεες προβλεψεις): exit', r2.returncode, '·', ((r2.stdout or '').strip().splitlines() or [''])[-1][:160])

if __name__ == '__main__':
    main()
