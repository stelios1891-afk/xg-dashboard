# -*- coding: utf-8 -*-
"""xi_pregame_eval.py — 21/10/2026: ΣΕΝΑΡΙΟ «ΠΡΩΙ ΜΕ ΡΕΠΟΡΤΑΖ» — η αναμενομενη ενδεκαδα (συνηθισμενη χωρις τους απουσες της λιστας) με τη φορμουλα.
Φορμουλα ΠΡΙΝ το ματς (συντελεστες LOSO πανω στα ιδια τα χαρακτηριστικα πριν το ματς, 3 σεζον → 4η):
  χαντικαπ = αξια + εμπιστοσυνη (διαφορα αναμενομενης − συνηθισμενης, γηπ − φιλ) · συνολα = εμπιστ./αξια επιθεσης & αμυνας + xGI (αθροισμα 2 ομαδων)
ΕΡΩΤΗΣΕΙΣ: (α) βελτιωνει την προβλεψη του μοντελου; · (β) η αγορα 24ω / 6ω / 55′ / κλεισιμο το εχει ηδη; (κλιση του λαθους της τιμης πανω στη φορμουλα)
  (γ) κινηση αγορας 24ω→6ω→55′→κλεισιμο προς τη μερια της φορμουλας · (δ) πονταρισμα «το πρωι» (6ω πριν) και 24ω πριν, οταν |φορμουλα| στο top 10%
ΚΡΙΤΗΡΙΟ (δ) (γραφτηκε ΠΡΙΝ): ROI > 0 σε ≥3/4 σεζον στα 2 βιβλια και η τιμη να κινειται υπερ μας ως το κλεισιμο."""
import sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
NL = chr(10)
src = open('xi_xgi_eval.py', encoding='utf-8').read()
exec(src[:src.index("print(f'ματς {len(D)} · με xGI")])          # D: στοχοι, gains, boot, show
P = pd.read_csv('xi_pregame_rows.csv', dtype={'mid': str})
D = D.merge(P, on='mid', how='left')
for k in ('V', 'T'): D[f'q_{k}'] = D[f'p{k}_h'] - D[f'p{k}_a']; D[f'qd_{k}'] = D[f'pd{k}_h'] - D[f'pd{k}_a']
for k in ('VO', 'VD', 'TO', 'TD', 'XGI'): D[f't_{k}'] = D[f'p{k}_h'].fillna(0) + D[f'p{k}_a'].fillna(0); D[f'td_{k}'] = D[f'pd{k}_h'].fillna(0) + D[f'pd{k}_a'].fillna(0)
D = D[D.pV_h.notna() & D.pV_a.notna()].copy()
_defs = src[src.index('def gains('):src.index("print(f'ματς {len(D)}')")] if "def gains(" in src else None
s2 = open('xi_age_totals_eval.py', encoding='utf-8').read(); exec(s2[s2.index('def gains('):s2.index("print(f'ματς {len(D)}')")])
SE = sorted(D.season.unique())
print(f'ματς με λιστα απουσων και στις 2 ομαδες: {len(D)} · ανα σεζον ' + ' · '.join(f'{s}: {(D.season == s).sum()}' for s in SE))
print(f'Δ υπεροχης απο απουσιες (αναμενομενη − συνηθισμενη): sd αξιας {D.q_V.std():.3f} · εμπιστ. {D.q_T.std():.3f} · ματς με ≥2 βασικους εκτος (μια ομαδα): {((D.nreg_h >= 2) | (D.nreg_a >= 2)).mean():.0%}')
YD = [('r_xgd', 'xG'), ('r_gd', 'γκολ')]; YT = [('r_tx', 'xG'), ('r_tg', 'γκολ')]
print(f'{NL}{"=" * 140}{NL}(α) ΒΕΛΤΙΩΝΕΙ ΤΗΝ ΠΡΟΒΛΕΨΗ ΤΟΥ ΜΟΝΤΕΛΟΥ; (βελτιωση ×1000 εκτος δειγματος [90%], ανα σεζον)')
show('χαντικαπ: απουσιες (λειπουν)', ['q_V', 'q_T'], YD)
show('χαντικαπ: απουσιες + αμφιβολοι εκτος', ['qd_V', 'qd_T'], YD)
show('συνολα: απουσιες (λειπουν)', ['t_VO', 't_VD', 't_TO', 't_TD', 't_XGI'], YT)
show('συνολα: + αμφιβολοι εκτος', ['td_VO', 'td_VD', 'td_TO', 'td_TD', 'td_XGI'], YT)
def loso_pred(cols, y):
    p = pd.Series(np.nan, index=D.index)
    for s in SE:
        tr = D[(D.season != s) & D[y].notna()]; te = D[D.season == s]
        X = np.column_stack([np.ones(len(tr))] + [tr[c].fillna(0).values for c in cols]); b = np.linalg.lstsq(X, tr[y].values, rcond=None)[0]
        p[te.index] = np.column_stack([np.zeros(len(te))] + [te[c].fillna(0).values for c in cols]) @ b
    return p
D['g_gd'] = loso_pred(['q_V', 'q_T'], 'r_xgd'); D['g_t'] = loso_pred(['t_VO', 't_VD', 't_TO', 't_TD', 't_XGI'], 'r_tx')
M = pd.read_csv('xi_market_timing_rows.csv', dtype={'mid': str, 'season': str})
Q = M.merge(D[['mid', 'g_gd', 'g_t']], on='mid', how='inner')
def fit(x, y):
    m = np.isfinite(x) & np.isfinite(y); x, y = x[m], y[m]
    xc = x - x.mean(); b = (xc * (y - y.mean())).sum() / (xc ** 2).sum(); res = y - y.mean() - b * xc
    return b, b / np.sqrt((res ** 2).sum() / (len(x) - 2) / (xc ** 2).sum()), len(x)
