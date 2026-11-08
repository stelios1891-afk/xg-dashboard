# -*- coding: utf-8 -*-
"""bcl_absence_test.py — BCL: ΑΠΟΥΣΙΕΣ ΠΑΙΚΤΩΝ (8/10/2026, Στελιος «μεινε στο BCL — εδειξε οτι βοηθανε οι απουσιες;» → «ξεκινα»).
Ιδιο με nba_absence_cutoffs / dom_bk_absence_test. Δεδομενα: fs_bk_players.jsonl (Flashscore λεπτα ανα παικτη: ματς BCL + εγχωρια 6 μεγαλων).
Προβλεψεις = live φορμουλα (bcl_engine_preds_live FIN) · αγορα Crown/Bet365 (bcl_mk), ανοιγμα & κλεισιμο, μεσος των δυο.
ΝΕΑ ΑΠΟΥΣΙΑ: παικτης με μεσο ορο ≥C′ (10 τελευταια που επαιξε), επαιξε σε 1 απο τα 3 τελευταια ματς της ομαδας, ΔΕΝ παιζει σημερα· C {15,20,25,30}.
Ιστορικο ομαδας: (i) ΜΟΝΟ ματς BCL · (ii) BCL + εγχωρια (οπου υπαρχουν: ACB LBA GBL TBL LNB BBL).
ΠΡΟ-ΔΗΛΩΜΕΝΑ (ΠΡΙΝ την εκτελεση): Α αγορα: κλιση (πραγμ − γραμμη) ανα 10′ διαφορας απουσιας (φιλ − γηπ). Β φιλτρο «χωρις pick (live κανονας ≥8%)
  αν η πλευρα μας λειπει ≥Χ′» Χ {20,30,50}: ΠΕΡΝΑ αν τα κομμενα χειροτερα σε ≥4/5 σεζον (με ≥3 picks) ΚΑΙ το ROI που μενει ανεβαινει. Εξοδος: bcl_absence_out.txt"""
import sys, json, pickle, collections, math
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
Phi = NormalDist().cdf
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
EV = [2021, 2022, 2023, 2024, 2025]; CS = (15, 20, 25, 30); XS = (20, 30, 50)
D = pickle.load(open('bcl_engine_preds_live.pkl', 'rb')); MK = pickle.load(open('bcl_mk.pkl', 'rb'))
FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
BCL = {e['id']: (int(k.split('_')[1]), e) for k, L in FG.items() if k.startswith('BCL_') for e in L if e.get('hs') not in (None, '')}
# ---- παικτες ανα ματς (γηπ/φιλοξ απο αθροισμα ποντων) ----
PL = {}
for ln in open('fs_bk_players.jsonl', encoding='utf-8'):
    r = json.loads(ln)
    if not r['p']: continue
    tm = collections.defaultdict(lambda: [0.0, {}])
    for x in r['p']:
        pid, nm, t3, mn, pts = x[:5]; tm[t3][0] += pts or 0; tm[t3][1][pid] = mn or 0.0
    if len(tm) != 2: continue
    (a3, A), (b3, Bv) = tm.items()
    try: hs, as_ = int(r['hs']), int(r['as_'])
    except Exception: continue
    if abs(A[0] - hs) < .5 and abs(Bv[0] - as_) < .5: hp, ap = A[1], Bv[1]
    elif abs(Bv[0] - hs) < .5 and abs(A[0] - as_) < .5: hp, ap = Bv[1], A[1]
    else: continue
    PL[r['id']] = (r['ts'], r['hid'], r['aid'], hp, ap, r['lg'])
nb = sum(1 for i in PL if PL[i][5] == 'BCL')
P(f'ματς BCL με παικτες (σωστη αντιστοιχιση): {nb} / {len(BCL)} · εγχωρια ματς για ιστορικο: {len(PL) - nb}')
TG = {'bcl': collections.defaultdict(list), 'all': collections.defaultdict(list)}
for gid, (ts, h, a, hp, ap, lg) in PL.items():
    for src in ('bcl', 'all'):
        if src == 'bcl' and lg != 'BCL': continue
        TG[src][h].append((ts, hp)); TG[src][a].append((ts, ap))
for src in TG:
    for v in TG[src].values(): v.sort(key=lambda x: x[0])
def missing(src, team, ts, today, C):
    g = [x for x in TG[src][team] if x[0] < ts - 3600]
    if len(g) < 3: return None
    last3 = [x[1] for x in g[-3:]]; hist = collections.defaultdict(list)
    for _, pl in g:
        for p, mn in pl.items():
            if mn > 0: hist[p].append(mn)
    tot = 0.0
    for p in set().union(*[{k for k, v in x.items() if v > 0} for x in last3]):
        if today.get(p, 0) > 0: continue
        rec = hist[p][-10:]; avg = sum(rec) / len(rec)
        if avg >= C: tot += avg
    return tot
