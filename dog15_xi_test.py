# -*- coding: utf-8 -*-
"""dog15_xi_test.py — 21/10/2026 (Στελιος: «επειδη το μοντελο ειναι μετριο, ας επικεντρωθουμε για αρχη ΜΟΝΟ στα αουτσαιντερ 15+ — να δουμε πως
βελτιωνουν οι ΠΡΟΒΛΕΠΟΜΕΝΕΣ ενδεκαδες (παρασκευη πρωι π.χ.) και οι LIVE (επισημες) ενδεκαδες»).
ΚΑΝΟΝΑΣ = ο live: αουτσαιντερ (γραμμη ≥ +0.5), αποδοση 1.70-2.10, edge ≥ 10% (p_cover, κρατηση 3%), αγωνιστικη 15+, CORE7. Μοντελο = ΣΗΜΕΡΙΝΗ live μηχανη (core7_live_replay: κοκκινες εμπειρικες + αγκυρα κοντων 15+).
ΜΕ ενδεκαδα: λ_γηπ = xg_h + Δ/2, λ_φιλ = xg_a − Δ/2 (Δ = διορθωση υπεροχης γηπεδουχου απο τη φορμουλα αξια + εμπιστοσυνη) — ιδιο με το Lineup Lab.
ΣΤΙΓΜΕΣ (τιμη ΤΗΣ ΙΔΙΑΣ στιγμης, Crown & Bet365 χωριστα):
  Α. ΠΡΟΗΓΟΥΜΕΝΗ ΜΕΡΑ (24ω πριν): ΠΡΟΒΛΕΠΟΜΕΝΗ 11αδα (predicted11, κλειδωνει ~25ω πριν) — μονο 2025-26, EPL/LaLiga/SerieA.
     Συντελεστες απο 2223-2425 (καμια διαρροη).
  Β. ΑΝΩ ΟΡΙΟ 24ω: η ΕΠΙΣΗΜΗ 11αδα σαν να την ξεραμε απο την προηγουμενη μερα (LOSO, 4 σεζον, 7 λιγκες) — «τελεια προβλεπομενη».
  Γ. 55′ ΠΡΙΝ: ΕΠΙΣΗΜΗ 11αδα (LOSO, 4 σεζον, 7 λιγκες) στην τιμη του 55′.
ΤΡΟΠΟΙ: (1) ΜΕ ΕΝΔΕΚΑΔΑ = ξαναϋπολογισμος edge (μπαινουν/βγαινουν picks) · (2) ΦΙΛΤΡΟ = μενουν τα picks του μοντελου, βγαινουν οσα η 11αδα
  ριχνει κατω απο 10% (κανενα νεο pick).
ΚΡΙΤΗΡΙΟ (γραφτηκε ΠΡΙΝ το τρεξιμο): χρησιμο αν ΜΕ ενδεκαδα → περισσοτερες μοναδες ΚΑΙ καλυτερο ROI σε ≥3/4 σεζον ΚΑΙ στα 2 βιβλια,
  με τα picks που ΒΓΑΙΝΟΥΝ αρνητικα. Για το Α (1 σεζον) μονο ενδειξη — δεν μπορει να περασει κριτηριο."""
import sys, io, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
NL = chr(10)
M = pd.read_csv('xi_market_timing_rows.csv', dtype={'mid': str, 'season': str})
# 21/10 (Στελιος «ιδια ακριβως μηχανη με το live;»): ΣΗΜΕΡΙΝΗ live μηχανη = cur_0.75_6_13~emps + αγκυρα κοντων γραμμων 15+ (core7_live_replay)
P = pd.read_csv('core7_live_replay.csv', dtype={'mid': str})[['mid', 'xg_h', 'xg_a', 'md', 'off_s']]
def anchored(xg_h, xg_a, off, md, line_abs):
    if md >= 15 and round(line_abs, 2) in (0.5, 0.75):
        T = xg_h + xg_a; s = (xg_h - xg_a) + off
        return max((T + s) / 2, .05), max((T - s) / 2, .05)
    return xg_h, xg_a
