"""
intl_regulars_test.py — ΤΕΣΤ «ΑΠΟΥΣΙΑ ΒΑΣΙΚΩΝ ΠΕΡΑ ΑΠΟ ΤΗΝ ΑΞΙΑ ΤΟΥΣ» (25/9/2026, εντολη Στελιου — παραδειγμα Ουγγαρια: Sallai 38/39 βασικος,
Varga 20/22, αλλα 9.5 / 2.1 εκατ. διπλα στον Szoboszlai 84 → η αξια κλησης μετραει την απουσια τους ~3 Elo).

ΟΡΙΣΜΟΙ (walk-forward, μονο πληροφορια ΠΡΙΝ το ματς):
  βασικος = παικτης στην αρχικη 11αδα σε ≥50% των ματς της ομαδας τις 730 ημερες πριν (≥4 ματς με ενδεκαδα)· βαρος = ποσοστο βασικου (0.5..1).
  απουσιες A = Σ βαρων των βασικων που ΔΕΝ ειναι στην αποστολη του ματς (11 + παγκος FotMob) — «αυτοι που επροκειτο να παιξουν» (ιδιο με V_own).
  εκδοχη «πυρηνας»: μονο βασικοι ≥75%.
ΠΡΟ-ΔΗΛΩΣΗ (γραφτηκε ΠΡΙΝ τρεξει, ΜΙΑ εκτελεση):
  Βαση = LIVE (Μ1 H3 diff + ln(V_own ratio)) — ιδιο δειγμα με intl_callup_test (αγωνιστικα, ολα τα μεγεθη διαθεσιμα).
  R1 = LIVE + (A_h − A_a) · R2 = LIVE + (A_core_h − A_core_a). Ordered logit, LOSO ανα σεζον.
  ΚΡΙΤΗΡΙΟ: RPS ALL < LIVE ΚΑΙ καλυτερο σε ≥4 απο τις σεζον. Συντελεστης = Elo ανα βασικο που λειπει ΠΕΡΑ απο την αξια του.
  ΑΝΑΦΟΡΑ: (α) η αγορα: υπολοιπο (Elo closing − Elo LIVE) ~ (A_h − A_a)· (β) ROI ιστορικων handicap picks (72ω) ανα «ποιος εχει τις περισσοτερες απουσιες βασικων».
Εξοδος: intl_regulars_test_out.txt
"""
import sys, json, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0, '.')
import picks
_src = open('intl_rating.py', encoding='utf-8').read(); _ns = {'np': np}
exec(_src[_src.index('def sig(x):'):_src.index("EVAL_SEASONS = ")], _ns)
sig, nelder_mead, rps, logloss = _ns['sig'], _ns['nelder_mead'], _ns['rps'], _ns['logloss']
_v = open('intl_value.py', encoding='utf-8').read(); _n2 = {'np': np, 'sig': sig, 'nelder_mead': nelder_mead}
exec(_v[_v.index('def fit_ol_multi'):_v.index('FEATS = ')], _n2)
fit_ol_multi, probs_multi = _n2['fit_ol_multi'], _n2['probs_multi']
out = []
def P_(s=''):
    print(s, flush=True); out.append(str(s))

SQ = json.load(open('intl_squads.json', encoding='utf-8'))
E = pd.read_csv('intl_callup_test_events.csv', dtype={'mid': str, 'season': str}, parse_dates=['date']).sort_values('date').reset_index(drop=True)
# ---- ιστορικο ενδεκαδων ανα ομαδα (ολα τα ματς με ενδεκαδα, και φιλικα) ----
games = {}
for r in E.itertuples():
    s = SQ.get(r.mid) or {}
    for k, tid in (('h', int(r.hid)), ('a', int(r.aid))):
        t = s.get(k) or {}
        if len(t.get('st') or []) >= 8 and len(t.get('p') or {}) >= 14:
            games.setdefault(tid, []).append((r.date, r.mid, set(int(x) for x in t['st']), set(int(x) for x in t['p'])))


