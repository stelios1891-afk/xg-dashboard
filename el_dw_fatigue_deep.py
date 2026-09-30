# -*- coding: utf-8 -*-
"""el_dw_fatigue_deep.py — ΚΟΥΡΑΣΗ ΣΤΗ ΔΙΑΒΟΛΟΒΔΟΜΑΔΑ, βαθια αναλυση (1/10/2026, Στελιος: «στο δικο μου μυαλο παιζει ρολο» — πριν την 3η αγων.).
Διαφορα απο el_fatigue_travel / el_domestic_before_dw (25/9): (1) ΚΑΙ ΣΥΝΟΛΑ ποντων · (2) διαφορα ξεκουρασης μεταξυ των 2 ομαδων
  (με ΚΑΙ τα εγχωρια) · (3) φορτος προηγουμενου ματς (παραταση, λεπτα των 5 βασικων) · (4) live μοντελο (h_new/t_new) ·
  (5) αγορα = Crown ανοιγμα ΚΑΙ κλεισιμο (αν η κουραση τιμολογειται μεσα στη μερα) · (6) τα picks μας (alert) σε 2α ματς διαβολοβδομαδας.
Δειγμα: κανονικη περιοδος E2021-E2025 με σειρα Crown· 2ο ματς διαβολοβδομαδας = ≤3.5 μερες απο το προηγουμενο ματς EL.
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ για live: (α) αποκλιση απο την αγορα (κλεισιμο) ιδια φορα σε ≥4/5 σεζον με |t| ≥ 2 · (β) ως διορθωση στο
  μοντελο: RMSE εκτος δειγματος (LOSO) καλυτερο σε ≥4/5 σεζον · (γ) δεν χαλαει τις μοναδες των picks στο alert.
Εξοδος: el_dw_fatigue_deep_out.txt"""
import sys, json, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
NS = {}
exec(open('el_alert_types.py', encoding='utf-8').read().split('ZZ = {}')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", ''), NS)
D, REC, PR, key, pick, settle, SE5 = (NS[k] for k in ('D', 'REC', 'PR', 'key', 'pick', 'settle', 'SE5'))
DOMNS = {}
exec(open('el_domestic_rating_test.py', encoding='utf-8').read().split('# ---- 3. EL μοντελο')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
     .replace("open('el_domestic_rating_test_out.txt', 'w'", "open('_unused_dw.txt', 'w'"), DOMNS)
MAP, DOM = DOMNS['MAP'], DOMNS['DOM']
FT = {}
exec(open('el_fatigue_travel.py', encoding='utf-8').read().split("D = pd.read_csv('el_preds_all.csv')")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", ''), FT)
ll, km = FT['ll'], FT['km']
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))
SCH = json.load(open('el_sched.json', encoding='utf-8'))
VEN = {f"{s}_{x['code']}": (x.get('vname'), x.get('tz')) for s, L in SCH.items() for x in L}
PL = json.load(open('el_players.json', encoding='utf-8'))
def top5(k, side):
    g = PL.get(k)
    if not g: return np.nan
    m = sorted([float(r[3] or 0) for r in g.get('ph' if side == 1 else 'pa', [])], reverse=True)
    return sum(m[:5]) if len(m) >= 5 else np.nan
# ---- εγχωρια ματς ανα (σεζον, ομαδα EL) ----
DG = {}
for (Y, code), (es, tid, L) in MAP.items():
    y = int(Y[1:]); k = f'{L}_{y % 100:02d}-{(y + 1) % 100:02d}'
    if k not in DOM: continue
    DG[(Y, code)] = sorted(pd.Timestamp(g[1][:10]).date() for g in DOM[k]['games'] if tid in (int(g[2]), int(g[3])))
# ---- μακροσκελες: ομαδα-ματς (ολες οι φασεις, για το «προηγουμενο ματς») ----
D = D.copy(); D['pos'] = np.arange(len(D))
T = pd.concat([D.assign(team=D.home, opp=D.away, side=1), D.assign(team=D.away, opp=D.home, side=-1)]).sort_values(['season', 'team', 't']).reset_index(drop=True)
T['loc'] = [ll(VEN.get(k, (None, None))[0]) for k in T.key]
T['tz'] = [VEN.get(k, (None, None))[1] for k in T.key]
g = T.groupby(['season', 'team'])
T['prev_t'] = g.t.shift(1); T['prev_loc'] = g['loc'].shift(1); T['prev_tz'] = g.tz.shift(1); T['prev_side'] = g.side.shift(1)
T['prev_key'] = g.key.shift(1); T['prev_gmin'] = g.gmin.shift(1)
T['rest_el'] = (T.t - T.prev_t).dt.total_seconds() / 86400
T['dw2'] = T.rest_el <= 3.5
T['prev_ot'] = T.prev_gmin > 40.5
T['prev_top5'] = [top5(k, s) if isinstance(k, str) else np.nan for k, s in zip(T.prev_key, T.prev_side)]
T['travel'] = [km(a, b) if (d and a and b) else np.nan for a, b, d in zip(T.prev_loc, T['loc'], T.dw2)]
def _tzd(a, b, d):
    try:
        if d and a is not None and b is not None: return abs(float(a) - float(b))
    except Exception:
        pass
    return np.nan
T['tzs'] = [_tzd(a, b, d) for a, b, d in zip(T.tz, T.prev_tz, T.dw2)]
def dom_info(Y, code, t):
    L = DG.get((Y, code), []); d = t.date()
    prev = [x for x in L if x < d]
    return ((d - prev[-1]).days if prev else np.nan), sum(1 for x in L if 0 < (d - x).days <= 7)
DI = [dom_info(s, c, t) for s, c, t in zip(T.season, T.team, T.t)]
T['rest_dom'] = [a for a, b in DI]; T['dom7'] = [b for a, b in DI]
el7 = np.zeros(len(T), int)
for _, x in T.groupby(['season', 'team']):
    tt = x.t.values
    el7[x.index.values] = [int(((tt < v) & (tt >= v - np.timedelta64(7, 'D'))).sum()) for v in tt]
