# -*- coding: utf-8 -*-
"""t2_blend.py — ΤΕΣΤ 2 = TODO #2: αναμειξη με την τιμη ΑΝΟΙΓΜΑΤΟΣ (αυτο ειναι η ποδοσφαιρικη «αγκυρα»). ΜΟΝΟ μετρηση.
Βαση = production + B2B 3.0 + απουσιες. Εκτιμηση μ = αγορα_ανοιγματος (δικαιη διαφορα χωρις γκανιοτα) + w·(μοντελο − αγορα).
Πλεγμα w ∈ {0.25, 0.33, 0.5, 0.75, 1.0} × κατωφλι edge ∈ {2, 4, 6, 8%}. Σημερινο = (w 1.0, 8%).
Picks = πλευρα με το μεγαλυτερο edge στο ανοιγμα (ιδια λογικη με roi_od). Settled στο ανοιγμα.

ΠΡΟ-ΔΗΛΩΜΕΝΑ (πριν το τρεξιμο):
 LOSO: για καθε σεζον Y διαλεγεται (w, κατωφλι) με το μεγαλυτερο ROI Οκτ-Δεκ στις αλλες 4 σεζον, με ελαχιστο 150 picks Οκτ-Δεκ σε αυτες
       (ευαισθησια: επιλογη με μεγιστες μοναδες). Ιδια διαδικασια χωριστα για ολη τη σεζον.
 ΠΕΡΝΑ αν: ROI LOSO Οκτ-Δεκ ≥ σημερινο Οκτ-Δεκ ROI ΚΑΙ θετικες σεζον LOSO ≥4/5 ΚΑΙ η βαθμονομηση καλυτερευει
       (σφαλμα βαθμονομησης = σταθμισμενος μεσος |πραγματικη − δηλωμενη πιθ.| των picks της επιλογης, μικροτερο απο σημερινο).
 Διαφορες ROI ±1.5pp = θορυβος.
Εξοδος: t2_blend_out.txt"""
import os, sys
SC = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, SC)
sys.stdout.reconfigure(encoding='utf-8')
from t_common import load, cover, side_pick, settle, np
D = load()
MG, OC, S, EV, ACT, SIG = D['MG'], D['OC'], D['SEAS_G'], D['EV'], D['ACT'], D['SIG']
V = MG + 3.0 * (D['B2A'] - D['B2H']) + 0.75 * D['LOSS2']
MON = D['G'].date.dt.month.values; ODm = np.isin(MON, [10, 11, 12])
IDX = [i for i in OC if S[i] in EV and np.isfinite(V[i])]
WS = (0.25, 0.33, 0.5, 0.75, 1.0); TH = (.02, .04, .06, .08)

def picks(w):
    R = []
    for i in IDX:
        L, mk, o1, o2 = OC[i]['o']; mu = mk + w * (V[i] - mk)
        s_, e, od_, p, pp = side_pick(mu, L, o1, o2, SIG); pnl, win = settle(ACT[i], L, s_, od_)
        R.append((i, S[i], ODm[i], e, p + pp / 2, win, pnl))
    return R
P = {w: picks(w) for w in WS}
def sel(w, thr, od=True, ys=EV):
    return [r for r in P[w] if r[3] >= thr and (r[2] or not od) and r[1] in ys]
def stats(R):
    if not R: return 0, 0.0, 0.0, {Y: 0.0 for Y in EV}
    u = np.array([r[6] for r in R]); ps = {Y: sum(r[6] for r in R if r[1] == Y) for Y in EV}
    return len(R), u.mean() * 100, u.sum(), ps
def calerr(R):
    B = [(.0, .04), (.04, .06), (.06, .08), (.08, .12), (.12, .16), (.16, .25), (.25, 9)]; tot = 0; n = 0
    for lo, hi in B:
        b = [r for r in R if lo <= r[3] < hi]
        if b: tot += len(b) * abs(np.mean([r[5] for r in b]) - np.mean([r[4] for r in b])); n += len(b)
    return tot / n if n else np.nan

