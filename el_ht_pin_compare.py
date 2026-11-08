# -*- coding: utf-8 -*-
"""el_ht_pin_compare.py — φετινα bets ημιχρονου (Crown) vs PINNACLE στο ιδιο ημιχρονο (toa_el_ht.jsonl). 29/10/2026.
Για καθε bet: γραμμη/τιμες Pinnacle, διαφορα απο Crown, edge της ΔΙΚΗΣ μας γραμμης στην Pinnacle (ιδιο σ 10.8), εκκαθαριση στην Pinnacle.
Εξοδος: el_ht_pin_compare_out.txt"""
import sys, json
import numpy as np
from statistics import NormalDist
Phi = NormalDist().cdf; SIG = 10.8
sys.stdout.reconfigure(encoding='utf-8')
S = {s['ng']: s for s in json.load(open('el_ht_pin_slots.json', encoding='utf-8'))}
import re, unicodedata
def tok(x):
    x = unicodedata.normalize('NFD', str(x)); x = ''.join(c for c in x if unicodedata.category(c) != 'Mn').lower()
    return set(w for w in re.findall(r'[a-z]{3,}', x) if w not in ('basketball', 'basket', 'club', 'the', 'sport', 'bc', 'kk', 'fc'))
NGN = {g['ngid']: (g['home'], g['away']) for g in json.load(open('nowgoal_el/sched_26-27.json', encoding='utf-8'))}
T = {}
for ln in open('toa_el_ht2.jsonl', encoding='utf-8'):                       # v2: ολα τα ματς της ωρας → ταιριασμα ονοματων (v1 επαιρνε το πρωτο = λαθος)
    r = json.loads(ln); h, a = NGN[r['ng']]; best = (0, None)
    for g in r.get('games') or []:
        sc = len(tok(h) & tok(g['home_team'])) + len(tok(a) & tok(g['away_team']))
        sc2 = len(tok(h) & tok(g['away_team'])) + len(tok(a) & tok(g['home_team']))
        if max(sc, sc2) > best[0]: best = (max(sc, sc2), g)
    r['game'] = best[1]; r['names'] = (h, a, best[1] and best[1]['home_team'], best[1] and best[1]['away_team']); T[r['ng']] = r
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def settle(tot, L, side, o):
    if tot == L: return 0.0
    return (o - 1) if ((tot > L) if side == 'O' else (tot < L)) else -1.0
rows = []
for ng, s in S.items():
    r = T.get(ng); pin = None
    if r and r.get('game'):
        for b in r['game'].get('bookmakers', []):
            if b['key'] != 'pinnacle': continue
            for m in b.get('markets', []):
                if m['key'] != 'totals': continue
                oc = {o['name']: o for o in m['outcomes']}
                if 'Over' in oc and 'Under' in oc and oc['Over'].get('point') == oc['Under'].get('point'):
                    pin = dict(line=oc['Over']['point'], oo=oc['Over']['price'], ou=oc['Under']['price'], upd=m.get('last_update') or b.get('last_update'))
    rows.append(dict(s=s, pin=pin, snap=(r or {}).get('snap_ts')))
have = [x for x in rows if x['pin']]
P(f'φετινα bets ημιχρονου (Crown, ≥8%): {len(rows)} · με τιμη Pinnacle στο ημιχρονο: {len(have)}')
P('\nματς | ημιχρ. | δικη μας | Crown (γραμμη @over/@under) | Pinnacle | πλευρα | τελικο | Crown μ | Pinnacle: edge δικης μας · μ')
uc, up, upb = [], [], []
for x in sorted(rows, key=lambda x: x['s']['tip']):
    s = x['s']; c = s['crown']; p = x['pin']; side = s['side']
    if p:
        po = Phi((s['ours'] - p['line']) / SIG); e = (po * p['oo'] - 1) if side == 'O' else ((1 - po) * p['ou'] - 1)
        u = settle(s['final'], p['line'], side, p['oo'] if side == 'O' else p['ou'])
        pt = f"{p['line']} @{p['oo']:.2f}/{p['ou']:.2f}"; pe = f'{e * 100:+.0f}% · {u:+.2f}'
        up.append(u); uc.append(s['u_crown'])
        if e >= .08: upb.append(u)
    else:
        pt, pe = '—', '—'
    P(f"{s['home']}–{s['away']} | {s['ht_pts']} | {s['ours']:.1f} | {c['line']} @{c['oo']:.2f}/{c['ou']:.2f} | {pt} | {side} | {s['final']} | {s['u_crown']:+.2f} | {pe}")
if have:
    d = np.array([x['pin']['line'] - x['s']['crown']['line'] for x in have])
    P(f'\nPinnacle − Crown γραμμη (ιδιο ημιχρονο): μεσος {d.mean():+.2f} π. · διαμεσος {np.median(d):+.1f} · ιδια γραμμη {np.mean(d == 0) * 100:.0f}% · Pinnacle ψηλοτερα {np.mean(d > 0) * 100:.0f}% · χαμηλοτερα {np.mean(d < 0) * 100:.0f}%')
    vig = np.mean([1 / x['pin']['oo'] + 1 / x['pin']['ou'] - 1 for x in have]); vc = np.mean([1 / x['s']['crown']['oo'] + 1 / x['s']['crown']['ou'] - 1 for x in have])
    P(f'γκανιοτα live συνολου: Pinnacle {vig * 100:.1f}% · Crown {vc * 100:.1f}%')
    P(f'ιδια bets: στην Crown {len(uc)} bets ROI {np.mean(uc) * 100:+.1f}% ({sum(uc):+.1f}μ) · στην Pinnacle {len(up)} bets ROI {np.mean(up) * 100:+.1f}% ({sum(up):+.1f}μ)')
    P(f'στην Pinnacle ΜΟΝΟ οσα ειχαν και εκει edge ≥8%: {len(upb)} bets ' + (f'ROI {np.mean(upb) * 100:+.1f}% ({sum(upb):+.1f}μ)' if upb else ''))
open('el_ht_pin_compare_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