T['el7'] = el7
T['rest_any'] = np.fmin(T.rest_el, T.rest_dom.fillna(99))
T['games7'] = T.el7 + T.dom7
# ---- αγορα / μοντελο (Crown ανοιγμα & κλεισιμο, E2021-25 RS) ----
MKT = {}
for p in REC[21]:
    if p in REC[23]:
        r1, r2 = REC[21][p], REC[23][p]
        MKT[p] = dict(mo=r1['ser'][0][1], mc=r1['ser'][-1][1], to=r2['ser'][0][1], tc=r2['ser'][-1][1],
                      hm=PR.get(key(p), {}).get('h_new', np.nan), tm=PR.get(key(p), {}).get('t_new', np.nan))
G = D.iloc[sorted(MKT)].copy(); G.index = sorted(MKT)
for c in ('mo', 'mc', 'to', 'tc', 'hm', 'tm'): G[c] = [MKT[p][c] for p in G.index]
G['margin'] = G.hs - G.as_; G['total'] = G.hs + G.as_
TH = T[T.side == 1].set_index('pos'); TA = T[T.side == -1].set_index('pos')
for pre, X in (('h_', TH), ('a_', TA)):
    for c in ('rest_el', 'rest_any', 'games7', 'dw2', 'prev_ot', 'prev_top5', 'travel', 'tzs', 'prev_side'):
        G[pre + c] = X.loc[G.index, c].values
G = G[G.phase == 'RS']
G['rm_c'] = G.margin - G.mc; G['rm_o'] = G.margin - G.mo; G['rm_m'] = G.margin - G.hm
G['rt_c'] = G.total - G.tc;  G['rt_o'] = G.total - G.to;  G['rt_m'] = G.total - G.tm
G['mv_m'] = G.mc - G.mo; G['mv_t'] = G.tc - G.to
dw = G[(G.h_dw2 == True) & (G.a_dw2 == True)].copy()
P(f'ματς με Crown ανοιγμα/κλεισιμο (RS E2021-25): {len(G)} · 2α διαβολοβδομαδας (και οι 2 ομαδες ≤3.5 μερες): {len(dw)} · μονο η μια: {int(((G.h_dw2 == True) ^ (G.a_dw2 == True)).sum())}')
def seas(G_, col):
    return ' '.join(f'{Y[-2:]}:{G_[G_.season == Y][col].mean():+.1f}' for Y in SE5 if (G_.season == Y).sum() >= 5)
def st(x, lab, w=50, extra=''):
    x = pd.Series(x).dropna()
    if len(x) < 8: P(f'  {lab:{w}s} n {len(x):4d}'); return
    se = x.std() / math.sqrt(len(x)); P(f'  {lab:{w}s} n {len(x):4d} · {x.mean():+6.2f} (±{1.96*se:.2f}, t {x.mean()/se:+.1f}){extra}')
# ---- 0. ελεγχος ιδεας Στελιου: ξεκουραση στα 2α ματς ----
P(''); P('=== 0. ΞΕΚΟΥΡΑΣΗ ΣΤΑ 2α ΜΑΤΣ ΔΙΑΒΟΛΟΒΔΟΜΑΔΑΣ ===')
pairs = pd.Series([f'{round(a)}-{round(b)}' for a, b in zip(dw.h_rest_el, dw.a_rest_el)]).value_counts()
P('  μερες απο το προηγουμενο ματς ΕΥΡΩΛΙΓΚΑΣ (γηπ-φιλ): ' + ' · '.join(f'{k}: {v} ({v/len(dw):.0%})' for k, v in pairs.items()))
rd = dw.h_rest_el - dw.a_rest_el
P(f'  ιδια ξεκουραση απο την Ευρωλιγκα (±0.5 μερα): {np.mean(np.abs(rd) < 0.5):.0%}')
ra = dw.h_rest_any - dw.a_rest_any
P(f'  ΜΕ τα εγχωρια (τελευταιο ματς οποιασδηποτε διοργανωσης): ιδια {np.mean(np.abs(ra) < 0.5):.0%} · διαφορα ≥1 μερα {np.mean(np.abs(ra) >= 0.5):.0%}')
P('  ματς στις 7 μερες πριν (EL+εγχωρια), γηπ-φιλ: ' + ' · '.join(f'{k}: {v}' for k, v in pd.Series([f'{int(a)}-{int(b)}' for a, b in zip(dw.h_games7, dw.a_games7)]).value_counts().head(8).items()))
# ---- 1. 2α διαβολοβδομαδας vs κανονικα ----
P(''); P('=== 1. 2α ΜΑΤΣ ΔΙΑΒΟΛΟΒΔΟΜΑΔΑΣ vs ΚΑΝΟΝΙΚΑ (γηπεδουχος· πραγματικο − αγορα κλεισιματος) ===')
nrm = G[(G.h_rest_el >= 5) & (G.a_rest_el >= 5)]
for lab, X in (('κανονικα (≥5 μερες και οι δυο)', nrm), ('2α διαβολοβδομαδας', dw)):
    st(X.rm_c, f'ΔΙΑΦΟΡΑ {lab}', extra=f' · vs ανοιγμα {X.rm_o.mean():+.2f} · vs μοντελο {X.rm_m.mean():+.2f} · [{seas(X, "rm_c")}]')
    st(X.rt_c, f'ΣΥΝΟΛΟ  {lab}', extra=f' · vs ανοιγμα {X.rt_o.mean():+.2f} · vs μοντελο {X.rt_m.mean():+.2f} · [{seas(X, "rt_c")}]')
P(f'  ρυθμος (κατοχες): κανονικα {nrm.pace.mean():.1f} · 2α διαβολοβδομαδας {dw.pace.mean():.1f} · συνολο πραγμ. {nrm.total.mean():.1f} vs {dw.total.mean():.1f} · γραμμη κλεισ. {nrm.tc.mean():.1f} vs {dw.tc.mean():.1f}')
# ---- 2. μεσα στα 2α: απο τη ματια της ΟΜΑΔΑΣ ----
P(''); P('=== 2. ΜΕΣΑ ΣΤΑ 2α ΜΑΤΣ: πραγματικο − αγορα ΥΠΕΡ της ομαδας με το χαρακτηριστικο (+ = τα πηγε καλυτερα απ οσο περιμενε η αγορα) ===')
P('   (αγορα κινηθηκε = κλεισιμο − ανοιγμα υπερ της ομαδας: − = η αγορα την «τιμωρησε» μεσα στη μερα)')
cols = ('rest_any', 'games7', 'prev_ot', 'prev_top5', 'travel', 'tzs', 'prev_side')
TM = pd.concat([dw.assign(sd=1, res_c=dw.rm_c, res_o=dw.rm_o, res_m=dw.rm_m, mv=dw.mv_m, **{c: dw['h_' + c] for c in cols}, **{'o_' + c: dw['a_' + c] for c in cols}),
                dw.assign(sd=-1, res_c=-dw.rm_c, res_o=-dw.rm_o, res_m=-dw.rm_m, mv=-dw.mv_m, **{c: dw['a_' + c] for c in cols}, **{'o_' + c: dw['h_' + c] for c in cols})])
