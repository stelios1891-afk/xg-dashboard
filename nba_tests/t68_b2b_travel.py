# -*- coding: utf-8 -*-
"""t68_b2b_travel.py — (24/10/2026) Στελιος: «η Charlotte επαιξε χθες εντος και ξανα εντος, το Miami εντος → εκτος· παιζει ρολο;»
ΕΡΩΤΗΜΑ: ομαδα σε back-to-back που ΔΕΝ ταξιδεψε καθολου (ιδιο γηπεδο με χθες) κουραζεται λιγοτερο απο ομαδα που ταξιδεψε,
         ανεξαρτητα απο αποσταση; (η ζωνη ωρας μετραει ηδη χωριστα στο live)
ΒΑΣΗ = LIVE: production CFG_H + αφετηρια ανα ομαδα + 0.75·γνωστες απουσιες + 3·(B2B φιλ − B2B γηπ)
       − 0.68·(|ωρες|·[προηγ. ≤2μ] γηπ − ιδιο φιλ)   (οπως nba_odds_scan TZ_K/TZ_GAP)
ΕΚΔΟΧΗ: + c·(Χ γηπ − Χ φιλ), Χ = 1 αν η ομαδα ειναι σε B2B ΚΑΙ το χθεσινο ματς ηταν στο ιδιο γηπεδο (0 χλμ)· c με LOSO.
ΠΕΡΙΓΡΑΦΙΚΟ: υπολοιπο (πραγματικο − ΒΑΣΗ) υπερ της ομαδας σε B2B, 4 τυποι: εντος→εντος · εκτος→εντος · εντος→εκτος · εκτος→εκτος.
ΔΕΙΓΜΑ: 5 σεζον 2021-22…2025-26 (κανονικη περιοδος), ιδια δεδομενα με t3/t3b.
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ (εγκριθηκε 24/10 πριν το τρεξιμο, ιδιο με t3/t3b): LOSO RMSE καλυτερο απο τη ΒΑΣΗ σε ≥4/5 σεζον ΚΑΙ
ROI ανοιγματος edge ≥8% Οκτ-Δεκ οχι χειροτερο απο −1.5pp. ROI ολης της σεζον = μονο πληροφορια.
Εξοδος: nba_tests/t68_b2b_travel_out.txt"""
import os, sys, io, contextlib
SC = os.path.dirname(os.path.abspath(__file__))
_src = open(os.path.join(SC, 't3b_travel_tz.py'), encoding='utf-8').read().split('# ---------- ΠΕΡΙΓΡΑΦΙΚΟ ----------')[0]
_src = _src.split('import os, sys, io, json, math, collections', 1)[1]
import json, math, collections
exec(_src)
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))

# ---------- προηγουμενο γηπεδο ανα ομαδα (για τους 4 τυπους) ----------
PREVLOC = np.full((N, 2), None, dtype=object); last2 = {}; lastloc2 = {}
for i in np.argsort(dD, kind='stable'):
    s, h_, a_, d = SEAS_G[i], G.home.values[i], G.away.values[i], dD[i]
    for j, t in enumerate((h_, a_)):
        if (s, t) in last2: PREVLOC[i, j] = lastloc2[(s, t)]
    loc_i = None if NEU[i] else h_
    last2[(s, h_)] = d; last2[(s, a_)] = d; lastloc2[(s, h_)] = loc_i; lastloc2[(s, a_)] = loc_i

# ---------- ΒΑΣΗ = LIVE (με ζωνη ωρας) ----------
TZL = np.abs(TZC) * (GAP <= 2)
BASEL = BASE - 0.68 * dif(TZL)
B2 = (GAP == 1)
NT = (B2 & (KM < 1) & ~NEU[:, None] & (PREVLOC != None)).astype(float)
BASE = BASEL; RES = ACT - BASE                                  # οι συναρτησεις του t3b (fit/loso/sse/line) διαβαζουν αυτα
P(f'ΒΑΣΗ live (B2B 3 + ζωνη 0.68/ω ≤2μ) RMSE {rm(BASE, EV):.4f}')

