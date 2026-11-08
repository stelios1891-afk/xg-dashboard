"""euro_adj_by_mismatch.py — 9/10/2026 (Στελιος: «Ολυμπιακος vs Καιρατ και vs Ντορτμουντ — ποσο σωστα κανουμε το adjust;»).
Για καθε φετινη ευρωπαικη παρατηρηση (ομαδα × ματς): μετα τη διορθωση αντιπαλου πρεπει να ισουται ΚΑΤΑ ΜΕΣΟ ΟΡΟ με το rating της ομαδας
— σε ΚΑΘΕ τυπο ματς. Χωριζουμε κατα το τι περιμενε το μοντελο (υπεροχη λ_ομαδας − λ_αντιπαλου): μεγαλο φαβορι … μεγαλο αουτσαιντερ.
Μεροληψια = διορθωμενο − rating (γκολ/ματς· επιθεση: + = φαινεται καλυτερη απ' ο,τι ειναι· αμυνα: + = φαινεται χειροτερη).
Αν η διορθωση ειναι σωστη, ολοι οι καδοι ≈ 0. Επισης: πραγματικο xG vs λ μοντελου ανα καδο (το ιδιο το λαθος προβλεψης)."""
import sys, io, contextlib, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
g = {'__name__': 'mm'}
with contextlib.redirect_stdout(io.StringIO()):
    exec(open('euro_oppadj_test.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1), g)
G = g['g']; SS, rate_base, pred_one, EQ0, eq_B1 = g['SS'], g['rate_base'], g['pred_one'], g['EQ0'], g['eq_B1']
TOP7 = g['TOP7']
G['eq_obs'] = EQ0; G['_OBS'] = {}; G['USED'] = set()
g['predict_arm'](g['make_rate_new'](1.0, track=True))
KEYS = list(G['USED'])
REC = {}
for (sea, tid), lst in G['EU_BY_TEAM'].items():
    for rec in lst: REC[(tid, rec[0], sea)] = rec
rows = []
for (tid, mid, fold, lg, sea) in KEYS:
    rec = REC.get((tid, mid, fold))
    if rec is None: continue
    _, d, ish, xgf, xga, gf, ga, oid, comp = rec
    st = SS(tid, d)
    if st is None or st['lg'] != lg or st['sea'] != sea: continue
    p = pred_one(tid, oid, d, fold, comp, mid) if ish else pred_one(oid, tid, d, fold, comp, mid)
    if p is None: continue
    lf, la = (p[0], p[1]) if ish else (p[1], p[0])
    r = rate_base(st, tid, fold, d); ra, rd = r[0] * r[2], r[1] * r[3]
    G['_OBS'] = {}; o0 = EQ0(tid, rec, fold, lg, sea); G['_OBS'] = {}; o1 = eq_B1(tid, rec, fold, lg, sea)
    if o0 is None or o1 is None: continue
    so = SS(oid, d)
    rows.append(dict(sup=lf - la, top7=lg in TOP7, opp7=(so is not None and so['lg'] in TOP7), comp=comp, home=ish,
                     a0=o0[0] - ra, d0=o0[1] - rd, a1=o1[0] - ra, d1=o1[1] - rd, xf=xgf, xa=xga, lf=lf, la=la))
D = pd.DataFrame(rows)
BK = ((-9, -1.0, 'μεγαλο αουτσαιντερ (≤−1)'), (-1.0, -0.3, 'αουτσαιντερ'), (-0.3, 0.3, 'ισορροπημενο'), (0.3, 1.0, 'φαβορι'), (1.0, 9, 'μεγαλο φαβορι (≥+1)'))
def c(x): return f'{x.mean():+.3f}±{x.std() / math.sqrt(len(x)):.3f}'
print(f'παρατηρησεις: {len(D)}\n')
print(f'{"τι περιμενε το μοντελο":28s} {"n":>5s} | ΣΗΜΕΡΙΝΗ (V0) επιθ / αμυνα     | Β1 επιθ / αμυνα               | xG πραγμ − μοντελο: για / κατα')
for lo, hi, lab in BK:
    x = D[(D.sup > lo) & (D.sup <= hi)]
    print(f'{lab:28s} {len(x):5d} | {c(x.a0)} / {c(x.d0)} | {c(x.a1)} / {c(x.d1)} | {c(x.xf - x.lf)} / {c(x.xa - x.la)}')
print('\nχωριστα: ομαδα CORE7 vs ομαδα αλλης λιγκας (xG πραγμ − μοντελο: για / κατα)')
for t7 in (True, False):
    for lo, hi, lab in BK:
        x = D[(D.top7 == t7) & (D.sup > lo) & (D.sup <= hi)]
        if len(x) < 30: continue
        print(f'   {"CORE7" if t7 else "αλλη ":5s} {lab:28s} n{len(x):5d} · {c(x.xf - x.lf)} / {c(x.xa - x.la)} · Β1 επιθ {c(x.a1)} αμυνα {c(x.d1)}')
