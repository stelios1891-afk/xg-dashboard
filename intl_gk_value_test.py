"""
intl_gk_value_test.py — ΤΕΣΤ «GK-aware» αξιας εθνικης (27/9/2026). Νεο script, βαση intl_callup_test.py (ΔΕΝ γραφει config/events).
V (live) = αθροισμα 11 μεγαλυτερων αξιων αποστολης χωρις θεσεις -> 2 ακριβοι τερματοφυλακες μετρανε και οι δυο.
GK-aware V = ΕΝΑΣ τερματοφυλακας + 10 πιο ακριβοι ΜΗ-τερματοφυλακες.
  Κανονας «most-starts» (K1g, fallback του K1og): μεταξυ των τερματοφυλακων της δεξαμενης (με αξια), αυτος με τις ΠΕΡΙΣΣΟΤΕΡΕΣ
  βασικες συμμετοχες (intl_squads st) με την ιδια εθνικη σε ματς ΑΥΣΤΗΡΑ πριν την ημερομηνια του ματς και εντος 730 ημερων·
  ισοπαλια -> πιο προσφατη βασικη συμμετοχη· κανεις με συμμετοχες -> ο πιο ακριβος.
  Κανονας «last» (K1g-last, K1og-last — 2η προσθηκη συντονιστη πριν την εκτελεση): ο GK που ξεκινησε το ΠΙΟ ΠΡΟΣΦΑΤΟ αγωνιστικο
  ματς (αυστηρα πριν, 730 ημερες) αν ειναι στη δεξαμενη· αλλιως κανονας rec· κανεις -> ο πιο ακριβος.
  Κανονας «rec» (K1g-rec, K1og-rec — προσθηκη συντονιστη πριν την εκτελεση): score = Σ w_comp × 0.5^(ημερες_πριν/180) πανω στις βασικες
  συμμετοχες (αυστηρα πριν, 730 ημερες), w_comp = 1.0 αγωνιστικα (nl/qual/tourn), 0.5 φιλικα· max score· κανεις -> ο πιο ακριβος.
  K1og / K1og-rec: τερματοφυλακας = αυτος που ΟΝΤΩΣ ξεκινησε το ματς (αν ειναι στα st με αξια), αλλιως ο αντιστοιχος κανονας.
  Αν η δεξαμενη δεν εχει κανεναν τερματοφυλακα με αξια -> fallback σε απλο top-11. Ελαχιστο 14 παικτες με αξια (οπως harness).
Τερματοφυλακας = pos.lower() in {'keeper','goalkeeper'}.
ΠΡΟ-ΔΗΛΩΣΗ: GK εκδοχη ΠΕΡΝΑ αν RPS ALL < RPS της αντιστοιχης μη-GK ΚΑΙ καλυτερη σε >=4 απο 6 σεζον. ΜΙΑ εκτελεση.
"""
import sys, json, bisect
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0, '.')
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
M = pd.read_csv('intl_matches.csv', dtype={'mid': str}, usecols=['mid', 'date', 'hid', 'aid', 'hn', 'an', 'ctype'], parse_dates=['date'])
NAME = {}
for r in M.itertuples():
    NAME[int(r.hid)] = r.hn; NAME[int(r.aid)] = r.an
H = {}
for pid, v in PV.items():
    h = sorted((d, float(x)) for d, x in (v.get('hist') or []) if d and x)
    if h:
        H[int(pid)] = ([d for d, _ in h], [x for _, x in h])
    elif v.get('mv_now'):
        H[int(pid)] = (['2026-09-19'], [float(v['mv_now'])])
GK = {int(p) for p, v in PV.items() if str(v.get('pos') or '').strip().lower() in ('keeper', 'goalkeeper')}
PNAME = {int(p): v.get('name') for p, v in PV.items()}


def value_at(pid, dstr):
    h = H.get(pid)
    if not h:
        return None
    i = bisect.bisect_right(h[0], dstr) - 1
    return h[1][i] if i >= 0 else h[1][0]


# ---- ιστορικο βασικων ανα ομαδα (ολα τα ματς του intl_matches με αποστολη) ----
starts = {}   # tid -> list of (date, set(st), w_comp)
for r in M.itertuples():
    s = SQ.get(r.mid) or {}
    w = 1.0 if r.ctype in ('nl', 'qual', 'tourn') else 0.5
    for k, tid in (('h', int(r.hid)), ('a', int(r.aid))):
        st = (s.get(k) or {}).get('st') or []
        if st:
            starts.setdefault(tid, []).append((r.date, {int(x) for x in st}, w))
for tid in starts:
    starts[tid].sort(key=lambda x: x[0])


