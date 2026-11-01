# -*- coding: utf-8 -*-
"""el_early_disagree.py — ΔΙΑΓΝΩΣΗ (25/9/2026, ερωτημα Στελιου για Μπαρτσα/Εφες/Βαλενθια):
στις πρωτες αγωνιστικες, οταν διαφωνουμε με την αγορα στη γραμμη (χαντικαπ), ποιος εχει δικιο;
Μπλοκ αγωνιστικων (αριθμος ματς της ομαδας στη σεζον) × μεγεθος διαφωνιας. Κανονικη περιοδος, 2020-25, v1 (live χαντικαπ).
ROI: πλευρα με edge ≥5% στο Pinnacle closing. Εξοδος: el_early_disagree_out.txt"""
import sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
_o = []
src = open('el_roi_v2.py', encoding='utf-8').read().split("P('Edge = P")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src)
out = _o
def P(s=''):
    print(s, flush=True); out.append(str(s))

# αγωνιστικη ≈ ποσα ματς κανονικης περιοδου εχει παιξει ο γηπεδουχος πριν απο αυτο +1
rs_all = D[D.phase == 'RS'].sort_values('date')
cnt, gno = {}, {}
for i, r in rs_all.iterrows():
    k = (r.season, r.home); cnt[k] = cnt.get(k, 0) + 1; ka = (r.season, r.away); cnt[ka] = cnt.get(ka, 0) + 1
    gno[i] = max(cnt[k], cnt[ka])
RND = np.array([gno.get(i, 99) for i in IDX])
dis = M_V1 - MM                                  # + = πιστευουμε περισσοτερο στον γηπεδουχο απο την αγορα
g = bets(M_V1, T_LO); g = g[g.mkt == 'sp'].copy()
jj = [j for j in range(len(IDX)) if RS[j] and not np.isnan(PRC[j, 0])]
g['rnd'] = RND[jj]; g['dis'] = np.abs(dis[jj]); g['season'] = SE[jj]

P('ΧΑΝΤΙΚΑΠ v1 — κλιση b ανα μπλοκ αγωνιστικων (0 = η διαφωνια μας ειναι θορυβος, 1 = εχουμε παντα δικιο)')
blocks = [(1, 3), (4, 6), (7, 10), (11, 17), (18, 25), (26, 40)]
for a, b in blocks:
    m = RS & (RND >= a) & (RND <= b)
    bb = np.polyfit(dis[m], (ACT - MM)[m], 1)[0]
    pos = sum(1 for s in EVAL if (m & (SE == s)).sum() >= 15 and np.polyfit(dis[m & (SE == s)], (ACT - MM)[m & (SE == s)], 1)[0] > 0)
    P(f'  αγων {a:2d}-{b:2d}: ματς {m.sum():4d} · μεση |διαφωνια| {np.abs(dis[m]).mean():4.1f} π. · b {bb:+.2f} · θετικο σε {pos}/6 σεζον')
P('')
P('ROI (edge ≥5%) ανα μπλοκ × μεγεθος διαφωνιας (ποντοι γραμμης)')
P(f'{"":12s} {"|δ|<3":>20s} {"3-6":>20s} {"≥6":>20s} {"ολα":>20s}')
def c(x):
    return f'{x.p.mean()*100:+5.1f}% ({len(x)})' if len(x) else '—'
for a, b in blocks:
    x = g[(g.edge >= 0.05) & (g.rnd >= a) & (g.rnd <= b)]
    P(f'  αγων {a:2d}-{b:2d} {c(x[x.dis < 3]):>20s} {c(x[(x.dis >= 3) & (x.dis < 6)]):>20s} {c(x[x.dis >= 6]):>20s} {c(x):>20s}')
P('')
P('Αγων 1-6, διαφωνια ≥6 π.: ανα σεζον')
x = g[(g.edge >= 0.05) & (g.rnd <= 6) & (g.dis >= 6)]
P('  ' + ' · '.join(f'{s[-4:]}: {c(x[x.season == s])}' for s in EVAL))
open('el_early_disagree_out.txt', 'w', encoding='utf-8').write('\n'.join(out))

# ---- ομαδες με μεγαλη αλλαγη ρεστερ (συνεχεια = μεριδιο λεπτων που μενει απο περσι) ----
CO = pd.read_csv('el_continuity.csv'); cont = {(r.season, r.team): r.cont for r in CO.itertuples()}
hc = np.array([cont.get((SE[j], D.home.values[IDX[j]]), np.nan) for j in jj]); ac = np.array([cont.get((SE[j], D.away.values[IDX[j]]), np.nan) for j in jj])
# ποια ομαδα «υποστηριζουμε» (πλευρα του στοιχηματος) και ποια ειναι απεναντι
side_home = np.array([dis[j] > 0 for j in jj])     # πιστευουμε περισσοτερο στον γηπεδουχο
g['cont_us'] = np.where(side_home, hc, ac); g['cont_them'] = np.where(side_home, ac, hc)
q = np.nanpercentile(CO.cont, 33)
P('')
P(f'ΑΛΛΑΓΗ ΡΟΣΤΕΡ (χαμηλη συνεχεια = κατω τριτημοριο, <{q:.2f} των λεπτων μενουν) · αγων 1-10 · edge ≥5%')
e = g[(g.edge >= 0.05) & (g.rnd <= 10)]
for lab, m in (('η ομαδα που ΣΤΗΡΙΖΟΥΜΕ αλλαξε πολυ', e.cont_us < q), ('η ομαδα ΑΠΕΝΑΝΤΙ αλλαξε πολυ', e.cont_them < q),
               ('καμια απο τις δυο', (e.cont_us >= q) & (e.cont_them >= q))):
    x = e[m.values]
    P(f'  {lab:38s} {c(x):>16s}  |δ|≥4: {c(x[x.dis >= 4]):>14s} · ανα σεζον ' + ' '.join(f'{s[-2:]}:{x[x.season == s].p.mean()*100:+.0f}%' if len(x[x.season == s]) else f'{s[-2:]}:—' for s in EVAL))
open('el_early_disagree_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
