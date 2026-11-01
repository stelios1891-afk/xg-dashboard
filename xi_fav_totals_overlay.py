# -*- coding: utf-8 -*-
"""xi_fav_totals_overlay.py — 21/10/2026 (Στελιος: «θα χρειαστουμε τεστ για φαβορι και συνολα»).
Ιδιο με xi_model_overlay (ενδεκαδα ΠΑΝΩ στο μοντελο, τιμη της ιδιας στιγμης), αλλα με τους ΠΡΑΓΜΑΤΙΚΟΥΣ κανονες:
 ΦΑΒΟΡΙ 15+ (live κανονας): μηχανη live (σωστο SoS, κοκκινες emps) + αγκυρα ×0.7 (μαθαινει απο 7η) · σωστα τεταρτα · γραμμη ≤ −0.5 · 1.70-2.10
   (αναπαραγωγη core7_fav15_retune) · διορθωση ενδεκαδας στην υπεροχη: S' = S + Δ
 ΣΥΝΟΛΑ (υποψηφιος κανονας): συνολο μοντελου με αγκυρα συνολων απο 7η (core7_totals_anchor_md1_test, Γ1) · διορθωση: T' = T + Δσυνολου
 Στιγμες: 55′ πριν (ΕΠΙΣΗΜΗ ενδεκαδα: f_gd / f_t) και 6ω πριν (ΑΠΟΥΣΙΕΣ: g_gd / g_t) · Crown & Bet365 (μεσος).
ΚΡΙΤΗΡΙΟ (γραφτηκε ΠΡΙΝ): χρησιμη αν τα picks που ΒΓΑΙΝΟΥΝ χανουν, αυτα που ΜΠΑΙΝΟΥΝ κερδιζουν, και «με ενδεκαδα» > «μονο μοντελο» σε μοναδες
  ΚΑΙ ROI σε ≥3/4 σεζον."""
import sys, io, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
NL = chr(10)
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
# ---------- φαβορι: μηχανη live + αγκυρα 0.7 ----------
src = open('core7_fav15_retune.py', encoding='utf-8').read()
gF = {'__name__': 'xfav'}
with contextlib.redirect_stdout(_Q()):
    exec(src[:src.index('rows = []')], gF)
