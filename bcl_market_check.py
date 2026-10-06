# -*- coding: utf-8 -*-
"""bcl_market_check.py — BCL: ΜΟΝΤΕΛΟ vs ΑΓΟΡΑ με ΟΛΟ το ιστορικο Nowgoal (6/10/2026, Στελιος «BCL σημερα»).
Προβλεψεις: bcl_engine_preds.pkl (FIN = τελικη μηχανη, ρυθμισεις LOSO — καθε σεζον με επιλογες απο τις αλλες).
ΠΡΟ-ΔΗΛΩΜΕΝΑ (ΠΡΙΝ την εκτελεση):
  Κ2 vs κλεισιμο Crown: b ≥ .15, t ≥ 2, θετικο σε ≥ 3/4 σεζον → «γνωση που η αγορα δεν εχει».
  ROI χαντικαπ, κανονας EuroCup (μοντελο μονο ≥8%): Crown ανοιγμα > 0 ΚΑΙ θετικο σε ≥ 3/4 σεζον ΚΑΙ Bet365 ανοιγμα > 0 → «περνα».
  Περιγραφικα (χωρις κριση): αρχη σεζον (1-3 ματς BCL της ομαδας γηπ.) vs υπολοιπα · μεγαλες διαφωνιες ≥5 ποντους.
Εξοδος: bcl_market_check_out.txt"""
import sys, os, json, math, pickle, collections
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
nd = NormalDist(); Phi = nd.cdf
PK = sys.argv[1] if len(sys.argv) > 1 else 'bcl_engine_preds.pkl'
D = pickle.load(open(PK, 'rb'))
ids, YS, act, FIN, H1, T = D['id'], D['y'], D['act'], D['FIN'], D['H1'], D['t']
FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
sc = {e['id']: (int(e['hs']), int(e['as_'])) for k, L in FG.items() if k.startswith('BCL_') for e in L if e.get('hs') not in (None, '')}
isb = np.array([i in sc for i in ids])
# αυξων αριθμος ματς BCL της ομαδας γηπ. στη σεζον
gno = np.zeros(len(ids), int); cnt = collections.Counter()
for i in sorted(np.where(isb)[0], key=lambda i: T[i]):
    cnt[(YS[i], D['hid'][i])] += 1; gno[i] = cnt[(YS[i], D['hid'][i])]
ROWS = collections.defaultdict(dict)
for ln in open('nowgoal_bcl/odds.jsonl', encoding='utf-8'):
    r = json.loads(ln)
    if r['t'] == 21: ROWS[r['ngid']][r['cid']] = sorted([x for x in r['rows'] if x[4] == 2 and x[1] is not None and x[2] and x[3]], key=lambda x: x[0])
idx = collections.defaultdict(list)
for i in np.where(isb)[0]: idx[sc[ids[i]]].append(i)
MK = {}
for f in sorted(os.listdir('nowgoal_bcl')):
    if not f.startswith('sched_'): continue
    for g in json.load(open('nowgoal_bcl/' + f, encoding='utf-8')):
        if g.get('hs') is None or g['ngid'] not in ROWS: continue
        tip = pd.Timestamp(g['bj']) - pd.Timedelta(hours=8); hit, sw = None, False
        for (a_, b_), swp in (((g['hs'], g['as_']), False), ((g['as_'], g['hs']), True)):
            for i in idx.get((a_, b_), []):
                if abs((pd.Timestamp(T[i]) - tip).total_seconds()) <= 26 * 3600: hit, sw = i, swp; break
            if hit is not None: break
        if hit is None: continue
        rec = {}
        for cid in (3, 8):
            R = ROWS[g['ngid']].get(cid)
            if not R: continue
            def cv(x):
                o1, o2 = 1 + x[2], 1 + x[3]; L = -x[1]; ph = (1 / o1) / (1 / o1 + 1 / o2); mu = -L + 12.0 * nd.inv_cdf(min(max(ph, 1e-4), 1 - 1e-4))
                return (-L, -mu, o2, o1) if sw else (L, mu, o1, o2)
            rec[cid] = dict(o=cv(R[0]), c=cv(R[-1]))
        if rec: MK[hit] = rec