def gk_starts(tid, pid, date):
    n = 0; last = None; sc = 0.0
    for d, st, w in starts.get(tid, []):
        if d >= date:
            break
        days = (date - d).days
        if days <= 730 and pid in st:
            n += 1; last = d; sc += w * 0.5 ** (days / 180.0)
    return n, last, sc


def pick_gk(tid, date, cands, rule):
    """cands: dict pid->value (GK με αξια). rule 'ms' (most starts) η 'rec'. Επιστρεφει (pid, τροπος)."""
    if rule == 'last':
        comp = [st for d, st, w in starts.get(tid, []) if d < date and (date - d).days <= 730 and w == 1.0]
        if comp:
            hit = [p for p in cands if p in comp[-1]]
            if hit:
                return max(hit, key=lambda p: cands[p]), 'lastcomp'
        rule = 'rec'
    sc = {p: gk_starts(tid, p, date) for p in cands}
    withst = [p for p in cands if sc[p][0] > 0]
    if withst:
        if rule == 'ms':
            return max(withst, key=lambda p: (sc[p][0], sc[p][1])), 'starts'
        return max(withst, key=lambda p: (sc[p][2], sc[p][1])), 'starts'
    return max(cands, key=lambda p: cands[p]), 'value'


def top11(pids, dstr, need=14):
    vals = sorted([v for v in (value_at(p, dstr) for p in set(pids)) if v], reverse=True)
    return sum(vals[:11]) if len(vals) >= need else np.nan


def top11_gk(pids, dstr, tid, date, rule, actual_st=None, need=14):
    vv = {p: value_at(p, dstr) for p in set(pids)}; vv = {p: v for p, v in vv.items() if v}
    if len(vv) < need:
        return np.nan, None
    g = {p: v for p, v in vv.items() if p in GK}
    if not g:
        return sum(sorted(vv.values(), reverse=True)[:11]), dict(chosen=None, mv=None, how='nogk', ngk_top11=0)
    top = sorted(vv, key=lambda p: -vv[p])[:11]
    mv = max(g, key=lambda p: g[p])
    how = None
    if actual_st is not None:
        act = [p for p in actual_st if p in g]
        if act:
            chosen = act[0]; how = 'actual'
    if how is None:
        chosen, how = pick_gk(tid, date, g, rule)
    nong = sorted([v for p, v in vv.items() if p not in GK], reverse=True)[:10]
    return g[chosen] + sum(nong), dict(chosen=chosen, mv=mv, how=how, ngk_top11=sum(p in GK for p in top))


squad = {}; team_games = {}
for r in D.itertuples():
    s = SQ.get(r.mid) or {}
    for k, tid in (('h', r.hid), ('a', r.aid)):
        t = s.get(k) or {}
        if len(t.get('st') or []) >= 8 and len(t.get('p') or {}) >= 14:
            squad[(r.mid, tid)] = dict(st=[int(x) for x in t['st']], p=[int(x) for x in t['p']])
            team_games.setdefault(int(tid), []).append((r.date, r.mid))

VARS = ('vc', 'vcg', 'vcr', 'vcl', 'vo', 'vog', 'vor', 'vol')
rows = []; info = []
for r in D.itertuples():
    dstr = r.date.strftime('%Y-%m-%d'); rec = dict(mid=r.mid, date=r.date, season=r.season, ctype=r.ctype, hid=r.hid, aid=r.aid, diff=r.diff, y=r.y)
    for k, tid in (('h', int(r.hid)), ('a', int(r.aid))):
        sq = squad.get((r.mid, tid))
        if sq is None:
            for c in VARS:
                rec[f'{c}_{k}'] = np.nan
            continue
        win = [m for (d, m) in team_games.get(tid, []) if abs((d - r.date).days) <= 6]
        union = [p for m in win for p in squad[(m, tid)]['p']]
        rec[f'vc_{k}'] = top11(union, dstr); rec[f'vo_{k}'] = top11(sq['p'], dstr)
        rec[f'vcg_{k}'], ic = top11_gk(union, dstr, tid, r.date, 'ms')
        rec[f'vcr_{k}'], icr = top11_gk(union, dstr, tid, r.date, 'rec')
        rec[f'vcl_{k}'], icl = top11_gk(union, dstr, tid, r.date, 'last')
        rec[f'vol_{k}'], iol = top11_gk(sq['p'], dstr, tid, r.date, 'last', actual_st=sq['st'])
        rec[f'vog_{k}'], io = top11_gk(sq['p'], dstr, tid, r.date, 'ms', actual_st=sq['st'])
        rec[f'vor_{k}'], ior = top11_gk(sq['p'], dstr, tid, r.date, 'rec', actual_st=sq['st'])
        act = [p for p in sq['st'] if p in GK]
        info.append(dict(mid=r.mid, date=r.date, season=r.season, ctype=r.ctype, tid=tid, ic=ic, icr=icr, icl=icl, io=io, ior=ior, iol=iol, actual=act[0] if act else None))
    rows.append(rec)
