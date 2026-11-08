# -*- coding: utf-8 -*-
"""xi_model_overlay.py — 21/10/2026 (Στελιος: «θελουμε η αλλαγη των ενδεκαδων να μπαινει ΠΑΝΩ στο μοντελο — εκει που ελεγε edge 6% στο αουτσαιντερ,
τωρα που το φαβορι εχει 2-3 αλλαγες να πηγαινει 12% π.χ. — αυτο κοιταμε»).
ΓΙΑ ΚΑΘΕ ματς CORE7 2223-2526 και καθε πλευρα: edge του live μοντελου (core7_mech_preds_bl_0.6) ΧΩΡΙΣ και ΜΕ διορθωση ενδεκαδας, στην τιμη ΤΗΣ ΙΔΙΑΣ στιγμης:
  (Ι) 55′ πριν, ΕΠΙΣΗΜΗ ενδεκαδα (f_gd: αξια + εμπιστοσυνη, LOSO) · (ΙΙ) 6 ωρες πριν, ΑΠΟΥΣΙΕΣ πρωινου (g_gd: αναμενομενη 11αδα, LOSO)
  μοντελο με διορθωση: λ_γηπ = xg_h + Δ/2, λ_φιλ = xg_a − Δ/2 (Δ = διορθωση υπεροχης).
ΡΟΛΟΙ οπως στο live: αουτσαιντερ (παιρνει ≥0.5, p_cover) · φαβορι (δινει ≥0.5, σωστα τεταρτα) · τιμη 1.70-2.10 · edge = live τυπος (κρατηση 3%).
ΣΥΓΚΡΙΣΗ για καθε κατωφλι: picks ΜΟΝΟ μοντελου vs ΜΕ ενδεκαδα → ROI, και χωρισμα: κρατηθηκαν / ΒΓΗΚΑΝ (η ενδεκαδα εριξε το edge) / ΜΠΗΚΑΝ (το ανεβασε).
Αγωνιστικες 7+ (και 15+ χωριστα, οπου ζουν τα live εγχωρια). Μεσος ορος Crown & Bet365.
ΚΡΙΤΗΡΙΟ (γραφτηκε ΠΡΙΝ): η διορθωση ειναι χρησιμη αν (α) τα picks που ΒΓΑΖΕΙ χανουν και τα picks που ΜΠΑΙΝΟΥΝ κερδιζουν, (β) το συνολο «με ενδεκαδα» εχει
  καλυτερο ROI ΚΑΙ οχι λιγοτερες μοναδες, σε ≥3/4 σεζον."""
import sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks, euro_shadow_scan as ES
NL = chr(10)
src = open('xi_pregame_eval.py', encoding='utf-8').read()
exec(src[:src.index("M = pd.read_csv('xi_market_timing_rows.csv'")])           # D με g_gd (απουσιες πριν, LOSO)
PRE = D[['mid', 'g_gd']]
M = pd.read_csv('xi_market_timing_rows.csv', dtype={'mid': str, 'season': str})
Pm = pd.read_csv('core7_mech_preds_bl_0.6.csv', dtype={'mid': str})[['mid', 'xg_h', 'xg_a', 'md']]
M = M.merge(Pm, on='mid').merge(PRE, on='mid', how='left')
SE = sorted(M.season.unique())
def ed(pw, pp, o): return pw * (o - 1) * (1 - picks.MARGIN) - (1 - pw - pp)
def side_edges(xh, xa, ln_home, oh, oa):
    d = picks.gd_dist(max(xh, .05), max(xa, .05)); out = []
    for side, ln, o in ((1, ln_home, oh), (-1, -ln_home, oa)):
        if not (1.70 <= o <= 2.10): out.append(None); continue
        if ln >= 0.5: pw, pp = picks.p_cover(d, side, ln); role = 'dog'
        elif ln <= -0.5: pw, pp = ES.cover_q(d, side, ln); role = 'fav'
        else: out.append(None); continue
        out.append((side, ln, o, role, ed(pw, pp, o)))
    return out
