# -*- coding: utf-8 -*-
"""shadow_report.py — Αξιολογηση της σκιωδους καταγραφης (A vs C vs B2) στα ματς 2627.

Ανα ματς κραταει το snapshot πιο κοντα στο KO−24h (ιδια συμβαση με τα backtests).
Κριθεντα: settle με αποτελεσματα (teamgame_inputs 2627). Επερχομενα: τρεχοντα picks.
Τρεχει on demand: python shadow_report.py
"""
import sys, json, datetime
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks

THR_B2 = [0.02, 0.04, 0.06, 0.08]

rows = {}
for line in open('shadow_picks.jsonl', encoding='utf-8'):
    r = json.loads(line)
    try:
        ko = datetime.datetime.fromisoformat(r['ko'].replace('Z', '+00:00'))
        t = datetime.datetime.fromisoformat(r['t'])
    except Exception:
        continue
    if t > ko:
        continue
    key = (r['hid'], r['aid'], r['ko'])
    d = abs((t - (ko - datetime.timedelta(hours=24))).total_seconds())
    if key not in rows or d < rows[key][0]:
        rows[key] = (d, r, ko)

TG = pd.read_csv('teamgame_inputs.csv')
TG['season'] = TG.season.astype(str)
cur = TG[TG.season == '2627']
res = {}
nmatch = {}
for _, g in cur[cur.is_home == True].iterrows():   # noqa: E712
    res[(int(g.team), int(g.opp))] = g.gf
for _, g in cur[cur.is_home == False].iterrows():  # noqa: E712
    k = (int(g.opp), int(g.team))
    if k in res:
        res[k] = res[k] - g.gf
for t_, g in cur.groupby('team'):
    nmatch[int(t_)] = len(g)

now = datetime.datetime.now(datetime.timezone.utc)
done = []; up = []
for (hid, aid, koiso), (_, r, ko) in rows.items():
    gd = res.get((hid, aid))
    if ko < now and gd is not None:
        done.append((r, gd))
    elif ko >= now:
        up.append(r)

print(f'σκιωδης καταγραφη: {len(rows)} ματς με snapshot · κριθεντα {len(done)} · επερχομενα {len(up)}')


def o_dog(r):
    return r['oh'] if r['dside'] == 1 else r['oa']


def cell(bets):
    if not bets:
        return '   -'
    n = len(bets); m = sum(bets) / n
    return f'{n:3d} bets {m*100:+7.2f}%  {sum(bets):+6.2f}u'


if done:
    print()
    print('=== ΚΡΙΘΕΝΤΑ (γραμμη ~-24h) ===')
    sysrows = []
    for r, gd in done:
        pnl = picks.settle(gd, r['dside'], r['ud'], o_dog(r))
        sysrows.append(dict(r=r, gd=gd, pnl=pnl))
    a = [s['pnl'] for s in sysrows if s['r']['isA']]
    c = [s['pnl'] for s in sysrows if s['r']['isC']]
    print(f"  A  (σημερινο @10%) : {cell(a)}")
    print(f"  C  (x.0/x.5  @10%) : {cell(c)}")
    for thr in THR_B2:
        b = [s['pnl'] for s in sysrows
             if s['r']['e_B2'] >= thr and picks.OMIN <= o_dog(s['r']) <= picks.OMAX]
        print(f"  B2 (ειλικρινες @{thr*100:.0f}%): {cell(b)}")
    for thr in (0.02, 0.04):
        k = [s['pnl'] for s in sysrows if s['r']['isA'] and s['r']['isC'] and s['r']['e_B2'] >= thr]
        print(f"  ΣΥΜΦΩΝΙΑ Α∩C∩B2>={thr*100:.0f}% : {cell(k)}")
    f2 = [picks.settle(s['gd'], -s['r']['dside'], -s['r']['ud'], s['r']['o_fav'])
          for s in sysrows
          if s['r']['e_B2f'] >= 0.02 and picks.OMIN <= s['r']['o_fav'] <= picks.OMAX]
    print(f"  φαβορι B2>=2% (πληροφοριακα, κλειστη υποθεση): {cell(f2)}")

if up:
    print()
    print('=== ΕΠΕΡΧΟΜΕΝΑ: τι λεει το καθε συστημα ===')
    for r in sorted(up, key=lambda z: z['ko']):
        tags = []
        if r['isA']:
            tags.append(f"A {r['e_A']*100:.0f}%")
        if r['isC']:
            tags.append(f"C {r['e_C']*100:.0f}%")
        if r['e_B2'] >= 0.02 and picks.OMIN <= o_dog(r) <= picks.OMAX:
            tags.append(f"B2 {r['e_B2']*100:.0f}%")
        if r['e_B2f'] >= 0.02 and picks.OMIN <= r['o_fav'] <= picks.OMAX:
            tags.append(f"B2-fav {r['e_B2f']*100:.0f}%")
        if not tags:
            continue
        dog = r['home'] if r['dside'] == 1 else r['away']
        print(f"  {r['ko'][:10]} {r['lg']:11s} {r['home'][:15]:15s}-{r['away'][:15]:15s} "
              f"dog {dog[:12]:12s} {r['ud']:+.2f} @{o_dog(r):.2f}  ->  {' · '.join(tags)}")
