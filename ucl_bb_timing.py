# -*- coding: utf-8 -*-
"""ucl_bb_timing.py — CHAMPIONS LEAGUE: ΤΑ ΙΔΙΑ ΤΕΣΤ ΧΡΟΝΙΣΜΟΥ ΜΕ ΤΗΝ ΕΥΡΩΛΙΓΚΑ (13/10/2026, Στελιος «θελω να κανεις τα ιδια τεστ που
καναμε και στο μπασκετ»). Προτυπα: el_fav_dog_timing / el_over_under_timing / el_over_late_test.
Σημερινη αλυσιδα & σημερινοι κανονες UCL, FotMob+FotMob, ζωνη αποδοσεων 1.70-2.10, εισοδος ≤72ω (live):
  ΦΑΒΟΡΙ ≥10% (σωστα τεταρτα) · ΑΟΥΤΣΑΪΝΤΕΡ ≥4% (p_cover) · |γραμμη| ≥0.5
  OVER ≥4% · UNDER ≥10% (μηχανη γκολ W2 πεναλτι 0.76 + κ 1.16 νεα μορφη, ισοπαλιες ×0.85 = live απο 10/10)
Crown & SBOBET (Nowgoal), ΚΑΘΕ αλλαγη τιμης απο τις 72ω ως τη σεντρα. ALERT = πρωτη στιγμη με edge ≥ κατωφλι (ανα ματς/αγορα/πλευρα).
Αποτελεσματα = ΜΕΣΟΣ ΟΡΟΣ των 2 βιβλιων. Σεζον 2223-2526 (4)· νεα μορφη = 2425-2526.
1. ΙΔΙΟ PICK: τιμη ALERT vs τιμη ΚΛΕΙΣΙΜΑΤΟΣ (ακομα κι αν στο κλεισιμο δεν ηταν πια pick).
2. ΑΝΑ ΩΡΑ ALERT: 48-72 / 24-48 / 12-24 / 6-12 / 2-6 / <2ω.
3. ΑΝΑ ΜΠΛΟΚ ΑΓΩΝΙΣΤΙΚΩΝ: ομιλοι/League Phase 1-3, 4-6, 7-8 (νεα), playoff, νοκ-αουτ.
4. ΚΑΝΟΝΑΣ «ΚΙΝΗΣΗ ΚΟΝΤΡΑ» (αναλογο move15 μπασκετ) — ΠΡΟ-ΔΗΛΩΜΕΝΟΣ: αν η αγορα (δικαιη υπεροχη / δικαιο συνολο σε γκολ)
   κινηθηκε ≥0.25 γκολ ΚΟΝΤΡΑ απο την πρωτη τιμη (72ω) ως το alert ΚΑΙ η κινηση ξεπερασε το 0.25 ≥6ω πριν τη σεντρα → καταγραφη.
5. ΚΑΝΟΝΑΣ «ΑΡΓΑ» (αναλογο late2h / late-over) — ΠΡΟ-ΔΗΛΩΜΕΝΟΣ: pick που πρωτοεμφανιζεται < Χ ωρες (οχι στις 72ω) → καταγραφη. ΚΥΡΙΟ Χ=6.
ΚΡΙΣΗ (ιδια με el_over_late_test, ανα αγορα, και για τους 2 κανονες): ΠΕΡΝΑ αν ΟΛΑ:
  (1) τα κομμενα: ROI < 0 ΚΑΙ χειροτερα απο οσα μενουν, στην τιμη του alert ΚΑΙ στο κλεισιμο,
  (2) χειροτερα απο οσα μενουν σε ≥3/4 σεζον (σεζον με ≥3 κομμενα),
  (3) ιδια φορα στα γειτονικα ορια (κοντρα 0.15 & 0.35 · Χ = 4 & 8),
  (4) οι μοναδες με τον κανονα ≥ χωρις,
  (5) ΚΑΙ στα 2 βιβλια χωριστα τα κομμενα χειροτερα (βλ. «μονο ενα αριθμο ανα αποτελεσμα» — σημειωνεται αν διαφωνουν).
Εξοδος: ucl_bb_timing_out.txt · ucl_bb_timing_alerts.pkl"""
import sys, io, os, json, glob, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
t = open('uel_timing.py', encoding='utf-8').read(); t = t[:t.index('B = pd.DataFrame(rows)')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
t = t.replace('\nrows = []\nfor i, mid in enumerate(MIDS):', '\nrows = []\nfor i, mid in enumerate([]):')
u = {'__name__': 'ut'}
with contextlib.redirect_stdout(io.StringIO()): exec(t, u)
sdist, cover_q, edge, picks, KO, TRAJ = u['sdist'], u['cover_q'], u['edge'], u['picks'], u['KO'], u['TRAJ']
MIDS, COMP, FM, GD, SEA, LH, LA = (u[k] for k in ('MIDS', 'COMP', 'FM', 'GD', 'SEA', 'LH_N', 'LA_N'))
COMP, SEA = np.asarray(COMP), np.asarray(SEA)
os.environ['W2_IN'] = 'euro_v6w2_preds_pen76.pkl'
b = open('uel_battery.py', encoding='utf-8').read(); b = b[:b.index('P0 = make_picks')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
w = {'__name__': 'w2'}
with contextlib.redirect_stdout(io.StringIO()): exec(b, w)
assert list(w['MIDS']) == list(MIDS)
GH, GA, RND = np.asarray(w['GH']), np.asarray(w['GA']), w['RND']
OH, OA = np.asarray(w['g']['LH2'], float).copy(), np.asarray(w['g']['LA2'], float).copy()
ucl = COMP == 'ChampionsLeague'; newf = np.isin(SEA, ['2425', '2526']); fh = OH >= OA
OH = np.where(ucl & newf & fh, OH * 1.16, OH); OA = np.where(ucl & newf & ~fh, OA * 1.16, OA)
import euro_shadow_scan as ES
DRAW_SCALE = 0.85
THR = dict(fav=0.10, dog=0.04, over=0.04, under=0.10)
def pl(gs):
    try:
        p = [float(x) for x in str(gs).split('/')]
        if len(p) == 2 and p[0] < 0: p[1] = -abs(p[1])
        return sum(p) / len(p)
    except Exception:
        return None
TOU = {}
for f in glob.glob('nowgoal_odds/*_UCL.jsonl'):
    for line in open(f, encoding='utf-8'):
        r = json.loads(line); bk = {3: 'Crown', 31: 'SBOBET'}.get(r['cid'])
        if bk is None: continue
        seq = sorted((int(mt), pl(gg), float(o) + 1, float(un) + 1) for mt, o, gg, un in (r.get('ou') or []) if mt and pl(gg) is not None)
        if seq: TOU[(str(r['mid']), bk)] = seq
def window(seq, ko):
    """καταστασεις απο τις 72ω (τελευταια εγγραφη ≤ KO−72ω, οχι παλιοτερη απο 96ω, ή η πρωτη μεταγενεστερη) ως τη σεντρα + κλεισιμο."""
    if not seq or not ko: return None, None
    st = ko - 72 * 3600
    pre = [x for x in seq if x[0] <= st]
    first = pre[-1] if pre and st - pre[-1][0] <= 24 * 3600 else None
    body = [x for x in seq if st < x[0] < ko]
    ser = ([(st,) + tuple(first[1:])] if first else []) + body
    cl = [x for x in seq if x[0] <= ko + 900]
    return ser, (cl[-1] if cl else None)
def settle_ou(tot, L, o, over):
    parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]; r = 0.0
    for p in parts:
        d = (tot - p) if over else (p - tot); r += ((o - 1) if d > 0 else (0 if d == 0 else -1)) / len(parts)
    return r
_ms = {}
def msup(L, oh, oa, T):
    k = (L, oh, oa, round(T, 2))
    if k in _ms: return _ms[k]
    tq = (1 / oh) / (1 / oh + 1 / oa); lo, hi = -4.5, 4.5
    for _ in range(20):
        s = (lo + hi) / 2; d = picks.gd_dist(max((T + s) / 2, .05), max((T - s) / 2, .05)); w_, p = picks.p_cover(d, 1, L)
        if w_ / max(1 - p, 1e-9) < tq: lo = s
        else: hi = s
    _ms[k] = (lo + hi) / 2; return _ms[k]
_mt = {}
def mtot(L, o, un):
    k = (L, o, un)
    if k in _mt: return _mt[k]
    q = (1 / o) / (1 / o + 1 / un); lo, hi = 0.5, 7.0
    for _ in range(20):
        T = (lo + hi) / 2; po, pu = ES.p_over(ES.tot_dist(T / 2, T / 2), L)
        if po / max(po + pu, 1e-9) < q: lo = T
        else: hi = T
    _mt[k] = (lo + hi) / 2; return _mt[k]
def block(mid, sea):
    r = str(RND.get(mid) or '')
    if r.isdigit():
        n = int(r); return '1-3' if n <= 3 else ('4-6' if n <= 6 else '7-8')
    return 'playoff' if r == 'playoff' else 'νοκ-αουτ'
rows = []
# 13/10 (Στελιος «τα over δεν ειναι αρνητικα, ψαξε τον κανονα που τρεχει live»): LIVE over UCL = ΚΑΙ ματς με ΜΙΑ ομαδα χωρις FotMob
# (Ben ή γκολ+Elo), με την ομαδα FotMob ×1.22 στο ζευγος συνολων (UCL_NONFM_OU_SCALE, ucl_nonfm_fix2_test) — μονο OVER, οχι χαντικαπ/under.
import pickle as _pk
_V = _pk.load(open('euro_v6_preds.pkl', 'rb')); _VI = {str(m): j for j, m in enumerate(_V['mids'])}
_LAB = {'shots': 'F', 'griffis': 'B', 'goals': 'G'}
def srcs(i):
    j = _VI.get(str(MIDS[i]))
    return (_LAB.get(_V['src_h'][j], '?'), _LAB.get(_V['src_a'][j], '?')) if j is not None else ('?', '?')
for i, mid in enumerate(MIDS):
    if not ucl[i]: continue
    sh_, sa_ = srcs(i)
    nf1 = (not FM[i]) and ((sh_ == 'F') != (sa_ == 'F'))
    if not (FM[i] or nf1): continue
    cat = 'FF' if FM[i] else 'NF1'
    ko = KO.get(mid)
    if not ko: continue
    dist = sdist(LH[i], LA[i]); T = LH[i] + LA[i]; tot = GH[i] + GA[i]
    oh_, oa_ = OH[i], OA[i]
    if nf1:
        if sh_ == 'F': oh_ = oh_ * 1.22
        else: oa_ = oa_ * 1.22
    td = ES.tot_dist(oh_, oa_, DRAW_SCALE)
    for bk in ('Crown', 'SBOBET'):
        # ---- χαντικαπ ----
        ser, cl = window(TRAJ.get((mid, bk)), ko) if cat == 'FF' else (None, None)
        if ser and cl:
            for side in (1, -1):
                for k_, (mt_, L, oh, oa) in enumerate(ser):
                    ln = L if side == 1 else -L; o = oh if side == 1 else oa
                    role = 'fav' if ln <= -0.5 else ('dog' if ln >= 0.5 else None)
                    if role is None or not (1.70 <= o <= 2.10): continue
                    pw, pp = cover_q(dist, side, ln) if role == 'fav' else picks.p_cover(dist, side, ln)
                    if edge(pw, pp, o) < THR[role]: continue
                    p0 = msup(ser[0][1], ser[0][2], ser[0][3], T) * side
                    pa = msup(L, oh, oa, T) * side
                    hx = None
                    if pa - p0 <= -0.15:                       # χρονος που η κινηση ξεπερασε καθε οριο
                        hx = {}
                        for x in ser[:k_ + 1]:
                            d = msup(x[1], x[2], x[3], T) * side - p0
                            for th in (0.15, 0.25, 0.35):
                                if d <= -th and th not in hx: hx[th] = (ko - x[0]) / 3600
                    lc = cl[1] if side == 1 else -cl[1]; oc = cl[2] if side == 1 else cl[3]
                    rows.append(dict(i=i, mid=mid, bk=bk, mk=role, cat=cat, sea=SEA[i], blk=block(mid, SEA[i]), hrs=(ko - mt_) / 3600, at_open=(k_ == 0),
                                     ln=ln, o=o, lc=lc, oc=oc, mv=pa - p0, hx=hx, mv_after=msup(cl[1], cl[2], cl[3], T) * side - pa,
                                     pa=picks.settle(GD[i], side, ln, o), pc=picks.settle(GD[i], side, lc, oc)))
                    break
        # ---- συνολα ----
        ser, cl = window(TOU.get((mid, bk)), ko)
        if ser and cl:
            for side in (('over', 'under') if cat == 'FF' else ('over',)):
                for k_, (mt_, L, o, un) in enumerate(ser):
                    od = o if side == 'over' else un
                    if not (1.70 <= od <= 2.10): continue
                    po, pu = ES.p_over(td, L)
                    pw_, pl_ = (po, pu) if side == 'over' else (pu, po)
                    if pw_ * (od - 1) * (1 - picks.MARGIN) - pl_ < THR[side]: continue
                    sg = 1 if side == 'over' else -1
                    p0 = mtot(ser[0][1], ser[0][2], ser[0][3]) * sg; pa = mtot(L, o, un) * sg
                    mv = pa - p0                                   # + = η αγορα ηρθε προς εμας (over: ανεβασε γκολ), − = κοντρα
                    hx = None
                    if mv <= -0.15:
                        hx = {}
                        for x in ser[:k_ + 1]:
                            d = mtot(x[1], x[2], x[3]) * sg - p0
                            for th in (0.15, 0.25, 0.35):
                                if d <= -th and th not in hx: hx[th] = (ko - x[0]) / 3600
                    oc = cl[2] if side == 'over' else cl[3]
                    rows.append(dict(i=i, mid=mid, bk=bk, mk=side, cat=cat, sea=SEA[i], blk=block(mid, SEA[i]), hrs=(ko - mt_) / 3600, at_open=(k_ == 0),
                                     ln=L, o=od, lc=cl[1], oc=oc, mv=mv, hx=hx, mv_after=mtot(cl[1], cl[2], cl[3]) * sg - pa,
                                     pa=settle_ou(tot, L, od, side == 'over'), pc=settle_ou(tot, cl[1], oc, side == 'over')))
                    break
X = pd.DataFrame(rows)
X.to_pickle('ucl_bb_timing_alerts.pkl')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
NAME = dict(fav='ΦΑΒΟΡΙ', dog='ΑΟΥΤΣΑΪΝΤΕΡ', over='OVER', under='UNDER')
def cell(d, col='pa'):
    """μεσος ορος 2 βιβλιων: ROI · picks (ανα βιβλιο) · μοναδες · θετικες σεζον."""
    if not len(d): return '—'
    g = d.groupby('bk')[col]; roi = g.mean().mean(); n = g.size().mean(); un = g.sum().mean()
    ps = d.groupby('sea')[col].mean()
    return f'{100*roi:+6.1f}% ({n:.0f}, {un:+5.1f}μ, {int((ps > 0).sum())}/{ps.size})'
def books(d, col='pa'):
    g = d.groupby('bk')[col].mean()
    return ' '.join(f'{b[0]} {100*v:+.0f}' for b, v in g.items())
def report(Y, label, need):
    """Y = υποσυνολο alerts · need = ποσες σεζον πρεπει να ειναι χειροτερα τα κομμενα (κριτηριο 2)."""
    P(''); P('#' * 100); P(f'### {label}'); P('#' * 100)
    P(f'alerts ≤72ω (ανα βιβλιο): ' + ' · '.join(f'{NAME[m]} {Y[Y.mk == m].groupby("bk").size().mean():.0f}' for m in NAME)
      + f' (over: FotMob+FotMob {Y[(Y.mk == "over") & (Y.cat == "FF")].groupby("bk").size().mean():.0f} + μια χωρις FotMob '
      + f'{Y[(Y.mk == "over") & (Y.cat == "NF1")].groupby("bk").size().mean():.0f})')
    for title, mks in (('ΧΑΝΤΙΚΑΠ', ('fav', 'dog')), ('ΣΥΝΟΛΑ', ('over', 'under'))):
        P(''); P(f'=== {title} · 1. ΙΔΙΟ PICK: τιμη ALERT vs τιμη ΚΛΕΙΣΙΜΑΤΟΣ ===')
        P('  ρολος                 · στο ALERT                    · στο ΚΛΕΙΣΙΜΟ                 · διαφορα · αποδοση · γραμμη ιδια/καλυτερη/χειροτερη · κινηση μετα (+ προς εμας)')
        rowsets = [(NAME[m], Y[Y.mk == m], m) for m in mks]
        if 'over' in mks:
            rowsets.insert(1, ('  └ FotMob+FotMob', Y[(Y.mk == 'over') & (Y.cat == 'FF')], 'over'))
            rowsets.insert(2, ('  └ μια χωρις FotMob', Y[(Y.mk == 'over') & (Y.cat == 'NF1')], 'over'))
        for nm, d, m in rowsets:
            if not len(d): continue
            if m == 'over':    better = d.lc < d.ln - 1e-9; worse = d.lc > d.ln + 1e-9
            elif m == 'under': better = d.lc > d.ln + 1e-9; worse = d.lc < d.ln - 1e-9
            else:              better = d.lc > d.ln + 1e-9; worse = d.lc < d.ln - 1e-9
            same = ~better & ~worse
            du = (d.groupby('bk').pc.sum().mean() - d.groupby('bk').pa.sum().mean())
            P(f'  {nm:<21}· {cell(d):<28} · {cell(d, "pc"):<28} · {du:+5.1f}μ · {d.o.mean():.2f}→{d.oc.mean():.2f} · '
              f'{100*same.mean():.0f}%/{100*better.mean():.0f}%/{100*worse.mean():.0f}% · {d.mv_after.mean():+.2f}  [alert {books(d)} | κλεισ {books(d, "pc")}]')
        P(''); P(f'=== {title} · 2. ΑΝΑ ΩΡΑ ΤΟΥ ALERT (πρωτη εμφανιση) — alert | κλεισιμο ===')
        for lo, hi in ((48, 73), (24, 48), (12, 24), (6, 12), (2, 6), (0, 2)):
            P(f'  {lo:2d}-{min(hi, 72):2d}ω  ' + '   ·   '.join(
                f'{NAME[m][:5]}: {cell(d)} | {cell(d, "pc")}' for m in mks for d in [Y[(Y.mk == m) & (Y.hrs >= lo) & (Y.hrs < hi)]]))
        P(''); P(f'=== {title} · 3. ΑΝΑ ΜΠΛΟΚ ΑΓΩΝΙΣΤΙΚΩΝ — alert | κλεισιμο ===')
        for bl in ('1-3', '4-6', '7-8', 'playoff', 'νοκ-αουτ'):
            P(f'  {bl:<9}' + '   ·   '.join(f'{NAME[m][:5]}: {cell(d)} | {cell(d, "pc")}' for m in mks for d in [Y[(Y.mk == m) & (Y.blk == bl)]]))
    SE = sorted(Y.sea.unique())
    def judge(m, cutf, lab, main, neigh):
        d = Y[Y.mk == m]; res = {}
        for k in [main] + list(neigh):
            cut = d[cutf(d, k)] if len(d) else d; keep = d.drop(cut.index)
            ys = [s for s in SE if (cut.sea == s).sum() / 2 >= 3]
            worse = sum(1 for s in ys if cut[cut.sea == s].pa.mean() < keep[keep.sea == s].pa.mean())
            bw = all(cut[cut.bk == b].pa.mean() < keep[keep.bk == b].pa.mean() for b in ('Crown', 'SBOBET') if (cut.bk == b).any())
            res[k] = dict(cut=cut, keep=keep, worse=worse, ny=len(ys), bw=bw,
                          u0=d.groupby('bk').pa.sum().mean(), u1=keep.groupby('bk').pa.sum().mean() if len(keep) else 0.0)
            P(f'  {lab}={k}: κοβει alert {cell(cut)} · κλεισ. {cell(cut, "pc")} | μενουν alert {cell(keep)} · κλεισ. {cell(keep, "pc")} | '
              f'χειροτερα σε {worse}/{len(ys)} σεζον · βιβλια {"✓" if bw else "✗"} ({books(cut) if len(cut) else "—"}) · μοναδες {res[k]["u0"]:+.1f} → {res[k]["u1"]:+.1f}')
        r = res[main]; c, k_ = r['cut'], r['keep']
        if not len(c):
            P('  ΚΡΙΣΗ: κανενα κομμενο → ΔΕΝ ΠΕΡΝΑ'); return
        c1 = c.pa.mean() < 0 and c.pc.mean() < 0 and c.pa.mean() < k_.pa.mean() and c.pc.mean() < k_.pc.mean()
        c2 = r['worse'] >= need
        c3 = all(len(res[x]['cut']) and res[x]['cut'].pa.mean() < res[x]['keep'].pa.mean() for x in neigh)
        c4 = r['u1'] >= r['u0']; c5 = r['bw']
        ok = c1 and c2 and c3 and c4 and c5
        P(f'  ΚΡΙΣΗ: (1) <0 & χειροτερα alert+κλεισ {"✓" if c1 else "✗"} · (2) {r["worse"]}/{r["ny"]} σεζον (χρειαζεται ≥{need}) {"✓" if c2 else "✗"} · (3) γειτονικα {"✓" if c3 else "✗"} · '
          f'(4) μοναδες {"✓" if c4 else "✗"} · (5) 2 βιβλια {"✓" if c5 else "✗"} → {"ΠΕΡΝΑ" if ok else "ΔΕΝ ΠΕΡΝΑ"}')
    def cut_move(d, th):
        return d.apply(lambda r: isinstance(r.hx, dict) and th in r.hx and r.hx[th] >= 6, axis=1)
    def cut_late(d, h):
        return (d.hrs < h) & ~d.at_open
    P(''); P('=== 4. ΚΑΝΟΝΑΣ «ΚΙΝΗΣΗ ΚΟΝΤΡΑ»: αγορα ≥θ γκολ κοντρα απο τις 72ω ως το alert, ξεπερασμενο ≥6ω πριν → καταγραφη (κυριο θ=0.25) ===')
    for m in NAME:
        P(f' {NAME[m]}:'); judge(m, cut_move, 'θ', 0.25, (0.15, 0.35))
    P(''); P('=== 5. ΚΑΝΟΝΑΣ «ΑΡΓΑ»: πρωτη εμφανιση < Χ ωρες πριν (οχι στις 72ω) → καταγραφη (κυριο Χ=6) ===')
    for m in NAME:
        P(f' {NAME[m]}:'); judge(m, cut_late, 'Χ', 6, (4, 8))
    P(''); P('(αναφορα) ΤΕΛΕΥΤΑΙΕΣ 2 ΩΡΕΣ (πρωτη εμφανιση <2ω): ' + ' · '.join(f'{NAME[m]} {cell(Y[(Y.mk == m) & (Y.hrs < 2)])}' for m in NAME))
    P('(αναφορα) κινηση κοντρα ≥0.25 που εγινε <6ω πριν: ' + ' · '.join(
        f'{NAME[m]} {cell(Y[(Y.mk == m) & Y.apply(lambda r: isinstance(r.hx, dict) and 0.25 in r.hx and r.hx[0.25] < 6, axis=1)])}' for m in NAME))
P('CHAMPIONS LEAGUE · σημερινοι κανονες · μεσος Crown/SBOBET · (ROI (picks ανα βιβλιο, μοναδες, θετικες σεζον))')
P('ΣΗΜ.: ο live κανονας των ΣΥΝΟΛΩΝ (κ, κατωφλια over 4% / under 10%, over και με μια ομαδα χωρις FotMob ×1.22) κριθηκε στη ΝΕΑ ΜΟΡΦΗ 2024-26·')
P('      η παλια μορφη (2022-24) ειναι μονο πλαισιο. Το χαντικαπ κρινεται σε ολες τις σεζον.')
report(X[X.sea.isin(['2425', '2526'])], 'ΝΕΑ ΜΟΡΦΗ 2024-26 — ΒΑΣΗ ΓΙΑ ΤΑ ΣΥΝΟΛΑ (κριτηριο 2: χειροτερα και στις 2 σεζον)', 2)
report(X, 'ΟΛΕΣ ΟΙ ΣΕΖΟΝ 2022-26 — ΒΑΣΗ ΓΙΑ ΤΟ ΧΑΝΤΙΚΑΠ (κριτηριο 2: ≥3 σεζον)· συνολα εδω = πλαισιο', 3)
open('ucl_bb_timing_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
