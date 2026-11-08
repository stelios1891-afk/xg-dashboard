# -*- coding: utf-8 -*-
"""dom_bk_known_abs_test.py — ΕΓΧΩΡΙΑ ΜΠΑΣΚΕΤ: ΑΠΟΥΣΙΕΣ ΠΟΥ ΞΕΡΟΥΜΕ ΠΡΙΝ ΤΟ ΜΑΤΣ ΧΩΡΙΣ ΠΗΓΗ (10/10/2026, Στελιος «τρεξτα ολα»).
Ιδεα: βασικος που ΕΛΕΙΨΕ ΣΤΟ ΠΡΟΗΓΟΥΜΕΝΟ ματς της ομαδας φαινεται στο box score → «γνωστη απουσια» πριν το σημερινο (live εφικτο απο
Flashscore χωρις RotoWire). Πιανει και ομαδες σε κριση (Αφιον, Σαμσουνσπορ, Λε Πορτελ: φευγουν πολλοι βασικοι μαζι).
Βαση: dom_bk_audit_R.pkl (FINAL + εδρα Β1 σε Ισπανια/Γερμανια) · παικτες: fs_bk_players.jsonl (λεπτα ανα παικτη, ολα τα ματς).
ΓΝΩΣΤΗ ΑΠΟΥΣΙΑ ομαδας: ταχτικοι (≥3 απο τα 10 τελευταια ματς, μ.ο. λεπτων ≥10′) που ΔΕΝ επαιξαν στο αμεσως προηγουμενο ματς·
  βαρος οπως Ευρωλιγκα με k = συνεχομενα χαμενα + 1 (σημερα): k ≤3 → 1 · 4-10 → 0.5 · >10 → 0.  Κ = Σ βαρος × λεπτα/40.
ΔΙΟΡΘΩΣΗ: διαφορα γηπ += β·(Κ_φιλ − Κ_γηπ), β LOSO (κοινο για ολα τα πρωταθληματα, απο τις αλλες 4 σεζον).
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση): ΠΕΡΝΑ αν RMSE καλυτερο σε ≥4/5 σεζον (ολα μαζι) ΚΑΙ σε ≥4/6 πρωταθληματα.
Αναφορα: «μαντεψια» σωστη; (ποσοι γνωστοι αποντες ΟΝΤΩΣ δεν επαιξαν) · αγορα: κλιση (πραγμ − κλεισιμο) στο Κ (+ = η αγορα τις υποτιμα)·
  αποσταση απο κλεισιμο · picks (μοντελο ≥8% & μιξη ≥6%, με ταβανι διαφωνιας 8).  Εξοδος: dom_bk_known_abs_out.txt"""
import os
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import sys, io, contextlib, pickle, math, collections, json
import numpy as np, pandas as pd
from statistics import NormalDist
LGS = ['ACB', 'LBA', 'GBL', 'TBL', 'LNB', 'BBL']
class _Buf(io.StringIO):
    def reconfigure(self, **k): pass
_src = open('dom_bk_outrights_test_4lg.py', encoding='utf-8').read()
_src = _src.replace("ARGS = ['GBL', 'TBL', 'LNB', 'BBL']", f"ARGS = {LGS!r}", 1).replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass').split("KX = (0, 1, 2, 3, 4, 6)")[0]
with contextlib.redirect_stdout(_Buf()):
    exec(_src, globals())
sys.stdout.reconfigure(encoding='utf-8')
O = []
def W(s=''): print(s, flush=True); O.append(str(s))
R = pickle.load(open('dom_bk_audit_R.pkl', 'rb'))
R['m'] = np.where(R.lg.isin({'ACB', 'BBL'}), R.pb, R.pf)
# ---- παικτες ανα ματς (γηπ/φιλοξ απο αθροισμα ποντων) ----
PLM = {}
for ln in open('fs_bk_players.jsonl', encoding='utf-8'):
    r = json.loads(ln)
    if r['lg'] not in LGS or not r['p']: continue
    tm = collections.defaultdict(lambda: [0.0, {}])
    for x in r['p']:
        pid, nm, t3, mn, pts = x[:5]; tm[t3][0] += pts or 0; tm[t3][1][pid] = mn or 0.0
    if len(tm) != 2: continue
    (a3, A), (b3, B_) = tm.items()
    try: hs, as_ = int(r['hs']), int(r['as_'])
    except Exception: continue
    if abs(A[0] - hs) < .5 and abs(B_[0] - as_) < .5: hp, ap = A[1], B_[1]
    elif abs(B_[0] - hs) < .5 and abs(A[0] - as_) < .5: hp, ap = B_[1], A[1]
    else: continue
    PLM[r['id']] = (r['ts'], r['hid'], r['aid'], hp, ap)
