"""ucl_early_honest_totals_B.py — 16/10/2026 (Στελιος: «τι διαφορα εχουν τα ματς της Β και γιατι δεν μπηκαν στο τεστ;»).
Ιδιο τεστ με ucl_early_honest_totals (τιμη ΑΚΡΙΒΩΣ στο σημειο χρονου, τιμιος χρονος −4/−7 μερες, χωρις κανονα φρεσκιας τιμης) αλλα για ματς
Champions League κατηγοριας Β (ΜΙΑ ομαδα χωρις FotMob: Ben/Griffis ή γκολ+Elo) με τη live διορθωση: η ομαδα FotMob ×1.22 στο ζευγος συνολων
(UCL_NONFM_OU_SCALE). Μονο OVER ≥4% (τα under της Β ειναι κλειστα: −22.9% 0/4)."""
import sys
_s = open('ucl_early_honest_totals.py', encoding='utf-8').read()
_s = _s.replace("I = np.array([i for i in np.where(COMP == 'ChampionsLeague')[0] if SRCC[i] == 'FF'])",
                "I = np.array([i for i in np.where(COMP == 'ChampionsLeague')[0] if SRCC[i] in ('BF', 'FG')])", 1)
_s = _s.replace("OH0, OA0 = OH[I], OA[I]",
"""OH0, OA0 = OH[I].copy(), OA[I].copy()
FMH = np.array([_V['src_h'][_VI[str(MIDS[i])]] == 'shots' for i in I])              # ποια πλευρα εχει FotMob
OH0 = np.where(FMH, OH0 * 1.22, OH0); OA0 = np.where(~FMH, OA0 * 1.22, OA0)
print(f'κατηγορια Β Champions: {len(I)} ματς (' + ', '.join(f'{s}: {(SEA[I] == s).sum()}' for s in sorted(set(SEA[I]))) + ')')""", 1)
_s = _s.replace("    for side, nm in (('over', 'OVER ≥4%'), ('under', 'UNDER ≥10%')):", "    for side, nm in (('over', 'OVER ≥4%'),):", 1)
exec(compile(_s, 'ucl_early_honest_totals.py', 'exec'))
