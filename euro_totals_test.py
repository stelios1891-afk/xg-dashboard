"""
euro_totals_test.py — 10/10/2026 (Στελιος: «παμε στα over — και τρεξε και τα under» · «εδω κοιταμε ΜΟΝΟ Champions League»). Champions League 2223-2526, FotMob+FotMob.
Μοντελο γκολ = live ζευγος OU (μηχανη W2: πεναλτι 0.76, χωρις γ, με κ στο φαβορι UCL νεας μορφης)· τιμολογηση τεταρτων (euro_shadow_scan.p_over).
Τιμες Crown & SBOBET (Nowgoal), ζωνη 1.70-2.10· μεσος ορος των 2 βιβλιων (και ανα βιβλιο οταν διαφωνουν).
1. ΒΑΘΜΟΝΟΜΗΣΗ: μοντελο vs πραγματικα γκολ vs αγορα (κλεισιμο), ανα διοργανωση/σεζον και ανα «μοντελο − αγορα».
2. ROI στο ΚΛΕΙΣΙΜΟ, OVER και UNDER, ανα κατωφλι edge 0-12%, ανα διοργανωση, σεζον θετικες, ανα βιβλιο.
3. ΑΝΑ ΓΡΑΜΜΗ (≤2.5 / 2.75-3 / ≥3.25).
4. ΧΡΟΝΙΣΜΟΣ: ροη πρωτης εμφανισης ≤72ω (72 → κλεισιμο), κινηση αγορας μετα, και picks που βγαινουν αργα μετα απο «κοντρα».
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ για υποψηφιο κανονα: θετικο ΚΑΙ στα 2 βιβλια, ≥3/4 σεζον, και θετικο σε 2 γειτονικα κατωφλια (οχι μεμονωμενο κελι).
"""
import sys, io, os, json, glob, contextlib
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
HS = (72, 60, 48, 36, 24, 18, 12, 8, 6, 4, 2, 1, 0)
rows = []
for i, mid in enumerate(MIDS):
    if not FM[i] or not ucl[i]: continue
    td = ES.tot_dist(OH[i], OA[i]); tot = GH[i] + GA[i]
    for bk in ('Crown', 'SBOBET'):
        for h in HS:
            s = snap_ou(mid, bk, h)
            if not s: continue
            L, o, un = s; po, pu = ES.p_over(td, L); mt = mtot(L, o, un)
            for side, od, p_w, p_l in (('over', o, po, pu), ('under', un, pu, po)):
                e = p_w * (od - 1) * (1 - picks.MARGIN) - p_l
                rows.append(dict(i=i, bk=bk, h=h, side=side, comp=COMP[i], sea=SEA[i], L=L, od=od, e=e, inz=1.70 <= od <= 2.10,
                                 pnl=settle(tot, L, od, side == 'over'), pos=(mt if side == 'over' else -mt), mt=mt, model=OH[i] + OA[i], tot=tot))
R = pd.DataFrame(rows)
CMP = ('ChampionsLeague',); CL = {'ChampionsLeague': 'UCL', 'EuropaLeague': 'UEL', 'ConferenceLeague': 'UECL'}
def c(x, short=False):
    if len(x) == 0: return '—'
    m = x.groupby('bk').pnl.agg(['mean', 'size']); ps = x.groupby('sea').pnl.mean()
    if short: return f'{m["size"].mean():.0f}/{100 * m["mean"].mean():+.0f}%'
    return f'{m["size"].mean():4.0f} picks {100 * m["mean"].mean():+6.1f}% ({int((ps > 0).sum())}/{ps.size}) [C {100 * m["mean"].get("Crown", np.nan):+.0f} / S {100 * m["mean"].get("SBOBET", np.nan):+.0f}]'
# ---- 1. βαθμονομηση (κλεισιμο, μοναδικα ματς, Crown) ----
K = R[(R.h == 0) & (R.side == 'over') & (R.bk == 'Crown')]
print('1. ΒΑΘΜΟΝΟΜΗΣΗ (κλεισιμο Crown): μεσα γκολ · μοντελο · αγορα (συνολο απο τη γραμμη/τιμες)')
for cm in CMP:
    x = K[K.comp == cm]
    print(f'   {CL[cm]:5s} n{len(x):4d} · γκολ {x.tot.mean():.2f} · μοντελο {x.model.mean():.2f} · αγορα {x.mt.mean():.2f} · ανα σεζον γκολ−μοντ ' +
          ' '.join(f'{s}:{(x[x.sea == s].tot - x[x.sea == s].model).mean():+.2f}' for s in sorted(x.sea.unique())))
K = K.assign(gap=K.model - K.mt)
print('   ανα «μοντελο − αγορα» (ολα): ' + ' · '.join(f'{lab}: n{len(y)} γκολ−αγορα {(y.tot - y.mt).mean():+.2f}' for lab, y in
      (('μοντ < αγορα −0.3', K[K.gap < -0.3]), ('−0.3..−0.1', K[(K.gap >= -0.3) & (K.gap < -0.1)]), ('±0.1', K[K.gap.abs() < 0.1]),
       ('+0.1..+0.3', K[(K.gap >= 0.1) & (K.gap < 0.3)]), ('μοντ > αγορα +0.3', K[K.gap >= 0.3]))))
