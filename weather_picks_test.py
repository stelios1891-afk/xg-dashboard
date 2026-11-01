"""
weather_picks_test.py — 6/10/2026 (Στελιος «τρεξτα»): ΒΡΟΧΗ πανω στα ΠΡΑΓΜΑΤΙΚΑ picks CORE7 (ιδια παραγωγη picks με manager_picks_test:
μηχανη live, dogs 15+ με αγκυρα στις κοντες, φαβορι 15+ αγκυρα .7 σωστα τεταρτα ≥10%, dogs 7-14 χαρτινα · κλεισιμο Pinnacle/Crown/Bet365 · 2223-2526).
Βροχη: (Α) ΠΡΟΓΝΩΣΗ 1 μερα πριν (Open-Meteo, 2024+) — αυτο που ξερεις · (Β) σταθμος (Meteostat) — αυτο που εγινε.
ΠΡΟ-ΔΗΛΩΣΗ ΦΙΛΤΡΟΥ «κοβω picks υπερ ΓΗΠΕΔΟΥΧΟΥ οταν η προγνωση 1 μερα λεει βροχη ≥2mm»:
(1) τα κομμενα αρνητικα σε ≥2/3 βιβλια, (2) αρνητικα σε ≥2/3 σεζον με προγνωση, (3) n ≥ 15 ανα βιβλιο, (4) οι μοναδες των υπολοιπων ≥ σημερα σε ≥2/3 βιβλια.
"""
import sys, io, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
s = open('core7_sos15_final.py', encoding='utf-8').read(); s = s[:s.index('RES = {}')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass')
g = {'__name__': 'sf'}
with contextlib.redirect_stdout(_Q()): exec(s, g)
D, run_L, load, NG, picks, ev_ok = g['D'], g['run_L'], g['load'], g['NG'], g['picks'], g['ev_ok']
xh, xa, _ = load('cur_0.75_6_13~emps'); D['xh'] = xh; D['xa'] = xa
S0, SA = run_L(0, 0, 6), run_L(0.5, 0, 6); S7 = S0 + 0.7 * (SA - S0); Tt = xh + xa
P = []
for i in np.where((D.md >= 6).values)[0]:
    r = D.loc[i]; per = '15+' if r.md >= 14 else '7-14'
    quotes = [('Pinnacle', (r.L, r.ah, r.aa) if r.L == r.L else None)] + [(bk, (NG.get((r.mid, bk)) or (None, None))[1]) for bk in ('Crown', 'Bet365')]
    for bk, q in quotes:
        if q is None or q[0] != q[0]: continue
        L, oh, oa = q
        sp = S0[i] + ((SA[i] - S0[i]) if abs(L) in (0.5, 0.75) else 0.0)
        for b in picks.evaluate_bet(max((Tt[i] + sp) / 2, .05), max((Tt[i] - sp) / 2, .05), L, oh, oa):
            P.append(dict(mid=str(r.mid), book=bk, season=r.season, per=per, role='dog', home=b['side'] == 1, pnl=picks.settle(r.gd, b['side'], b['hcap'], b['odds'])))
        if per == '15+' and abs(L) >= 0.5:
            side = 1 if L < 0 else -1; ud = -abs(L); o = oh if side == 1 else oa
            if 1.70 <= o <= 2.10:
                dist = picks.gd_dist_dom(max((Tt[i] + S7[i]) / 2, .05), max((Tt[i] - S7[i]) / 2, .05))
                if ev_ok(dist, side, ud, o) >= 0.10:
                    P.append(dict(mid=str(r.mid), book=bk, season=r.season, per=per, role='fav', home=side == 1, pnl=picks.settle(r.gd, side, ud, o)))
P = pd.DataFrame(P)
OM = pd.read_pickle('weather_rows_om.pkl')[['mid', 'roof', 'f1_rain', 'rain']].rename(columns={'rain': 'rain_era5'})
MS = pd.read_pickle('weather_rows_ms.pkl')[['mid', 'rain']].rename(columns={'rain': 'rain_st'})
X = P.merge(OM, on='mid', how='left').merge(MS, on='mid', how='left')
X = X[X.roof != True]
BK = ('Pinnacle', 'Crown', 'Bet365')
def fm(d):
    if len(d) < 5: return f'n{len(d):4d}' + ' ' * 22
    ps = d.groupby('season').pnl.mean()
    return f'n{len(d):4d} {100*d.pnl.mean():+6.1f}% {d.pnl.sum():+6.1f}u {int((ps > 0).sum())}/{ps.size}'
def show(sub, lab):
    print(f'\n[{lab}] ολα: ' + ' | '.join(fm(sub[sub.book == b]) for b in BK))
    F = sub[sub.f1_rain.notna()]
    print(f'   με προγνωση (2024+){"":24s} ' + ' | '.join(fm(F[F.book == b]) for b in BK))
    for nm, c in (('ΥΠΕΡ γηπεδουχου · προγνωση ≥1mm', F.home & (F.f1_rain >= 1)), ('ΥΠΕΡ γηπεδουχου · προγνωση ≥2mm', F.home & (F.f1_rain >= 2)),
                  ('ΥΠΕΡ φιλοξενουμενου · προγνωση ≥1mm', ~F.home & (F.f1_rain >= 1)), ('ΥΠΕΡ φιλοξενουμενου · προγνωση ≥2mm', ~F.home & (F.f1_rain >= 2))):
        x = F[c]; print(f'   {nm:44s} ' + ' | '.join(fm(x[x.book == b]) for b in BK))
    S = sub[sub.rain_st.notna()]
    for nm, c in (('ΥΠΕΡ γηπεδουχου · σταθμος ≥2mm (εγινε)', S.home & (S.rain_st >= 2)), ('ΥΠΕΡ φιλοξενουμενου · σταθμος ≥2mm (εγινε)', ~S.home & (S.rain_st >= 2))):
        x = S[c]; print(f'   {nm:44s} ' + ' | '.join(fm(x[x.book == b]) for b in BK))
    cut = F[F.home & (F.f1_rain >= 2)]; keep = F[~(F.home & (F.f1_rain >= 2))]
    c1 = sum(cut[cut.book == b].pnl.sum() < 0 for b in BK) >= 2
    ps = cut.groupby('season').pnl.mean(); c2 = int((ps < 0).sum()) >= 2
    c3 = min(len(cut[cut.book == b]) for b in BK) >= 15
    c4 = sum(keep[keep.book == b].pnl.sum() >= F[F.book == b].pnl.sum() for b in BK) >= 2
    print(f'   ΚΡΙΣΗ «κοβω υπερ γηπεδουχου σε προγνωση ≥2mm»: (1){"✓" if c1 else "✗"} (2){"✓" if c2 else "✗"} ({int((ps < 0).sum())}/{ps.size}) (3){"✓" if c3 else "✗"} (4){"✓" if c4 else "✗"} → '
          + ('ΠΕΡΝΑ' if (c1 and c2 and c3 and c4) else 'οχι'))
show(X[(X.role == 'dog') & (X.per == '15+')], 'ΑΟΥΤΣΑΙΝΤΕΡ 15+ (live)')
show(X[(X.role == 'fav') & (X.per == '15+')], 'ΦΑΒΟΡΙ 15+ (live)')
show(X[(X.role == 'dog') & (X.per == '7-14')], 'ΑΟΥΤΣΑΙΝΤΕΡ 7-14 (χαρτινα)')
show(X[X.per == '15+'], 'ΟΛΑ ΤΑ PICKS 15+')
