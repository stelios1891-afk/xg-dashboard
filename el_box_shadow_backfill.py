# -*- coding: utf-8 -*-
"""el_box_shadow_backfill.py — ΣΚΙΑ «δικο box» χαντικαπ: ΑΝΑΔΡΟΜΙΚΑ οι φετινες αγωνιστικες που εχουν παιχτει (23/10/2026, Στελιος).
ΜΟΝΟ ΠΕΡΙΓΡΑΦΙΚΟ (η κριση ειναι στις αγωνιστικες 11-38): ~70 ματς, ολα στη ζωνη 1-10 οπου στα τεστ το box ηταν ΧΕΙΡΟΤΕΡΟ απο το PIR.
Για καθε παιγμενο ματς E2026: γραμμη μοντελου ΠΡΙΝ το ματς (el_shadow_lines.json, «live» = παγωμενη) · αποντες = τακτικοι (≥3/10 φετινα,
≥10′) που ΔΕΝ επαιξαν (box score — πληρης γνωση, η σελιδα lineups της ωρας εκεινης δεν υπαρχει αναδρομικα) · κοστος live (PIR) και
σκιας (el_box_shadow) με το el_absence.team_cost · τιμες Pinnacle: η ΠΡΩΤΗ που ειδε ο scanner (el_odds_hist.jsonl) και η τελευταια πριν
το τζαμπολ (κλεισιμο) · picks ≥8% · CLV = αποδοση μας / αποδοση κλεισιματος (ιδια πλευρα & γραμμη).
Εξοδος: el_box_shadow_backfill_out.txt"""
import os, sys, json, math, collections, datetime as dt
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)
import el_absence as E, el_picks as EP
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
B = json.load(open('el_box.json', encoding='utf-8')); SH = json.load(open('el_shadow_lines.json', encoding='utf-8'))
try: prev = json.load(open('el_player_min_prev.json', encoding='utf-8'))['players']
except Exception: prev = {}
H = collections.defaultdict(list)
for ln in open('el_odds_hist.jsonl', encoding='utf-8'):
    try: r = json.loads(ln); H[int(r['code'])].append(r)
    except Exception: pass
for v in H.values(): v.sort(key=lambda r: r['t'])
SEASON, SM = 'E2026', 11.5
rows = []
for k, g in sorted(B.items(), key=lambda kv: kv[1].get('utc', '')):
    if not k.startswith(SEASON + '_') or 'ph' not in g or g.get('hs') is None: continue
    sh = SH.get(str(g['code']))
    if not sh or sh.get('live') is None: continue
    ko = dt.datetime.fromisoformat(g['utc'].replace('Z', '+00:00'))
    odds = [r for r in H.get(int(g['code']), []) if r.get('line') is not None and dt.datetime.fromisoformat(r['t']).replace(tzinfo=dt.timezone.utc) < ko]
    if not odds: continue
    res = {}
    for side, tc, lst in (('h', g['hcode'], g['ph']), ('a', g['acode'], g['pa'])):
        tg = [x for x in E._team_games(B, SEASON, tc) if x[0] < g['utc']]
        roster = {}
        for _, _, nm in tg: roster.update(nm)
        played_today = {p[0] for p in lst if (p[2] or 0) > 0}
        last10 = tg[-10:]
        reg = [pid for pid in roster if sum(1 for _, mn, _ in last10 if mn.get(pid, 0) > 0) >= 3 and pid not in played_today]
        shd = {'box': 0.0, 'ok': True}
        c, det, _, _ = E.team_cost(B, SEASON, tc, [roster[p] for p in reg], g['utc'], prev, None, (), shadow=shd)
        res[side] = (c, shd['box'] if shd['ok'] else None, det)
    if res['h'][1] is None or res['a'][1] is None: continue
    adj, adjb = res['a'][0] - res['h'][0], res['a'][1] - res['h'][1]
    rows.append(dict(code=g['code'], rnd=g.get('rnd'), home=g['hcode'], away=g['acode'], utc=g['utc'], m=float(sh['live']), adj=adj, adjb=adjb,
                     act=g['hs'] - g['as_'], op=odds[0], cl=odds[-1], det=res['h'][2] + res['a'][2]))