TH = collections.defaultdict(list)
for gid, (ts, h, a, hp, ap) in PLM.items():
    TH[h].append((ts, gid, hp)); TH[a].append((ts, gid, ap))
for v in TH.values(): v.sort(key=lambda x: x[0])
def known(team, ts, today):
    L = [x for x in TH.get(team, []) if x[0] < ts - 3600]
    if len(L) < 3: return None, 0, 0
    last10 = L[-10:]; cnt = collections.Counter(p for _, _, d in last10 for p, mn in d.items() if mn > 0)
    K, nk, ret = 0.0, 0, 0
    for pid, c in cnt.items():
        if c < 3 or L[-1][2].get(pid, 0) > 0: continue
        mins = [d[pid] for _, _, d in L if d.get(pid, 0) > 0][-10:]
        if np.mean(mins) < 10: continue
        k = 1
        for _, _, d in reversed(L):
            if d.get(pid, 0) > 0: break
            k += 1
        w = 1.0 if k <= 3 else (.5 if k <= 10 else 0.0)
        if w == 0: continue
        K += w * np.mean(mins) / 40; nk += 1
        if today is not None and today.get(pid, 0) > 0: ret += 1
    return K, nk, ret
KH, KA, ok = np.zeros(len(R)), np.zeros(len(R)), np.zeros(len(R), bool); NK = NR = 0
for j, r in enumerate(R.itertuples()):
    gid = G.id.values[r.i]; ts = pd.Timestamp(G.t.values[r.i]).timestamp(); h, a = G.hid.values[r.i], G.aid.values[r.i]
    tod = PLM.get(gid)
    kh, nh, rh = known(h, ts, tod[3] if tod else None); ka, na, ra = known(a, ts, tod[4] if tod else None)
    if kh is None or ka is None: continue
    KH[j], KA[j], ok[j] = kh, ka, True
    if tod: NK += nh + na; NR += rh + ra
R = R[ok].copy(); X = (KA - KH)[ok]; R['X'] = X
W(f'ματς με αγορα & ιστορικο παικτων: {len(R)} · με γνωστη απουσια (καποια πλευρα): {np.mean((KH[ok] > 0) | (KA[ok] > 0)):.0%} · '
  f'γνωστοι αποντες {NK}: ΞΑΝΑΕΠΑΙΞΑΝ σημερα {NR} ({NR / max(1, NK):.0%}) → η «μαντεψια» σωστη {1 - NR / max(1, NK):.0%}')
res = (R.act - R.m).values; yy = R.y.values; lg_ = R.lg.values
b_all = float(X @ res / (X @ X)); W(f'κλιση ολα τα δεδομενα: β {b_all:+.2f} π. ανα 40′ γνωστης απουσιας (υπερ του αντιπαλου)')
held = np.zeros(len(R)); bs = []
for Y in EV:
    tr = yy != Y; b = float(X[tr] @ res[tr] / (X[tr] @ X[tr] + 1.0)); bs.append(b); held[yy == Y] = b * X[yy == Y]
rm_ = lambda v, m: float(np.sqrt(np.mean(v[m] ** 2)))
dS = [rm_(res - held, yy == Y) - rm_(res, yy == Y) for Y in EV]; dL = [rm_(res - held, lg_ == L) - rm_(res, lg_ == L) for L in LGS]
ok_ = sum(x < 0 for x in dS) >= 4 and sum(x < 0 for x in dL) >= 4
W(f'LOSO β {[round(b, 2) for b in bs]} · RMSE {rm_(res, np.ones(len(R), bool)):.3f} → {rm_(res - held, np.ones(len(R), bool)):.3f}')
W('  ανα σεζον ' + ' '.join(f'{x:+.3f}' for x in dS) + f' → {sum(x < 0 for x in dS)}/5 · ανα πρωταθλημα ' + ' '.join(f'{NAME[L][:4]} {x:+.3f}' for L, x in zip(LGS, dL))
  + f' → {sum(x < 0 for x in dL)}/6 · ' + ('<- ΠΕΡΝΑ' if ok_ else '✗'))
