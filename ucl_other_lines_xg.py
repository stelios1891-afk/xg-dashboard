"""ucl_other_lines_xg.py — 10/10/2026 (Στελιος: «μπορεις να συγκρινεις τα μπετς μας με τα τελικα xg και να βρεις το fair xg? οπως στο Pick History»).
Picks των γραμμων 0 / −0.25 / +0.25 (UCL κατηγορια Α, @4%, πρωτη εμφανιση ≤72ω) + για συγκριση τα picks του live κανονα (|γραμμη| ≥0.5).
Για καθε pick: fair xG = η τιμη που δικαιολογουν τα ΤΕΛΙΚΑ xG του ματς (picks.gd_dist + p_cover, ιδια μεθοδος με το Pick History),
αξια xG = τιμη / fair − 1. Αν η αξια xG ειναι κοντα στο ROI → το κερδος το «επαιξαν» οι ομαδες· αν πολυ χαμηλοτερη → τυχη στο σκορ.
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

# ---- τελικα xG ανα ματς (σουτ FotMob) ----
XG = {}
for f in glob.glob('data_Europe_*.json'):
    for mid, m in json.load(open(f, encoding='utf-8')).items():
        sh = m.get('shots') or []
        if not sh: continue
        hid = int(m['home']['id'])
        xh = sum(s['xg'] for s in sh if s.get('xg') is not None and int(s['tid']) == hid)
        xa = sum(s['xg'] for s in sh if s.get('xg') is not None and int(s['tid']) != hid)
        XG[str(mid)] = (xh, xa)
def xg_value(i, side, ln, o):
    x = XG.get(str(MIDS[i]))
    if not x: return np.nan, np.nan
    dist = picks.gd_dist(max(x[0], 0.05), max(x[1], 0.05))          # ιδια μεθοδος με το Pick History
    pw, pp = picks.p_cover(dist, side, ln)
    if pw <= 0: return np.nan, np.nan
    fair = (1 - pp) / pw
    return fair, o / fair - 1
# ροη του live κανονα (|γραμμη| ≥0.5) για συγκριση
rule_rows = []
for i in np.where(ucl)[0]:
    if SRCC[i] != 'FF': continue
    D = sdist(LH_N[i], LA_N[i])
    for bk in ('Crown', 'SBOBET'):
        for h in HS:
            s = SN.get((i, bk, h))
            if not s: continue
            L, oh, oa = s
            for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                if not (1.70 <= o <= 2.10) or abs(ln) < 0.5: continue
                role = 'fav' if ln < 0 else 'dog'
                pw, pp = cover_q(D, side, ln) if role == 'fav' else picks.p_cover(D, side, ln)
                e = edge(pw, pp, o)
                if e >= (0.10 if role == 'fav' else 0.04):
                    rule_rows.append(dict(i=i, bk=bk, h=h, grp='κανονας ' + role, side=side, sea=SEA[i], ln=ln, od=o, home=side == 1, e=e,
                                          pnl=picks.settle(GD[i], side, ln, o)))
RR = pd.DataFrame(rule_rows).sort_values('h', ascending=False).groupby(['i', 'bk', 'side']).head(1)
def table(F, lab):
    F = F.copy()
    v = [xg_value(r.i, r.side, r.ln, r.od) for r in F.itertuples()]
    F['fair'] = [a for a, b in v]; F['xv'] = [b for a, b in v]
    F = F.dropna(subset=['xv'])
    if len(F) == 0:
        print(f'   {lab:24s} —'); return
    n = F.groupby('bk').size().mean()
    roi = F.groupby('bk').pnl.mean().mean(); xv = F.groupby('bk').xv.mean().mean()
    pos = (F.xv > 0).mean()
    ps = F.groupby('sea').agg(r=('pnl', 'mean'), x=('xv', 'mean'))
    print(f'   {lab:24s} {n:4.0f} picks · ROI πραγματικο {100 * roi:+6.1f}% · ΑΞΙΑ xG {100 * xv:+6.1f}% · τιμη {F.od.mean():.2f} vs fair xG {F.fair.median():.2f} (διαμεσος) · '
          f'θετικη αξια xG {100 * pos:.0f}% · ανα σεζον ROI/xG: ' + ' '.join(f'{s[2:]} {100 * a.r:+.0f}/{100 * a.x:+.0f}' for s, a in ps.iterrows()))
print(NL + 'ΣΥΓΚΡΙΣΗ ΜΕ ΤΑ ΤΕΛΙΚΑ xG (οπως Pick History: fair = τιμη που δικαιολογουν τα τελικα xG, αξια xG = τιμη/fair − 1)')
print('UCL κατηγορια Α · edge ≥4% (κανονας: φαβ ≥10% / dog ≥4%) · πρωτη εμφανιση ≤72ω · Crown/SBOBET μεσος')
for lab, seas in (('ΚΑΙ ΟΙ 4 ΣΕΖΟΝ', SEAS), ('ΝΕΑ ΜΟΡΦΗ', NEW)):
    print(NL + f'== {lab}')
    for g in GRPS:
        F4 = first(R[(R.grp == g) & R.sea.isin(seas)], 0.04)
        table(F4, g)
        table(F4[F4.home], '   εντος'); table(F4[~F4.home], '   εκτος')
    for role in ('fav', 'dog'):
        table(RR[(RR.grp == 'κανονας ' + role) & RR.sea.isin(seas)], f'(συγκριση) κανονας {role}')
