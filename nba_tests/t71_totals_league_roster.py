# -*- coding: utf-8 -*-
"""t71_totals_league_roster.py — ΣΥΝΟΛΑ NBA ΣΤΟ ΑΝΟΙΓΜΑ: «ΚΛΙΜΑ ΣΚΟΡ» ΛΙΓΚΑΣ (Α) + ΟΜΑΔΕΣ ΠΟΥ ΑΛΛΑΞΑΝ ΠΟΛΥ (Γ) (24/10/2026, Στελιος
«τρεξε τα τεστ — στο ανοιγμα υπαρχουν ευκαιριες αρκει να βρουμε το σωστο μοτιβο»). Αφορμη: ανα σεζον, αγων 1-10, πραγματικο − ανοιγμα
−4.9 / −0.3 / +1.0 / +1.3 / +2.2 π. (2021-26) και φετος −7.2 ± 3.1 (28 ματς) → η αγορα αργει να πιασει το «κλιμα» της σεζον;
ΒΑΣΗ: nba_tests/_t35_totals.csv (Crown, ΑΝΟΙΓΜΑ, 5 σεζον 2021-26): T γραμμη, oo/ou αποδοσεις, fair δικαιο, cfair κλεισιμο, tot πραγματικο, gn αγων.
(Α) ΚΛΙΜΑ: R_N = μεσο (πραγματικο − δικαιο ΚΛΕΙΣΙΜΑΤΟΣ) στα N προηγουμενα ματς της ΣΕΖΟΝ (ημερα < ημερα ματς), N ∈ {30, 60, 100, 150}
  (με λιγοτερα απο N/2 → κανενα). ΚΑΝΟΝΑΣ: over στο ανοιγμα αν R_N ≥ k, under αν R_N ≤ −k, k ∈ {2, 3, 4} π.
(Γ) ΡΟΣΤΕΡ: share = μεριδιο περσινων λεπτων που μενουν (nba_carry_share.json)· αγων ≤ 20· ομαδα «αλλαξε πολυ» = share < s, s ∈ {0.4, 0.5}·
  κατηγορια ματς: 0 / 1 / 2 ομαδες που αλλαξαν. ΚΑΝΟΝΑΣ: κατευθυνση (over/under) = προσημο του μεσου (πραγμ − ανοιγμα) της κατηγοριας στις ΑΛΛΕΣ σεζον.
LOSO: παραμετροι (και κατευθυνση στο Γ) απο τις αλλες 4 σεζον με μοναδες· ελεγχος στην 5η.
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ (καθε μερος χωριστα): LOSO picks n ≥ 150 ΚΑΙ ROI > 0 ΚΑΙ CLV > 0 (κλεισιμο προς το pick) ΚΑΙ θετικο σε ≥4/5 σεζον.
Περιγραφικα: κλιση (πραγμ − ανοιγμα) πανω στο R_N ανα σεζον · ανα αγωνα (≤10, 11-20, 21+). Εξοδος: nba_tests/t71_totals_league_roster_out.txt"""
import os, sys, json, collections
import numpy as np, pandas as pd
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC); sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
D = pd.read_csv(os.path.join(SC, '_t35_totals.csv'))
O = D[D.tau == 'ανοιγμα'].copy().sort_values(['sea', 'date', 'i']).reset_index(drop=True)
O = O.dropna(subset=['T', 'oo', 'ou', 'fair', 'cfair', 'tot'])
O['res_o'] = O.tot - O.fair; O['res_c'] = O.tot - O.cfair
SEAS = sorted(O.sea.unique())
def settle(r, side):                                   # side +1 over, −1 under · αποτελεσμα σε μοναδες στην τιμη ανοιγματος
    x = (r['tot'] - r['T']) * side
    od = r.oo if side > 0 else r.ou
    return (od - 1) if x > 0 else (0.0 if x == 0 else -1.0)
def summ(picks):
    if not picks: return '—', 0, 0.0, 0, 0.0
    df = pd.DataFrame(picks, columns=['sea', 'u', 'clv'])
    ps = df.groupby('sea').u.sum()
    return (f'{100 * df.u.mean():+6.1f}% ({len(df):4d}, {df.u.sum():+6.1f}μ, {int((ps > 0).sum())}/{df.sea.nunique()}) CLV {df.clv.mean():+.2f}π',
            len(df), 100 * df.u.mean(), int((ps > 0).sum()), df.clv.mean())
# ---------------- (Α) ΚΛΙΜΑ ----------------
NS, KS = (30, 60, 100, 150), (2, 3, 4)
for N in NS:
    vals = np.full(len(O), np.nan)
    for s in SEAS:
        idx = O.index[O.sea == s]; sub = O.loc[idx]
        for j, (ii, r) in enumerate(sub.iterrows()):
            prev = sub[sub.date < r.date].res_c.values[-N:]
            if len(prev) >= N / 2: vals[ii] = prev.mean()
    O[f'R{N}'] = vals
P('NBA ΣΥΝΟΛΑ ΣΤΟ ΑΝΟΙΓΜΑ (Crown) · 5 σεζον · ματς ' + str(len(O)))
P('\n=== (Α) ΚΛΙΜΑ ΣΚΟΡ: περιγραφικο — κλιση (πραγματικο − ανοιγμα) πανω στο R_N (1 = η αγορα δεν το εχει καθολου, 0 = το εχει) ===')
for N in NS:
    m = O[f'R{N}'].notna()
    b = np.polyfit(O.loc[m, f'R{N}'], O.loc[m, 'res_o'], 1)[0]
    bs = ' · '.join(f'{s % 100}: {np.polyfit(O.loc[m & (O.sea == s), f"R{N}"], O.loc[m & (O.sea == s), "res_o"], 1)[0]:+.2f}' for s in SEAS)
    P(f'  N={N:3d}: κλιση {b:+.2f} · ανα σεζον {bs} · ματς {int(m.sum())}')