def cat(lab, m):
    x = TM[m.fillna(False).astype(bool)] if hasattr(m, 'fillna') else TM[m]
    if len(x) < 8: P(f'  {lab:48s} n {len(x)}'); return
    se = x.res_c.std() / math.sqrt(len(x))
    per = ' '.join(f'{Y[-2:]}:{x[x.season == Y].res_c.mean():+.1f}' for Y in SE5 if (x.season == Y).sum() >= 4)
    P(f'  {lab:48s} n {len(x):4d} · vs κλεισ. {x.res_c.mean():+5.2f} (t {x.res_c.mean()/se:+.1f}) · vs ανοιγ. {x.res_o.mean():+5.2f} · vs μοντ. {x.res_m.mean():+5.2f} · αγορα κινηθηκε {x.mv.mean():+.2f} · [{per}]')
cat('ΛΙΓΟΤΕΡΗ ξεκουραση (με εγχωρια) κατα ≥1 μερα', TM.rest_any <= TM.o_rest_any - 1)
cat('ιδια ξεκουραση (με εγχωρια)', (TM.rest_any - TM.o_rest_any).abs() < 1)
cat('ΠΕΡΙΣΣΟΤΕΡΑ ματς στις 7 μερες (≥+1)', TM.games7 >= TM.o_games7 + 1)
cat('4+ ματς στις 7 μερες', TM.games7 >= 4)
cat('3 ματς στις 7 μερες', TM.games7 == 3)
cat('2 ή λιγοτερα στις 7 μερες', TM.games7 <= 2)
cat('ΠΑΡΑΤΑΣΗ στο προηγουμενο (ο αντιπαλος οχι)', (TM.prev_ot == True) & (TM.o_prev_ot != True))
q75, q25 = TM.prev_top5.quantile(0.75), TM.prev_top5.quantile(0.25)
cat(f'βαρια λεπτα βασικων στο προηγ. (top-5 ≥{q75:.0f} λεπτα)', TM.prev_top5 >= q75)
cat(f'ελαφρια λεπτα βασικων στο προηγ. (≤{q25:.0f})', TM.prev_top5 <= q25)
cat('βασικοι επαιξαν ≥15 λεπτα περισσοτερα απο του αντιπαλου', TM.prev_top5 >= TM.o_prev_top5 + 15)
cat('ΕΚΤΟΣ → ΕΚΤΟΣ (2 εκτος σερι)', (TM.sd == -1) & (TM.prev_side == -1))
cat('ΕΝΤΟΣ → ΕΚΤΟΣ', (TM.sd == -1) & (TM.prev_side == 1))
cat('ΕΚΤΟΣ → ΕΝΤΟΣ', (TM.sd == 1) & (TM.prev_side == -1))
cat('ΕΝΤΟΣ → ΕΝΤΟΣ (2 εντος σερι)', (TM.sd == 1) & (TM.prev_side == 1))
for lo, hi in ((0, 1), (1, 1000), (1000, 2000), (2000, 99999)):
    cat(f'φιλοξενουμενος: ταξιδι {lo}-{hi if hi < 99999 else "+"} χλμ απο το προηγ. ματς', (TM.sd == -1) & (TM.travel >= lo) & (TM.travel < hi))
cat('φιλοξενουμενος: αλλαγη ζωνης ωρας ≥1', (TM.sd == -1) & (TM.tzs >= 1))
# ---- 3. ΣΥΝΟΛΑ ----
P(''); P('=== 3. ΣΥΝΟΛΑ στα 2α ματς: πραγματικο − αγορα (+ = βγηκαν περισσοτεροι ποντοι απ οσους περιμενε η αγορα) ===')
def tcat(lab, m):
    x = dw[m.fillna(False).astype(bool)] if hasattr(m, 'fillna') else dw[m]
    if len(x) < 8: P(f'  {lab:48s} n {len(x)}'); return
    se = x.rt_c.std() / math.sqrt(len(x))
    P(f'  {lab:48s} n {len(x):4d} · vs κλεισ. {x.rt_c.mean():+5.2f} (t {x.rt_c.mean()/se:+.1f}) · vs ανοιγ. {x.rt_o.mean():+5.2f} · vs μοντ. {x.rt_m.mean():+5.2f} · αγορα κινηθηκε {x.mv_t.mean():+.2f} · [{seas(x, "rt_c")}]')