# ---- αγορα ----
W(''); W('ΑΓΟΡΑ: κλιση (πραγμ − γραμμη) στο Χ (+ = η αγορα υποτιμα τις γνωστες απουσιες) · και (γραμμη − μοντελο) (ποσο τις εχει η αγορα)')
for nm, col in (('ανοιγμα', 'mo'), ('κλεισιμο', 'mc')):
    z = (R.act - R[col]).values; b = np.polyfit(X, z, 1)[0]; r_ = z - np.polyval(np.polyfit(X, z, 1), X)
    se = math.sqrt(np.sum(r_ ** 2) / (len(X) - 2) / np.sum((X - X.mean()) ** 2)); per = sum(np.polyfit(X[yy == Y], z[yy == Y], 1)[0] > 0 for Y in EV)
    mm = np.polyfit(X, (R[col] - R.m).values, 1)[0]
    W(f'  {nm}: υπολοιπο {b:+.2f} (t {b / se:+.1f}, θετ {per}/5) · η αγορα μετακινειται {mm:+.2f} ανα μοναδα Χ (το μοντελο μας: 0)')
W(''); W('ΑΠΟΣΤΑΣΗ ΑΠΟ ΚΛΕΙΣΙΜΟ (RMSE μοντ vs κλεισ) ανα πρωταθλημα: πριν → με γνωστες απουσιες')
for L in LGS + ['ΟΛΑ']:
    m = np.ones(len(R), bool) if L == 'ΟΛΑ' else lg_ == L
    W(f'  {NAME.get(L, L):9s} {rm_(res, m):.2f} → {rm_(res - held, m):.2f} · κλεισιμο {rm_((R.act - R.mc).values, m):.2f}')
# ---- picks ----
Phi = NormalDist().cdf
def picks(adj):
    out = {}
    for rule, s, thr, mix in (('μοντελο ≥8%', 12.2, .08, False), ('μιξη ≥6%', 12.3, .06, True)):
        for when in ('op', 'cl'):
            U = []
            for r, a in zip(R.itertuples(), adj):
                mk = MK.get(r.i); L, o1, o2 = mk[when]; mm = mk['mo' if when == 'op' else 'mc']; mod = r.m + a
                if abs(mod - r.mo) >= 8: continue                          # ταβανι διαφωνιας (dom_bk_step2)
                mu = mm + .5 * (mod - mm) if mix else mod
                if abs(L - round(L)) < 1e-9: pw = Phi((mu + L - .5) / s); pl = Phi((-mu - L - .5) / s)
                else: pw = Phi((mu + L) / s); pl = 1 - pw
                pp = 1 - pw - pl; e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1; sd, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
                if e < thr: continue
                v = (r.act + L) * sd; U.append(((od - 1) if v > 0 else (0 if v == 0 else -1), r.y, r.lg))
            out[(rule, when)] = U
    return out
W(''); W('PICKS (ταβανι διαφωνιας 8): πριν → με γνωστες απουσιες')
A0, A1 = picks(np.zeros(len(R))), picks(held)
for k in A0:
    f = lambda U: f'{np.mean([u for u, _, _ in U])*100:+.1f}% ({len(U)}, {sum(u for u, _, _ in U):+.1f}μ, θετ {sum(1 for Y in EV if np.mean([u for u, y, _ in U if y == Y] or [0]) > 0)}/5)'
    W(f'  {k[0]:11s} {"ανοιγμα " if k[1] == "op" else "κλεισιμο"}: {f(A0[k])} → {f(A1[k])}')
    W('      ανα πρωταθλημα (με): ' + ' · '.join(f'{NAME[L][:4]} {np.mean([u for u, _, l in A1[k] if l == L] or [0])*100:+.0f}% ({sum(1 for _, _, l in A1[k] if l == L)})' for L in LGS))
pickle.dump(R.assign(held=held), open('dom_bk_known_abs_R.pkl', 'wb'))
open('dom_bk_known_abs_out.txt', 'w', encoding='utf-8').write('\n'.join(O))
