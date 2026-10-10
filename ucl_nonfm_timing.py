"""ucl_nonfm_timing.py — 10/10/2026 (Στελιος: «περνα τη διορθωση στα over, και θελω να τρεξεις το τεστ χρονισμου και σε αυτα»).
OVER σε UCL ματς με μια ομαδα χωρις FotMob, ΜΕ τη διορθωση συνολων (ομαδα FotMob ×(1+δ), δ LOSO ανα σεζον — ucl_nonfm_fix2_test), ≥4%, 1.70-2.10,
πρωτη εμφανιση ≤72ω, μεσος Crown/SBOBET. Ανα παραθυρο εμφανισης: ROI στην εμφανιση vs αν περιμενα το κλεισιμο, κινηση αγορας (συνολο γκολ) πριν/μετα,
τελευταιες 8ω και κοντρα. Ιδια μορφη με ucl_unders_timing / ucl_overs_timing_newfmt.
"""
import sys, io, os, json, glob, contextlib
DRAW_SCALE = 0.85
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
t = open('uel_timing.py', encoding='utf-8').read(); t = t[:t.index('B = pd.DataFrame(rows)')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
t = t.replace('\nrows = []\nfor i, mid in enumerate(MIDS):', '\nrows = []\nfor i, mid in enumerate([]):')
u = {'__name__': 'ut'}
with contextlib.redirect_stdout(io.StringIO()): exec(t, u)
picks, KO = u['picks'], u['KO']
MIDS, COMP, FM, SEA = u['MIDS'], np.asarray(u['COMP']), u['FM'], np.asarray(u['SEA'])
os.environ['W2_IN'] = 'euro_v6w2_preds_pen76.pkl'
b = open('uel_battery.py', encoding='utf-8').read(); b = b[:b.index('P0 = make_picks')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
w = {'__name__': 'w2'}
with contextlib.redirect_stdout(io.StringIO()): exec(b, w)
assert list(w['MIDS']) == list(MIDS)
GH, GA = np.asarray(w['GH']), np.asarray(w['GA'])
OH, OA = np.asarray(w['g']['LH2'], float).copy(), np.asarray(w['g']['LA2'], float).copy()
ucl = COMP == 'ChampionsLeague'; newf = np.isin(SEA, ['2425', '2526']); fh = OH >= OA
OH = np.where(ucl & newf & fh, OH * 1.16, OH); OA = np.where(ucl & newf & ~fh, OA * 1.16, OA)
import euro_shadow_scan as ES
def pl(gs):
    try:
        p = [float(x) for x in str(gs).split('/')]
        if len(p) == 2 and p[0] < 0: p[1] = -abs(p[1])
        return sum(p) / len(p)
    except Exception:
        return None
TOU = {}
for f in glob.glob('nowgoal_odds/*_U*.jsonl'):
    for line in open(f, encoding='utf-8'):
        r = json.loads(line); bk = {3: 'Crown', 31: 'SBOBET'}.get(r['cid'])
        if bk is None: continue
        seq = sorted((int(mt), pl(gg), float(o) + 1, float(un) + 1) for mt, o, gg, un in (r.get('ou') or []) if mt and pl(gg) is not None)
        if seq: TOU[(str(r['mid']), bk)] = seq
def snap_ou(mid, bk, h):
    ko = KO.get(mid); seq = TOU.get((mid, bk))
    if not ko or not seq: return None
    cut = ko - h * 3600 if h else ko + 900
    prev = [x for x in seq if x[0] <= cut]
    if not prev or (h and (ko - prev[-1][0]) / 3600 > h + 24): return None
    return prev[-1][1:]
def settle(tot, L, o, over):
    parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]; r = 0.0
    for p in parts:
        d = (tot - p) if over else (p - tot); r += ((o - 1) if d > 0 else (0 if d == 0 else -1)) / len(parts)
    return r
def mtot(L, o, un):
    q = (1 / o) / (1 / o + 1 / un); lo, hi = 0.5, 7.0
    for _ in range(22):
        T = (lo + hi) / 2; po, pu = ES.p_over(ES.tot_dist(T / 2, T / 2), L)
        if po / max(po + pu, 1e-9) < q: lo = T
        else: hi = T
    return (lo + hi) / 2
import pickle as _pk
_V = _pk.load(open('euro_v6_preds.pkl', 'rb')); _VI = {str(m): j for j, m in enumerate(_V['mids'])}
_LAB = {'shots': 'F', 'griffis': 'B', 'goals': 'G'}
def _cat(i):
    j = _VI.get(str(MIDS[i]))
    if j is None: return '?'
    a, b = sorted((_LAB.get(_V['src_h'][j], '?'), _LAB.get(_V['src_a'][j], '?')))
    return a + b
SRCC = [_cat(i) for i in range(len(MIDS))]

LH_N, LA_N, sdist, cover_q, edge, snap_ah, GD = (u[k] for k in ('LH_N', 'LA_N', 'sdist', 'cover_q', 'edge', 'snap', 'GD'))
LH_N = np.asarray(LH_N, float); LA_N = np.asarray(LA_N, float); GD = np.asarray(GD, float)
SEAS = ('2223', '2324', '2425', '2526')
def srcs(i):
    j = _VI.get(str(MIDS[i]))
    return (_LAB.get(_V['src_h'][j], '?'), _LAB.get(_V['src_a'][j], '?')) if j is not None else ('?', '?')
U = []; FMH = {}; NFS = {}
for i in np.where(ucl)[0]:
    sh, sa = srcs(i)
    if (sh == 'F') != (sa == 'F'):                 # ακριβως μια μη-FotMob
        U.append(i); FMH[i] = sh == 'F'; NFS[i] = sa if sh == 'F' else sh
U = np.array(U)
FH = np.array([FMH[i] for i in U]); NS = np.array([NFS[i] for i in U])
print(f'UCL ματς με μια ομαδα χωρις FotMob: {len(U)} (Ben {int((NS == "B").sum())} · γκολ+Elo {int((NS == "G").sum())}) · ανα σεζον ' +
      ' '.join(f'{s}:{int((SEA[U] == s).sum())}' for s in SEAS))
def pairs(delta, idx):
    fh = np.array([FMH[i] for i in idx]); m = 1 + delta
    ah_h = np.where(fh, LH_N[idx] * m, LH_N[idx]); ah_a = np.where(fh, LA_N[idx], LA_N[idx] * m)
    ou_h = np.where(fh, OH[idx] * m, OH[idx]); ou_a = np.where(fh, OA[idx], OA[idx] * m)
    return ah_h, ah_a, ou_h, ou_a
from math import lgamma
LGF = {i: lgamma(GH[i] + 1) + lgamma(GA[i] + 1) for i in U}
def ll(delta, idx):
    a, b, c, d = pairs(delta, idx); gh = GH[idx]; ga = GA[idx]
    k = np.array([LGF[i] for i in idx])
    return ((gh * np.log(a) - a + ga * np.log(b) - b - k).sum() + (gh * np.log(c) - c + ga * np.log(d) - d - k).sum()) / 2
# ---- αγορα (snapshots, ανεξαρτητα απο δ) ----
HS = (72, 60, 48, 36, 24, 18, 12, 8, 6, 4, 2, 1, 0)
SA, SO = [], []
for i in U:
    mid = MIDS[i]
    for bk in ('Crown', 'SBOBET'):
        for h in HS:
            a = snap_ah(mid, bk, h)
            if a: SA.append((i, bk, h) + tuple(a))
            o = snap_ou(mid, bk, h)
            if o: SO.append((i, bk, h) + tuple(o))
def make_picks(lam_ah, lam_ou, fav_thr=0.10):
    rows = []
    D = {i: sdist(*lam_ah[i]) for i in lam_ah}
    for (i, bk, h, L, oh, oa) in SA:
        if i not in D: continue
        for side, ln, o in ((1, L, oh), (-1, -L, oa)):
            if not (1.70 <= o <= 2.10) or abs(ln) < 0.5: continue
            role = 'fav' if ln < 0 else 'dog'
            pw, pp = cover_q(D[i], side, ln) if role == 'fav' else picks.p_cover(D[i], side, ln)
            e = edge(pw, pp, o)
            if e >= (fav_thr if role == 'fav' else 0.04):
                big = (side == 1) == FMH[i]
                rows.append(dict(i=i, bk=bk, h=h, mkt='AH', side=role + ('_big' if big else '_small'), sea=SEA[i], ns=NFS[i], e=e, od=o,
                                 pnl=picks.settle(GD[i], side, ln, o)))
    T = {i: ES.tot_dist(lam_ou[i][0], lam_ou[i][1], DRAW_SCALE) for i in lam_ou}
    for (i, bk, h, L, o, un) in SO:
        if i not in T: continue
        po, pu = ES.p_over(T[i], L); tot = GH[i] + GA[i]
        for side, od, pw, pl in (('over', o, po, pu), ('under', un, pu, po)):
            if not (1.70 <= od <= 2.10): continue
            e = pw * (od - 1) * (1 - picks.MARGIN) - pl
            if e >= (.04 if side == 'over' else .10):
                rows.append(dict(i=i, bk=bk, h=h, mkt='OU', side=side, sea=SEA[i], ns=NFS[i], e=e, od=od, pnl=settle(tot, L, od, side == 'over')))
    P = pd.DataFrame(rows)
    if len(P) == 0: return pd.DataFrame(columns=['i', 'bk', 'h', 'mkt', 'side', 'sea', 'ns', 'e', 'od', 'pnl'])
    P = P.sort_values('h', ascending=False)
    ah = P[P.mkt == 'AH'].groupby(['i', 'bk', 'side']).head(1)
    ou = P[P.mkt == 'OU'].groupby(['i', 'bk', 'side']).head(1).sort_values('h', ascending=False).groupby(['i', 'bk']).head(1)
    return pd.concat([ah, ou])
def cc(x):
    if len(x) == 0: return '   — '
    m = x.groupby('bk').pnl.mean(); n = x.groupby('bk').size().mean(); ps = x.groupby('sea').pnl.mean()
    return (f'{n:4.0f} picks {100 * m.mean():+6.1f}% [C {100 * m.get("Crown", np.nan):+.0f} / S {100 * m.get("SBOBET", np.nan):+.0f}] '
            f'μοναδες {m.mean() * n:+5.1f} (' + ' '.join(f'{s[2:]} {100 * v:+.0f}' for s, v in ps.items()) + ')')
def units(x): return x.groupby('bk').pnl.sum().mean() if len(x) else 0.0
NL = chr(10)
# ================= Α. ΣΗΜΕΡΑ =================
print(NL + 'Α1. ΒΑΘΜΟΝΟΜΗΣΗ σημερα (σκοπια ομαδας FotMob = «μεγαλη») — πραγματικα / μοντελο χαντικαπ / μοντελο συνολων')
bg = np.where(FH, GH[U], GA[U]); sg = np.where(FH, GA[U], GH[U])
bl = np.where(FH, LH_N[U], LA_N[U]); sl = np.where(FH, LA_N[U], LH_N[U])
bo = np.where(FH, OH[U], OA[U]); so = np.where(FH, OA[U], OH[U])
CLINE = {}
for (i, bk, h, L, oh, oa) in SA:
    if h == 0 and bk == 'Crown': CLINE[i] = -L if FMH[i] else L
for lab, m in (('ΟΛΑ', np.ones(len(U), bool)), ('Ben', NS == 'B'), ('γκολ+Elo', NS == 'G'), ('μεγαλη = φαβορι μοντελου', bl > sl), ('μεγαλη = αουτσαιντερ', bl <= sl)):
    cl = np.array([CLINE.get(i, np.nan) for i in U[m]])
    print(f'   {lab:26s} n{m.sum():3d} · μεγαλη βαζει {bg[m].mean():.2f} / {bl[m].mean():.2f} / {bo[m].mean():.2f} · μικρη {sg[m].mean():.2f} / {sl[m].mean():.2f} / {so[m].mean():.2f} · '
          f'διαφορα {(bg - sg)[m].mean():+.2f} / μοντ {(bl - sl)[m].mean():+.2f} / αγορα(γραμμη) {np.nanmean(cl):+.2f} (n{np.isfinite(cl).sum()})')
base_ah = {i: (LH_N[i], LA_N[i]) for i in U}; base_ou = {i: (OH[i], OA[i]) for i in U}
P0 = make_picks(base_ah, base_ou)
GRID = np.round(np.arange(0, 0.81, 0.02), 2)
print(NL + 'Α2. PICKS ΣΗΜΕΡΑ χωρις αλλαγη (4 σεζον)')
for lab, k in (('χαντικαπ ΦΑΒ μεγαλης ≥10%', 'fav_big'), ('χαντικαπ ΦΑΒ μικρης ≥10%', 'fav_small'),
               ('χαντικαπ DOG μεγαλης ≥4%', 'dog_big'), ('χαντικαπ DOG μικρης ≥4%', 'dog_small'), ('over ≥4%', 'over'), ('under ≥10%', 'under')):
    print(f'   {lab:28s} {cc(P0[P0.side == k])}')
for thr in (0.0, 0.04):
    Px = make_picks(base_ah, base_ou, fav_thr=thr)
    print(f'   χαντικαπ ΦΑΒ μεγαλης ≥{int(thr * 100)}%      {cc(Px[Px.side == "fav_big"])}')

# ================= ΧΩΡΙΣΤΕΣ ΔΙΟΡΘΩΣΕΙΣ: δ στα ΣΥΝΟΛΑ, μ στο ΧΑΝΤΙΚΑΠ =================
def ou_pair(delta, idx):
    fh = np.array([FMH[i] for i in idx]); m = 1 + delta
    return np.where(fh, OH[idx] * m, OH[idx]), np.where(fh, OA[idx], OA[idx] * m)
def ah_pair(mu, idx):
    fh = np.array([FMH[i] for i in idx])
    sh = np.where(fh, mu / 2, -mu / 2)            # η «μεγαλη» (FotMob) +μ/2, η μικρη −μ/2 · συνολο ιδιο (μορφη γ)
    return np.maximum(LH_N[idx] + sh, 0.05), np.maximum(LA_N[idx] - sh, 0.05)
def ll_pair(a, b, idx):
    k = np.array([LGF[i] for i in idx])
    return (GH[idx] * np.log(a) - a + GA[idx] * np.log(b) - b - k).sum()

# ================= ΧΡΟΝΙΣΜΟΣ των OVER με τη διορθωση (δ LOSO ανα σεζον) =================
DL = {}
for hold in SEAS:
    tr = U[SEA[U] != hold]
    DL[hold] = GRID[np.argmax([ll_pair(*ou_pair(d, tr), tr) for d in GRID])]
print(NL + 'δ ανα κρυμμενη σεζον: ' + ' · '.join(f'{s} {DL[s]:.2f}' for s in SEAS))
MT = {}
for (i, bk, h, L, o, un) in SO:
    MT[(i, bk, h)] = mtot(L, o, un)
rows = []
for i in U:
    c, d = ou_pair(DL[SEA[i]], np.array([i]))
    td = ES.tot_dist(c[0], d[0], DRAW_SCALE)
    for (j, bk, h, L, o, un) in [x for x in SO if x[0] == i]:
        po, pu = ES.p_over(td, L)
        e = po * (o - 1) * (1 - picks.MARGIN) - pu
        rows.append(dict(i=i, bk=bk, h=h, L=L, od=o, e=e, inz=1.70 <= o <= 2.10, sea=SEA[i], ns=NFS[i],
                         pnl=settle(GH[i] + GA[i], L, o, True), mt=MT[(i, bk, h)]))
R2 = pd.DataFrame(rows)
F = R2[R2.inz & (R2.e >= .04)].sort_values('h', ascending=False).groupby(['i', 'bk']).head(1).copy()
C0 = R2[R2.h == 0].set_index(['i', 'bk'])
M0 = R2.sort_values('h', ascending=False).groupby(['i', 'bk']).mt.first()
F['pc'] = [C0.pnl.get((r.i, r.bk), np.nan) for r in F.itertuples()]
F['oc'] = [C0.od.get((r.i, r.bk), np.nan) for r in F.itertuples()]
F['ec'] = [C0.e.get((r.i, r.bk), np.nan) for r in F.itertuples()]
F['mv_after'] = [C0.mt.get((r.i, r.bk), np.nan) - r.mt for r in F.itertuples()]      # + = η αγορα ΑΝΕΒΑΣΕ τα γκολ (προς το over μας)
F['mv_before'] = [r.mt - M0.get((r.i, r.bk), np.nan) for r in F.itertuples()]        # − = κοντρα πριν την εισοδο
def ct(x):
    if len(x) == 0: return '—'
    m = x.groupby('bk').pnl.mean(); n = x.groupby('bk').size().mean(); ps = x.groupby('sea').pnl.mean()
    mc = x.dropna(subset=['pc']).groupby('bk').pc.mean()
    return (f'{n:4.0f} picks · στην εμφανιση {100 * m.mean():+6.1f}% (' + ' '.join(f'{s[2:]} {100 * v:+.0f}' for s, v in ps.items()) +
            f') · αν περιμενα κλεισιμο {100 * mc.mean():+6.1f}% · τιμη {x.od.mean():.2f}→{x.oc.mean():.2f} · edge κλεισ. {100 * x.ec.mean():+.1f}%')
print(NL + 'OVER μη-FotMob UCL με διορθωση — ΟΛΑ: ' + ct(F))
print(f'   {"βγηκε":9s} | ROI / αναμονη / τιμες | κοντρα ΠΡΙΝ | κινηση ΜΕΤΑ (+ προς εμας) | % ανεβηκαν γκολ / % κατεβηκαν')
for hi, lo, wl in ((72, 72, '72ω'), (60, 48, '60-48ω'), (36, 24, '36-24ω'), (18, 12, '18-12ω'), (8, 4, '8-4ω'), (2, 0, '2ω-κλεισ')):
    y = F[(F.h <= hi) & (F.h >= lo)]
    if len(y) == 0: continue
    print(f'   {wl:9s} | {ct(y)} | {y.mv_before.mean():+.2f} | {y.mv_after.mean():+.2f} | {100 * (y.mv_after >= .05).mean():3.0f}% / {100 * (y.mv_after <= -.05).mean():3.0f}%')
L8 = F[F.h <= 8]; E8 = F[F.h > 8]
print(f'   ΤΕΛΕΥΤΑΙΕΣ 8ω: {ct(L8)} · μετα απο κοντρα ≥0.05: {100 * (L8.mv_before <= -.05).mean():.0f}%')
print(f'   ΠΡΙΝ ΤΙΣ 8ω:   {ct(E8)}')
print(f'   νεα μορφη μονο: {ct(F[F.sea.isin(("2425", "2526"))])}')
