"""
intl_importance_test.py — ΣΗΜΑΣΙΑ ΠΑΙΚΤΗ ΠΕΡΑ ΑΠΟ ΤΗΝ ΑΞΙΑ (25/9/2026, Στελιος: «ο Xhaka ειναι ο αρχηγος και ισως ο πιο σημαντικος παικτης· με μονο
την αξια δεν θα τον νιωσει το μοντελο — τεστ με διαφορους τροπους: συμμετοχες με την εθνικη, FotMob rating, οτιδηποτε»).

ΒΑΣΗ = LIVE (Μ1 H3 diff + αξια αποστολης ln(V_own), intl_callup_test_events). Δειγμα: αγωνιστικα 2021..2526 (ιδιο με intl_regulars_test).
ΣΗΜΑΣΙΑ ΠΑΙΚΤΗ (walk-forward, ΜΟΝΟ ματς με την εθνικη, πριν το ματς· παικτες με ≥2 εκκινησεις στις 730 ημερες):
  W0 βασικος   = ποσοστο εκκινησεων (αναφορα — το intl_regulars_test)
  W1 λεπτα     = λεπτα / (90 × ματς)
  W2 συμμετοχες = συνολικες συμμετοχες με την εθνικη (ΟΛΟ το ιστορικο, cap 80) / 80
  W3 rating    = ποσοστο εκκινησεων × max(μεσο FotMob rating − 6.0, 0.2)   (rating 2 ετων, ≥3 ματς με rating)
  W4 αρχηγος   = ποσοστο εκκινησεων × (1 + 2·ποσοστο ως αρχηγος)
  W5 συνδυασμος = λεπτα × max(rating − 6.0, 0.2) × (1 + 2·αρχηγος)
  Απουσια ομαδας A_w = Σ w των παικτων που ΔΕΝ ειναι στην αποστολη του ματς / Σ w ολων · χαρακτηριστικο dA = A_w(γηπ) − A_w(φιλοξ).
ΠΡΟ-ΔΗΛΩΣΗ (ΠΡΙΝ τρεξει, ΜΙΑ εκτελεση): ordered logit LOSO ανα σεζον· ΠΕΡΝΑ ενας τροπος αν RPS < LIVE συνολικα ΚΑΙ σε ≥4/6 σεζον.
  Αναφορα: συντελεστης (Elo για «λειπει το 10% της σημασιας»), αγορα (closing − LIVE ~ dA, t), ROI ιστορικων handicap picks,
  και η περιπτωση Ελβετιας (Xhaka + Embolo): ποσο της σημασιας λειπει με καθε τροπο.
Εξοδος: intl_importance_test_out.txt
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
RT = json.load(open('intl_player_ratings.json', encoding='utf-8'))
NM = json.load(open('intl_player_names.json', encoding='utf-8'))
E = pd.read_csv('intl_callup_test_events.csv', dtype={'mid': str, 'season': str}, parse_dates=['date']).sort_values('date').reset_index(drop=True)
P_(f'ratings FotMob: {len(RT)} ματς · ενδεκαδες: {len(SQ)}')

# ---- ιστορικο ανα ομαδα: (date, mid, starters, minutes{pid}, rating{pid}, captain{pid}) ----
games = {}; caps_hist = {}
for r in E.itertuples():
    s = SQ.get(r.mid) or {}; rt = RT.get(r.mid) or {}
    for k, tid in (('h', int(r.hid)), ('a', int(r.aid))):
        t = s.get(k) or {}
        if len(t.get('st') or []) < 8 or len(t.get('p') or {}) < 14:
            continue
        rr = rt.get(k) or {}
        games.setdefault(tid, []).append(dict(date=r.date, mid=r.mid, st=set(int(x) for x in t['st']), mins={int(p): int(v or 0) for p, v in t['p'].items()},
                                              dressed=set(int(p) for p in t['p']), rating={int(p): v[0] for p, v in rr.items() if v[0]}, cap={int(p) for p, v in rr.items() if v[1]}))


def weights(tid, date, mid):
    g = games.get(tid, []); past = [x for x in g if x['date'] < date and (date - x['date']).days <= 730]; allp = [x for x in g if x['date'] < date]
    cur = [x for x in g if x['mid'] == mid]
    if len(past) < 4 or not cur:
        return None
    n = len(past); starts = {}; mins = {}; rts = {}; capc = {}
    for x in past:
        for p in x['st']: starts[p] = starts.get(p, 0) + 1
        for p, m in x['mins'].items(): mins[p] = mins.get(p, 0) + m
        for p, v in x['rating'].items(): rts.setdefault(p, []).append(v)
        for p in x['cap']: capc[p] = capc.get(p, 0) + 1
    caps = {}
    for x in allp:
        for p, m in x['mins'].items():
            if m > 0: caps[p] = caps.get(p, 0) + 1
    W = {k: {} for k in ('W0', 'W1', 'W2', 'W3', 'W4', 'W5')}
    for p, sc in starts.items():
        if sc < 2: continue
        sh = sc / n; mn = mins.get(p, 0) / (90 * n); rl = rts.get(p, []); rq = max(np.mean(rl) - 6.0, 0.2) if len(rl) >= 3 else 0.6; cs = capc.get(p, 0) / n
        W['W0'][p] = sh; W['W1'][p] = mn; W['W2'][p] = min(caps.get(p, 0), 80) / 80; W['W3'][p] = sh * rq; W['W4'][p] = sh * (1 + 2 * cs); W['W5'][p] = mn * rq * (1 + 2 * cs)
    dressed = cur[0]['dressed']
    return {k: (sum(w for p, w in v.items() if p not in dressed) / sum(v.values()) if v and sum(v.values()) > 0 else np.nan) for k, v in W.items()}, W, dressed


feats = {k: ([], []) for k in ('W0', 'W1', 'W2', 'W3', 'W4', 'W5')}
for r in E.itertuples():
    a, b = weights(int(r.hid), r.date, r.mid), weights(int(r.aid), r.date, r.mid)
    for k in feats:
        feats[k][0].append(a[0][k] if a else np.nan); feats[k][1].append(b[0][k] if b else np.nan)
for k, (h, a) in feats.items():
    E[f'A_{k}_h'] = h; E[f'A_{k}_a'] = a; E[f'd{k}'] = E[f'A_{k}_h'] - E[f'A_{k}_a']
LAB = {'W0': 'βασικος (αναφορα)', 'W1': 'λεπτα', 'W2': 'συμμετοχες εθνικης', 'W3': 'FotMob rating', 'W4': 'αρχηγος', 'W5': 'συνδυασμος'}
C = E[E.ctype.isin(['nl', 'qual', 'tourn'])].replace([np.inf, -np.inf], np.nan).dropna(subset=['diff', 'lv_own'] + [f'd{k}' for k in feats]).copy()
P_(f'δειγμα: {len(C)} αγωνιστικα ματς · μεση απουσια σημασιας ανα ομαδα: ' + ' · '.join(f"{LAB[k]} {pd.concat([C[f'A_{k}_h'], C[f'A_{k}_a']]).mean() * 100:.0f}%" for k in feats))
SEAS = ['2021', '2122', '2223', '2324', '2425', '2526']
FEATS = {'LIVE (diff + αξια αποστολης)': ['diff', 'lv_own']} | {f'+ {LAB[k]}': ['diff', 'lv_own', f'd{k}'] for k in feats}
T_ = []; coefs = {}
for name, fs in FEATS.items():
    row = dict(variant=name); allP = []; ally = []
    for s in SEAS:
        tr = C[C.season != s]; te = C[C.season == s]
        if len(te) < 20:
            row[s] = np.nan; continue
        b, c1, c2 = fit_ol_multi(tr[fs].values.astype(float), tr['y'].values)
        Pm = probs_multi(te[fs].values.astype(float), b, c1, c2); row[s] = round(rps(Pm, te['y'].values), 4); allP.append(Pm); ally.append(te['y'].values)
    Pm = np.vstack(allP); yy = np.concatenate(ally); row['ALL'] = round(rps(Pm, yy), 5); row['n'] = len(yy)
    coefs[name] = fit_ol_multi(C[fs].values.astype(float), C['y'].values)[0]; T_.append(row)
T = pd.DataFrame(T_).set_index('variant'); pd.set_option('display.width', 230)
P_('\n' + T.to_string())
ref = T.iloc[0]; passed = []
P_('\nΚΡΙΤΗΡΙΟ (vs LIVE): RPS μικροτερο ΚΑΙ καλυτερο σε ≥4/6 σεζον · συντελεστης = Elo οταν λειπει το 10% της σημασιας της ομαδας')
for v in T.index[1:]:
    better = sum(1 for s in SEAS if pd.notna(T.loc[v, s]) and T.loc[v, s] < ref[s]); ok = T.loc[v, 'ALL'] < ref['ALL'] and better >= 4
    b = coefs[v]; elo10 = b[2] / b[0] * 0.10
    P_(f'  {v:28s}: ΔRPS {T.loc[v, "ALL"] - ref["ALL"]:+.5f} · καλυτερο σε {better}/6 · {elo10:+.1f} Elo ανα 10% απουσια · {"ΠΕΡΝΑ" if ok else "—"}')
    if ok: passed.append(v)
# ---- αγορα ----
CL = json.load(open('intl_close_hist.json', encoding='utf-8')); CFG = json.load(open('intl_vcall_config.json', encoding='utf-8'))
def sup(line, oh, oa, T=2.6):
    kk = 1 / oh + 1 / oa; tgt = (1 / oh) / kk; lo, hi = -4.0, 4.0
    for _ in range(30):
        mid_ = (lo + hi) / 2; pw, pp_ = picks.p_cover(picks.gd_dist(max((T + mid_) / 2, .15), max((T - mid_) / 2, .15)), 1, line); pe = pw / max(1 - pp_, 1e-9)
        lo, hi = (mid_, hi) if pe < tgt else (lo, mid_)
    return (lo + hi) / 2
A = C[C.mid.isin(CL.keys())].copy()
A['res'] = [sup(float(CL[m]['ah_line']), float(CL[m]['ah_h']), float(CL[m]['ah_a'])) / 0.0049 for m in A.mid]; A['res'] -= A['diff'] + CFG['elo_per_ln'] * A.lv_own
P_(f'\n(α) ΑΓΟΡΑ ({len(A)} ματς με closing): η αγορα αφαιρει επιπλεον (Elo ανα 10% απουσια σημασιας, περα απο LIVE)')
for k in feats:
    x = A[f'd{k}'].values; y = A.res.values; xm = x - x.mean(); bb = float(np.sum(xm * (y - y.mean())) / np.sum(xm ** 2)); e = y - y.mean() - bb * xm
    se = math.sqrt(np.sum(e ** 2) / (len(x) - 2) / np.sum(xm ** 2)); P_(f'  {LAB[k]:20s}: {bb * 0.1:+.1f} Elo (t {bb / se:+.1f})')
# ---- ROI ----
Bt = pd.read_csv('intl_window_test_proper_ahproper_bets.csv', dtype={'mid': str, 'season': str})
Bt = Bt[(Bt.win == '72ω') & Bt.rule.str.startswith('AH')].merge(E[['mid'] + [f'd{k}' for k in feats]], on='mid')
P_('\n(β) ROI ιστορικων handicap picks (72ω, μεσος Crown/SBOBET, ολα τα μοντελα) ανα απουσια σημασιας (διαφορα ≥10%)')
for k in feats:
    g = np.where(Bt.side == 1, Bt[f'd{k}'], -Bt[f'd{k}'])
    grp = np.where(g >= 0.10, 'η ΔΙΚΗ μας χωρις σημαντικους', np.where(g <= -0.10, 'ο ΑΝΤΙΠΑΛΟΣ χωρις σημαντικους', 'παρομοια'))
    cells = []
    for lab_ in ('η ΔΙΚΗ μας χωρις σημαντικους', 'παρομοια', 'ο ΑΝΤΙΠΑΛΟΣ χωρις σημαντικους'):
        x = Bt[grp == lab_]; c, s_ = x[x.book == 'Crown'], x[x.book == 'SBOBET']
        cells.append(f'{lab_}: {(c.pnl.mean() + s_.pnl.mean()) / 2 * 100:+.1f}% (n~{(len(c) + len(s_)) // 2})')
    P_(f'  {LAB[k]:20s}: ' + ' · '.join(cells))
# ---- Ελβετια: Xhaka + Embolo ----
sw = E[(E.hn == 'Switzerland') | (E.an == 'Switzerland')] if 'hn' in E else None
M = pd.read_csv('intl_matches.csv', dtype={'mid': str}); swid = int(M[M.hn == 'Switzerland'].hid.iloc[0])
g = games.get(swid, []); last = max(x['date'] for x in g); now = last + pd.Timedelta(days=1)
past = [x for x in g if (now - x['date']).days <= 730]
res = weights(swid, now + pd.Timedelta(days=0), None)
# «εικονικο» ματς: αποστολη = ολοι οι παικτες των 2 ετων ΕΚΤΟΣ Xhaka/Embolo
def pid_of(name):
    return [int(p) for p, n in NM.items() if n and name.lower() in n.lower()]
xh, emb = pid_of('Granit Xhaka'), pid_of('Breel Embolo')
games[swid].append(dict(date=now, mid='SIM', st=set(), mins={}, dressed=set(p for x in past for p in x['dressed']) - set(xh) - set(emb), rating={}, cap=set()))
r_ = weights(swid, now, 'SIM')
if r_:
    fr, W, _ = r_
    P_('\nΕΛΒΕΤΙΑ χωρις Xhaka + Embolo — ποσο της σημασιας της ομαδας λειπει με καθε τροπο:')
    for k in feats:
        wx = sum(W[k].get(p, 0) for p in xh) / sum(W[k].values()) * 100; we = sum(W[k].get(p, 0) for p in emb) / sum(W[k].values()) * 100
        rank = sorted(W[k].items(), key=lambda kv: -kv[1]); rx = next((i + 1 for i, (p, _) in enumerate(rank) if p in xh), None)
        P_(f'  {LAB[k]:20s}: λειπει {fr[k] * 100:4.1f}% (Xhaka {wx:.1f}% — #{rx} στην ομαδα · Embolo {we:.1f}%)')
P_('\nΑΠΟΤΕΛΕΣΜΑ: ' + ('ΠΕΡΝΟΥΝ: ' + ', '.join(passed) if passed else 'ΚΑΝΕΝΑΣ τροπος δεν περνα'))
open('intl_importance_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
