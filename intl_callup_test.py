"""
intl_callup_test.py — ΤΕΣΤ «ΑΞΙΑ ΚΛΗΣΗΣ» αντι / επιπλεον της «δυνατης ενδεκαδας 2 ετων» (V_full) στο Μοντελο 1 εθνικων (25/9/2026, εντολη Στελιου).

ΕΡΩΤΗΜΑ: αν λειπουν βασικοι (π.χ. Χααλαντ + Εντεγκααρντ εκτος κλησης), το live Μ1 δεν το βλεπει (V_full = 80ο εκατοστημοριο αξιας
ενδεκαδας 730 ημερων). Βελτιωνει το μοντελο η αξια των παικτων που ΟΝΤΩΣ ειναι διαθεσιμοι;

ΙΣΤΟΡΙΚΗ «ΚΛΗΣΗ» (δεν υπαρχουν ιστορικες λιστες κλησεων): ενωση των αποστολων ματς (11 βασικοι + ΟΛΟΣ ο παγκος FotMob, intl_squads.json)
της ομαδας στο ΙΔΙΟ διεθνες παραθυρο (ματς με διαφορα ≤6 ημερες). Ο,τι ντυθηκε σε ενα απο τα 2 ματς του παραθυρου ≈ κληθηκε.
  V_call = αθροισμα των 11 ΜΕΓΑΛΥΤΕΡΩΝ αξιων της ενωσης (αξια παικτη την ημερομηνια του ματς, intl_player_values)· ≥14 παικτες με αξια.
  V_own  = το ιδιο μονο απο την αποστολη του ΙΔΙΟΥ ματς (γνωστη ~1 ωρα πριν — δευτερευον, πιο «οψιμη» πληροφορια).
  V_full = οπως live (walk-forward 80ο εκατ. αξιας βασικης ενδεκαδας 730 ημερων, ≥3 ματς).
  Απουσιες: r = V_call / V_full (1 = ολοι εκει, 0.8 = λειπει το 20% της δυνατης ενδεκαδας).

ΠΡΟ-ΔΗΛΩΣΗ (γραφτηκε ΠΡΙΝ τρεξει, ΜΙΑ εκτελεση):
  Βαση diff = Μ1 live (H3, intl_preds_H.csv, walk-forward). Ordered logit, LOSO ανα σεζον (2021..2526), αγωνιστικα (nl/qual/tourn),
  ΙΔΙΟ δειγμα για ολες τις εκδοχες (ματς με ολα τα μεγεθη και στις 2 πλευρες).
    V0 diff · V1 diff+ln(V_full ratio) [LIVE] · K1 diff+ln(V_call ratio) [αντικατασταση] · K2 diff+ln(V_full ratio)+ln(r_h/r_a) [προσθηκη απουσιων]
    δευτερευοντα: K1o / K2o με V_own.
  ΚΡΙΤΗΡΙΟ «ΠΕΡΝΑ» (οπως intl_value2): RPS ALL < V1 ΚΑΙ καλυτερο απο V1 σε ≥4 απο τις σεζον που αξιολογουνται.
  ΑΝΑΦΟΡΑ (δεν αποφασιζει): (α) η αγορα τιμολογει τις απουσιες; υπολοιπο (Elo αγορας closing AH − Elo live Μ1) ~ ln(r_h/r_a), κλιση & t·
    (β) ROI των ιστορικων picks (τεστ 72ω, σωστα τεταρτα, Crown/SBOBET) ανα «ποιος εχει τις περισσοτερες απουσιες»:
        g = ln(r_πλευρας μας / r_αντιπαλου): g < −0.10 (η ΔΙΚΗ ΜΑΣ ομαδα χωρις βασικους) · |g| ≤ 0.10 · g > 0.10 (ο αντιπαλος χωρις βασικους).
Εξοδος: intl_callup_test_out.txt, intl_callup_test_events.csv
"""
import sys, json, math, bisect
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

PV = json.load(open('intl_player_values.json', encoding='utf-8'))
SQ = json.load(open('intl_squads.json', encoding='utf-8'))
D = pd.read_csv('intl_preds_H.csv', dtype={'season': str, 'mid': str}, parse_dates=['date']).sort_values('date').reset_index(drop=True)
D['y'] = np.where(D.gd > 0, 2, np.where(D.gd == 0, 1, 0))
H = {}
for pid, v in PV.items():
    h = sorted((d, float(x)) for d, x in (v.get('hist') or []) if d and x)
    if h:
        H[int(pid)] = ([d for d, _ in h], [x for _, x in h])
    elif v.get('mv_now'):
        H[int(pid)] = (['2026-09-19'], [float(v['mv_now'])])


def value_at(pid, dstr):
    h = H.get(pid)
    if not h:
        return None
    i = bisect.bisect_right(h[0], dstr) - 1
    return h[1][i] if i >= 0 else h[1][0]


