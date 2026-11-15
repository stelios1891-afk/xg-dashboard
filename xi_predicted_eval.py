# -*- coding: utf-8 -*-
"""xi_predicted_eval.py — 21/10/2026 (Στελιος: «ναι» — ΠΡΑΓΜΑΤΙΚΕΣ ΠΡΟΒΛΕΠΟΜΕΝΕΣ ενδεκαδες για το πρωι αντι για τη δικη μας εκτιμηση).
ΔΕΙΓΜΑ: 2025-26, EPL / LaLiga / Serie A — προβλεπομενες 11αδες predicted11 (κλειδωνουν ~25ω πριν), pred_pids_2526.json.
ΙΔΙΑ ΦΟΡΜΟΥΛΑ, ΙΔΙΟΣ ΟΡΙΣΜΟΣ για 4 ενδεκαδες (ολες vs τη ΣΥΝΗΘΙΣΜΕΝΗ): καμια (μοντελο σκετο) · ΔΙΚΗ ΜΑΣ (συνηθισμενη − λιστα Sofascore) ·
  ΠΡΟΒΛΕΠΟΜΕΝΗ (predicted11) · ΠΡΑΓΜΑΤΙΚΗ (επισημη, μονο για συγκριση/55′).
ΣΥΝΤΕΛΕΣΤΕΣ: απο τις ΑΛΛΕΣ σεζον (2223-2425, πραγματικη 11αδα vs συνηθισμενη) → εφαρμογη στο 2526 (καμια διαρροη).
ΜΕΤΡΑ (Crown): λαθος² · ΚΛΙΣΗ περα απο την αγορα στις 24ω / 6ω / 55′ · κινηση αγορας 24ω→6ω→55′→κλεισιμο προς τη φορμουλα ·
  πονταρισμα «ενδεκαδα πανω στο μοντελο» (αουτσαιντερ/φαβορι/over/under, σταθερα κατωφλια) στις 24ω και 6ω."""
import sys, io, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks, euro_shadow_scan as ES
NL = chr(10)
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
src = open('xi_xgi_eval.py', encoding='utf-8').read()
g0 = {'__name__': 'x0'}
with contextlib.redirect_stdout(_Q()): exec(src[:src.index("print(f'ματς {len(D)} · με xGI")], g0)
D = g0['D']
P = pd.read_csv('xi_pregame_rows.csv', dtype={'mid': str}); D = D.merge(P, on='mid', how='left')
for pre in ('p', 'r', 'a'):
    D[f'{pre}_gV'] = D[f'{pre}V_h'] - D[f'{pre}V_a']; D[f'{pre}_gT'] = D[f'{pre}T_h'] - D[f'{pre}T_a']
    for k in ('VO', 'VD', 'TO', 'TD', 'XGI'): D[f'{pre}_t{k}'] = D[f'{pre}{k}_h'] + D[f'{pre}{k}_a']
TR = D[(D.season != '2526') & D.a_gV.notna()]
def coef(cols, y):
    q = TR[TR[y].notna()]; X = np.column_stack([np.ones(len(q))] + [q[c].fillna(0).values for c in cols]); return np.linalg.lstsq(X, q[y].values, rcond=None)[0][1:]
bG = coef(['a_gV', 'a_gT'], 'r_xgd'); bT = coef(['a_tVO', 'a_tVD', 'a_tTO', 'a_tTD', 'a_tXGI'], 'r_tx')
print(f'συντελεστες (2223-2425, πραγματικη 11αδα vs συνηθισμενη): χαντικαπ αξια {bG[0]:+.3f} · εμπιστ. {bG[1]:+.3f} │ συνολα ' + ' '.join(f'{v:+.3f}' for v in bT))
T = D[(D.season == '2526') & D.r_ok_h.fillna(False).astype(bool) & D.r_ok_a.fillna(False).astype(bool)].copy()
for pre, lab in (('p', 'sofa'), ('r', 'pred'), ('a', 'act')):
    T[f'fg_{lab}'] = bG[0] * T[f'{pre}_gV'].fillna(0) + bG[1] * T[f'{pre}_gT'].fillna(0)
    T[f'ft_{lab}'] = sum(b * T[f'{pre}_t{k}'].fillna(0) for b, k in zip(bT, ('VO', 'VD', 'TO', 'TD', 'XGI')))
