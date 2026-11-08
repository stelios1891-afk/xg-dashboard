"""uel_value_stretch_combo.py — 15/10/2026 (Στελιος: «το θεμα ειναι να κοβει κακα αουτσαιντερ και να προσθετει φαβορι · δοκιμασε αξια + τεντωμα στις
εκτος top-5 · διαφορετικα βαρη και βρες μεσω LOSO το καλυτερο»).
ΜΟΝΤΕΛΟ (μονο Europa): 1) ΤΕΝΤΩΜΑ μονο ομαδων εκτος top-5: log λ_γηπ += b·(t_γηπ·[εκτος top-5] − t_φιλ·[εκτος top-5])/2 (φιλ αντιστροφα)
                       2) ΑΞΙΑ: διαφορα = (1−w)·(μετα το 1) + w·«τι λεει η αξια ενδεκαδας» · συνολο γκολ ιδιο
ΒΑΡΗ: b ∈ {0, −0.25, −0.5, −0.75} × w ∈ {0, 0.25, 0.5, 0.75} (16 συνδυασμοι).
 Α) για καθε συνδυασμο, picks με τους κανονες UEL (φαβ ≥4% σωστα τεταρτα ≤−0.5 · dog ≥10% p_cover ≥+0.5 · 1.70-2.10 · πρωτη εμφανιση ≤72ω,
    Crown & SBOBET) — κατηγορια Α & Β: φαβορι / αουτσαιντερ, ROI, μοναδες
 Β) LOSO: για καθε σεζον διαλεγεται ο συνδυασμος απο τις ΑΛΛΕΣ 3 (1: μεγιστη πιθανοφανεια γκολ · 2: μεγιστες μοναδες picks) → αποτελεσμα στην κρατημενη
 Γ) για τον LOSO-συνδυασμο: τι ΚΟΒΕΙ / τι ΠΡΟΣΘΕΤΕΙ ανα αγορα vs σημερινο.
"""
import sys
exec(open("euro_value_filter_check.py", encoding="utf-8").read().split("# πλευρα ΧΩΡΙΣ FotMob")[0])
NL = chr(10)
x = A[(A.comp == 'EuropaLeague') & A.hasv].reset_index(drop=True); seas = sorted(x.sea.unique())
import os as _os, pickle as _pk
XGB = _os.environ.get('XG_BASE')               # 15/10: βαση με αλλο μεριδιο xG (π.χ. 0.8 / 1.0) απο euro_blend_dump_* (ως λογος προς το 0.6)
if XGB:
    _d6 = _pk.load(open('euro_blend_dump_0.6.pkl', 'rb')); _dx = _pk.load(open(f'euro_blend_dump_{XGB}.pkl', 'rb'))
    _i6 = {str(m): k for k, m in enumerate(_d6['MIDS'])}; _ix = {str(m): k for k, m in enumerate(_dx['MIDS'])}
    _ms = [str(MIDS[int(i)]) for i in x.i]
    x['lh'] = x.lh.values * np.array([_dx['LH'][_ix[m]] / _d6['LH'][_i6[m]] if m in _ix and m in _i6 and _d6['LH'][_i6[m]] > 0 else 1.0 for m in _ms])
    x['la'] = x.la.values * np.array([_dx['LA'][_ix[m]] / _d6['LA'][_i6[m]] if m in _ix and m in _i6 and _d6['LA'][_i6[m]] > 0 else 1.0 for m in _ms])
    print(f'ΒΑΣΗ: μοντελο με {int(float(XGB) * 100)}% xG')
x['nh'] = (~x.lgh.isin(TOP5)).astype(float); x['na'] = (~x.lga.isin(TOP5)).astype(float)
x['zt'] = (x.th * x.nh - x.ta * x.na) / 2
x['vm'] = [VF[s][0] * lv + VF[s][1] for s, lv in zip(x.sea, x.lv_)]
def lamC(y, b, w):
    lh = y.lh.values * np.exp(b * y.zt.values); la = y.la.values * np.exp(-b * y.zt.values)
    if w > 0:
        T = lh + la; m = (1 - w) * (lh - la) + w * y.vm.values
        lh = np.maximum((T + m) / 2, .05); la = np.maximum((T - m) / 2, .05)
    return lh, la
