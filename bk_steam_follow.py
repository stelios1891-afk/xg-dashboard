# -*- coding: utf-8 -*-
"""bk_steam_follow.py — ΑΚΟΛΟΥΘΩΝΤΑΣ ΤΟ «STEAM» ΣΤΟ ΜΠΑΣΚΕΤ (17/10/2026, Στελιος: «οπως ο κανονας Γ στην Ευρωλιγκα, οπου κοντρα = εξυπνα
χρηματα — πως θα λαμβανουμε alerts οταν μπαινουν χρηματα καπου και να ακολουθουμε; το steamwatch το κανει για ποδοσφαιρο… ερευνησε το στο μπασκετ»).
ΧΩΡΙΣ ΜΟΝΤΕΛΟ — μονο αγορα. Euroleague / EuroCup / BCL, σεζον 20-21 … 26-27 (οσο υπαρχει), Nowgoal, πληρες ματς (ot 6), pre-match γραμμες (flag 2).
Γραμμη χαντικαπ = αναμενομενη διαφορα γηπεδουχου (+ = φαβορι γηπεδουχος· επιβεβαιωθηκε: μ(διαφορα − γραμμη) = +0.04). o1 = γηπεδουχος / over.
ΔΙΚΑΙΗ ΤΙΜΗ (σε ποντους): F = γραμμη + σ·Φ⁻¹(p1), p1 = (1/d1)/(1/d1+1/d2), d = HK+1 · σ χαντικαπ 11.5 (BCL 12), συνολο 16.7 (BCL 17.3).
ΠΡΟ-ΔΗΛΩΜΕΝΟΣ ΟΡΙΣΜΟΣ (γραφτηκε ΠΡΙΝ την εκτελεση):
  ALERT = η ΠΡΩΤΗ στιγμη που η δικαιη τιμη κινηθηκε ≥X ποντους μεσα σε παραθυρο W (τρεχουσα τιμη − τιμη που ισχυε W πριν).
  ΚΥΡΙΟ: X = 1.5, W = 60′ · επιπλεον X ∈ {1, 2, 3}, W ∈ {15′, 3ω}. Ενα alert ανα ματς / αγορα / ρυθμιση. Χρειαζεται τιμη ≥W πριν (οχι η 1η ωρα ανοιγματος).
  ΑΚΟΛΟΥΘΩ = πονταρω την πλευρα προς την οποια ηρθαν τα χρηματα, στην τιμη ΑΜΕΣΩΣ μετα την κινηση (στο alert) και με καθυστερηση +5′ / +15′ / +60′,
  και, για συγκριση, στο κλεισιμο. CLV = (δικαιη κλεισιματος − δικαιη στην τιμη μας) προς την πλευρα μας. ΚΟΝΤΡΑ = η αλλη πλευρα στο alert.
  ΚΡΙΤΗΡΙΟ «ΔΟΥΛΕΥΕΙ»: ROI στο +5′ > 0, θετικο σε ≥ 2/3 των σεζον, CLV > 0, ιδια φορα στο 2ο βιβλιο (Bet365 με δικα του alerts).
Crown = κυριο βιβλιο (cid 3) · Bet365 (cid 8) = αναπαραγωγη. Εξοδος: bk_steam_follow_out.txt"""
import sys, json, glob, collections, math
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
IQ = NormalDist().inv_cdf
COMPS = (('EL', 'Euroleague', 'nowgoal_el'), ('EC', 'EuroCup', 'nowgoal_ec'), ('BCL', 'BCL', 'nowgoal_bcl'))
SIG = {('EL', 21): 11.5, ('EL', 23): 16.7, ('EC', 21): 11.5, ('EC', 23): 16.7, ('BCL', 21): 12.0, ('BCL', 23): 17.3}
BOOK = {3: 'Crown', 8: 'Bet365'}
SHIFT = 8 * 3600
S, SERIES = {}, {}
for c, _, d in COMPS:
    for f in glob.glob(f'{d}/sched_*.json'):
        for g in json.load(open(f, encoding='utf-8')):
            if g.get('hs') is None: continue
            g['tip'] = (pd.Timestamp(g['bj']) - pd.Timedelta(hours=8)).tz_localize('UTC').timestamp(); S[(c, g['ngid'])] = g
    for l in open(f'{d}/odds.jsonl', encoding='utf-8'):
        r = json.loads(l)
        t = r.get('t', 21) or 21
        if r['ot'] != 6 or t not in (21, 23) or r['cid'] not in BOOK: continue
        g = S.get((c, r['ngid']))
        if not g: continue
        sg = SIG[(c, t)]; rows = []
        for q in r['rows']:
            if len(q) < 5: continue
            q = [q[0] + SHIFT] + list(q[1:])                 # οι χρονοι του Nowgoal μπασκετ ειναι 8ω πισω (ιδιο με bk_move_rules_test)
            if q[4] != 2 or q[0] >= g['tip'] or q[1] == 0 or q[2] <= 0 or q[3] <= 0: continue
            d1, d2 = q[2] + 1, q[3] + 1; p1 = (1 / d1) / (1 / d1 + 1 / d2)
            rows.append((q[0], q[1], d1, d2, q[1] + sg * IQ(min(max(p1, 1e-4), 1 - 1e-4))))
        rows.sort()
        if len(rows) >= 2: SERIES[(c, r['ngid'], t, r['cid'])] = (r['sea'], rows)
