"""ucl_timing_test.py — 10/10/2026 (Στελιος: «γιατι μπαινουμε 72ω στο Champions League; εχουμε τεστ χρονισμου;»).
Σημερινη αλυσιδα (base), σημερινοι κανονες UCL (φαβ ≥10% σωστα τεταρτα, dog ≥4% p_cover), FotMob+FotMob, 1.70-2.10, Crown & SBOBET (μεσος).
(Α) picks που βγαινουν σε καθε στιγμη (96/72/48/24/6ω, κλεισιμο) — ROI.
(Β) ΙΔΙΑ picks: οσα βγηκαν στις 72ω (και στις 24ω) — αν τα παιζαμε σε καθε μεταγενεστερη στιγμη (τιμη/γραμμη εκεινης της στιγμης): ROI
    + κινηση αγορας (υπεροχη απο τη γραμμη) υπερ/κατα μας μεχρι το κλεισιμο. Ανα φαβορι/αουτσαιντερ. Και UECL για συγκριση."""
import sys, io, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
t = open('uel_timing.py', encoding='utf-8').read(); t = t[:t.index('B = pd.DataFrame(rows)')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
t = t.replace('\nrows = []\nfor i, mid in enumerate(MIDS):', '\nrows = []\nfor i, mid in enumerate([]):')
u = {'__name__': 'ut'}
with contextlib.redirect_stdout(io.StringIO()): exec(t, u)
snap, sdist, cover_q, edge, picks = u['snap'], u['sdist'], u['cover_q'], u['edge'], u['picks']
MIDS, COMP, FM, GD, SEA, LH, LA = (u[k] for k in ('MIDS', 'COMP', 'FM', 'GD', 'SEA', 'LH_N', 'LA_N'))
HS = (96, 72, 48, 24, 6, 0)
def evalside(i, side, L, o, dist, ucl):
    ln = L if side == 1 else -L
    role = 'fav' if ln <= -0.5 else ('dog' if ln >= 0.5 else None)
    if role is None or not (1.70 <= o <= 2.10): return None
    pw, pp = cover_q(dist, side, ln) if role == 'fav' else picks.p_cover(dist, side, ln)
    e = edge(pw, pp, o); thr = (0.10 if role == 'fav' else 0.04) if ucl else (0.04 if role == 'fav' else 0.10)
    return dict(role=role, e=e, pick=e >= thr, pnl=picks.settle(GD[i], side, ln, o), ln=ln, o=o)
def mkt_sup(L, oh, oa, T):
    tq = (1 / oh) / (1 / oh + 1 / oa); lo, hi = -4.5, 4.5
    for _ in range(22):
        s = (lo + hi) / 2; d = picks.gd_dist(max((T + s) / 2, .05), max((T - s) / 2, .05)); w, p = picks.p_cover(d, 1, L)
        if w / max(1 - p, 1e-9) < tq: lo = s
        else: hi = s
    return (lo + hi) / 2
A, B = [], []
for comp in ('ChampionsLeague', 'ConferenceLeague'):
    for i, mid in enumerate(MIDS):
        if COMP[i] != comp or not FM[i]: continue
        dist = sdist(LH[i], LA[i]); ucl = comp == 'ChampionsLeague'
        for bk in ('Crown', 'SBOBET'):
            S = {h: snap(mid, bk, h) for h in HS}
            for h in HS:
                if not S[h]: continue
                L, oh, oa = S[h]
                for side, o in ((1, oh), (-1, oa)):
                    r = evalside(i, side, L, o, dist, ucl)
                    if r and r['pick']: A.append(dict(comp=comp, bk=bk, h=h, role=r['role'], sea=SEA[i], pnl=r['pnl']))
            for h0 in (72, 24):
                if not S[h0]: continue
                L0, oh0, oa0 = S[h0]
                for side, o0 in ((1, oh0), (-1, oa0)):
                    r0 = evalside(i, side, L0, o0, dist, ucl)
                    if not (r0 and r0['pick']): continue
                    T = LH[i] + LA[i]; m0 = mkt_sup(L0, oh0, oa0, T) * side
                    for h in [x for x in HS if x <= h0]:
                        if not S[h]: continue
                        L, oh, oa = S[h]; ln = L if side == 1 else -L; o = oh if side == 1 else oa
                        B.append(dict(comp=comp, bk=bk, h0=h0, h=h, role=r0['role'], sea=SEA[i], pnl=picks.settle(GD[i], side, ln, o),
                                      mv=m0 - mkt_sup(L, oh, oa, T) * side))
A, B = pd.DataFrame(A), pd.DataFrame(B)
def c(x):
    if len(x) == 0: return '—'
    m = x.groupby('bk').pnl.agg(['mean', 'size']); ps = x.groupby('sea').pnl.mean()
    return f'{m["size"].mean():4.0f} {100 * m["mean"].mean():+6.1f}% ({int((ps > 0).sum())}/{ps.size})'
lab = lambda h: 'κλεισ' if h == 0 else f'{h}ω'
for comp in ('ChampionsLeague', 'ConferenceLeague'):
    print(f'\n========== {comp} ==========')
    print('(Α) picks που βγαινουν σε καθε στιγμη (n picks · ROI · θετικες σεζον):')
    for role in ('fav', 'dog', None):
        x = A[(A.comp == comp) & ((A.role == role) if role else True)]
        print(f'   {"ΦΑΒΟΡΙ" if role == "fav" else ("ΑΟΥΤΣΑΙΝΤΕΡ" if role == "dog" else "ΟΛΑ"):12s} ' + ' · '.join(f'{lab(h)} {c(x[x.h == h])}' for h in HS))
    for h0 in (72, 24):
        print(f'(Β) ΙΔΙΑ picks που βγηκαν στις {h0}ω — ROI αν τα παιζαμε σε καθε στιγμη · κινηση αγορας ΠΡΟΣ τη δικη μας πλευρα ως εκεινη τη στιγμη (γκολ, + = η αγορα ηρθε προς εμας):')
        for role in ('fav', 'dog', None):
            x = B[(B.comp == comp) & (B.h0 == h0) & ((B.role == role) if role else True)]
            print(f'   {"ΦΑΒΟΡΙ" if role == "fav" else ("ΑΟΥΤΣΑΙΝΤΕΡ" if role == "dog" else "ΟΛΑ"):12s} ' + ' · '.join(f'{lab(h)} {c(x[x.h == h])} κιν {-x[x.h == h].mv.mean():+.2f}' for h in HS if h <= h0))
