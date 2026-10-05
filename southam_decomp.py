"""
southam_decomp.py — 5/10/2026: ΔΙΟΡΘΩΣΗ ΣΥΜΠΙΕΣΗΣ της υπεροχης (το μοντελο βλεπει τα φαβορι πιο αδυναμα απο την αγορα → υπερτιμα ΟΛΑ τα dogs).
Βαθμονομηση προς την ΤΕΛΙΚΗ αγορα (Crown), LOSO ανα σεζον: msup ≈ a + k·sup_μοντελου [+ υψομετρο + συνθετικο + ζωνες ωρας + ταξιδι].
Ετσι το μοντελο «μιλα τη γλωσσα της αγορας» και μενει μονο η ΔΙΑΦΩΝΙΑ του. Μετα: ποσα dogs/φαβορι βγαινουν, ROI στο κλεισιμο ΚΑΙ στο ανοιγμα,
βαθμονομηση picks (μοντελο/αγορα/εγινε), και αν η διαφωνια εχει πληροφορια (b). Περιγραφικο — τιποτα live.
"""
import sys, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks, southam_common as C
from southam_geo import GEO
R = pd.read_csv('southam_phase3_rows_v2emps.csv', dtype={'mid': str, 'season': str})
R = R[(R.per != '1-6') & R.win.isin(['open', 'close'])].copy()
PP = pd.read_csv('southam_preds.csv', dtype={'mid': str}).set_index('mid')
R['kh'] = R.mid.map(PP.home_name).map(C.key); R['ka'] = R.mid.map(PP.away_name).map(C.key)
def hav(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    return 6371 * 2 * math.asin(math.sqrt(math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2))
R['lkm'] = [np.log1p(hav(GEO[h], GEO[a]) / 1000) for h, a in zip(R.kh, R.ka)]
R['tz'] = [GEO[h][2] - GEO[a][2] for h, a in zip(R.kh, R.ka)]
R['alt'] = [float(GEO[h][3] - GEO[a][3] > 1000) - float(GEO[h][3] - GEO[a][3] < -1000) for h, a in zip(R.kh, R.ka)]
R['turf'] = [float(GEO[h][4] == 1 and GEO[a][4] == 0) for h, a in zip(R.kh, R.ka)]
CL = R[(R.win == 'close') & (R.book == 'Crown')].drop_duplicates('mid').set_index('mid')
def fit(tr, feats):
    X = np.c_[np.ones(len(tr)), tr.sup.values] if not feats else np.c_[np.ones(len(tr)), tr.sup.values, tr[feats].values]
    b, *_ = np.linalg.lstsq(X, tr.msup.values, rcond=None); return b
def apply(d, b, feats):
    X = np.c_[np.ones(len(d)), d.sup.values] if not feats else np.c_[np.ones(len(d)), d.sup.values, d[feats].values]
    return X @ b
VAR = {'σημερα (χωρις)': None, 'αποσυμπιεση (a+k·sup)': [], '+ υψομ/συνθ/ζωνες/ταξιδι': ['alt', 'turf', 'tz', 'lkm']}
def parts(x): return [x] if (x * 4) % 2 == 0 else [x - .25, x + .25]
out = []
for lg in ('Brazil', 'MLS'):
    base = CL[CL.league == lg]
    for nm, feats in VAR.items():
        cal = {}
        for s in sorted(base.season.unique()):
            if feats is None: continue
            b = fit(base[base.season != s], feats)
            te = base[base.season == s]; cal.update(dict(zip(te.index, apply(te, b, feats))))
            if s == sorted(base.season.unique())[-1]:
                print(f'  {lg} {nm}: k = {b[1]:.2f} (συντελεστης τεντωματος· 1 = καμια αλλαγη)' + (' · ' + ' '.join(f'{f} {v:+.3f}' for f, v in zip(feats, b[2:])) if feats else ''))
        X = R[R.league == lg]
        for r in X.itertuples():
            s_ = cal.get(r.mid, r.sup) if feats is not None else r.sup
            d = picks.gd_dist_dom(max((r.tot + s_) / 2, .05), max((r.tot - s_) / 2, .05))
            for side, ln, o, oo in ((1, r.ah, r.oh, r.oa), (-1, -r.ah, r.oa, r.oh)):
                if abs(ln) < 0.5 or not (1.70 <= o <= 2.10): continue
                pw, pp = picks.p_cover(d, side, ln); e = pw * (o - 1) * (1 - picks.MARGIN) - (1 - pw - pp)
                if ln < 0:                                   # φαβορι: σωστα τεταρτα
                    e = 0.
                    for L in parts(ln):
                        a, q = picks.p_cover(d, side, L); e += (a * (o - 1) * (1 - picks.MARGIN) - (1 - a - q)) / len(parts(ln))
                if e < 0.06: continue
                cm = 0.
                for L in parts(ln):
                    a, q = picks.p_cover(d, side, L); cm += (a + 0.5 * q) / len(parts(ln))
                out.append(dict(league=lg, vr=nm, season=r.season, book=r.book, win=r.win, per=r.per, role='dog' if ln > 0 else 'fav',
                                edge=e, pnl=picks.settle(r.gd, side, ln, o), c_mod=cm, c_mkt=(1 / o) / (1 / o + 1 / oo),
                                c_act=(picks.settle(r.gd, side, ln, 2.0) + 1) / 2, sdiff=s_ - (CL.at[r.mid, 'msup'] if r.mid in CL.index else np.nan), gdres=r.gd - (CL.at[r.mid, 'msup'] if r.mid in CL.index else np.nan)))
B = pd.DataFrame(out)
def st(d, nse):
    if len(d) < 16: return f'n{len(d)//2:4d}' + ' ' * 40
    ps = d.groupby('season').pnl.mean()
    return (f'n{len(d)//2:4d} ROI {100*d.pnl.mean():+6.1f}% {d.pnl.sum()/2:+6.1f}u {int((ps > 0).sum())}/{nse} · '
            f'μοντ {100*d.c_mod.mean():.0f}%/αγορ {100*d.c_mkt.mean():.0f}%/εγινε {100*d.c_act.mean():.0f}%')
print('\nPICKS μετα τη διορθωση (edge ≥10%, 1.70-2.10, αγων 7+) — n ανα βιβλιο · ROI μεσος Crown/SBOBET · καλυψη μοντελο/αγορα/εγινε')
for lg in ('Brazil', 'MLS'):
    nse = R[R.league == lg].season.nunique()
    for role in ('dog', 'fav'):
        for win in ('close', 'open'):
            for per in ('7-14', '15+'):
                print(f' {lg:6s} {role:3s} {win:5s} {per:5s} | ' + ' | '.join(f'{nm[:14]:14s} {st(B[(B.league == lg) & (B.vr == nm) & (B.role == role) & (B.win == win) & (B.per == per) & (B.edge >= 0.10)], nse)}'
                                                                     for nm in VAR))
print('\nΠΛΗΡΟΦΟΡΙΑ της διαφωνιας μετα τη διορθωση: (γκολ − αγορα) ~ b·(μοντελο_διορθ − αγορα), ολα τα ματς, κλεισιμο Crown')
for lg in ('Brazil', 'MLS'):
    base = CL[CL.league == lg]
    for nm, feats in VAR.items():
        if feats is None:
            x = base.sup - base.msup
        else:
            cal = pd.Series(dtype=float)
            for s in sorted(base.season.unique()):
                b = fit(base[base.season != s], feats); te = base[base.season == s]; cal = pd.concat([cal, pd.Series(apply(te, b, feats), index=te.index)])
            x = cal.reindex(base.index) - base.msup
        y = base.gd - base.msup; X = np.c_[np.ones(len(x)), x.values]; c, *_ = np.linalg.lstsq(X, y.values, rcond=None); e = y.values - X @ c
        se = np.sqrt((e @ e) / (len(y) - 2) / ((x - x.mean()) ** 2).sum())
        print(f'  {lg:6s} {nm:28s} b = {c[1]:+.2f} ±{se:.2f} · μεση |διαφωνια| {x.abs().mean():.3f} γκολ')
