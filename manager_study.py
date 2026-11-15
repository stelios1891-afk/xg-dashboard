"""
manager_study.py — 5/10/2026 (Στελιος «παμε»): ΑΛΛΑΓΗ ΠΡΟΠΟΝΗΤΗ — ολες οι πτυχες, με ΟΜΑΔΑ-ΕΛΕΓΧΟ (επιστροφη στον μεσο ορο).
Δεδομενα: προπονητης καθε ματς (managers_all.json, FotMob) · σουτ/xG (data_*.json) · τελικη γραμμη Pinnacle (core7_sos15_final, 2223-2526)
· ανοιγμα/κλεισιμο Crown & κλεισιμο Bet365 (Nowgoal) · προβλεψη μηχανης live (core7_mech_preds_cur_0.75_6_13~emps.csv). CORE7.
Για καθε ματς της ομαδας μετα την αλλαγη: (1) υπολοιπο vs ΑΓΟΡΑ (γκολ − υπεροχη αγορας) · (2) vs ΜΟΝΤΕΛΟ · (3) DATA: xG διαφορα/ματς.
ΟΜΑΔΑ-ΕΛΕΓΧΟΣ (μονο για αλλαγες μεσα στη σεζον): ομαδες σε ιδια φαση σεζον με παρομοιο σερι (βαθμοι & xG διαφορα τελευταιων 8) ΧΩΡΙΣ
αλλαγη προπονητη (−8..+15 ματς) — οι 10 πλησιεστερες ανα αλλαγη. ΑΠΟΤΕΛΕΣΜΑ ΠΡΟΠΟΝΗΤΗ = ομαδα που αλλαξε − ελεγχος.
Ε1 «φρεσκος αερας» · Ε2 κακη vs ατυχη vs τυχερη · Ε3 ποιος ερχεται (ιστορικο, μεταβατικος, αλλαγη υφους) · Ε4 καλοκαιρινη αλλαγη · Ε5 ROI.
Τιποτα live.
"""
import sys, io, contextlib, json, glob
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
LG = ['EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'PrimeiraLiga', 'Eredivisie']
SEAS = ['2122', '2223', '2324', '2425', '2526']
MG = json.load(open('managers_all.json', encoding='utf-8'))
# ---- αγορα & μοντελο ----
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
src = open('core7_sos15_final.py', encoding='utf-8').read()
pre = src[:src.index('RES = {}')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass')
g = {'__name__': 'mgr'}
with contextlib.redirect_stdout(_Q()):
    exec(pre, g)
D, NG = g['D'], g['NG']
MK = {r.mid: r for r in D.itertuples()}
PR = pd.read_csv('core7_mech_preds_cur_0.75_6_13~emps.csv', dtype={'mid': str}).set_index('mid')
# ---- χρονολογιο ομαδων ----
rows = []
for lg in LG:
    for sea in SEAS:
        try: d = json.load(open(f'data_{lg}_{sea}.json', encoding='utf-8'))
        except FileNotFoundError: continue
        for mid, m in d.items():
            mid = str(mid)
            if m.get('hs') is None or mid not in MG: continue
            H, A = int(m['home']['id']), int(m['away']['id'])
            sh = [s for s in m.get('shots') or [] if s.get('xg') is not None]
            if not ({s.get('tid') for s in sh} >= {H, A}): continue
            x = {t: sum(s['xg'] for s in sh if s.get('tid') == t and s.get('sit') != 'Penalty') for t in (H, A)}
            n = {t: sum(1 for s in sh if s.get('tid') == t) for t in (H, A)}
            mg = MG[mid]; dt = pd.Timestamp(m['date'].replace(' UTC', ''))
            mk = MK.get(mid); pr = PR.loc[mid] if mid in PR.index else None
            for side, t, o, gf, ga, cc in ((1, H, A, m['hs'], m['as'], mg.get('h')), (-1, A, H, m['as'], m['hs'], mg.get('a'))):
                r = dict(lg=lg, sea=sea, mid=mid, date=dt, team=t, opp=o, home=side == 1, coach=(cc or [None])[0], coach_nm=(cc or [None, None])[1],
                         gf=gf, ga=ga, xgf=x[t], xga=x[o], shf=n[t], sha=n[o], pts=3 * (gf > ga) + (gf == ga))
                if mk is not None and mk.s_mkt == mk.s_mkt:
                    r['mkt'] = side * mk.s_mkt
                    L = mk.L * side if mk.L == mk.L else np.nan; od = mk.ah if side == 1 else mk.aa
                    r['pnl_pin'] = picks.settle(side * (mk.gd), 1, L, od) if (L == L and od == od) else np.nan
                    for bk in ('Crown', 'Bet365'):
                        q = NG.get((mid, bk))
                        if q:
                            for nm, qq in (('open', q[0]), ('close', q[1])):
                                Lq = qq[0] * side; oq = qq[1] if side == 1 else qq[2]
                                r[f'pnl_{bk}_{nm}'] = picks.settle(side * mk.gd, 1, Lq, oq)
                if pr is not None:
                    r['mod'] = side * (pr.xg_h - pr.xg_a)
                rows.append(r)
T = pd.DataFrame(rows).sort_values(['team', 'date']).reset_index(drop=True)
T['gd'] = T.gf - T.ga; T['xgd'] = T.xgf - T.xga
T['r_mkt'] = T.gd - T.mkt; T['r_mod'] = T.gd - T['mod']
T['md'] = T.groupby(['team', 'lg', 'sea']).cumcount() + 1
T['i'] = T.groupby('team').cumcount()
print(f'ομαδες-ματς: {len(T)} · με αγορα: {T.mkt.notna().sum()} · με προπονητη: {T.coach.notna().sum()}')
# ---- αλλαγες (ΚΑΘΑΡΙΣΜΕΝΕΣ): το FotMob γραφει μερικες φορες τον βοηθο στον παγκο (τιμωρια/ασθενεια) → «σεκανς» ≤2 ματς
#      αναμεσα στον ΙΔΙΟ προπονητη = θορυβος. Μεταβατικος = σεκανς ≤4 ματς αναμεσα σε ΔΙΑΦΟΡΕΤΙΚΟΥΣ προπονητες.
EV = []
for t, g_ in T.groupby('team'):
    g_ = g_.reset_index(drop=True)
    co = g_.coach.ffill().bfill().tolist()
    runs = []
    for i, c in enumerate(co):
        if runs and runs[-1][0] == c: runs[-1][2] += 1
        else: runs.append([c, i, 1])
    changed = True
    while changed:
        changed = False
        for j in range(1, len(runs) - 1):
            if runs[j][2] <= 2 and runs[j - 1][0] == runs[j + 1][0]:
                runs[j - 1][2] += runs[j][2] + runs[j + 1][2]; del runs[j:j + 2]; changed = True; break
    for j in range(1, len(runs)):
        prv, cur = runs[j - 1], runs[j]
        if prv[2] <= 4 and j >= 2 and runs[j - 2][0] != cur[0]: continue      # η αλλαγη ξεκινησε ηδη με τον μεταβατικο (καταγραφηκε)
        k = cur[1]; a, b = g_.loc[k - 1], g_.loc[k]
        caretaker = cur[2] <= 4 and j + 1 < len(runs)
        perm = runs[j + 1] if caretaker else cur
        summer = a.sea != b.sea
        prev = g_.loc[max(0, k - 8):k - 1]
        EV.append(dict(team=t, k=k, lg=b.lg, sea=b.sea, date=b.date, md=b.md, summer=summer, old=prv[0], new=perm[0],
                       new_nm=g_.loc[perm[1], 'coach_nm'], tenure=perm[2], caretaker=caretaker, pre_ppg=prev.pts.mean(), pre_gd=prev.gd.mean(),
                       pre_xgd=prev.xgd.mean(), pre_luck=(prev.gd - prev.xgd).mean(), pre_rmkt=prev.r_mkt.mean(), n_pre=len(prev)))
E = pd.DataFrame(EV)
print(f'αλλαγες: {len(E)} · καλοκαιρινες {int(E.summer.sum())} · μεσα στη σεζον {int((~E.summer).sum())} · μεταβατικοι (≤4 ματς) {int(E.caretaker.sum())}')
print('ανα σεζον (μεσα στη σεζον): ' + ' '.join(f'{s}:{n}' for s, n in E[~E.summer].groupby('sea').size().items()))
# ---- μετα-παραθυρα ----
WIN = [(1, 3), (4, 8), (9, 15), (16, 30)]
TT = {t: g_.reset_index(drop=True) for t, g_ in T.groupby('team')}
def post(t, k, lo, hi, same_sea=None):
    g_ = TT[t]; x = g_.loc[k + lo - 1:k + hi - 1]
    if same_sea is not None: x = x[x.sea == same_sea]
    return x
# ---- ελεγχος: σημεια χωρις αλλαγη −8..+15 ----
chg = {(e.team, e.k) for e in E.itertuples()}
CAND = []
for t, g_ in TT.items():
    ks = [k for (tt, k) in chg if tt == t]
    for k in range(8, len(g_) - 3):
        if any(-15 <= k - kk <= 8 for kk in ks): continue
        if g_.loc[k, 'sea'] != g_.loc[k - 1, 'sea']: continue
        prev = g_.loc[k - 8:k - 1]
        CAND.append((t, k, g_.loc[k, 'md'], g_.loc[k, 'sea'], prev.pts.mean(), prev.xgd.mean(), (prev.gd - prev.xgd).mean()))
C = pd.DataFrame(CAND, columns=['team', 'k', 'md', 'sea', 'ppg', 'xgd', 'luck'])
def controls(e, n=10):
    c = C[(C.team != e.team) & ((C.md - e.md).abs() <= 5)]
    dist = ((c.ppg - e.pre_ppg) / 0.5) ** 2 + ((c.xgd - e.pre_xgd) / 0.4) ** 2
    return c.loc[dist.nsmallest(n).index]
def outcome(t, k, lo, hi, sea):
    x = post(t, k, lo, hi, sea)
    return dict(r_mkt=x.r_mkt.mean(), r_mod=x.r_mod.mean(), xgd=x.xgd.mean(), ppg=x.pts.mean(), n=len(x))
INS = E[(~E.summer) & (E.n_pre >= 5)].copy()
res = []
for e in INS.itertuples():
    ctl = controls(e)
    for lo, hi in WIN:
        o = outcome(e.team, e.k, lo, hi, e.sea)
        if o['n'] == 0: continue
        co = [outcome(c.team, c.k, lo, hi, c.sea) for c in ctl.itertuples()]
        co = pd.DataFrame(co); co = co[co.n > 0]
        res.append(dict(team=e.team, sea=e.sea, win=f'{lo}-{hi}', ev=e.Index, caretaker=e.caretaker, pre_luck=e.pre_luck, pre_xgd=e.pre_xgd, pre_ppg=e.pre_ppg,
                        **{f't_{k}': v for k, v in o.items()}, **{f'c_{k}': co[k].mean() for k in ('r_mkt', 'r_mod', 'xgd', 'ppg')},
                        pre_xgd_c=ctl.xgd.mean()))
RS = pd.DataFrame(res)
RS['d_mkt'] = RS.t_r_mkt - RS.c_r_mkt; RS['d_mod'] = RS.t_r_mod - RS.c_r_mod; RS['d_xgd'] = RS.t_xgd - RS.c_xgd; RS['d_ppg'] = RS.t_ppg - RS.c_ppg
RS.to_csv('manager_study_rows.csv', index=False)
def line(d, lab):
    if len(d) < 15: return f'   {lab:30s} n{len(d):4d}'
    out = []
    for col, nm in (('ppg', 'βαθμοι/ματς'), ('xgd', 'xG διαφ.'), ('r_mod', 'vs ΜΟΝΤΕΛΟ'), ('r_mkt', 'vs ΑΓΟΡΑ')):
        dd = (d[f't_{col}'] - d[f'c_{col}']).dropna(); se = dd.std() / np.sqrt(len(dd)) if len(dd) > 2 else np.nan
        ps = d.assign(x=d[f't_{col}'] - d[f'c_{col}']).groupby('sea').x.mean()
        out.append(f'{nm} {d[f"t_{col}"].mean():+.2f}/{d[f"c_{col}"].mean():+.2f} Δ{dd.mean():+.2f}±{se:.2f} [{int((ps > 0).sum())}/{len(ps)}]')
    return f'   {lab:30s} n{len(d):4d} · ' + ' · '.join(out)
print('\nΕ1 «ΦΡΕΣΚΟΣ ΑΕΡΑΣ» — αλλαγες ΜΕΣΑ στη σεζον: ομαδα που αλλαξε / ΕΛΕΓΧΟΣ (ιδιο σερι, χωρις αλλαγη) · Δ = αποτελεσμα προπονητη ±SE [σεζον θετικες]')
print('   (υπολοιπα σε γκολ/ματς· «vs ΑΓΟΡΑ» θετικο = η ομαδα τα πηγε καλυτερα απο τη γραμμη Pinnacle)')
for w in ('1-3', '4-8', '9-15', '16-30'):
    print(line(RS[RS.win == w], f'ματς {w} μετα'))
print(f'   (πριν την αλλαγη, τελευταια 8: βαθμοι/ματς {INS.pre_ppg.mean():.2f} · xG διαφ {INS.pre_xgd.mean():+.2f} · τυχη (γκολ−xG) {INS.pre_luck.mean():+.2f})')
print('\nΕ2 ΚΑΚΗ vs ΑΤΥΧΗ vs ΤΥΧΕΡΗ (σερι πριν την αλλαγη)')
RS['typ'] = np.where(RS.pre_luck <= -0.35, 'ΑΤΥΧΗ (αποτελεσματα < data)', np.where(RS.pre_luck >= 0.20, 'ΤΥΧΕΡΗ (αποτελεσματα > data)', 'ΚΑΚΗ ΚΑΙ ΣΤΑ ΔΥΟ / ισορροπια'))
for typ in ('ΑΤΥΧΗ (αποτελεσματα < data)', 'ΚΑΚΗ ΚΑΙ ΣΤΑ ΔΥΟ / ισορροπια', 'ΤΥΧΕΡΗ (αποτελεσματα > data)'):
    print(f'  [{typ}]  αλλαγες: {RS[(RS.typ == typ) & (RS.win == "1-3")].ev.nunique()}')
    for w in ('1-3', '4-8', '9-15'):
        print(line(RS[(RS.typ == typ) & (RS.win == w)], f'ματς {w}'))
print('  και με βαση τα DATA πριν: ')
for lab, cond in (('xG διαφ. πριν ≤ −0.4 (κακη στα data)', RS.pre_xgd <= -0.4), ('xG διαφ. πριν > −0.1 (ΟΚ στα data)', RS.pre_xgd > -0.1)):
    for w in ('1-3', '4-8'):
        print(line(RS[cond & (RS.win == w)], f'{lab[:22]} {w}'))
print('\nΕ3α ΜΕΤΑΒΑΤΙΚΟΣ (≤4 ματς) vs ΜΟΝΙΜΟΣ')
for cl, lab in ((True, 'μεταβατικος'), (False, 'μονιμος')):
    for w in ('1-3', '4-8'):
        print(line(RS[(RS.caretaker == cl) & (RS.win == w)], f'{lab} {w}'))
# ---- Ε3β ιστορικο νεου προπονητη ----
T['r_mkt_x'] = T.xgd - T.mkt          # xG διαφορα πανω απο οσο εδινε η αγορα (επιδοση «επεξεργασιας»)
def record(coach, before):
    x = T[(T.coach == coach) & (T.date < before)]
    return x.r_mkt_x.mean() if x.r_mkt_x.notna().sum() >= 15 else np.nan, x.r_mkt_x.notna().sum()
E['new_rec'], E['new_rec_n'] = zip(*[record(e.new, e.date) for e in E.itertuples()])
E['old_rec'], E['old_rec_n'] = zip(*[record(e.old, e.date) for e in E.itertuples()])
RS = RS.merge(E[['new_rec', 'old_rec']], left_on='ev', right_index=True, how='left')
print('\nΕ3β ΠΟΙΟΣ ΕΡΧΕΤΑΙ — ιστορικο του νεου στα προηγουμενα ματς του (xG διαφορα πανω απο τη γραμμη αγορας, ≥15 ματς στη βαση μας)')
print(f'   αλλαγες με ιστορικο νεου: {RS[(RS.win == "1-3") & RS.new_rec.notna()].ev.nunique()} · και παλιου & νεου: {RS[(RS.win == "1-3") & RS.new_rec.notna() & RS.old_rec.notna()].ev.nunique()}')
for w in ('1-3', '4-8', '9-15'):
    x = RS[(RS.win == w) & RS.new_rec.notna()]
    if len(x) < 15: continue
    hi = x.new_rec >= x.new_rec.median()
    print(line(x[hi], f'ΚΑΛΟ ιστορικο νεου {w}')); print(line(x[~hi], f'ΚΑΚΟ ιστορικο νεου {w}'))
    cc = x[['new_rec', 'd_mkt', 'd_xgd']].corr()
    print(f'      συσχετιση ιστορικου νεου με Δ vs αγορα {cc.loc["new_rec", "d_mkt"]:+.2f} · με Δ xG {cc.loc["new_rec", "d_xgd"]:+.2f} (n{len(x)})')
# ---- Ε3γ αλλαγη υφους ----
st = []
for e in INS.itertuples():
    g_ = TT[e.team]; b4 = g_.loc[max(0, e.k - 8):e.k - 1]; af = g_.loc[e.k:e.k + 7]; af = af[af.sea == e.sea]
    if len(af) < 4: continue
    st.append(dict(ev=e.Index, d_shf=af.shf.mean() - b4.shf.mean(), d_sha=af.sha.mean() - b4.sha.mean(),
                   d_q=(af.xgf.sum() / max(af.shf.sum(), 1)) - (b4.xgf.sum() / max(b4.shf.sum(), 1))))
STY = pd.DataFrame(st).set_index('ev'); RS = RS.merge(STY, left_on='ev', right_index=True, how='left')
RS['style'] = (RS.d_shf.abs() + RS.d_sha.abs())
print('\nΕ3γ ΑΛΛΑΓΗ ΥΦΟΥΣ (ποσο αλλαζουν τα σουτ υπερ/κατα στα 8 πρωτα ματς) — μεγαλη vs μικρη αλλαγη, αποτελεσμα στα ματς 9-15')
x = RS[(RS.win == '9-15') & RS['style'].notna()]
if len(x) > 20:
    hi = x['style'] >= x['style'].median()
    print(line(x[hi], 'μεγαλη αλλαγη υφους')); print(line(x[~hi], 'μικρη αλλαγη υφους'))
# ---- Ε4 καλοκαιρινη ----
print('\nΕ4 ΚΑΛΟΚΑΙΡΙΝΗ ΑΛΛΑΓΗ — υπολοιπο vs ΜΟΝΤΕΛΟ & vs ΑΓΟΡΑ ανα αγωνιστικη (ομαδες με νεο προπονητη vs χωρις)')
SUM = E[E.summer][['team', 'sea']].drop_duplicates(); SUM['sch'] = 1
T2 = T.merge(SUM, on=['team', 'sea'], how='left'); T2['sch'] = T2.sch.fillna(0)
for lo, hi in ((1, 6), (7, 14), (15, 25), (26, 40)):
    x = T2[(T2.md >= lo) & (T2.md <= hi) & T2.mkt.notna()]
    a, b = x[x.sch == 1], x[x.sch == 0]
    ps = a.groupby('sea').r_mod.mean()
    print(f'   αγωνιστικες {lo}-{hi}: ΝΕΟΣ n{len(a):4d} vs ΜΟΝΤΕΛΟ {a.r_mod.mean():+.3f} (±{a.r_mod.std()/np.sqrt(len(a)):.3f}, {int((ps < 0).sum())}/{len(ps)} σεζον αρνητ.) · vs ΑΓΟΡΑ {a.r_mkt.mean():+.3f}'
          f' | ΙΔΙΟΣ n{len(b):4d} vs ΜΟΝΤΕΛΟ {b.r_mod.mean():+.3f} · vs ΑΓΟΡΑ {b.r_mkt.mean():+.3f}')
# ---- Ε5 ROI ----
print('\nΕ5 ΤΥΦΛΟ ROI ΥΠΕΡ της ομαδας με νεο προπονητη (μεσα στη σεζον) — Pinnacle κλεισιμο | Crown ανοιγμα | Crown κλεισιμο | Bet365 κλεισιμο')
def roi(x, c):
    y = x[c].dropna(); ps = x.groupby('sea')[c].mean()
    return f'n{len(y):4d} {100*y.mean():+6.1f}% ({int((ps > 0).sum())}/{ps.notna().sum()})' if len(y) >= 15 else f'n{len(y):4d}'
for lo, hi in ((1, 3), (4, 8), (9, 15)):
    xs = pd.concat([post(e.team, e.k, lo, hi, e.sea) for e in INS.itertuples()])
    print(f'   ματς {lo}-{hi}: ' + ' | '.join(roi(xs, c) for c in ('pnl_pin', 'pnl_Crown_open', 'pnl_Crown_close', 'pnl_Bet365_close')))
for typ, cond in (('ΑΤΥΧΗ', INS.pre_luck <= -0.35), ('ΚΑΚΗ/ισορροπια', (INS.pre_luck > -0.35) & (INS.pre_luck < 0.20))):
    xs = pd.concat([post(e.team, e.k, 1, 8, e.sea) for e in INS[cond].itertuples()])
    print(f'   {typ} ματς 1-8: ' + ' | '.join(roi(xs, c) for c in ('pnl_pin', 'pnl_Crown_open', 'pnl_Crown_close', 'pnl_Bet365_close')))
# ---- Ε5β ΚΟΝΤΡΑ στην ομαδα με νεο προπονητη (ποντααρισμα στον αντιπαλο) ----
OPP = T.set_index(['mid', 'team'])
def against(x):
    keys = list(zip(x.mid, x.opp)); y = OPP.reindex(keys)
    y = y.assign(sea=x.sea.values)
    return y
print('\nΕ5β ΤΥΦΛΟ ROI ΚΟΝΤΡΑ στην ομαδα με νεο προπονητη (στον αντιπαλο) — Pinnacle κλεισιμο | Crown ανοιγμα | Crown κλεισιμο | Bet365 κλεισιμο')
for lab, sub in (('ολες', INS), ('μεταβατικος', INS[INS.caretaker]), ('μονιμος', INS[~INS.caretaker]),
                 ('ΚΑΚΗ/ισορροπια', INS[(INS.pre_luck > -0.35) & (INS.pre_luck < 0.20)]), ('ΑΤΥΧΗ', INS[INS.pre_luck <= -0.35])):
    for lo, hi in ((1, 3), (4, 8), (1, 8), (9, 15)):
        xs = pd.concat([post(e.team, e.k, lo, hi, e.sea) for e in sub.itertuples()])
        ya = against(xs)
        print(f'   {lab:15s} ματς {lo}-{hi}: ' + ' | '.join(roi(ya, c) for c in ('pnl_pin', 'pnl_Crown_open', 'pnl_Crown_close', 'pnl_Bet365_close')))
