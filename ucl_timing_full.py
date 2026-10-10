"""
ucl_timing_full.py — 10/10/2026 (Στελιος: «τεστ χρονισμου χωρις αξια, πιο αναλυτικα απο 72ω ως το κλεισιμο, χωριστα γκολ/φαβορι/αουτσαιντερ,
και τα picks που προκυπτουν 24ω → 2ω — αν εκει που υπαρχει κοντρα προς το κλεισιμο, υπαρχει λογος να τα αποφυγουμε»).
Champions League 2223-2526, σημερινη αλυσιδα, σημερινοι κανονες: φαβορι ≥10% (σωστα τεταρτα), αουτσαιντερ ≥4% (p_cover),
OVER ≥4% (μηχανη γκολ W2 πεναλτι 0.76 + κ, καθαρη τιμολογηση τεταρτων), FotMob+FotMob, 1.70-2.10. Crown & SBOBET (Nowgoal), μεσος ορος.
Στιγμες: 72, 60, 48, 36, 24, 18, 12, 8, 6, 4, 2, 1ω πριν, κλεισιμο.
(Α) picks που υπαρχουν σε καθε στιγμη.
(Β) ΡΟΗ «πρωτη εμφανιση ≤72ω» (= live κανονας): ROI ανα παραθυρο πρωτης εμφανισης + κινηση αγορας απο την εισοδο ως το κλεισιμο.
(Γ) picks που εμφανιζονται ΠΡΩΤΗ φορα 24ω → 2ω: πως προεκυψαν (η αγορα κινηθηκε ΜΑΚΡΙΑ απο την πλευρα μας = «κοντρα») —
    ROI ανα μεγεθος κοντρας απο τις 72ω, και αν η κοντρα συνεχιζεται ως το κλεισιμο.
"""
import sys, io, os, json, glob, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
t = open('uel_timing.py', encoding='utf-8').read(); t = t[:t.index('B = pd.DataFrame(rows)')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
t = t.replace('\nrows = []\nfor i, mid in enumerate(MIDS):', '\nrows = []\nfor i, mid in enumerate([]):')
u = {'__name__': 'ut'}
with contextlib.redirect_stdout(io.StringIO()): exec(t, u)
snap, sdist, cover_q, edge, picks, KO = u['snap'], u['sdist'], u['cover_q'], u['edge'], u['picks'], u['KO']
MIDS, COMP, FM, GD, SEA, LH, LA = (u[k] for k in ('MIDS', 'COMP', 'FM', 'GD', 'SEA', 'LH_N', 'LA_N'))
# ---- μηχανη γκολ (W2, πεναλτι 0.76): προ-γ λ με εδρα + κ στο φαβορι UCL (οπως το live ζευγος xgh_ou/xga_ou) ----
os.environ['W2_IN'] = 'euro_v6w2_preds_pen76.pkl'
b = open('uel_battery.py', encoding='utf-8').read(); b = b[:b.index('P0 = make_picks')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
w = {'__name__': 'w2'}
with contextlib.redirect_stdout(io.StringIO()): exec(b, w)
assert list(w['MIDS']) == list(MIDS)
GH, GA = np.asarray(w['GH']), np.asarray(w['GA'])
OH, OA = np.asarray(w['g']['LH2'], float).copy(), np.asarray(w['g']['LA2'], float).copy()
ucl = np.asarray(COMP) == 'ChampionsLeague'; KAP = w['g'].get('UCL_FAV_SCALE', 1.16)
newf = np.isin(np.asarray(SEA), ['2425', '2526'])
fh = OH >= OA
OH = np.where(ucl & newf & fh, OH * KAP, OH); OA = np.where(ucl & newf & ~fh, OA * KAP, OA)
import euro_shadow_scan as ES
# ---- τροχιες OU (Nowgoal) ----
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
def snap_ou(mid, bk, h):
    ko = KO.get(mid); seq = TOU.get((mid, bk))
    if not ko or not seq: return None
    cut = ko - h * 3600 if h else ko + 900
    prev = [x for x in seq if x[0] <= cut]
    if not prev or (h and (ko - prev[-1][0]) / 3600 > h + 24): return None
    return prev[-1][1:]
def settle_ou(tot, L, o):
    parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]; r = 0.0
    for p in parts:
        d = tot - p; r += ((o - 1) if d > 0 else (0 if d == 0 else -1)) / len(parts)
    return r
def msup(L, oh, oa, T):
    tq = (1 / oh) / (1 / oh + 1 / oa); lo, hi = -4.5, 4.5
    for _ in range(22):
        s = (lo + hi) / 2; d = picks.gd_dist(max((T + s) / 2, .05), max((T - s) / 2, .05)); w_, p = picks.p_cover(d, 1, L)
        if w_ / max(1 - p, 1e-9) < tq: lo = s
        else: hi = s
    return (lo + hi) / 2
def mtot(L, o, un):        # «αγορα» συνολο: το συνολο λ οπου P(over)/P(under) = τιμη αγορας χωρις γκανιοτα
    q = (1 / o) / (1 / o + 1 / un); lo, hi = 0.5, 7.0
    for _ in range(22):
        T = (lo + hi) / 2; po, pu = ES.p_over(ES.tot_dist(T / 2, T / 2), L)
        if po / max(po + pu, 1e-9) < q: lo = T
        else: hi = T
    return (lo + hi) / 2
HS = (72, 60, 48, 36, 24, 18, 12, 8, 6, 4, 2, 1, 0)
rows = []
for i, mid in enumerate(MIDS):
    if not ucl[i] or not FM[i]: continue
    dist = sdist(LH[i], LA[i]); td = ES.tot_dist(OH[i], OA[i]); T = LH[i] + LA[i]
    for bk in ('Crown', 'SBOBET'):
        for h in HS:
            s = snap(mid, bk, h)
            if s:
                L, oh, oa = s
                for side, o in ((1, oh), (-1, oa)):
                    ln = L if side == 1 else -L
                    role = 'fav' if ln <= -0.5 else ('dog' if ln >= 0.5 else None)
                    if role is None or not (1.70 <= o <= 2.10): continue
                    pw, pp = cover_q(dist, side, ln) if role == 'fav' else picks.p_cover(dist, side, ln)
                    e = edge(pw, pp, o)
                    rows.append(dict(i=i, bk=bk, h=h, mk=role, side=side, e=e, pick=e >= (0.10 if role == 'fav' else 0.04),
                                     pnl=picks.settle(GD[i], side, ln, o), pos=msup(L, oh, oa, T) * side, sea=SEA[i]))
            so = snap_ou(mid, bk, h)
            if so:
                L, o, un = so
                if 1.70 <= o <= 2.10:
                    po, pu = ES.p_over(td, L); e = po * (o - 1) * (1 - picks.MARGIN) - pu
                    rows.append(dict(i=i, bk=bk, h=h, mk='over', side=0, e=e, pick=e >= 0.04, pnl=settle_ou(GH[i] + GA[i], L, o),
                                     pos=mtot(L, o, un), sea=SEA[i]))
R = pd.DataFrame(rows)
NAME = {'fav': 'ΦΑΒΟΡΙ', 'dog': 'ΑΟΥΤΣΑΙΝΤΕΡ', 'over': 'OVER (γκολ)'}
lab = lambda h: 'κλεισ' if h == 0 else f'{h}ω'
def c(x, short=False):
    if len(x) == 0: return '—'
    m = x.groupby('bk').pnl.agg(['mean', 'size']); ps = x.groupby('sea').pnl.mean()
    return f'{m["size"].mean():.0f}/{100 * m["mean"].mean():+.0f}%' if short else f'{m["size"].mean():4.0f} picks {100 * m["mean"].mean():+6.1f}% ({int((ps > 0).sum())}/{ps.size})'
print('Champions League 2022-2026 · μεσος Crown/SBOBET · (n picks / ROI)')
print('\n(Α) PICKS ΠΟΥ ΥΠΑΡΧΟΥΝ ΣΕ ΚΑΘΕ ΣΤΙΓΜΗ')
for mk in ('fav', 'dog', 'over'):
    x = R[(R.mk == mk) & R.pick]
    print(f'   {NAME[mk]:12s} ' + ' · '.join(f'{lab(h)} {c(x[x.h == h], True)}' for h in HS))
# ---- (Β) ροη πρωτης εμφανισης ----
P = R[R.pick].sort_values('h', ascending=False)
first = P.groupby(['i', 'bk', 'mk', 'side']).head(1)
CL = R[R.h == 0].set_index(['i', 'bk', 'mk', 'side']).pos
P72 = R.sort_values('h', ascending=False).groupby(['i', 'bk', 'mk', 'side']).pos.first()   # ΠΡΩΤΗ διαθεσιμη τιμη (≤72ω)
first = first.assign(pos_cl=[CL.get((r.i, r.bk, r.mk, r.side), np.nan) for r in first.itertuples()],
                     pos72=[P72.get((r.i, r.bk, r.mk, r.side), np.nan) for r in first.itertuples()])
# κινηση: + = η αγορα πηγε ΠΡΟΣ την πλευρα μας (υπεροχη/συνολο μας ανεβηκε) μετα την εισοδο
first['mv_after'] = first.pos_cl - first.pos
first['mv_before'] = first.pos - first.pos72          # απο την ΠΡΩΤΗ διαθεσιμη τιμη (≤72ω) ως την εισοδο: − = κοντρα (η αγορα πηγε μακρια μας → εγινε pick)
WIN = ((72, 48, '72-48ω'), (47, 24, '36-24ω'), (23, 12, '18-12ω'), (11, 6, '8-6ω'), (5, 2, '4-2ω'), (1, 0, '1ω-κλεισ'))
print('\n(Β) ΡΟΗ «ΠΡΩΤΗ ΕΜΦΑΝΙΣΗ ≤72ω» (live κανονας) — ανα παραθυρο πρωτης εμφανισης · κινηση αγορας απο την εισοδο ως το κλεισιμο (+ = προς εμας)')
for mk in ('fav', 'dog', 'over'):
    x = first[first.mk == mk]
    print(f'   {NAME[mk]:12s} ΟΛΑ {c(x)} · κιν μετα {x.mv_after.mean():+.2f}')
    for hi, lo, wl in WIN:
        y = x[(x.h <= hi) & (x.h >= lo)]
        if len(y): print(f'      {wl:9s} {c(y)} · κιν μετα την εισοδο {y.mv_after.mean():+.2f}')
print('\n(Γ) PICKS ΠΟΥ ΕΜΦΑΝΙΖΟΝΤΑΙ ΠΡΩΤΗ ΦΟΡΑ 24ω → 2ω: ποσο «κοντρα» (η αγορα πηγε μακρια απο την πλευρα μας απο την ΠΡΩΤΗ διαθεσιμη τιμη ως την εισοδο, γκολ)')
L_ = first[(first.h <= 24) & (first.h >= 2)]
for mk in ('fav', 'dog', 'over'):
    x = L_[L_.mk == mk]
    print(f'   {NAME[mk]:12s} ΟΛΑ {c(x)} · μεση κινηση πριν την εισοδο {x.mv_before.mean():+.2f} · μετα {x.mv_after.mean():+.2f}')
    for lo, hi, gl in ((-9, -0.25, 'μεγαλη κοντρα (≥0.25)'), (-0.25, -0.05, 'μικρη κοντρα (0.05-0.25)'), (-0.05, 9, 'χωρις κοντρα / υπερ μας')):
        y = x[(x.mv_before > lo) & (x.mv_before <= hi)]
        if len(y): print(f'      {gl:26s} {c(y)} · κιν μετα την εισοδο {y.mv_after.mean():+.2f}')
    z = x[x.mv_before <= -0.05]
    for gl, m in (('κοντρα που ΣΥΝΕΧΙΣΕ ως το κλεισιμο', z.mv_after < -0.02), ('κοντρα που ΓΥΡΙΣΕ προς εμας', z.mv_after > 0.02), ('κοντρα που σταματησε', z.mv_after.abs() <= 0.02)):
        y = z[m]
        if len(y): print(f'      {gl:36s} {c(y)}')
first.to_pickle('ucl_timing_full_first.pkl')