DF = gF['D']; S = gF['S0'] + 0.7 * (gF['SA'] - gF['S0']); TT = gF['T']; ev_ok = gF['ev_ok']
FAV = pd.DataFrame({'mid': DF.mid.astype(str).values, 'S': np.asarray(S), 'Tf': np.asarray(TT), 'md_f': DF.md.values})
# ---------- συνολα: αγκυρα συνολων απο 7η ----------
s2 = open('core7_totals_anchor_md1_test.py', encoding='utf-8').read()
gT = {'__name__': 'xtot'}
with contextlib.redirect_stdout(_Q()):
    exec(s2[:s2.index('rows = []; prestale = []')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass'), gT)
PT = gT['P']; TA = gT['anchored'](6); ou_eval, tdist = gT['ou_eval'], gT['tdist']
TOT = pd.DataFrame({'mid': PT.mid.astype(str).values, 'Ta': TA, 'sup_t': (PT.xg_h - PT.xg_a).values, 'md_t': PT.md.values})
# ---------- φορμουλες ενδεκαδας (επισημη / απουσιες) & τιμες ----------
M = pd.read_csv('xi_market_timing_rows.csv', dtype={'mid': str, 'season': str})
s3 = open('xi_pregame_eval.py', encoding='utf-8').read()
gP = {'__name__': 'xpre'}
with contextlib.redirect_stdout(_Q()):
    exec(s3[:s3.index("M = pd.read_csv('xi_market_timing_rows.csv'")], gP)
PRE = gP['D'][['mid', 'g_gd', 'g_t']]
M = M.merge(PRE, on='mid', how='left').merge(FAV, on='mid', how='left').merge(TOT, on='mid', how='left')
SE = sorted(M.season.unique())
rows = []
for r in M.to_dict('records'):
    for tp, a_gd, a_t in (('55′', 'f_gd', 'f_t'), ('6ω', 'g_gd', 'g_t')):
        # ---- φαβορι 15+ ----
        L, oh, oa = r.get(f'L_{tp}'), r.get(f'oh_{tp}'), r.get(f'oa_{tp}'); dg = r.get(a_gd)
        if r.get('S') == r.get('S') and r.get('md_f') == r.get('md_f') and r['md_f'] >= 14 and L == L and dg == dg and r['gd'] == r['gd']:
            lh = -L
            if abs(lh) >= 0.5:
                side = 1 if lh < 0 else -1; ud = -abs(lh); o = oh if side == 1 else oa
                if 1.70 <= o <= 2.10:
                    e = []
                    for sv in (r['S'], r['S'] + dg):
                        dist = picks.gd_dist_dom(max((r['Tf'] + sv) / 2, .05), max((r['Tf'] - sv) / 2, .05)); e.append(ev_ok(dist, side, ud, o))
                    rows.append(dict(mid=r['mid'], kind='fav', tp=tp, bk=r['bk'], season=r['season'], md=r['md_f'], e0=e[0], e1=e[1], pnl=picks.settle(r['gd'], side, ud, o)))
        # ---- συνολα ----
        L, oo, uu = r.get(f'OL_{tp}'), r.get(f'oo_{tp}'), r.get(f'ou_{tp}'); dt_ = r.get(a_t)
        if r.get('Ta') == r.get('Ta') and r.get('md_t') == r.get('md_t') and r['md_t'] >= 6 and L == L and dt_ == dt_ and r['tg'] == r['tg']:
            s_ = r['sup_t']
            for over, o in ((True, oo), (False, uu)):
                if not (1.70 <= o <= 2.10): continue
                ee = []
                for Tv in (r['Ta'], r['Ta'] + dt_):
                    d = tdist((Tv + s_) / 2, (Tv - s_) / 2); ee.append(ou_eval(d, L, over, o, int(r['tg'])))
                rows.append(dict(mid=r['mid'], kind='over' if over else 'under', tp=tp, bk=r['bk'], season=r['season'], md=r['md_t'], e0=ee[0][0], e1=ee[1][0], pnl=ee[0][1]))
R = pd.DataFrame(rows)
def summ(q):
    if not len(q): return '—'
    s = q.groupby('season').pnl.mean(); return f'{len(q) / 2:5.0f} {100 * q.pnl.mean():+6.1f}% ({sum(s > 0)}/4)'
def block(q, Ts, zone=None):
    print(f'      {"κατωφλι":10s} │ {"ΜΟΝΟ μοντελο":>20s} │ {"ΜΕ ενδεκαδα":>20s} │ {"κρατηθηκαν":>20s} │ {"ΒΓΗΚΑΝ":>20s} │ {"ΜΠΗΚΑΝ":>20s} │ μοναδες μονο → με')
    for lo, hi, lab in Ts:
        a = q[(q.e0 >= lo) & (q.e0 < hi)]; b = q[(q.e1 >= lo) & (q.e1 < hi)]
        kept = q[(q.e0 >= lo) & (q.e0 < hi) & (q.e1 >= lo) & (q.e1 < hi)]; out = a[~a.index.isin(kept.index)]; inn = b[~b.index.isin(kept.index)]
        sa, sb = a.groupby('season').pnl.mean(), b.groupby('season').pnl.mean(); better = sum(sb.get(s, -9) > sa.get(s, -9) for s in SE)
        print(f'      {lab:10s} │ {summ(a):>20s} │ {summ(b):>20s} │ {summ(kept):>20s} │ {summ(out):>20s} │ {summ(inn):>20s} │ {a.pnl.sum() / 2:+6.1f} → {b.pnl.sum() / 2:+6.1f} (ROI καλυτερο {better}/4)')
for tp, lab in (('55′', 'Ι. 55′ ΠΡΙΝ — ΕΠΙΣΗΜΗ ΕΝΔΕΚΑΔΑ'), ('6ω', 'ΙΙ. 6 ΩΡΕΣ ΠΡΙΝ — ΑΠΟΥΣΙΕΣ (συνηθισμενη 11αδα − λιστα Sofascore)')):
    print(f'{NL}{"=" * 150}{NL}{lab}')
    print('   ΦΑΒΟΡΙ 15+ (live κανονας: αγκυρα 0.7, σωστα τεταρτα)')
    block(R[(R.kind == 'fav') & (R.tp == tp)], [(0.08, 9, '≥8%'), (0.10, 9, '≥10% (live)'), (0.12, 9, '≥12%'), (0.10, 0.13, '10-13%')])
    for kd, kl in (('over', 'OVER'), ('under', 'UNDER')):
        for mm, ml in ((6, '7+'), (14, '15+')):
            print(f'   ΣΥΝΟΛΑ {kl} αγων. {ml} (αγκυρα συνολων απο 7η)')
            block(R[(R.kind == kd) & (R.tp == tp) & (R.md >= mm)], [(0.06, 9, '≥6%'), (0.08, 9, '≥8%'), (0.10, 9, '≥10%'), (0.12, 9, '≥12%')])
R.to_csv('xi_fav_totals_overlay_rows.csv', index=False)