def absences(tid, date, mid):
    g = games.get(tid, []); past = [x for x in g if x[0] < date and (date - x[0]).days <= 730]
    cur = [x for x in g if x[1] == mid]
    if len(past) < 4 or not cur:
        return np.nan, np.nan, np.nan
    n = len(past); cnt = {}
    for _, _, st, _ in past:
        for p in st:
            cnt[p] = cnt.get(p, 0) + 1
    dressed = cur[0][3]
    reg = {p: c / n for p, c in cnt.items() if c / n >= 0.5}
    a_all = sum(w for p, w in reg.items() if p not in dressed)
    a_core = sum(w for p, w in reg.items() if w >= 0.75 and p not in dressed)
    return a_all, a_core, len(reg)


for k, col in (('h', 'hid'), ('a', 'aid')):
    res = [absences(int(t), d, m) for t, d, m in zip(E[col], E.date, E.mid)]
    E[f'A_{k}'] = [x[0] for x in res]; E[f'Ac_{k}'] = [x[1] for x in res]; E[f'nreg_{k}'] = [x[2] for x in res]
E['dA'] = E.A_h - E.A_a; E['dAc'] = E.Ac_h - E.Ac_a
C = E[E.ctype.isin(['nl', 'qual', 'tourn'])].replace([np.inf, -np.inf], np.nan).dropna(subset=['diff', 'lv_own', 'dA', 'dAc']).copy()
P_('ΤΕΣΤ ΑΠΟΥΣΙΑΣ ΒΑΣΙΚΩΝ ΠΕΡΑ ΑΠΟ ΤΗΝ ΑΞΙΑ — βαση LIVE (Μ1 H3 + αξια κλησης/αποστολης) · ordered logit LOSO · αγωνιστικα')
Aall = pd.concat([C.A_h, C.A_a])
P_(f'δειγμα {len(C)} ματς · βασικοι ανα ομαδα: μεσος {pd.concat([C.nreg_h, C.nreg_a]).mean():.1f} · απουσιες βασικων ανα ομαδα-ματς: '
   f'μεσος {Aall.mean():.2f} · 0: {(Aall < 0.01).mean() * 100:.0f}% · ≥2: {(Aall >= 2).mean() * 100:.0f}% · ≥3: {(Aall >= 3).mean() * 100:.0f}%')
FEATS = {'LIVE (diff + αξια αποστολης)': ['diff', 'lv_own'], 'R1 LIVE + απουσιες βασικων': ['diff', 'lv_own', 'dA'],
         'R2 LIVE + απουσιες πυρηνα (≥75%)': ['diff', 'lv_own', 'dAc'], '(ref) diff + απουσιες, χωρις αξια': ['diff', 'dA']}
SEAS = ['2021', '2122', '2223', '2324', '2425', '2526']
T_ = []; coefs = {}
for name, fs in FEATS.items():
    row = dict(variant=name); allP = []; ally = []
    for s in SEAS:
        tr = C[C.season != s]; te = C[C.season == s]
        if len(te) < 20:
            row[s] = np.nan; continue
        b, c1, c2 = fit_ol_multi(tr[fs].values.astype(float), tr['y'].values)
        Pm = probs_multi(te[fs].values.astype(float), b, c1, c2)
        row[s] = round(rps(Pm, te['y'].values), 4); allP.append(Pm); ally.append(te['y'].values)
    Pm = np.vstack(allP); yy = np.concatenate(ally)
    row['ALL'] = round(rps(Pm, yy), 5); row['logloss'] = round(logloss(Pm, yy), 4); row['n'] = len(yy)
    coefs[name] = fit_ol_multi(C[fs].values.astype(float), C['y'].values)[0]
    T_.append(row)
T = pd.DataFrame(T_).set_index('variant'); pd.set_option('display.width', 230)
P_('\n' + T.to_string())
ref = T.iloc[0]
P_('\nΚΡΙΤΗΡΙΟ (vs LIVE): RPS ALL μικροτερο ΚΑΙ καλυτερο σε ≥4 σεζον')
for v in list(T.index)[1:3]:
    better = sum(1 for s in SEAS if pd.notna(T.loc[v, s]) and T.loc[v, s] < ref[s]); nev = sum(pd.notna(T.loc[v, s]) for s in SEAS)
    P_(f'  {v:34s}: ΔRPS {T.loc[v, "ALL"] - ref["ALL"]:+.5f} · καλυτερο σε {better}/{nev} · {"ΠΕΡΝΑ" if (T.loc[v, "ALL"] < ref["ALL"] and better >= 4) else "—"}')