E = pd.DataFrame(rows)
for c in VARS:
    E[f'l_{c}'] = np.log(E[f'{c}_h'] / E[f'{c}_a'])
# ιδιο δειγμα με το harness: mids του intl_callup_test_events.csv μετα τα φιλτρα του harness
EV = pd.read_csv('intl_callup_test_events.csv', dtype={'mid': str})
EV = EV[EV.ctype.isin(['nl', 'qual', 'tourn'])].replace([np.inf, -np.inf], np.nan).dropna(subset=['diff', 'lv_full', 'lv_call', 'lv_own', 'l_abs', 'l_abs_own'])
C = E[E.mid.isin(set(EV.mid))].replace([np.inf, -np.inf], np.nan).dropna(subset=['diff'] + [f'l_{c}' for c in VARS]).copy()
P_('ΤΕΣΤ GK-aware ΑΞΙΑΣ — Μοντελο 1 εθνικων (H3) · ordered logit LOSO · αγωνιστικα ματς')
P_('ΠΡΟ-ΔΗΛΩΣΗ: GK εκδοχη ΠΕΡΝΑ αν RPS ALL < μη-GK αντιστοιχης (K1g/K1g-rec vs K1, K1og/K1og-rec vs K1o) ΚΑΙ καλυτερη σε >=4/6 σεζον. ΜΙΑ εκτελεση.')
P_(f'δειγμα: {len(C)} ματς (harness δειγμα {len(EV)}) · τερματοφυλακες στο intl_player_values: {len(GK)}')
FEATS = {'K1 V_call top11': ['diff', 'l_vc'], 'K1g V_call GK-ms': ['diff', 'l_vcg'], 'K1g-rec V_call GK-rec': ['diff', 'l_vcr'], 'K1g-last V_call GK-last': ['diff', 'l_vcl'],
         'K1o V_own top11': ['diff', 'l_vo'], 'K1og V_own GK-ms': ['diff', 'l_vog'], 'K1og-rec V_own GK-rec': ['diff', 'l_vor'], 'K1og-last V_own GK-last': ['diff', 'l_vol']}
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
        row[s] = rps(Pm, te['y'].values); allP.append(Pm); ally.append(te['y'].values)
    Pm = np.vstack(allP); yy = np.concatenate(ally)
    row['ALL'] = rps(Pm, yy); row['logloss'] = logloss(Pm, yy); row['n'] = len(yy)
    coefs[name] = fit_ol_multi(C[fs].values.astype(float), C['y'].values)[0]
    T_.append(row)
T = pd.DataFrame(T_).set_index('variant'); pd.set_option('display.width', 220)
P_('\n' + T.round({**{s: 4 for s in SEAS}, 'ALL': 5, 'logloss': 4}).to_string())
P_(f'\nsanity: K1 ALL {T.loc["K1 V_call top11", "ALL"]:.5f} vs harness .16700 (Δ {T.loc["K1 V_call top11", "ALL"] - 0.16700:+.5f}) · '
   f'K1o ALL {T.loc["K1o V_own top11", "ALL"]:.5f} vs harness .16694 (Δ {T.loc["K1o V_own top11", "ALL"] - 0.16694:+.5f})')
P_('\nΚΡΙΤΗΡΙΟ: GK vs μη-GK αντιστοιχη')
for g, b in (('K1g V_call GK-ms', 'K1 V_call top11'), ('K1g-rec V_call GK-rec', 'K1 V_call top11'), ('K1g-last V_call GK-last', 'K1 V_call top11'),
             ('K1og V_own GK-ms', 'K1o V_own top11'), ('K1og-rec V_own GK-rec', 'K1o V_own top11'), ('K1og-last V_own GK-last', 'K1o V_own top11')):
    better = sum(1 for s in SEAS if T.loc[g, s] < T.loc[b, s])
    d = T.loc[g, 'ALL'] - T.loc[b, 'ALL']
    P_(f'  {g:24s} vs {b:16s}: ΔRPS {d:+.5f} · Δlogloss {T.loc[g, "logloss"] - T.loc[b, "logloss"]:+.4f} · καλυτερη σε {better}/6 · {"ΠΕΡΝΑ" if (d < 0 and better >= 4) else "ΔΕΝ ΠΕΡΝΑ"}')
    P_('     ανα σεζον Δ: ' + ' '.join(f'{s}:{T.loc[g, s] - T.loc[b, s]:+.5f}' for s in SEAS))
P_('\nσυντελεστης αξιας (fit σε ολο το δειγμα), Elo ανα διπλασιασμο:')
for name, b in coefs.items():
    P_(f'  {name:24s}: {b[1] / b[0] * np.log(2):+.1f}')

