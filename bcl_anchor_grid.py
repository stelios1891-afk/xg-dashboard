# -*- coding: utf-8 -*-
"""bcl_anchor_grid.py — BCL αγκυρωση: ΠΛΕΓΜΑ ποσοστου διαφωνιας w × κατωφλι (21/10/2026, Στελιος «μηπως να δοκιμαζες και αλλα ποσοστα;»).
Ιδια βαση με bcl_anchor_test. Προβλεψη = αγορα + w·(FIN − αγορα), σ = τυπ. αποκλιση (πραγμ − προβλεψη) ολων. Πινακας ROI/μοναδες ανα (w, κατωφλι)
+ LOSO που διαλεγει (w, κατωφλι) με ΜΟΝΑΔΕΣ (οχι RMSE) + walk-forward. Περιγραφικο συμπληρωμα του προ-δηλωμενου τεστ."""
import sys
src = open('bcl_anchor_test.py', encoding='utf-8').read().split("# ---------- μηχανες ----------")[0].replace("open('bcl_anchor_test_out.txt'", "open('NUL'")
exec(src)
WS = (.1, .2, .3, .4, .5, .6, .7, .8, 1.0); THR = (.04, .06, .08, .10, .12)
G = {}
for w in WS:
    pr = FO + w * (FIN - FO); sg = float(np.std(ACT - pr))
    for th in THR: G[(w, th)] = (pr, sg, evaluate(pr, sg, th))
P(''); P('=== ΠΛΕΓΜΑ (ολες οι σεζον) · κελι: ROI (picks, μοναδες) ===')
P('  w \ κατωφλι | ' + ' | '.join(f'{int(t * 100)}%'.center(24) for t in THR))
for w in WS:
    cs = []
    for th in THR:
        R = G[(w, th)][2]; a = np.array([x[1] for x in R]) if R else np.array([0.0])
        cs.append(f'{100 * a.mean():+5.1f}% ({len(R):4d}, {a.sum():+6.1f}μ)')
    P(f'  w {w:<4} (σ {G[(w, .08)][1]:.1f}) | ' + ' | '.join(c.center(24) for c in cs))
P(f'  LIVE (μοντελο μονο του, σ 12, ≥8%): {cell(LIVE)}')
# LOSO με μοναδες
held = []; ch = {}
for s in SE:
    tr = Y != s
    best = max(G, key=lambda k: sum(x[1] for x in G[k][2] if x[0] != s)); ch[s] = best
    held += [x for x in G[best][2] if x[0] == s]
P(''); P(f'LOSO (επιλογη με μοναδες): {ch}'); P(f'  → {cell(held)} · LIVE {cell(LIVE)}')
uL, uH = units_by(LIVE), units_by(held); P('  ανα σεζον μοναδες LOSO / LIVE: ' + ' · '.join(f'{s}: {uH.get(s, 0):+.1f}/{uL.get(s, 0):+.1f}' for s in SE))
WF = []
for s in [x for x in SE if x >= 2022]:
    tr = Y < s
    def u_tr(k):
        w, th = k; pr = FO + w * (FIN - FO); sg = float(np.std(ACT[tr] - pr[tr])); return sum(x[1] for x in evaluate(pr, sg, th, mask=tr)), sg
    best = max(G, key=lambda k: u_tr(k)[0]); w, th = best; pr = FO + w * (FIN - FO); sg = u_tr(best)[1]
    WF += evaluate(pr, sg, th, mask=(Y == s)); P(f'  walk-forward {s}: επιλογη w {w} κατωφλι {th}')
uW = units_by(WF); P(f'  WALK-FORWARD 2022-25: {cell(WF)} · ' + ' · '.join(f'{s}: {uW.get(s, 0):+.1f}' for s in SE if s >= 2022))