# ---- 2. ROI στο κλεισιμο ανα κατωφλι ----
print('\n2. ROI ΣΤΟ ΚΛΕΙΣΙΜΟ (1.70-2.10) ανα κατωφλι edge')
Z = R[(R.h == 0) & R.inz]
for side in ('over', 'under'):
    print(f'   {side.upper()}:')
    for cm in CMP:
        x = Z[(Z.side == side) & ((Z.comp == cm) if cm != 'ΟΛΑ' else True)]
        print(f'      {CL.get(cm, cm):5s} ' + ' · '.join(f'≥{int(th * 100)}% {c(x[x.e >= th], True)}' for th in (0, .02, .04, .06, .08, .10, .12)))
    for cm in CMP:
        x = Z[(Z.side == side) & (Z.comp == cm) & (Z.e >= .04)]
        print(f'      {CL[cm]:5s} @4% αναλυτικα: {c(x)}')
    print(f'      ΤΥΦΛΑ (ολα τα {side}, χωρις μοντελο): ' + ' · '.join(f'{CL[cm]} {c(Z[(Z.side == side) & (Z.comp == cm)], True)}' for cm in CMP))
# ---- 3. ανα γραμμη ----
print('\n3. ΑΝΑ ΓΡΑΜΜΗ (κλεισιμο, @4%)')
for side in ('over', 'under'):
    x = Z[(Z.side == side) & (Z.e >= .04)]
    print(f'   {side.upper():5s} ' + ' · '.join(f'{lab}: {c(x[m], True)}' for lab, m in (('≤2.5', x.L <= 2.5), ('2.75-3', (x.L > 2.5) & (x.L <= 3)), ('≥3.25', x.L > 3))) +
          ' || UCL ' + ' · '.join(f'{lab}: {c(x[m & (x.comp == "ChampionsLeague")], True)}' for lab, m in (('≤2.5', x.L <= 2.5), ('2.75-3', (x.L > 2.5) & (x.L <= 3)), ('≥3.25', x.L > 3))))
# ---- 4. χρονισμος: ροη πρωτης εμφανισης ----
print('\n4. ΧΡΟΝΙΣΜΟΣ — ροη «πρωτη εμφανιση ≤72ω» @4% (ζωνη 1.70-2.10)')
P = R[R.inz & (R.e >= .04)].sort_values('h', ascending=False)
first = P.groupby(['i', 'bk', 'side']).head(1).copy()
POSC = R[R.h == 0].set_index(['i', 'bk', 'side']).pos
POS0 = R.sort_values('h', ascending=False).groupby(['i', 'bk', 'side']).pos.first()
first['mv_after'] = [POSC.get((r.i, r.bk, r.side), np.nan) - r.pos for r in first.itertuples()]
first['mv_before'] = [r.pos - POS0.get((r.i, r.bk, r.side), np.nan) for r in first.itertuples()]
PX = R.set_index(['i', 'bk', 'side', 'h']).pnl
WIN = ((72, 72, '72ω'), (60, 48, '60-48ω'), (36, 24, '36-24ω'), (18, 12, '18-12ω'), (8, 4, '8-4ω'), (2, 0, '2ω-κλεισ'))
for side in ('over', 'under'):
    for cm in CMP:
        x = first[(first.side == side) & (first.comp == cm)]
        print(f'   {side.upper():5s} {CL[cm]:5s} ΟΛΑ {c(x)} · κιν μετα την εισοδο {x.mv_after.mean():+.2f} (+ = αγορα προς εμας)')
        for hi, lo, wl in WIN:
            y = x[(x.h <= hi) & (x.h >= lo)]
            if len(y) == 0: continue
            pc = [PX.get((r.i, r.bk, r.side, 0), np.nan) for r in y.itertuples()]; pc = [v for v in pc if np.isfinite(v)]
            print(f'      βγηκε {wl:9s} {c(y)} · αν περιμενα ως κλεισ {100 * np.mean(pc) if pc else np.nan:+.0f}% · κιν μετα {y.mv_after.mean():+.2f} · κοντρα πριν {y.mv_before.mean():+.2f}')
print('\n   ΑΡΓΑ (24ω → κλεισιμο) ανα «κοντρα» πριν την εισοδο:')
for side in ('over', 'under'):
    x = first[(first.side == side) & (first.h <= 24)]
    print(f'   {side.upper():5s} ' + ' · '.join(f'{lab}: {c(x[m], True)}' for lab, m in (('μεγαλη κοντρα ≥0.25', x.mv_before <= -0.25),
          ('μικρη 0.05-0.25', (x.mv_before <= -0.05) & (x.mv_before > -0.25)), ('χωρις κοντρα', x.mv_before > -0.05))))
first.to_pickle('euro_totals_first.pkl')