M = M.merge(P, on='mid')
M = M[(M.md >= 15) & M.gd.notna()]
# ---- διορθωση ΠΡΟΒΛΕΠΟΜΕΝΗΣ (2526): συντελεστες απο 2223-2425, ιδια με xi_predicted_eval ----
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
src = open('xi_xgi_eval.py', encoding='utf-8').read()
g0 = {'__name__': 'x0'}
with contextlib.redirect_stdout(_Q()): exec(src[:src.index("print(f'ματς {len(D)} · με xGI")], g0)
D = g0['D'].merge(pd.read_csv('xi_pregame_rows.csv', dtype={'mid': str}), on='mid', how='left')
for pre in ('r', 'a'):
    D[f'{pre}_gV'] = D[f'{pre}V_h'] - D[f'{pre}V_a']; D[f'{pre}_gT'] = D[f'{pre}T_h'] - D[f'{pre}T_a']
TR = D[(D.season != '2526') & D.a_gV.notna() & D.r_xgd.notna()]
X = np.column_stack([np.ones(len(TR)), TR.a_gV.fillna(0), TR.a_gT.fillna(0)]); bG = np.linalg.lstsq(X, TR.r_xgd.values, rcond=None)[0][1:]
ok = D.r_ok_h.fillna(False).astype(bool) & D.r_ok_a.fillna(False).astype(bool)
D['p_gd'] = np.where(ok & (D.season == '2526'), bG[0] * D.r_gV.fillna(0) + bG[1] * D.r_gT.fillna(0), np.nan)
M = M.merge(D[['mid', 'p_gd']], on='mid', how='left')
print(f'αγωνιστικη 15+ · ματς×βιβλια {len(M)} · με προβλεπομενη (2526) {M.p_gd.notna().sum()} · συντελεστες προβλ. αξια {bG[0]:+.3f} εμπιστ. {bG[1]:+.3f}')
print(f'μεγεθος διορθωσης |Δ| (γκολ): προβλεπομενη μεσο {M.p_gd.abs().mean():.3f} · top 20% ≥ {M.p_gd.abs().quantile(.8):.3f} │ '
      f'επισημη μεσο {M.f_gd.abs().mean():.3f} · top 20% ≥ {M.f_gd.abs().quantile(.8):.3f}')

def ed(pw, pp, o): return pw * (o - 1) * (1 - picks.MARGIN) - (1 - pw - pp)
def dog_edge(xh, xa, L_home, oh, oa):
    """L_home = γραμμη γηπεδουχου (Nowgoal: θετικη = δινει ο γηπεδουχος → γηπ. γραμμη = −L). Επιστρεφει (side, ln, o, edge) για τον αουτσαιντερ."""
    lnh = -L_home
    for side, ln, o in ((1, lnh, oh), (-1, -lnh, oa)):
        if ln >= 0.5 and 1.70 <= o <= 2.10:
            d = picks.gd_dist_dom(max(xh, .05), max(xa, .05)); pw, pp = picks.p_cover(d, side, ln); return side, ln, o, ed(pw, pp, o)
    return None
rows = []
for r in M.to_dict('records'):
    for case, tp, dcol in (('Α', '24ω', 'p_gd'), ('Β', '24ω', 'f_gd'), ('Γ', '55′', 'f_gd')):
        L, oh, oa, dl = r.get(f'L_{tp}'), r.get(f'oh_{tp}'), r.get(f'oa_{tp}'), r.get(dcol)
        if L is None or L != L or dl is None or dl != dl: continue
        xh, xa = anchored(r['xg_h'], r['xg_a'], r['off_s'], r['md'], abs(L))
        a = dog_edge(xh, xa, L, oh, oa)
        if not a: continue
        b = dog_edge(xh + dl / 2, xa - dl / 2, L, oh, oa)
        side, ln, o, e0 = a; e1 = b[3]
        pnl = picks.settle(r['gd'], side, ln, o)
        rows.append(dict(case=case, bk=r['bk'], season=r['season'], league=r['league'], e0=e0, e1=e1, pnl=pnl,
                         dl_side=dl * side))          # + = η 11αδα ευνοει τον αουτσαιντερ μας
