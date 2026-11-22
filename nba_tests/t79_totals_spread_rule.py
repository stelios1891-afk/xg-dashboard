# -*- coding: utf-8 -*-
"""t79_totals_spread_rule.py — ΣΥΝΟΛΑ NBA: PICKS ΑΝΑΛΟΓΑ ΜΕ ΤΟ ΜΕΓΕΘΟΣ ΤΟΥ ΧΑΝΤΙΚΑΠ (24/10/2026, Στελιος «ναι» στον ορισμο).
Μηχανισμος (t74-t78): (πραγματικο − γραμμη συνολου) αυξανεται με το |χαντικαπ| — ανισα ματς → περισσοτεροι ποντοι, κλειστα → λιγοτεροι.
ΚΑΝΟΝΑΣ: picks του μοντελου συνολων (edge ≥8%, ανοιγμα Crown, σ 18) ΜΕ το boost +k οταν |χαντ| ≥11 (k απο τις αλλες σεζον / τις προηγουμενες στο WF):
  OVER μονο αν |χαντ| ≥ X · UNDER μονο αν |χαντ| ≤ Y · τιποτα αλλο. X ∈ {6, 8, 10, 12}, Y ∈ {1.5, 3, 4.5}.
ΠΡΟ-ΔΗΛΩΜΕΝΟ (εγκριθηκε πριν το τρεξιμο): LOSO (X, Y απο τις αλλες 4 σεζον με μοναδες) → n ≥150 ΚΑΙ ROI >0 ΚΑΙ CLV >0 ΚΑΙ θετικο ≥4/5 σεζον
  ΚΑΙ WALK-FORWARD (2024 ← 2022-23 · 2025 ← 2022-24 · 2026 ← 2022-25, και k και X, Y μονο απο προηγουμενες) συνολο >0 ΚΑΙ θετικο ≥2/3.
Πληροφορια: ανα μηνα · συγκριση με «ολα τα picks» (με boost). Εξοδος: nba_tests/t79_totals_spread_rule_out.txt"""
import os, sys
SC = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(SC, 't77_boost_picks.py'), encoding='utf-8').read().split("for thr in (10, 11):")[0]
exec(src)
O['step'] = (O.asp >= 11).astype(float)
def kfit(seas):
    tr = O[O.sea.isin(seas)]; x = tr.step.values; return float((x * tr.rm.values).sum() / (x * x).sum())
def picks_rule(sub, k, X, Y):
    R = []
    for _, r in sub.iterrows():
        mu = r['mu'] + k * r['step']
        po = 1 - ND.cdf((r['T'] - mu) / SIG); eo = po * r['oo'] - 1; eu = (1 - po) * r['ou'] - 1
        sd, e = (1, eo) if eo >= eu else (-1, eu)
        if e < 0.08: continue
        if X is not None and ((sd > 0 and r['asp'] < X) or (sd < 0 and r['asp'] > Y)): continue
        R.append((r['sea'], sd, settle(r, sd), sd * (r['cfair'] - r['fair']), int(r['mon'])))
    return pd.DataFrame(R, columns=['sea', 'sd', 'u', 'clv', 'mon'])
def show(lab, d):
    if not len(d): Q(f'  {lab:34s} —'); return 0, 0, 0, 0
    ps = d.groupby('sea').u.sum()
    Q(f"  {lab:34s} {100 * d.u.mean():+6.1f}% ({len(d):4d}, {d.u.sum():+6.1f}μ, θετ {int((ps > 0).sum())}/{d.sea.nunique()}) CLV {d.clv.mean():+.2f}π · over {int((d.sd > 0).sum())} / under {int((d.sd < 0).sum())} · ανα σεζον "
      + ' '.join(f'{s % 100}:{ps[s]:+.1f}μ' for s in ps.index))
    return len(d), 100 * d.u.mean(), int((ps > 0).sum()), d.clv.mean()
GRID = [(X, Y) for X in (6, 8, 10, 12) for Y in (1.5, 3, 4.5)]
Q('NBA ΣΥΝΟΛΑ · picks μοντελου ανα μεγεθος χαντικαπ · ανοιγμα Crown · 5 σεζον')
Q('\n=== ΟΛΟ ΤΟ ΠΛΕΓΜΑ (ολες οι σεζον, μονο πληροφορια) ===')
kall = {Y: kfit([s for s in SEAS if s != Y]) for Y in SEAS}
cache = {}
for X, Y in GRID:
    d = pd.concat([picks_rule(O[O.sea == s], kall[s], X, Y) for s in SEAS]); cache[(X, Y)] = d
    show(f'over |χ|≥{X} · under |χ|≤{Y}', d)
Q('\n=== LOSO ===')
sel = {s: max(GRID, key=lambda g: cache[g][cache[g].sea != s].u.sum()) for s in SEAS}
Q('  επιλογες: ' + ' · '.join(f'{s % 100}: X={sel[s][0]} Y={sel[s][1]}' for s in SEAS))
L = pd.concat([cache[sel[s]][cache[sel[s]].sea == s] for s in SEAS])
n, roi, pos, clv = show('LOSO κανονας', L)
base = pd.concat([picks_rule(O[O.sea == s], kall[s], None, None) for s in SEAS]); show('συγκριση: ΟΛΑ τα picks (με boost)', base)
Q('  ανα μηνα (LOSO κανονας): ' + ' · '.join(f'{lab} {100 * L[L.mon.isin(ms)].u.mean():+.1f}% ({int(L.mon.isin(ms).sum())})' for lab, ms in (('Οκτ-Δεκ', (10, 11, 12)), ('Ιαν-Φεβ', (1, 2)), ('Μαρ-Απρ', (3, 4)))))
Q('\n=== WALK-FORWARD (k, X, Y μονο απο τις ΠΡΟΗΓΟΥΜΕΝΕΣ σεζον) ===')
W = []
for s in (2024, 2025, 2026):
    prev = [x for x in SEAS if x < s]; kp = kfit(prev)
    best = max(GRID, key=lambda g: pd.concat([picks_rule(O[O.sea == p], kp, *g) for p in prev]).u.sum())
    d = picks_rule(O[O.sea == s], kp, *best); W.append(d)
    Q(f'  {s}: k {kp:+.2f} · X={best[0]} Y={best[1]} · {100 * d.u.mean():+.1f}% ({len(d)}, {d.u.sum():+.1f}μ) CLV {d.clv.mean():+.2f}')
WF = pd.concat(W); wps = WF.groupby('sea').u.sum()
Q(f'  WF συνολο: {100 * WF.u.mean():+.1f}% ({len(WF)}, {WF.u.sum():+.1f}μ) · θετικες {int((wps > 0).sum())}/3')
ok = n >= 150 and roi > 0 and clv > 0 and pos >= 4 and WF.u.sum() > 0 and (wps > 0).sum() >= 2
Q(f'\nΚΡΙΤΗΡΙΟ: LOSO n {n} (≥150) · ROI {roi:+.1f}% (>0) · CLV {clv:+.2f} (>0) · θετικες {pos}/5 (≥4) · WF {WF.u.sum():+.1f}μ (>0), {int((wps > 0).sum())}/3 (≥2) → '
  f'{"ΠΕΡΝΑΕΙ" if ok else "ΔΕΝ ΠΕΡΝΑΕΙ"}')
open(os.path.join(SC, 't79_totals_spread_rule_out.txt'), 'w', encoding='utf-8').write('\n'.join(out2))