pickle.dump({ids[i]: v for i, v in MK.items()}, open('bcl_mk.pkl', 'wb'))   # αγορα ανα ματς (για αλλα τεστ)
EVS = sorted({int(YS[i]) for i in MK if np.isfinite(FIN[i])})
NEED = math.ceil(.75 * len(EVS))   # 4 σεζον → 3 · 5 σεζον → 4 (ιδιο με τον προ-δηλωμενο κανονα του bcl_engine_test)
ii = [i for i in MK if 3 in MK[i] and np.isfinite(FIN[i])]
P(f'ΑΓΟΡΑ Nowgoal: {len(MK)} ματς BCL με χαντικαπ · ' + ' · '.join(f'{y}-{(y+1)%100:02d}: {sum(1 for i in MK if YS[i] == y)}' for y in EVS))
SIG = float(np.std([act[i] - MK[i][3]['c'][1] for i in ii]))
P(f'σ (πραγματικο − κλεισιμο) {SIG:.1f}')
P(''); P('=== 1. ΑΚΡΙΒΕΙΑ (λαθος, ποντοι — μικροτερο = καλυτερο) ===')
for y in EVS + ['ΟΛΑ']:
    s = [i for i in ii if y == 'ΟΛΑ' or YS[i] == y]
    if not s: continue
    a = act[s]; P(f'  {str(y):5s} n {len(s):3d} · μοντελο {np.sqrt(np.mean((a - FIN[s])**2)):.2f} · ανοιγμα {np.sqrt(np.mean((a - np.array([MK[i][3]["o"][1] for i in s]))**2)):.2f} · κλεισιμο {np.sqrt(np.mean((a - np.array([MK[i][3]["c"][1] for i in s]))**2)):.2f}')
P(''); P('=== 2. Κ2: ξερει το μοντελο κατι που δεν ξερει η αγορα; (b ≥ .15, t ≥ 2, ≥3/4 των σεζον) ===')
def k2(s, wh):
    x = np.array([FIN[i] - MK[i][3][wh][1] for i in s]); z = np.array([act[i] - MK[i][3][wh][1] for i in s])
    c = np.polyfit(x, z, 1); r_ = z - np.polyval(c, x); se = math.sqrt(np.sum(r_ ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2)); return c[0], c[0] / se
for wh, lab in (('c', 'κλεισιμο'), ('o', 'ανοιγμα')):
    b, t = k2(ii, wh); per = [k2([i for i in ii if YS[i] == y], wh)[0] for y in EVS if sum(YS[i] == y for i in ii) > 20]
    ok = b >= .15 and t >= 2 and sum(q > 0 for q in per) >= NEED
    P(f'  vs {lab:9s} b {b:+.2f} (t {t:+.1f}) · ανα σεζον ' + ' '.join(f'{q:+.2f}' for q in per) + ('  ✓' if ok and wh == 'c' else ('  ✗' if wh == 'c' else '')))
def cover(m_, L, s):
    if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
    pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
def bets(s, book, wh, thr, w=1.0):
    R = []
    for i in s:
        if book not in MK[i]: continue
        L, mk, o1, o2 = MK[i][book][wh]; pw, pp, pl = cover(mk + w * (FIN[i] - mk), L, SIG)
        e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1; s_, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
        if e < thr: continue
        xx = (act[i] + L) * s_; R.append(((od - 1) if xx > 0 else (0 if xx == 0 else -1), int(YS[i]), i, s_, e))
    return R
def cell(R):
    if not R: return '—'
    u = np.array([q[0] for q in R]); pos = sum(1 for y in EVS if [q for q in R if q[1] == y] and np.mean([q[0] for q in R if q[1] == y]) > 0)
    nys = sum(1 for y in EVS if [q for q in R if q[1] == y])
    return f'{u.mean()*100:+.1f}% (n {len(R)}, {u.sum():+.1f}u, θετ {pos}/{nys})'
