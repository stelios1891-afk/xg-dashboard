# -*- coding: utf-8 -*-
"""bcl_home_test.py — BCL ΕΔΡΑ (6/10/2026, Στελιος «εδρες ειδες; ποσο παιρνει ο γηπεδουχος; η Χολον παιζει στη Βουλγαρια»).
Ποσο παιρνει ιστορικα ο γηπεδουχος στο BCL, ανα φαση και ανα «ειδος εδρας», και πώς το βλεπει το μοντελο και η αγορα.
Κατηγοριες (ματς BCL με προβλεψη + αγορα Nowgoal Crown):
  κανονικη εδρα (ομιλοι / 2η φαση / νοκ-αουτ σειρες) · ισραηλινες «εντος» απο 10/2023 (παιζουν σε αλλη χωρα) · ισραηλινες εντος 2020-22 (στο Ισραηλ) ·
  προκριματικα (μινι-τουρνουα σε μια πολη — σχεδον ουδετερα) · Final Four (ουδετερο) · σεζον 2020-21 (COVID, χωρις κοσμο/φουσκα).
Μετρα: πραγματικη διαφορα γηπ. · προβλεψη μοντελου (live φορμουλα) · κλεισιμο αγορας · υπολοιπα (πραγματικο − μοντελο, πραγματικο − αγορα).
ΠΡΟ-ΔΗΛΩΜΕΝΟ: «το μοντελο δινει λαθος εδρα» σε μια κατηγορια αν |πραγματικο − μοντελο| ≥ 1.5 π. με t ≥ 2 (ή n < 30: μονο ενδειξη).
Εξοδος: bcl_home_test_out.txt"""
import sys, json, math, pickle, collections
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
try: FG.update({k: v for k, v in json.load(open('fs_bk_extra.json', encoding='utf-8')).items() if k not in FG})
except Exception: pass
isr = {t for k, L in FG.items() if k.startswith('ISR_') for e in L for t in (e['hid'], e['aid'])}
ukr = {t for k, L in FG.items() if k.startswith('UKR_') for e in L for t in (e['hid'], e['aid'])}
E = {e['id']: e for k, L in FG.items() if k.startswith('BCL_') for e in L}
# Final Four = τελευταια 4 ματς «Play Offs» καθε σεζον (ημιτελικοι, 3η θεση, τελικος)
ff = set()
for y in range(2016, 2027):
    po = sorted([e for e in FG.get(f'BCL_{y}', []) if 'Play Offs' in (e.get('stage') or '')], key=lambda e: e['ts'])
    ff |= {e['id'] for e in po[-4:]}
D = pickle.load(open('bcl_engine_preds_live.pkl', 'rb'))
MK = pickle.load(open('bcl_mk.pkl', 'rb'))
ids, ys, act, FIN = D['id'], D['y'], D['act'], D['FIN']
st = json.load(open('bcl_state.json', encoding='utf-8'))
P(f"Εδρα μεσα στο μοντελο: κοινη κλιμακα {st['m2']['h']:.2f} π. (ολες οι διοργανωσεις μαζι) · μονο-BCL {st['m1']['h'] * st['m1']['pace'] / 100:.2f} π. → μιξη ≈ {.75 * st['m2']['h'] + .25 * st['m1']['h'] * st['m1']['pace'] / 100:.2f} π. σε ΚΑΘΕ ματς BCL")
def cat(i):
    e = E.get(ids[i]); s = (e or {}).get('stage') or ''
    if ids[i] in ff: return 'Final Four (ουδετερο)'
    if 'Qualification' in s: return 'προκριματικα (μινι-τουρνουα)'
    if ys[i] == 2020: return '2020-21 (COVID)'
    if e and e['hid'] in isr and (e['ts'] >= 1696636800): return 'ισραηλινες «εντος» απο 10/2023 (εξω απο Ισραηλ)'
    if e and e['hid'] in isr: return 'ισραηλινες εντος 2021-22/2022-23 (στο Ισραηλ)'
    if e and e['hid'] in ukr and e['ts'] >= 1645660800: return 'ουκρανικες «εντος» μετα 24/2/2022'
    return 'κανονικη εδρα'
C = collections.defaultdict(list)
for i in range(len(ids)):
    if not np.isfinite(FIN[i]): continue
    mk = MK.get(ids[i], {}).get(3)
    C[cat(i)].append((act[i], FIN[i], mk['c'][1] if mk else np.nan, int(ys[i])))
def ms(x):
    x = np.array([v for v in x if np.isfinite(v)]); return (x.mean(), x.std(ddof=1) / math.sqrt(len(x)) if len(x) > 1 else np.nan, len(x))
P(''); P('κατηγορια · n · πραγματικη διαφ. γηπ. · μοντελο · αγορα (κλεισιμο) · πραγματικο − μοντελο (t) · πραγματικο − αγορα (t) · αγορα − μοντελο')
for c, R in sorted(C.items(), key=lambda kv: -len(kv[1])):
    a = [r[0] for r in R]; m = [r[1] for r in R]; k = [r[2] for r in R]
    rm_, rk = ms([x - y for x, y in zip(a, m)]), ms([x - y for x, y in zip(a, k)])
    km_ = ms([y - x for x, y in zip(m, k)])
    flag = ' ← ΛΑΘΟΣ ΕΔΡΑ ΣΤΟ ΜΟΝΤΕΛΟ' if abs(rm_[0]) >= 1.5 and abs(rm_[0] / rm_[1]) >= 2 and rm_[2] >= 30 else (' ← ενδειξη (λιγα ματς)' if abs(rm_[0]) >= 1.5 and rm_[2] < 30 else '')
    P(f'  {c:48s} n {len(R):4d} · πραγμ. {np.mean(a):+5.1f} · μοντ. {np.mean(m):+5.1f} · αγορα {np.nanmean(k):+5.1f} (n {km_[2]}) · '
      f'πραγμ.−μοντ. {rm_[0]:+5.1f} (t {rm_[0] / rm_[1]:+.1f}) · πραγμ.−αγορα {rk[0]:+5.1f} (t {rk[0] / rk[1]:+.1f}) · αγορα−μοντ. {km_[0]:+5.1f}{flag}')