tcat('ΟΛΑ τα 2α', pd.Series(True, index=dw.index))
tcat('και οι δυο με 4+ ματς στις 7 μερες', (dw.h_games7 >= 4) & (dw.a_games7 >= 4))
tcat('ματς στις 7 μερες (2 ομαδες μαζι) ≥ 7', dw.h_games7 + dw.a_games7 >= 7)
tcat('ματς στις 7 μερες (2 ομαδες μαζι) ≤ 5', dw.h_games7 + dw.a_games7 <= 5)
tcat('ΠΑΡΑΤΑΣΗ στο προηγουμενο καποιας', (dw.h_prev_ot == True) | (dw.a_prev_ot == True))
s5 = dw.h_prev_top5 + dw.a_prev_top5
tcat('βαρια λεπτα βασικων (2 ομαδες, πανω 25%)', s5 >= s5.quantile(0.75))
tcat('ελαφρια λεπτα βασικων (κατω 25%)', s5 <= s5.quantile(0.25))
tcat('φιλοξενουμενος ταξιδι ≥1000 χλμ', dw.a_travel >= 1000)
tcat('φιλοξενουμενος 2 εκτος σερι', dw.a_prev_side == -1)
# ---- 4. ΟΛΑ τα ματς: κλισεις ----
P(''); P('=== 4. ΟΛΑ τα ματς (οχι μονο διαβολοβδομαδα): αποκλιση απο το ΚΛΕΙΣΙΜΟ ~ κουραση (διαφορα γηπ − φιλ / αθροισμα) — κλιση, t, ανα σεζον ===')
A = G.copy()
A['d_rest'] = np.clip(A.h_rest_any, 0, 5) - np.clip(A.a_rest_any, 0, 5)
A['d_g7'] = A.h_games7 - A.a_games7
A['d_top5'] = (A.h_prev_top5 - A.a_prev_top5) / 10
A['d_ot'] = A.h_prev_ot.astype(float) - A.a_prev_ot.astype(float)
A['s_g7'] = A.h_games7 + A.a_games7
A['s_top5'] = (A.h_prev_top5 + A.a_prev_top5) / 10
A['s_rest'] = np.clip(A.h_rest_any, 0, 5) + np.clip(A.a_rest_any, 0, 5)
PASS = []
def reg(y, x, lab):
    m = A[[y, x, 'season']].dropna()
    cf = np.polyfit(m[x], m[y], 1); b = cf[0]; r = m[y] - np.polyval(cf, m[x])
    se = math.sqrt(np.sum(r ** 2) / (len(m) - 2) / np.sum((m[x] - m[x].mean()) ** 2))
    per = [np.polyfit(m[m.season == Y][x], m[m.season == Y][y], 1)[0] for Y in SE5 if (m.season == Y).sum() > 30 and m[m.season == Y][x].std() > 0]
    same = sum(np.sign(p) == np.sign(b) for p in per); ok = abs(b / se) >= 2 and same >= 4
    if ok: PASS.append((y, x, lab))
    P(f'  {lab:54s} n {len(m)} · κλιση {b:+.3f} (t {b/se:+.1f}) · ιδια φορα {same}/{len(per)} · [' + ' '.join(f'{p:+.2f}' for p in per) + ']' + ('   ← ΠΕΡΝΑ (α)' if ok else ''))
reg('rm_c', 'd_rest', 'ΔΙΑΦΟΡΑ ~ διαφορα ξεκουρασης (μερες, με εγχωρια)')
reg('rm_c', 'd_g7', 'ΔΙΑΦΟΡΑ ~ διαφορα ματς στις 7 μερες')
reg('rm_c', 'd_top5', 'ΔΙΑΦΟΡΑ ~ διαφορα λεπτων βασικων προηγ. (ανα 10)')
reg('rm_c', 'd_ot', 'ΔΙΑΦΟΡΑ ~ διαφορα παρατασης προηγ.')
reg('rt_c', 's_g7', 'ΣΥΝΟΛΟ ~ ματς στις 7 μερες (2 ομαδες)')
reg('rt_c', 's_rest', 'ΣΥΝΟΛΟ ~ ξεκουραση (αθροισμα μερων)')
reg('rt_c', 's_top5', 'ΣΥΝΟΛΟ ~ λεπτα βασικων προηγ. (αθροισμα, ανα 10)')
P('  απεναντι στο ΜΟΝΤΕΛΟ (χρειαζεται το μοντελο διορθωση, ανεξαρτητα απο την αγορα;):')
for y, x, lab in (('rm_m', 'd_rest', 'ΔΙΑΦΟΡΑ vs μοντ. ~ διαφορα ξεκουρασης'), ('rm_m', 'd_g7', 'ΔΙΑΦΟΡΑ vs μοντ. ~ διαφορα ματς 7 μερων'),
                  ('rm_m', 'd_top5', 'ΔΙΑΦΟΡΑ vs μοντ. ~ διαφορα λεπτων βασικων'),
                  ('rt_m', 's_g7', 'ΣΥΝΟΛΟ vs μοντ. ~ ματς 7 μερων'), ('rt_m', 's_top5', 'ΣΥΝΟΛΟ vs μοντ. ~ λεπτα βασικων'), ('rt_m', 's_rest', 'ΣΥΝΟΛΟ vs μοντ. ~ ξεκουραση')):
    reg(y, x, lab)
# ---- 4β. οσα περασαν το (α): LOSO διορθωση του μοντελου ----
if PASS:
    P(''); P('=== 4β. ΟΣΑ ΠΕΡΑΣΑΝ (α): διορθωση μοντελου με κλιση απο τις ΑΛΛΕΣ σεζον (LOSO) — RMSE ===')
    for y, x, lab in PASS:
        tgt = 'margin' if y.startswith('rm') else 'total'; base = 'hm' if tgt == 'margin' else 'tm'
        m = A[[x, 'season', tgt, base]].dropna(); rb, rn = [], []
        for Y in SE5:
            tr, te = m[m.season != Y], m[m.season == Y]
            b = np.polyfit(tr[x], tr[tgt] - tr[base], 1)[0]
            rb.append(np.sqrt(np.mean((te[tgt] - te[base]) ** 2))); rn.append(np.sqrt(np.mean((te[tgt] - te[base] - b * (te[x] - tr[x].mean())) ** 2)))
        w_ = sum(n < b for n, b in zip(rn, rb))
        P(f'  {lab:54s} RMSE ανα σεζον ' + ' '.join(f'{n - b:+.3f}' for n, b in zip(rn, rb)) + f' → καλυτερο {w_}/5 {"ΠΕΡΝΑ (β)" if w_ >= 4 else "✗"}')
# ---- 5. τα picks μας ----
P(''); P('=== 5. ΤΑ PICKS ΜΑΣ (alert Crown, live μοντελο, χωρις καταγραφες): 2α ματς διαβολοβδομαδας vs υπολοιπα ===')
DWSET = set(dw.index)
for t, nm in ((21, 'ΧΑΝΤΙΚΑΠ'), (23, 'ΣΥΝΟΛΑ')):
    R = {'2α διαβολοβδομαδας': [], 'υπολοιπα': []}
    RR = {'υπερ του ΠΙΟ ξεκουραστου (≥1 μερα)': [], 'υπερ του ΠΙΟ κουρασμενου (≥1 μερα)': [], 'ιδια ξεκουραση': []}
    for p, r in REC[t].items():
        m = PR.get(key(p), {}).get(('h_' if t == 21 else 't_') + 'new')
        if m is None or not np.isfinite(m) or p not in G.index: continue
        ser, tip = r['ser'], r['tip']; o = ser[0]
        for k_, row in enumerate(ser):
            if row[0] >= tip: break
            side, e, od = pick(t, m, row)
            if e < 0.08: continue
            hrs = (tip - row[0]) / 3600; mvv = -(row[1] - o[1]) * side
            if k_ > 0 and ((t == 21 and hrs < 2) or (t == 23 and mvv >= 1.5)): break
            pnl = settle(t, p, side, row, od); R['2α διαβολοβδομαδας' if p in DWSET else 'υπολοιπα'].append((pnl, D.season.values[p]))
            if t == 21 and p in DWSET:
                d_ = (G.loc[p, 'h_rest_any'] - G.loc[p, 'a_rest_any']) * side
                RR['υπερ του ΠΙΟ ξεκουραστου (≥1 μερα)' if d_ >= 1 else ('υπερ του ΠΙΟ κουρασμενου (≥1 μερα)' if d_ <= -1 else 'ιδια ξεκουραση')].append((pnl, D.season.values[p]))
            break
    for k, L in list(R.items()) + (list(RR.items()) if t == 21 else []):
        if L:
            a = np.array([x[0] for x in L]); ss = [x[1] for x in L]
            pos = sum(1 for s in SE5 if s in ss and np.mean([x[0] for x in L if x[1] == s]) > 0)
            P(f'  {nm:9s} {k:38s} n {len(a):4d} · ROI {a.mean()*100:+6.1f}% · μοναδες {a.sum():+6.1f} · {pos}/5')