# ---- συχνοτητα αλλαγης τερματοφυλακα ----
I = pd.DataFrame(info); I = I[I.mid.isin(set(C.mid))]
P_(f'\nΣΥΧΝΟΤΗΤΑ (ομαδα-ματς στο δειγμα: {len(I)})')
for lab, col in (('K1g (κληση, most-starts)', 'ic'), ('K1g-rec (κληση, rec)', 'icr'), ('K1g-last (κληση, last comp)', 'icl'),
                 ('K1og (ιδια αποστολη, actual->ms)', 'io'), ('K1og-rec (ιδια αποστολη, actual->rec)', 'ior'), ('K1og-last (ιδια αποστολη, actual->last)', 'iol')):
    x = [d for d in I[col] if d]
    n = len(x); ch = sum(1 for d in x if d['chosen'] is not None and d['chosen'] != d['mv'])
    hows = pd.Series([d['how'] for d in x]).value_counts().to_dict()
    two = sum(1 for d in x if d['ngk_top11'] >= 2); zero = sum(1 for d in x if d['ngk_top11'] == 0)
    P_(f'  {lab:40s}: επιλεγμενος ≠ πιο ακριβος GK σε {ch}/{n} ({ch / n * 100:.1f}%) · τροπος {hows}')
x0 = [d for d in I['ic'] if d]
P_(f'  απλο top11: ≥2 GK μεσα σε {sum(d["ngk_top11"] >= 2 for d in x0)}/{len(x0)} ({np.mean([d["ngk_top11"] >= 2 for d in x0]) * 100:.1f}%) · '
   f'0 GK σε {sum(d["ngk_top11"] == 0 for d in x0)} ({np.mean([d["ngk_top11"] == 0 for d in x0]) * 100:.1f}%)  [δεξαμενη κλησης]')
for lab, col in (('most-starts', 'ic'), ('rec', 'icr'), ('last', 'icl')):
    x = [(d, a) for d, a in zip(I[col], I.actual) if d and d['chosen'] is not None and a is not None]
    P_(f'  ακριβεια κανονα {lab:11s} (κληση) vs πραγματικος βασικος: {sum(d["chosen"] == a for d, a in x)}/{len(x)} ({np.mean([d["chosen"] == a for d, a in x]) * 100:.1f}%)')
x = [(d, a) for d, a in zip(I.ic, I.actual) if d and d['chosen'] is not None and a is not None]
P_(f'  ακριβεια «πιο ακριβος GK» vs πραγματικος βασικος: {np.mean([d["mv"] == a for d, a in x]) * 100:.1f}%')

# ---- παραδειγματα ----
IA = pd.DataFrame(info)
nm = lambda p: (PNAME.get(p) or str(p)) if p else '-'
def show(tid, k):
    S = IA[IA.tid == tid].sort_values('date').tail(k)
    P_(f'\n{NAME.get(tid, tid)} ({tid}) — τελευταια {k} ματς με αποστολη (ολοι οι τυποι):')
    for r in S.itertuples():
        ic = r.ic or {}; icr = r.icr or {}; icl = r.icl or {}; ds = r.date.strftime('%Y-%m-%d')
        P_(f'  {ds} {r.ctype:8s} ms: {nm(ic.get("chosen"))} ({ic.get("how")}) · rec: {nm(icr.get("chosen"))} ({icr.get("how")}) · last: {nm(icl.get("chosen"))} ({icl.get("how")}) · '
           f'πιο ακριβος: {nm(ic.get("mv"))} · ξεκινησε: {nm(r.actual)}')
    r = S.iloc[-1]; ic = r.ic or {}
    if ic.get('mv'):
        # λεπτομερεια για ολους τους GK της δεξαμενης κλησης στο τελευταιο ματς
        win = [m for (d, m) in team_games.get(tid, []) if abs((d - r.date).days) <= 6]
        pool = {p for m in win for p in squad[(m, tid)]['p'] if p in GK}
        dstr = r.date.strftime('%Y-%m-%d')
        for p in sorted(pool, key=lambda p: -(value_at(p, dstr) or 0)):
            n, last, sc = gk_starts(tid, p, r.date)
            P_(f'     GK {nm(p):28s} αξια {(value_at(p, dstr) or 0) / 1e6:5.1f}M · starts730 {n} · rec-score {sc:.2f} · τελευταια βασικη {last.strftime("%Y-%m-%d") if last is not None else "-"}')
show(8205, 8)
for tid in (8570, 8497):
    show(tid, 3)
P_('\nROI: το (β) του intl_callup_test ειναι ROI υπαρχοντων picks ανα ομαδα απουσιων, ΟΧΙ αξιολογηση πονταρισματος ανα εκδοχη μοντελου -> ROI ανα εκδοχη ΠΑΡΑΛΕΙΠΕΤΑΙ.')
open('intl_gk_value_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
