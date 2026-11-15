# -*- coding: utf-8 -*-
"""ucl_early_disagree.py — CHAMPIONS LEAGUE: ΔΙΑΦΩΝΙΕΣ ΠΟΥ ΥΠΑΡΧΟΥΝ ΗΔΗ 4-7 ΜΕΡΕΣ ΠΡΙΝ (16/10/2026, Στελιος «μετρα ναι» — αφορμη:
πολλες διαφωνιες στις προβλεψεις UCL 20-22/10, ενω ολα τα τεστ ειναι ≤72ω).
Ιδια αλυσιδα/κανονες/αγορα με ucl_bb_timing (Crown & SBOBET, μεσος ορος 2 βιβλιων, FotMob+FotMob· over και με μια μη-FotMob ×1.22):
  ΦΑΒ ≥10% (σωστα τεταρτα) · DOG ≥4% (p_cover) · OVER ≥4% · UNDER ≥10% · 1.70-2.10 · |γραμμη| ≥0.5 στο χαντικαπ.
ΣΤΙΓΜΙΟΤΥΠΑ: 168ω (7 μερες) · 120ω (5) · 96ω (4) · 72ω · 48ω · 24ω · κλεισιμο. Σε καθε στιγμη: η τελευταια τιμη ≤ στιγμη (μονο αν η αγορα
ειχε ανοιξει). Αν ειναι pick: ROI στην τιμη της στιγμης · ROI της ιδιας πλευρας αν περιμενα τις 72ω και το κλεισιμο · % που ηταν ακομα pick
στις 72ω · κινηση αγορας στιγμη→κλεισιμο (γκολ, + = προς το pick). Συνολα: μονο νεα μορφη 2024-26· χαντικαπ: ολες οι σεζον + νεα μορφη.
ΠΕΡΙΓΡΑΦΙΚΟ (χωρις κανονα/κριση). ΠΡΟΣΟΧΗ: τα ratings του backtest ειναι «προ-αγωνα» (δεδομενα ως την ημερα του ματς) — 4-7 μερες πριν
το live μοντελο ξερει ΛΙΓΟΤΕΡΑ ματς (μπορει να λειπει 1 εγχωριο), αρα το backtest ειναι ελαφρως αισιοδοξο για τις νωρις στιγμες.
Εξοδος: ucl_early_disagree_out.txt"""
import sys, io, contextlib, pickle
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('ucl_bb_timing.py', encoding='utf-8').read()
src = src[:src.index('rows = []\n# 13/10')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
g = {'__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, g)
MIDS, COMP, FM, SEA, LH, LA, GD, GH, GA, KO, TRAJ, TOU = (g[k] for k in ('MIDS', 'COMP', 'FM', 'SEA', 'LH', 'LA', 'GD', 'GH', 'GA', 'KO', 'TRAJ', 'TOU'))
OH, OA, sdist, cover_q, edge, picks, ES, msup, mtot, settle_ou, THR = (g[k] for k in ('OH', 'OA', 'sdist', 'cover_q', 'edge', 'picks', 'ES', 'msup', 'mtot', 'settle_ou', 'THR'))
DRAW_SCALE = g['DRAW_SCALE']
_V = pickle.load(open('euro_v6_preds.pkl', 'rb')); _VI = {str(m): j for j, m in enumerate(_V['mids'])}
_LAB = {'shots': 'F', 'griffis': 'B', 'goals': 'G'}
def srcs(i):
    j = _VI.get(str(MIDS[i]))
    return (_LAB.get(_V['src_h'][j], '?'), _LAB.get(_V['src_a'][j], '?')) if j is not None else ('?', '?')
CPS = [168, 120, 96, 72, 48, 24, 0]
def at(seq, t):
    pre = [x for x in seq if x[0] <= t]
    return pre[-1] if pre else None
rows = []; cover = {}
for i, mid in enumerate(MIDS):
    if COMP[i] != 'ChampionsLeague': continue
    sh_, sa_ = srcs(i)
    nf1 = (not FM[i]) and ((sh_ == 'F') != (sa_ == 'F'))
    if not (FM[i] or nf1): continue
    ko = KO.get(mid)
    if not ko: continue
    newf = SEA[i] in ('2425', '2526')
    dist = sdist(LH[i], LA[i]); T = LH[i] + LA[i]; tot = GH[i] + GA[i]
    oh_, oa_ = OH[i], OA[i]
    if nf1:
        if sh_ == 'F': oh_ *= 1.22
        else: oa_ *= 1.22
    td = ES.tot_dist(oh_, oa_, DRAW_SCALE)
    for bk in ('Crown', 'SBOBET'):
        seq = [x for x in (TRAJ.get((mid, bk)) or []) if x[0] < ko] if FM[i] else []
        tseq = [x for x in (TOU.get((mid, bk)) or []) if x[0] < ko] if newf else []
        for h in CPS:
            t = ko - h * 3600 if h else ko - 60
            # ---- χαντικαπ ----
            x = at(seq, t) if seq else None
            if x is not None:
                cover[('AH', h, bk)] = cover.get(('AH', h, bk), 0) + 1
                x72 = at(seq, ko - 72 * 3600); cl = seq[-1]
                for side in (1, -1):
                    _, L, oh, oa = x; ln = L if side == 1 else -L; o = oh if side == 1 else oa
                    role = 'fav' if ln <= -0.5 else ('dog' if ln >= 0.5 else None)
                    if role is None or not (1.70 <= o <= 2.10): continue
                    pw, pp = cover_q(dist, side, ln) if role == 'fav' else picks.p_cover(dist, side, ln)
                    if edge(pw, pp, o) < THR[role]: continue
                    def st(y):
                        if y is None: return None, None
                        l2 = y[1] if side == 1 else -y[1]; o2 = y[2] if side == 1 else y[3]
                        return picks.settle(GD[i], side, l2, o2), (l2, o2)
                    p72, s72 = st(x72) if h > 72 else (None, None)
                    still = None
                    if s72:
                        r2 = 'fav' if s72[0] <= -0.5 else ('dog' if s72[0] >= 0.5 else None)
                        if r2 and 1.70 <= s72[1] <= 2.10:
                            a2, b2 = cover_q(dist, side, s72[0]) if r2 == 'fav' else picks.p_cover(dist, side, s72[0])
                            still = edge(a2, b2, s72[1]) >= THR[r2]
                        else:
                            still = False
                    rows.append(dict(mk=role, h=h, bk=bk, sea=SEA[i], newf=newf, mid=mid, pa=picks.settle(GD[i], side, ln, o),
                                     p72=p72, still=still, pc=st(cl)[0], mv=(msup(cl[1], cl[2], cl[3], T) - msup(L, oh, oa, T)) * side))
            # ---- συνολα (νεα μορφη) ----
            y = at(tseq, t) if tseq else None
            if y is not None:
                cover[('OU', h, bk)] = cover.get(('OU', h, bk), 0) + 1
                y72 = at(tseq, ko - 72 * 3600); cl = tseq[-1]
                for side in (('over', 'under') if FM[i] else ('over',)):
                    _, L, o, un = y; od = o if side == 'over' else un
                    if not (1.70 <= od <= 2.10): continue
                    po, pu = ES.p_over(td, L); pw_, pl_ = (po, pu) if side == 'over' else (pu, po)
                    if pw_ * (od - 1) * (1 - picks.MARGIN) - pl_ < THR[side]: continue
                    sg = 1 if side == 'over' else -1
                    def sto(z):
                        if z is None: return None
                        return settle_ou(tot, z[1], z[2] if side == 'over' else z[3], side == 'over')
                    still = None
                    if h > 72 and y72 is not None:
                        o72 = y72[2] if side == 'over' else y72[3]
                        if 1.70 <= o72 <= 2.10:
                            a2, b2 = ES.p_over(td, y72[1]); w2, l2 = (a2, b2) if side == 'over' else (b2, a2)
                            still = w2 * (o72 - 1) * (1 - picks.MARGIN) - l2 >= THR[side]
                        else:
                            still = False
                    rows.append(dict(mk=side, h=h, bk=bk, sea=SEA[i], newf=True, mid=mid, pa=settle_ou(tot, L, od, side == 'over'),
                                     p72=(sto(y72) if h > 72 else None), still=still, pc=sto(cl),
                                     mv=(mtot(cl[1], cl[2], cl[3]) - mtot(L, o, un)) * sg))
X = pd.DataFrame(rows)
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def cell(d, col):
    d = d[d[col].notna()]
    if not len(d): return '      —           '
    gb = d.groupby('bk')[col]; roi = gb.mean().mean(); n = gb.size().mean()
    ps = d.groupby('sea')[col].mean()
    return f'{100*roi:+6.1f}% ({n:3.0f}, {int((ps > 0).sum())}/{ps.size})'
LAB = {168: '7 μερες (168ω)', 120: '5 μερες (120ω)', 96: '4 μερες (96ω)', 72: '72ω', 48: '48ω', 24: '24ω', 0: 'κλεισιμο'}
P('CHAMPIONS LEAGUE · picks που υπαρχουν σε καθε στιγμη πριν τη σεντρα · μεσος Crown/SBOBET · κελι = ROI (picks ανα βιβλιο, θετικες σεζον)')
P('στηλες: ROI στην τιμη της στιγμης | αν περιμενα τις 72ω (ιδια πλευρα) | αν περιμενα το κλεισιμο | % ακομα pick στις 72ω | κινηση ως κλεισιμο (+ = προς εμας)')
P('ΚΑΛΥΨΗ αγορας (ματς με τιμη, ανα βιβλιο): ' + ' · '.join(f"{LAB[h]}: AH {np.mean([cover.get(('AH', h, b), 0) for b in ('Crown', 'SBOBET')]):.0f} / OU {np.mean([cover.get(('OU', h, b), 0) for b in ('Crown', 'SBOBET')]):.0f}" for h in CPS))
for mk, nm, flt in (('fav', 'ΦΑΒΟΡΙ ≥10% · ολες οι σεζον', None), ('fav', 'ΦΑΒΟΡΙ ≥10% · νεα μορφη', True), ('dog', 'ΑΟΥΤΣΑΪΝΤΕΡ ≥4% · ολες οι σεζον', None),
                    ('dog', 'ΑΟΥΤΣΑΪΝΤΕΡ ≥4% · νεα μορφη', True), ('over', 'OVER ≥4% · νεα μορφη', True), ('under', 'UNDER ≥10% · νεα μορφη', True)):
    P(''); P(f'=== {nm} ===')
    for h in CPS:
        d = X[(X.mk == mk) & (X.h == h)]
        if flt: d = d[d.newf]
        if not len(d): P(f'  {LAB[h]:15s} —'); continue
        stl = d.still.dropna().astype(float)
        P(f'  {LAB[h]:15s} {cell(d, "pa")} | 72ω {cell(d, "p72") if h > 72 else "        ·         "} | κλεισ {cell(d, "pc")} | '
          f'{(100*stl.mean() if len(stl) else float("nan")):4.0f}% | {d.mv.mean():+.2f}')
open('ucl_early_disagree_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
