"""ucl_other_lines_deep.py — 10/10/2026 (Στελιος: «ειμαι αισιοδοξος και για τις 3 ... να δεις ποσο μπορουμε να τις εμπιστευτουμε»).
UCL κατηγορια Α, κυριες γραμμες 0 (DNB) / −0.25 / +0.25 (εκτος live κανονα |γραμμη| ≥0.5), live μηχανη χαντικαπ, σωστα τεταρτα,
1.70-2.10, πρωτη εμφανιση ≤72ω, Crown & SBOBET μεσος. ΠΡΟ-ΔΗΛΩΜΕΝΑ ανα γραμμη (@4%):
  Κ1 θετικο και στα 2 βιβλια, ≥3/4 σεζον θετικες ΚΑΙ οι 2 σεζον νεας μορφης θετικες.
  Κ2 κατωφλι απο LOSO (0-14%) → εκτος δειγματος ROI >0.
  Κ3 CLV: η αγορα κινειται ΠΡΟΣ το pick μετα την εισοδο (μεση μεταβολη «διαφορας που δικαιολογει η τιμη» >0).
  Κ4 βαθμονομηση: |P κερδους μοντελου − πραγματικο| ≤ max(5 μοναδες, |αγορα − πραγματικο|).
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

NL = chr(10)
LH_N, LA_N, sdist, cover_q, edge, snap_ah, GD = (u[k] for k in ('LH_N', 'LA_N', 'sdist', 'cover_q', 'edge', 'snap', 'GD'))
LH_N = np.asarray(LH_N, float); LA_N = np.asarray(LA_N, float); GD = np.asarray(GD, float)
SEAS = ('2223', '2324', '2425', '2526'); NEW = ('2425', '2526')
HS = (72, 60, 48, 36, 24, 18, 12, 8, 6, 4, 2, 1, 0)
GRPS = ('0 (DNB)', '−0.25 (δινει)', '+0.25 (παιρνει)')
def grp_of(ln):
    if abs(ln) >= 0.5: return None
    if abs(ln) < 0.01: return '0 (DNB)'
    return '−0.25 (δινει)' if ln < 0 else '+0.25 (παιρνει)'
rows = []; SN = {}
for i in np.where(ucl)[0]:
    if SRCC[i] != 'FF': continue
    D = sdist(LH_N[i], LA_N[i]); mid = MIDS[i]
    for bk in ('Crown', 'SBOBET'):
        for h in HS:
            s = snap_ah(mid, bk, h)
            if not s: continue
            L, oh, oa = s; SN[(i, bk, h)] = (L, oh, oa)
            for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                if not (1.70 <= o <= 2.10): continue
                g = grp_of(ln)
                if g is None: continue
                pw, pp = cover_q(D, side, ln)
                rows.append(dict(i=i, bk=bk, h=h, grp=g, side=side, sea=SEA[i], ln=ln, od=o, home=side == 1,
                                 mfav=(LH_N[i] > LA_N[i]) == (side == 1), pw=pw, pp=pp,
                                 e=edge(pw, pp, o), pnl=picks.settle(GD[i], side, ln, o)))
R = pd.DataFrame(rows)
def implied_margin(i, L, oh, oa):
    """διαφορα γκολ (γηπεδουχος) που δικαιολογει η τιμη της αγορας στη γραμμη L (χωρις γκανιοτα), με το συνολο του μοντελου"""
    q = (1 / oh) / (1 / oh + 1 / oa); T = LH_N[i] + LA_N[i]; lo, hi = -4.0, 4.0
    for _ in range(26):
        M = (lo + hi) / 2
        pw, pp = cover_q(sdist(max((T + M) / 2, .05), max((T - M) / 2, .05)), 1, L)
        r = pw / max(1 - pp, 1e-9)
        if r < q: lo = M
        else: hi = M
    return (lo + hi) / 2
def first(x, thr):
    y = x[x.e >= thr].sort_values('h', ascending=False)
    return y.groupby(['i', 'bk', 'side']).head(1).copy()
def enrich(F):
    F = F.copy()
    pc, mvb, mva, oc = [], [], [], []
    for r in F.itertuples():
        c = SN.get((r.i, r.bk, 0))
        hs = [h for h in HS if (r.i, r.bk, h) in SN]
        m_e = implied_margin(r.i, *SN[(r.i, r.bk, r.h)]) * r.side
        m_0 = implied_margin(r.i, *SN[(r.i, r.bk, hs[0])]) * r.side
        if c:
            L, oh, oa = c; ln = L if r.side == 1 else -L; o = oh if r.side == 1 else oa
            pc.append(picks.settle(GD[r.i], r.side, ln, o)); oc.append(o)
            mva.append(implied_margin(r.i, *c) * r.side - m_e)
        else:
            pc.append(np.nan); oc.append(np.nan); mva.append(np.nan)
        mvb.append(m_e - m_0)
    F['pc'] = pc; F['oc'] = oc; F['mv_after'] = mva; F['mv_before'] = mvb
    return F
def cc(x, close=True):
    if len(x) == 0: return '—'
    m = x.groupby('bk').pnl.mean(); n = x.groupby('bk').size().mean(); ps = x.groupby('sea').pnl.mean()
    s = (f'{n:4.0f} picks {100 * m.mean():+6.1f}% [C {100 * m.get("Crown", np.nan):+.0f} / S {100 * m.get("SBOBET", np.nan):+.0f}] μον {m.mean() * n:+5.1f} ('
         + ' '.join(f'{s[2:]} {100 * v:+.0f}' for s, v in ps.items()) + ')')
    if close and 'pc' in x:
        s += f' · αν περιμενα κλεισ. {100 * x.dropna(subset=["pc"]).groupby("bk").pc.mean().mean():+.1f}%'
    return s
K = {}
for g in GRPS:
    X = R[R.grp == g]
    F4 = enrich(first(X, 0.04))
    print(NL + '=' * 100 + NL + f'ΓΡΑΜΜΗ {g} — UCL κατηγορια Α · edge ≥4% · πρωτη εμφανιση ≤72ω (τιμη εκεινης της στιγμης)')
    print(f'   ΟΛΑ 4 σεζον: {cc(F4)}')
    print(f'   νεα μορφη:   {cc(F4[F4.sea.isin(NEW)])}')
    m = F4.groupby('bk').pnl.mean(); ps = F4.groupby('sea').pnl.mean(); psn = ps[ps.index.isin(NEW)]
    k1 = bool((m > 0).all()) and (ps > 0).sum() >= 3 and len(psn) == 2 and bool((psn > 0).all())
    # LOSO κατωφλι
    GR = np.round(np.arange(0, 0.15, 0.02), 2); outs = []
    for hold in SEAS:
        tr = X[X.sea != hold]
        sc = {t: first(tr, t).groupby('bk').pnl.mean().mean() for t in GR}
        t = max(sc, key=lambda k: sc[k]); te = first(X[X.sea == hold], t)
        outs.append((hold, t, te.groupby('bk').pnl.mean().mean() if len(te) else np.nan, te.groupby('bk').size().mean() if len(te) else 0))
    tot_n = sum(o[3] for o in outs); loso = sum(o[2] * o[3] for o in outs if o[3]) / max(tot_n, 1)
    k2 = loso > 0
    print('   LOSO κατωφλι: ' + ' · '.join(f'{o[0]} διαλεξε ≥{int(o[1] * 100)}% → {100 * o[2]:+.0f}% ({o[3]:.0f})' for o in outs) + f' · ΣΥΝΟΛΟ εκτος δειγματος {100 * loso:+.1f}% ({tot_n:.0f})')
    # CLV
    a = F4.mv_after.dropna()
    k3 = a.mean() > 0
    print(f'   ΑΓΟΡΑ ΜΕΤΑ ΤΗΝ ΕΙΣΟΔΟ: κινηση διαφορας προς εμας {a.mean():+.3f} γκολ (θετικο = η αγορα ηρθε προς εμας) · '
          f'ηρθε προς εμας {100 * (a > 0.02).mean():.0f}% / κοντρα {100 * (a < -0.02).mean():.0f}% · τιμη {F4.od.mean():.2f} → κλεισ. {F4.oc.mean():.2f}')
    # βαθμονομηση
    pred = (F4.pw / (1 - F4.pp).clip(lower=1e-9)).mean()
    res = F4.copy(); res['win'] = res.pnl > 0; res['push'] = res.pnl == 0
    real = (res.win.sum() + 0.0) / max((~res.push).sum(), 1)
    mk = (1 / F4.od / (1 / F4.od + 1 / np.where(F4.side == 1, [SN[(r.i, r.bk, r.h)][2] for r in F4.itertuples()], [SN[(r.i, r.bk, r.h)][1] for r in F4.itertuples()]))).mean()
    k4 = abs(pred - real) <= max(0.05, abs(mk - real))
    print(f'   ΒΑΘΜΟΝΟΜΗΣΗ (P κερδους χωρις push): μοντελο {100 * pred:.1f}% · αγορα {100 * mk:.1f}% · πραγματικο {100 * real:.1f}% (n{(~res.push).sum()})')
    # χρονισμος
    print('   ΧΡΟΝΙΣΜΟΣ (ποτε πρωτοβγηκε):')
    for hi, lo, wl in ((72, 72, '72ω'), (60, 48, '60-48ω'), (36, 24, '36-24ω'), (18, 8, '18-8ω'), (6, 0, '6ω-κλεισ')):
        y = F4[(F4.h <= hi) & (F4.h >= lo)]
        if len(y): print(f'      {wl:9s} {cc(y)} · κοντρα πριν {y.mv_before.mean():+.2f} · κινηση μετα {y.mv_after.mean():+.2f}')
    print('   ΠΟΙΑ ΠΛΕΥΡΑ: ' + ' · '.join(f'{lab}: {cc(F4[msk], False)}' for lab, msk in (('φαβορι μοντελου', F4.mfav), ('αουτσαιντερ μοντελου', ~F4.mfav))))
    print('   ΕΝΤΟΣ/ΕΚΤΟΣ: ' + ' · '.join(f'{lab}: {cc(F4[msk], False)}' for lab, msk in (('εντος', F4.home), ('εκτος', ~F4.home))))
    print(f'   ΚΡΙΤΗΡΙΑ: Κ1 {"✓" if k1 else "✗"} · Κ2 {"✓" if k2 else "✗"} · Κ3 {"✓" if k3 else "✗"} · Κ4 {"✓" if k4 else "✗"}')
    K[g] = (k1, k2, k3, k4)
print(NL + 'ΣΥΝΟΨΗ: ' + ' · '.join(f'{g}: {sum(v)}/4' for g, v in K.items()))
