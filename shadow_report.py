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
    key = (r['hid'], r['aid'])          # ενα ανα ματς — αν αλλαξε το ΚΟ, κραταμε το νεοτερο ΚΟ
    d = abs((t - (ko - datetime.timedelta(hours=24))).total_seconds())
    if key in rows and rows[key][2] != ko:
        if ko > rows[key][2]:
            rows[key] = (d, r, ko)      # νεο ΚΟ αντικαθιστα το παλιο
        continue
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
for (hid, aid), (_, r, ko) in rows.items():
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
    wi = [s['pnl'] for s in sysrows
          if s['r']['isA'] and (s['r'].get('e_I') or -1) >= picks.EDGE]
    print(f"  W∩I (live ∩ in-season)  : {cell(wi)}   [ενεργο απο τη 15η — πριν, e_I κενο]")
    f2 = [picks.settle(s['gd'], -s['r']['dside'], -s['r']['ud'], s['r']['o_fav'])
          for s in sysrows
          if s['r']['e_B2f'] >= 0.02 and picks.OMIN <= s['r']['o_fav'] <= picks.OMAX]
    print(f"  φαβορι B2>=2% (πληροφοριακα, κλειστη υποθεση): {cell(f2)}")

if done:
    # ---- #5 ετυμηγοριας 5.1 (16/9/2026): ΣΚΙΑ κατωφλιων ΔΗΛΩΜΕΝΟΥ edge ανα ΖΩΝΗ ----
    # Ζωνες: ΒΑΘΙΕΣ ud>=1 / ΜΕΣΑΙΕΣ ud<1. Πλεγμα προ-δηλωμενο: 6/8/10(live)/12/14%.
    # Ιστορικο prior (dom_edge_curve 5σ): βαθιες 5-10% = −5.2%±5.2 (το κατεβασμα ΔΕΝ
    # στηριζεται απο το backtest — η σκια καλειται να το διαψευσει, οχι να το κρινει
    # ξανα στο ιδιο δειγμα). ΠΡΟΧΕΙΡΟ κριτηριο κρισης (οριστικοποιειται με το 5.1 ΠΡΙΝ
    # την κριση, οχι μετα τα νουμερα): κατεβασμα πηχη ζωνης ΜΟΝΟ αν τα ΕΞΤΡΑ picks
    # (κατω απο το live @10) εχουν n>=40, ROI>0, t>=1 στη 2627· ανεβασμα ΜΟΝΟ αν τα
    # ΚΟΜΜΕΝΑ (10→νεο) εχουν n>=40, ROI<0, t<=−1. Κριση: Μαιος 2027, οχι νωριτερα.
    # Καλυψη sub-10%: απο 16/9 (πριν, dogs με e_B2<0 δεν καταγραφονταν).
    print()
    print('=== ΖΩΝΕΣ (σκια #5): δηλωμενο edge ανα ζωνη γραμμης (καλυψη sub-10% απο 16/9) ===')
    ZONES = [('ΒΑΘΙΕΣ (ud>=1)', lambda r: r['ud'] >= 1.0), ('ΜΕΣΑΙΕΣ (ud<1)', lambda r: r['ud'] < 1.0)]
    THR_A = [0.06, 0.08, 0.10, 0.12, 0.14]
    for zlbl, zf in ZONES:
        print(f'  -- {zlbl} --')
        for thr in THR_A:
            b = [s['pnl'] for s in sysrows
                 if zf(s['r']) and s['r']['e_A'] >= thr and picks.OMIN <= o_dog(s['r']) <= picks.OMAX]
            tag = ' <- live' if abs(thr - picks.EDGE) < 1e-9 else ''
            print(f'     @{thr*100:2.0f}%: {cell(b)}{tag}')
        # τα ΕΞΤΡΑ του κατεβασματος και τα ΚΟΜΜΕΝΑ του ανεβασματος (delta vs live @10)
        ex = [s['pnl'] for s in sysrows
              if zf(s['r']) and 0.06 <= s['r']['e_A'] < picks.EDGE
              and picks.OMIN <= o_dog(s['r']) <= picks.OMAX]
        ct = [s['pnl'] for s in sysrows
              if zf(s['r']) and picks.EDGE <= s['r']['e_A'] < 0.14
              and picks.OMIN <= o_dog(s['r']) <= picks.OMAX]
        print(f'     ΕΞΤΡΑ 6-10% (κατεβασμα): {cell(ex)}')
        print(f'     ΚΟΜΜΕΝΑ 10-14% (ανεβασμα): {cell(ct)}')

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