TPS = ['24ω', '6ω', '55′', 'κλεισ.']
for kind, f, pre, yv in (('ΧΑΝΤΙΚΑΠ', 'g_gd', 's', 'gd'), ('ΣΥΝΟΛΑ', 'g_t', 'T', 'tg')):
    print(f'{NL}{"=" * 140}{NL}{kind} — φορμουλα ΠΡΙΝ το ματς (απουσιες)')
    for bk in ('Crown', 'Bet365'):
        q = Q[Q.bk == bk]
        res = ' · '.join(f'{t} {fit(q[f].values, (q[yv] - q[f"{pre}_{t}"]).values)[0]:+.2f} (t {fit(q[f].values, (q[yv] - q[f"{pre}_{t}"]).values)[1]:.1f})' for t in TPS)
        mv = ' · '.join(f'{a}→{b} {fit(q[f].values, (q[f"{pre}_{b}"] - q[f"{pre}_{a}"]).values)[0]:+.2f} (t {fit(q[f].values, (q[f"{pre}_{b}"] - q[f"{pre}_{a}"]).values)[1]:.1f})' for a, b in zip(TPS[:-1], TPS[1:]))
        print(f'   {bk:7s} (β) λαθος τιμης πανω στη φορμουλα: {res}{NL}   {bk:7s} (γ) κινηση αγορας: {mv}')
    q = Q[Q.bk == 'Crown']; thr = q[f].abs().quantile(.90); top = q[q[f].abs() >= thr]; sg = np.sign(top[f])
    print(f'   TOP 10% απουσιες (|φορμουλα| ≥ {thr:.2f}, n {len(top)}): κινηση ΠΡΟΣ τη φορμουλα απο 24ω: ' + ' · '.join(f'{t} {((top[f"{pre}_{t}"] - top[f"{pre}_24ω"]) * sg).mean():+.3f}' for t in TPS[1:])
          + f' · η φορμουλα ελεγε {top[f].abs().mean():.2f}')
def settle_ou(tg, L, o, over):
    parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]; r = 0.0
    for p in parts:
        dd = (tg - p) if over else (p - tg); r += ((o - 1) if dd > 0 else (0 if dd == 0 else -1)) / len(parts)
    return r
print(f'{NL}{"=" * 140}{NL}(δ) ΠΟΝΤΑΡΙΣΜΑ προς τη μερια της φορμουλας οταν |φορμουλα| στο top 10% (ορια απο τις αλλες σεζον)')
for kind, f in (('χαντικαπ', 'g_gd'), ('συνολα', 'g_t')):
    for tp in ('24ω', '6ω'):
        for bk in ('Crown', 'Bet365'):
            q = Q[Q.bk == bk]; out = []; allp = []
            for s in SE:
                thr = q[q.season != s][f].abs().quantile(.90); z = q[(q.season == s) & (q[f].abs() >= thr)]; pn = []
                for r in z.to_dict('records'):
                    if kind == 'χαντικαπ':
                        L, oh, oa, Lc, ohc, oac = r.get(f'L_{tp}'), r.get(f'oh_{tp}'), r.get(f'oa_{tp}'), r.get('L_κλεισ.'), r.get('oh_κλεισ.'), r.get('oa_κλεισ.')
                        if L != L or Lc != Lc or r['gd'] != r['gd']: continue
                        side = 1 if r[f] > 0 else -1; ln = -L if side == 1 else L; o, oc = (oh, ohc) if side == 1 else (oa, oac)
                        mvv = ((-Lc) - (-L)) if side == 1 else (Lc - L)       # + = η γραμμη μας εγινε πιο ακριβη = κινηση υπερ μας
                        pn.append((picks.settle(r['gd'], side, ln, o), o / oc - 1 if L == Lc else np.nan, -mvv))
                    else:
                        L, oo, uu, Lc, ooc, uuc = r.get(f'OL_{tp}'), r.get(f'oo_{tp}'), r.get(f'ou_{tp}'), r.get('OL_κλεισ.'), r.get('oo_κλεισ.'), r.get('ou_κλεισ.')
                        if L != L or Lc != Lc or r['tg'] != r['tg']: continue
                        over = r[f] > 0; o, oc = (oo, ooc) if over else (uu, uuc)
                        pn.append((settle_ou(r['tg'], L, o, over), o / oc - 1 if L == Lc else np.nan, (Lc - L) if over else (L - Lc)))
                if pn: a = np.array(pn, float); out.append((s, len(a), a[:, 0].mean())); allp += pn
            A = np.array(allp, float)
            print(f'   {kind:9s} {tp:4s} {bk:7s} n {len(A):4d} · ROI {100 * A[:, 0].mean():+.1f}% · τιμη vs κλεισιμο {100 * np.nanmean(A[:, 1]):+.1f}% · κινηση γραμμης υπερ μας {np.nanmean(A[:, 2]):+.3f} · '
                  + ' · '.join(f'{s}: {100 * r:+.0f}% ({n})' for s, n, r in out) + f' · θετικες {sum(r > 0 for _, _, r in out)}/4')