B = pd.DataFrame(rows)
TH = 0.10
def cell(z):
    return f'{len(z):4d} {100 * z.pnl.mean():+6.1f}% {z.pnl.sum():+6.1f}μ' if len(z) else '   0      —        —'
def seasons(z0, z1):
    out = []
    for s in sorted(B.season.unique()):
        a, b = z0[z0.season == s], z1[z1.season == s]
        if len(a) == 0 and len(b) == 0: continue
        out.append(f"{s}: {a.pnl.sum():+5.1f}→{b.pnl.sum():+5.1f}μ")
    return ' · '.join(out)
TITLE = {'Α': 'Α. ΠΡΟΗΓΟΥΜΕΝΗ ΜΕΡΑ (24ω) — ΠΡΟΒΛΕΠΟΜΕΝΗ 11αδα (2025-26, EPL/LaLiga/SerieA)',
         'Β': 'Β. ΑΝΩ ΟΡΙΟ (24ω) — ΕΠΙΣΗΜΗ 11αδα σαν να ηταν γνωστη απο την προηγουμενη μερα (4 σεζον, CORE7)',
         'Γ': 'Γ. 55′ ΠΡΙΝ — ΕΠΙΣΗΜΗ 11αδα (4 σεζον, CORE7)'}
for case in ('Α', 'Β', 'Γ'):
    print(f'{NL}{"=" * 150}{NL}{TITLE[case]} · αουτσαιντερ 15+ · edge ≥ 10%')
    print(f'   {"βιβλιο":7s}│ {"ΜΟΝΟ μοντελο":>22s} │ {"ΜΕ ενδεκαδα":>22s} │ {"ΦΙΛΤΡΟ (μονο βγαζει)":>22s} │ {"ΒΓΗΚΑΝ":>22s} │ {"ΜΠΗΚΑΝ":>22s}')
    for bk in ('Crown', 'Bet365'):
        z = B[(B.case == case) & (B.bk == bk)]
        z0, z1 = z[z.e0 >= TH], z[z.e1 >= TH]
        kept = z[(z.e0 >= TH) & (z.e1 >= TH)]; out = z[(z.e0 >= TH) & (z.e1 < TH)]; inn = z[(z.e0 < TH) & (z.e1 >= TH)]
        print(f'   {bk:7s}│ {cell(z0)} │ {cell(z1)} │ {cell(kept)} │ {cell(out)} │ {cell(inn)}')
        print(f'   {"":7s}│ ανα σεζον (μονο → με): {seasons(z0, z1)}')
    # ευαισθησια κατωφλιου (μεσος 2 βιβλιων)
    z = B[B.case == case]
    line = []
    for th in (0.06, 0.08, 0.10, 0.12, 0.14):
        a, b = z[z.e0 >= th], z[z.e1 >= th]
        line.append(f'≥{100 * th:.0f}%: {100 * a.pnl.mean():+.1f}%→{100 * b.pnl.mean():+.1f}% ({a.pnl.sum() / 2:+.1f}→{b.pnl.sum() / 2:+.1f}μ)')
    print('   κατωφλια (μεσος 2 βιβλιων): ' + ' · '.join(line))
    # τα picks του μοντελου χωρισμενα κατα το τι λεει η 11αδα
    z0 = z[z.e0 >= TH]
    if len(z0):
        q = []
        for lab, m_ in (('11αδα ΚΟΝΤΡΑ ≥0.10 γκολ', z0.dl_side <= -0.10), ('ουδετερη', z0.dl_side.abs() < 0.10), ('11αδα ΥΠΕΡ ≥0.10 γκολ', z0.dl_side >= 0.10)):
            w = z0[m_]; q.append(f'{lab}: {len(w) // 2:4d} picks {100 * w.pnl.mean():+6.1f}%' if len(w) else f'{lab}: 0')
        print('   picks μοντελου ανα «τι λεει η 11αδα» (μεσος 2 βιβλιων): ' + ' │ '.join(q))
B.to_csv('dog15_xi_test_rows.csv', index=False)