for od, per in ((True, 'ΟΚΤ-ΔΕΚ'), (False, 'ΟΛΗ Η ΣΕΖΟΝ')):
    print(f'\n=== Α. ΠΛΕΓΜΑ ({per}) — picks / ROI% / θετικες σεζον · σφαλμα βαθμονομησης ===')
    print(f'  {"w":>5s} | ' + ' | '.join(f'{"κατωφλι " + str(int(t * 100)) + "%":^27s}' for t in TH))
    for w in WS:
        cells = []
        for t in TH:
            n, roi, u, ps = stats(sel(w, t, od)); cells.append(f'{n:5d} {roi:+6.1f}% {sum(ps[Y] > 0 for Y in EV)}/5 cal{calerr(sel(w, t, od)):.3f}')
        print(f'  {w:5.2f} | ' + ' | '.join(cells))

    cur = sel(1.0, .08, od); n0, r0, u0, ps0 = stats(cur)
    for crit in ('ROI', 'μοναδες'):
        held = []; ch = []
        for Y in EV:
            oth = [x for x in EV if x != Y]; best = None
            for w in WS:
                for t in TH:
                    n, roi, u, _ = stats(sel(w, t, od, oth))
                    if n < (150 if od else 375): continue
                    sc = roi if crit == 'ROI' else u
                    if best is None or sc > best[0]: best = (sc, w, t)
            ch.append((best[1], int(best[2] * 100))); held += sel(best[1], best[2], od, [Y])
        n, roi, u, ps = stats(held); npos = sum(ps[Y] > 0 for Y in EV)
        ok = roi >= r0 and npos >= 4 and calerr(held) < calerr(cur)
        print(f'\n  LOSO [{per}, επιλογη με {crit}]: επιλογες (w, κατ%) ανα σεζον {ch}')
        print(f'    LOSO : {n:5d} picks · ROI {roi:+6.1f}% · {u:+7.1f}u · ανα σεζον ' + ' '.join(f'{ps[Y]:+6.1f}' for Y in EV) + f' · θετ {npos}/5 · cal {calerr(held):.3f}')
        print(f'    ΣΗΜΕΡΑ (w1, 8%): {n0:5d} picks · ROI {r0:+6.1f}% · {u0:+7.1f}u · ανα σεζον ' + ' '.join(f'{ps0[Y]:+6.1f}' for Y in EV) + f' · θετ {sum(ps0[Y] > 0 for Y in EV)}/5 · cal {calerr(cur):.3f}')
        print(f'    → ΚΡΙΤΗΡΙΟ: {"ΠΕΡΝΑ" if ok else "ΔΕΝ ΠΕΡΝΑ"} (ROI {roi:+.1f} vs {r0:+.1f} · θετ {npos}/5 · cal {calerr(held):.3f} vs {calerr(cur):.3f})')

print('\n=== Β. ΒΑΘΜΟΝΟΜΗΣΗ ανα καδο ΔΗΛΩΜΕΝΟΥ edge (ολη η σεζον, ολοι οι αγωνες, πλευρα με το μεγαλυτερο edge) ===')
B = [(0, .02), (.02, .04), (.04, .06), (.06, .08), (.08, .12), (.12, .16), (.16, .25), (.25, 9)]
print(f'  {"w":>5s} | ' + ' | '.join(f'{f"{lo*100:g}-{hi*100:g}%" if hi < 9 else f"{lo*100:g}%+":^20s}' for lo, hi in B))
for w in WS:
    cells = []
    for lo, hi in B:
        b = [r for r in P[w] if lo <= r[3] < hi]
        cells.append(f'{len(b):4d} {np.mean([r[4] for r in b]):.3f}/{np.mean([r[5] for r in b]):.3f} {np.mean([r[6] for r in b]) * 100:+5.1f}%' if b else f'{"—":^20s}')
    print(f'  {w:5.2f} | ' + ' | '.join(cells))
print('  (καθε κελι: n · δηλωμενη/πραγματικη πιθ. καλυψης · ROI ανοιγματος)')

# κλιση b (ποσο της διαφωνιας ειναι αληθινο) ανα σεζον
print('\n=== Γ. κλιση b: (πραγμ − αγορα_ανοιγμ) = a + b·(μοντελο − αγορα_ανοιγμ) ===')
for od, per in ((True, 'Οκτ-Δεκ'), (False, 'ολη')):
    out = []
    for Y in EV:
        ii = [i for i in IDX if S[i] == Y and (ODm[i] or not od)]
        x = np.array([V[i] - OC[i]['o'][1] for i in ii]); y = np.array([ACT[i] - OC[i]['o'][1] for i in ii])
        out.append(np.polyfit(x, y, 1)[0])
    ii = [i for i in IDX if (ODm[i] or not od)]
    x = np.array([V[i] - OC[i]['o'][1] for i in ii]); y = np.array([ACT[i] - OC[i]['o'][1] for i in ii]); b = np.polyfit(x, y, 1)[0]
    r = y - np.polyval(np.polyfit(x, y, 1), x); se = np.sqrt(r.var() / (len(x) * x.var()))
    print(f'  {per:8s}: b = {b:.2f} ± {se:.2f} (n {len(ii)}) · ανα σεζον ' + ' '.join(f'{v:+.2f}' for v in out))
