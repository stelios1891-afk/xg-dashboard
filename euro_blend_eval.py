"""
euro_blend_eval.py — 9/10/2026 (Στελιος «τρεξτο, με περισσοτερη βαση στο Europa»): ΜΙΞΗ xG/γκολ στα εγχωρια ratings ΓΙΑ ΤΗΝ ΕΥΡΩΠΗ.
Σημερινη ευρωπαικη αλυσιδα (κοκκινες emps) ξαναχτισμενη με μιξη b (βαρος xG στα 13+ ματς & στο prior· ραμπα 100%→b): 0.2 / 0.4 / 0.6 (σημερα) / 0.8 / 1.0.
Μετρα ανα διοργανωση: πιθανοφανεια γκολ (Poisson), μεροληψια φαβορι εντος/εκτος, picks (σημερινοι κανονες, κλεισιμο, μεσος Crown/SBOBET).
ΠΡΟ-ΔΗΛΩΣΗ: μιξη ανα διοργανωση επιλεγεται LOSO (μεγιστη πιθανοφανεια στις 3 σεζον) — αλλαζουμε μονο αν (1) η εκτος-δειγματος πιθανοφανεια
ειναι καλυτερη απο το 0.6 σε ≥3/4 σεζον ΚΑΙ (2) τα picks της διοργανωσης δεν χειροτερευουν (μοναδες ≥ σημερα). UEL: επιπλεον αν μικραινει
η μεροληψια εκτος φαβορι.
"""
import sys, pickle
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
TAGS = ['0.2', '0.4', '0.6', '0.8', '1.0']
DUMP = {t: pickle.load(open(f'euro_blend_dump_{t}.pkl', 'rb')) for t in TAGS}
B0 = DUMP['0.6']
for t in TAGS: assert DUMP[t]['MIDS'] == B0['MIDS']
GH, GA, GD, SEA, COMP = B0['GH'], B0['GA'], B0['GD'], B0['SEA'], B0['COMP']
SEAS = ('2223', '2324', '2425', '2526'); CMP = ('EuropaLeague', 'ChampionsLeague', 'ConferenceLeague')
def ll(t, m): d = DUMP[t]; return float(np.sum(GH[m] * np.log(d['LH'][m]) - d['LH'][m] + GA[m] * np.log(d['LA'][m]) - d['LA'][m]))
def bias(t, m):
    d = DUMP[t]; s = d['LH'] - d['LA']
    return (GD - s)[m & (s >= .5)].mean(), (-(GD - s))[m & (s <= -.5)].mean()
def roi(P, comp):
    x = P[P.comp == comp]; ps = x.groupby('sea').pnl.mean()
    return len(x) / 2, 100 * x.pnl.mean() if len(x) else np.nan, x.pnl.sum() / 2, int((ps > 0).sum())
print('1. ΟΛΟ ΤΟ ΔΕΙΓΜΑ (για εικονα) — Δπιθανοφανεια γκολ vs 0.6 · μεροληψια φαβορι εντος/εκτος · picks')
for c in CMP:
    m = COMP == c; print(f'\n[{c}]')
    for t in TAGS:
        eh, ea = bias(t, m); n, r, u, sp = roi(DUMP[t]['P0'], c)
        print(f'   xG {float(t):.0%}: Δπιθ {ll(t, m) - ll("0.6", m):+6.1f} · φαβ εντος {eh:+.3f} / εκτος {ea:+.3f} · picks n{n:4.0f} {r:+6.1f}% {u:+6.1f}u σεζ {sp}/4')
print('\n2. ΑΝΑ ΣΕΖΟΝ — Δπιθανοφανεια vs 0.6')
for c in CMP:
    print(f'   [{c}] ' + ' · '.join(f'xG {float(t):.0%}: ' + ' '.join(f'{ll(t, (COMP == c) & (SEA == s)) - ll("0.6", (COMP == c) & (SEA == s)):+.1f}' for s in SEAS) for t in TAGS if t != '0.6'))
print('\n3. LOSO ανα διοργανωση (μιξη απο τις 3 αλλες σεζον)')
for c in CMP:
    ch = {}; dll = {}; rows = []
    for te in SEAS:
        tr = (COMP == c) & (SEA != te); tm = (COMP == c) & (SEA == te)
        best = max(TAGS, key=lambda t: ll(t, tr)); ch[te] = best; dll[te] = ll(best, tm) - ll('0.6', tm)
        P = DUMP[best]['P0']; rows.append(P[(P.comp == c) & (P.sea == te)])
    R = pd.concat(rows); P6 = DUMP['0.6']['P0']; P6 = P6[P6.comp == c]
    u_new, u_old = R.pnl.sum() / 2, P6.pnl.sum() / 2
    c1 = sum(v > 0 for v in dll.values()) >= 3; c2 = u_new >= u_old
    s = DUMP[ch[SEAS[-1]]]; eh, ea = bias(ch[SEAS[-1]], COMP == c)
    print(f'   [{c:17s}] επιλογες ' + ' '.join(f'{k}:{float(v):.0%}' for k, v in ch.items()) + ' · Δπιθ ' + ' '.join(f'{k}:{v:+.1f}' for k, v in dll.items())
          + f' · picks {len(R) / 2:.0f} {100 * R.pnl.mean():+.1f}% {u_new:+.1f}u vs σημερα {len(P6) / 2:.0f} {100 * P6.pnl.mean():+.1f}% {u_old:+.1f}u'
          + f' → (1){"✓" if c1 else "✗"} (2){"✓" if c2 else "✗"} {"ΑΛΛΑΓΗ" if c1 and c2 else "ΜΕΝΕΙ 60%"}')
print('\n4. EUROPA LEAGUE — picks ανα μιξη × ρολος × εδρα (ολο το δειγμα)')
for t in TAGS:
    P = DUMP[t]['P0']; x = P[P.comp == 'EuropaLeague']
    cells = []
    for role, hm, lab in (('fav', True, 'φαβ εντος'), ('fav', False, 'φαβ εκτος'), ('dog', True, 'αουτ εντος'), ('dog', False, 'αουτ εκτος')):
        y = x[(x.role == role) & (x.home == hm)]; cells.append(f'{lab} {len(y) / 2:3.0f} {100 * y.pnl.mean() if len(y) else 0:+5.1f}%')
    print(f'   xG {float(t):.0%}: ' + ' · '.join(cells) + f' · ΟΛΑ {len(x) / 2:.0f} {100 * x.pnl.mean():+.1f}%')
