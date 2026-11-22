# -*- coding: utf-8 -*-
"""ucl_md12_fav_missed.py — 19/10/2026 (Στελιος «παμε φαβορι στο 4% — υπηρχε φαβορι τις 2 πρωτες αγωνιστικες που δεν παιξαμε;»).
Απο το euro_shadow.jsonl (καθε αλλαγη τιμης/μοντελου του scanner): UCL αγων. 1-2, FotMob και οι 2, φαβορι (≤−0.5), 1.70-2.10,
σωστα τεταρτα (e_clean), ΣΗΜΕΡΙΝΟΣ κανονας: πρωτη εμφανιση με edge ≥4% μεσα σε 168ω, οχι <2ω. Ποια ΔΕΝ εφτασαν ποτε 10% (= χαμενα)."""
import json, datetime, sys
sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0, '.')
import picks
P = {m['mid']: m for m in json.load(open('euro_projections.json', encoding='utf-8'))['matches']}
R = [json.loads(l) for l in open('euro_shadow.jsonl', encoding='utf-8')]
R = [r for r in R if r['comp'] == 'ChampionsLeague' and str(r.get('rnd')) in ('1', '2') and r.get('src_h') == 'FotMob' and r.get('src_a') == 'FotMob']
def hb(r):
    ko = datetime.datetime.fromisoformat(r['ko'].replace('Z', '+00:00')); t = datetime.datetime.fromisoformat(r['t'] + '+00:00')
    return (ko - t).total_seconds() / 3600
led = {}
for l in open('euro_picks_ledger.jsonl', encoding='utf-8'):
    q = json.loads(l)
    if q.get('mkt') == 'AH': led[(q['mid'], q['side'])] = q
out = []
for mid in sorted({r['mid'] for r in R}, key=lambda m: min(x['ko'] for x in R if x['mid'] == m)):
    rs = sorted([r for r in R if r['mid'] == mid], key=lambda r: r['t'])
    for side, tag in ((1, 'h'), (-1, 'a')):
        first = None; mx = -9
        for r in rs:
            h = hb(r); ln = r['line'] if side == 1 else -r['line']; o = r['oh'] if side == 1 else r['oa']
            if h > 168 or h < 0 or ln > -0.5 or not (1.70 <= o <= 2.10): continue
            e = r[f'e_clean_{tag}']; mx = max(mx, e)
            if e >= 0.04 and first is None and h >= 2: first = (h, ln, o, e)
        if not first: continue
        m = P.get(mid, {}); sc = m.get('score', '')
        gh, ga = (int(s) for s in sc.split(' - ')) if ' - ' in sc else (None, None)
        h, ln, o, e = first
        pnl = picks.settle((gh - ga) if side == 1 else (ga - gh), 1, ln, o) if gh is not None else None
        team = rs[0]['home'] if side == 1 else rs[0]['away']
        L = led.get((mid, side))
        out.append((rs[0]['rnd'], rs[0]['home'], rs[0]['away'], team, ln, o, e, h, mx, sc, pnl, L))
print(f'{"αγ":2s} {"ματς":42s} {"ομαδα":22s} {"γραμμη":>6s} {"τιμη":>5s} {"edge 1ης":>8s} {"ωρες":>5s} {"max edge":>8s} {"σκορ":>6s} {"αποτ.":>6s}  στο ledger;')
for rnd, hm, aw, tm, ln, o, e, h, mx, sc, pnl, L in out:
    ls = (f"ΝΑΙ ({L['line']:+} @{L['odds']} edge {100 * L['edge']:.0f}%, pnl {L.get('pnl')})" if L else 'ΟΧΙ')
    print(f'{rnd:2s} {hm + " - " + aw:42s} {tm:22s} {ln:+6.2f} {o:5.2f} {100 * e:7.1f}% {h:5.0f} {100 * mx:7.1f}% {sc:>6s} {pnl if pnl is not None else float("nan"):+6.2f}  {ls}')
miss = [z for z in out if not z[11]]
print(f'\nΔΕΝ μπηκαν στο ledger (χαμενα με το παλιο 10%): {len(miss)} · αποτελεσμα στην τιμη 1ης εμφανισης: {sum(z[10] for z in miss if z[10] is not None):+.2f} μοναδες')