def cover(m_, L, s=12.0):
    if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
    pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
rows = []
for k, i in enumerate(D['id']):
    y = int(D['y'][k])
    if y not in EV or i not in MK or i not in PL or not np.isfinite(D['FIN'][k]): continue
    ts, h, a, hp, ap, _ = PL[i]; e = BCL[i][1]; act = int(e['hs']) - int(e['as_']); m = float(D['FIN'][k])
    r = dict(y=y, act=act, m=m)
    mo = [v['o'][1] for b, v in MK[i].items() if b in (3, 8) and 'o' in v]; mc = [v['c'][1] for b, v in MK[i].items() if b in (3, 8) and 'c' in v]
    if not mo: continue
    r['mo'] = np.mean(mo); r['mc'] = np.mean(mc) if mc else np.nan
    us = []; side = None
    for b in (3, 8):
        o = MK[i].get(b, {}).get('o')
        if not o: continue
        L, mu, o1, o2 = o; pw, pp, pl = cover(m, L); e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
        s_, ed, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
        if ed >= .08: x = (act + L) * s_; us.append((od - 1) if x > 0 else (0 if x == 0 else -1)); side = s_
    r['u'] = float(np.mean(us)) if us else None; r['side'] = side
    for src in ('bcl', 'all'):
        for C in CS:
            r[f'{src}h{C}'] = missing(src, h, ts, hp, C); r[f'{src}a{C}'] = missing(src, a, ts, ap, C)
    rows.append(r)
R = pd.DataFrame(rows)
P(f'ματς με αγορα + προβλεψη + παικτες: {len(R)} · picks live κανονα: {R.u.notna().sum()}')
for src, nm in (('bcl', 'ΙΣΤΟΡΙΚΟ ΜΟΝΟ BCL'), ('all', 'ΙΣΤΟΡΙΚΟ BCL + ΕΓΧΩΡΙΑ')):
    P(''); P(f'################ {nm} ################')
    for C in CS:
        hh, aa = R[f'{src}h{C}'], R[f'{src}a{C}']; ok = hh.notna() & aa.notna(); S = R[ok]
        a_ = np.r_[hh[ok], aa[ok]]
        P(f'  C {C}′: ματς με ιστορικο {ok.sum()} · ομαδα-ματς με απουσια {np.mean(a_ > 0):.0%} · μεσα λεπτα {a_[a_ > 0].mean() if (a_ > 0).any() else 0:.0f}′')
        x = (S[f'{src}a{C}'] - S[f'{src}h{C}']) / 10
        cells = []
        for lab, col in (('κλεισ', 'mc'), ('ανοιγ', 'mo'), ('μοντ', 'm')):
            z = S.act - S[col]; okz = z.notna(); xx, zz = x[okz], z[okz]
            b = np.polyfit(xx, zz, 1)[0]; r_ = zz - np.polyval(np.polyfit(xx, zz, 1), xx); se = math.sqrt(np.sum(r_ ** 2) / (len(xx) - 2) / np.sum((xx - xx.mean()) ** 2))
            cells.append(f'{lab} {b:+.2f} (t {b / se:+.1f})')
        P('     αγορα/μοντελο κλιση ανα 10′: ' + ' · '.join(cells))
        K = S[S.u.notna()].copy()
        K['us'] = np.where(K.side == 1, K[f'{src}h{C}'], K[f'{src}a{C}']); K['op'] = np.where(K.side == 1, K[f'{src}a{C}'], K[f'{src}h{C}'])
        def cell(s): return f'{s.u.mean()*100:+.1f}% ({len(s)})' if len(s) else '—'
        P(f'     picks: ολα {cell(K)} · η ΔΙΚΗ ΜΑΣ πλευρα λειπει {cell(K[K.us > 0])} · μονο ο ΑΝΤΙΠΑΛΟΣ {cell(K[(K.op > 0) & (K.us == 0)])} · κανεις {cell(K[(K.us == 0) & (K.op == 0)])}')
        for X in XS:
            cut = K[K.us >= X]; keep = K[K.us < X]
            worse = sum(1 for Y in EV if (cut.y == Y).sum() >= 3 and cut[cut.y == Y].u.mean() < keep[keep.y == Y].u.mean())
            ny = sum(1 for Y in EV if (cut.y == Y).sum() >= 3)
            okf = ny >= 4 and worse >= 4 and len(keep) and keep.u.mean() > K.u.mean()
            P(f'     φιλτρο Χ {X}′: κοβει {cell(cut)} · μενουν {cell(keep)} · χειροτερα σε {worse}/{ny}' + ('  <- ΠΕΡΝΑ' if okf else '  ✗'))
open('bcl_absence_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
