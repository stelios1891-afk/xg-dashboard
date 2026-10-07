# -*- coding: utf-8 -*-
"""bcl_small_history.py — BCL: ΠΩΣ ΠΗΓΑΝ ΟΙ ΠΡΟΒΛΕΨΕΙΣ ΓΙΑ ΟΜΑΔΕΣ ΤΩΝ 9 ΜΙΚΡΩΝ ΠΡΩΤΑΘΛΗΜΑΤΩΝ (χωρις εγχωρια) — ανα αριθμο ματς BCL της ομαδας
(7/10/2026, Στελιος: «ηταν θορυβωδεις στην αρχη και σιγα σιγα με τα ευρωπαικα και μεγαλυτερο δειγμα ανεβηκαν; να το δουμε αναλυτικα»).
Προβλεψεις = live φορμουλα (bcl_engine_preds_live.pkl FIN). Αγορα = Crown/Bet365 ανοιγμα & κλεισιμο (bcl_mk.pkl, μεσος). Μικρα = CZE FIN BUL POR SUI CYP DEN GEO SVK.
Ολα απο τη μερια της ομαδας του μικρου πρωταθληματος (αν παιζουν δυο μικρες: γηπεδουχος). Picks: live κανονας ≥8% στο ανοιγμα, σ 12.
Εξοδος: bcl_small_history_out.txt"""
import sys, json, pickle, collections, math
import numpy as np
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
import bcl_common as B
SMALL = {'CZE', 'FIN', 'BUL', 'POR', 'SUI', 'CYP', 'DEN', 'GEO', 'SVK'}
Phi = NormalDist().cdf
D = pickle.load(open('bcl_engine_preds_live.pkl', 'rb')); MK = pickle.load(open('bcl_mk.pkl', 'rb'))
FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
E = {e['id']: e for k, L in FG.items() if k.startswith('BCL_') for e in L if e.get('hs') not in (None, '')}
rows = B.load(pre=False, extra2=True, include=('CZE', 'FIN')); by_y = collections.defaultdict(list)
for r in rows: by_y[r[0]].append(r)
MC = {y: B._main_comp(v) for y, v in by_y.items()}
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
# αριθμος ματς BCL καθε ομαδας μεσα στη σεζον (με προκριματικα)
order = sorted([i for i in E], key=lambda i: E[i]['ts']); cnt = collections.Counter(); GN = {}
for i in order:
    e = E[i]; y = int([k for k in FG if k.startswith('BCL_') and any(x.get('id') == i for x in FG[k])][0].split('_')[1]) if False else None
for k, L in FG.items():
    if not k.startswith('BCL_'): continue
    y = int(k.split('_')[1])
    for e in sorted([x for x in L if x.get('hs') not in (None, '')], key=lambda x: x['ts']):
        h, a = B.ALIAS.get(e['hid'], e['hid']), B.ALIAS.get(e['aid'], e['aid'])
        cnt[(y, h)] += 1; cnt[(y, a)] += 1; GN[e['id']] = (cnt[(y, h)], cnt[(y, a)])
def cover(m_, L, s=12.0):
    if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
    pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
R = []
for k, i in enumerate(D['id']):
    if i not in E or not np.isfinite(D['FIN'][k]) or i not in MK: continue
    y = int(D['y'][k]); e = E[i]; h, a = B.ALIAS.get(e['hid'], e['hid']), B.ALIAS.get(e['aid'], e['aid'])
    lg = lambda t: MC.get(y, {}).get(t) or MC.get(y - 1, {}).get(t)
    sh, sa = lg(h) in SMALL, lg(a) in SMALL
    s = 1 if sh else (-1 if sa else 1); small = sh or sa
    gn = GN.get(i, (0, 0)); g_ = gn[0] if s == 1 else gn[1]
    if not small: g_ = max(gn)
    act = int(e['hs']) - int(e['as_']); m = float(D['FIN'][k])
    mk = MK[i]; mo = np.mean([v['o'][1] for v in mk.values() if 'o' in v]); mc = np.mean([v['c'][1] for v in mk.values() if 'c' in v]) if any('c' in v for v in mk.values()) else np.nan
    pk = {}
    for book in (3, 8):
        if book not in mk or 'o' not in mk[book]: continue
        L, _, o1, o2 = mk[book]['o']; pw, pp, pl = cover(m, L); e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
        side, ed, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
        if ed >= .08:
            x = (act + L) * side; pk[book] = ((od - 1) if x > 0 else (0 if x == 0 else -1), side * s)   # (κερδος, +1 = υπερ της μικρης)
    R.append(dict(y=y, small=small, both=sh and sa, gb=g_, act=act * s, m=m * s, mo=mo * s, mc=mc * s, pk=pk, lg=lg(h) if sh else lg(a)))