open('el_dw_fatigue_deep_out.txt', 'w', encoding='utf-8').write('\n'.join(out))

# ---- 6. ΤΑΞΙΔΙ ΦΙΛΟΞΕΝΟΥΜΕΝΟΥ ≥1000 χλμ στο 2ο ματς: κριτηρια (β) και (γ) ----
P(''); P('=== 6. ΦΙΛΟΞΕΝΟΥΜΕΝΟΣ ΜΕ ΤΑΞΙΔΙ ≥1000 χλμ ΑΠΟ ΤΟ ΠΡΟΗΓΟΥΜΕΝΟ ΜΑΤΣ (2ο διαβολοβδομαδας): (β) διορθωση μοντελου LOSO · (γ) picks ===')
G['trav'] = (G.a_dw2 == True) & (G.a_travel >= 1000)
G['trav_tz'] = (G.a_dw2 == True) & (G.a_tzs >= 1)
for flag, lab in (('trav', 'ταξιδι ≥1000 χλμ'), ('trav_tz', 'αλλαγη ζωνης ωρας ≥1')):
    X = G[G[flag]]
    P(f'  {lab}: {len(X)} ματς · αποκλιση απο κλεισιμο {X.rm_c.mean():+.2f} · απο μοντελο {X.rm_m.mean():+.2f} · επικαλυψη με το αλλο {((G.trav) & (G.trav_tz)).sum()}')
    DL = {}
    for Y in SE5:
        tr = G[(G.season != Y) & G[flag]]; DL[Y] = tr.rm_m.mean()
    rb, rn, ra, rna = [], [], [], []
    for Y in SE5:
        te = G[G.season == Y]; adj = te.hm + np.where(te[flag], DL[Y], 0.0)
        rb.append(np.sqrt(np.mean((te.margin - te.hm) ** 2))); rn.append(np.sqrt(np.mean((te.margin - adj) ** 2)))
        tf = te[te[flag]]; ra.append(np.sqrt(np.mean((tf.margin - tf.hm) ** 2))); rna.append(np.sqrt(np.mean((tf.margin - tf.hm - DL[Y]) ** 2)))
    w_ = sum(n < b for n, b in zip(rn, rb))
    P(f'    διορθωση (LOSO) ανα σεζον: ' + ' '.join(f'{Y[-2:]}:{DL[Y]:+.1f}' for Y in SE5) + ' π. υπερ γηπεδουχου')
    P(f'    (β) RMSE ολης της σεζον: ' + ' '.join(f'{n - b:+.4f}' for n, b in zip(rn, rb)) + f' → καλυτερο {w_}/5 {"ΠΕΡΝΑ" if w_ >= 4 else "✗"}'
      + ' · μονο τα ματς με ταξιδι: ' + ' '.join(f'{n - b:+.2f}' for n, b in zip(rna, ra)))
    for t_ in (21,):
        res = {'live': [], 'με διορθωση': []}
        for p, r in REC[t_].items():
            if p not in G.index: continue
            m0 = PR.get(key(p), {}).get('h_new')
            if m0 is None or not np.isfinite(m0): continue
            Y = D.season.values[p]
            for nm, m in (('live', m0), ('με διορθωση', m0 + (DL[Y] if G.loc[p, flag] else 0.0))):
                ser, tip = r['ser'], r['tip']
                for k_, row in enumerate(ser):
                    if row[0] >= tip: break
                    side, e, od = pick(21, m, row)
                    if e < 0.08: continue
                    if k_ > 0 and (tip - row[0]) / 3600 < 2: break
                    res[nm].append((settle(21, p, side, row, od), Y, bool(G.loc[p, flag]), side)); break
        for nm, L in res.items():
            a = np.array([x[0] for x in L]); f_ = [x for x in L if x[2]]
            per = ' '.join(f'{Y[-2:]}:{sum(x[0] for x in L if x[1] == Y):+.1f}' for Y in SE5)
            P(f'    (γ) ΧΑΝΤΙΚΑΠ {nm:12s} ολα: n {len(a)} · ROI {a.mean()*100:+.1f}% · μοναδες {a.sum():+.1f} [{per}] · στα ματς με ταξιδι: n {len(f_)} · μοναδες {sum(x[0] for x in f_):+.1f}'
              + f' (υπερ γηπ {sum(1 for x in f_ if x[3] == 1)} / υπερ φιλ {sum(1 for x in f_ if x[3] == -1)})')
open('el_dw_fatigue_deep_out.txt', 'w', encoding='utf-8').write('\n'.join(out))