BS = (0.0, -0.25, -0.5, -0.75); WS = (0.0, 0.25, 0.5, 0.75)
COMBOS = [(b, w) for b in BS for w in WS]
import os
if os.environ.get('COMBO_SPLIT'): COMBOS = [(0.0, 0.0), (0.0, 0.5), (-0.25, 0.75), (-0.75, 0.75)]
# στιγμιοτυπα μια φορα
HSP = [h for h in HS if h > 0]
SN = {}
for r in x.itertuples():
    mid = str(MIDS[int(r.i)])
    for bk in ('Crown', 'SBOBET'):
        SN[(int(r.i), bk, 0)] = snapT(mid, bk, 0)
        for h in HSP: SN[(int(r.i), bk, h)] = snapT(mid, bk, h)
MC = {}
def mcl(i, bk):
    k = (i, bk)
    if k not in MC: s = SN[(i, bk, 0)]; MC[k] = implied_margin(i, *s) if s else np.nan
    return MC[k]
def picks_for(lh, la):
    out = []
    for k_, r in x.iterrows():
        i = int(r.i); D_ = sdist(lh[k_], la[k_])
        for bk in ('Crown', 'SBOBET'):
            got = set()
            for h in HSP:
                s = SN[(i, bk, h)]
                if not s: continue
                L, oh, oa = s
                for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                    if side in got or not (1.70 <= o <= 2.10): continue
                    if ln <= -0.5: f = cover_q; th = .04; kind = 'φαβ'
                    elif ln >= 0.5: f = picks.p_cover; th = .10; kind = 'dog'
                    else: continue
                    if edge(*f(D_, side, ln), o) < th: continue
                    got.add(side)
                    out.append(dict(i=i, side=side, bk=bk, cat=r['cat'], sea=r['sea'], kind=kind, ven='εντος' if side == 1 else 'εκτος', pnl=picks.settle(GD[i], side, ln, o)))
    return pd.DataFrame(out)
PK = {}; LL = {}
for b, w in COMBOS:
    lh, la = lamC(x, b, w); PK[(b, w)] = picks_for(lh, la)
    LL[(b, w)] = {s: ll(x[x.sea == s], lh[(x.sea == s).values], la[(x.sea == s).values]) for s in seas}
def u(y): return y.groupby('bk').pnl.sum().mean() if len(y) else 0.0
def cell(y):
    if len(y) == 0: return '—'
    m = y.groupby('bk').pnl.mean(); n = y.groupby('bk').size().mean(); return f'{n:3.0f} {100 * m.mean():+5.0f}% {m.mean() * n:+5.1f}μ'
if os.environ.get('COMBO_SPLIT'):
    print('ΦΑΒΟΡΙ ΚΑΤΗΓΟΡΙΑΣ Α ΧΩΡΙΣΜΕΝΑ (εντος / εκτος) ανα συνδυασμο · κανονικο μοντελο, πρωτη εμφανιση ≤72ω')
    for b, w in COMBOS:
        P = PK[(b, w)]
        print(f'   b {b:+.2f} / w {w:.2f} │ εντος {cell(P[(P.cat == "A") & (P.kind == "φαβ") & (P.ven == "εντος")])} │ εκτος {cell(P[(P.cat == "A") & (P.kind == "φαβ") & (P.ven == "εκτος")])}')
    sys.exit()