P(''); P('κανονικη εδρα ανα σεζον (πραγματικο − μοντελο · πραγματικο − αγορα):')
R = C['κανονικη εδρα']
for y in sorted({r[3] for r in R}):
    s = [r for r in R if r[3] == y]
    P(f'  {y}-{(y + 1) % 100:02d}: n {len(s):3d} · πραγμ. {np.mean([r[0] for r in s]):+.1f} · πραγμ.−μοντ. {np.mean([r[0] - r[1] for r in s]):+.1f} · πραγμ.−αγορα {np.nanmean([r[0] - r[2] for r in s]):+.1f}')
P(''); P('ισραηλινες «εντος» απο 10/2023 — ανα ματς:')
for i in range(len(ids)):
    if np.isfinite(FIN[i]) and cat(i).startswith('ισραηλινες «εντος»'):
        e = E[ids[i]]; mk = MK.get(ids[i], {}).get(3)
        P(f"  {e['home'][:20]:20s} - {e['away'][:20]:20s} {e['hs']}-{e['as_']} · μοντ. {FIN[i]:+.1f} · αγορα {mk['c'][1] if mk else float('nan'):+.1f}")
open('bcl_home_test_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))

# ---------- ΔΙΟΡΘΩΣΗ ΕΔΡΑΣ ανα κατηγορια, LOSO (εκτιμηση στις αλλες σεζον → εφαρμογη στη σεζον που λειπει) ----------
# ΠΡΟ-ΔΗΛΩΜΕΝΟ: μπαινει αν το λαθος (RMSE ολων των ματς BCL) πεφτει σε ≥4/5 σεζον 2021-25 ΚΑΙ το ROI ≥8% (Crown ανοιγμα) δεν χειροτερευει.
from statistics import NormalDist
Phi = NormalDist().cdf
EV = [2021, 2022, 2023, 2024, 2025]
CAT = np.array([cat(i) for i in range(len(ids))])
ok_ = np.isfinite(FIN)
ADJ = np.zeros(len(ids)); used = {}
for Y in EV:
    tr = ok_ & np.isin(ys, [x for x in EV if x != Y]); te = ys == Y
    for c in set(CAT):
        m = tr & (CAT == c)
        if m.sum() >= 15:
            d = float(np.mean(act[m] - FIN[m])); ADJ[te & (CAT == c)] = d; used.setdefault(c, []).append(round(d, 1))
NEW = FIN + ADJ
P(''); P('################ ΔΙΟΡΘΩΣΗ ΕΔΡΑΣ ΑΝΑ ΚΑΤΗΓΟΡΙΑ (LOSO) ################')
for c, v in used.items(): P(f'  {c}: διορθωση ανα σεζον {v}')
def rm(v, m): m = m & np.isfinite(v); return float(np.sqrt(np.mean((act - v)[m] ** 2)))
d = [rm(NEW, ys == Y) - rm(FIN, ys == Y) for Y in EV]
P('  λαθος: ' + ' '.join(f'{Y}: {rm(FIN, ys == Y):.3f}→{rm(NEW, ys == Y):.3f}' for Y in EV) + f' · καλυτερο {sum(x < 0 for x in d)}/5')
def roi(MOD, book=3):
    R = []
    for i in range(len(ids)):
        mk = MK.get(ids[i], {}).get(book)
        if not mk or not np.isfinite(MOD[i]) or ys[i] not in EV: continue
        L, mu, o1, o2 = mk['o']
        pw = Phi((MOD[i] + L) / 12.0) if abs(L - round(L)) > 1e-9 else Phi((MOD[i] + L - .5) / 12.0)
        pl = 1 - Phi((MOD[i] + L) / 12.0) if abs(L - round(L)) > 1e-9 else Phi((-MOD[i] - L - .5) / 12.0)
        pp = 1 - pw - pl; e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
        s, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
        if e < .08: continue
        x = (act[i] + L) * s; R.append((od - 1) if x > 0 else (0 if x == 0 else -1))
    return np.mean(R) * 100, len(R), sum(R)
for b, nm_ in ((3, 'Crown'), (8, 'Bet365')):
    a0, a1 = roi(FIN, b), roi(NEW, b)
    P(f'  ROI ≥8% {nm_} ανοιγμα: χωρις {a0[0]:+.1f}% ({a0[1]}, {a0[2]:+.1f}u) → με διορθωση {a1[0]:+.1f}% ({a1[1]}, {a1[2]:+.1f}u)')
okH = sum(x < 0 for x in d) >= 4 and roi(NEW, 3)[2] >= roi(FIN, 3)[2]
P('  ΚΡΙΣΗ: ' + ('✓ ΜΠΑΙΝΕΙ' if okH else '✗'))
open('bcl_home_test_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
