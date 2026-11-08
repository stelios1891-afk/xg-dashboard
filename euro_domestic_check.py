"""euro_domestic_check.py — 9/10/2026 (Στελιος: «να δουμε οτι τα εγχωρια περνανε σωστα στα ratings των ευρωπαικων»).
Για καθε ομαδα των φετινων κυπελλων: ποσα φετινα εγχωρια ματς ΒΛΕΠΕΙ το ευρωπαικο μοντελο (side_state n) vs ποσα εχει ΠΡΑΓΜΑΤΙΚΑ
τελειωμενα (με σουτ) στο data_<λιγκα>_<σεζον>.json, + τελευταιο ματς ανα λιγκα (φρεσκαδα) + πηγη (FotMob/Ben/γκολ)."""
import sys, os, io, json, contextlib, runpy
from datetime import datetime, timezone
from collections import Counter
sys.path.insert(0, os.getcwd()); sys.stdout.reconfigure(encoding='utf-8')
os.environ['EURO_PROJ_OUT'] = os.path.join(os.environ.get('TEMP', '.'), 'ep_check.json')
with contextlib.redirect_stdout(io.StringIO()):
    g = runpy.run_path('euro_live_projections.py')
eng, fx, kodt, GKEYS = g['eng'], g['fx'], g['kodt'], g['GKEYS']
now = datetime.now(timezone.utc).replace(tzinfo=None)
teams = {}
for k, v in fx.items():
    for m in v:
        teams[int(m['hid'])] = m['hname']; teams[int(m['aid'])] = m['aname']
real = {}; last = {}
for tid in teams:
    st = g['_orig_side_state'](tid, now)
    if st is None: continue
    key = (st['lg'], st['sea'])
    if key not in real:
        p = f'data_{st["lg"]}_{st["sea"]}.json'; cnt = Counter(); mx = None
        if os.path.exists(p):
            for m in json.load(open(p, encoding='utf-8')).values():
                if m.get('hs') is None: continue
                d = kodt(m['date'])
                if d is None or d > now: continue
                if m.get('shots') or (key in eng.GOAL_ONLY):
                    cnt[int(m['home']['id'])] += 1; cnt[int(m['away']['id'])] += 1
                mx = d if mx is None or d > mx else mx
        real[key] = cnt; last[key] = mx
bad = []; ok = 0; miss = []; rows = []
for tid, nm in sorted(teams.items(), key=lambda x: x[1]):
    st = g['_orig_side_state'](tid, now)
    if st is None:
        miss.append(nm); continue
    key = (st['lg'], st['sea']); r = real[key].get(tid, 0)
    src = 'Ben' if key in GKEYS else ('γκολ' if key in eng.GOAL_ONLY else 'FotMob')
    rows.append((nm, st['lg'], st['sea'], st['n'], r, src))
    if st['n'] != r and src != 'Ben': bad.append((nm, st['lg'], st['sea'], st['n'], r, src))
    else: ok += 1
print(f'ομαδες κυπελλων: {len(teams)} · με rating {len(rows)} · χωρις rating {len(miss)}')
print(f'n μοντελου == πραγματικα ματς: {ok}/{len(rows)}')
for b in bad: print(f'   ΔΙΑΦΟΡΑ {b[0]:24s} {b[1]} {b[2]} μοντελο {b[3]} vs αρχειο {b[4]} [{b[5]}]')
if miss: print('   χωρις rating: ' + ', '.join(miss))
print('\nτελευταιο εγχωριο ματς ανα λιγκα (φρεσκαδα):')
for key, mx in sorted(last.items(), key=lambda x: x[1] or datetime(2000, 1, 1)):
    print(f'   {key[0]:16s} {key[1]}  {mx.strftime("%d/%m") if mx else "—"}  ({sum(1 for r in rows if (r[1], r[2]) == key)} ομαδες κυπελλων)')
print('\nπηγες:', Counter(r[5] for r in rows))