# ---- αποστολες ανα ομαδα-ματς ----
squad = {}; team_games = {}
for r in D.itertuples():
    s = SQ.get(r.mid) or {}
    for k, tid in (('h', r.hid), ('a', r.aid)):
        t = s.get(k) or {}
        if len(t.get('st') or []) >= 8 and len(t.get('p') or {}) >= 14:
            squad[(r.mid, tid)] = dict(st=[int(x) for x in t['st']], p=[int(x) for x in t['p']])
            team_games.setdefault(int(tid), []).append((r.date, r.mid))


def top11(pids, dstr, need=14):
    vals = sorted([v for v in (value_at(p, dstr) for p in set(pids)) if v], reverse=True)
    return sum(vals[:11]) if len(vals) >= need else np.nan


def xi_value(st, dstr):
    got = [v for v in (value_at(p, dstr) for p in st) if v]
    return sum(got) * len(st) / len(got) if len(got) >= len(st) - 3 else np.nan


rows = []; hist = {}
for r in D.itertuples():
    dstr = r.date.strftime('%Y-%m-%d'); rec = dict(mid=r.mid, date=r.date, season=r.season, ctype=r.ctype, hid=r.hid, aid=r.aid, diff=r.diff, y=r.y, gd=r.gd)
    for k, tid in (('h', int(r.hid)), ('a', int(r.aid))):
        sq = squad.get((r.mid, tid))
        past = [v for (d, v) in hist.get(tid, []) if (r.date - d).days <= 730 and v > 0]
        rec[f'vf_{k}'] = float(np.percentile(past, 80)) if len(past) >= 3 else np.nan
        if sq is None:
            rec[f'vc_{k}'] = rec[f'vo_{k}'] = np.nan; continue
        win = [m for (d, m) in team_games.get(tid, []) if abs((d - r.date).days) <= 6]
        union = [p for m in win for p in squad[(m, tid)]['p']]
        rec[f'vc_{k}'] = top11(union, dstr); rec[f'vo_{k}'] = top11(sq['p'], dstr)
        xv = xi_value(sq['st'], dstr)
        if xv and xv > 0:
            hist.setdefault(tid, []).append((r.date, float(xv)))
    rows.append(rec)
E = pd.DataFrame(rows)
E['lv_full'] = np.log(E.vf_h / E.vf_a); E['lv_call'] = np.log(E.vc_h / E.vc_a); E['lv_own'] = np.log(E.vo_h / E.vo_a)
E['r_h'] = E.vc_h / E.vf_h; E['r_a'] = E.vc_a / E.vf_a; E['l_abs'] = np.log(E.r_h / E.r_a)
E['l_abs_own'] = np.log((E.vo_h / E.vf_h) / (E.vo_a / E.vf_a))
C = E[E.ctype.isin(['nl', 'qual', 'tourn'])].replace([np.inf, -np.inf], np.nan).dropna(subset=['diff', 'lv_full', 'lv_call', 'lv_own', 'l_abs', 'l_abs_own']).copy()
P_('ΤΕΣΤ ΑΞΙΑΣ ΚΛΗΣΗΣ — Μοντελο 1 εθνικων (H3) · ordered logit LOSO · αγωνιστικα ματς')
P_(f'δειγμα: {len(C)} ματς με ολα τα μεγεθη (απο {int(E.ctype.isin(["nl", "qual", "tourn"]).sum())} αγωνιστικα)')
P_('απουσιες r = V_call/V_full: μεσος %.2f · p10 %.2f · p50 %.2f · p90 %.2f · ματς με r<0.80 σε μια πλευρα: %d'
   % (pd.concat([C.r_h, C.r_a]).mean(), pd.concat([C.r_h, C.r_a]).quantile(.1), pd.concat([C.r_h, C.r_a]).quantile(.5),
      pd.concat([C.r_h, C.r_a]).quantile(.9), int(((C.r_h < .8) | (C.r_a < .8)).sum())))
FEATS = {'V0 diff': ['diff'], 'V1 +V_full [LIVE]': ['diff', 'lv_full'], 'K1 +V_call (αντι V_full)': ['diff', 'lv_call'],
         'K2 +V_full+απουσιες': ['diff', 'lv_full', 'l_abs'], 'K1o +V_own': ['diff', 'lv_own'], 'K2o +V_full+απουσιες_own': ['diff', 'lv_full', 'l_abs_own']}
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
T = pd.DataFrame(T_).set_index('variant'); pd.set_option('display.width', 220)
P_('\n' + T.to_string())
ref = T.loc['V1 +V_full [LIVE]']
P_('\nΚΡΙΤΗΡΙΟ (vs V1 live): RPS ALL μικροτερο ΚΑΙ καλυτερο σε ≥4 σεζον')
for v in T.index:
    if v.startswith(('V0', 'V1')):
        continue
    better = sum(1 for s in SEAS if pd.notna(T.loc[v, s]) and T.loc[v, s] < ref[s]); nev = sum(pd.notna(T.loc[v, s]) for s in SEAS)
    P_(f'  {v:28s}: ΔRPS {T.loc[v, "ALL"] - ref["ALL"]:+.5f} · καλυτερο σε {better}/{nev} · {"ΠΕΡΝΑ" if (T.loc[v, "ALL"] < ref["ALL"] and better >= 4) else "—"}')
