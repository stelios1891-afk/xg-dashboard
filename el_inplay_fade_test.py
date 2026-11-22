# -*- coding: utf-8 -*-
"""el_inplay_fade_test.py — LIVE ΑΝΤΙΣΤΡΟΦΗ στα ΣΥΝΟΛΑ Ευρωλιγκας (1/10/2026, ιδεα Στελιου: «παιξαμε over 161.5, πριν το ματς πηγε 159.5·
αν στο live μπουν ποντοι και η γραμμη παει 165.5, παιρνουμε under — γιατι η κινηση πριν το ματς ηταν προς το under»).
Δεδομενα: Nowgoal in-play (flag 3: γραμμη, over/under, σκορ γηπ/φιλ) — ΜΟΝΟ 2025-26 (~400 ματς) · Crown (cid 3) & Bet365 (cid 8).
Pre-match: ανοιγμα→κλεισιμο της ιδιας εταιρειας (flag 2). Τελικο σκορ: sched (με παρατασεις, οπως και οι live γραμμες).
ΣΚΑΝΔΑΛΗ: πρωτη live τιμη με (live γραμμη − γραμμη κλεισιματος) ≥ K (K = 3/5/8) ενω το σκορ ειναι ακομα ≤ S (50 ≈ 1η περιοδος, 90 ≈ ημιχρονο)
  → UNDER σε αυτη τη γραμμη/τιμη. Καθρεφτης: live γραμμη ≤ κλεισιμο − K → OVER.
ΟΜΑΔΕΣ ανα pre-match κινηση (κλεισιμο − ανοιγμα): ΚΑΤΩ ≤ −1.5 · ιδια · ΠΑΝΩ ≥ +1.5. Ιδεα = UNDER μετα απο ΚΑΤΩ (& OVER μετα απο ΠΑΝΩ).
Επισης: μεροληψια live γραμμης (τελικο − live γραμμη) στη σκανδαλη.
Εξοδος: el_inplay_fade_test_out.txt"""
import json, sys
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))
S = {g['ngid']: g for g in json.load(open('nowgoal_el/sched_25-26.json', encoding='utf-8')) if g.get('hs') is not None}
REC = {}
for ln in open('nowgoal_el/odds.jsonl', encoding='utf-8'):
    r = json.loads(ln)
    if r['ot'] == 6 and r.get('t') == 23 and r['ngid'] in S and r['cid'] in (3, 8): REC[(r['ngid'], r['cid'])] = r['rows']
def games(cid):
    G = []
    for (ng, c), rows in REC.items():
        if c != cid: continue
        rows = sorted(rows, key=lambda x: x[0])
        pre = [x for x in rows if x[4] == 2 and x[1] and x[2] and x[3]]
        ip = [x for x in rows if x[4] == 3 and x[1] and x[2] and x[3] and x[5] is not None]
        if len(pre) < 2 or len(ip) < 5: continue
        g = S[ng]; G.append(dict(ng=ng, open=pre[0][1], close=pre[-1][1], ip=ip, fin=g['hs'] + g['as_']))
    return G
def run(G, K, Smax, side):
    res = []
    for g in G:
        for x in g['ip']:
            sc = x[5] + x[6]
            if sc > Smax: break
            d = x[1] - g['close']
            if (side == 'under' and d >= K) or (side == 'over' and d <= -K):
                od = 1 + (x[3] if side == 'under' else x[2]); v = (g['fin'] - x[1]) * (1 if side == 'over' else -1)
                res.append(dict(mv=g['close'] - g['open'], pnl=(od - 1) if v > 0 else (0 if v == 0 else -1), bias=g['fin'] - x[1], od=od, sc=sc))
                break
    return res
def cell(L):
    if not L: return '—'
    return f"{np.mean([r['pnl'] for r in L])*100:+6.1f}% ({len(L):3d}, τελ−live {np.mean([r['bias'] for r in L]):+5.1f}π, απ {np.mean([r['od'] for r in L]):.2f})"
for cid, nm in ((3, 'CROWN'), (8, 'BET365')):
    G = games(cid)
    mv = np.array([g['close'] - g['open'] for g in G])
    P(''); P(f'=== {nm}: {len(G)} ματς 2025-26 με pre-match & live · pre-match κινηση: ΚΑΤΩ ≤−1.5 {np.sum(mv <= -1.5)} · ιδια {np.sum(np.abs(mv) < 1.5)} · ΠΑΝΩ ≥+1.5 {np.sum(mv >= 1.5)} ===')
    for Smax, ph in ((50, 'σκορ ≤50 (~1η περιοδος)'), (90, 'σκορ ≤90 (~ημιχρονο)')):
        P(f'  {ph}:')
        for K in (3, 5, 8):
            U = run(G, K, Smax, 'under'); O = run(G, K, Smax, 'over')
            P(f'    live γραμμη ≥ κλεισιμο+{K}: UNDER | pre ΚΑΤΩ {cell([r for r in U if r["mv"] <= -1.5])} | ιδια {cell([r for r in U if abs(r["mv"]) < 1.5])} | pre ΠΑΝΩ {cell([r for r in U if r["mv"] >= 1.5])} | ΟΛΑ {cell(U)}')
            P(f'    live γραμμη ≤ κλεισιμο−{K}: OVER  | pre ΠΑΝΩ {cell([r for r in O if r["mv"] >= 1.5])} | ιδια {cell([r for r in O if abs(r["mv"]) < 1.5])} | pre ΚΑΤΩ {cell([r for r in O if r["mv"] <= -1.5])} | ΟΛΑ {cell(O)}')
            I = [r for r in U if r['mv'] <= -1.5] + [r for r in O if r['mv'] >= 1.5]
            A = [r for r in U if r['mv'] >= 1.5] + [r for r in O if r['mv'] <= -1.5]
            P(f'      → ΙΔΕΑ (live κοντρα στην pre-match κινηση, παιζουμε προς την pre-match): {cell(I)} · αντιθετο: {cell(A)}')
open('el_inplay_fade_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
