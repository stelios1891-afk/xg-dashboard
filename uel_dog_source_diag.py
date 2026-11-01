"""uel_dog_source_diag.py — 14/10/2026 (Στελιος: «αν η ποιοτητα των ομαδων δεν μεταφερεται πληρως, γιατι στα αουτσαιντερ χανουμε τοσο; εκει που
βρισκουμε μικροτερη διαφορα δεν θα επρεπε να πληρωνομαστε;»). Europa, κατηγορια Α, picks αουτσαιντερ @10% (σημερινος κανονας UEL: p_cover,
γραμμη ≥+0.5, 1.70-2.10, πρωτη εμφανιση ≤72ω χωρις την τελευταια τιμη). Απο τη σκοπια του ΑΟΥΤΣΑΙΝΤΕΡ: διαφορα αγορα / μοντελο / xG / γκολ,
εντος/εκτος, + αναλυση λαθους μοντελου (vs xG) σε ΕΔΡΑ (a=+0.20) και ΣΥΜΠΙΕΣΗ (b=−0.41) απο uel_home_away_fav_diag.
"""
import sys, os
NL = chr(10)
src = open('uel_home_away_fav_diag.py', encoding='utf-8').read().split("print('1) ΑΝΑΛΥΣΗ ΛΑΘΟΥΣ")[0]
_REAL = sys.stdout; exec(src); sys.stdout = _REAL
A_, B_ = 0.20, -0.41
P = []
for r in C[C.comp == 'EuropaLeague'].itertuples():
    i = r.i; D = sdist(LH_N[i], LA_N[i])
    for bk in ('Crown', 'SBOBET'):
        got = set()
        for h in (72, 60, 48, 36, 24, 18, 12, 8, 6, 4, 2, 1):
            s = snap_ah(MIDS[i], bk, h)
            if not s: continue
            L, oh, oa = s
            for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                if side in got or ln < 0.5 or not (1.70 <= o <= 2.10): continue
                if edge(*picks.p_cover(D, side, ln), o) < .10: continue
                got.add(side)
                xh, xa = XG[str(MIDS[i])]; pw, pp = picks.p_cover(picks.gd_dist(max(xh, .05), max(xa, .05)), side, ln)
                P.append(dict(sea=r.sea, bk=bk, home=side == 1, pnl=picks.settle(GD[i], side, ln, o), xv=edge(pw, pp, o), ln=ln,
                              mm=side * r.mgd, km=side * implied_margin(i, L, oh, oa), xg=side * r.xgd, gd=side * r.gd,
                              e_a=side * A_, e_b=side * B_ * r.mgd))
P = pd.DataFrame(P)
print('ΑΟΥΤΣΑΙΝΤΕΡ @10% — Europa κατηγορια Α (διαφορα απο τη σκοπια του αουτσαιντερ· αρνητικη = χανει)')
for nm, m_ in (('ΟΛΑ', P.home | ~P.home), ('αουτσαιντερ ΕΚΤΟΣ (κοντρα σε γηπεδουχο φαβορι)', ~P.home), ('αουτσαιντερ ΕΝΤΟΣ', P.home)):
    y = P[m_]
    print(f'{NL}   {nm}: {cc(y)} · αξια xG {100 * y.xv.mean():+.1f}%')
    print(f'      γραμμη +{y.ln.mean():.2f} · ΑΓΟΡΑ {y.km.mean():+.2f} · ΜΟΝΤΕΛΟ {y.mm.mean():+.2f} · xG {y.xg.mean():+.2f} · γκολ {y.gd.mean():+.2f}')
    err = y.mm - y.xg
    print(f'      μοντελο − xG {err.mean():+.2f} (υπερεκτιμα τον αουτσαιντερ αν +) = απο ΕΔΡΑ {-y.e_a.mean():+.2f} + απο ΣΥΜΠΙΕΣΗ {-y.e_b.mean():+.2f} + υπολοιπο {err.mean() + y.e_a.mean() + y.e_b.mean():+.2f}')
    print(f'      αγορα − xG {(y.km - y.xg).mean():+.2f}')