# ---------- ΠΕΡΙΓΡΑΦΙΚΟ ----------
P('\n=== ΠΕΡΙΓΡΑΦΙΚΟ: ομαδα σε B2B — υπολοιπο (πραγματικο − ΒΑΣΗ) υπερ της (π.), μεσος ± SE (n) ===')
P('   θετικο = πηγε ΚΑΛΥΤΕΡΑ απο το live (κουραστηκε λιγοτερο απο −3)')
cells = collections.defaultdict(list); rows = []
for i in np.where(ev_m & OK & ~NEU)[0]:
    for j in (0, 1):
        if not B2[i, j] or PREVLOC[i, j] is None: continue
        t = (G.home.values[i], G.away.values[i])[j]
        prev_home = PREVLOC[i, j] == t; now_home = j == 0
        typ = ('εντος' if prev_home else 'εκτος') + ' → ' + ('εντος' if now_home else 'εκτος')
        r = RES[i] * (1 if j == 0 else -1)
        cells[typ].append(r); cells['ΧΩΡΙΣ ταξιδι (0 χλμ)' if NT[i, j] else 'ΜΕ ταξιδι'].append(r)
        rows.append((SEAS_G[i], typ, r))
for typ in ('εντος → εντος', 'εκτος → εντος', 'εντος → εκτος', 'εκτος → εκτος', 'ΧΩΡΙΣ ταξιδι (0 χλμ)', 'ΜΕ ταξιδι'):
    x = np.array(cells[typ])
    if typ == 'ΧΩΡΙΣ ταξιδι (0 χλμ)': P('   ---')
    P(f'   {typ:22s} {x.mean():+5.2f} ± {x.std(ddof=1) / np.sqrt(len(x)):4.2f}  (n {len(x)})')
P('   ανα σεζον (εντος→εντος / εκτος→εντος / εντος→εκτος / εκτος→εκτος):')
for Y in EV:
    P(f'     {Y}: ' + ' / '.join(f'{np.mean([r for s, t_, r in rows if s == Y and t_ == k]):+5.2f} (n{sum(1 for s, t_, r in rows if s == Y and t_ == k)})'
                             for k in ('εντος → εντος', 'εκτος → εντος', 'εντος → εκτος', 'εκτος → εκτος')))

# ---------- ΕΚΔΟΧΗ ----------
base_s = {Y: rm(BASE, [Y]) for Y in EV}
nb, rb, ub, psb, _ = roi_od(BASE)
X = np.c_[dif(NT)]
v, cf = loso(X)
def ln(lab, vv):
    n1, r1, u1, ps1, _ = roi_od(vv); n2, r2, u2, ps2, _ = roi_od(vv, msk=ALL)
    bet = sum(rm(vv, [Y]) < base_s[Y] - 1e-5 for Y in EV)
    P(f'{lab:26s} | {rm(vv, EV):8.4f} | {bet}/5 | {r1:+6.1f}% ({n1:4d}) {u1:+7.1f}u {sum(ps1[Y] > 0 for Y in EV)}/5 | {r2:+6.1f}% ({n2:4d}) {u2:+7.1f}u')
    return bet, r1
P(f'\n=== ΕΚΔΟΧΗ (LOSO) ===\n{"εκδοχη":26s} | RMSE ολα | καλ.| ROI Οκτ-Δεκ ≥8%  (n)   units θετ | ROI ολη ≥8%  (n)   units')
ln('ΒΑΣΗ (live)', BASE)
bet, r1 = ln('+ c·B2B χωρις ταξιδι', v)
P('συντελεστης c ανα fold (σεζον-στοχος 2022…2026, π. υπερ της ομαδας που ΔΕΝ ταξιδεψε): ' + ' · '.join(f'{cf[Y][0]:+.2f}' for Y in EV)
  + f' · ολα τα δεδομενα {fit(X, EV)[0]:+.2f}')
P('ανα σεζον RMSE (ΒΑΣΗ / εκδοχη): ' + ' · '.join(f'{Y}: {base_s[Y]:.4f}/{rm(v, [Y]):.4f}' for Y in EV))
P(f'\nΚΡΙΤΗΡΙΟ: RMSE καλυτερο {bet}/5 (απαιτ. ≥4) · ROI Οκτ-Δεκ {r1:+.1f}% vs ΒΑΣΗ {rb:+.1f}% (Δ {r1 - rb:+.1f}pp, απαιτ. > −1.5) → '
  f'{"ΠΕΡΝΑΕΙ" if bet >= 4 and r1 - rb > -1.5 else "ΔΕΝ ΠΕΡΝΑΕΙ"}')
open(os.path.join(SC, 't68_b2b_travel_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