def rule_A(r, N, k):
    v = r[f'R{N}']
    if np.isnan(v) or abs(v) < k: return 0
    return 1 if v > 0 else -1
P('\n  κανονες (ολες οι σεζον, μονο πληροφορια):')
for N in NS:
    for k in KS:
        pk = [(r.sea, settle(r, sd), sd * (r.cfair - r.fair)) for _, r in O.iterrows() if (sd := rule_A(r, N, k))]
        P(f'   N={N:3d} k={k}: {summ(pk)[0]}')
sel = {}
for Y in SEAS:
    oth = O[O.sea != Y]; best = None
    for N in NS:
        for k in KS:
            u = sum(settle(r, sd) for _, r in oth.iterrows() if (sd := rule_A(r, N, k)))
            if best is None or u > best[0]: best = (u, N, k)
    sel[Y] = best[1:]
pkA = [(r.sea, settle(r, sd), sd * (r.cfair - r.fair), r.gn) for _, r in O.iterrows() if (sd := rule_A(r, *sel[r.sea]))]
txt, n, roi, pos, clv = summ([p[:3] for p in pkA])
P(f'  LOSO επιλογες: ' + ' · '.join(f'{Y % 100}: N={sel[Y][0]} k={sel[Y][1]}' for Y in SEAS))
P(f'  LOSO: {txt}')
for lab, lo, hi in (('αγων ≤10', 1, 10), ('11-20', 11, 20), ('21+', 21, 999)):
    P(f'     {lab:9s} {summ([p[:3] for p in pkA if lo <= p[3] <= hi])[0]}')
okA = n >= 150 and roi > 0 and clv > 0 and pos >= 4
P(f'  ΚΡΙΤΗΡΙΟ (Α): n {n} (≥150) · ROI {roi:+.1f}% · CLV {clv:+.2f} · θετικες {pos}/5 → {"ΠΕΡΝΑΕΙ" if okA else "ΔΕΝ ΠΕΡΝΑΕΙ"}')
# ---------------- (Γ) ΡΟΣΤΕΡ ----------------
SH = json.load(open(os.path.join(ROOT, 'nba_carry_share.json'), encoding='utf-8'))['share']
O['sh_h'] = [SH.get(f'{s}|{h}', np.nan) for s, h in zip(O.sea, O.home)]; O['sh_a'] = [SH.get(f'{s}|{a}', np.nan) for s, a in zip(O.sea, O.away)]
E = O[(O.gn <= 20) & O.sh_h.notna() & O.sh_a.notna()].copy()
P(f'\n=== (Γ) ΟΜΑΔΕΣ ΠΟΥ ΑΛΛΑΞΑΝ ΠΟΛΥ (αγων ≤20, ματς {len(E)}) · μεριδιο περσινων λεπτων που μενουν ===')
for s_ in (0.4, 0.5):
    E[f'c{s_}'] = (E.sh_h < s_).astype(int) + (E.sh_a < s_).astype(int)
    for c in (0, 1, 2):
        x = E[E[f'c{s_}'] == c]
        if len(x) < 5: continue
        P(f'  share <{s_}: {c} ομαδες · n {len(x):4d} · πραγμ − ανοιγμα {x.res_o.mean():+5.2f} ± {x.res_o.std() / np.sqrt(len(x)):.2f} · κινηση ως κλεισιμο {(x.cfair - x.fair).mean():+.2f} · '
          'ανα σεζον ' + ' '.join(f'{s % 100}:{x[x.sea == s].res_o.mean():+.1f}' for s in SEAS if (x.sea == s).any()))
selC = {}
for Y in SEAS:
    oth = E[E.sea != Y]; best = None
    for s_ in (0.4, 0.5):
        for c in (1, 2):
            g = oth[oth[f'c{s_}'] >= c]
            if len(g) < 30: continue
            sd = 1 if g.res_o.mean() > 0 else -1
            u = sum(settle(r, sd) for _, r in g.iterrows())
            if best is None or u > best[0]: best = (u, s_, c, sd)
    selC[Y] = best[1:]
pkC = [(r.sea, settle(r, selC[r.sea][2]), selC[r.sea][2] * (r.cfair - r.fair)) for _, r in E.iterrows() if r[f'c{selC[r.sea][0]}'] >= selC[r.sea][1]]
txt, n, roi, pos, clv = summ(pkC)
P(f'  LOSO επιλογες: ' + ' · '.join(f'{Y % 100}: share<{selC[Y][0]} ≥{selC[Y][1]} ομαδες → {"over" if selC[Y][2] > 0 else "under"}' for Y in SEAS))
P(f'  LOSO: {txt}')
okC = n >= 150 and roi > 0 and clv > 0 and pos >= 4
P(f'  ΚΡΙΤΗΡΙΟ (Γ): n {n} (≥150) · ROI {roi:+.1f}% · CLV {clv:+.2f} · θετικες {pos}/5 → {"ΠΕΡΝΑΕΙ" if okC else "ΔΕΝ ΠΕΡΝΑΕΙ"}')
open(os.path.join(SC, 't71_totals_league_roster_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