T['fg_none'] = 0.0; T['ft_none'] = 0.0; T['tg'] = T.hg + T.ag
print(f'ματς 2025-26 με προβλεπομενες και στις 2 ομαδες: {len(T)} · ' + ' · '.join(f'{l}: {(T.league == l).sum()}' for l in sorted(T.league.unique())))
print(f'ποσο μοιαζουν με την πραγματικη (συσχετιση της διορθωσης): δικη μας {T[["fg_sofa", "fg_act"]].corr().iloc[0, 1]:.2f} · προβλεπομενη {T[["fg_pred", "fg_act"]].corr().iloc[0, 1]:.2f}')
M = pd.read_csv('xi_market_timing_rows.csv', dtype={'mid': str, 'season': str}); M = M[M.bk == 'Crown']
Q = T.merge(M[['mid'] + [c for c in M.columns if c.startswith(('s_', 'T_', 'L_', 'oh_', 'oa_', 'OL_', 'oo_', 'ou_'))]], on='mid', how='inner')
gT = {'__name__': 'xt'}; s2 = open('core7_totals_anchor_md1_test.py', encoding='utf-8').read()
with contextlib.redirect_stdout(_Q()): exec(s2[:s2.index('rows = []; prestale = []')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass'), gT)
TOT = pd.DataFrame({'mid': gT['P'].mid.astype(str).values, 'Ta': gT['anchored'](6)}); Q = Q.merge(TOT, on='mid', how='left')
def slope(x, y):
    m = np.isfinite(x) & np.isfinite(y); x, y = x[m], y[m]
    if len(x) < 30: return np.nan, np.nan
    X = np.column_stack([np.ones(len(x)), x]); b = np.linalg.lstsq(X, y, rcond=None)[0]; res = y - X @ b
    return b[1], np.sqrt((res ** 2).sum() / (len(x) - 2) / ((x - x.mean()) ** 2).sum())
VERS = (('none', 'καμια (σκετο μοντελο)'), ('sofa', 'ΔΙΚΗ ΜΑΣ (συνηθ. − Sofascore)'), ('pred', 'ΠΡΟΒΛΕΠΟΜΕΝΗ (predicted11)'), ('act', 'ΠΡΑΓΜΑΤΙΚΗ (επισημη)'))
print(f'{NL}{"=" * 140}{NL}Α. ΧΑΝΤΙΚΑΠ — λαθος² και ΚΛΙΣΗ περα απο την αγορα (Crown) στη στιγμη: 24ω · 6ω · 55′  (n {len(Q)})')
for v, lab in VERS:
    m = (Q.xg_h - Q.xg_a) + Q[f'fg_{v}']
    parts = []
    for tp in ('24ω', '6ω', '55′'):
        b, se = slope((m - Q[f's_{tp}']).values, (Q.gd - Q[f's_{tp}']).values); parts.append(f'{tp} {b:+.2f}±{se:.2f}')
    print(f'   {lab:32s} │ λαθος² {((Q.gd - m) ** 2).mean():.4f} │ κλιση ' + ' · '.join(parts))
print(f'{NL}Β. ΣΥΝΟΛΑ — λαθος² και ΚΛΙΣΗ περα απο την αγορα')
q = Q[Q.Ta.notna()]
for v, lab in VERS:
    m = q.Ta + q[f'ft_{v}']
    parts = []
    for tp in ('24ω', '6ω', '55′'):
        b, se = slope((m - q[f'T_{tp}']).values, (q.tg - q[f'T_{tp}']).values); parts.append(f'{tp} {b:+.2f}±{se:.2f}')
    print(f'   {lab:32s} │ λαθος² {((q.tg - m) ** 2).mean():.4f} │ κλιση ' + ' · '.join(parts))
print(f'{NL}Γ. ΚΙΝΗΣΗ ΑΓΟΡΑΣ προς τη διορθωση της ΠΡΟΒΛΕΠΟΜΕΝΗΣ (1 = κουνηθηκε οσο λεει η φορμουλα) — την ειχε η αγορα στις 24ω;')
for kind, f, pre in (('χαντικαπ', 'fg_pred', 's'), ('συνολα', 'ft_pred', 'T')):
    out = []
    for a, b in (('24ω', '6ω'), ('6ω', '55′'), ('55′', 'κλεισ.')):
        bb, se = slope(Q[f].values, (Q[f'{pre}_{b}'] - Q[f'{pre}_{a}']).values); out.append(f'{a}→{b} {bb:+.2f}±{se:.2f}')
    print(f'   {kind:9s}: ' + ' · '.join(out))
# ---- πονταρισμα: διορθωση πανω στο μοντελο ----
def ed(pw, pp, o): return pw * (o - 1) * (1 - picks.MARGIN) - (1 - pw - pp)
rows = []
for r in Q.to_dict('records'):
    for tp in ('24ω', '6ω'):
        L, oh, oa = r.get(f'L_{tp}'), r.get(f'oh_{tp}'), r.get(f'oa_{tp}')
        if L == L and r['gd'] == r['gd']:
            lnh = -L
            for v in ('none', 'sofa', 'pred'):
                dl = r[f'fg_{v}']; d = picks.gd_dist(max(r['xg_h'] + dl / 2, .05), max(r['xg_a'] - dl / 2, .05))
                for side, ln, o in ((1, lnh, oh), (-1, -lnh, oa)):
                    if not (1.70 <= o <= 2.10) or abs(ln) < 0.5: continue
                    role = 'dog' if ln >= 0.5 else 'fav'
                    pw, pp = picks.p_cover(d, side, ln) if role == 'dog' else ES.cover_q(d, side, ln)
                    rows.append(dict(tp=tp, v=v, kind=role, e=ed(pw, pp, o), pnl=picks.settle(r['gd'], side, ln, o)))
        L, oo, uu = r.get(f'OL_{tp}'), r.get(f'oo_{tp}'), r.get(f'ou_{tp}')
        if L == L and r['tg'] == r['tg'] and r.get('Ta') == r.get('Ta'):
            s_ = r['xg_h'] - r['xg_a']
            for v in ('none', 'sofa', 'pred'):
                Tv = r['Ta'] + r[f'ft_{v}']; d = gT['tdist']((Tv + s_) / 2, (Tv - s_) / 2)
                for over, o in ((True, oo), (False, uu)):
                    if not (1.70 <= o <= 2.10): continue
                    e, p = gT['ou_eval'](d, L, over, o, int(r['tg'])); rows.append(dict(tp=tp, v=v, kind='over' if over else 'under', e=e, pnl=p))
B = pd.DataFrame(rows)
print(f'{NL}Δ. ΠΟΝΤΑΡΙΣΜΑ (2025-26, Crown): picks / ROI / μοναδες με edge ≥ 10% — σκετο μοντελο vs + δικη μας vs + προβλεπομενη')
for tp in ('24ω', '6ω'):
    for kd in ('dog', 'fav', 'over', 'under'):
        cells = []
        for v in ('none', 'sofa', 'pred'):
            z = B[(B.tp == tp) & (B.kind == kd) & (B.v == v) & (B.e >= .10)]
            cells.append(f'{len(z):4d} {100 * z.pnl.mean():+6.1f}% {z.pnl.sum():+6.1f}μ' if len(z) else '   —')
        print(f'   {tp:4s} {kd:6s} │ ' + ' │ '.join(cells))