print(f'σειρες τιμων: {len(SERIES)} · ματς με σκορ: {len(S)}')
# ελεγχος φορας o1 (γηπεδουχος/over): η διορθωση με τις αποδοσεις πρεπει να ΜΕΙΩΝΕΙ το σφαλμα στο κλεισιμο
for t, nm in ((21, 'χαντικαπ'), (23, 'συνολο')):
    eL, eF = [], []
    for (c, ng, tt, cid), (sea, rows) in SERIES.items():
        if tt != t or cid != 3: continue
        g = S[(c, ng)]; y = g['hs'] - g['as_'] if t == 21 else g['hs'] + g['as_']
        eL.append((y - rows[-1][1]) ** 2); eF.append((y - rows[-1][4]) ** 2)
    print(f'  ελεγχος φορας {nm}: MSE γραμμη {np.mean(eL):.2f} · MSE δικαιη {np.mean(eF):.2f} (πρεπει ≤)')

def at(rows, ts):
    """τιμη που ισχυει τη στιγμη ts (τελευταια αλλαγη ≤ ts)"""
    lo, hi = 0, len(rows)
    while lo < hi:
        m = (lo + hi) // 2
        if rows[m][0] <= ts: lo = m + 1
        else: hi = m
    return rows[lo - 1] if lo else None

def settle(y, L, d, side):
    v = side * (y - L)
    return 0.0 if v == 0 else (d - 1 if v > 0 else -1.0)

def alerts(X, W, cid):
    out = []
    for (c, ng, t, cb), (sea, rows) in SERIES.items():
        if cb != cid: continue
        g = S[(c, ng)]; y = g['hs'] - g['as_'] if t == 21 else g['hs'] + g['as_']
        t0 = rows[0][0]
        for i in range(1, len(rows)):
            ts = rows[i][0]
            if ts - W < t0: continue
            b = at(rows, ts - W)
            dF = rows[i][4] - b[4]
            if abs(dF) < X: continue
            sd = 1 if dF > 0 else -1
            rec = dict(comp=c, sea=sea, t=t, side=sd, dF=dF, hrs=(g['tip'] - ts) / 3600, age=(ts - t0) / 3600, ng=ng)
            cl = rows[-1]
            for lab, dl in (('alert', 0), ('+5′', 300), ('+15′', 900), ('+60′', 3600), ('κλεισιμο', None)):
                q = cl if dl is None else (at(rows, ts + dl) if ts + dl < g['tip'] else None)
                if q is None: rec['pnl_' + lab] = np.nan; rec['clv_' + lab] = np.nan; continue
                rec['pnl_' + lab] = settle(y, q[1], q[2] if sd == 1 else q[3], sd)
                rec['clv_' + lab] = sd * (cl[4] - q[4])
            q = rows[i]; rec['pnl_κοντρα'] = settle(y, q[1], q[3] if sd == 1 else q[2], -sd)
            rec['mv_after'] = sd * (cl[4] - rows[i][4])
            out.append(rec); break
    return pd.DataFrame(out)

def cell(y, col='+5′'):
    v = y['pnl_' + col].dropna()
    if len(v) < 8: return f'{"—":>7s} ({len(v):3d})'
    return f'{100 * v.mean():+6.1f}% ({len(v):3d})'

def seas(y, col='+5′'):
    s = y.groupby('sea')['pnl_' + col].mean().dropna()
    s = s[y.groupby('sea').size().reindex(s.index) >= 5]
    return f'{int((s > 0).sum())}/{len(s)}'