P(''); P('=== 3. ROI χαντικαπ, κανονας μοντελο μονο ≥8% (οπως EuroCup) ===')
main = {}
for book, wh, lab in ((3, 'o', 'Crown ανοιγμα'), (3, 'c', 'Crown κλεισιμο'), (8, 'o', 'Bet365 ανοιγμα'), (8, 'c', 'Bet365 κλεισιμο')):
    R = bets(ii, book, wh, .08); main[(book, wh)] = R; P(f'  {lab:16s} {cell(R)}')
    P('      ανα σεζον: ' + ' · '.join(f'{y}-{(y+1)%100:02d} {cell([q for q in R if q[1] == y])}' for y in EVS))
R = main[(3, 'o')]; u = [q[0] for q in R]
pos = sum(1 for y in EVS if [q for q in R if q[1] == y] and np.mean([q[0] for q in R if q[1] == y]) > 0)
okR = R and np.mean(u) > 0 and pos >= NEED and main[(8, 'o')] and np.mean([q[0] for q in main[(8, 'o')]]) > 0
P(f'  ΚΡΙΣΗ (Crown ανοιγμα > 0, ≥{NEED}/{len(EVS)} σεζον, Bet365 ανοιγμα > 0): ' + ('✓ ΠΕΡΝΑ' if okR else '✗ ΔΕΝ ΠΕΡΝΑ'))
P(''); P('=== 4. Αλλα ορια / μιξη (περιγραφικα, Crown ανοιγμα) ===')
for thr in (.04, .06, .08, .12, .16):
    P(f'  μοντελο ≥{thr:.0%}: {cell(bets(ii, 3, "o", thr))}  |  μιξη 50/50 ≥{thr:.0%}: {cell(bets(ii, 3, "o", thr, .5))}')
P(''); P('=== 5. ΑΡΧΗ ΣΕΖΟΝ (1-3 ματς BCL γηπ.) vs ΥΠΟΛΟΙΠΑ (Crown ανοιγμα, μοντελο ≥8%) ===')
for lab, f in (('1-3', lambda i: gno[i] <= 3), ('4+', lambda i: gno[i] > 3)):
    s = [i for i in ii if f(i)]
    a = act[s]; P(f'  {lab:4s} n {len(s):3d} · λαθος μοντελο {np.sqrt(np.mean((a - FIN[s])**2)):.2f} vs ανοιγμα {np.sqrt(np.mean((a - np.array([MK[i][3]["o"][1] for i in s]))**2)):.2f} · Κ2 ανοιγμα b {k2(s, "o")[0]:+.2f} (t {k2(s, "o")[1]:+.1f}) · ROI {cell(bets(s, 3, "o", .08))}')
P(''); P('=== 6. ΜΕΓΑΛΕΣ ΔΙΑΦΩΝΙΕΣ (|μοντελο − ανοιγμα| ≥ 5 ποντους): ποιος ειχε δικιο; ===')
for lo, hi in ((0, 3), (3, 5), (5, 8), (8, 99)):
    s = [i for i in ii if lo <= abs(FIN[i] - MK[i][3]['o'][1]) < hi]
    if len(s) < 5: continue
    toward = np.mean([np.sign(FIN[i] - MK[i][3]['o'][1]) * (act[i] - MK[i][3]['o'][1]) for i in s])
    gap = np.mean([abs(FIN[i] - MK[i][3]['o'][1]) for i in s])
    P(f'  διαφωνια {lo}-{hi if hi < 99 else "+"}: n {len(s):3d} · μεση διαφωνια {gap:.1f} · το αποτελεσμα πηγε προς το μοντελο κατα {toward:+.1f} ποντους (θα ηταν {gap:.1f} αν ειχε απολυτο δικιο)')
open(PK.replace('bcl_engine_preds', 'bcl_market_check_out').replace('.pkl', '.txt'), 'w', encoding='utf-8').write(chr(10).join(out))