print('Α) ΚΑΘΕ ΣΥΝΔΥΑΣΜΟΣ (ολες οι σεζον) — picks ανα βιβλιο · ROI · μοναδες')
print(f'   {"τεντωμα b / αξια w":20s} │ {"Α φαβορι":>18s} │ {"Α αουτσαιντερ":>18s} │ {"Β φαβορι":>18s} │ {"Β αουτσαιντερ":>18s} │ {"ΣΥΝΟΛΟ":>18s} │ πιθανοφανεια (vs σημερινο)')
for b, w in COMBOS:
    P = PK[(b, w)]; dl = sum(LL[(b, w)].values()) - sum(LL[(0.0, 0.0)].values())
    c = [cell(P[(P.cat == c_) & (P.kind == k)]) for c_, k in (('A', 'φαβ'), ('A', 'dog'), ('B', 'φαβ'), ('B', 'dog'))]
    print(f'   b {b:+.2f} / w {w:.2f}      │ ' + ' │ '.join(f'{v:>18s}' for v in c) + f' │ {cell(P):>18s} │ {dl:+6.1f}')
print(f'{NL}Β) LOSO — συνδυασμος απο τις αλλες 3 σεζον')
for crit in ('πιθανοφανεια', 'μοναδες picks'):
    outs = []; ch = []
    for s in seas:
        if crit == 'πιθανοφανεια':
            best = max(COMBOS, key=lambda c: sum(v for ss, v in LL[c].items() if ss != s))
        else:
            best = max(COMBOS, key=lambda c: u(PK[c][PK[c].sea != s]))
        ch.append(best); outs.append(PK[best][PK[best].sea == s])
    Z = pd.concat(outs); Z0 = PK[(0.0, 0.0)]
    print(f'   κριτηριο {crit:14s}: ' + ' · '.join(f'{s[2:]}: b {c[0]:+.2f} w {c[1]:.2f}' for s, c in zip(seas, ch)))
    for nm, f in (('Α φαβορι', lambda y: (y.cat == 'A') & (y.kind == 'φαβ')), ('Α αουτσαιντερ', lambda y: (y.cat == 'A') & (y.kind == 'dog')),
                  ('Β φαβορι', lambda y: (y.cat == 'B') & (y.kind == 'φαβ')), ('Β αουτσαιντερ', lambda y: (y.cat == 'B') & (y.kind == 'dog')), ('ΣΥΝΟΛΟ', lambda y: y.kind.notna())):
        a = Z0[f(Z0)]; z = Z[f(Z)]
        print(f'      {nm:14s} σημερινο {cell(a):>18s} → εκτος δειγματος {cell(z):>18s} · σεζον ' +
              ' '.join(f'{s[2:]}:{100 * z[z.sea == s].pnl.mean():+.0f}' for s in seas))
# Γ) κοβει / προσθετει για τον πιο συχνο συνδυασμο του κριτηριου πιθανοφανειας
from collections import Counter
bestc = Counter(max(COMBOS, key=lambda c: sum(v for ss, v in LL[c].items() if ss != s)) for s in seas).most_common(1)[0][0]
P0 = PK[(0.0, 0.0)]; P1 = PK[bestc]
k0 = set(zip(P0.i, P0.side, P0.bk)); k1 = set(zip(P1.i, P1.side, P1.bk))
print(f'{NL}Γ) ΣΥΝΔΥΑΣΜΟΣ b {bestc[0]:+.2f} / w {bestc[1]:.2f} vs σημερινο — τι ΚΟΒΕΙ / τι ΠΡΟΣΘΕΤΕΙ')
for c_ in ('A', 'B'):
    for k in ('φαβ εντος', 'φαβ εκτος', 'dog'):
        kk = k.split()[0]; vv = k.split()[1] if ' ' in k else None
        a = P0[(P0.cat == c_) & (P0.kind == kk) & ((P0.ven == vv) if vv else True)]; bq = P1[(P1.cat == c_) & (P1.kind == kk) & ((P1.ven == vv) if vv else True)]
        cut = a[[t not in k1 for t in zip(a.i, a.side, a.bk)]]; add = bq[[t not in k0 for t in zip(bq.i, bq.side, bq.bk)]]
        print(f'   {c_} {k:12s} σημερινο {cell(a):>18s} │ ΚΟΒΕΙ {cell(cut):>18s} │ ΠΡΟΣΘΕΤΕΙ {cell(add):>18s} │ νεο {cell(bq):>18s}')