P(f'φετινα παιγμενα ματς με γραμμη μοντελου & τιμες Pinnacle: {len(rows)} (αγωνιστικες {min(r["rnd"] for r in rows)}-{max(r["rnd"] for r in rows)})')
P(f'ματς με τουλαχιστον μια απουσια που μετραει: {sum(1 for r in rows if abs(r["adj"]) > 1e-9 or abs(r["adjb"]) > 1e-9)}')
Y = np.array([r['act'] for r in rows], float)
for nm, key in (('χωρις απουσιες', None), ('LIVE (PIR)', 'adj'), ('ΣΚΙΑ (δικο box)', 'adjb')):
    pred = np.array([r['m'] + (r[key] if key else 0.0) for r in rows])
    P(f'  ακριβεια {nm:18s}: RMSE διαφορας {math.sqrt(np.mean((Y - pred) ** 2)):.3f} ποντοι')
def picks(key):
    L = []
    for r in rows:
        o = r['op']; Lh, oh, oa = float(o['line']), float(o['oh']), float(o['oa']); m = r['m'] + (r[key] if key else 0.0)
        pw, pp = EP.cover(m, Lh, SM); pl = 1 - pw - pp
        for side, p_, od, hc in ((1, pw, oh, Lh), (-1, pl, oa, -Lh)):
            e = p_ * od + pp - 1
            if e < EP.HC_MIN: continue
            x = (r['act'] + Lh) * side
            u = (od - 1) if x > 0 else (0 if x == 0 else -1)
            c = r['cl']; clv = None
            if float(c['line']) == Lh: clv = od / float(c['oh'] if side == 1 else c['oa']) - 1
            L.append(dict(code=r['code'], side=side, u=u, clv=clv, e=e))
    return L
P(''); P('## PICKS ≥8% στην ΠΡΩΤΗ τιμη Pinnacle που ειδε ο scanner (1 μοναδα/pick) · CLV = αποδοση μας / κλεισιματος − 1 (ιδια γραμμη)')
PK = {}
for nm, key in (('χωρις απουσιες', None), ('LIVE (PIR)', 'adj'), ('ΣΚΙΑ (δικο box)', 'adjb')):
    L = picks(key); PK[nm] = L; cl = [x['clv'] for x in L if x['clv'] is not None]
    P(f'  {nm:18s}: picks {len(L):3d} · μοναδες {sum(x["u"] for x in L):+6.2f} · ROI {np.mean([x["u"] for x in L]) * 100 if L else 0:+6.1f}% · '
      f'CLV {np.mean(cl) * 100 if cl else float("nan"):+5.1f}% ({len(cl)} με ιδια γραμμη στο κλεισιμο)')
a = {(x['code'], x['side']) for x in PK['LIVE (PIR)']}; b = {(x['code'], x['side']) for x in PK['ΣΚΙΑ (δικο box)']}
P(f'  κοινα picks {len(a & b)} · μονο live {len(a - b)} · μονο σκια {len(b - a)}')
P(''); P('## 5 ματς με τη μεγαλυτερη διαφορα live ↔ σκια (διορθωση απουσιων υπερ γηπεδουχου, ποντοι)')
for r in sorted(rows, key=lambda r: -abs(r['adjb'] - r['adj']))[:5]:
    P(f'  αγων {r["rnd"]} {r["home"]}-{r["away"]} {r["utc"][:10]} · live {r["adj"]:+.2f} · σκια {r["adjb"]:+.2f} · μοντελο {r["m"]:+.1f} → πραγματικο {r["act"]:+.0f}'
      f' · αποντες: {"; ".join(d for d in r["det"] if "→" in d)[:200]}')
open('el_box_shadow_backfill_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
