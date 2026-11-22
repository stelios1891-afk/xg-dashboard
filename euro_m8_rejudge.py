# -*- coding: utf-8 -*-
"""euro_m8_rejudge.py — 5/11/2026 (Στελιος: «οκ ναι»). Το harness του τεστ ειχε ΠΑΛΙΑ φορμουλα κοκκινων (uel_homefav_reds) → ξανακριση των φετινων ευρωπαικων (Μ8 βαρος 0.5, LOSO συντελεστες)
σε ΚΑΘΕ live κανονα χαντικαπ, ΧΩΡΙΣ vs ΜΕ, αποτελεσμα 90′, Crown & SBOBET (μεσος). Εισοδος απο euro_m8_dump (μιξη 60% = κυρια μηχανη, 80% = UEL φαβ εντος). Τα συνολα δεν αλλαζουν με Μ8.
ΚΑΝΟΝΕΣ (ιδια μεθοδος με το τεστ του καθε κανονα): UCL Α φαβ ≥4 σωστα τεταρτα / dog ≥10 p_cover / DNB ≥4, πρωτη εμφανιση 168-2ω, τιμιος χρονος (ucl_rule_band_test) · UEL Α γηπ φαβ ≥4, 36/24/18/12ω, μιξη 80% ·
UECL Α φαβ ≥4 / dog ≥10, 72ω-κλεισιμο (uecl_full_review) · UECL Β dog χωρις FotMob ≥10 p_cover, 72ω-κλεισιμο. 1.70-2.10.
ΚΡΙΤΗΡΙΑ (οπως 9/10 uel_homefav_inseason): (α) ROI με ≥ ROI χωρις, (β) με: ≥3/4 σεζον θετικες (UCL νεα μορφη: και οι 2), (γ) με: θετικο και στα 2 βιβλια."""
import sys, io, json, pickle, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
_SIO = io.StringIO; io.StringIO = _Q
t = open('uel_timing.py', encoding='utf-8').read(); t = t[:t.index('B = pd.DataFrame(rows)')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
t = t.replace('\nrows = []\nfor i, mid in enumerate(MIDS):', '\nrows = []\nfor i, mid in enumerate([]):')
u = {'__name__': 'ut'}
with contextlib.redirect_stdout(_Q()): exec(t, u)
sys.stdout = sys.__stdout__; sys.stdout.reconfigure(encoding='utf-8'); io.StringIO = _SIO
import picks
snap, sdist, cover_q, edge = u['snap'], u['sdist'], u['cover_q'], u['edge']
P6 = pickle.load(open('euro_m8_dump_0.6.pkl', 'rb')); P8 = pickle.load(open('euro_m8_dump_0.8.pkl', 'rb'))
MIDS, SEA, COMP, GD, FM = P6['MIDS'], np.asarray(P6['SEA']), np.asarray(P6['COMP']), P6['GD'], P6['FM']
assert MIDS == P8['MIDS'] == [str(m) for m in u['MIDS']]
_V = pickle.load(open('euro_v6_preds.pkl', 'rb')); _VI = {str(m): j for j, m in enumerate(_V['mids'])}
SH = np.array([_V['src_h'][_VI[m]] if m in _VI else '?' for m in MIDS]); SA = np.array([_V['src_a'][_VI[m]] if m in _VI else '?' for m in MIDS])
print(f"ελεγχος πηγων: FotMob+FotMob harness {FM.sum()} · euro_v6 {((SH == 'shots') & (SA == 'shots')).sum()} · διαφορες {(FM != ((SH == 'shots') & (SA == 'shots'))).sum()}")
NEW = ('2425', '2526'); SEAS = ('2223', '2324', '2425', '2526')
# ---- ελεγχος: harness vs dumps
sup = lambda L: np.asarray(L[0]) - np.asarray(L[1])
for lab, f, P in (('dump base06 (60%)', 'euro_blend_dump_base06.pkl', P6), ('dump 0.8', 'euro_blend_dump_0.8.pkl', P8)):
    D = pickle.load(open(f, 'rb')); ix = {str(x): k for k, x in enumerate(D['MIDS'])}
    j = np.array([ix.get(x, -1) for x in MIDS]); ok = (j >= 0) & FM
    dd = sup(P['BASE'])[ok] - (np.asarray(D['LH'])[j[ok]] - np.asarray(D['LA'])[j[ok]])
    cc = COMP[ok]
    print(f'ΕΛΕΓΧΟΣ harness χωρις Μ8 vs {lab}: FotMob+FotMob n={ok.sum()} |Δυπεροχης| μεσο {np.abs(dd).mean():.3f} · ' + ' · '.join(f'{c[:3]} {np.abs(dd[cc == c]).mean():.3f}' for c in sorted(set(cc))))
# ---- τιμιος χρονος UCL: ιδιος λογος sh4/sh7 προς base06 και στις δυο μηχανες
_b = pickle.load(open('euro_blend_dump_base06.pkl', 'rb')); _ib = {str(m): k for k, m in enumerate(_b['MIDS'])}
def ratio(name):
    d = pickle.load(open(f'euro_blend_dump_{name}.pkl', 'rb')); iv = {str(m): k for k, m in enumerate(d['MIDS'])}
    rh = np.array([d['LH'][iv[m]] / _b['LH'][_ib[m]] if m in iv and m in _ib and _b['LH'][_ib[m]] > 0 else 1.0 for m in MIDS])
    ra = np.array([d['LA'][iv[m]] / _b['LA'][_ib[m]] if m in iv and m in _ib and _b['LA'][_ib[m]] > 0 else 1.0 for m in MIDS])
    return rh, ra
R4, R7 = ratio('sh4'), ratio('sh7')
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
H_UCL = (168, 144, 120, 96, 72, 60, 48, 36, 24, 18, 12, 8, 6, 4, 2); H_UEL = (36, 24, 18, 12); H_UECL = (72, 60, 48, 36, 24, 18, 12, 8, 6, 4, 2, 1, 0)
def run(LL, mask, kind, thr, hs, honest=False, sidefn=None):
    out = []
    for i in np.where(mask)[0]:
        mid = MIDS[i]
        for bk in ('Crown', 'SBOBET'):
            cl = snap(mid, bk, 0)
            for side in ((1, -1) if sidefn is None else (sidefn(i),)):
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
                    e = edge(pw, pp, o)
                    if e < thr: continue
                    mv = side * (fair(cl[0], cl[1], cl[2]) - fair(L, oh, oa)) if cl else np.nan
                    out.append(dict(i=i, bk=bk, side=side, sea=SEA[i], h=h, e=e, pnl=picks.settle(float(GD[i]), side, ln, o), mv=mv)); break
    return pd.DataFrame(out, columns=['i', 'bk', 'side', 'sea', 'h', 'e', 'pnl', 'mv'])
def desc(z):
    if not len(z): return '   0 picks'
    return f"{len(z) / 2:5.1f} picks ROI {100 * z.pnl.mean():+6.1f}% {z.pnl.sum() / 2:+6.1f}μ ±{100 * z.groupby('i').pnl.mean().std() / np.sqrt(z.i.nunique()):4.1f} │ " + ' '.join(f"{s[2:]}:{100 * z[z.sea == s].pnl.mean():+.0f}" for s in SEAS if (z.sea == s).any()) + f" │ C {100 * z[z.bk == 'Crown'].pnl.mean():+.1f} S {100 * z[z.bk == 'SBOBET'].pnl.mean():+.1f} │ κινηση {z.mv.mean():+.3f}"
def judge(w, wo, seas_need):
    a = w.pnl.mean() >= wo.pnl.mean()
    ps = w.groupby('sea').pnl.mean(); b = (ps > 0).sum() >= seas_need
    bb = w.groupby('bk').pnl.mean(); c = bool((bb > 0).all()) and len(bb) == 2
    return a, b, c
TOT = []
def rule(name, P, mask, kind, thr, hs, honest=False, sidefn=None, new_only=False):
    Z0, Z1 = run(P['BASE'], mask, kind, thr, hs, honest, sidefn), run(P['INS'], mask, kind, thr, hs, honest, sidefn)
    print(f'\n{name}')
    print(f'   ΧΩΡΙΣ {desc(Z0)}'); print(f'   ΜΕ    {desc(Z1)}')
    Z4 = run(P['M4'], mask, kind, thr, hs, honest, sidefn); print(f'   Μ4    {desc(Z4)}')   # Μ4 = ο «καλυτερος» της κρισης 9/10 με σωστες κοκκινες (euro_adj_methods_emps*)
    if new_only: print(f'   νεα μορφη Μ4    {desc(Z4[Z4.sea.isin(NEW)])}')
    k0, k1 = set(zip(Z0.i, Z0.bk, Z0.side)), set(zip(Z1.i, Z1.bk, Z1.side))
    lv = Z0[[x not in k1 for x in zip(Z0.i, Z0.bk, Z0.side)]]; en = Z1[[x not in k0 for x in zip(Z1.i, Z1.bk, Z1.side)]]
    com0 = Z0[[x in k1 for x in zip(Z0.i, Z0.bk, Z0.side)]]; com1 = Z1[[x in k0 for x in zip(Z1.i, Z1.bk, Z1.side)]]
    f = lambda y: f'{len(y) / 2:.1f} picks {y.pnl.sum() / 2:+.1f}μ'
    print(f'   κοινα {f(com0)} (με Μ8 {f(com1)}) · φευγουν {f(lv)} · μπαινουν {f(en)}')
    per = pd.DataFrame({'a': Z0.groupby('i').pnl.sum() / 2, 'b': Z1.groupby('i').pnl.sum() / 2}).fillna(0); dd = per.b - per.a
    print(f'   διαφορα ΜΕ−ΧΩΡΙΣ σε μοναδες {dd.sum():+.1f}μ ±{dd.std() * np.sqrt(len(dd)):.1f}')
    if new_only:
        z0n, z1n = Z0[Z0.sea.isin(NEW)], Z1[Z1.sea.isin(NEW)]
        print(f'   νεα μορφη ΧΩΡΙΣ {desc(z0n)}'); print(f'   νεα μορφη ΜΕ    {desc(z1n)}')
        a, b, c = judge(z1n, z0n, 2)
    else:
        a, b, c = judge(Z1, Z0, 3)
    print(f"   ΚΡΙΤΗΡΙΑ: (α) ROI με ≥ χωρις {'✓' if a else '✗'} · (β) σεζον {'✓' if b else '✗'} · (γ) 2 βιβλια {'✓' if c else '✗'} → {'ΠΕΡΝΑ' if a and b and c else 'ΔΕΝ ΠΕΡΝΑ'}")
    TOT.append(dict(r=name, u0=Z0.pnl.sum() / 2, u1=Z1.pnl.sum() / 2, n0=len(Z0) / 2, n1=len(Z1) / 2, u4=Z4.pnl.sum() / 2, n4=len(Z4) / 2, ok=a and b and c))
UCLm = (COMP == 'ChampionsLeague') & FM; UELm = (COMP == 'EuropaLeague') & FM; ECm = (COMP == 'ConferenceLeague') & FM
ECB = (COMP == 'ConferenceLeague') & ((SH == 'shots') != (SA == 'shots'))
rule('UCL φαβορι ≥4%', P6, UCLm, 'fav', .04, H_UCL, True, new_only=True)
rule('UCL αουτσαιντερ ≥10%', P6, UCLm, 'dog', .10, H_UCL, True, new_only=True)
rule('UCL DNB ≥4%', P6, UCLm, 'dnb', .04, H_UCL, True, new_only=True)
rule('UEL φαβορι εντος ≥4% (μιξη 80%)', P8, UELm, 'fav', .04, H_UEL, sidefn=lambda i: 1)
rule('UEL φαβορι εντος ≥4% ΜΟΝΟ 24ω (προ-δηλωση 9/10)', P8, UELm, 'fav', .04, (24,), sidefn=lambda i: 1)
rule('UECL Α φαβορι ≥4%', P6, ECm, 'fav', .04, H_UECL)
rule('UECL Α αουτσαιντερ ≥10%', P6, ECm, 'dog', .10, H_UECL)
rule('UECL Β αουτσαιντερ χωρις FotMob ≥10%', P6, ECB, 'dog', .10, H_UECL, sidefn=lambda i: (1 if SA[i] == 'shots' else -1))
print('\nΣΥΝΟΨΗ (χωρις το 24ω, που ειναι υποσυνολο)')
T = pd.DataFrame(TOT); T = T[~T.r.str.contains('ΜΟΝΟ 24ω')]
print(T.round(1).to_string(index=False)); print(f'ΣΥΝΟΛΟ χωρις {T.u0.sum():+.1f}μ ({T.n0.sum():.0f} picks) · με {T.u1.sum():+.1f}μ ({T.n1.sum():.0f} picks) · Μ4 {T.u4.sum():+.1f}μ ({T.n4.sum():.0f} picks)')
print('\nΣΥΝΤΕΛΕΣΤΕΣ Μ8 (a, log λ ομαδας, log λ αντιπαλου, χασμα, εδρα) — ΔΕΝ γραφτηκαν στο euro_m8_coef.json')
C = json.load(open('euro_m8_coef.json', encoding='utf-8'))
print('   live 60%:', [round(x, 3) for x in C['coef']], '→ σωστες κοκκινες:', [round(float(x), 3) for x in P6['full']])
print('   live 80%:', [round(x, 3) for x in C['coef_by_blend']['0.8']], '→ σωστες κοκκινες:', [round(float(x), 3) for x in P8['full']])
