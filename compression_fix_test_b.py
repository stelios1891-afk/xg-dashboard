"""compression_fix_test_b.py — 13/10/2026 (Στελιος: «αυτο ειναι μονο στην Α;»). Ιδια διορθωση με compression_fix_test (Conference, διαφορα × s,
s LOSO απο ΟΛΑ τα ματς της διοργανωσης = 0.80 σε καθε σεζον) αλλα picks στην ΚΑΤΗΓΟΡΙΑ Β: φαβ / dog ανα πλευρα (ομαδα ΜΕ ή ΧΩΡΙΣ FotMob),
κανονες UECL (φαβ ≥4% σωστα τεταρτα · dog ≥10% p_cover · 1.70-2.10 · πρωτη εμφανιση ≤72ω · Crown & SBOBET).
"""
import sys
src = open('compression_fix_test.py', encoding='utf-8').read().split("GRID = np.round(np.arange(0.50, 1.21, 0.05), 2)")[0]
exec(src)
LABS = {'shots': 'F', 'griffis': 'B', 'goals': 'G'}
def picks_B(idx, smap):
    out = []
    for i in idx:
        if SRCC[i] in ('FF',) or 'F' not in SRCC[i]: continue
        j = VI[str(MIDS[i])]; fmh = V6['src_h'][j] == 'shots'
        D = sdist(*pair(i, smap.get(SEA[i], 1.0)))
        for bk in ('Crown', 'SBOBET'):
            got = set()
            for h in HS:
                key = (i, bk, h)
                if key not in SNAP: SNAP[key] = snap_ah(MIDS[i], bk, h)
                s = SNAP[key]
                if not s: continue
                L, oh, oa = s
                for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                    if side in got or not (1.70 <= o <= 2.10): continue
                    big = (side == 1) == fmh
                    if ln <= -0.5: pw, pp = cover_q(D, side, ln); th = .04; k = 'φαβ ' + ('ΜΕ FotMob' if big else 'ΧΩΡΙΣ FotMob')
                    elif ln >= 0.5: pw, pp = picks.p_cover(D, side, ln); th = .10; k = 'dog ' + ('ΜΕ FotMob' if big else 'ΧΩΡΙΣ FotMob')
                    else: continue
                    if edge(pw, pp, o) >= th:
                        got.add(side); out.append(dict(bk=bk, sea=SEA[i], k=k, pnl=picks.settle(GD[i], side, ln, o)))
    return pd.DataFrame(out)
idx_all = [i for i in range(len(MIDS)) if COMP[i] == 'ConferenceLeague' and LH_N[i] > 0 and VI.get(str(MIDS[i])) is not None]
SM = {s_: 0.80 for s_ in SEAS_}
P0 = picks_B(idx_all, {}); P1 = picks_B(idx_all, SM)
print('CONFERENCE, ΚΑΤΗΓΟΡΙΑ Β — picks σημερα → με διορθωση ×0.80 (LOSO: 0.80 σε καθε σεζον)')
for k in ('φαβ ΜΕ FotMob', 'φαβ ΧΩΡΙΣ FotMob', 'dog ΜΕ FotMob', 'dog ΧΩΡΙΣ FotMob'):
    print(f'   {k:18s} σημερα {cc_(P0[P0.k == k])}')
    print(f'   {"":18s} με s   {cc_(P1[P1.k == k])}')
for lab, P in (('σημερα', P0), ('με s', P1)):
    print(f'   ΣΥΝΟΛΟ Β {lab}: {cc_(P)}')
