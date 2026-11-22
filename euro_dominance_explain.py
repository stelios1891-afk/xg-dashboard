"""euro_dominance_explain.py — 9/10/2026 (Στελιος: «εξηγησε την υπερβολη στα ανισα ευρωπαικα με παραδειγματα»).
Ολα τα ευρωπαικα του δειγματος (2223-2526), σημερινη αλυσιδα (base, χωρις φετινα): οπτικη ΦΑΒΟΡΙ του μοντελου.
Καδοι κατα προβλεπομενη υπεροχη: μοντελο λ_φαβ−λ_αουτ · αγορα (Crown κλεισιμο, υπεροχη απο τη γραμμη) · πραγματικα xG · πραγματικα γκολ.
+ εντος/εκτος, CORE7-φαβ vs αλλο, + παραδειγματα 2526."""
import sys, io, json, contextlib, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
g = {'__name__': 'de'}
with contextlib.redirect_stdout(io.StringIO()):
    exec(open('euro_oppadj_test.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1), g)
G = g['g']; MIDS, SEA, COMP, GD, BASE, CROWN, picks = g['MIDS'], g['SEA'], g['COMP'], g['GD'], g['BASE'], g['CROWN'], g['picks']
S = G['S']; LGH, LGA = G['LGH'], G['LGA']; FMm = g['FMm']
XG = {}
for sea in ('2223', '2324', '2425', '2526'):
    for mid, m in json.load(open(f'data_Europe_{sea}.json', encoding='utf-8')).items():
        if not m.get('shots') or m.get('hs') is None: continue
        h, a = int(m['home']['id']), int(m['away']['id']); agg = {h: 0.0, a: 0.0}
        for s in m['shots']:
            if s.get('xg') is not None and s.get('tid') in agg: agg[s['tid']] += 0.25 if s.get('sit') == 'Penalty' else s['xg']
        XG[str(mid)] = (agg[h], agg[a], m['home'].get('name'), m['away'].get('name'))
def msup(L, oh, oa, T):
    tq = (1 / oh) / (1 / oh + 1 / oa); lo, hi = -4.5, 4.5
    for _ in range(24):
        s = (lo + hi) / 2; d = picks.gd_dist(max((T + s) / 2, .05), max((T - s) / 2, .05)); w, p = picks.p_cover(d, 1, L)
        if w / max(1 - p, 1e-9) < tq: lo = s
        else: hi = s
    return (lo + hi) / 2
LH, LA = BASE
TOP7 = g['TOP7']
rows = []
for i, mid in enumerate(MIDS):
    if mid not in XG: continue
    xh, xa, nh, na = XG[mid]
    fh = LH[i] >= LA[i]; sgn = 1 if fh else -1
    ms = msup(*CROWN[mid], LH[i] + LA[i]) * sgn if mid in CROWN else np.nan
    rows.append(dict(sea=SEA[i], comp=COMP[i], fav_home=fh, fav7=(LGH[i] if fh else LGA[i]) in TOP7, dog7=(LGA[i] if fh else LGH[i]) in TOP7,
                     fav=nh if fh else na, dog=na if fh else nh, lf=max(LH[i], LA[i]), ld=min(LH[i], LA[i]),
                     mod=abs(LH[i] - LA[i]), mkt=ms, xgf=xh if fh else xa, xgd=xa if fh else xh, gdiff=GD[i] * sgn,
                     gf=(S.gh.values[i] if fh else S.ga.values[i]), ga=(S.ga.values[i] if fh else S.gh.values[i])))
D = pd.DataFrame(rows); D['xdiff'] = D.xgf - D.xgd
BK = ((0, .3, 'ισορροπημενο (<0.3)'), (.3, .7, 'μικρο φαβορι'), (.7, 1.2, 'φαβορι'), (1.2, 1.8, 'μεγαλο φαβορι'), (1.8, 9, 'τεραστιο φαβορι (1.8+)'))
def tab(X, title):
    print(f'\n{title}')
    print(f'   {"":24s} {"n":>4s} | {"ΜΟΝΤΕΛΟ":>8s} {"ΑΓΟΡΑ":>7s} {"xG":>6s} {"ΓΚΟΛ":>6s} | λ φαβ→xG φαβ · λ αουτ→xG αουτ')
    for lo, hi, lab in BK:
        x = X[(X["mod"] >= lo) & (X["mod"] < hi)]
        if len(x) < 15: continue
        print(f'   {lab:24s} {len(x):4d} | {x["mod"].mean():+8.2f} {x.mkt.mean():+7.2f} {x.xdiff.mean():+6.2f} {x.gdiff.mean():+6.2f} | '
              f'{x.lf.mean():.2f}→{x.xgf.mean():.2f} · {x.ld.mean():.2f}→{x.xgd.mean():.2f}')
tab(D, 'ΟΛΑ τα ευρωπαικα (διαφορα γκολ υπερ φαβορι)')
tab(D[D.fav_home], 'ΦΑΒΟΡΙ ΕΝΤΟΣ')
tab(D[~D.fav_home], 'ΦΑΒΟΡΙ ΕΚΤΟΣ')
for c in ('ChampionsLeague', 'EuropaLeague', 'ConferenceLeague'):
    tab(D[D.comp == c], c)
tab(D[D.fav7 & ~D.dog7], 'φαβορι CORE7 vs αουτσαιντερ αλλης λιγκας')
tab(D[D.fav7 & D.dog7], 'CORE7 vs CORE7')
tab(D[~D.fav7 & ~D.dog7], 'καμια CORE7')
print('\nΠΑΡΑΔΕΙΓΜΑΤΑ 2526 (μεγαλα φαβορι μοντελου ≥1.5): μοντελο λ φαβ-αουτ · αγορα υπεροχη · xG · σκορ')
E = D[(D.sea == '2526') & (D['mod'] >= 1.5)].sort_values('mod', ascending=False)
for r in E.head(25).itertuples():
    print(f'   {r.fav[:20]:20s} {"(ε)" if r.fav_home else "(Χ)"} vs {r.dog[:18]:18s} [{r.comp[:4]}] μοντελο {r.lf:.2f}-{r.ld:.2f} (υπ {r.mod:+.2f}) · '
          f'αγορα {r.mkt:+.2f} · xG {r.xgf:.2f}-{r.xgd:.2f} · σκορ {r.gf}-{r.ga}')
print(f'\n   μεσοι ορ. αυτων ({len(E)}): μοντελο {E["mod"].mean():+.2f} · αγορα {E.mkt.mean():+.2f} · xG {E.xdiff.mean():+.2f} · γκολ {E.gdiff.mean():+.2f}')