def tstat(v):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    return v.mean() / (v.std() / math.sqrt(len(v))) if len(v) > 5 and v.std() > 0 else np.nan

HDR = (f'   {"":28s} │ {"ROI alert":>13s} {"+5′":>13s} {"+15′":>13s} {"+60′":>13s} {"κλεισιμο":>13s} │ {"θετ.σεζ":>7s} {"t(+5′)":>6s} │ '
       f'{"CLV +5′":>7s} {"κινηση μετα":>11s} │ {"ΚΟΝΤΡΑ":>13s}')
def row(lab, y):
    if not len(y): print(f'   {lab:28s} │ —'); return
    print(f'   {lab:28s} │ {cell(y, "alert"):>13s} {cell(y, "+5′"):>13s} {cell(y, "+15′"):>13s} {cell(y, "+60′"):>13s} {cell(y, "κλεισιμο"):>13s} │ '
          f'{seas(y):>7s} {tstat(y["pnl_+5′"]):6.2f} │ {y["clv_+5′"].mean():+7.2f} {y.mv_after.mean():+11.2f} │ {cell(y, "κοντρα"):>13s}')

def baseline(cid):
    """ΒΑΣΗ: τυχαιο πονταρισμα της πλευρας γηπεδουχου/over στο κλεισιμο → ROI ≈ −γκανιοτα"""
    v = []
    for (c, ng, t, cb), (sea, rows) in SERIES.items():
        if cb != cid: continue
        g = S[(c, ng)]; y = g['hs'] - g['as_'] if t == 21 else g['hs'] + g['as_']; q = rows[-1]
        v.append((settle(y, q[1], q[2], 1) + settle(y, q[1], q[3], -1)) / 2)
    return 100 * np.mean(v)

for cid in (3, 8):
    print(f'\n{"#" * 150}\nΒΙΒΛΙΟ {BOOK[cid]} · βαση (τυχαια πλευρα στο κλεισιμο) ROI {baseline(cid):+.1f}%  — κελι = ROI (πληθος bets)')
    A = alerts(1.5, 3600, cid)
    for t, nm in ((21, 'ΧΑΝΤΙΚΑΠ'), (23, 'ΣΥΝΟΛΑ')):
        y0 = A[A.t == t]
        print(f'\n== {nm} · ΚΥΡΙΟ: κινηση ≥1.5 ποντων μεσα σε 60′ ==\n{HDR}')
        row('ΟΛΑ', y0)
        for c, cn, _ in COMPS: row(f'  {cn}', y0[y0.comp == c])
        print('   — ποτε εγινε η κινηση (ωρες πριν το τζαμπολ) —')
        for lab, lo, hi in (('≥24ω', 24, 1e9), ('6-24ω', 6, 24), ('2-6ω', 2, 6), ('<2ω', 0, 2)): row(f'  {lab}', y0[(y0.hrs >= lo) & (y0.hrs < hi)])
        print('   — μεγεθος κινησης —')
        for lab, lo, hi in (('1.5-2', 1.5, 2), ('2-3', 2, 3), ('≥3', 3, 1e9)): row(f'  {lab}', y0[(y0.dF.abs() >= lo) & (y0.dF.abs() < hi)])
        if t == 21:
            print('   — προς ποια πλευρα —')
            row('  προς γηπεδουχο', y0[y0.side == 1]); row('  προς φιλοξενουμενο', y0[y0.side == -1])
        else:
            print('   — προς ποια πλευρα —')
            row('  προς OVER', y0[y0.side == 1]); row('  προς UNDER', y0[y0.side == -1])
        print('   — ανα σεζον (+5′) —')
        for s in sorted(y0.sea.unique()): row(f'  {s}', y0[y0.sea == s])
    print(f'\n== ΑΛΛΕΣ ΡΥΘΜΙΣΕΙΣ ({BOOK[cid]}) — ολες οι διοργανωσεις ==\n{HDR}')
    for X in (1.0, 1.5, 2.0, 3.0):
        for W, wl in ((900, "15′"), (3600, "60′"), (10800, "3ω")):
            B = alerts(X, W, cid)
            for t, nm in ((21, 'χαντ'), (23, 'συν')): row(f'{nm} ≥{X:g} σε {wl}', B[B.t == t])
    A.to_pickle(f'bk_steam_alerts_{BOOK[cid]}.pkl')
