# -*- coding: utf-8 -*-
"""euro_clean_rules.py — 5/11/2026 (Στελιος: «τρεξε το 3»). ΚΑΘΑΡΟΣ ΠΙΝΑΚΑΣ ολων των κανονων Ευρωπης: σωστες κοκκινες (emps), δυναμεις και αποτελεσματα στο 90′, φετινα ευρωπαικα (Μ8) στο χαντικαπ.
ΜΗΧΑΝΕΣ: χαντικαπ = euro_m8_dump (INS· 60% ολα, 80% UEL φαβ εντος) · συνολα = ζευγος W2 με πεναλτι 0.76 (euro_variant_build c90p), κ UCL 1.16, μη-FotMob UCL ×1.22 (οπως live).
ΕΙΣΟΔΟΣ (ιδια με το τεστ του καθε κανονα): UCL πρωτη εμφανιση 168-2ω, τιμιος χρονος (c90sh4/c90sh7) · UEL φαβ εντος 36/24/18/12ω · ολα τα αλλα 72ω-κλεισιμο. 1.70-2.10, Crown & SBOBET (μεσος).
«ΠΑΛΙΟ» = οπως τα παλια τεστ (euro_v6w2_preds 8/9 ή pen76, αποτελεσμα με παραταση), για ελεγχο αναπαραγωγης.
ΚΡΙΤΗΡΙΑ (γραφτηκαν πριν): UCL νεα μορφη: ROI>0 + και οι 2 σεζον θετικες · αλλοι: ROI>0, 2 βιβλια θετικα, ≥3/4 σεζον · ολοι: CLV οχι αρνητικο (t<−1.5), αξια xG>0 (χαντικαπ).
ΚΑΤΩΦΛΙ: LOSO (κρυμμενη σεζον → κατωφλι με τις περισσοτερες μοναδες στις αλλες). Αλλαγη υποψηφια μονο αν κοβεται στα κριτηρια ΚΑΙ το LOSO δεν διαλεγει το σημερινο."""
import sys, os, io, json, glob, pickle, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
_SIO = io.StringIO; io.StringIO = _Q
t = open('uel_timing.py', encoding='utf-8').read(); t = t[:t.index('B = pd.DataFrame(rows)')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
t = t.replace('\nrows = []\nfor i, mid in enumerate(MIDS):', '\nrows = []\nfor i, mid in enumerate([]):')
u = {'__name__': 'ut'}
with contextlib.redirect_stdout(_Q()): exec(t, u)
def pairW2(tag):
    os.environ['W2_IN'] = tag
    b = open('uel_battery.py', encoding='utf-8').read(); b = b[:b.index('P0 = make_picks')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
    w = {'__name__': 'w2'}
    with contextlib.redirect_stdout(_Q()): exec(b, w)
    return np.asarray(w['g']['LH2'], float).copy(), np.asarray(w['g']['LA2'], float).copy(), np.asarray(w['GH'], float), np.asarray(w['GA'], float), [str(m) for m in w['MIDS']]
OLD_W2 = pairW2('euro_v6w2_preds_pen76.pkl'); NEW_W2 = pairW2('euro_v6w2_preds_c90p.pkl')
sys.stdout = sys.__stdout__; sys.stdout.reconfigure(encoding='utf-8'); io.StringIO = _SIO
import picks, euro_shadow_scan as ES
snap, sdist, cover_q, edge, KO = u['snap'], u['sdist'], u['cover_q'], u['edge'], u['KO']
P6 = pickle.load(open('euro_m8_dump_0.6.pkl', 'rb')); P8 = pickle.load(open('euro_m8_dump_0.8.pkl', 'rb'))
MIDS, SEA, COMP, GD, FM = P6['MIDS'], np.asarray(P6['SEA']), np.asarray(P6['COMP']), P6['GD'], P6['FM']
assert MIDS == P8['MIDS'] == [str(m) for m in u['MIDS']] == OLD_W2[4] == NEW_W2[4]
_V = pickle.load(open('euro_v6_preds.pkl', 'rb')); _VI = {str(m): j for j, m in enumerate(_V['mids'])}
SH = np.array([_V['src_h'][_VI[m]] if m in _VI else '?' for m in MIDS]); SA = np.array([_V['src_a'][_VI[m]] if m in _VI else '?' for m in MIDS])
NEW = ('2425', '2526'); SEAS = ('2223', '2324', '2425', '2526')
R90 = {}; XG = {}
for f in glob.glob('data_Europe_*.json'):
    for k, m in json.load(open(f, encoding='utf-8')).items():
        if m.get('hs') is not None and m.get('as') is not None: R90[str(k)] = (m['hs'], m['as'])
        sh = m.get('shots') or []
        if sh:
            hid = int(m['home']['id'])
            XG[str(k)] = (sum(s['xg'] for s in sh if s.get('xg') is not None and int(s['tid']) == hid), sum(s['xg'] for s in sh if s.get('xg') is not None and int(s['tid']) != hid))
TOT90 = np.array([sum(R90[m]) if m in R90 else np.nan for m in MIDS], float)
assert not np.isnan(TOT90).any() and all(R90[m][0] - R90[m][1] == GD[i] for i, m in enumerate(MIDS))
GD_OLD = np.asarray(u['GD'], float); TOT_OLD = OLD_W2[2] + OLD_W2[3]
print(f'90′ vs παλια αποτελεσματα: διαφορα σε {(GD_OLD != GD).sum()} ματς διαφορας τερματων · {(TOT_OLD != TOT90).sum()} ματς συνολου')
# ---- τιμιος χρονος
_b = pickle.load(open('euro_blend_dump_c90.pkl', 'rb')); _ib = {str(m): k for k, m in enumerate(_b['MIDS'])}
def ratio(name):
    d = pickle.load(open(f'euro_blend_dump_{name}.pkl', 'rb')); iv = {str(m): k for k, m in enumerate(d['MIDS'])}
    rh = np.array([d['LH'][iv[m]] / _b['LH'][_ib[m]] if m in iv and m in _ib and _b['LH'][_ib[m]] > 0 else 1.0 for m in MIDS])
    ra = np.array([d['LA'][iv[m]] / _b['LA'][_ib[m]] if m in iv and m in _ib and _b['LA'][_ib[m]] > 0 else 1.0 for m in MIDS])
    return rh, ra
R4, R7 = ratio('c90sh4'), ratio('c90sh7')
# ---- συνολα
UCLb = (COMP == 'ChampionsLeague'); NEWb = np.isin(SEA, NEW)
FMH, FMA = SH == 'shots', SA == 'shots'
KAPPA_T = 1.16; NONFM_T = float(getattr(ES, 'UCL_NONFM_OU_SCALE', 1.22))
def pair_live(W2):
    oh, oa = W2[0].copy(), W2[1].copy(); fh = oh >= oa
    oh = np.where(UCLb & NEWb & fh, oh * KAPPA_T, oh); oa = np.where(UCLb & NEWb & ~fh, oa * KAPPA_T, oa)
    one = FMH != FMA
    oh = np.where(UCLb & one & FMH, oh * NONFM_T, oh); oa = np.where(UCLb & one & FMA, oa * NONFM_T, oa)
    return oh, oa
OH_O, OA_O = pair_live(OLD_W2); OH_N, OA_N = pair_live(NEW_W2)
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
def snap_ou(mid, bk, h, stale=True):
    ko = KO.get(mid); seq = TOU.get((mid, bk))
    if not ko or not seq: return None
    cut = ko - h * 3600 if h else ko + 900
    prev = [x for x in seq if x[0] <= cut]
    if not prev or (stale and h and (ko - prev[-1][0]) / 3600 > h + 24): return None
    return prev[-1][1:]
def settle_t(tot, L, o, over):
    parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]; r = 0.0
    for p in parts:
        d = (tot - p) if over else (p - tot); r += ((o - 1) if d > 0 else (0 if d == 0 else -1)) / len(parts)
    return r
_ct = {}
def mtot(L, o, un):
    k = (L, o, un)
    if k in _ct: return _ct[k]
    q = (1 / o) / (1 / o + 1 / un); lo, hi = 0.5, 7.0
    for _ in range(22):
        T = (lo + hi) / 2; po, pu = ES.p_over(ES.tot_dist(T / 2, T / 2, .85), L)
        if po / max(po + pu, 1e-9) < q: lo = T
        else: hi = T
    _ct[k] = (lo + hi) / 2; return _ct[k]
_c = {}
def fair(l, oh, oa, T=2.9):
    k = (l, oh, oa)
    if k in _c: return _c[k]
    q = (1 / oh) / (1 / oh + 1 / oa); lo, hi = -5., 5.
    parts = [l] if (l * 4) % 2 == 0 else [l - .25, l + .25]
    for _ in range(30):
        s = (lo + hi) / 2; d = picks.gd_dist(max((T + s) / 2, .05), max((T - s) / 2, .05))
        c = [picks.p_cover(d, 1, L) for L in parts]; pe = sum(a for a, _ in c) / max(sum(1 - b for _, b in c), 1e-9)
        lo, hi = (s, hi) if pe < q else (lo, s)
    _c[k] = (lo + hi) / 2; return _c[k]
def xg_value(i, side, ln, o):
    x = XG.get(MIDS[i])
    if not x: return np.nan
    pw, pp = picks.p_cover(picks.gd_dist(max(x[0], .05), max(x[1], .05)), side, ln)
    return o / ((1 - pp) / pw) - 1 if pw > 0 else np.nan
H_UCL = (168, 144, 120, 96, 72, 60, 48, 36, 24, 18, 12, 8, 6, 4, 2); H_UEL = (36, 24, 18, 12); H_72 = (72, 60, 48, 36, 24, 18, 12, 8, 6, 4, 2, 1, 0)
# ---- ροες: για καθε ματς/βιβλιο/πλευρα η ακολουθια (h, edge, pnl, clv, xv)· το κατωφλι διαλεγει την πρωτη με edge ≥ Τ
def seq_ah(LL, gd, mask, kind, hs, honest=False, sidefn=None):
    S = []
    for i in np.where(mask)[0]:
        mid = MIDS[i]
        for bk in ('Crown', 'SBOBET'):
            cl = snap(mid, bk, 0)
            for side in ((1, -1) if sidefn is None else (sidefn(i),)):
                q = []
                for h in hs:
                    s = snap(mid, bk, h)
                    if not s: continue
                    L, oh, oa = s; ln = L if side == 1 else -L; o = oh if side == 1 else oa
                    if not (1.70 <= o <= 2.10): continue
                    if kind == 'fav' and ln > -0.5: continue
                    if kind == 'dog' and ln < 0.5: continue
                    if kind == 'dnb' and abs(ln) > .01: continue
                    lh, la = LL[0][i], LL[1][i]
                    if honest and h > 120: lh, la = lh * R7[0][i], la * R7[1][i]
                    elif honest and h >= 96: lh, la = lh * R4[0][i], la * R4[1][i]
                    D = sdist(lh, la); pw, pp = picks.p_cover(D, side, ln) if kind == 'dog' else cover_q(D, side, ln)
                    q.append((h, edge(pw, pp, o), L, oh, oa, ln, o))
                if q: S.append(dict(i=i, bk=bk, side=side, q=q, cl=cl))
    def eval_(rec):
        i, side = rec['i'], rec['side']; cl = rec['cl']; h, e, L, oh, oa, ln, o = rec['hit']
        return dict(i=i, bk=rec['bk'], side=side, sea=SEA[i], h=h, e=e, pnl=picks.settle(float(gd[i]), side, ln, o), clv=side * (fair(cl[0], cl[1], cl[2]) - fair(L, oh, oa)) if cl else np.nan, xv=xg_value(i, side, ln, o))
    return S, eval_
def seq_ou(OH, OA, tot, mask, over, hs, honest=False, stale=True):
    S = []; sg = 1 if over else -1
    for i in np.where(mask)[0]:
        mid = MIDS[i]
        for bk in ('Crown', 'SBOBET'):
            cl = snap_ou(mid, bk, 0, stale); q = []
            for h in hs:
                s = snap_ou(mid, bk, h, stale)
                if not s: continue
                L, oo, un = s; o = oo if over else un
                if not (1.70 <= o <= 2.10): continue
                oh, oa = OH[i], OA[i]
                if honest and h > 120: oh, oa = oh * R7[0][i], oa * R7[1][i]
                elif honest and h >= 96: oh, oa = oh * R4[0][i], oa * R4[1][i]
                po, pu = ES.p_over(ES.tot_dist(oh, oa, .85), L); pw, pp = (po, pu) if over else (pu, po)
                q.append((h, pw * (o - 1) * (1 - picks.MARGIN) - pp, L, oo, un, o))
            if q: S.append(dict(i=i, bk=bk, side=sg, q=q, cl=cl))
    def eval_(rec):
        i = rec['i']; cl = rec['cl']; h, e, L, oo, un, o = rec['hit']
        return dict(i=i, bk=rec['bk'], side=sg, sea=SEA[i], h=h, e=e, pnl=settle_t(tot[i], L, o, over), clv=sg * (mtot(cl[0], cl[1], cl[2]) - mtot(L, oo, un)) if cl else np.nan, xv=np.nan)
    return S, eval_
def at(pack, T, hi=None):
    S, ev = pack; out = []
    for r in S:
        f = next((x for x in r['q'] if x[1] >= T), None)
        if f is None or (hi is not None and f[1] >= hi): continue
        r2 = dict(r); r2['hit'] = f; out.append(ev(r2))
    return pd.DataFrame(out, columns=['i', 'bk', 'side', 'sea', 'h', 'e', 'pnl', 'clv', 'xv'])
def units(z):
    return z.pnl.sum() / 2
def tval(v):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    return v.mean() / (v.std() / np.sqrt(len(v))) if len(v) > 3 and v.std() > 0 else np.nan
def desc(z):
    if not len(z): return '   0 picks'
    return f"{len(z) / 2:5.1f} picks ROI {100 * z.pnl.mean():+6.1f}% {units(z):+6.1f}μ ±{100 * z.groupby('i').pnl.mean().std() / np.sqrt(z.i.nunique()):4.1f} │ " + ' '.join(f"{s[2:]}:{100 * z[z.sea == s].pnl.mean():+.0f}" for s in SEAS if (z.sea == s).any()) + f" │ C {100 * z[z.bk == 'Crown'].pnl.mean():+.1f} S {100 * z[z.bk == 'SBOBET'].pnl.mean():+.1f} │ CLV {z.clv.mean():+.3f} (t {tval(z.clv):+.1f}) │ αξια xG {100 * z.xv.mean():+.1f}%"
SUM = []
def rule(name, old, new, thr, grid, new_only=False, handicap=True, live=True, hi=None):
    print(f"\n{'=' * 8} {name} {'(ΣΚΙΑ)' if not live else ''}")
    zo, zn = at(old, thr, hi), at(new, thr, hi)
    if new_only: zo_, zn_ = zo[zo.sea.isin(NEW)], zn[zn.sea.isin(NEW)]
    else: zo_, zn_ = zo, zn
    print(f'   ΠΑΛΙΟ  {desc(zo_)}'); print(f'   ΚΑΘΑΡΟ {desc(zn_)}')
    if new_only: print(f'   4 σεζον ΚΑΘΑΡΟ {desc(zn)}')
    ps = zn_.groupby('sea').pnl.mean(); bb = zn_.groupby('bk').pnl.mean()
    a = len(zn_) > 0 and zn_.pnl.mean() > 0
    b = bool((ps > 0).all()) and len(ps) == 2 if new_only else (ps > 0).sum() >= 3
    c = new_only or (bool((bb > 0).all()) and len(bb) == 2)
    tv = tval(zn_.clv); d = not (np.isfinite(tv) and zn_.clv.mean() < 0 and tv < -1.5)
    e = (not handicap) or zn_.xv.mean() > 0
    ok = a and b and c and d and e
    print(f"   ΚΡΙΤΗΡΙΑ: ROI>0 {'✓' if a else '✗'} · σεζον {'✓' if b else '✗'} · 2 βιβλια {'✓' if c else '✗'} · CLV {'✓' if d else '✗'} · αξια xG {'✓' if e else ('—' if not handicap else '✗')} → {'ΚΡΑΤΙΕΤΑΙ' if ok else 'ΚΟΒΕΤΑΙ'}")
    pool = (lambda z: z[z.sea.isin(NEW)]) if new_only else (lambda z: z)
    print('   ΚΑΤΩΦΛΙΑ: ' + ' · '.join(f"≥{int(round(T * 100))}% {len(pool(at(new, T))) / 2:.0f}p {100 * pool(at(new, T)).pnl.mean():+.1f}% {units(pool(at(new, T))):+.1f}μ" for T in grid))
    if hi is None:
        folds = NEW if new_only else SEAS; ch = {}; oos = []; cur = []
        tabs = {T: pool(at(new, T)) for T in grid}
        for s in folds:
            sc = {T: units(tabs[T][tabs[T].sea != s]) for T in grid}
            best = max(sc, key=lambda k: sc[k]); ch[s] = best
            oos.append(tabs[best][tabs[best].sea == s]); cur.append(tabs[thr][tabs[thr].sea == s])
        oo = pd.concat(oos); cc = pd.concat(cur)
        same = all(abs(v - thr) < 1e-9 for v in ch.values())
        print('   LOSO: ' + ' '.join(f'{s[2:]}→{int(round(v * 100))}%' for s, v in ch.items()) + f" · εκτος δειγματος {units(oo):+.1f}μ ({100 * oo.pnl.mean():+.1f}%) vs σημερινο {units(cc):+.1f}μ ({100 * cc.pnl.mean():+.1f}%)" + (' · διαλεγει ΠΑΝΤΑ το σημερινο' if same else ''))
    else:
        same = True; oo = cc = zn_
    SUM.append(dict(κανονας=name, live=live, παλιο_n=len(zo_) / 2, παλιο=round(100 * zo_.pnl.mean(), 1) if len(zo_) else np.nan, n=len(zn_) / 2, ROI=round(100 * zn_.pnl.mean(), 1) if len(zn_) else np.nan, μ=round(units(zn_), 1),
                    clv=round(zn_.clv.mean(), 3), ok=ok, loso_ιδιο=same))
UCLA = (COMP == 'ChampionsLeague') & FM; UELA = (COMP == 'EuropaLeague') & FM; ECA = (COMP == 'ConferenceLeague') & FM
UCLB = (COMP == 'ChampionsLeague') & (FMH != FMA); ECB = (COMP == 'ConferenceLeague') & (FMH != FMA)
OLD_A6 = (np.asarray(u['LH_N'], float), np.asarray(u['LA_N'], float))
_d8 = pickle.load(open('euro_blend_dump_0.8.pkl', 'rb')); OLD_A8 = (np.asarray(_d8['LH'], float), np.asarray(_d8['LA'], float))
G4 = (.04, .06, .08, .10, .12, .14); side_b = lambda i: (1 if FMA[i] else -1)
# ---------- ΧΑΝΤΙΚΑΠ LIVE
rule('UCL φαβορι ≥4%', seq_ah(OLD_A6, GD_OLD, UCLA, 'fav', H_UCL, True), seq_ah(P6['INS'], GD, UCLA, 'fav', H_UCL, True), .04, G4, new_only=True)
rule('UCL αουτσαιντερ ≥10%', seq_ah(OLD_A6, GD_OLD, UCLA, 'dog', H_UCL, True), seq_ah(P6['INS'], GD, UCLA, 'dog', H_UCL, True), .10, G4, new_only=True)
rule('UCL DNB ≥4%', seq_ah(OLD_A6, GD_OLD, UCLA, 'dnb', H_UCL, True), seq_ah(P6['INS'], GD, UCLA, 'dnb', H_UCL, True), .04, G4, new_only=True)
rule('UEL φαβορι εντος ≥4% (80% xG, 12-36ω)', seq_ah(OLD_A8, GD_OLD, UELA, 'fav', H_UEL, sidefn=lambda i: 1), seq_ah(P8['INS'], GD, UELA, 'fav', H_UEL, sidefn=lambda i: 1), .04, G4)
rule('UECL Α φαβορι ≥4%', seq_ah(OLD_A6, GD_OLD, ECA, 'fav', H_72), seq_ah(P6['INS'], GD, ECA, 'fav', H_72), .04, G4)
rule('UECL Α αουτσαιντερ ≥10%', seq_ah(OLD_A6, GD_OLD, ECA, 'dog', H_72), seq_ah(P6['INS'], GD, ECA, 'dog', H_72), .10, G4)
rule('UECL Β αουτσαιντερ χωρις FotMob ≥10%', seq_ah(OLD_A6, GD_OLD, ECB, 'dog', H_72, sidefn=side_b), seq_ah(P6['INS'], GD, ECB, 'dog', H_72, sidefn=side_b), .10, G4 + (.16, .18))
# ---------- ΣΥΝΟΛΑ LIVE
rule('UCL over Α ≥4%', seq_ou(OH_O, OA_O, TOT_OLD, UCLA, True, H_UCL, True, False), seq_ou(OH_N, OA_N, TOT90, UCLA, True, H_UCL, True, False), .04, G4, new_only=True, handicap=False)
rule('UCL over Β (μια ομαδα χωρις FotMob) ≥4%', seq_ou(OH_O, OA_O, TOT_OLD, UCLB, True, H_UCL, True, False), seq_ou(OH_N, OA_N, TOT90, UCLB, True, H_UCL, True, False), .04, G4, new_only=True, handicap=False)
rule('UECL Α over ≥−2%', seq_ou(OH_O, OA_O, TOT_OLD, ECA, True, H_72), seq_ou(OH_N, OA_N, TOT90, ECA, True, H_72), -.02, (-.06, -.04, -.02, 0., .02, .04, .06, .08), handicap=False)
rule('UECL Β under ≥14%', seq_ou(OH_O, OA_O, TOT_OLD, ECB, False, H_72), seq_ou(OH_N, OA_N, TOT90, ECB, False, H_72), .14, (.06, .08, .10, .12, .14, .16, .18), handicap=False)
# ---------- ΣΚΙΕΣ
rule('UCL αουτσαιντερ 4-10%', seq_ah(OLD_A6, GD_OLD, UCLA, 'dog', H_UCL, True), seq_ah(P6['INS'], GD, UCLA, 'dog', H_UCL, True), .04, G4, new_only=True, live=False, hi=.10)
rule('UCL under Α ≥10%', seq_ou(OH_O, OA_O, TOT_OLD, UCLA, False, H_UCL, True, False), seq_ou(OH_N, OA_N, TOT90, UCLA, False, H_UCL, True, False), .10, G4, new_only=True, handicap=False, live=False)
rule('UEL under Α ≥10%', seq_ou(OH_O, OA_O, TOT_OLD, UELA, False, H_72), seq_ou(OH_N, OA_N, TOT90, UELA, False, H_72), .10, G4, handicap=False, live=False)
rule('UEL over Α ≥4%', seq_ou(OH_O, OA_O, TOT_OLD, UELA, True, H_72), seq_ou(OH_N, OA_N, TOT90, UELA, True, H_72), .04, G4, handicap=False, live=False)
rule('UEL φαβορι εκτος ≥4%', seq_ah(OLD_A6, GD_OLD, UELA, 'fav', H_72, sidefn=lambda i: -1), seq_ah(P6['INS'], GD, UELA, 'fav', H_72, sidefn=lambda i: -1), .04, G4, live=False)
rule('UEL αουτσαιντερ ≥10%', seq_ah(OLD_A6, GD_OLD, UELA, 'dog', H_72), seq_ah(P6['INS'], GD, UELA, 'dog', H_72), .10, G4, live=False)
print('\nΣΥΝΟΨΗ (UCL = νεα μορφη)')
T = pd.DataFrame(SUM); print(T.to_string(index=False))
L = T[T.live]; print(f"LIVE συνολο: {L.n.sum():.0f} picks {L.μ.sum():+.1f}μ")