EV = [2021, 2022, 2023, 2024, 2025]
BINS = [('ματς 1-3', 1, 3), ('4-6', 4, 6), ('7-10', 7, 10), ('11+', 11, 99)]
def block(title, sel):
    P(''); P(f'## {title}')
    P('  ζωνη        n   | λαθος: μοντελο / ανοιγμα / κλεισιμο | μεροληψια (πραγμ − προβλ, + = η ομαδα πηγε καλυτερα): μοντελο / κλεισιμο | picks ≥8% ανοιγμα: Crown · Bet365 (ποσα υπερ της ομαδας)')
    for lab, a, b in BINS + [('ΟΛΑ', 1, 99)]:
        S = [r for r in sel if a <= r['gb'] <= b and r['y'] in EV]
        if len(S) < 5: continue
        ac = np.array([r['act'] for r in S]); mm = np.array([r['m'] for r in S]); mo = np.array([r['mo'] for r in S]); mc = np.array([r['mc'] for r in S])
        ok = np.isfinite(mc)
        cells = []
        for book, nm in ((3, 'Crown'), (8, 'B365')):
            u = [r['pk'][book] for r in S if book in r['pk']]
            if u: cells.append(f"{nm} {np.mean([x[0] for x in u])*100:+.1f}% ({len(u)}, υπερ {sum(1 for x in u if x[1] > 0)})")
        P(f'  {lab:9s} {len(S):4d}  | {math.sqrt(np.mean((ac - mm) ** 2)):5.2f} / {math.sqrt(np.mean((ac - mo) ** 2)):5.2f} / {math.sqrt(np.mean((ac[ok] - mc[ok]) ** 2)):5.2f} | '
          f'{np.mean(ac - mm):+5.2f} / {np.mean(ac[ok] - mc[ok]):+5.2f} | ' + ' · '.join(cells))
small = [r for r in R if r['small'] and not r['both']]
block('ΟΜΑΔΕΣ ΜΙΚΡΩΝ ΠΡΩΤΑΘΛΗΜΑΤΩΝ (απο τη μερια τους, 2021-26)', small)
block('ΥΠΟΛΟΙΠΑ ΜΑΤΣ BCL (γηπεδουχος· ζωνη = μεγαλυτερος αριθμος ματς των δυο)', [r for r in R if not r['small']])
P(''); P('## ΑΝΑ ΣΕΖΟΝ (ομαδες μικρων): n · λαθος μοντελο / κλεισιμο · μεροληψια μοντελου · picks Crown')
for Y in EV:
    S = [r for r in small if r['y'] == Y]
    if not S: continue
    ac = np.array([r['act'] for r in S]); mm = np.array([r['m'] for r in S]); mc = np.array([r['mc'] for r in S]); ok = np.isfinite(mc)
    u = [r['pk'][3][0] for r in S if 3 in r['pk']]
    P(f'  {Y}-{(Y + 1) % 100:02d}: n {len(S):3d} · {math.sqrt(np.mean((ac - mm) ** 2)):5.2f} / {math.sqrt(np.mean((ac[ok] - mc[ok]) ** 2)):5.2f} · {np.mean(ac - mm):+5.2f} · '
      + (f'{np.mean(u)*100:+.1f}% ({len(u)})' if u else '—'))
P(''); P('## ΑΝΑ ΠΡΩΤΑΘΛΗΜΑ (ομαδες μικρων): n · λαθος μοντελο / κλεισιμο · μεροληψια μοντελου')
for c in sorted(SMALL):
    S = [r for r in small if r['lg'] == c and r['y'] in EV]
    if len(S) < 3: continue
    ac = np.array([r['act'] for r in S]); mm = np.array([r['m'] for r in S]); mc = np.array([r['mc'] for r in S]); ok = np.isfinite(mc)
    P(f'  {c}: n {len(S):3d} · {math.sqrt(np.mean((ac - mm) ** 2)):5.2f} / {math.sqrt(np.mean((ac[ok] - mc[ok]) ** 2)):5.2f} · {np.mean(ac - mm):+5.2f}')
open('bcl_small_history_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