rows = []
for r in M.to_dict('records'):
    if r['gd'] != r['gd'] or r['md'] < 6: continue
    for tp, adj in (('55′', 'f_gd'), ('6ω', 'g_gd')):
        L, oh, oa = r.get(f'L_{tp}'), r.get(f'oh_{tp}'), r.get(f'oa_{tp}')
        dlt = r.get(adj)
        if L is None or L != L or dlt is None or dlt != dlt: continue
        lnh = -L                                                  # Nowgoal: θετικη = δινει ο γηπεδουχος
        base = side_edges(r['xg_h'], r['xg_a'], lnh, oh, oa); new = side_edges(r['xg_h'] + dlt / 2, r['xg_a'] - dlt / 2, lnh, oh, oa)
        for b, n in zip(base, new):
            if b is None: continue
            side, ln, o, role, e0 = b; e1 = n[4]
            rows.append(dict(mid=r['mid'], tp=tp, bk=r['bk'], season=r['season'], md=r['md'], role=role, e0=e0, e1=e1, d=dlt * side, pnl=picks.settle(r['gd'], side, ln, o)))
R = pd.DataFrame(rows)
print(f'πλευρες-τιμες: {len(R)} · μεση |αλλαγη edge| απο ενδεκαδα: 55′ {100 * (R[R.tp == "55′"].e1 - R[R.tp == "55′"].e0).abs().mean():.1f}% · 6ω {100 * (R[R.tp == "6ω"].e1 - R[R.tp == "6ω"].e0).abs().mean():.1f}%')
def summ(q):
    if not len(q): return '—'
    s = q.groupby('season').pnl.mean(); return f'{len(q) / 2:5.0f} {100 * q.pnl.mean():+6.1f}% ({sum(s > 0)}/4)'
for tp, lab in (('55′', 'Ι. 55′ ΠΡΙΝ — ΕΠΙΣΗΜΗ ΕΝΔΕΚΑΔΑ'), ('6ω', 'ΙΙ. 6 ΩΡΕΣ ΠΡΙΝ — ΑΠΟΥΣΙΕΣ ΠΡΩΙΝΟΥ')):
    print(f'{NL}{"=" * 150}{NL}{lab}  (picks, ROI, θετικες σεζον — μεσος Crown/Bet365)')
    for role, rl in (('dog', 'ΑΟΥΤΣΑΙΝΤΕΡ'), ('fav', 'ΦΑΒΟΡΙ')):
        for mdl, mmin in (('αγων. 7+', 6), ('αγων. 15+', 14)):
            q = R[(R.tp == tp) & (R.role == role) & (R.md >= mmin)]
            print(f'   {rl} {mdl}')
            print(f'      {"κατωφλι":8s} │ {"ΜΟΝΟ μοντελο":>20s} │ {"ΜΕ ενδεκαδα":>20s} │ {"κρατηθηκαν":>20s} │ {"ΒΓΗΚΑΝ":>20s} │ {"ΜΠΗΚΑΝ":>20s} │ μοναδες μονο → με')
            for T in (0.04, 0.06, 0.08, 0.10, 0.12):
                a, b = q[q.e0 >= T], q[q.e1 >= T]; kept = q[(q.e0 >= T) & (q.e1 >= T)]; out = q[(q.e0 >= T) & (q.e1 < T)]; inn = q[(q.e0 < T) & (q.e1 >= T)]
                ua, ub = a.pnl.sum() / 2, b.pnl.sum() / 2
                sa, sb = a.groupby('season').pnl.mean(), b.groupby('season').pnl.mean()
                better = sum((sb.get(s, 0) > sa.get(s, 0)) for s in SE)
                print(f'      ≥{int(T * 100):2d}%     │ {summ(a):>20s} │ {summ(b):>20s} │ {summ(kept):>20s} │ {summ(out):>20s} │ {summ(inn):>20s} │ {ua:+6.1f} → {ub:+6.1f} (καλυτερο ROI σε {better}/4)')
R.to_csv('xi_model_overlay_rows.csv', index=False)
