# -*- coding: utf-8 -*-
"""intl90_scan.py — 19/10/2026: ελεγχος 90' για τα ματς εθνικων που ΔΕΝ ελεγξε το euro_regulation
(αρχεια χωρις σουτ: AFCON 2012-21, AFCONQ, AsianCup 2023, GoldCup 2023, WCQ CAF/AFC/CONCACAF, φιλικα + intl_results_scores.json).
Μονο αναγνωση: γραφει intl90_scan.json (mid -> {src, ft90, final, reason}) και intl90_results_scores_fixed.json. Τα originals ΔΕΝ αλλαζουν."""
import json, glob, re, os, sys, time
from concurrent.futures import ThreadPoolExecutor
sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0, '.')
import intl_fetch

CT = ['Friendlies', 'NationsLeagueA', 'NationsLeagueB', 'NationsLeagueC', 'NationsLeagueD', 'WCQ_UEFA', 'EUROQ', 'WCQ_CONMEBOL', 'WCQ_AFC',
      'WCQ_CAF', 'WCQ_CONCACAF', 'EURO', 'WorldCup', 'CopaAmerica', 'AFCON', 'AsianCup', 'GoldCup', 'AFCONQ']
REG = ('FirstHalf', 'SecondHalf')
todo = {}          # mid -> (src, hs, as, home, away, date)
seen = set()
for f in sorted(glob.glob('data_*.json')):
    m = re.match(r'data_([A-Za-z_]+?)_(\d{4})\.json$', os.path.basename(f))
    if not m or m.group(1) not in CT:
        continue
    for mid, r in json.load(open(f, encoding='utf-8')).items():
        if r.get('hs') is None:
            continue
        seen.add(str(mid))
        if r.get('p90') or r.get('shots'):
            continue                      # ελεγμενο απο euro_regulation ή εχει σουτ (καμια βολη >90' → οχι παραταση)
        try:
            int(str(r.get('round'))); continue      # ομιλος
        except Exception:
            pass
        todo.setdefault(str(mid), (os.path.basename(f), r['hs'], r['as'], r['home']['name'], r['away']['name'], str(r.get('date'))))
S = json.load(open('intl_results_scores.json', encoding='utf-8'))
for mid, r in S.items():
    if mid in seen or r['comp'] not in CT:
        continue
    todo.setdefault(mid, ('intl_results_scores.json:' + r['comp'] + '_' + r['sea'], r['hs'], r['as'], r['hname'], r['aname'], r['utc']))
print('προς ελεγχο:', len(todo))


def chk(mid):
    try:
        md = json.loads(intl_fetch.get(f'https://www.fotmob.com/api/data/matchDetails?matchId={mid}'))
    except Exception as e:
        return mid, dict(err=str(e)[:80])
    c = md.get('content') or {}
    ev = ((c.get('matchFacts') or {}).get('events') or {}).get('events', []) or []
    shots = (c.get('shotmap') or {}).get('shots') or []
    halves = [e.get('halfStrShort') for e in ev if e.get('type') == 'Half']
    st = (md.get('header') or {}).get('status') or {}
    reason = ((st.get('reason') or {}).get('short') or '')
    extra = any(h in ('AET', 'PEN', 'Pen', 'AP') for h in halves) or any(s.get('period') not in REG for s in shots if s.get('period')) \
        or reason in ('AET', 'Pen', 'PEN', 'AP')
    ft = next((e for e in ev if e.get('type') == 'Half' and e.get('halfStrShort') == 'FT'), None)
    teams = (md.get('header') or {}).get('teams') or []
    fin = (teams[0].get('score'), teams[1].get('score')) if len(teams) > 1 else (None, None)
    return mid, dict(extra=bool(extra), reason=reason, halves=halves, ft90=((ft['homeScore'], ft['awayScore']) if ft and ft.get('homeScore') is not None else None),
                     final=fin, n_ev=len(ev))


res = {}
with ThreadPoolExecutor(4) as ex:
    for i, (mid, r) in enumerate(ex.map(chk, list(todo))):
        res[mid] = dict(r, src=todo[mid][0], stored=(todo[mid][1], todo[mid][2]), home=todo[mid][3], away=todo[mid][4], date=todo[mid][5])
        if (i + 1) % 200 == 0:
            print(i + 1, flush=True)
json.dump(res, open('intl90_scan.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
err = [m for m, r in res.items() if r.get('err')]
ext = {m: r for m, r in res.items() if r.get('extra')}
print(f'λαθη fetch: {len(err)} · με παραταση/πεναλτι: {len(ext)}')
for m, r in sorted(ext.items(), key=lambda kv: kv[1]['date']):
    chg = r['ft90'] is not None and tuple(r['ft90']) != tuple(r['stored'])
    print(f"{r['date'][:16]:16s} {r['src'][:38]:38s} {r['home'][:18]:18s}-{r['away'][:18]:18s} αρχειο {r['stored'][0]}-{r['stored'][1]} · 90' {r['ft90']} · τελικο {r['final']} · {r['reason']} {'ΑΛΛΑΓΗ' if chg else ''}")
# διορθωμενο αντιγραφο του score-only αρχειου
fx = json.load(open('intl_results_scores.json', encoding='utf-8')); nfix = 0
for m, r in ext.items():
    if m in fx and r['ft90'] is not None and tuple(r['ft90']) != (fx[m]['hs'], fx[m]['as']):
        fx[m]['hs_ft'], fx[m]['as_ft'] = fx[m]['hs'], fx[m]['as']; fx[m]['hs'], fx[m]['as'] = r['ft90']; fx[m]['reg90'] = True; nfix += 1
json.dump(fx, open('intl90_results_scores_fixed.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('intl90_results_scores_fixed.json: διορθωθηκαν', nfix)
