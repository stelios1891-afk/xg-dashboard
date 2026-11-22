# -*- coding: utf-8 -*-
"""bk_steam_multi.py — 17/10/2026: STEAM με 4 ΒΙΒΛΙΑ (Crown, Bet365 απο odds.jsonl · SBOBET, William Hill απο odds_extra.jsonl), EL / EC / BCL 2020-26.
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ιδιοι ορισμοι με bk_steam_follow / bk_steam_lag): κινηση = δικαιη τιμη ≥1.5 π. μεσα σε 60′, πρωτη ανα ματς/αγορα/βιβλιο.
 (Α) ΑΚΟΛΟΥΘΩ στο ιδιο βιβλιο (+5′) — για καθε βιβλιο.
 (Β) ΠΙΝΑΚΑΣ «ποιος οδηγει»: alert στο βιβλιο Χ → ποντος στο Υ (που δεν ειχε ακολουθησει ≥½ τη στιγμη του alert), τιμη Υ στο +5′.
 (Γ) ΣΥΝΑΙΝΕΣΗ: 2ο βιβλιο κινειται ≥1.5 προς την ιδια μερια μεσα σε 60′ απο το 1ο → τη στιγμη της επιβεβαιωσης ποντος στα βιβλια που
     ΔΕΝ εχουν ακολουθησει (μεσος ROI ανα ματς). Κριτηριο «δουλευει»: ROI > 0, ≥ 4/6 σεζον, και στις 2 αγορες ή στις 3 διοργανωσεις.
Εξοδος: bk_steam_multi_out.txt"""
import sys, io, contextlib, json, os
import numpy as np, pandas as pd
_src = open('bk_steam_follow.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1).split("for cid in (3, 8):\n    print(f'\\n{\"#\"")[0]
with contextlib.redirect_stdout(io.StringIO()): exec(_src)
sys.stdout.reconfigure(encoding='utf-8')
BOOK.update({31: 'SBOBET', 10: 'William Hill'})
for c, _, d in COMPS:
    fn = f'{d}/odds_extra.jsonl'
    if not os.path.exists(fn): continue
    for l in open(fn, encoding='utf-8'):
        r = json.loads(l); g = S.get((c, r['ngid']))
        if not g: continue
        sg = SIG[(c, r['t'])]; rows = []
        for q in r['rows']:
            if len(q) < 5: continue
            q = [q[0] + SHIFT] + list(q[1:])
            if q[4] != 2 or q[0] >= g['tip'] or not q[1] or not q[2] or q[2] <= 0 or q[3] <= 0: continue
            d1, d2 = q[2] + 1, q[3] + 1; p1 = (1 / d1) / (1 / d1 + 1 / d2)
            rows.append((q[0], q[1], d1, d2, q[1] + sg * IQ(min(max(p1, 1e-4), 1 - 1e-4))))
        rows.sort()
        if len(rows) >= 2: SERIES[(c, r['ngid'], r['t'], r['cid'])] = (r['sea'], rows)
BKS = (3, 8, 31, 10); W = 3600; X = 1.5
cnt = {b: sum(1 for k in SERIES if k[3] == b) for b in BKS}
print('σειρες ανα βιβλιο: ' + ' · '.join(f'{BOOK[b]} {cnt[b]}' for b in BKS))
# πρωτο alert ανα (ματς, αγορα, βιβλιο)
AL = {}
for (c, ng, t, cb), (sea, rows) in SERIES.items():
    t0 = rows[0][0]
    for i in range(1, len(rows)):
        ts = rows[i][0]
        if ts - W < t0: continue
        dF = rows[i][4] - at(rows, ts - W)[4]
        if abs(dF) >= X: AL[(c, ng, t, cb)] = (ts, 1 if dF > 0 else -1, abs(dF), sea); break
def yv(c, ng, t):
    g = S[(c, ng)]; return g['hs'] - g['as_'] if t == 21 else g['hs'] + g['as_']
def bet_at(c, ng, t, b, ts, sd):
    sr = SERIES.get((c, ng, t, b))
    if not sr: return None
    q = at(sr[1], ts)
    return None if q is None or ts >= S[(c, ng)]['tip'] else settle(yv(c, ng, t), q[1], q[2] if sd == 1 else q[3], sd)
def followed(c, ng, t, b, ts, sd, size):
    sr = SERIES.get((c, ng, t, b))
    if not sr: return None
    a, z = at(sr[1], ts - W), at(sr[1], ts)
    if a is None or z is None: return None
    return sd * (z[4] - a[4]) >= 0.5 * size
def cellf(v, seas):
    v = np.asarray(v, float)
    if len(v) < 15: return f'{"—":>7s} ({len(v):4d})     '
    s = pd.Series(v).groupby(np.asarray(seas)).mean(); s = s[pd.Series(seas).value_counts().reindex(s.index) >= 5]
    return f'{100 * v.mean():+6.1f}% ({len(v):4d}) {int((s > 0).sum())}/{len(s)}'
for t, nm in ((21, 'ΧΑΝΤΙΚΑΠ'), (23, 'ΣΥΝΟΛΑ')):
    print(f'\n{"=" * 140}\n{nm}')
    print(f'\n (Α) ΑΚΟΛΟΥΘΩ ΣΤΟ ΙΔΙΟ ΒΙΒΛΙΟ (+5′) — ROI (bets) θετικες σεζον')
    print(f'   {"":14s}' + ''.join(f'{cn:>24s}' for _, cn, _ in COMPS) + f'{"ΟΛΑ":>24s}')
    for b in BKS:
        line = f'   {BOOK[b]:14s}'
        for cc in [c for c, _, _ in COMPS] + [None]:
            v, ss = [], []
            for (c, ng, tt, cb), (ts, sd, size, sea) in AL.items():
                if tt != t or cb != b or (cc and c != cc): continue
                p = bet_at(c, ng, t, b, ts + 300, sd)
                if p is not None: v.append(p); ss.append(sea)
            line += f'{cellf(v, ss):>24s}'
        print(line)
    print(f'\n (Β) ALERT ΣΤΟ (γραμμη) → ΠΟΝΤΟΣ ΣΤΟ (στηλη), οταν αυτο δεν ειχε ακολουθησει · τιμη +5′ · ολες οι διοργανωσεις')
    print(f'   {"alert \\ ποντος":14s}' + ''.join(f'{BOOK[b]:>24s}' for b in BKS))
    for a in BKS:
        line = f'   {BOOK[a]:14s}'
        for b in BKS:
            if a == b: line += f'{"·":>24s}'; continue
            v, ss = [], []
            for (c, ng, tt, cb), (ts, sd, size, sea) in AL.items():
                if tt != t or cb != a: continue
                f = followed(c, ng, t, b, ts, sd, size)
                if f is None or f: continue
                p = bet_at(c, ng, t, b, ts + 300, sd)
                if p is not None: v.append(p); ss.append(sea)
            line += f'{cellf(v, ss):>24s}'
        print(line)
    print(f'\n (Β2) ιδιο, ανα διοργανωση (ποντος σε ΟΠΟΙΟΔΗΠΟΤΕ αλλο βιβλιο δεν ειχε ακολουθησει, μεσος ανα alert)')
    print(f'   {"alert στο":14s}' + ''.join(f'{cn:>24s}' for _, cn, _ in COMPS))
    for a in BKS:
        line = f'   {BOOK[a]:14s}'
        for cc, _, _ in COMPS:
            v, ss = [], []
            for (c, ng, tt, cb), (ts, sd, size, sea) in AL.items():
                if tt != t or cb != a or c != cc: continue
                ps = [bet_at(c, ng, t, b, ts + 300, sd) for b in BKS if b != a and followed(c, ng, t, b, ts, sd, size) is False]
                ps = [p for p in ps if p is not None]
                if ps: v.append(np.mean(ps)); ss.append(sea)
            line += f'{cellf(v, ss):>24s}'
        print(line)
    print(f'\n (Γ) ΣΥΝΑΙΝΕΣΗ: 2 βιβλια κινηθηκαν ≥1.5 ιδια μερια (το 2ο μεσα σε 60′ απο το 1ο) → ποντος στα υπολοιπα που δεν ακολουθησαν, +5′')
    print(f'   {"":22s}' + ''.join(f'{cn:>24s}' for _, cn, _ in COMPS) + f'{"ΟΛΑ":>24s}')
    rows_ = {}
    games = {}
    for (c, ng, tt, cb), v in AL.items():
        if tt == t: games.setdefault((c, ng), []).append((v[0], cb, v[1], v[2], v[3]))
    for lab, pair in (('οποια 2 βιβλια', None), ('Crown + SBOBET (Ασια)', {3, 31}), ('Bet365 + WH (Ευρωπη)', {8, 10})):
        line = f'   {lab:22s}'
        for cc in [c for c, _, _ in COMPS] + [None]:
            v, ss = [], []
            for (c, ng), L in games.items():
                if cc and c != cc: continue
                L = sorted(L)
                for k in range(1, len(L)):
                    ok = [x for x in L[:k] if x[2] == L[k][2] and L[k][0] - x[0] <= 3600]
                    if not ok: continue
                    used = {ok[0][1], L[k][1]}
                    if pair and used != pair: continue
                    ts, sd = L[k][0], L[k][2]
                    ps = [bet_at(c, ng, t, b, ts + 300, sd) for b in BKS if b not in used and followed(c, ng, t, b, ts, sd, L[k][3]) is False]
                    ps = [p for p in ps if p is not None]
                    if ps: v.append(np.mean(ps)); ss.append(L[k][4])
                    break
            line += f'{cellf(v, ss):>24s}'
        print(line)
