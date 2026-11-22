"""uel_late_under_test.py — 14/10/2026 (Στελιος: «δοκιμασε το under κατηγορια Α»). ΑΚΡΙΒΩΣ το uel_late_over_test για UNDER
(10/10 under Α: LOSO εκτος δειγματος +9.8% αλλα νεα μορφη @4% −3% → δεν περασε). Αρχικη περιγραφη:
over Europa League με ΑΡΓΗ εισοδο.
Ιστορικο: 10/10 (uel_full_review) over UEL θετικα σε καθε κατωφλι με εισοδο ≤72ω αλλα ΔΕΝ περασαν (2526 αρνητικο, LOSO +2.9%)·
χρονισμος 36-12ω +23.6%. 14/10 (uel_lineup_rule4) τιμη 1ω: μοντελο over +10%.
ΙΔΙΑ live μηχανη (W2, ισοπαλιες ×0.85), ΜΟΝΟ FotMob+FotMob (κατηγορια Α, οπως ο scanner), 1.70-2.10, Crown & SBOBET, ενα pick ανα ματς/βιβλιο.
ΠΑΡΑΘΥΡΑ: ΚΥΡΙΟ (προ-δηλωμενο) = πρωτη φορα που edge ≥ κατωφλι μεσα στις τελευταιες 12ω · δευτερευον = τιμη 1ω πριν · αναφορα = ≤72ω (σημερα).
ΠΡΟ-ΔΗΛΩΜΕΝΑ ΚΡΙΤΗΡΙΑ (ιδια με 10/10): Κ1 κατωφλι επιλεγμενο LOSO → εκτος δειγματος θετικο · Κ2 στο κατωφλι αυτο: θετικο ΚΑΙ στα 2 βιβλια ·
Κ3 ≥3/4 σεζον θετικες · Κ4 ΚΑΙ οι 2 σεζον νεας μορφης (2425, 2526) θετικες. Επιπλεον (πληροφορια): ROI στο κλεισιμο, γκολ vs xG vs αγορα.
"""
import sys, io, contextlib
src = open('uel_full_review.py', encoding='utf-8').read().split('# ======================= 1. ΣΥΝΟΛΑ')[0]
src = src.replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
import os
_R = sys.stdout; sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(src); sys.stdout = _R
sys.stdout.reconfigure(encoding='utf-8')
rows = []
for i in UEL:
    if SRCC[i] != 'FF': continue
    td = ES.tot_dist(OH[i], OA[i], DRAW_SCALE); tot = GH[i] + GA[i]
    for bk in ('Crown', 'SBOBET'):
        for h in HS:
            s = snap_ou(MIDS[i], bk, h)
            if not s: continue
            L, ov_, o = s; pu, po = ES.p_over(td, L)
            if not (1.70 <= o <= 2.10) and h: continue
            rows.append(dict(i=i, bk=bk, h=h, sea=SEA[i], L=L, od=o, e=po * (o - 1) * (1 - picks.MARGIN) - pu,
                             pnl=settle(tot, L, o, False) if 1.70 <= o <= 2.10 else np.nan, mt=-mtot(L, ov_, o)))
RT = pd.DataFrame(rows)
CL = RT[RT.h == 0].set_index(['i', 'bk'])
RT = RT[(RT.h > 0) & RT.pnl.notna()]
def stream(win, th, seas=SEAS):
    y = RT[(RT.e >= th) & RT.sea.isin(seas)]
    if win == '1ω': return y[y.h == 1]
    y = y[y.h <= (12 if win == '≤12ω' else 72)].sort_values('h', ascending=False)
    return y.groupby(['i', 'bk']).head(1)
TH = (0, .02, .04, .06, .08, .10, .12, .14)
def crit(x):
    m = x.groupby('bk').pnl.mean(); ps = x.groupby('sea').pnl.mean(); pn = ps[ps.index.isin(NEW)]
    return bool((m > 0).all()), (ps > 0).sum() >= 3, len(pn) == 2 and bool((pn > 0).all())
ck = lambda b: '✓' if b else '✗'
for win in ('≤12ω', '1ω', '≤72ω'):
    print(NL + f'===== ΠΑΡΑΘΥΡΟ {win}' + ('  ← ΚΥΡΙΟ' if win == '≤12ω' else ('  (αναφορα = σημερινος τροπος)' if win == '≤72ω' else '')))
    for th in TH: print(f'   ≥{int(th * 100):2d}% {cc(stream(win, th))}')
    outs = []
    for hold in SEAS:
        tr = [s for s in SEAS if s != hold]
        sc = {th: stream(win, th, tr).groupby('bk').pnl.mean().mean() for th in TH}
        t = max(sc, key=lambda k: sc[k]); outs.append((hold, t, stream(win, t, (hold,))))
    n = sum(o[2].groupby('bk').size().mean() for o in outs if len(o[2]))
    tot = sum(o[2].groupby('bk').pnl.mean().mean() * o[2].groupby('bk').size().mean() for o in outs if len(o[2]))
    k1 = tot > 0
    best = pd.Series([o[1] for o in outs]).mode().iloc[0]
    F = stream(win, best).copy(); k2, k3, k4 = crit(F)
    F['pc'] = [CL.pnl.get((r.i, r.bk), np.nan) for r in F.itertuples()]
    F['clv'] = [CL.mt.get((r.i, r.bk), np.nan) - r.mt for r in F.itertuples()]
    ii = F.drop_duplicates('i').i.values; xg = [sum(XG[str(MIDS[k])]) for k in ii if str(MIDS[k]) in XG]
    print('   LOSO: ' + ' · '.join(f'{h[2:]}→≥{int(t * 100)}%' for h, t, _ in outs) + f' · ΕΚΤΟΣ ΔΕΙΓΜΑΤΟΣ {100 * tot / max(n, 1):+.1f}% ({n:.0f} picks)')
    print(f'   κατωφλι ≥{int(best * 100)}%: {cc(F)}')
    print(f'      Κ1 εκτος δειγματος {ck(k1)} · Κ2 2 βιβλια {ck(k2)} · Κ3 ≥3/4 σεζον {ck(k3)} · Κ4 νεα μορφη {ck(k4)}  → {"ΠΕΡΝΑ" if all((k1, k2, k3, k4)) else "ΔΕΝ ΠΕΡΝΑ"}')
    print(f'      αν περιμενα το κλεισιμο: {100 * F.pc.mean():+.1f}% · αγορα μετα την εισοδο {F.clv.mean():+.2f} γκολ (+ = προς εμας, δηλ. συνολο κατω) · '
          f'γκολ {np.mean(GH[ii] + GA[ii]):.2f} · xG {np.mean(xg):.2f} · αγορα {-F.mt.mean():.2f} · μοντελο {np.mean(OH[ii] + OA[ii]):.2f}')