# ---- 7. ΤΑΞΙΔΙ: κανονικη εβδομαδα vs διαβολοβδομαδα · προηγουμενο εντος/εκτος (ερωτηση Στελιου 1/10) ----
P(''); P('=== 7. ΤΑΞΙΔΙ ΦΙΛΟΞΕΝΟΥΜΕΝΟΥ: κανονικη εβδομαδα vs 2ο ματς διαβολοβδομαδας · απο εντος ή απο εκτος ===')
HB = T[T.side == 1].groupby(['season', 'team'])['loc'].agg(lambda s: s.dropna().mode().iloc[0] if len(s.dropna()) else None)
AW = T[T.side == -1].set_index('pos')
G['a_home_loc'] = [HB.get((s, a)) for s, a in zip(G.season, G.away)]
G['a_loc_now'] = [AW.loc[p, 'loc'] for p in G.index]
G['a_from_home'] = [km(h, c) if (h and c) else np.nan for h, c in zip(G.a_home_loc, G.a_loc_now)]
G['a_prev_side2'] = [AW.loc[p, 'prev_side'] for p in G.index]
G['a_rest'] = G.a_rest_el
def tr(lab, m):
    x = G[m.fillna(False).astype(bool)]
    if len(x) < 8: P(f'  {lab:62s} n {len(x)}'); return
    s1 = x.rm_c.std() / math.sqrt(len(x))
    per = ' '.join(f'{Y[-2:]}:{-x[x.season == Y].rm_m.mean():+.1f}' for Y in SE5 if (x.season == Y).sum() >= 4)
    P(f'  {lab:62s} n {len(x):4d} · φιλοξ. vs ΜΟΝΤΕΛΟ {-x.rm_m.mean():+5.2f} (t {-x.rm_m.mean()/(x.rm_m.std()/math.sqrt(len(x))):+.1f}) · vs αγορα {-x.rm_c.mean():+5.2f} (t {-x.rm_c.mean()/s1:+.1f}) · [vs μοντ. ανα σεζον {per}]')
nw = G.a_rest >= 5
P('  ΚΑΝΟΝΙΚΗ ΕΒΔΟΜΑΔΑ (≥5 μερες απο το προηγ. ματς), αποσταση εδρας φιλοξ. → γηπεδο:')
for lo, hi in ((0, 1000), (1000, 2000), (2000, 99999)):
    tr(f'    {lo}-{hi if hi < 99999 else "+"} χλμ', nw & (G.a_from_home >= lo) & (G.a_from_home < hi))
d2 = G.a_dw2 == True
P('  2ο ΜΑΤΣ ΔΙΑΒΟΛΟΒΔΟΜΑΔΑΣ, αποσταση ΑΠΟ ΤΟ ΠΡΟΗΓΟΥΜΕΝΟ γηπεδο:')
for lo, hi in ((0, 1000), (1000, 99999)):
    for ps, pl in ((1, 'προηγ. ΕΝΤΟΣ (σπιτι → ταξιδι)'), (-1, 'προηγ. ΕΚΤΟΣ (ταξιδι → ταξιδι)')):
        tr(f'    {lo}-{hi if hi < 99999 else "+"} χλμ · {pl}', d2 & (G.a_travel >= lo) & (G.a_travel < hi) & (G.a_prev_side2 == ps))
P('  2ο ΜΑΤΣ ΔΙΑΒΟΛΟΒΔΟΜΑΔΑΣ, ΕΚΤΟΣ → ΕΚΤΟΣ: μακρια απο το σπιτι αλλα κοντα στο προηγ. (≥1000 απο εδρα, <1000 απο προηγ.)')
tr('    ', d2 & (G.a_prev_side2 == -1) & (G.a_from_home >= 1000) & (G.a_travel < 1000))
P('  ΣΥΓΚΡΙΣΗ ιδιας αποστασης: ≥1000 χλμ σε κανονικη εβδομαδα vs στο 2ο ματς')
tr('    κανονικη εβδομαδα, ≥1000 χλμ απο την εδρα', nw & (G.a_from_home >= 1000))
tr('    2ο ματς, ≥1000 χλμ απο το προηγ. γηπεδο', d2 & (G.a_travel >= 1000))
tr('    1ο ματς διαβολοβδομαδας (ξερει οτι ξαναπαιζει σε 2 μερες), ≥1000 απο εδρα', (G.a_rest >= 5) & (G.a_from_home >= 1000) & False)
open('el_dw_fatigue_deep_out.txt', 'w', encoding='utf-8').write('\n'.join(out))

# ---- 8. (α) ΞΕΧΩΡΙΣΤΗ διορθωση απο εντος / απο εκτος (με συγκρατηση) · (β) ΓΗΠΕΔΟΥΧΟΣ στο 2ο ματς ----
P(''); P('=== 8α. ΦΙΛΟΞΕΝΟΥΜΕΝΟΣ ≥1000 χλμ: ΜΙΑ διορθωση vs ΔΥΟ (απο εντος / απο εκτος), LOSO RMSE ανα σεζον ===')
G['tr_home'] = (G.a_dw2 == True) & (G.a_travel >= 1000) & (G.a_prev_side2 == 1)
G['tr_away'] = (G.a_dw2 == True) & (G.a_travel >= 1000) & (G.a_prev_side2 == -1)
G['tr_any'] = G.tr_home | G.tr_away
def loso(groups, shrink=None, lab=''):
    rb, rn, used = [], [], {}
    for Y in SE5:
        tr_ = G[G.season != Y]; te = G[G.season == Y]; adj = te.hm.copy()
        pool = tr_[tr_.tr_any].rm_m.mean()
        for gcol in groups:
            x = tr_[tr_[gcol]].rm_m; d = x.mean()
            if shrink: d = pool + (d - pool) * len(x) / (len(x) + shrink)
            adj = adj + np.where(te[gcol], d, 0.0); used.setdefault(gcol, []).append(d)
        rb.append(np.sqrt(np.mean((te.margin - te.hm) ** 2))); rn.append(np.sqrt(np.mean((te.margin - adj) ** 2)))
    w_ = sum(n < b for n, b in zip(rn, rb))
    P(f'  {lab:44s} διορθωση ' + ' · '.join(f'{g}: {np.mean(v):+.2f}' for g, v in used.items()) + ' · RMSE vs live ' + ' '.join(f'{n - b:+.4f}' for n, b in zip(rn, rb))
      + f' (συνολο {sum(rn) - sum(rb):+.4f}) → {w_}/5')
    return rn