P_('\nσυντελεστες (ολο το δειγμα), σε Elo ανα διπλασιασμο:')
for name, b in coefs.items():
    if len(b) > 1:
        P_(f'  {name:28s}: ' + ', '.join(f'{f}: {b[i] / b[0] * np.log(2):+.0f}' for i, f in enumerate(FEATS[name]) if i > 0))

# ---- (α) η αγορα τιμολογει τις απουσιες; ----
CL = json.load(open('intl_close_hist.json', encoding='utf-8'))


def sup_from_line(line, oh, oa, T=2.6):
    kk = 1 / oh + 1 / oa; tgt = (1 / oh) / kk; lo, hi = -4.0, 4.0
    for _ in range(30):
        mid = (lo + hi) / 2; lh_ = max((T + mid) / 2, 0.15); la_ = max((T - mid) / 2, 0.15)
        pw, pp_ = picks.p_cover(picks.gd_dist(lh_, la_), 1, line); p_eff = pw / max(1 - pp_, 1e-9)
        lo, hi = (mid, hi) if p_eff < tgt else (lo, mid)
    return (lo + hi) / 2


VF_ELO = json.load(open('intl_team_vfull.json', encoding='utf-8'))['elo_per_ln']
A = C[C.mid.isin(CL.keys())].copy()
A['d_mkt'] = [sup_from_line(float(CL[m]['ah_line']), float(CL[m]['ah_h']), float(CL[m]['ah_a'])) / 0.0049 for m in A.mid]
A['res'] = A.d_mkt - (A['diff'] + VF_ELO * A.lv_full)
P_(f'\n(α) ΑΓΟΡΑ vs ΑΠΟΥΣΙΕΣ — {len(A)} ματς με closing AH Crown: υπολοιπο (Elo αγορας − Elo Μ1 live) ~ ln(r_h/r_a)')
for lab, col in (('απουσιες παραθυρου (κληση)', 'l_abs'), ('απουσιες ιδιου ματς', 'l_abs_own')):
    x = A[col].values; y = A.res.values; xm = x - x.mean()
    b = float(np.sum(xm * (y - y.mean())) / np.sum(xm ** 2)); e = y - y.mean() - b * xm
    se = math.sqrt(np.sum(e ** 2) / (len(x) - 2) / np.sum(xm ** 2))
    P_(f'  {lab:28s}: κλιση {b * math.log(2):+.0f} Elo ανα διπλασιασμο (t {b / se:+.1f}) · για r 0.80 vs 1.00: {b * math.log(0.8):+.0f} Elo')
big = A[(A.r_h < 0.85) | (A.r_a < 0.85)]
P_(f'  ματς με r<0.85 σε μια πλευρα: {len(big)} · μεσο υπολοιπο προς την πλευρα με τις απουσιες: '
   f'{np.mean([(-1 if rh < ra else 1) * rs for rh, ra, rs in zip(big.r_h, big.r_a, big.res)]):+.0f} Elo (αρνητικο = η αγορα τη βαζει ΧΑΜΗΛΟΤΕΡΑ απο το Μ1)')

# ---- (β) ROI ιστορικων picks ανα απουσιες ----
B = pd.read_csv('intl_window_test_proper_ahproper_bets.csv', dtype={'mid': str, 'season': str})
B = B[(B.win == '72ω') & B.rule.str.startswith('AH')].merge(E[['mid', 'l_abs']], on='mid', how='inner').dropna(subset=['l_abs'])
B['g'] = np.where(B.side == 1, B.l_abs, -B.l_abs)
B['ομαδα'] = np.where(B.g < -0.10, 'η ΔΙΚΗ μας χωρις βασικους', np.where(B.g > 0.10, 'ο ΑΝΤΙΠΑΛΟΣ χωρις βασικους', 'παρομοια'))
P_(f'\n(β) ROI ιστορικων handicap picks (72ω, σωστα τεταρτα) ανα απουσιες · g = ln(r_δικη μας / r_αντιπαλου)')
for mdl in ('M1', 'M2', 'M3'):
    for bk in ('Crown', 'SBOBET'):
        s = B[(B.model == mdl) & (B.book == bk)]
        P_(f'  {mdl} {bk:6s}: ' + ' · '.join(f"{g}: n{len(x)} {x.pnl.mean() * 100:+.1f}%" for g, x in s.groupby('ομαδα')))
E.to_csv('intl_callup_test_events.csv', index=False)
open('intl_callup_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
