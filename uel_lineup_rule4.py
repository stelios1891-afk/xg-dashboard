"""uel_lineup_rule4.py — 14/10/2026 (Στελιος: «στο over το μοντελο κατι βλεπει, η καλη ενδεκαδα το επιβεβαιωνει, το rotation το καταστρεφει·
στο χαντικαπ ειναι κοντρα: οταν συμφωνουν χανει, οταν διαφωνουν κερδιζει — περιεργο»).
Ελεγχος: γνωμη μοντελου (συμφωνει/διαφωνει) × ποσοστο ενδεκαδας φαβορι (≥1.00 / 0.90-1.00 / <0.90 / ολα), UEL & UECL,
χαντικαπ φαβορι και over, με ± τυπικο σφαλμα. Ιδια δεδομενα με uel_lineup_rule3 (τιμη 1ω, 1.70-2.10, Crown+SBOBET). Διαγνωστικο.
"""
import sys, os
src = open('uel_lineup_rule3.py', encoding='utf-8').read().split('# ---------- 2. πινακας')[0]
_R = sys.stdout; sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(src); sys.stdout = _R; sys.stdout.reconfigure(encoding='utf-8')
def cs(x, col):
    x = x.dropna(subset=[col])
    if len(x) < 10: return f'n{len(x) / 2:4.0f} (λιγα)'
    m = x.groupby('bk')[col].mean().mean(); n = x.groupby('bk').size().mean(); se = x[col].std() / np.sqrt(n)
    ps = x.groupby('sea')[col].mean()
    return f'{n:4.0f} picks {100 * m:+6.1f}% ±{100 * se:4.1f} (' + ' '.join(f'{s[2:]} {100 * v:+.0f}' for s, v in ps.items()) + ')'
BINS = (('πληρης ≥1.00', lambda r: r >= 1.0), ('0.90-1.00', lambda r: (r >= .9) & (r < 1.0)), ('rotation <0.90', lambda r: r < .9), ('ολα', lambda r: r > 0))
for cm in ('EuropaLeague', 'ConferenceLeague'):
    print(NL + f'========== {cm}')
    U = B[(B.comp == cm)].dropna(subset=['medge'])
    print('  ΧΑΝΤΙΚΑΠ ΦΑΒΟΡΙ (τυφλο, χωρις τα uel_home_fav) — ROI | αξια xG')
    for lab, f in BINS:
        x = U[f(U.ratio)]
        for gl, g in (('μοντ. ΣΥΜΦΩΝΕΙ', x.medge >= 0), ('μοντ. ΔΙΑΦΩΝΕΙ', x.medge < 0)):
            y = x[g]; print(f'    {lab:15s} {gl:15s} {cs(y, "pnl")} | xG {100 * y.xv.mean():+5.1f}%')
    O = OU[OU.comp == cm].dropna(subset=['eo'])
    print('  OVER (κυρια γραμμη 1ω) — ROI')
    for lab, f in BINS:
        x = O[f(O.ratio)]
        for gl, g in (('μοντ. βλεπει OVER', x.eo >= 0), ('μοντ. βλεπει UNDER', x.eo < 0)):
            y = x[g]; print(f'    {lab:15s} {gl:18s} OVER {cs(y, "over")} · γκολ {y.tg.mean():.2f} xG {y.xg_t.mean():.2f} αγορα {y.mt.mean():.2f}')
