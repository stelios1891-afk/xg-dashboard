# -*- coding: utf-8 -*-
"""travel_scenarios.py — 25/10/2026 (Στελιος: «η κουραση κουβαλιεται — η Ντορτμουντ 3 εκτος σερι (2 Ευρωπη, 1 πρωταθλημα), η Αρσεναλ 2 εκτος
(πρωταθλημα+Ευρωπη) και μετα εντος· διαφορετικα σεναρια» → «τρεξτο» στις παλιες σεζον).
ΔΕΙΓΜΑ: ματς πρωταθληματος (CORE7 + οσες λιγκες εχουν αγορα στο travel_fatigue_full) που παιζει ομαδα της Δυτ./Κεντρ. Ευρωπης 1.5-6 μερες ΜΕΤΑ απο
ευρωπαικο, 2021-26. Ημερολογιο = πρωταθληματα + Ευρωπη + προκριματικα + ΚΥΠΕΛΛΑ (travel_fatigue_full). Αγορα = κλεισιμο Crown (αλλιως Bet365,
αλλιως 1Χ2 για διαφορα/συνολο — χωρις under). ΙΔΙΕΣ μετρησεις με το travel_fatigue_full (rt = γκολ − αγορα, und = under κλεισ., rc = διαφορα
της ομαδας − αγορα, opp = χαντικαπ κοντρα στην ομαδα).
ΟΙΚΟΓΕΝΕΙΕΣ ΣΕΝΑΡΙΩΝ (ΠΡΟ-ΔΗΛΩΜΕΝΕΣ, απο το τελευταιο ευρωπαικο και τα ματς των 14 ημερων πριν):
  Σ0  Ευρωπη ΕΝΤΟΣ (ελεγχος)
  Σ1  Ευρωπη ΕΚΤΟΣ, πριν απο αυτη ματς ΕΝΤΟΣ (σερι εκτος = 1)
  Σ2  Ευρωπη ΕΚΤΟΣ, σερι εκτος = 2  (π.χ. Αρσεναλ «Π✈ Ε✈»)
  Σ3  Ευρωπη ΕΚΤΟΣ, σερι εκτος ≥3 ΚΑΙ 2 ευρωπαικα εκτος στις 14 μερες (π.χ. Ντορτμουντ «Ε✈ Π✈ Ε✈»)
  Σ3β Ευρωπη ΕΚΤΟΣ, σερι εκτος ≥3, μονο 1 ευρωπαικο εκτος
  καθε οικογενεια × ματς πρωταθληματος ΕΝΤΟΣ/ΕΚΤΟΣ × ταξιδι του ευρωπαικου <1.500 / ≥1.500 χλμ· + «πυκνο» (≥4 ματς στις 14 μερες, με κυπελλα).
ΚΡΙΤΗΡΙΟ (γραφτηκε ΠΡΙΝ): σεναριο = ΣΗΜΑ για under μονο αν (α) ≥40 bets under, (β) γκολ−αγορα ιδια φορα σε ≥3/4 σεζον με αγορα AH/OU (2223-2526),
  (γ) |t| ≥ 2, (δ) under κλεισ. > 0 ΚΑΙ καλυτερο απο τον ελεγχο Σ0 της ιδιας εδρας. Αλλιως περιγραφη. Επισης κοιταμε αν η ΚΛΙΜΑΚΩΣΗ Σ1→Σ2→Σ3 πηγαινει
  προς τα κατω (αν η κουραση «κουβαλιεται», τα γκολ/η διαφορα πρεπει να πεφτουν βαθμιαια).
Δεν αλλαζει τιποτα live."""
import sys, os, io, contextlib
import numpy as np, pandas as pd
src = open('travel_fatigue_full.py', encoding='utf-8').read()
cut = src.index('def ms(v):')
g = {'__name__': 'tf'}
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
with contextlib.redirect_stdout(_Q()):
    exec(src[:cut].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass'), g)
sys.stdout = sys.__stdout__
sys.stdout.reconfigure(encoding='utf-8')
B, G, CAL, LOC, km = g['B'], g['G'], g['CAL'], g['LOC'], g['km']
B = B[(B.kind == 'dom') & B.rc.notna()].copy()
KIND = {'dom': 'Π', 'eu': 'Ε', 'cup': 'Κ'}


def sched(tid, mid):
    """Ματς της ομαδας στις 14 μερες πριν το mid (χωρις αυτο): λιστα (t, kind, away, km)· + ξεκουραση."""
    L = CAL.get(tid) or []
    y = G[mid]; t0 = y['t']
    prev = [e for e in L if e[0] < t0 - pd.Timedelta(hours=6)]
    win = [e for e in prev if (t0 - e[0]).total_seconds() / 86400 <= 14]
    before = prev[-len(win) - 1] if len(prev) > len(win) else None
    loc = LOC.get(before[2]) if (before and before[2]) else LOC.get(tid)
    out = []
    for e in win:
        ven = LOC.get(e[2]) if e[2] else loc
        out.append((e[0], KIND.get(e[4], '?'), bool(e[3]), km(loc, ven) if (loc and ven) else 0.0)); loc = ven or loc
    streak = 0
    for e in reversed(prev):
        if e[3]: streak += 1
        else: break
    rest = (t0 - prev[-1][0]).total_seconds() / 86400 if prev else np.nan
    return out, streak, rest


rows = []
for r in B.to_dict('records'):
    y = G[r['mid']]; tid = y['h'] if r['s2'] == 1 else y['a']; oid = y['a'] if r['s2'] == 1 else y['h']
    seq, streak, rest = sched(tid, r['mid']); _, ostreak, orest = sched(oid, r['mid'])
    eu_aw = sum(1 for s in seq if s[1] == 'Ε' and s[2])
    last_eu = [s for s in seq if s[1] == 'Ε']
    if not last_eu:
        continue
    eu_away = last_eu[-1][2]
    if not eu_away: fam = 'Σ0 Ευρωπη εντος (ελεγχος)'
    elif streak <= 1: fam = 'Σ1 εκτος σερι 1 (Π🏠 Ε✈)'
    elif streak == 2: fam = 'Σ2 εκτος σερι 2 (π.χ. Π✈ Ε✈)'
    elif eu_aw >= 2: fam = 'Σ3 σερι ≥3 & 2 Ευρωπη εκτος (Ε✈ Π✈ Ε✈)'
    else: fam = 'Σ3β σερι ≥3, 1 Ευρωπη εκτος'
    scen = ' '.join(f"{s[1]}{'✈' if s[2] else '🏠'}" for s in seq[-3:]) + (' → Π🏠' if r['nhome'] else ' → Π✈')
    # 25/10 (τεστ 4): ΚΑΤΑΣΤΑΣΗ ΤΟΥ ΑΝΤΙΠΑΛΟΥ — ευρωπαικο ≤6 μερες πριν; εκτος; ποσα χλμ;
    _oe = [e for e in (CAL.get(oid) or []) if e[4] == 'eu' and e[0] < G[r['mid']]['t'] and (G[r['mid']]['t'] - e[0]).total_seconds() / 86400 <= 6]
    opp_eu = bool(_oe); opp_eu_away = bool(_oe and _oe[-1][3])
    opp_trip = km(LOC.get(oid), LOC.get(_oe[-1][2])) if (opp_eu_away and _oe[-1][2]) else 0.0
    rows.append(dict(r, tid=tid, oid=oid, opp_eu=opp_eu, opp_eu_away=opp_eu_away, opp_trip=opp_trip,
                     fam=fam, scen=scen, streak=streak, eu_away14=eu_aw, n14=len(seq), rest=rest, orest=orest,
                     rest_diff=rest - orest if np.isfinite(orest) else np.nan, trip_band='≥1.500' if r['trip'] >= 1500 else '<1.500'))
D = pd.DataFrame(rows)
AH_SEAS = ['2223', '2324', '2425', '2526']


def stat(z, lab, base=None):
    rt = z.rt.dropna(); u = z.und.dropna(); rc = z.rc.dropna(); op = z.roi_opp.dropna() if 'roi_opp' in z else pd.Series(dtype=float)
    if len(rt) < 5:
        return None
    se = rt.std(ddof=1) / np.sqrt(len(rt)); t = rt.mean() / se if se > 0 else np.nan
    zz = z[z.sea.isin(AH_SEAS) & z.rt.notna()]
    sg = [np.sign(g.rt.mean()) for _, g in zz.groupby('sea') if len(g) >= 3]
    same = max(sum(1 for s in sg if s < 0), sum(1 for s in sg if s > 0)); dirn = '−' if sum(1 for s in sg if s < 0) >= sum(1 for s in sg if s > 0) else '+'
    useas = ' '.join(f"{s[2:]}:{100 * g.und.mean():+.0f}" for s, g in z[z.und.notna()].groupby('sea'))
    ok = (len(u) >= 40 and same >= 3 and abs(t) >= 2 and u.mean() > 0 and (base is None or u.mean() > base))
    return (f"   {lab:44s} n {len(rt):4d} │ γκολ−αγορα {rt.mean():+.2f}±{se:.2f} (t {t:+.1f}) {dirn} {same}/{len(sg)} │ under κλεισ. "
            f"{100 * u.mean():+6.1f}% ({len(u):3d}) [{useas}] │ διαφορα ομαδας−αγορα {rc.mean():+.2f} │ χαντ. κοντρα {100 * op.mean():+5.1f}%"
            + ('  ✓ ΣΗΜΑ' if ok else ''))


NL = chr(10)
print(f"ΣΕΝΑΡΙΑ ΚΟΥΡΑΣΗΣ — επομενο ματς πρωταθληματος μετα απο ευρωπαικο (1.5-6 μερες), ομαδες Δυτ./Κεντρ. Ευρωπης, 2021-26 · ματς {len(D)}")
print('γκολ−αγορα: + = μπηκαν περισσοτερα απο τη γραμμη συνολων στο κλεισιμο · under κλεισ. = ROI του under στο κλεισιμο (Crown/Bet365) ·')
print('διαφορα ομαδας−αγορα: + = η ομαδα της Ευρωπης πηγε καλυτερα απο οσο περιμενε η αγορα · χαντ. κοντρα = ROI χαντικαπ ΚΑΤΑ της ομαδας της Ευρωπης')
for venue, vlab in ((True, 'ΠΡΩΤΑΘΛΗΜΑ ΕΝΤΟΣ'), (False, 'ΠΡΩΤΑΘΛΗΜΑ ΕΚΤΟΣ')):
    print(f"{NL}{'=' * 170}{NL}### {vlab}")
    Z = D[D.nhome == venue]
    base = Z[Z.fam.str.startswith('Σ0')].und.mean()
    for fam in sorted(Z.fam.unique()):
        s = stat(Z[Z.fam == fam], fam, None if fam.startswith('Σ0') else base)
        if s: print(s)
        if not fam.startswith('Σ0'):
            for tb in ('<1.500', '≥1.500'):
                s = stat(Z[(Z.fam == fam) & (Z.trip_band == tb)], f'   └ ταξιδι Ευρωπης {tb} χλμ', base)
                if s: print(s)
    print('   — πυκνοτητα (ολες οι οικογενειες με Ευρωπη εκτος) —')
    W = Z[~Z.fam.str.startswith('Σ0')]
    for lab, m in (('≤3 ματς στις 14 μερες', W.n14 <= 3), ('≥4 ματς στις 14 μερες (με κυπελλα)', W.n14 >= 4),
                   ('ξεκουραση ≤3.0 μερες', W.rest <= 3.0), ('ξεκουραση >3.0', W.rest > 3.0),
                   ('λιγοτερη ξεκουραση απο αντιπαλο κατα ≥1μ', W.rest_diff <= -1), ('ιδια/περισσοτερη ξεκουραση', W.rest_diff > -1)):
        s = stat(W[m], lab, base)
        if s: print(s)
print(f"{NL}{'=' * 170}{NL}### ΣΥΧΝΟΤΕΡΑ ΑΚΡΙΒΗ ΣΕΝΑΡΙΑ (τελευταια 3 ματς → σημερα), n ≥ 25")
vc = D.scen.value_counts()
for sc, n in vc[vc >= 25].items():
    s = stat(D[D.scen == sc], sc)
    if s: print(s)
D.to_pickle('travel_scenarios.pkl')
# ---- 25/10 (ελεγχος πριν την αναφορα): το Σ3 ηταν ΟΛΟ μικρες λιγκες/προκριματικα με 1Χ2 → ιδιος πινακας ΜΟΝΟ με πραγματικη γραμμη AH/OU ----
print(f"{NL}{'=' * 170}{NL}### ΜΟΝΟ ΜΑΤΣ ΜΕ ΠΡΑΓΜΑΤΙΚΗ ΓΡΑΜΜΗ ΧΑΝΤΙΚΑΠ/ΣΥΝΟΛΩΝ (Crown/Bet365, 2022-26) · ματς {int((D.src == 'AH/OU').sum())} · λιγκες: "
      + ', '.join(f'{k} {v}' for k, v in D[D.src == 'AH/OU'].lg.value_counts().head(12).items()))
DA = D[D.src == 'AH/OU']
for venue, vlab in ((True, 'ΠΡΩΤΑΘΛΗΜΑ ΕΝΤΟΣ'), (False, 'ΠΡΩΤΑΘΛΗΜΑ ΕΚΤΟΣ')):
    print(f"--- {vlab}")
    Z = DA[DA.nhome == venue]; base = Z[Z.fam.str.startswith('Σ0')].und.mean()
    for fam in sorted(Z.fam.unique()):
        s = stat(Z[Z.fam == fam], fam, None if fam.startswith('Σ0') else base)
        if s: print(s)
        if not fam.startswith('Σ0'):
            for lab, m in (('<1.500', Z.trip < 1500), ('1.500-2.500', (Z.trip >= 1500) & (Z.trip < 2500)), ('≥2.500', Z.trip >= 2500)):
                s = stat(Z[(Z.fam == fam) & m], f'   └ ταξιδι Ευρωπης {lab} χλμ', base)
                if s: print(s)