P_('\nσυντελεστες (ολο το δειγμα): αξια σε Elo ανα διπλασιασμο · απουσιες σε Elo ανα ΒΑΣΙΚΟ που λειπει (αρνητικο = χανει η ομαδα με τις απουσιες)')
for name, b in coefs.items():
    fs = FEATS[name]; parts = []
    for i, f in enumerate(fs):
        if i == 0:
            continue
        parts.append(f'{f}: {b[i] / b[0] * (np.log(2) if f.startswith("lv") else 1):+.1f}')
    P_(f'  {name:34s}: ' + ', '.join(parts))

# ---- (α) αγορα ----
CL = json.load(open('intl_close_hist.json', encoding='utf-8'))
CFG = json.load(open('intl_vcall_config.json', encoding='utf-8'))


def sup_from_line(line, oh, oa, T=2.6):
    kk = 1 / oh + 1 / oa; tgt = (1 / oh) / kk; lo, hi = -4.0, 4.0
    for _ in range(30):
        mid = (lo + hi) / 2; lh_ = max((T + mid) / 2, 0.15); la_ = max((T - mid) / 2, 0.15)
        pw, pp_ = picks.p_cover(picks.gd_dist(lh_, la_), 1, line); p_eff = pw / max(1 - pp_, 1e-9)
        lo, hi = (mid, hi) if p_eff < tgt else (lo, mid)
    return (lo + hi) / 2


A = C[C.mid.isin(CL.keys())].copy()
A['d_mkt'] = [sup_from_line(float(CL[m]['ah_line']), float(CL[m]['ah_h']), float(CL[m]['ah_a'])) / 0.0049 for m in A.mid]
A['res'] = A.d_mkt - (A['diff'] + CFG['elo_per_ln'] * A.lv_own)
P_(f'\n(α) ΑΓΟΡΑ — {len(A)} ματς με closing AH: υπολοιπο (Elo αγορας − Elo LIVE) ~ (απουσιες βασικων γηπ − φιλοξ)')
for lab, col in (('ολοι οι βασικοι', 'dA'), ('πυρηνας ≥75%', 'dAc')):
    x = A[col].values; y = A.res.values; xm = x - x.mean()
    b = float(np.sum(xm * (y - y.mean())) / np.sum(xm ** 2)); e = y - y.mean() - b * xm
    se = math.sqrt(np.sum(e ** 2) / (len(x) - 2) / np.sum(xm ** 2))
    P_(f'  {lab:18s}: η αγορα αφαιρει {b:+.1f} Elo ανα βασικο που λειπει ΠΕΡΑ απο το LIVE (t {b / se:+.1f})')

# ---- (β) ROI ιστορικων picks ----
B = pd.read_csv('intl_window_test_proper_ahproper_bets.csv', dtype={'mid': str, 'season': str})
B = B[(B.win == '72ω') & B.rule.str.startswith('AH')].merge(E[['mid', 'dA']], on='mid', how='inner').dropna(subset=['dA'])
B['g'] = np.where(B.side == 1, B.dA, -B.dA)          # >0: η ΔΙΚΗ μας ομαδα εχει περισσοτερους βασικους εκτος
B['ομαδα'] = np.where(B.g >= 1, 'η ΔΙΚΗ μας χωρις ≥1 βασικο παραπανω', np.where(B.g <= -1, 'ο ΑΝΤΙΠΑΛΟΣ χωρις ≥1 βασικο παραπανω', 'παρομοια'))
P_('\n(β) ROI ιστορικων handicap picks (72ω, σωστα τεταρτα) ανα διαφορα απουσιων βασικων')
for mdl in ('M1', 'M2', 'M3'):
    for bk in ('Crown', 'SBOBET'):
        s = B[(B.model == mdl) & (B.book == bk)]
        P_(f'  {mdl} {bk:6s}: ' + ' · '.join(f"{g}: n{len(x)} {x.pnl.mean() * 100:+.1f}%" for g, x in s.groupby('ομαδα')))
E[['mid', 'A_h', 'A_a', 'Ac_h', 'Ac_a', 'nreg_h', 'nreg_a']].to_csv('intl_regulars_test_events.csv', index=False)
open('intl_regulars_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