r1 = loso(['tr_any'], lab='ΜΙΑ κοινη')
r2 = loso(['tr_home', 'tr_away'], lab='ΔΥΟ, ακριβως οπως μετρηθηκαν')
r3 = loso(['tr_home', 'tr_away'], shrink=50, lab='ΔΥΟ, με συγκρατηση (50 ματς) προς τον κοινο')
P('  ΔΥΟ-με-συγκρατηση vs ΜΙΑ: ' + ' '.join(f'{a - b:+.4f}' for a, b in zip(r3, r1)) + f' → καλυτερο {sum(a < b for a, b in zip(r3, r1))}/5')
P(''); P('=== 8β. ΓΗΠΕΔΟΥΧΟΣ στο 2ο ματς διαβολοβδομαδας: απο που ερχεται (υπερ γηπεδουχου· vs μοντελο / αγορα) ===')
HO = T[T.side == 1].set_index('pos')
G['h_prev_side2'] = [HO.loc[p, 'prev_side'] for p in G.index]
def hc(lab, m):
    x = G[m.fillna(False).astype(bool)]
    if len(x) < 8: P(f'  {lab:58s} n {len(x)}'); return
    sm_ = x.rm_m.std() / math.sqrt(len(x)); sc = x.rm_c.std() / math.sqrt(len(x))
    per = ' '.join(f'{Y[-2:]}:{x[x.season == Y].rm_m.mean():+.1f}' for Y in SE5 if (x.season == Y).sum() >= 4)
    P(f'  {lab:58s} n {len(x):4d} · vs ΜΟΝΤΕΛΟ {x.rm_m.mean():+5.2f} (t {x.rm_m.mean()/sm_:+.1f}) · vs αγορα {x.rm_c.mean():+5.2f} (t {x.rm_c.mean()/sc:+.1f}) · [vs μοντ. {per}]')
h2 = G.h_dw2 == True
hc('ΕΝΤΟΣ → ΕΝΤΟΣ (επαιξε και το 1ο στο σπιτι)', h2 & (G.h_prev_side2 == 1))
hc('ΕΚΤΟΣ → ΕΝΤΟΣ, γυρισμα <1000 χλμ', h2 & (G.h_prev_side2 == -1) & (G.h_travel < 1000))
hc('ΕΚΤΟΣ → ΕΝΤΟΣ, γυρισμα ≥1000 χλμ', h2 & (G.h_prev_side2 == -1) & (G.h_travel >= 1000))
P('  ...και με τον φιλοξενουμενο (ΙΔΙΟ ματς): ')
hc('  γηπ. ΕΝΤΟΣ→ΕΝΤΟΣ & φιλοξ. ≥1000 χλμ', h2 & (G.h_prev_side2 == 1) & G.tr_any)
hc('  γηπ. ΕΝΤΟΣ→ΕΝΤΟΣ & φιλοξ. <1000 χλμ', h2 & (G.h_prev_side2 == 1) & ~G.tr_any)
hc('  γηπ. γυρισμα ≥1000 & φιλοξ. ≥1000 χλμ (και οι 2 ταξιδεψαν)', h2 & (G.h_prev_side2 == -1) & (G.h_travel >= 1000) & G.tr_any)
hc('  γηπ. γυρισμα ≥1000 & φιλοξ. <1000', h2 & (G.h_prev_side2 == -1) & (G.h_travel >= 1000) & ~G.tr_any)
open('el_dw_fatigue_deep_out.txt', 'w', encoding='utf-8').write('\n'.join(out))

# ---- 9. ΕΝΙΑΙΟΣ ΔΕΙΚΤΗΣ: χλμ ταξιδιου καθε ομαδας μεσα στη διαβολοβδομαδα (ταξιδι για το 1ο ματς αν ηταν εκτος + ταξιδι για το 2ο) ----
P(''); P('=== 9. ΔΙΑΦΟΡΑ ΚΟΥΡΑΣΗΣ ΑΠΟ ΤΑΞΙΔΙΑ στη διαβολοβδομαδα: (χλμ φιλοξ. − χλμ γηπ.) / 1000 → αποκλιση υπερ γηπ. vs μοντελο ===')
T['home_loc'] = [HB.get((s, t_)) for s, t_ in zip(T.season, T.team)]
T['prev2_loc'] = T.groupby(['season', 'team'])['loc'].shift(2)
T['prev2_t'] = T.groupby(['season', 'team']).t.shift(2)
def leg_in(r):
    """ταξιδι ΠΡΟΣ το προηγουμενο ματς (αν ηταν εκτος): απο το γηπεδο πριν απ αυτο αν ηταν ≤4 μερες πριν, αλλιως απο την εδρα"""
    if r.prev_side != -1 or not r.prev_loc: return 0.0
    src = r.prev2_loc if (isinstance(r.prev2_t, pd.Timestamp) and (r.prev_t - r.prev2_t).total_seconds() / 86400 <= 4 and r.prev2_loc) else r.home_loc
    return km(src, r.prev_loc) if src else np.nan
T['leg1'] = [leg_in(r) if d else np.nan for r, d in zip(T.itertuples(), T.dw2)]
T['leg2'] = [km(a, b) if (d and a and b) else (0.0 if d else np.nan) for a, b, d in zip(T.prev_loc, T['loc'], T.dw2)]
T['dwkm'] = T.leg1 + T.leg2
HO2 = T[T.side == 1].set_index('pos'); AW2 = T[T.side == -1].set_index('pos')
G['h_dwkm'] = HO2.loc[G.index, 'dwkm'].values; G['a_dwkm'] = AW2.loc[G.index, 'dwkm'].values
Z = G[(G.h_dw2 == True) & (G.a_dw2 == True)].dropna(subset=['h_dwkm', 'a_dwkm']).copy()
Z['dk'] = (Z.a_dwkm - Z.h_dwkm) / 1000
P(f'  ματς: {len(Z)} · χλμ γηπ μ.ο. {Z.h_dwkm.mean():.0f} · φιλοξ. {Z.a_dwkm.mean():.0f} · διαφορα (φιλ−γηπ) διασπορα {Z.dk.std():.2f} χιλ.χλμ')
for y, lab in (('rm_m', 'vs ΜΟΝΤΕΛΟ'), ('rm_c', 'vs ΑΓΟΡΑ')):
    cf = np.polyfit(Z.dk, Z[y], 1); r = Z[y] - np.polyval(cf, Z.dk)
    se = math.sqrt(np.sum(r ** 2) / (len(Z) - 2) / np.sum((Z.dk - Z.dk.mean()) ** 2))
    per = [np.polyfit(Z[Z.season == Y].dk, Z[Z.season == Y][y], 1)[0] for Y in SE5]
    P(f'  {lab:12s} κλιση {cf[0]:+.2f} π. ανα 1000 χλμ διαφορας (t {cf[0]/se:+.1f}) · σταθερος ορος {cf[1]:+.2f} · ανα σεζον [' + ' '.join(f'{p:+.2f}' for p in per) + f'] · ιδια φορα {sum(np.sign(p) == np.sign(cf[0]) for p in per)}/5')
