# -*- coding: utf-8 -*-
"""ec_round1_picks.py — «ΑΠΟ ΠΕΡΙΕΡΓΕΙΑ» (1/10/2026, Στελιος): τι picks θα εβγαζε το live μοντελο EuroCup (ec1) στην 1η αγωνιστικη.
Προβλεψη = ec_projections.json (walk-forward: μονο οτι ηταν γνωστο ΠΡΙΝ τη μερα του ματς — εγχωρια ως τοτε, προετοιμασια, ειδικοι).
ΠΡΟΣΟΧΗ: οι αποδοσεις νικητη (3η γνωμη) ειναι ΜΕΤΑ την 1η αγωνιστικη → ελαφρα διαρροη· δειχνεται και χωρις αυτες.
Αγορα = Crown (Nowgoal) ανοιγμα / κλεισιμο (Pinnacle δεν καταγραφηκε για την 1η) · picks edge ≥8% χαντικαπ, σ 11.5 (ιδιο με το live).
Γραφει επισης ec_closing_backfill.jsonl (κλεισιμο Crown για τις καρτες του dashboard).
Εξοδος: ec_round1_picks_out.txt"""
import sys, json, math, datetime as dt
import numpy as np
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
from el_picks import cover
N = NormalDist(); SM = 11.5
import os
P = json.load(open(os.environ.get('EC_PROJ_F', 'ec_projections.json'), encoding='utf-8'))
G = [g for g in P['games'] if g['round'] == 1 and g['played']]
SCH = [x for x in json.load(open('nowgoal_ec/sched_26-27.json', encoding='utf-8')) if x['hs'] is not None]
ROWS = {}
for ln in open('nowgoal_ec/odds.jsonl', encoding='utf-8'):
    r = json.loads(ln)
    if r['sea'] == '26-27': ROWS[(r['ngid'], r['t'], r['cid'])] = r['rows']
PRIOR = json.load(open('ec_prior.json', encoding='utf-8'))
def mk(ngid, t, cid, tip, sw):
    rows = sorted([x for x in ROWS.get((ngid, t, cid), []) if x[4] == 2 and x[1] is not None and x[2] and x[3] and x[0] + 8 * 3600 <= tip + 600], key=lambda x: x[0])
    if not rows: return None
    res = {}
    for nm, x in (('o', rows[0]), ('c', rows[-1])):
        o1, o2 = 1 + x[2], 1 + x[3]
        if t == 21:
            L = -x[1]
            res[nm] = (-L, o2, o1) if sw else (L, o1, o2)       # γραμμη ΓΗΠΕΔΟΥΧΟΥ μας (−2.5 = δινει 2.5)
        else:
            res[nm] = (x[1], o1, o2)
        res[nm + '_t'] = dt.datetime.fromtimestamp(x[0] + 8 * 3600, dt.timezone.utc).isoformat()[:16]
    return res
out = []
P_ = lambda s='': (out.append(s), print(s))
back = []
tot = {'o': [], 'c': []}
P_('=== EuroCup 1η αγωνιστικη: μοντελο ec1 (πριν το ματς) vs Crown — picks χαντικαπ edge ≥8% ===')
P_('  ματς | σκορ | μοντελο (γραμμη γηπ.) | Crown ανοιγμα → κλεισιμο | pick ανοιγμα | pick κλεισιμο')
for g in sorted(G, key=lambda g: g['utc']):
    tip = dt.datetime.fromisoformat(g['utc'].replace('Z', '+00:00')).timestamp()
    hit, sw = None, False
    for x in SCH:
        bj = dt.datetime.fromisoformat(x['bj']).replace(tzinfo=dt.timezone.utc) - dt.timedelta(hours=8)
        if abs(bj.timestamp() - tip) > 26 * 3600: continue
        if (x['hs'], x['as_']) == (g['hs'], g['as_']): hit = x; break
        if (x['as_'], x['hs']) == (g['hs'], g['as_']): hit, sw = x, True; break
    if not hit:
        P_(f"  {g['home'][:20]} - {g['away'][:20]}: δεν βρεθηκε στη Nowgoal"); continue
    sp = mk(hit['ngid'], 21, 3, tip, sw); tt = mk(hit['ngid'], 23, 3, tip, sw)
    m = float(g['margin']); act = g['hs'] - g['as_']
    cells = []
    for w in ('o', 'c'):
        if not sp:
            cells.append('—'); continue
        L, oh, oa = sp[w]
        pw, pp = cover(m, L, SM); pl = 1 - pw - pp
        best = None
        for side, p_, od, hc in ((1, pw, oh, L), (-1, pl, oa, -L)):
            e = p_ * od + pp - 1
            if e >= 0.08 and (best is None or e > best[1]): best = (side, e, od, hc)
        if best:
            side, e, od, hc = best
            v = (act + L) * side
            pnl = (od - 1) if v > 0 else (0 if v == 0 else -1)
            tot[w].append(pnl)
            team = g['home'] if side == 1 else g['away']
            cells.append(f"{team.split()[0]} {'+' if hc >= 0 else ''}{hc:g} @{od:.2f} edge {e*100:.0f}% → {'✅' if pnl > 0 else ('➖' if pnl == 0 else '❌')} {pnl:+.2f}")
        else:
            cells.append('—')
    if sp:
        back.append(dict(t=sp['c_t'], code=g['code'], commence=g['utc'][:16].replace('Z', '') + ':00+00:00', line=sp['c'][0], oh=sp['c'][1], oa=sp['c'][2],
                         **(dict(tl=tt['c'][0], to=tt['c'][1], tu=tt['c'][2]) if tt else {}), src='crown'))
    P_(f"  {g['home'][:22]:22s} - {g['away'][:22]:22s} | {g['hs']}-{g['as_']} | {-m:+5.1f} | "
       + (f"{sp['o'][0]:+5.1f} → {sp['c'][0]:+5.1f}" if sp else '—') + f" | {cells[0]} | {cells[1]}")
P_('')
for w, lab in (('o', 'ΑΝΟΙΓΜΑ'), ('c', 'ΚΛΕΙΣΙΜΟ')):
    a = np.array(tot[w])
    P_(f'  {lab}: {len(a)} picks · {sum(a > 0)}-{sum(a < 0)}' + (f'-{sum(a == 0)}' if (a == 0).any() else '') + f' · {a.sum():+.2f} μονάδες' + (f' · ROI {a.mean()*100:+.1f}%' if len(a) else ''))
with open('ec_closing_backfill.jsonl' if 'EC_PROJ_F' not in os.environ else '_unused_bf.jsonl', 'w', encoding='utf-8') as fh:
    for r in back: fh.write(json.dumps(r, ensure_ascii=False) + '\n')
P_(f'\nec_closing_backfill.jsonl: {len(back)} ματς (κλεισιμο Crown για τις καρτες)')
open('ec_round1_picks_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
