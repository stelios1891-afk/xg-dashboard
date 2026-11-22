"""
uel_timing.py — 9/10/2026 (Στελιος «με τον χρονισμο αλλαζουν τα δεδομενα;»): ΧΡΟΝΙΣΜΟΣ με τη ΣΗΜΕΡΙΝΗ ευρωπαικη αλυσιδα
(το euro_early_roi 10/9 ηταν παλια εκδοχη: χωρις σωστα τεταρτα φαβορι, μονο Crown, κατωφλια @4/@10 και για τις 2 πλευρες).
Ιδια picks με uel_battery (FotMob+FotMob, 1.70-2.10, |γραμμη| ≥0.5, κατωφλια live: UCL φαβ@10 dog@4 · UEL/UECL φαβ@4 dog@10),
αλλα ΕΠΙΛΟΓΗ ΚΑΙ ΤΙΜΗ στη γραμμη/αποδοση του βιβλιου Τ ωρες πριν τη σεντρα (τελευταια εγγραφη ≤ KO−T, οχι παλιοτερη απο 24ω).
Crown & SBOBET. Περιγραφικο + ΚΟΙΝΟ δειγμα (ματς με τιμη σε ολες τις στιγμες) για δικαιη συγκριση.
"""
import sys, io, json, glob, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('uel_battery.py', encoding='utf-8').read(); src = src[:src.index('P0 = make_picks')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
g = {'__name__': 'ut'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
MIDS, GD, SEA, COMP, FM, picks, LH_N, LA_N, KO, parse_line, sdist, cover_q, edge, fm = (g[k] for k in (
    'MIDS', 'GD', 'SEA', 'COMP', 'FM', 'picks', 'LH_N', 'LA_N', 'KO', 'parse_line', 'sdist', 'cover_q', 'edge', 'fm'))
HOURS = [72, 48, 24, 6, 2, 0]
TRAJ = {}
for f in glob.glob('nowgoal_odds/*_U*.jsonl'):
    for ln in open(f, encoding='utf-8'):
        r = json.loads(ln)
        if r['cid'] not in (3, 31): continue
        rows = []
        for mt, u, gg, dn in r.get('ah') or []:
            gl = parse_line(gg)
            try: rows.append((int(mt), -gl, float(u) + 1, float(dn) + 1))
            except (TypeError, ValueError): pass
        TRAJ[(str(r['mid']), 'Crown' if r['cid'] == 3 else 'SBOBET')] = sorted(x for x in rows if x[1] is not None)
def snap(mid, bk, h):
    ko = KO.get(mid); seq = TRAJ.get((mid, bk))
    if not ko or not seq: return None
    cut = ko - h * 3600 if h else ko + 900
    prev = [x for x in seq if x[0] <= cut]
    if not prev or (h and (ko - prev[-1][0]) / 3600 > h + 24): return None
    return prev[-1][1:]
rows = []
for i, mid in enumerate(MIDS):
    if not FM[i]: continue
    dist = sdist(LH_N[i], LA_N[i]); c = COMP[i]
    for bk in ('Crown', 'SBOBET'):
        for h in HOURS:
            s = snap(mid, bk, h)
            if not s: continue
            L, oh, oa = s
            for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                if not (1.70 <= o <= 2.10) or abs(ln) < 0.5: continue
                role = 'fav' if ln < 0 else 'dog'
                pw, pp = cover_q(dist, side, ln) if role == 'fav' else picks.p_cover(dist, side, ln)
                e = edge(pw, pp, o)
                thr = (0.10 if role == 'fav' else 0.04) if c == 'ChampionsLeague' else (0.04 if role == 'fav' else 0.10)
                if e >= thr: rows.append(dict(mid=mid, comp=c, sea=SEA[i], book=bk, h=h, role=role, home=side == 1, edge=e, pnl=picks.settle(GD[i], side, ln, o)))
B = pd.DataFrame(rows)
HAS = {}
for i, mid in enumerate(MIDS):
    if FM[i]: HAS[mid] = all(snap(mid, bk, h) for bk in ('Crown', 'SBOBET') for h in HOURS)
lab = lambda h: 'κλεισιμο' if h == 0 else f'−{h}ω'
for title, sel in (('ΟΛΑ τα διαθεσιμα', B), ('ΚΟΙΝΟ δειγμα (τιμη σε ολες τις στιγμες και στα 2 βιβλια)', B[B.mid.map(HAS).fillna(False)])):
    print(f'\n=== {title} — ROI μεσος Crown/SBOBET (n = picks ανα βιβλιο) ===')
    for c in ('EuropaLeague', 'ChampionsLeague', 'ConferenceLeague'):
        print(f' [{c}]')
        for h in HOURS:
            x = sel[(sel.comp == c) & (sel.h == h)]
            print(f'   {lab(h):9s} ολα {fm(x)} · φαβ {fm(x[x.role == "fav"])[:30]} · dogs {fm(x[x.role == "dog"])[:30]}')
print('\n=== UEL ανα σεζον (ολα τα διαθεσιμα) ===')
for h in HOURS:
    x = B[(B.comp == 'EuropaLeague') & (B.h == h)]
    print(f'   {lab(h):9s} ' + ' · '.join(f'{s}: {fm(v)[:22]}' for s, v in x.groupby('sea')))
print('\n=== UEL φαβορι εντος/εκτος ανα στιγμη ===')
for h in HOURS:
    x = B[(B.comp == 'EuropaLeague') & (B.h == h) & (B.role == 'fav')]
    print(f'   {lab(h):9s} εντος {fm(x[x.home])[:30]} · εκτος {fm(x[~x.home])[:30]}')