P('  ανα ζωνη διαφορας (φιλ − γηπ, χλμ): ')
for lo, hi in ((-99, -1), (-1, 0.5), (0.5, 1.5), (1.5, 2.5), (2.5, 99)):
    x = Z[(Z.dk >= lo) & (Z.dk < hi)]
    if len(x) >= 8: P(f'    {lo*1000 if lo > -99 else "−∞"}…{hi*1000 if hi < 99 else "+∞"}: n {len(x):3d} · vs μοντελο {x.rm_m.mean():+5.2f} · vs αγορα {x.rm_c.mean():+5.2f}')
# LOSO: διορθωση = κλιση × dk (χωρις σταθερο ορο — μονο η διαφορα ταξιδιου), κλιση απο τις αλλες σεζον
rb, rn, rs = [], [], []
for Y in SE5:
    tr_ = Z[Z.season != Y]; b = np.sum(tr_.dk * tr_.rm_m) / np.sum(tr_.dk ** 2); rs.append(b)
    te = G[G.season == Y]; dk = pd.Series(0.0, index=te.index); zz = Z[Z.season == Y]; dk.loc[zz.index] = zz.dk
    rb.append(np.sqrt(np.mean((te.margin - te.hm) ** 2))); rn.append(np.sqrt(np.mean((te.margin - te.hm - b * dk) ** 2)))
w_ = sum(n < b for n, b in zip(rn, rb))
P(f'  LOSO διορθωση = κλιση × διαφορα χλμ (κλισεις {" ".join(f"{b:+.2f}" for b in rs)} π./1000 χλμ): RMSE ολης της σεζον ' + ' '.join(f'{n - b:+.4f}' for n, b in zip(rn, rb))
  + f' (συνολο {sum(rn) - sum(rb):+.4f}) → καλυτερο {w_}/5 {"ΠΕΡΝΑ" if w_ >= 4 else "✗"}  [συγκριση: ΜΙΑ κοινη διορθωση συνολο −0.1088]')
open('el_dw_fatigue_deep_out.txt', 'w', encoding='utf-8').write('\n'.join(out))

# ---- 10. ΦΙΛΟΞ ≥1000 χλμ, διορθωση αναλογα με τον ΓΗΠΕΔΟΥΧΟ (εμεινε σπιτι / ταξιδεψε) ----
P(''); P('=== 10. ΦΙΛΟΞ. ≥1000 χλμ: διορθωση αναλογα με το αν ο ΓΗΠΕΔΟΥΧΟΣ επαιξε και το 1ο στο σπιτι (LOSO) ===')
G['tr_hh'] = G.tr_any & (G.h_prev_side2 == 1)
G['tr_hx'] = G.tr_any & (G.h_prev_side2 == -1)
r4 = loso(['tr_hh', 'tr_hx'], lab='ΔΥΟ (γηπ. σπιτι / γηπ. ταξιδεψε)')
r5 = loso(['tr_hh', 'tr_hx'], shrink=50, lab='ΔΥΟ με συγκρατηση (50)')
P('  vs ΜΙΑ κοινη: ' + ' '.join(f'{a - b:+.4f}' for a, b in zip(r5, r1)) + f' → καλυτερο {sum(a < b for a, b in zip(r5, r1))}/5')
open('el_dw_fatigue_deep_out.txt', 'w', encoding='utf-8').write('\n'.join(out))

# ---- 11. 2×2: φιλοξ. απο εντος/εκτος × γηπ. σπιτι/ταξιδεψε (φιλοξ. ≥1000 χλμ) ----
P(''); P('=== 11. 2×2 (φιλοξ. ≥1000 χλμ): αποκλιση υπερ γηπ. vs μοντελο ===')
for ap, al in ((1, 'φιλοξ. ΑΠΟ ΕΝΤΟΣ'), (-1, 'φιλοξ. ΑΠΟ ΕΚΤΟΣ')):
    for hp, hl in ((1, 'γηπ. ΕΜΕΙΝΕ σπιτι'), (-1, 'γηπ. ΤΑΞΙΔΕΨΕ')):
        x = G[G.tr_any & (G.a_prev_side2 == ap) & (G.h_prev_side2 == hp)]
        if len(x): P(f'  {al:18s} · {hl:18s} n {len(x):3d} · vs μοντελο {x.rm_m.mean():+5.2f} (±{1.96 * x.rm_m.std() / math.sqrt(max(len(x), 2)):.1f}) · vs αγορα {x.rm_c.mean():+5.2f}')
open('el_dw_fatigue_deep_out.txt', 'w', encoding='utf-8').write('\n'.join(out))

# ---- 12. γηπεδουχος που «ταξιδεψε» ΚΟΝΤΑ (π.χ. Μιλανο → Μπολονια): μετραει σαν «εμεινε σπιτι»; (φιλοξ. ≥1000 χλμ) ----
P(''); P('=== 12. ΦΙΛΟΞ. ≥1000 χλμ · γηπεδουχος: σπιτι / γυρισε απο ΚΟΝΤΙΝΟ εκτος / απο ΜΑΚΡΙΝΟ εκτος (vs μοντελο) ===')
for lab, m in (('γηπ. ΕΜΕΙΝΕ σπιτι', G.tr_any & (G.h_prev_side2 == 1)),
               ('γηπ. γυρισε απο εκτος <500 χλμ', G.tr_any & (G.h_prev_side2 == -1) & (G.h_travel < 500)),
               ('γηπ. γυρισε απο εκτος 500-1000 χλμ', G.tr_any & (G.h_prev_side2 == -1) & (G.h_travel >= 500) & (G.h_travel < 1000)),
               ('γηπ. γυρισε απο εκτος ≥1000 χλμ', G.tr_any & (G.h_prev_side2 == -1) & (G.h_travel >= 1000))):
    x = G[m]
    if len(x): P(f'  {lab:36s} n {len(x):3d} · vs μοντελο {x.rm_m.mean():+5.2f} (±{1.96 * x.rm_m.std() / math.sqrt(max(len(x), 2)):.1f}) · vs αγορα {x.rm_c.mean():+5.2f}')
open('el_dw_fatigue_deep_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
